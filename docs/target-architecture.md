# PhenoAI — Target Architecture

## Architecture Comparison

### Current State
```
Tauri → spawns Python (Conda cavfish310) → FastAPI → MMPose full stack → inference
```
- **Runtime size**: ~2GB Conda env + ~1GB model weights
- **Startup**: 15-30s (Python + MMPose registry initialization)
- **Dependencies**: PyTorch, mmengine, mmcv, mmpose (CaVFish fork), mmpretrain, mmdet
- **Portability**: Requires Conda on target machine

### Target State
```
Tauri → spawns lightweight Python sidecar → FastAPI → ONNX Runtime → inference
```
- **Runtime size**: ~200MB ONNX Runtime + ~400MB ONNX model + ~50MB Python packages
- **Startup**: 2-5s
- **Dependencies**: onnxruntime, numpy, opencv-python, fastapi, uvicorn
- **Portability**: pip-installable, no Conda required

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                      DEVELOPMENT / BUILD SIDE                     │
│                     (NOT shipped with desktop app)                │
│                                                                   │
│  model_build/                                                     │
│  ├── export_model.py      — MMPose → ONNX export                │
│  ├── validate_export.py   — Parity check: MMPose vs ONNX        │
│  ├── model_metadata.json  — Authoritative model metadata         │
│  └── README.md            — Export instructions                   │
│                                                                   │
│  Requires: Conda, MMPose, PyTorch, mmpretrain, mmengine, etc.   │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    PRODUCTION RUNTIME SIDE                         │
│                  (shipped with desktop app)                        │
│                                                                   │
│  inference_runtime/                                               │
│  ├── __init__.py                                                  │
│  ├── types.py             — Data types (InferenceRequest/Result) │
│  ├── preprocessing.py     — Image → tensor (pure NumPy/OpenCV)  │
│  ├── inference.py         — ONNX Runtime session management     │
│  ├── postprocessing.py    — Heatmap → keypoints (UDPHeatmap)    │
│  ├── runtime_server.py    — FastAPI server (thin replacement)    │
│  └── requirements.txt     — Minimal runtime deps                 │
│                                                                   │
│  Requires ONLY: onnxruntime, numpy, opencv-python, fastapi,     │
│                 uvicorn, pydantic                                 │
│                                                                   │
│  Artifacts: model.onnx + model_metadata.json                     │
└──────────────────────────────┬───────────────────────────────────┘
                               │ HTTP (localhost:PORT)
┌──────────────────────────────▼───────────────────────────────────┐
│  desktop/src-tauri/                                               │
│  ├── main.rs              — Spawns inference runtime process     │
│  │                          No Conda lookup required              │
│  │                          Uses bundled/pip-installed Python     │
│  └── tauri.conf.json      — Updated sidecar config               │
│                                                                   │
│  desktop/src/              — Vue 3 frontend (UNCHANGED)           │
│  └── utils/api.ts         — Same HTTP API contract                │
└──────────────────────────────────────────────────────────────────┘
```

## Runtime Boundary

### What runs at runtime (shipped):
| Component | Purpose | Dependencies |
|-----------|---------|-------------|
| `inference_runtime/` | Preprocessing, ONNX inference, postprocessing | onnxruntime, numpy, opencv-python |
| `inference_runtime/runtime_server.py` | HTTP API | fastapi, uvicorn, pydantic |
| `backend/cavfish/phenotypes.py` | Phenotype computation | numpy |
| `backend/cavfish/draw.py` | Keypoint overlay | opencv-python |
| `backend/cavfish/export.py` | CSV/JSON/image export | opencv-python, numpy |
| `backend/cavfish/io.py` | Image file discovery | stdlib |
| `model.onnx` | Exported model artifact | — |
| `model_metadata.json` | Model configuration | — |

### What does NOT run at runtime (build-only):
| Component | Purpose |
|-----------|---------|
| `model_build/` | Model export and validation scripts |
| `backend/cavfish/manager.py` | MMPose model construction (DEPRECATED at runtime) |
| `backend/cavfish/infer.py` | MMPose inference pipeline (DEPRECATED at runtime) |
| `backend/phenolosses/` | Custom loss functions |
| `backend/custom_transforms.py` | Training augmentations |
| `backend/third_party/` | Vendored MMPose heads |
| `models/cavfish_v1/config.py` | MMEngine config |
| `models/cavfish_v1/weights.pth` | PyTorch checkpoint |

## Model Build Boundary

The `model_build/` directory is a developer-only tool:

```
model_build/
├── export_model.py         — Loads MMPose model, exports to ONNX
├── validate_export.py      — Compares MMPose vs ONNX outputs
├── model_metadata.json     — Generated metadata (input shape, normalization, keypoints)
├── requirements.txt        — Full MMPose/PyTorch deps for export environment
└── README.md               — How to run export
```

**Export flow:**
1. Load model using `backend/cavfish/manager.py` (requires MMPose env)
2. Create dummy input tensor (1, 3, 256, 192)
3. `torch.onnx.export()` with dynamic batch size
4. Validate ONNX model using `onnxruntime`
5. Generate `model_metadata.json` with all preprocessing/postprocessing parameters
6. Run parity test comparing MMPose and ONNX outputs on sample images

## Tauri Integration Boundary

### IPC Contract (preserved from current system)

The HTTP API contract between frontend and backend is **unchanged**:

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `/health` | GET | — | `{ok, device, model_dir}` |
| `/model/info` | GET | — | Model metadata JSON |
| `/infer/image` | POST | `{image_path, return_overlay_png}` | Prediction dict |
| `/infer/folder` | POST | `{folder_path, recursive, limit, return_overlay_png}` | `{count, predictions}` |
| `/export/csv` | POST | `{output_path, predictions}` | `{ok, output_path}` |
| `/export/json` | POST | `{output_path, predictions}` | `{ok, output_path}` |
| `/export/annotated-images` | POST | `{output_dir, predictions, suffix}` | `{ok, output_dir}` |

### Backend Spawn Changes

**Current:** Tauri looks for Conda → finds `cavfish310` env → spawns Python with MMPose
**Target:** Tauri looks for bundled Python (or system pip env) → spawns `inference_runtime/runtime_server.py`

## Packaging Strategy

### Development Mode
```
# Install model_build deps (only for export/validation)
cd model_build && pip install -r requirements.txt

# Install runtime deps (for running the app)
cd inference_runtime && pip install -r requirements.txt

# Run Tauri dev
cd desktop && npm run tauri dev
```

### Production Build
```
# 1. Export model (one-time, developer machine)
cd model_build && python export_model.py

# 2. Bundle artifacts
cp model_build/output/model.onnx  desktop/src-tauri/resources/
cp model_build/model_metadata.json desktop/src-tauri/resources/

# 3. Bundle runtime
# Option A: PyInstaller/Nuitka binary (no Python needed on target)
# Option B: Embedded Python with pip packages (smaller, simpler)

# 4. Build Tauri
cd desktop && npm run tauri build
```

### Model Artifact Location Strategy
1. **Bundled**: `<app>/resources/model.onnx` + `model_metadata.json`
2. **App data**: `<app_data>/PhenoAI/models/model.onnx` (downloaded or copied from bundle)
3. **Environment override**: `PHENOAI_MODEL_DIR` env var

## Migration Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| ONNX export fails for custom heads | Blocks ONNX path | Fallback: trace with `torch.jit.trace`, or keep PyTorch-only thin runtime |
| Numerical drift between PyTorch and ONNX | Output differences | Validate with tolerance tests (±0.5 pixel keypoints) |
| UDPHeatmap postprocessing mismatch | Incorrect keypoints | Re-implement codec in pure NumPy, validate against MMPose reference |
| Custom ViT backbone export issue | May need mmpretrain at export | Temporarily import mmpretrain during export only |
| Dynamic input shapes | ONNX may require fixed batch | Export with opset 17, dynamic_axes for batch dim |

## Rollback Strategy

1. **Legacy backend preserved**: All files in `backend/` remain functional. The `backend/api/app.py` still works with MMPose if Conda env is available.
2. **Tauri runtime selection**: The Rust code can detect which backend is available:
   - If `inference_runtime/` + `model.onnx` exist → use thin runtime
   - Else if Conda env exists → fall back to legacy MMPose backend
3. **Environment variable override**: `PHENOAI_USE_LEGACY=1` forces the old MMPose path.
4. **Both paths are tested**: Parity tests ensure identical outputs within tolerance.

## Migration Phases

```
Phase 3: Decouple       — Isolate MMPose code, make preprocessing explicit
Phase 4: Export          — Create ONNX export pipeline
Phase 5: Thin runtime   — Build ONNX-based inference server
Phase 6: Tauri update   — Point Tauri at thin runtime
Phase 7: Packaging       — Remove Conda from build/deploy path
Phase 8: Testing         — Validate parity between old and new paths
```
