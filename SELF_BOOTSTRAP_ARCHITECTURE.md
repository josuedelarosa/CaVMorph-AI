# Fish Morphometrics Desktop App - Self-Bootstrapping Architecture

## Overview

This desktop application uses a **self-bootstrapping architecture** where the Python backend is not frozen with PyInstaller, but instead installed and managed at runtime in an app-local environment.

### Key Benefits

- ✅ **Truly portable**: No system Python or conda dependencies
- ✅ **Smaller app size**: No bundled PyInstaller executable
- ✅ **Easier updates**: Backend can be updated independently
- ✅ **Better debugging**: Full Python stack traces and logging
- ✅ **Reproducible**: Pinned dependencies via pyproject.toml

## Architecture

```
┌─────────────────────────────────────────┐
│         Tauri Desktop App (Rust)        │
│  - Native window management             │
│  - Bootstrap orchestration              │
│  - Backend lifecycle management         │
└────────────┬────────────────────────────┘
             │
             ├─ First Launch
             │  ├─ Check if bootstrapped
             │  ├─ Create venv in ~/Library/Application Support/FishMorph/venv
             │  ├─ Install backend package with dependencies
             │  └─ Download & verify model weights
             │
             └─ Every Launch
                └─ Start backend: `venv/bin/python -m cavfish_backend serve --port 8008`
```

## Directory Structure

### Development

```
cavfish-inference/
├── backend/                    # Python backend package
│   ├── cavfish_backend/       # New entry point module
│   │   ├── __init__.py
│   │   ├── __main__.py        # CLI: python -m cavfish_backend serve
│   │   └── server.py          # FastAPI server wrapper
│   ├── cavfish/               # Core inference logic
│   ├── api/                   # FastAPI app
│   ├── phenolosses/           # Custom losses
│   ├── third_party/           # Vendored mmpose components
│   └── pyproject.toml         # Dependencies (pinned versions)
├── desktop/
│   ├── bootstrap_backend.py   # Bootstrap script (bundled with app)
│   ├── src/                   # Vue.js frontend
│   └── src-tauri/             # Rust Tauri code
│       └── src/main.rs        # Bootstrap + backend lifecycle
└── models/                    # Model weights (for development)
```

### Production (User's Machine)

```
~/Library/Application Support/FishMorph/
├── venv/                      # App-managed Python environment
│   ├── bin/python
│   └── lib/python3.10/site-packages/
├── backend/                   # Copied backend source
│   ├── cavfish_backend/
│   ├── cavfish/
│   ├── api/
│   └── pyproject.toml
├── models/                    # Downloaded model weights
│   └── model_weights.pth
├── logs/                      # Backend logs
│   ├── bootstrap.log
│   └── backend.log
└── config.json                # Bootstrap status
```

## Backend Package Structure

### Entry Point

```python
# python -m cavfish_backend serve --port 8008

cavfish_backend/
├── __init__.py        # Package metadata
├── __main__.py        # CLI entry point
└── server.py          # Uvicorn server launcher
```

### CLI Commands

```bash
# Start server
python -m cavfish_backend serve --port 8008 --device cpu

# Options
--port PORT          Port to bind to (default: 8008)
--host HOST          Host to bind to (default: 127.0.0.1)
--device DEVICE      Device: cpu or cuda (default: cpu)
--log-level LEVEL    Log level (default: info)
```

## Bootstrap Process

### First Launch Sequence

1. **Check Bootstrap Status**
   - Check if `~/Library/Application Support/FishMorph/config.json` exists
   - Verify venv exists at expected location

2. **Run Bootstrap** (if needed)
   ```bash
   python3 bootstrap_backend.py \
       --backend-source /path/to/bundled/backend
   ```

3. **Bootstrap Steps**
   - Create venv using `python3 -m venv`
   - Upgrade pip
   - Install backend package: `pip install -e /path/to/backend`
   - Download model weights (optional, if URL configured)
   - Verify model checksum (SHA256)
   - Save config.json

4. **Start Backend**
   ```bash
   ~/Library/Application Support/FishMorph/venv/bin/python \
       -m cavfish_backend serve --port 8008
   ```

5. **Health Check**
   - Poll `GET http://127.0.0.1:8008/health`
   - Timeout: 60 seconds

## Dependencies Management

### pyproject.toml (Pinned Versions)

```toml
[project]
name = "cavfish-backend"
version = "0.1.0"
requires-python = ">=3.10,<3.11"
dependencies = [
    "fastapi==0.115.6",
    "uvicorn[standard]==0.34.0",
    "torch==2.1.0",
    "torchvision==0.16.0",
    "opencv-python==4.10.0.84",
    "pillow==11.0.0",
    "numpy==1.26.4",
    "scipy==1.14.1",
    "pandas==2.2.3",
    "pydantic==2.10.5",
    "mmengine==0.10.5",
    "mmcv==2.2.0",
    "yapf==0.43.0",
]
```

### Why Pinned Versions?

- **Reproducibility**: Same versions everywhere
- **Security**: Known versions, controlled updates
- **Stability**: No surprise breaking changes
- **Scientific rigor**: Results must be reproducible

## Model Management

### Configuration

```python
# In bootstrap_backend.py
class BootstrapConfig:
    model_url = "https://your-cdn.com/models/cavfish_v1_weights.pth"
    model_checksum = "abc123..."  # SHA256 checksum
    model_filename = "model_weights.pth"
```

### Download & Verification

```python
# Download model
urllib.request.urlretrieve(model_url, local_path)

# Verify checksum
sha256_hash = hashlib.sha256()
with open(local_path, "rb") as f:
    for chunk in iter(lambda: f.read(4096), b""):
        sha256_hash.update(chunk)

if sha256_hash.hexdigest() != expected_checksum:
    raise ValueError("Model checksum mismatch")
```

## Building the App

### Prerequisites

- **Python 3.10.x** (for testing backend)
- **Node.js 18+** (for frontend)
- **Rust/Cargo** (for Tauri)
- **Conda** (optional, for development environment)

### Build Steps

```bash
# 1. Activate conda environment (if using)
conda activate cavfish310

# 2. Run build script
./build_self_bootstrap.sh
```

### Build Output

- **macOS**: `desktop/src-tauri/target/release/bundle/dmg/`
- **Linux**: `desktop/src-tauri/target/release/bundle/appimage/`
- **Windows**: `desktop/src-tauri/target/release/bundle/msi/`

## Development Mode

```bash
# Terminal 1: Start development backend
cd backend
conda activate cavfish310
python -m cavfish_backend serve --port 8008

# Terminal 2: Start Tauri dev mode
cd desktop
npm install
cd src-tauri
cargo tauri dev
```

In dev mode, Tauri tries to spawn backend with `python3 -m backend.api.cli` (legacy compatibility).

## Logging

### Bootstrap Logs
```
~/Library/Application Support/FishMorph/logs/bootstrap.log
```

Contains:
- Venv creation
- Dependency installation
- Model download progress
- Checksum verification

### Backend Logs
```
~/Library/Application Support/FishMorph/logs/backend.log
```

Contains:
- Server startup
- Request logs
- Inference logs
- Errors and warnings

## Troubleshooting

### Bootstrap Fails

**Check logs:**
```bash
tail -f ~/Library/Application\ Support/FishMorph/logs/bootstrap.log
```

**Common issues:**
- No internet connection (for pip install)
- Python 3.10 not available on system
- Insufficient disk space

**Solution:**
Delete bootstrap directory and retry:
```bash
rm -rf ~/Library/Application\ Support/FishMorph
```

### Backend Won't Start

**Check backend log:**
```bash
tail -f ~/Library/Application\ Support/FishMorph/logs/backend.log
```

**Common issues:**
- Port already in use
- Missing model weights
- Corrupt venv

**Solution:**
```bash
# Re-bootstrap
rm ~/Library/Application\ Support/FishMorph/config.json
# Restart app
```

### Model Checksum Mismatch

**Symptom:**
```
ERROR: Model checksum verification failed
```

**Solution:**
1. Check model URL is correct
2. Verify checksum in `bootstrap_backend.py`
3. Re-download:
   ```bash
   rm ~/Library/Application\ Support/FishMorph/models/*.pth
   rm ~/Library/Application\ Support/FishMorph/config.json
   ```

## Security Considerations

### Pinned Dependencies
All dependencies are pinned to specific versions. Update carefully:

```bash
# Test updates in dev environment first
cd backend
pip install --upgrade torch torchvision
pip freeze > requirements.txt
# Review changes, update pyproject.toml
```

### Model Verification
Models are verified with SHA256 checksums. Never skip verification in production.

### File System Permissions
App only writes to:
- `~/Library/Application Support/FishMorph/` (app data)
- User-selected export directories

## Future Enhancements

### Potential Improvements

1. **Delta Updates**
   - Download only changed dependencies
   - Incremental backend updates

2. **GPU Support**
   - Detect CUDA availability
   - Install GPU-specific torch wheels

3. **Multiple Models**
   - Support different fish species
   - Model switching at runtime

4. **Offline Mode**
   - Bundle minimal dependencies
   - Only download extras if needed

5. **Auto-Updates**
   - Check for backend updates
   - In-app update mechanism

## Comparison: PyInstaller vs Self-Bootstrap

| Aspect | PyInstaller | Self-Bootstrap |
|--------|-------------|----------------|
| **App Size** | ~2-3 GB | ~50 MB |
| **First Launch** | Instant | 2-5 minutes |
| **Updates** | Full redownload | Backend only |
| **Debugging** | Limited | Full Python stack |
| **Python Deps** | Bundled | User downloads |
| **Portability** | High | High |
| **Build Complexity** | High | Medium |

## License

[Your License Here]

## Credits

- Tauri: https://tauri.app
- MMPose: https://github.com/open-mmlab/mmpose
- Vue.js: https://vuejs.org
