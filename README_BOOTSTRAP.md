# 🐟 Fish Morphometrics - Self-Bootstrapping Desktop App

> **A portable, offline-capable desktop application for automated fish phenotyping using deep learning.**

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/your-org/cavfish-inference)
[![Python](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What is This?

A production-ready desktop application that uses ViTPose-based deep learning models to automatically detect anatomical keypoints on fish images and calculate biologically meaningful phenotypic measurements.

**Key Features:**
- ✅ **Fully Offline** - No cloud, no internet required after setup
- ✅ **Self-Bootstrapping** - Creates its own Python environment
- ✅ **Zero Config** - Just install and run
- ✅ **Cross-Platform** - macOS, Linux, Windows
- ✅ **Batch Processing** - Analyze hundreds of images
- ✅ **Multiple Profiles** - Support for different fish species
- ✅ **Export Ready** - CSV, JSON, annotated images

## Quick Start

### For Users

1. **Download** the installer for your platform
2. **Install** the app
3. **Launch** - First time takes 3-7 minutes (one-time setup)
4. **Drag & Drop** your fish images
5. **Analyze** and export results

### For Developers

```bash
# Clone and build
git clone https://github.com/your-org/cavfish-inference.git
cd cavfish-inference
./build_self_bootstrap.sh

# Install is in desktop/src-tauri/target/release/bundle/
```

## Architecture

### The Problem with Traditional Packaging

**Old Way (PyInstaller)**:
- 🔴 App size: 2-3 GB
- 🔴 Build time: Hours
- 🔴 Updates: Full redownload
- 🔴 Debugging: Nearly impossible
- 🔴 Platform issues: Frequent

**New Way (Self-Bootstrap)**:
- 🟢 App size: 50 MB
- 🟢 Build time: Minutes
- 🟢 Updates: Backend only
- 🟢 Debugging: Full Python stack
- 🟢 Platform issues: None

### How It Works

```
┌──────────────────────────┐
│   Tauri Desktop (50MB)   │
│   - Native UI            │
│   - Bootstrap Script     │
│   - Backend Source       │
└────────┬─────────────────┘
         │
         │ First Launch
         ↓
┌─────────────────────────────────┐
│  App Data Directory              │
│  ~/Library/.../FishMorph/        │
│  ├─ venv/          (Python env)  │
│  ├─ backend/       (Installed)   │
│  ├─ models/        (Weights)     │
│  └─ logs/          (Debugging)   │
└─────────────────────────────────┘
         │
         │ Every Launch
         ↓
┌─────────────────────────────────┐
│  Backend Server                  │
│  venv/bin/python -m cavfish_backend │
│  serve --port 8008               │
└─────────────────────────────────┘
```

## Documentation

### Getting Started
- 📖 [Quick Start Guide](QUICK_START_BOOTSTRAP.md) - Build and run in 10 minutes
- 🏗️ [Architecture Overview](SELF_BOOTSTRAP_ARCHITECTURE.md) - How it works
- 📦 [Deployment Guide](DEPLOYMENT_GUIDE.md) - Build and distribute

### Reference
- 🔄 [Refactor Summary](REFACTOR_SUMMARY.md) - What changed from PyInstaller
- ☑️ [Implementation Checklist](BOOTSTRAP_CHECKLIST.md) - Testing and deployment
- 🐛 [Troubleshooting](DEPLOYMENT_GUIDE.md#troubleshooting) - Common issues

## System Requirements

### Minimum
- **OS**: macOS 11+, Windows 10+, Ubuntu 20.04+
- **RAM**: 4 GB
- **Disk**: 5 GB free
- **Internet**: Required for first launch only

### Recommended
- **RAM**: 16 GB
- **CPU**: 4+ cores
- **Disk**: SSD with 10 GB free

## Technology Stack

### Frontend
- **Framework**: Vue.js 3
- **Build Tool**: Vite
- **UI**: Custom components with Tailwind-inspired styles

### Desktop
- **Framework**: Tauri 1.4 (Rust)
- **Platform**: Native on macOS, Linux, Windows

### Backend
- **Language**: Python 3.10
- **Web Framework**: FastAPI
- **Server**: Uvicorn
- **ML Framework**: PyTorch 2.1
- **Pose Estimation**: Custom ViTPose implementation
- **Computer Vision**: OpenCV, Pillow

### Dependencies (Pinned)
```toml
torch==2.1.0
torchvision==0.16.0
fastapi==0.115.6
uvicorn==0.34.0
opencv-python==4.10.0.84
numpy==1.26.4
mmengine==0.10.5
mmcv==2.2.0
```

## Features

### Multi-Profile Support
Create custom profiles for different fish species with specific keypoint configurations:
- Define which keypoints to detect
- Configure phenotype measurements
- Persistent settings

### Batch Processing
- Process entire folders of images
- Progress tracking
- Parallel inference (future)

### Export Options
- **CSV**: Tabular data with all measurements
- **JSON**: Structured data with metadata
- **Images**: Annotated images with keypoints and measurements

### Visualization
- Live preview of detected keypoints
- Phenotype lines overlay
- Confidence scores
- Interactive image viewer

## Development

### Prerequisites
```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Node.js 18+
nvm install 18

# Install Python 3.10
conda create -n cavfish310 python=3.10
conda activate cavfish310
```

### Build from Source
```bash
# Clone
git clone https://github.com/your-org/cavfish-inference.git
cd cavfish-inference

# Activate environment
conda activate cavfish310

# Build
./build_self_bootstrap.sh
```

### Development Mode
```bash
# Terminal 1: Backend
conda activate cavfish310
cd backend
python -m cavfish_backend serve --port 8008

# Terminal 2: Frontend
cd desktop
npm run dev

# Terminal 3: Tauri
cd desktop/src-tauri
cargo tauri dev
```

### Testing
```bash
# Verify backend
python test_self_bootstrap.py

# Run tests
cd backend
pytest

# Frontend tests
cd desktop
npm test
```

## Project Structure

```
cavfish-inference/
├── backend/
│   ├── cavfish_backend/       # Entry point module
│   │   ├── __init__.py
│   │   ├── __main__.py        # CLI
│   │   └── server.py          # Server launcher
│   ├── cavfish/               # Core inference
│   ├── api/                   # FastAPI app
│   ├── phenolosses/           # Custom losses
│   ├── third_party/           # Vendored mmpose
│   └── pyproject.toml         # Dependencies
├── desktop/
│   ├── src/                   # Vue.js frontend
│   ├── src-tauri/             # Tauri/Rust
│   │   └── src/main.rs        # Bootstrap logic
│   └── bootstrap_backend.py   # Bootstrap script
├── models/                    # Model weights
├── docs/                      # Documentation
└── build_self_bootstrap.sh    # Build script
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Roadmap

### v0.2.0 (Q2 2026)
- [ ] GPU support (CUDA)
- [ ] Auto-updates
- [ ] Progressive download
- [ ] Model marketplace

### v0.3.0 (Q3 2026)
- [ ] Multi-species support
- [ ] Batch export improvements
- [ ] Performance optimizations
- [ ] Cloud sync (optional)

### v1.0.0 (Q4 2026)
- [ ] Production-ready
- [ ] Full documentation
- [ ] Tutorial videos
- [ ] Publication

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Citation

If you use this software in your research, please cite:

```bibtex
@software{fish_morphometrics_2026,
  title = {Fish Morphometrics: Automated Phenotyping Desktop Application},
  author = {Your Name},
  year = {2026},
  url = {https://github.com/your-org/cavfish-inference}
}
```

## Support

- 📧 Email: support@yourorg.com
- 💬 Discord: [Join our server](https://discord.gg/yourserver)
- 🐛 Issues: [GitHub Issues](https://github.com/your-org/cavfish-inference/issues)
- 📚 Docs: [Full Documentation](https://docs.yoursite.com)

## Acknowledgments

- **MMPose Team** - Foundational pose estimation framework
- **Tauri Team** - Excellent desktop app framework
- **OpenMMLab** - mmengine and mmcv
- **Contributors** - All who have contributed code, ideas, and feedback

## Status

🟢 **Active Development**

- Current Version: 0.1.0
- Architecture: Self-Bootstrapping
- Status: Testing Phase
- Next Release: v0.1.0 (Production)

---

**Made with ❤️ for fisheries science and aquaculture research**
