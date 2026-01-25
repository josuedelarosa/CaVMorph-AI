# Deployment & Build Guide

## Quick Start (Development)

### Prerequisites
- **Python 3.10+** with conda environment `cavfish310`
- **Node.js 16+** with npm
- **Rust 1.60+** with Tauri CLI: `cargo install tauri-cli`
- **Git** for version control

### Setup (First Time)

```bash
# 1. Clone repository
git clone <repo-url>
cd cavfish-inference

# 2. Activate conda environment
conda activate cavfish310

# 3. Install Node dependencies (frontend)
cd desktop
npm install
cd ..

# 4. Test backend API standalone
python -m backend.api.cli --port 8888

# 5. Test frontend development (separate terminal)
cd desktop
npm run dev

# 6. Launch Tauri dev app (separate terminal)
cd desktop/src-tauri
cargo tauri dev
```

### Development Workflow

1. **Backend changes**: Modify Python files in `backend/`
   - Backend reloads automatically (Python script re-imported)
   - API endpoints available at `http://127.0.0.1:8888`

2. **Frontend changes**: Modify files in `desktop/src/`
   - Hot reload: Changes reflected immediately in dev window
   - View console for errors

3. **Testing**: 
   ```bash
   # Test backend directly
   python -m backend.api.cli --port 8888 &
   curl http://127.0.0.1:8888/health
   
   # Test with sample image
   curl -X POST http://127.0.0.1:8888/infer/image \
     -H "Content-Type: application/json" \
     -d '{"image_path": "fish.jpg"}'
   ```

## Production Build

### macOS (Intel & Apple Silicon Universal)

```bash
# 1. Build backend binary
cd backend
pyinstaller api/cli.spec --distpath ../dist

# 2. Build Tauri app
cd ../desktop/src-tauri
cargo tauri build --target universal-apple-darwin

# 3. Result
ls -la ../../target/release/bundle/macos/
# Fish\ Morphometrics.app (or FishMorphometrics.app)
```

**Output**:
- `target/release/bundle/macos/Fish Morphometrics.dmg` (installer)
- `target/release/bundle/macos/Fish Morphometrics.app` (app bundle)

### Windows (MSVC, x86_64)

```bash
# 1. Ensure Visual Studio Build Tools installed
# 2. Build backend binary
cd backend
pyinstaller api/cli.spec --distpath ../dist

# 3. Build Tauri app
cd ../desktop/src-tauri
cargo tauri build

# 4. Result
ls target/release/bundle/msi/
# FishMorphometrics_0.1.0_x64-setup.exe
```

**Output**:
- `target/release/bundle/msi/FishMorphometrics_*.msi` (Windows installer)

### Linux (GTK, x86_64)

```bash
# 1. Install dependencies
sudo apt-get install libssl-dev libgtk-3-dev librsvg2-dev

# 2. Build backend binary
cd backend
pyinstaller api/cli.spec --distpath ../dist

# 3. Build Tauri app
cd ../desktop/src-tauri
cargo tauri build

# 4. Result
ls target/release/bundle/deb/
# fish-morphometrics_0.1.0_amd64.deb
```

**Output**:
- `target/release/bundle/deb/fish-morphometrics_*.deb` (Debian package)
- `target/release/bundle/appimage/FishMorphometrics_*.AppImage` (AppImage)

## Backend Binary (PyInstaller)

### What Gets Bundled

The PyInstaller spec (`backend/api/cli.spec`) includes:

```
dist/fish_backend/
├── fish_backend (executable)
├── _internal/
│   ├── torch/             # Deep learning framework
│   ├── mmpose/            # Pose estimation library
│   ├── mmengine/          # Model building framework
│   ├── cv2/               # Computer vision
│   ├── numpy/             # Numerical computing
│   ├── fastapi/           # Web framework
│   ├── uvicorn/           # ASGI server
│   ├── pydantic/          # Data validation
│   └── [other deps]
├── models/cavfish_v1/     # Model weights & config
│   ├── config.py
│   ├── weights.pth
│   └── meta.json
└── [other shared libs]
```

**Size**: ~800MB (uncompressed), ~300MB (compressed ZIP)

### Env Variables for Binary

When Tauri launches the backend binary:

| Variable | Value | Purpose |
|---|---|---|
| `FISH_DEVICE` | `cpu` | PyTorch device |
| `FISH_PORT` | `8888` | Backend API port |
| `FISH_MODEL_DIR` | `models/cavfish_v1` | Model path (relative to app dir) |

## Tauri Bundling

### macOS App Structure

```
Fish Morphometrics.app/
├── Contents/
│   ├── Info.plist
│   ├── MacOS/
│   │   └── cavfish-inference (Rust binary)
│   ├── Resources/
│   │   ├── fish_backend (Python binary)
│   │   ├── models/ (symlink or copied)
│   │   └── [frontend assets]
│   └── Frameworks/
│       └── WebKit.framework
└── [code signature files]
```

### Windows App Structure

```
Program Files/Fish Morphometrics/
├── cavfish-inference.exe (Rust binary)
├── fish_backend.exe (Python binary)
├── models/
├── resources/ (frontend assets)
└── [DLLs]
```

### Linux App Structure

```
/opt/fish-morphometrics/
├── cavfish-inference (Rust binary)
├── fish_backend (Python binary)
├── models/
├── lib/ (shared libraries)
└── [desktop entry]
```

## Troubleshooting

### Backend Won't Start

1. Check if port is already in use:
   ```bash
   lsof -i :8008  # macOS/Linux
   netstat -ano | findstr :8008  # Windows
   ```

2. Check backend logs:
   ```bash
   # In dev, look at terminal where `cargo tauri dev` was run
   # Should show Uvicorn startup message
   ```

3. Test backend manually:
   ```bash
   python -m backend.api.cli --port 8888
   curl http://127.0.0.1:8888/health
   ```

### Model Not Found

Ensure `models/cavfish_v1/` exists in app bundle with:
- `config.py` (inference config)
- `weights.pth` (model weights)
- `meta.json` (keypoint & phenotype metadata)

### Frontend Won't Load

1. Check Tauri dev server: `npm run dev` should run on `http://localhost:5173`
2. Check CSP header in `tauri.conf.json`
3. Check frontend console for errors

### PyInstaller Fails

```bash
# Clean previous builds
rm -rf dist/ build/ *.spec

# Try rebuild with verbose output
pyinstaller backend/api/cli.spec -v
```

Common issues:
- Missing dependencies → add to `hiddenimports` in `.spec`
- Data files not bundled → add to `datas` tuple
- Module import errors → check `backend/__init__.py` files

## CI/CD Integration

### GitHub Actions Example (macOS)

```yaml
name: Build macOS App
on: [push, pull_request]

jobs:
  build:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - uses: conda-incubator/setup-miniconda@v2
        with:
          environment-file: environment.yml
          activate-environment: cavfish310
      - uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          target: x86_64-apple-darwin
      - uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          target: aarch64-apple-darwin
      - run: pyinstaller backend/api/cli.spec
      - run: cd desktop/src-tauri && cargo tauri build --target universal-apple-darwin
      - uses: actions/upload-artifact@v3
        with:
          name: macos-dmg
          path: target/release/bundle/macos/*.dmg
```

## Release Checklist

- [ ] Update version in `Cargo.toml` (`desktop/src-tauri/`)
- [ ] Update version in `tauri.conf.json` (`desktop/src-tauri/`)
- [ ] Update version in `package.json` (`desktop/`)
- [ ] Test on all three platforms (or use CI)
- [ ] Build binaries (PyInstaller + Tauri)
- [ ] Sign executables (optional but recommended)
- [ ] Create GitHub Release with binaries
- [ ] Upload to app stores (if applicable)

## Performance Optimization

### PyInstaller Binary Size

- Remove unnecessary imports (check `hiddenimports`)
- Use `--onefile` flag if file count is an issue
- Compress with UPX (optional, may slow startup)

### Runtime Performance

- Model loads once and caches (first image takes ~5 seconds)
- Subsequent images ~0.5-1 second each (CPU only)
- Consider adding CUDA support for faster inference (optional)

## Security Notes

- App runs fully offline (no network calls except local backend)
- No telemetry or analytics
- User data stays local (no cloud upload)
- Model weights are frozen (no remote loading)
- Consider code signing for macOS/Windows distribution

## Future Enhancements

- [ ] Automatic updates (Tauri update plugin)
- [ ] Multi-language support (i18n)
- [ ] Dark mode
- [ ] Model hot-swap (load different weight files)
- [ ] GPU acceleration (CUDA support)
- [ ] Real-time preview with parameter adjustment
