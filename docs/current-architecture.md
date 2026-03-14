# PhenoAI — Current Architecture

## Overview

PhenoAI is a desktop fish morphometrics application that uses deep learning (ViT-based pose estimation) to detect 20 anatomical keypoints on fish images and compute phenotypic measurements from those keypoints.

```
┌─────────────────────────────────────────────────────────┐
│                     Tauri Shell (Rust)                   │
│  - Locates Conda env "cavfish310"                       │
│  - Spawns Python backend process                        │
│  - Manages backend lifecycle                            │
│  - Serves Vue 3 frontend                                │
└──────────────────────┬──────────────────────────────────┘
                       │  HTTP (localhost:PORT)
┌──────────────────────▼──────────────────────────────────┐
│               Python Backend (FastAPI + uvicorn)         │
│  - Loads MMPose model via registry                      │
│  - Runs inference pipeline                              │
│  - Computes phenotypes from keypoints                   │
│  - Exports CSV / JSON / annotated images                │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              MMPose / MMEngine / PyTorch                  │
│  - TopdownPoseEstimator with ViT-Base backbone          │
│  - Custom CavfishHeatmapHead + HeatmapHeadPheno         │
│  - UDPHeatmap codec (192×256 → 48×64)                   │
│  - PoseDataPreprocessor (ImageNet normalization)         │
└─────────────────────────────────────────────────────────┘
```

## Component Map

### Desktop Shell — `desktop/src-tauri/src/main.rs`
- Finds Conda executable across system paths
- Resolves Python from `cavfish310` Conda environment
- Spawns Python backend with inline startup script
- Passes env vars: `FISH_PORT`, `FISH_DEVICE=cpu`, `FISH_MODEL_DIR`
- Polls TCP port until backend is ready (60s timeout)
- First-run setup: installs Miniforge, creates Conda env, installs all dependencies, downloads model weights

### Frontend — `desktop/src/`
- Vue 3 SPA with Vite bundler
- Communicates with backend via `@tauri-apps/api/http` (Tauri HTTP client)
- Endpoints consumed: `/health`, `/model/info`, `/infer/image`, `/infer/folder`, `/export/*`

### Python Backend — `backend/`

#### API Layer (`backend/api/app.py`)
- FastAPI application with CORS enabled
- Loads model at import time via `ModelManager`
- Endpoints: health, model info, single/folder inference, CSV/JSON/image export

#### Model Management (`backend/cavfish/manager.py`)
- Registers all MMPose modules at import time
- Imports custom transforms and loss functions into MMPose registry
- `build_model_from_cfg()`: `Config.fromfile()` → `MODELS.build()` → `load_checkpoint()`

#### Inference (`backend/cavfish/infer.py`)
- `infer_image(model, rgb, cfg_path, device)` — main inference entry point
- Preprocessing:
  1. RGB → BGR conversion
  2. Full-image bounding box: `[0, 0, W, H]`
  3. `GetBBoxCenterScale(padding=1.25)`
  4. `TopdownAffine(input_size=(192,256), use_udp=True)`
  5. `PackPoseInputs`
  6. (inside model) `PoseDataPreprocessor`: normalize with mean=[123.675,116.28,103.53], std=[58.395,57.12,57.375], BGR→RGB
- Postprocessing:
  1. `model.test_step()` returns `PoseDataSample` with decoded keypoints
  2. `serialize_pose_data_sample()` extracts keypoints, scores, bboxes to JSON-safe dict

#### Model Pack (`backend/cavfish/model_pack.py`)
- Validates model directory: `config.py`, `weights.pth`, `meta.json`
- Auto-generates `meta.json` from config if missing

#### Phenotypes (`backend/cavfish/phenotypes.py`)
- Computes pairwise distances (euclidean, x-only, y-only) between keypoints
- Optionally normalizes by Standard Length (keypoint pair [0,1])
- Pure NumPy — no MMPose dependency

#### Drawing (`backend/cavfish/draw.py`)
- Draws keypoint overlay on images
- Pure OpenCV — no MMPose dependency

#### Export (`backend/cavfish/export.py`)
- CSV, JSON, annotated image export
- Pure Python/OpenCV — no MMPose dependency

### Model Configuration — `models/cavfish_v1/`
- `config.py` — MMEngine Python config defining full model architecture
- `weights.pth` — PyTorch checkpoint (~1GB, downloaded on first run)
- `meta.json` — Derived metadata: keypoint names, phenotype pairs, codec settings

### Custom Components (training-coupled, registered in MMPose registry)
- `backend/phenolosses/` — Custom loss functions (training-only, but loaded at runtime for registry)
- `backend/custom_transforms.py` — Training augmentations (not used in inference pipeline)
- `backend/third_party/` — Vendored/modified MMPose heads

## Dependency Chain (Runtime)

```
Runtime binary depends on:
├── Python 3.10 (via Conda env "cavfish310")
├── PyTorch 2.1.0 (CPU-only)
├── mmengine 0.10.5
│   ├── Config, Compose, registry, load_checkpoint
│   └── InstanceData, PixelData
├── mmcv 2.2.0
│   ├── BaseTransform
│   └── build_conv_layer, build_upsample_layer
├── mmpose (CaVFish fork, commit f050def)
│   ├── TopdownPoseEstimator
│   ├── PoseDataSample, PoseDataPreprocessor
│   ├── Registry (MODELS, TRANSFORMS, KEYPOINT_CODECS)
│   ├── All transforms (LoadImage, GetBBoxCenterScale, TopdownAffine, PackPoseInputs)
│   ├── UDPHeatmap codec
│   └── All loss submodules (force-imported for registry)
├── mmpretrain 1.2.0
│   └── VisionTransformer backbone
├── mmdet 3.3.0 (transitive, never imported directly)
├── opencv-python 4.10.0.84
├── numpy 1.26.4 (<2.0 required)
├── fastapi 0.115.6 + uvicorn 0.34.0
├── pydantic 2.10.5
└── scipy, pandas, pillow (declared but not imported in core runtime path)
```

## Key Observations

1. **Entire MMPose ecosystem is a runtime dependency** — the model cannot be loaded without `MODELS.build()`, `Config.fromfile()`, `register_all_modules()`, and the full registry chain.
2. **Custom loss functions and transforms are loaded at runtime** even though they're only needed for training — `manager.py` imports them to satisfy the registry during model construction.
3. **The model is stored as a PyTorch `.pth` checkpoint** — requires the exact class hierarchy to deserialize.
4. **First-run setup installs ~2GB of Conda packages** including the full OpenMMLab stack.
5. **CPU-only inference** — the app is hardcoded to `FISH_DEVICE=cpu`.
6. **No ONNX export exists** — the model has never been exported from the PyTorch/MMPose format.
7. **Preprocessing is performed via MMPose transforms** (Compose pipeline) which require the full registry to instantiate.
8. **Postprocessing (phenotype computation, drawing, export) is already decoupled** — these modules use only NumPy/OpenCV and could be reused as-is.
