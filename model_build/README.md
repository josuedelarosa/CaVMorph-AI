# Model Build

This directory contains scripts for exporting the PhenoAI model from MMPose/PyTorch format to ONNX.

**This directory is for developers only. It is NOT part of the shipped desktop application.**

## Prerequisites

You need the full MMPose/Conda environment to run these scripts:

```bash
# Activate the development environment
conda activate cavfish310

# Or install the build requirements
pip install -r requirements.txt
```

## Export Model

```bash
python model_build/export_model.py \
  --model-dir models/cavfish_v1 \
  --output-dir model_build/output \
  --copy-to-model-dir
```

This will:
1. Load the MMPose model from `models/cavfish_v1/config.py` + `weights.pth`
2. Export the backbone + head to ONNX format
3. Generate `model_metadata.json` with all preprocessing/postprocessing parameters
4. Optionally copy `model.onnx` + `model_metadata.json` to the model directory

### Output Files

| File | Description |
|------|-------------|
| `model.onnx` | ONNX model (backbone + head, ~400MB) |
| `model_metadata.json` | Input shape, normalization params, keypoint schema, phenotype config |

## Validate Export

```bash
python model_build/validate_export.py \
  --model-dir models/cavfish_v1 \
  --test-image path/to/fish.jpg \
  --tolerance 1.0
```

Compares MMPose and ONNX outputs keypoint-by-keypoint. Reports:
- Per-keypoint pixel distance
- Max/mean deviation
- Pass/fail at the specified tolerance

## Model Metadata

The `model_metadata.json` file documents everything the runtime needs:

```json
{
  "codec_input_size": [192, 256],      // (W, H) input to the model
  "heatmap_size": [48, 64],            // (W, H) output heatmap
  "normalization_mean": [123.675, 116.28, 103.53],
  "normalization_std": [58.395, 57.12, 57.375],
  "padding": 1.25,                      // bbox padding factor
  "phenotype_pairs": [[0,1], [2,3], ...],
  "phenotype_names": ["BI", "Bd", ...],
  ...
}
```
