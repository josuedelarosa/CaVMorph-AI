#!/usr/bin/env python3
"""
PhenoAI Export Validation: Compare MMPose vs ONNX Runtime outputs

Loads the same image through both the legacy MMPose pipeline and the new
ONNX Runtime pipeline, then compares outputs for numerical parity.

Usage:
  python model_build/validate_export.py \
    --model-dir models/cavfish_v1 \
    --test-image path/to/fish.jpg

If no test image is provided, generates a synthetic test image.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import cv2
import numpy as np

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "backend"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("validate")


def generate_synthetic_image(width: int = 640, height: int = 480) -> np.ndarray:
    """Generate a synthetic BGR test image with gradients and shapes."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    # Gradient background
    for c in range(3):
        img[:, :, c] = np.linspace(50, 200, width, dtype=np.uint8)[np.newaxis, :]
    # Add shapes
    cv2.ellipse(img, (width // 2, height // 2), (width // 3, height // 5), 0, 0, 360, (180, 120, 60), -1)
    cv2.circle(img, (width // 4, height // 3), 20, (255, 0, 0), -1)
    cv2.circle(img, (3 * width // 4, height // 3), 20, (0, 0, 255), -1)
    return img


def run_mmpose_inference(model_dir: Path, image_bgr: np.ndarray, device: str = "cpu") -> dict:
    """Run inference using the legacy MMPose pipeline."""
    from cavfish.model_pack import ensure_model_pack
    from cavfish.manager import build_model_from_cfg
    from cavfish.infer import infer_image

    pack = ensure_model_pack(model_dir)
    model = build_model_from_cfg(str(pack.config_path), str(pack.weights_path), device)

    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    pred = infer_image(model, rgb, cfg_path=str(pack.config_path), device=device)
    return pred


def run_onnx_inference(model_dir: Path, image_bgr: np.ndarray) -> dict:
    """Run inference using the ONNX Runtime pipeline."""
    from inference_runtime.inference import ONNXInferenceEngine

    onnx_path = model_dir / "model.onnx"
    meta_path = model_dir / "model_metadata.json"

    if not onnx_path.exists():
        # Try model_build/output
        alt_dir = _SCRIPT_DIR / "output"
        onnx_path = alt_dir / "model.onnx"
        meta_path = alt_dir / "model_metadata.json"

    engine = ONNXInferenceEngine(str(onnx_path), str(meta_path))
    result = engine.infer(image_bgr)
    return result.to_legacy_dict()


def compare_predictions(mmpose_pred: dict, onnx_pred: dict, tolerance_px: float = 1.0):
    """Compare keypoint predictions from both pipelines."""
    # Extract keypoints
    mm_kpts = np.array(mmpose_pred.get("keypoints", [[[]]]))
    onnx_kpts = np.array(onnx_pred.get("keypoints", [[[]]]))

    # Normalize shapes
    if mm_kpts.ndim == 3 and mm_kpts.shape[0] == 1:
        mm_kpts = mm_kpts[0]
    if onnx_kpts.ndim == 3 and onnx_kpts.shape[0] == 1:
        onnx_kpts = onnx_kpts[0]

    if mm_kpts.shape != onnx_kpts.shape:
        logger.error(
            "Shape mismatch: MMPose=%s, ONNX=%s", mm_kpts.shape, onnx_kpts.shape
        )
        return False

    # Per-keypoint distance
    diffs = np.linalg.norm(mm_kpts - onnx_kpts, axis=1)
    max_diff = float(np.max(diffs))
    mean_diff = float(np.mean(diffs))

    logger.info("Keypoint comparison (pixels):")
    logger.info("  Mean diff: %.4f px", mean_diff)
    logger.info("  Max diff:  %.4f px", max_diff)
    logger.info("  Tolerance: %.1f px", tolerance_px)

    for i, d in enumerate(diffs):
        status = "OK" if d <= tolerance_px else "FAIL"
        logger.info("  KP %2d: diff=%.4f px [%s]", i, d, status)

    passed = max_diff <= tolerance_px
    if passed:
        logger.info("PASS: All keypoints within %.1f px tolerance", tolerance_px)
    else:
        logger.warning(
            "FAIL: Max diff %.4f px exceeds %.1f px tolerance",
            max_diff, tolerance_px,
        )

    # Compare scores
    mm_scores = np.array(mmpose_pred.get("keypoint_scores", [[]]))
    onnx_scores = np.array(onnx_pred.get("keypoint_scores", [[]]))
    if mm_scores.ndim == 2 and mm_scores.shape[0] == 1:
        mm_scores = mm_scores[0]
    if onnx_scores.ndim == 2 and onnx_scores.shape[0] == 1:
        onnx_scores = onnx_scores[0]

    if mm_scores.shape == onnx_scores.shape:
        score_diffs = np.abs(mm_scores - onnx_scores)
        logger.info("Score comparison:")
        logger.info("  Mean diff: %.6f", float(np.mean(score_diffs)))
        logger.info("  Max diff:  %.6f", float(np.max(score_diffs)))

    return passed


def main():
    parser = argparse.ArgumentParser(description="Validate ONNX export parity")
    parser.add_argument(
        "--model-dir",
        type=str,
        default=str(_REPO_ROOT / "models" / "cavfish_v1"),
    )
    parser.add_argument(
        "--test-image",
        type=str,
        default=None,
        help="Path to test image (uses synthetic if not provided)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=1.0,
        help="Maximum allowed keypoint difference in pixels (default: 1.0)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
    )
    args = parser.parse_args()

    model_dir = Path(args.model_dir).resolve()

    if args.test_image:
        image_bgr = cv2.imread(args.test_image, cv2.IMREAD_COLOR)
        if image_bgr is None:
            logger.error("Failed to read test image: %s", args.test_image)
            sys.exit(1)
        logger.info("Using test image: %s (%dx%d)", args.test_image, image_bgr.shape[1], image_bgr.shape[0])
    else:
        image_bgr = generate_synthetic_image()
        logger.info("Using synthetic test image (640x480)")

    logger.info("=" * 60)
    logger.info("Running MMPose inference...")
    mmpose_pred = run_mmpose_inference(model_dir, image_bgr, args.device)

    logger.info("=" * 60)
    logger.info("Running ONNX inference...")
    onnx_pred = run_onnx_inference(model_dir, image_bgr)

    logger.info("=" * 60)
    passed = compare_predictions(mmpose_pred, onnx_pred, args.tolerance)

    # Save comparison report
    report = {
        "tolerance_px": args.tolerance,
        "passed": passed,
        "mmpose_keypoints": mmpose_pred.get("keypoints"),
        "onnx_keypoints": onnx_pred.get("keypoints"),
    }
    report_path = _SCRIPT_DIR / "validation_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("Report saved: %s", report_path)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
