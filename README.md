# PhenoAI

Automated morphometric analysis of fish photographs. Detects 20 anatomical landmarks, computes 14 phenotype measurements, and exports results as CSV, JSON, or annotated images.

Runs entirely offline. No data is transmitted.

---

## Requirements

- macOS 12+, Windows 10+, or Ubuntu 20.04+
- 8 GB RAM (16 GB recommended for large batches)
- ~500 MB disk space

---

## Installation

Download the latest release for your platform from [Releases](../../releases):

- **macOS**: `PhenoAI_x.x.x_aarch64.dmg`
- **Windows**: `PhenoAI_x.x.x_x64-setup.exe`

Python and the model weights are bundled. No additional dependencies are required.

---

## Usage

1. Click **Select Folder** and choose a directory of fish photos (JPG, PNG, TIFF).
2. Click **Analyze**. Results appear as each image is processed.
3. Select any result to review the keypoint overlay and phenotype measurements.
4. Export via **CSV**, **JSON**, or **Annotated Images**.

Keypoints are color-coded by detection confidence: red below 50%, orange 50-75%, green above 75%. Low-confidence points should be reviewed manually.

---

## Web Deployment

A Docker-based interface is available for server or shared-lab deployment:

```sh
docker compose up -d
```

The app is accessible at `http://your-server/phenoai-web/`. See [docker-compose.yml](docker-compose.yml) for port and path configuration.

---

## Building from Source

Prerequisites: Node.js 18+, Rust 1.70+, Python 3.10+.

```sh
git clone https://github.com/your-org/cavfish-inference.git
cd cavfish-inference/desktop
npm install
npm run tauri build
```

For the web build only:

```sh
npm run build:web
```

Output lands in `desktop/dist-web/`.

---

## Model

The default model (`models/cavfish_v1/model.onnx`) was trained on lateral-view cavefish photographs and runs via ONNX Runtime on CPU. Keypoint names, phenotype pairs, and scale reference can be customized in `models/cavfish_v1/meta.json`.

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).

Files under `backend/third_party/mmpose/` and `backend/third_party/base_head.py` are derived from [MMPose](https://github.com/open-mmlab/mmpose) (Copyright OpenMMLab, Apache License 2.0) and retain their original license headers.
