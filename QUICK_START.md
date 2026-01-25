# Quick Start Guide

## 5-Minute Setup for Developers

### ⚠️ IMPORTANT: Use `cavfish310` Environment

This project requires the **cavfish310** conda environment with pre-installed ML dependencies.

```bash
# Verify environment exists
conda env list | grep cavfish310

# Activate it
conda activate cavfish310

# Verify packages
python3 -c "import torch, mmpose, fastapi; print('✅ All dependencies ready')"
```

### Prerequisites

- **Conda** environment `cavfish310` (already set up with PyTorch, MMPose, FastAPI)
- **Node.js 16+**
- **Rust 1.60+** (with `cargo tauri` CLI)

```bash
# Install Tauri CLI
cargo install tauri-cli

# Verify versions
python3 --version      # Should be 3.10+
node --version         # Should be 16+
cargo --version        # Should be 1.60+
```

### Step 1: Clone & Setup

```bash
git clone <your-repo-url>
cd cavfish-inference

# Activate conda environment (REQUIRED)
conda activate cavfish310

# Install frontend dependencies
cd desktop
npm install
cd ..
```

### Step 2: Run in Development Mode

**Terminal 1: Start backend API**
```bash
conda activate cavfish310
python3 -m backend.api.cli --port 8008
# Output: Uvicorn running on http://127.0.0.1:8008
```

**Terminal 2: Start frontend dev server** (optional, for hot reload)
```bash
cd desktop
npm run dev
# Output: Local: http://localhost:5173
```

**Terminal 3: Launch Tauri app**
```bash
cd desktop/src-tauri
cargo tauri dev
```

The app window will open. Tauri automatically connects to both the backend (8008) and frontend dev server (5173).

### Step 3: Test the App

1. Click **"Select Folder"**
2. Navigate to `<repo>/models/cavfish_v1/tmp/` (or any folder with images)
3. Click **"Analyze Images"**
4. Wait for processing (~1-2 seconds per image)
5. View results in the table
6. Click **"Export CSV"** to download results

## Build for Production

### Quick Build (all platforms)

```bash
# Make sure cavfish310 is activated first!
conda activate cavfish310

# Then run build script (it will re-activate the environment)
./build.sh
```

Or manually:

```bash
conda activate cavfish310

# 1. Build backend binary
python3 -m pyinstaller backend/api/cli.spec --distpath dist

# 2. Build Tauri app
cd desktop/src-tauri
cargo tauri build
```

Results in `target/release/bundle/`

### Platform-Specific Builds

**macOS (Intel + Apple Silicon)**
```bash
cd desktop/src-tauri
cargo tauri build --target universal-apple-darwin
```

**Windows (x86_64)**
```bash
cd desktop/src-tauri
cargo tauri build
# Creates: FishMorphometrics_0.1.0_x64-setup.exe
```

**Linux (x86_64)**
```bash
cd desktop/src-tauri
cargo tauri build
# Creates: fish-morphometrics_0.1.0_amd64.deb
```

## Directory Structure

```
cavfish-inference/
├── backend/                      # Python backend
│   ├── api/
│   │   ├── cli.py               # Entry point
│   │   └── app.py               # FastAPI routes
│   ├── cavfish/                 # Core inference logic
│   ├── phenolosses/             # Custom losses
│   ├── requirements.txt          # Dependencies
│   └── api/cli.spec             # PyInstaller config
│
├── desktop/                      # Tauri frontend
│   ├── src/
│   │   ├── App.vue              # Main component
│   │   ├── main.ts              # Entry point
│   │   ├── types/               # TypeScript types
│   │   ├── utils/               # API & helpers
│   │   └── styles/              # CSS
│   ├── src-tauri/
│   │   ├── src/main.rs          # Rust app
│   │   ├── Cargo.toml           # Rust deps
│   │   └── tauri.conf.json      # Config
│   ├── index.html               # HTML template
│   ├── package.json             # Node deps
│   ├── vite.config.ts           # Bundler config
│   └── tsconfig.json            # TS config
│
├── models/cavfish_v1/           # Model files
│   ├── config.py                # Training config
│   ├── weights.pth              # Model weights
│   └── meta.json                # Metadata
│
├── ARCHITECTURE.md              # System design
├── DEPLOYMENT.md                # Build guide
├── README.md                    # User guide
└── build.sh                     # Build script
```

## Common Commands

### Development

```bash
# Make sure cavfish310 is activated!
conda activate cavfish310

# Run backend standalone
python3 -m backend.api.cli --port 8888

# Test backend health
curl http://127.0.0.1:8008/health

# Run frontend dev server
cd desktop && npm run dev

# Launch Tauri dev app
cd desktop/src-tauri && cargo tauri dev

# View app logs
cd desktop/src-tauri && cargo tauri dev 2>&1 | tee app.log
```

### Building

```bash
# Activate environment first!
conda activate cavfish310

# Build everything (script handles env activation)
./build.sh

# Build just backend
python3 -m pyinstaller backend/api/cli.spec --distpath dist

# Build just frontend
cd desktop && npm run build

# Build just Tauri
cd desktop/src-tauri && cargo tauri build

# Clean build artifacts
cargo clean
rm -rf desktop/dist/ desktop/src-tauri/target/
```

### Testing

```bash
# Activate cavfish310 first
conda activate cavfish310

# Test backend with sample image
curl -X POST http://127.0.0.1:8008/infer/image \
  -H "Content-Type: application/json" \
  -d '{"image_path": "fish.jpg", "return_overlay_png": true}' \
  | python3 -m json.tool

# List available endpoints
curl http://127.0.0.1:8008/openapi.json | python3 -m json.tool
```

## Troubleshooting

### Backend won't start

```bash
# Check if port 8008 is already in use
lsof -i :8008

# Use a different port
python -m backend.api.cli --port 8888

# Enable verbose logging
RUST_LOG=debug cargo tauri dev
```

### Frontend won't load

```bash
# Check Vite dev server
cd desktop && npm run dev

# Check CSP headers in tauri.conf.json
# Ensure 'wasm-unsafe-eval' is in script-src
```

### PyInstaller fails

```bash
# Clean and rebuild
rm -rf dist/ build/
python3 -m pip install --upgrade pyinstaller
python3 -m pyinstaller backend/api/cli.spec -v
```

### Model not found

```bash
# Check model directory exists
ls -la models/cavfish_v1/

# Must contain:
# - config.py
# - weights.pth
# - meta.json
```

## Development Tips

1. **Backend changes**: Edit `backend/` → backend auto-reloads on file change
2. **Frontend changes**: Edit `desktop/src/` → hot reload in dev mode
3. **Config changes**: Edit `tauri.conf.json` or `Cargo.toml` → rebuild Tauri
4. **Model changes**: Must rebuild backend binary with PyInstaller

## Next Steps

1. **Customize UI**: Edit `desktop/src/App.vue` and `desktop/src/styles/main.css`
2. **Add endpoints**: Edit `backend/api/app.py`
3. **Adjust phenotypes**: Edit `models/cavfish_v1/config.py` and regenerate `meta.json`
4. **Add logging**: Configure Rust logging in `main.rs`

## Resources

- **Tauri Docs**: https://tauri.app/v1/docs/
- **Vue 3 Docs**: https://vuejs.org/guide/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **MMPose Docs**: https://mmpose.readthedocs.io/

## Getting Help

- Check `ARCHITECTURE.md` for system design
- See `DEPLOYMENT.md` for build details
- Read `README.md` for user guide
- File GitHub issues for bugs

---

**Happy hacking! 🐠**
