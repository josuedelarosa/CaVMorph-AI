# Fish Morphometrics - Self-Bootstrapping Refactor Summary

## What Changed

We've completely refactored the desktop application from a **PyInstaller-frozen** architecture to a **self-bootstrapping** architecture that creates and manages its own Python environment at runtime.

## Before (PyInstaller)

```
┌─────────────────────┐
│   Tauri App (2GB+)  │
│   ├─ UI (50MB)      │
│   └─ fish_backend   │  ← Frozen Python executable
│      ├─ Python      │     (~2GB with all deps)
│      ├─ torch       │
│      ├─ numpy       │
│      └─ mmpose      │
└─────────────────────┘

Problems:
❌ Huge app size (2-3 GB)
❌ Difficult to debug (frozen Python)
❌ Hard to update backend
❌ macOS dylib issues
❌ Long build times
```

## After (Self-Bootstrap)

```
┌─────────────────────────────┐
│   Tauri App (50MB)          │
│   ├─ UI                     │
│   ├─ bootstrap_backend.py   │  ← Bootstrap script
│   └─ backend/ (source)      │  ← Backend source code
└─────────────────────────────┘
          │
          │ First Launch
          ↓
┌─────────────────────────────────────────┐
│ ~/Library/Application Support/FishMorph/│
│ ├─ venv/                                │  ← App-managed Python
│ │  ├─ bin/python                        │
│ │  └─ lib/python3.10/site-packages/    │
│ ├─ backend/                             │  ← Installed backend
│ ├─ models/                              │  ← Downloaded weights
│ └─ logs/                                │  ← Runtime logs
└─────────────────────────────────────────┘

Benefits:
✅ Small app size (50 MB)
✅ Easy debugging (full Python)
✅ Easy backend updates
✅ No dylib issues
✅ Fast builds
✅ Reproducible installs
```

## Key Components Created

### 1. Backend Package (`backend/cavfish_backend/`)

New entry point module that makes backend a proper Python package:

```python
# python -m cavfish_backend serve --port 8008

cavfish_backend/
├── __init__.py      # Version info
├── __main__.py      # CLI entry point
└── server.py        # Uvicorn launcher
```

**Purpose**: Clean CLI interface for starting the backend server.

### 2. Bootstrap Script (`desktop/bootstrap_backend.py`)

Comprehensive bootstrap script (12KB) that:
- Creates isolated venv in app data directory
- Installs backend package with pinned dependencies
- Downloads and verifies model weights (SHA256)
- Saves configuration
- Provides detailed logging

**Purpose**: One-time setup on first launch to prepare the backend environment.

### 3. Updated Tauri Code (`desktop/src-tauri/src/main.rs`)

Enhanced Rust code that:
- Detects if backend is bootstrapped
- Runs bootstrap if needed
- Starts backend from venv
- Monitors health
- Handles errors gracefully

**Key Functions**:
- `is_backend_bootstrapped()` - Check if setup is complete
- `run_bootstrap()` - Execute bootstrap process
- `spawn_backend_prod()` - Launch backend from venv

### 4. Dependencies Management (`backend/pyproject.toml`)

Pinned dependencies for reproducibility:

```toml
[project]
name = "cavfish-backend"
version = "0.1.0"
requires-python = ">=3.10,<3.11"
dependencies = [
    "fastapi==0.115.6",
    "torch==2.1.0",
    "torchvision==0.16.0",
    "numpy==1.26.4",
    # ... all pinned to exact versions
]
```

**Purpose**: Ensure identical installations across all user machines.

### 5. Build Script (`build_self_bootstrap.sh`)

Simplified build process (no PyInstaller):

```bash
#!/bin/bash
# 1. Check prerequisites
# 2. Build frontend (Vue.js)
# 3. Build Tauri app (bundles backend source)
# 4. Create platform installer
```

**Purpose**: One-command build for distribution.

## User Experience

### First Launch (3-7 minutes)

```
🚀 Fish Morphometrics
   Initializing...

   ⏳ Creating Python environment...
   ⏳ Installing dependencies... (2-5 min)
   ⏳ Downloading model weights... (1-2 min)
   ⏳ Verifying installation...
   
   ✅ Ready!
```

### Subsequent Launches (5 seconds)

```
🚀 Fish Morphometrics
   
   ✅ Ready!
```

## File Locations

### Development

```
cavfish-inference/
├── backend/
│   ├── cavfish_backend/       # NEW: Entry point module
│   ├── cavfish/               # Core logic
│   ├── api/                   # FastAPI app
│   └── pyproject.toml         # NEW: Dependency manifest
├── desktop/
│   ├── bootstrap_backend.py   # NEW: Bootstrap script
│   └── src-tauri/
│       └── src/main.rs        # UPDATED: Bootstrap integration
└── build_self_bootstrap.sh    # NEW: Build script
```

### Production (User's Machine)

```
macOS:
  ~/Library/Application Support/FishMorph/
  ├── venv/                    # Isolated Python environment
  ├── backend/                 # Installed backend package
  ├── models/                  # Model weights
  ├── logs/                    # Bootstrap & backend logs
  └── config.json              # Bootstrap status

Linux:
  ~/.local/share/FishMorph/
  └── (same structure)

Windows:
  %APPDATA%\FishMorph\
  └── (same structure)
```

## How It Works

### Bootstrap Flow

```
1. User launches app
   ↓
2. Tauri checks: is_backend_bootstrapped()?
   ├─ Yes → Go to step 5
   └─ No  → Continue
   ↓
3. Run bootstrap_backend.py
   ├─ Create venv
   ├─ Install dependencies (pip install -e backend/)
   ├─ Download model weights
   └─ Save config.json
   ↓
4. Bootstrap complete
   ↓
5. Start backend:
   ~/Library/Application Support/FishMorph/venv/bin/python \
     -m cavfish_backend serve --port 8008
   ↓
6. Health check: GET /health
   ↓
7. App ready ✅
```

### Runtime Flow

```
Frontend (Vue.js)
   ↓ HTTP
Backend (FastAPI)
   ↓
Inference Engine (cavfish)
   ↓
Model (PyTorch)
```

## Testing

### Verify Setup

```bash
# Test backend package
python test_self_bootstrap.py

# Expected output:
# ✓ PASS   Backend Import
# ✓ PASS   Backend CLI  
# ✓ PASS   Bootstrap Script
```

### Manual Test

```bash
# Test backend manually
conda activate cavfish310
cd backend
python -m cavfish_backend serve --port 8008

# In browser: http://127.0.0.1:8008/docs
```

### Integration Test

```bash
# Test full app in dev mode
cd desktop
npm install
cd src-tauri
cargo tauri dev
```

## Build & Distribute

### Build

```bash
./build_self_bootstrap.sh
```

**Output**:
- **macOS**: `desktop/src-tauri/target/release/bundle/dmg/Fish Morphometrics.dmg`
- **Linux**: `desktop/src-tauri/target/release/bundle/appimage/fish-morphometrics.AppImage`
- **Windows**: `desktop\src-tauri\target\release\bundle\msi\Fish Morphometrics.msi`

### Distribute

1. **Upload installer** to download server
2. **Users download** and install
3. **First launch** runs bootstrap (one-time)
4. **App ready** for immediate use

## Advantages

### For Users

- ✅ **Small download**: 50 MB vs 2-3 GB
- ✅ **Fast updates**: Backend-only updates possible
- ✅ **Transparent**: Can inspect Python environment
- ✅ **Debuggable**: Full error messages and logs

### For Developers

- ✅ **Fast builds**: No PyInstaller (minutes vs hours)
- ✅ **Easy debugging**: No frozen Python mysteries
- ✅ **Standard Python**: Normal pip install workflow
- ✅ **Version control**: Dependencies tracked in pyproject.toml
- ✅ **Reproducible**: Exact versions everywhere

### For Scientists

- ✅ **Verifiable**: Can inspect installed packages
- ✅ **Reproducible**: Pinned dependency versions
- ✅ **Auditable**: Clear dependency chain
- ✅ **Updatable**: Can update specific components

## Limitations

### Known Issues

1. **First launch delay**: 3-7 minutes for bootstrap
   - **Mitigation**: Show progress, explain what's happening
   
2. **Internet required**: For first launch dependency download
   - **Mitigation**: Could pre-bundle minimal deps
   
3. **Disk space**: Requires 3-5 GB total
   - **Mitigation**: Document requirements clearly

### Not Included

- ❌ GPU support (CPU inference only)
- ❌ Auto-updates (manual download required)
- ❌ Offline mode (needs internet for bootstrap)

## Future Enhancements

### Possible Improvements

1. **Progressive download**: Start app, download in background
2. **Delta updates**: Only download changed packages
3. **GPU support**: Detect CUDA, install GPU wheels
4. **Auto-updates**: In-app update mechanism
5. **Offline bundles**: Pre-package core dependencies
6. **Multi-model**: Support multiple fish species
7. **Model marketplace**: Download models on demand

## Migration Path

If you have an existing PyInstaller build:

1. **Keep old build** available during transition
2. **Test new architecture** thoroughly
3. **Update documentation** for users
4. **Communicate** the change (explain benefits)
5. **Provide support** for first-launch issues

## Documentation

### For Users
- `DEPLOYMENT_GUIDE.md` - Installation and usage
- `docs/USER_GUIDE.md` - How to use the app

### For Developers
- `SELF_BOOTSTRAP_ARCHITECTURE.md` - Technical details
- `backend/README.md` - Backend API reference
- `test_self_bootstrap.py` - Verification script

## Verification Checklist

Before deploying:

- [ ] `test_self_bootstrap.py` passes
- [ ] Backend starts with `python -m cavfish_backend serve`
- [ ] Frontend builds without errors
- [ ] Tauri app builds successfully
- [ ] Bootstrap script works independently
- [ ] Model checksum is correct
- [ ] Dependencies are all pinned
- [ ] Logs are written to correct location
- [ ] App data directory is created properly
- [ ] Backend stops cleanly on app exit

## Support

### Getting Help

- **Architecture questions**: Read `SELF_BOOTSTRAP_ARCHITECTURE.md`
- **Build issues**: Check `DEPLOYMENT_GUIDE.md`
- **Runtime errors**: Check logs in `~/Library/Application Support/FishMorph/logs/`

### Reporting Issues

When reporting problems, include:
1. OS and version
2. Bootstrap log
3. Backend log
4. Steps to reproduce

---

**Architecture Version**: Self-Bootstrapping v1.0  
**Date**: 2026-01-25  
**Status**: ✅ Ready for Testing
