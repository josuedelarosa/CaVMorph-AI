# PhenoAI — Tauri Runtime Integration

## Overview

The Tauri desktop shell communicates with the inference backend via HTTP over localhost. This document describes the IPC contract and the two supported runtime paths.

## Runtime Selection

On startup, the Tauri shell auto-selects the best available runtime:

```
1. Check: does model.onnx + model_metadata.json + inference_runtime/ exist?
   → YES: Use thin ONNX runtime (spawn_backend_onnx)
   → NO: Fall through

2. Check: does cavfish310 Conda env exist with MMPose installed?
   → YES: Use legacy MMPose runtime (spawn_backend legacy path)
   → NO: Show setup screen
```

### Environment Variable Overrides

| Variable | Effect |
|----------|--------|
| `PHENOAI_USE_LEGACY=1` | Force legacy MMPose backend even if ONNX is available |
| `PHENOAI_PYTHON=/path/to/python` | Override Python executable for thin runtime |
| `FISH_MODEL_DIR=/path/to/models` | Override model directory |
| `FISH_DEVICE=cpu` | Device selection (default: cpu) |

## HTTP API Contract

The frontend communicates with whichever backend is running via the same HTTP API. The contract is identical between ONNX and legacy backends.

### Endpoints

#### `GET /health`
```json
// Response
{
  "ok": true,
  "device": "cpu",
  "model_dir": "/path/to/models/cavfish_v1"
}
```

#### `GET /model/info`
```json
// Response
{
  "dataset_name": "Cavfish Morphometrics v1",
  "num_keypoints": 20,
  "keypoint_names": ["Upper Snout Tip", ...],
  "codec_input_size": [192, 256],
  "phenotype_pairs": [[0,1], [2,3], ...],
  "phenotype_names": ["BI", "Bd", ...],
  "phenotype_types": ["x", "y", ...],
  ...
}
```

#### `POST /infer/image`
```json
// Request
{
  "image_path": "/absolute/path/to/image.jpg",
  "return_overlay_png": true
}

// Response
{
  "image_path": "/absolute/path/to/image.jpg",
  "keypoints": [[[x1,y1], [x2,y2], ...]],
  "keypoint_scores": [[0.95, 0.87, ...]],
  "bboxes": [[0, 0, 640, 480]],
  "bbox_scores": [1.0],
  "extra_pred_fields": {
    "phenotypes": [
      {"id": 0, "pair": [0,1], "name": "BI", "type": "x", "value_px": 123.4, "value_norm": 1.0},
      ...
    ]
  },
  "overlay_png_base64": "base64encodedstring...",
  "overlay_path": "/path/to/overlay.jpg"
}
```

#### `POST /infer/folder`
```json
// Request
{
  "folder_path": "/path/to/images",
  "recursive": true,
  "limit": null,
  "return_overlay_png": true,
  "profile_id": "optional-id",
  "profile_name": "optional-name"
}

// Response
{
  "count": 5,
  "predictions": [
    { /* same as /infer/image response */ },
    ...
  ]
}
```

#### `POST /export/csv`
```json
// Request
{"output_path": "/path/to/output.csv", "predictions": [...]}
// Response
{"ok": true, "output_path": "/path/to/output.csv"}
```

#### `POST /export/json`
```json
// Request
{"output_path": "/path/to/output.json", "predictions": [...]}
// Response
{"ok": true, "output_path": "/path/to/output.json"}
```

#### `POST /export/annotated-images`
```json
// Request
{"output_dir": "/path/to/output", "predictions": [...], "suffix": "_annotated"}
// Response
{"ok": true, "output_dir": "/path/to/output"}
```

## Error Handling

### Missing Model Artifact
If `model.onnx` or `model_metadata.json` are missing:
- ONNX path falls back to legacy MMPose path
- If neither is available, the setup screen is shown

### Corrupted Runtime
If the backend process crashes on startup:
- Tauri captures stderr output
- Error message shown to user with details
- Log file written to `<app_data>/logs/backend.log`

### Invalid Input Image
If an image cannot be read:
- `/infer/image`: Returns HTTP 400 with detail message
- `/infer/folder`: Skips the bad image and continues

## Tauri Commands (Rust → Frontend)

| Command | Purpose |
|---------|---------|
| `get_backend_url` | Returns the `http://127.0.0.1:PORT` URL |
| `check_setup_needed` | Returns `true` if no runtime is available |
| `check_conda_installed` | Returns conda path or error (legacy) |
| `check_conda_env_exists` | Whether cavfish310 env exists (legacy) |
| `run_first_time_setup` | Triggers full Conda setup (legacy) |
| `finish_setup_and_start` | Starts backend and returns URL |
| `get_app_data_path` | Returns app data directory path |

## Process Lifecycle

```
App Start
  ├── is_setup_complete()?
  │   ├── ONNX runtime available? → spawn_backend_onnx(port)
  │   └── Conda env available? → spawn_backend(port) [legacy]
  │
  ├── Setup needed → Show SetupView.vue
  │   └── User completes setup → finish_setup_and_start
  │
  └── Backend running → Frontend loads
      └── Window close → child.kill()
```
