# Inference Runtime — ONNX Inference Engine
"""
Thin inference engine using ONNX Runtime.
No MMPose, no PyTorch at runtime. Only onnxruntime + numpy + opencv.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    import onnxruntime as ort
except ImportError:
    ort = None  # type: ignore[assignment]

from .types import ModelMetadata, InferenceResult, PhenotypeResult
from .preprocessing import preprocess_image
from .postprocessing import (
    decode_udp_heatmaps,
    transform_keypoints_to_original,
    compute_phenotypes,
)

logger = logging.getLogger("phenoai.inference")


class ONNXInferenceEngine:
    """ONNX Runtime inference engine for PhenoAI keypoint detection."""

    def __init__(
        self,
        model_path: str,
        metadata_path: str,
        device: str = "cpu",
    ):
        if ort is None:
            raise ImportError(
                "onnxruntime is required for inference. "
                "Install it with: pip install onnxruntime"
            )

        self.model_path = Path(model_path)
        self.metadata_path = Path(metadata_path)

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"Metadata not found: {self.metadata_path}")

        # Load metadata
        with open(self.metadata_path, "r", encoding="utf-8") as f:
            meta_dict = json.load(f)
        self.metadata = ModelMetadata.from_dict(meta_dict)

        # Create ONNX Runtime session
        providers = ["CPUExecutionProvider"]
        if device != "cpu":
            if "CUDAExecutionProvider" in ort.get_available_providers():
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self.session = ort.InferenceSession(
            str(self.model_path),
            sess_options=sess_options,
            providers=providers,
        )

        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

        logger.info(
            "Loaded ONNX model: %s (input=%s, output=%s)",
            self.model_path.name,
            self.input_name,
            self.output_name,
        )

    def infer(self, image_bgr: np.ndarray) -> InferenceResult:
        """Run inference on a single BGR image.

        Args:
            image_bgr: Input image in BGR format (H, W, 3) uint8.

        Returns:
            InferenceResult with keypoints in original image coordinates.
        """
        h, w = image_bgr.shape[:2]
        input_size = tuple(self.metadata.codec_input_size)  # (W, H) = (192, 256)
        heatmap_size = tuple(self.metadata.heatmap_size)  # (W, H) = (48, 64)

        # Preprocess
        tensor, center, scale = preprocess_image(
            image_bgr,
            input_size=input_size,
            mean=np.array(self.metadata.normalization_mean, dtype=np.float32),
            std=np.array(self.metadata.normalization_std, dtype=np.float32),
            padding=self.metadata.padding,
        )

        # Run ONNX inference
        outputs = self.session.run(
            [self.output_name],
            {self.input_name: tensor.astype(np.float32)},
        )

        # Output shape: (1, K, hm_H, hm_W) — heatmaps
        heatmaps = outputs[0][0]  # (K, hm_H, hm_W)

        # Decode heatmaps to keypoints in input image space
        kp_input, scores = decode_udp_heatmaps(
            heatmaps,
            input_size=input_size,
            heatmap_size=heatmap_size,
        )

        # Transform keypoints to original image coordinates
        kp_original = transform_keypoints_to_original(
            kp_input, center, scale, input_size
        )

        bbox = [0.0, 0.0, float(w), float(h)]

        result = InferenceResult(
            image_path="",
            keypoints=[kp_original.tolist()],
            keypoint_scores=[scores.tolist()],
            bboxes=[bbox],
            bbox_scores=[1.0],
        )

        # Compute phenotypes
        if self.metadata.phenotype_pairs:
            pheno_list = compute_phenotypes(
                kp_original,
                pairs=self.metadata.phenotype_pairs,
                scale_by_sl=self.metadata.phenotype_scale_by_sl,
                sl_pair=self.metadata.phenotype_sl_pair,
                phenotype_names=self.metadata.phenotype_names,
                phenotype_types=self.metadata.phenotype_types,
            )
            result.phenotypes = [
                PhenotypeResult(
                    id=p["id"],
                    pair=p["pair"],
                    name=p["name"],
                    type=p["type"],
                    value_px=p["value_px"],
                    value_norm=p["value_norm"],
                )
                for p in pheno_list
            ]

        return result

    def infer_path(self, image_path: str) -> InferenceResult:
        """Run inference on an image file path."""
        bgr = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if bgr is None:
            return InferenceResult(
                image_path=image_path,
                keypoints=[],
                keypoint_scores=[],
                bboxes=[],
                bbox_scores=[],
                error=f"Failed to read image: {image_path}",
            )

        result = self.infer(bgr)
        result.image_path = image_path
        return result

    def get_metadata_dict(self) -> Dict[str, Any]:
        """Return model metadata as a dict (for /model/info endpoint)."""
        return self.metadata.to_dict()


class FallbackPyTorchEngine:
    """Fallback engine that uses the legacy MMPose backend.
    
    DEPRECATED: This exists only as a migration bridge. It will be removed
    once ONNX export is validated and stable.
    """

    def __init__(self, model_dir: str, device: str = "cpu"):
        import warnings
        warnings.warn(
            "FallbackPyTorchEngine uses the legacy MMPose runtime. "
            "This is deprecated and will be removed in a future version. "
            "Export your model to ONNX using model_build/export_model.py.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.model_dir = Path(model_dir)
        self.device = device
        self._model = None
        self._meta = None
        self._config_path = None

    def _ensure_loaded(self):
        if self._model is not None:
            return

        from backend.cavfish.model_pack import ensure_model_pack, read_meta
        from backend.cavfish.manager import ModelManager

        pack = ensure_model_pack(self.model_dir)
        self._config_path = str(pack.config_path)
        self._meta = read_meta(pack.meta_path)

        mgr = ModelManager(
            str(pack.config_path),
            str(pack.weights_path),
            device=self.device,
        )
        self._model = mgr.load()

    def infer(self, image_bgr: np.ndarray) -> InferenceResult:
        self._ensure_loaded()

        from backend.cavfish.infer import infer_image

        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        pred = infer_image(
            self._model,
            rgb,
            cfg_path=self._config_path,
            device=self.device,
        )

        return InferenceResult(
            image_path="",
            keypoints=pred.get("keypoints", []),
            keypoint_scores=pred.get("keypoint_scores", []),
            bboxes=pred.get("bboxes", []),
            bbox_scores=pred.get("bbox_scores", []),
        )

    def infer_path(self, image_path: str) -> InferenceResult:
        bgr = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if bgr is None:
            return InferenceResult(
                image_path=image_path,
                keypoints=[],
                keypoint_scores=[],
                bboxes=[],
                bbox_scores=[],
                error=f"Failed to read image: {image_path}",
            )
        result = self.infer(bgr)
        result.image_path = image_path
        return result

    def get_metadata_dict(self) -> Dict[str, Any]:
        self._ensure_loaded()
        return dict(self._meta) if self._meta else {}


def create_engine(
    model_dir: str,
    device: str = "cpu",
    force_legacy: bool = False,
) -> ONNXInferenceEngine | FallbackPyTorchEngine:
    """Factory function: create the best available inference engine.

    Priority:
      1. ONNX Runtime (if model.onnx + model_metadata.json exist)
      2. Legacy PyTorch/MMPose fallback (if config.py + weights.pth exist)

    Set force_legacy=True or env PHENOAI_USE_LEGACY=1 to force the old path.
    """
    import os

    model_path = Path(model_dir)

    if force_legacy or os.environ.get("PHENOAI_USE_LEGACY", "").strip() == "1":
        logger.info("Using legacy PyTorch/MMPose engine (forced)")
        return FallbackPyTorchEngine(model_dir, device)

    onnx_path = model_path / "model.onnx"
    metadata_path = model_path / "model_metadata.json"

    if onnx_path.exists() and metadata_path.exists():
        logger.info("Using ONNX Runtime engine: %s", onnx_path)
        return ONNXInferenceEngine(str(onnx_path), str(metadata_path), device)

    # Fallback: check for legacy model files
    config_path = model_path / "config.py"
    weights_path = model_path / "weights.pth"
    if config_path.exists() and weights_path.exists():
        logger.warning(
            "ONNX model not found at %s. Falling back to legacy MMPose engine. "
            "Run model_build/export_model.py to create the ONNX model.",
            onnx_path,
        )
        return FallbackPyTorchEngine(model_dir, device)

    raise FileNotFoundError(
        f"No model artifacts found in {model_dir}. "
        f"Expected either model.onnx + model_metadata.json (ONNX) "
        f"or config.py + weights.pth (legacy PyTorch)."
    )
