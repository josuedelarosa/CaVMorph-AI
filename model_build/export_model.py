#!/usr/bin/env python3
"""
PhenoAI Model Export: MMPose PyTorch → ONNX

This script converts the CaVFish/MMPose ViTPose model to ONNX format
for use with the thin ONNX Runtime inference engine.

Requirements:
  - The full MMPose/Conda environment (cavfish310)
  - Model files: config.py + weights.pth in the model directory

Usage:
  python model_build/export_model.py [--model-dir models/cavfish_v1] [--output-dir model_build/output]

Outputs:
  - model.onnx              — Exported ONNX model
  - model_metadata.json     — Metadata for the inference runtime
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# Ensure the repo root is on the path
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "backend"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("export")


def load_mmpose_model(config_path: str, weights_path: str, device: str = "cpu"):
    """Load the MMPose model using the existing manager."""
    logger.info("Loading MMPose model from %s ...", config_path)
    from cavfish.manager import build_model_from_cfg

    model = build_model_from_cfg(config_path, weights_path, device=device)
    logger.info("Model loaded successfully")
    return model


def extract_backbone_and_head(model):
    """Extract the backbone + head subgraph for export.

    The TopdownPoseEstimator wraps:
      - data_preprocessor (normalization — we'll do this in preprocessing.py)
      - backbone (ViT)
      - head (CavfishHeatmapHead with deconv + final_layer)

    For ONNX export, we export backbone + head as a single graph.
    The data_preprocessor normalization is replicated in preprocessing.py.
    """
    import torch
    import torch.nn as nn

    class BackboneHeadWrapper(nn.Module):
        """Wrapper that takes a normalized (1,3,H,W) tensor and outputs heatmaps."""

        def __init__(self, backbone, head):
            super().__init__()
            self.backbone = backbone
            self.head = head

        def forward(self, x):
            feats = self.backbone(x)
            # backbone returns tuple of feature maps; head expects the last one
            if isinstance(feats, (list, tuple)):
                feats = feats[-1]
            # Head forward: deconv → conv → final_layer
            x = self.head.deconv_layers(feats)
            x = self.head.conv_layers(x)
            x = self.head.final_layer(x)
            return x

    wrapper = BackboneHeadWrapper(model.backbone, model.head)
    wrapper.eval()
    return wrapper


def export_to_onnx(
    model,
    wrapper,
    output_path: str,
    input_size: tuple = (192, 256),  # (W, H)
    opset_version: int = 17,
):
    """Export the backbone+head wrapper to ONNX."""
    import torch

    inp_w, inp_h = input_size
    dummy_input = torch.randn(1, 3, inp_h, inp_w, dtype=torch.float32)

    logger.info("Exporting to ONNX: %s (opset %d)", output_path, opset_version)
    logger.info("  Input shape: %s", dummy_input.shape)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        wrapper,
        (dummy_input,),
        output_path,
        opset_version=opset_version,
        input_names=["input"],
        output_names=["heatmaps"],
        dynamic_axes={
            "input": {0: "batch_size"},
            "heatmaps": {0: "batch_size"},
        },
        do_constant_folding=True,
    )

    logger.info("ONNX export complete: %s", output_path)

    # Verify output shape
    import onnxruntime as ort

    session = ort.InferenceSession(output_path, providers=["CPUExecutionProvider"])
    test_output = session.run(None, {"input": dummy_input.numpy()})
    logger.info("  Output shape: %s", test_output[0].shape)

    return test_output[0].shape


def build_metadata(
    config_path: str,
    output_shape: tuple,
    opset_version: int = 17,
) -> dict:
    """Build the model_metadata.json from the MMEngine config."""
    from cavfish.model_pack import load_py_config

    cfg = load_py_config(Path(config_path))

    metainfo = cfg.get("metainfo", {})
    codec = cfg.get("codec", {})
    model_cfg = cfg.get("model", {})
    preprocessor = model_cfg.get("data_preprocessor", {})

    # Extract keypoint names
    kp_info = metainfo.get("keypoint_info", {})
    kp_names = []
    for kid in sorted(kp_info.keys()):
        kp_names.append(kp_info[kid].get("name", f"kp{kid + 1}"))

    # Extract phenotype config from head
    head = model_cfg.get("head", {})
    loss_pheno = head.get("loss_pheno", {})
    pairs = loss_pheno.get("pairs", [])
    pairs_norm = [[int(p[0]), int(p[1])] for p in pairs]

    # Read existing meta.json for phenotype names/types if available
    meta_json_path = Path(config_path).parent / "meta.json"
    pheno_names = []
    pheno_types = []
    scale_by_sl = bool(loss_pheno.get("scale_by_SL", False))
    sl_pair = [0, 1] if scale_by_sl else None

    if meta_json_path.exists():
        existing_meta = json.loads(meta_json_path.read_text(encoding="utf-8"))
        pheno_names = existing_meta.get("phenotype_names", [])
        pheno_types = existing_meta.get("phenotype_types", [])
        sl_pair_existing = existing_meta.get("phenotype_sl_pair")
        if sl_pair_existing is not None:
            sl_pair = sl_pair_existing

    input_size = codec.get("input_size", (192, 256))
    heatmap_size = codec.get("heatmap_size", (48, 64))

    metadata = {
        "dataset_name": metainfo.get("dataset_name", "fish_20kpt"),
        "num_keypoints": metainfo.get("num_keypoints", 20),
        "keypoint_names": kp_names,
        "codec_input_size": [int(input_size[0]), int(input_size[1])],
        "heatmap_size": [int(heatmap_size[0]), int(heatmap_size[1])],
        "sigma": codec.get("sigma", 2.0),
        "normalization_mean": preprocessor.get("mean", [123.675, 116.28, 103.53]),
        "normalization_std": preprocessor.get("std", [58.395, 57.12, 57.375]),
        "bgr_to_rgb": preprocessor.get("bgr_to_rgb", True),
        "padding": 1.25,
        "phenotype_pairs": pairs_norm,
        "phenotype_names": pheno_names,
        "phenotype_types": pheno_types,
        "phenotype_scale_by_sl": scale_by_sl,
        "phenotype_sl_pair": sl_pair,
        "model_version": "cavfish_v1",
        "onnx_opset": opset_version,
        "onnx_output_shape": list(output_shape),
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return metadata


def main():
    parser = argparse.ArgumentParser(description="Export PhenoAI MMPose model to ONNX")
    parser.add_argument(
        "--model-dir",
        type=str,
        default=str(_REPO_ROOT / "models" / "cavfish_v1"),
        help="Directory containing config.py and weights.pth",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(_SCRIPT_DIR / "output"),
        help="Output directory for model.onnx and model_metadata.json",
    )
    parser.add_argument(
        "--opset",
        type=int,
        default=17,
        help="ONNX opset version (default: 17)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Device for model loading (default: cpu)",
    )
    parser.add_argument(
        "--copy-to-model-dir",
        action="store_true",
        help="Also copy outputs to the model directory for immediate use",
    )
    args = parser.parse_args()

    model_dir = Path(args.model_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    config_path = model_dir / "config.py"
    weights_path = model_dir / "weights.pth"

    if not config_path.exists():
        logger.error("Config not found: %s", config_path)
        sys.exit(1)
    if not weights_path.exists():
        logger.error("Weights not found: %s", weights_path)
        sys.exit(1)

    # Step 1: Load model
    t0 = time.time()
    model = load_mmpose_model(str(config_path), str(weights_path), args.device)

    # Step 2: Extract backbone + head
    wrapper = extract_backbone_and_head(model)

    # Step 3: Export to ONNX
    onnx_path = output_dir / "model.onnx"
    codec = model.cfg.codec if hasattr(model.cfg, "codec") else {"input_size": (192, 256)}
    input_size = codec.get("input_size", (192, 256)) if isinstance(codec, dict) else (192, 256)

    output_shape = export_to_onnx(
        model, wrapper, str(onnx_path), input_size=tuple(input_size), opset_version=args.opset
    )

    # Step 4: Build and save metadata
    metadata = build_metadata(str(config_path), output_shape, args.opset)
    metadata_path = output_dir / "model_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("Metadata saved: %s", metadata_path)

    # Step 5: Optionally copy to model directory
    if args.copy_to_model_dir:
        import shutil
        dest_onnx = model_dir / "model.onnx"
        dest_meta = model_dir / "model_metadata.json"
        shutil.copy2(str(onnx_path), str(dest_onnx))
        shutil.copy2(str(metadata_path), str(dest_meta))
        logger.info("Copied outputs to model dir: %s", model_dir)

    elapsed = time.time() - t0
    logger.info("Export complete in %.1fs", elapsed)
    logger.info("  ONNX model: %s (%.1f MB)", onnx_path, onnx_path.stat().st_size / 1e6)
    logger.info("  Metadata: %s", metadata_path)


if __name__ == "__main__":
    main()
