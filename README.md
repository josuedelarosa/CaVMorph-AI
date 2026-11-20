# CaVMorph-A

Automated morphometric analysis of fish photographs. Detects 20 anatomical landmarks, computes 14 phenotype measurements, and exports results as CSV, JSON, or annotated images.

Runs entirely offline. No data leaves your machine.

---

## Installation

Pre-built installers are available on the [Releases](https://github.com/josuedelarosa/CaVMorph-AI/releases/tag/v1.0.0) page (v1.0.0):

| Platform | File |
|----------|------|
| macOS (Apple Silicon) | `CaVMorph-AI_macos_aarch64.dmg` |
| Windows | `CaVMorph-AI_windows_x64.exe` |
| Linux | `CaVMorph-AI_linux_x64.deb` |

Python and the model weights are bundled. No additional dependencies are required.

---

## Web Access

A hosted version is available at [https://bivl2ab.uis.edu.co/cavmorph-ai-web/](https://bivl2ab.uis.edu.co/cavmorph-ai-web/).

---

## Usage

1. Click **Select Folder** and choose a directory of fish photos (JPG, PNG, TIFF).
2. Click **Analyze**. Results appear as each image is processed.
3. Select any result to review the keypoint overlay and phenotype measurements.
4. Export via **CSV**, **JSON**, or **Annotated Images**.

---

## Requirements

- macOS 12+, Windows 10+, or Ubuntu 20.04+
- 8 GB RAM (16 GB recommended for large batches)
- ~550 MB disk space

---

## Model

The model was trained on the CaVFish database. Keypoint names, phenotype pairs, and scale reference can be customized in `models/cavfish_v1/meta.json`.

If you use CaVMorph-AI in your research, please cite:

> Poveda-Cuellar, J.L.; Rodríguez-de la Rosa, J.; Martínez-Carrillo, F.; García-Melo, J.E.; García-Melo, L.J.; Marchant, S. & Reu, B. Morphological trait database for Neotropical freshwater fishes powered from artificial intelligence.

---

## Building from Source

Prerequisites: Node.js 18+, Rust 1.70+, Python 3.10+.

```sh
git clone https://github.com/josuedelarosa/CaVMorph-AI.git
cd CaVMorph-AI/desktop
npm install
npm run tauri build
```

For the web build only:

```sh
npm run build:web
```

Output lands in `desktop/dist-web/`.

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).

Files under `backend/third_party/mmpose/` and `backend/third_party/base_head.py` are derived from [MMPose](https://github.com/open-mmlab/mmpose) (Copyright OpenMMLab, Apache License 2.0) and retain their original license headers.
