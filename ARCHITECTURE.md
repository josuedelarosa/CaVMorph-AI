# Cavfish Inference Desktop App - Architecture

## Overview

A native cross-platform desktop application for automated fish morphometrics using a ViTPose-based deep learning model. Built with:

- **Frontend**: Tauri + HTML/CSS/JavaScript (native window, offline-first)
- **Backend API**: FastAPI + Uvicorn (sidecar process)
- **Inference**: mmpose/mmengine with custom ViTPose head
- **Packaging**: PyInstaller (backend binary) + Tauri bundler (desktop app)

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Tauri Desktop Window                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Frontend UI (TypeScript + React)           │   │
│  │  - File/folder picker                               │   │
│  │  - Batch inference progress                          │   │
│  │  - Keypoint visualization (canvas overlay)           │   │
│  │  - Phenotype table display                           │   │
│  │  - Export buttons (CSV/JSON/PNG)                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                   │
│                  HTTP (127.0.0.1:PORT)                      │
│                           ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │      Tauri Commands & File System Bridge             │   │
│  │  - Sidecar process management                        │   │
│  │  - File dialog integration                           │   │
│  │  - Window controls                                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ stdio/env
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Backend Sidecar Process (Python)                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │          FastAPI Application (port 8008+)            │   │
│  │                                                      │   │
│  │  /health              - Health check endpoint        │   │
│  │  /model/info          - Model metadata (meta.json)  │   │
│  │  /infer/image         - Single image inference       │   │
│  │  /infer/folder        - Batch inference              │   │
│  │  /export/csv          - CSV export                   │   │
│  │  /export/json         - JSON export                  │   │
│  │  /export/annotated    - Annotated image export       │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                   │
│                           ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        Cavfish Inference Engine                      │   │
│  │                                                      │   │
│  │  model_pack.py      - Model file management          │   │
│  │  manager.py         - Model loading/caching          │   │
│  │  infer.py           - Array-based inference (RGB)   │   │
│  │  phenotypes.py      - Phenotype computation          │   │
│  │  draw.py            - Keypoint visualization         │   │
│  │  export.py          - CSV/JSON/PNG export            │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                   │
│                           ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │      MMPose + MMEngine (Vendored Components)        │   │
│  │                                                      │   │
│  │  third_party/mmpose/  - Vendored model registry    │   │
│  │  phenolosses/         - Custom loss functions        │   │
│  │  custom_transforms.py - Custom augmentation          │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                   │
│                           ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │    Model & Weights (Frozen in Models Directory)      │   │
│  │                                                      │   │
│  │  models/cavfish_v1/                                 │   │
│  │  ├── config.py           - Training config          │   │
│  │  ├── config_infer.py     - Inference-only config    │   │
│  │  ├── weights.pth         - ViTPose weights          │   │
│  │  ├── meta.json           - Keypoint & phenotype     │   │
│  │  └── tmp/               - Overlay images (runtime)  │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
              Disk (Image Loading & Export)
```

## Key Design Decisions

### 1. Backend as Sidecar
- Spawned by Tauri on app startup
- Communicates via HTTP (127.0.0.1)
- Dynamic port discovery via env var `FISH_PORT`
- Runs in CPU mode only (`FISH_DEVICE=cpu`)
- Can be replaced in dev with `python -m backend.api.cli`

### 2. No External Python Installation
- Backend binary packaged with PyInstaller
- All dependencies frozen into executable
- Users download ~500MB app, no pip/conda needed
- FISH_DEVICE, FISH_PORT set by Tauri

### 3. Inference-Only Registry
- No training code in production
- Vendored MMPose components only
- Single registry (no upstream collisions)
- Config uses `config_infer.py` (not training config)

### 4. 20 Anatomical Keypoints
- Fixed architecture
- 14 phenotype pairs (distances derived from keypoints)
- Optional normalization by "standard length" (SL)
- All phenotypes computed on client after inference

### 5. User Workflow
1. Drag/drop or select folder of already-cropped fish images
2. Click "Analyze" → batch inference with progress bar
3. Live preview of keypoints on first image
4. View phenotype table (one row per image, one column per pair)
5. Export results (CSV, JSON, annotated PNG)
6. All offline, no network required

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `FISH_DEVICE` | `cpu` | PyTorch device (cpu/cuda) |
| `FISH_PORT` | `8008` | Backend API port |
| `FISH_MODEL_DIR` | `models/cavfish_v1` | Model directory path |

## Build & Packaging

### Development
```bash
cd desktop/src-tauri
cargo tauri dev
```
- Tauri launches dev window
- Python backend spawned via `python -m backend.api.cli`
- Hot-reload for frontend (if using web bundler)

### Production (macOS example)
```bash
# Build backend binary
pyinstaller backend/api/cli.spec

# Build Tauri app
cd desktop/src-tauri
cargo tauri build

# Result: target/release/bundle/macos/FishMorphometrics.app
```

Platform-specific builds:
- **macOS**: Universal (x86_64 + ARM64) via `cargo tauri build`
- **Windows**: MSVC (x86_64 only) via `cargo tauri build`
- **Linux**: GTK (x86_64 only) via `cargo tauri build`

## File Organization

```
cavfish-inference/
├── backend/                         # Python backend
│   ├── api/
│   │   ├── cli.py                   # Entry point (startup script)
│   │   └── app.py                   # FastAPI application
│   ├── cavfish/
│   │   ├── model_pack.py            # Model file discovery
│   │   ├── manager.py               # Model loader
│   │   ├── infer.py                 # Inference pipeline
│   │   ├── phenotypes.py            # Phenotype computation
│   │   ├── draw.py                  # Visualization
│   │   └── export.py                # CSV/JSON/PNG export
│   ├── phenolosses/                 # Custom losses (training refs only)
│   ├── third_party/                 # Vendored MMPose code
│   ├── custom_transforms.py         # Custom augmentation
│   └── requirements.txt              # Python dependencies
│
├── desktop/                         # Tauri frontend
│   ├── src/                         # Frontend code (HTML/CSS/JS/TS/React)
│   │   ├── index.html               # Entry point
│   │   ├── main.tsx                 # React app (if using React)
│   │   ├── components/
│   │   ├── pages/
│   │   └── styles/
│   ├── src-tauri/
│   │   ├── src/
│   │   │   └── main.rs              # Tauri setup
│   │   ├── Cargo.toml               # Rust dependencies
│   │   └── tauri.conf.json          # Tauri config
│   ├── package.json                 # Node dependencies (dev only)
│   ├── vite.config.ts               # Bundler config (optional)
│   └── tsconfig.json                # TypeScript config
│
├── models/                          # Model & config
│   └── cavfish_v1/
│       ├── config.py                # Full training config
│       ├── config_infer.py          # Inference-only config
│       ├── weights.pth              # Model weights
│       └── meta.json                # Runtime metadata
│
├── requirements.lock.txt            # Locked deps (reference)
├── ARCHITECTURE.md                  # This file
├── DEPLOYMENT.md                    # Build & release guide
└── README.md                        # User guide
```

## API Specification

### GET /health
Returns server status and device info.
```json
{
  "ok": true,
  "device": "cpu",
  "model_dir": "/path/to/models/cavfish_v1"
}
```

### GET /model/info
Returns model metadata (from meta.json).
```json
{
  "dataset_name": "fish_20kpt",
  "num_keypoints": 20,
  "keypoint_names": ["kp1", ..., "kp20"],
  "codec_input_size": [192, 256],
  "phenotype_pairs": [[0, 1], [3, 2], ...],
  "phenotype_scale_by_sl": true,
  "phenotype_sl_pair": [0, 3]
}
```

### POST /infer/image
Single image inference.
```json
{
  "image_path": "/path/to/fish.jpg",
  "return_overlay_png": false
}
```

Response:
```json
{
  "image_path": "...",
  "keypoints": [[x1, y1], [x2, y2], ...],  // 20 keypoints
  "keypoint_scores": [s1, s2, ...],        // confidence per keypoint
  "extra_pred_fields": {
    "phenotypes": [
      {
        "id": 0,
        "pair": [0, 1],
        "name": "pair_0_1",
        "value_px": 150.5,
        "value_norm": 0.82
      },
      ...
    ]
  },
  "overlay_path": "/path/to/overlay.png"  // if requested
}
```

### POST /infer/folder
Batch inference.
```json
{
  "folder_path": "/path/to/images",
  "recursive": true,
  "limit": null,
  "return_overlay_png": true
}
```

Response:
```json
{
  "count": 10,
  "predictions": [
    { /* same as /infer/image */ },
    ...
  ]
}
```

### POST /export/csv
Export predictions to CSV.
```json
{
  "output_path": "/path/to/results.csv",
  "predictions": [ /* array of predictions */ ]
}
```

### POST /export/json
Export predictions to JSON.
```json
{
  "output_path": "/path/to/results.json",
  "predictions": [ /* array of predictions */ ]
}
```

### POST /export/annotated-images
Export annotated images.
```json
{
  "output_dir": "/path/to/output",
  "predictions": [ /* array of predictions */ ],
  "suffix": "_annotated"
}
```

## Performance & Limitations

### Single Image Inference
- **Model load time**: ~2-5 seconds (first call, cached after)
- **Inference time**: ~0.5-1 second per image (CPU, ViTPose-base)
- **Peak memory**: ~2GB RAM

### Batch Processing
- No GPU acceleration (CPU only)
- Sequential processing (one image at a time)
- Progress reported to frontend via HTTP polls

### Input Requirements
- **Image format**: JPEG, PNG, BMP, TIFF
- **Pre-processing**: Must be already cropped (full-body fish)
- **Size**: Any resolution; internally resized to 192x256

## Supported Platforms

- **macOS**: 10.14+ (Intel & Apple Silicon)
- **Windows**: 10+ (MSVC)
- **Linux**: Ubuntu 18.04+ (GTK, x86_64)

## Offline Operation

✓ App runs fully offline
✓ No phone-home telemetry
✓ No authentication required
✓ All data stays local

## Future Enhancements

- Multi-GPU batch processing (if CUDA available)
- Real-time preview with adjustable parameters
- Custom phenotype pair definition
- Model swap capability (multiple architectures)
- Landmark naming customization
- Integration with BiAsia database export
