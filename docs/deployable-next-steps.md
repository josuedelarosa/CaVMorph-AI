# Deployable Next Steps (Ordered)

This is the execution order to move PhenoAI from validated parity to a shippable desktop build.

## 1. Lock Model Artifacts (Release Input)

1. Export ONNX from the approved weights:
```bash
conda activate cavfish310
python model_build/export_model.py --model-dir models/cavfish_v1 --output-dir model_build/output --copy-to-model-dir
```
2. Verify artifacts exist:
- `models/cavfish_v1/model.onnx`
- `models/cavfish_v1/model_metadata.json`
3. Record model hash for release notes:
```bash
python - <<'PY'
import hashlib, pathlib
p = pathlib.Path('models/cavfish_v1/model.onnx')
print(hashlib.sha256(p.read_bytes()).hexdigest())
PY
```

## 2. Numerical Validation Gate

1. Run export parity against representative images:
```bash
conda activate cavfish310
python model_build/validate_export.py --model-dir models/cavfish_v1 --test-image path/to/fish.jpg --tolerance 1.0
```
2. Confirm pass criteria:
- per-keypoint max error <= 1.0 px
- no systematic bias on specific keypoints

## 3. Runtime Test Gate (No Conda)

1. Install thin runtime deps:
```bash
python -m pip install -r inference_runtime/requirements.txt
python -m pip install pytest
```
2. Run runtime tests:
```bash
python -m pytest tests/test_preprocessing.py tests/test_postprocessing.py tests/test_inference.py -v
python -m pytest tests/test_runtime_server.py -v
```
3. Run backend smoke manually:
```bash
python -m inference_runtime.runtime_server
```
Then check:
- `GET /health`
- `GET /model/info`
- `POST /infer/image`

## 4. Tauri Integration Gate

1. Validate ONNX path is selected first (without legacy env):
```bash
cd desktop
npm install
npm run tauri dev
```
2. Confirm app boot behavior:
- backend starts without Conda
- inference works from UI image flow
- CSV/JSON export endpoints function

## 5. Packaging Gate

1. Build desktop artifacts:
```bash
cd desktop
npm run tauri build
```
2. Validate packaged app on clean machine:
- no Conda present
- no MMPose installed
- app still runs inference end-to-end

## 6. Release Readiness Gate

Ship only when all are true:
- ONNX parity checks pass
- all tests pass
- packaged app works on target OS without Conda
- rollback env var documented: `PHENOAI_USE_LEGACY=1`
- model hash and build version recorded in release notes

## 7. Optional Hardening (Recommended)

1. Bundle a dedicated runtime venv in app resources for deterministic installs.
2. Pin `onnxruntime` and `opencv-python` versions in release branch.
3. Add CI job for `tests/test_preprocessing.py -k parity` using cavfish310 image.
