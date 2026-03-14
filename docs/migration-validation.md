# Migration Validation Guide

This document describes how to validate that the ONNX Runtime inference path
produces numerically identical (or within-tolerance) results compared to the
legacy MMPose/PyTorch path.

## What Is Numerically Identical

| Component | Status | Notes |
|-----------|--------|-------|
| Preprocessing (affine warp) | **Identical** | Same UDP warp matrix formula, same OpenCV `warpAffine` with `INTER_LINEAR` + `BORDER_CONSTANT` |
| Normalization | **Identical** | Same mean/std values, same BGR→RGB conversion |
| Postprocessing (heatmap argmax) | **Identical** | Same integer peak detection |
| UDPHeatmap sub-pixel refinement | **Should match** | Re-implemented Taylor expansion with Hessian; may differ by < 0.1 px at boundary conditions |
| Keypoint inverse transform | **Identical** | Same inverse affine applied via `get_warp_matrix_udp` → `cv2.invertAffineTransform` |
| Phenotype computation | **Identical** | Same distance formulas (euclidean, x, y), same SL normalization logic |

## What May Differ Within Tolerance

### ONNX Runtime vs. PyTorch Model Output

The ONNX export via `torch.onnx.export()` is expected to produce **bitwise-identical** heatmaps
for the same input tensor on the same hardware with `opset_version=17`. However:

- **Float32 rounding**: CPU inference may diverge by ±1e-6 across different ONNX Runtime versions.
- **Graph optimizations**: ONNX Runtime applies graph-level optimizations that may reorder floating-point ops, causing ±1e-5 absolute differences in heatmap values.
- **Sub-pixel refinement sensitivity**: Because the Taylor expansion uses 2nd-order derivatives (Hessian), tiny changes in the heatmap values (from float rounding) can shift the sub-pixel offset by ≤0.1 px.

**Expected tolerance**: < 0.5 pixel per keypoint in original image coordinates.

### Cross-Platform Differences

| Scenario | Expected |
|----------|----------|
| Same OS, same ONNX Runtime version | Bitwise identical |
| Same OS, different ONNX Runtime minor version | < 1e-5 heatmap diff → < 0.1 px |
| Cross-OS (macOS ↔ Windows ↔ Linux) | < 1e-4 heatmap diff → < 0.5 px |

## Validation Commands

### 1. Export the ONNX Model (One-Time, Requires Conda)

```bash
conda activate cavfish310
cd model_build
python export_model.py \
    --config ../models/cavfish_v1/config.py \
    --weights ../models/cavfish_v1/weights.pth \
    --output ../models/cavfish_v1/model.onnx
```

### 2. Run Parity Validation

```bash
conda activate cavfish310
python model_build/validate_export.py \
    --config models/cavfish_v1/config.py \
    --weights models/cavfish_v1/weights.pth \
    --onnx models/cavfish_v1/model.onnx \
    --test-images test_images/ \
    --tolerance 1.0
```

This script:
1. Runs MMPose inference on each test image
2. Runs ONNX Runtime inference on the same images
3. Compares per-keypoint pixel distances
4. Reports PASS/FAIL per image and overall

### 3. Run Unit Tests

```bash
# No Conda required
pip install pytest numpy opencv-python
cd tests
pytest test_preprocessing.py test_postprocessing.py test_inference.py -v
```

### 4. Run Runtime Server Smoke Tests

```bash
pip install pytest fastapi httpx numpy opencv-python
pytest tests/test_runtime_server.py -v
```

## Known Discrepancies

### 1. Heatmap Boundary Conditions

When a keypoint's Gaussian peak falls exactly on the heatmap border (row 0, column 0,
last row, or last column), the sub-pixel refinement clamps differently than MMPose.
The Taylor expansion guard in our implementation skips refinement for edge pixels
(same as MMPose), but the exact clamping logic may differ by ≤0.25 px.

**Impact**: Negligible. Fish keypoints are interior to the image in practice.

### 2. Phenotype SL Normalization Edge Case

If SL (standard length, keypoints 0→1) is < 1e-6 pixels, the legacy code may produce
`inf` or `nan` while the new code produces `None` for normalized values.

**Impact**: Only occurs with degenerate inputs (collapsed fish).

### 3. BGR/RGB Ordering

The legacy pipeline reads images as BGR (OpenCV default) and converts to RGB via
`PoseDataPreprocessor(bgr_to_rgb=True)`. The new pipeline reads as BGR and converts
to RGB in `preprocess_image()`. The ordering is guaranteed identical because both
use the same `image[:, :, ::-1]` flip.

## Rollback Strategy

If ONNX results are found to be unacceptable:

1. Set environment variable: `PHENOAI_USE_LEGACY=1`
2. The `create_engine()` factory will instantiate `FallbackPyTorchEngine`
3. The Tauri shell will detect Conda and spawn the legacy `backend/api/app.py` server

No code changes are required for rollback — just the environment variable.

## Acceptance Criteria

The ONNX runtime is validated when:

- [ ] All 20 keypoints are within **1.0 pixel** of the MMPose predictions on ≥10 test images
- [ ] All phenotype distances are within **0.5 pixel** of the MMPose-computed values
- [ ] SL-normalized phenotypes are within **0.005** of the MMPose values
- [ ] The runtime server passes all endpoint smoke tests
- [ ] Cross-platform builds (macOS, Windows) produce the same keypoints to within 0.5 px
