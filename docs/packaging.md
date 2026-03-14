# PhenoAI — Packaging & Deployment Guide

## Directory Layout (Production)

```
PhenoAI.app (or .exe/.AppImage)
├── inference_runtime/
│   ├── __init__.py
│   ├── types.py
│   ├── preprocessing.py
│   ├── postprocessing.py
│   ├── inference.py
│   ├── runtime_server.py
│   └── requirements.txt
├── backend/cavfish/
│   ├── draw.py           ← reused for overlay drawing
│   ├── export.py          ← reused for CSV/JSON export
│   ├── phenotypes.py      ← reused for phenotype computation
│   └── io.py              ← reused for image discovery
├── models/cavfish_v1/
│   ├── model.onnx         ← exported ONNX model
│   ├── model_metadata.json ← model configuration
│   └── meta.json          ← legacy metadata (optional)
└── src-tauri/             ← compiled Tauri binary
```

## 1. Development Mode

### Setup
```bash
# Clone the repository
git clone <repo-url>
cd cavfish-inference

# Install runtime dependencies (no Conda needed!)
pip install -r inference_runtime/requirements.txt

# Export the model (requires Conda env with MMPose — one-time operation)
conda activate cavfish310
python model_build/export_model.py --copy-to-model-dir

# Install frontend dependencies
cd desktop
npm install
```

### Running
```bash
# Start the Tauri dev server
cd desktop
npm run tauri dev

# Or run the inference runtime standalone
python -m inference_runtime.runtime_server
```

### Environment Variables (Development)
| Variable | Default | Description |
|----------|---------|-------------|
| `FISH_MODEL_DIR` | `models/cavfish_v1` | Model directory |
| `FISH_PORT` | `8008` | Backend server port |
| `FISH_DEVICE` | `cpu` | Inference device |
| `PHENOAI_USE_LEGACY` | `0` | Set to `1` to force legacy MMPose backend |

## 2. Build Mode

### Export Model (one-time, developer machine)
```bash
conda activate cavfish310
python model_build/export_model.py \
  --model-dir models/cavfish_v1 \
  --output-dir model_build/output \
  --copy-to-model-dir

# Validate the export
python model_build/validate_export.py \
  --model-dir models/cavfish_v1 \
  --test-image path/to/fish.jpg
```

### Build Desktop App
```bash
cd desktop
npm install
npm run tauri build
```

## 3. Packaged Desktop Runtime

### What gets bundled
The Tauri build bundles:
- Compiled Rust binary (Tauri shell)
- Vue 3 frontend (built by Vite)
- `inference_runtime/` directory (Python source)
- `backend/cavfish/` (draw, export, phenotypes, io modules)
- `models/cavfish_v1/model.onnx` + `model_metadata.json`

### Python on the target machine
Two options:

**Option A: Bundled pip venv (recommended)**
```bash
# During build: create a minimal venv
python -m venv desktop/src-tauri/resources/venv
./desktop/src-tauri/resources/venv/Scripts/pip install -r inference_runtime/requirements.txt
```
The Tauri app uses this bundled venv.

**Option B: System Python**
If the user has Python 3.10+ with `pip`, Tauri can auto-install requirements on first run.

## 4. Model Artifact Location Strategy

Priority order (checked by Tauri at startup):

| Priority | Location | Use case |
|----------|----------|----------|
| 1 | `$FISH_MODEL_DIR` env var | Developer override |
| 2 | `<app_data>/PhenoAI/models/cavfish_v1/` | Downloaded/installed models |
| 3 | `<app_bundle>/resources/models/cavfish_v1/` | Bundled with app |
| 4 | `<repo>/models/cavfish_v1/` | Development fallback |

Required files:
- `model.onnx` — ONNX model (~400MB)
- `model_metadata.json` — Model configuration

## 5. Cross-Platform Assumptions

| Platform | App Data Dir | Cache Dir |
|----------|-------------|-----------|
| macOS | `~/.phenoai/` | `~/Library/Caches/PhenoAI/` |
| Windows | `%APPDATA%/PhenoAI/` | `%LOCALAPPDATA%/PhenoAI/` |
| Linux | `~/.local/share/phenoai/` | `~/.cache/phenoai/` |

### Platform-specific notes
- **macOS**: No more Miniforge download or AMFI issues with thin runtime
- **Windows**: `CREATE_NO_WINDOW` flag applied to backend process
- **All**: Model weights are downloaded or bundled, never compiled

## 6. Environment Variable Reference

### Runtime
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FISH_MODEL_DIR` | No | Auto-detected | Model directory |
| `FISH_PORT` | No | Random free port | Backend port |
| `FISH_DEVICE` | No | `cpu` | Inference device |
| `PHENOAI_USE_LEGACY` | No | `0` | Force legacy backend |
| `PHENOAI_PYTHON` | No | Auto-detected | Python for thin runtime |

### Build-time only
| Variable | Description |
|----------|-------------|
| `FISH_BACKEND_DIR` | Override backend source directory |

## 7. Developer-Only Dependencies

These are NOT needed for the shipped desktop app:

| Package | Purpose | When needed |
|---------|---------|-------------|
| Conda / Miniforge | MMPose environment | Model export only |
| PyTorch | Model loading | Model export only |
| mmengine, mmcv | Config/registry | Model export only |
| mmpose (CaVFish) | Model architecture | Model export only |
| mmpretrain | ViT backbone | Model export only |
| mmdet | Transitive dep | Never (can be omitted) |
| xtcocotools | Evaluation | Training only |

## Runtime Dependency Summary

### ONNX Runtime Path (target)
```
onnxruntime    ~200MB
numpy          ~30MB
opencv-python  ~50MB
fastapi        ~1MB
uvicorn        ~1MB
pydantic       ~5MB
─────────────────────
Total:         ~290MB (vs ~2GB for Conda path)
```

### Legacy Path (deprecated)
```
Full Conda env: ~2GB
Model weights:  ~1GB
─────────────────────
Total:          ~3GB
```
