# Fish Morphometrics - Quick Start Guide

## Self-Bootstrapping Architecture

This guide gets you from source code to distributable app in 10 minutes.

## Prerequisites (5 minutes)

```bash
# 1. Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 2. Install Node.js 18+ (via nvm recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# 3. Verify installations
rustc --version  # Should work
node --version   # Should be 18+
python3 --version # Should be 3.10.x

# 4. Install Python dependencies (development only)
conda env create -f environment.yml
conda activate cavfish310
```

## Build (5 minutes)

```bash
# Clone repository (if not already done)
git clone https://github.com/your-org/cavfish-inference.git
cd cavfish-inference

# Activate conda environment
conda activate cavfish310

# Run single-command build
./build_self_bootstrap.sh

# Wait for completion...
# ✓ Frontend built
# ✓ Tauri compiled
# ✓ Bundle created
```

## Test (2 minutes)

```bash
# Test backend package
python test_self_bootstrap.py

# Output should show:
# ✓ PASS   Backend Import
# ✓ PASS   Backend CLI
# ✓ PASS   Bootstrap Script
```

## Locate Build

```bash
# macOS
open desktop/src-tauri/target/release/bundle/dmg/

# Linux
nautilus desktop/src-tauri/target/release/bundle/appimage/

# Windows
explorer desktop\src-tauri\target\release\bundle\msi\
```

## Install & Run

### macOS
```bash
# Open the DMG
open "Fish Morphometrics.dmg"

# Drag to Applications
# First launch: Right-click → Open

# Wait 3-7 minutes for first-time bootstrap
# Subsequent launches: Instant!
```

### Linux
```bash
# Make executable
chmod +x Fish-Morphometrics.AppImage

# Run
./Fish-Morphometrics.AppImage

# Wait 3-7 minutes for first-time bootstrap
```

### Windows
```powershell
# Run installer
Start-Process "Fish Morphometrics.msi"

# Follow installer
# First launch takes 3-7 minutes
```

## Development Mode

For active development:

```bash
# Terminal 1: Backend
conda activate cavfish310
cd backend
python -m cavfish_backend serve --port 8008

# Terminal 2: Frontend
cd desktop
npm install
npm run dev

# Terminal 3: Tauri (optional)
cd desktop/src-tauri
cargo tauri dev
```

## Verify Installation

After first launch, check:

```bash
# macOS/Linux
ls -la ~/Library/Application\ Support/FishMorph/
# Should see: venv/, backend/, models/, logs/, config.json

# Check logs
tail ~/Library/Application\ Support/FishMorph/logs/bootstrap.log
tail ~/Library/Application\ Support/FishMorph/logs/backend.log
```

## Common Issues

### Build Fails: "cargo: command not found"
```bash
# Restart terminal after Rust install
# Or manually source:
source $HOME/.cargo/env
```

### Build Fails: "node: command not found"
```bash
# Install Node.js 18+
nvm install 18
nvm use 18
```

### Build Fails: "Python 3.10 not found"
```bash
# Install Python 3.10 via conda
conda create -n cavfish310 python=3.10
conda activate cavfish310
```

### First Launch Hangs
```bash
# Check logs
tail -f ~/Library/Application\ Support/FishMorph/logs/bootstrap.log

# If stuck, delete and retry:
rm -rf ~/Library/Application\ Support/FishMorph
# Re-launch app
```

### Backend Won't Start
```bash
# Check backend log
tail -f ~/Library/Application\ Support/FishMorph/logs/backend.log

# Force re-bootstrap
rm ~/Library/Application\ Support/FishMorph/config.json
# Re-launch app
```

## What Happens on First Launch?

```
1. App launches
   ↓
2. Detects no existing backend
   ↓
3. Shows "Initializing..." UI
   ↓
4. Creates Python venv (30s)
   ↓
5. Installs dependencies (2-4 min)
   ├─ torch
   ├─ torchvision
   ├─ fastapi
   ├─ numpy
   └─ mmpose ecosystem
   ↓
6. Downloads model weights (1-2 min)
   ├─ Downloads from CDN
   └─ Verifies SHA256 checksum
   ↓
7. Starts backend server (5s)
   ↓
8. Health check passes
   ↓
9. App ready! ✅
```

Total: **3-7 minutes** (only once!)

## File Structure

After build:

```
cavfish-inference/
├── backend/                    # Backend source (bundled with app)
│   ├── cavfish_backend/       # Entry point module
│   ├── cavfish/               # Inference logic
│   ├── api/                   # FastAPI app
│   └── pyproject.toml         # Dependencies
├── desktop/
│   ├── bootstrap_backend.py   # Bootstrap script (bundled)
│   ├── src/                   # Vue.js frontend
│   └── src-tauri/
│       ├── src/main.rs        # Tauri app
│       └── target/release/bundle/
│           ├── dmg/           # macOS installer
│           ├── appimage/      # Linux installer
│           └── msi/           # Windows installer
└── models/                    # Development models (not bundled)
```

After installation on user machine:

```
~/Library/Application Support/FishMorph/
├── venv/                      # Isolated Python environment
│   ├── bin/python
│   └── lib/python3.10/site-packages/
├── backend/                   # Installed backend
├── models/                    # Downloaded weights
│   └── model_weights.pth
├── logs/                      # Logs
│   ├── bootstrap.log
│   └── backend.log
└── config.json                # Bootstrap status
```

## Next Steps

1. **Test the app** with sample images
2. **Read the docs**:
   - `SELF_BOOTSTRAP_ARCHITECTURE.md` - How it works
   - `DEPLOYMENT_GUIDE.md` - Distribution guide
   - `REFACTOR_SUMMARY.md` - What changed
3. **Customize**:
   - Update model URL in `desktop/bootstrap_backend.py`
   - Modify branding in `desktop/src-tauri/tauri.conf.json`
   - Add features to Vue.js frontend

## Support

- **Issues**: https://github.com/your-org/cavfish-inference/issues
- **Docs**: See `docs/` directory
- **Logs**: Check `~/Library/Application Support/FishMorph/logs/`

---

**Version**: 0.1.0  
**Architecture**: Self-Bootstrapping  
**Build Time**: ~5 minutes  
**First Launch**: 3-7 minutes  
**Subsequent Launches**: <5 seconds
