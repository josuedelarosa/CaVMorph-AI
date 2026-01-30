# Fish Morphometrics - Deployment Guide
## Self-Bootstrapping Architecture

## Overview

The self-bootstrapping architecture eliminates the need for PyInstaller and creates a truly portable desktop application. The app ships with only the UI and a bootstrap script, then creates and manages its own Python environment on first launch.

## Prerequisites for Building

### Required Software

1. **Python 3.10.x**
   ```bash
   python3 --version  # Should show 3.10.x
   ```

2. **Node.js 18+**
   ```bash
   node --version  # Should be 18.0.0 or higher
   ```

3. **Rust & Cargo**
   ```bash
   # Install via rustup
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   
   cargo --version  # Verify installation
   ```

4. **Conda** (recommended for development)
   ```bash
   conda --version
   ```

### Platform-Specific Requirements

#### macOS
- Xcode Command Line Tools
  ```bash
  xcode-select --install
  ```

#### Linux
- Build essentials
  ```bash
  sudo apt-get install -y build-essential libssl-dev pkg-config
  ```

#### Windows
- Visual Studio Build Tools
- MSVC compiler

## Build Process

### Step 1: Clone and Setup

```bash
# Clone repository
git clone https://github.com/your-org/cavfish-inference.git
cd cavfish-inference

# Create and activate conda environment
conda env create -f environment.yml
conda activate cavfish310
```

### Step 2: Verify Backend

```bash
# Test backend package
python test_self_bootstrap.py

# You should see:
# ✓ PASS   Backend Import
# ✓ PASS   Backend CLI
# ✓ PASS   Bootstrap Script
```

### Step 3: Configure Model Download (Optional)

Edit `desktop/bootstrap_backend.py`:

```python
class BootstrapConfig:
    # ... other config ...
    
    # Set your model hosting URL
    model_url = "https://your-cdn.com/models/cavfish_v1_weights.pth"
    
    # Calculate and set SHA256 checksum
    model_checksum = "YOUR_SHA256_CHECKSUM_HERE"
```

To generate checksum:
```bash
sha256sum models/cavfish_v1/best_coco_AP_epoch_4780.pth
```

### Step 4: Build Application

```bash
# Run build script
./build_self_bootstrap.sh
```

This will:
1. Install frontend dependencies
2. Build Vue.js frontend
3. Build Tauri app with Rust
4. Bundle backend source code with app
5. Create platform-specific installer

### Step 5: Locate Build Artifacts

```bash
# macOS
ls -lh desktop/src-tauri/target/release/bundle/dmg/

# Linux
ls -lh desktop/src-tauri/target/release/bundle/appimage/

# Windows
dir desktop\src-tauri\target\release\bundle\msi\
```

## First Launch Behavior

When a user launches the app for the first time:

### 1. Bootstrap Detection
```
Checking if backend is bootstrapped...
Looking for: ~/Library/Application Support/FishMorph/config.json
Result: Not found → Need to bootstrap
```

### 2. Bootstrap Process
```
Creating directories:
  ✓ ~/Library/Application Support/FishMorph/
  ✓ ~/Library/Application Support/FishMorph/venv/
  ✓ ~/Library/Application Support/FishMorph/models/
  ✓ ~/Library/Application Support/FishMorph/logs/

Creating virtual environment...
  ✓ Using Python 3.10.19

Installing dependencies...
  ⏳ This may take 2-5 minutes...
  ✓ Installed: torch, torchvision, fastapi, uvicorn, etc.

Downloading model weights...
  ⏳ Downloading from CDN...
  ✓ Downloaded 500 MB
  ✓ Checksum verified

Saving configuration...
  ✓ config.json created

Bootstrap complete!
```

### 3. Backend Startup
```
Starting backend server...
  Command: ~/Library/Application Support/FishMorph/venv/bin/python \
           -m cavfish_backend serve --port 8008

Waiting for health check...
  ⏳ GET http://127.0.0.1:8008/health
  ✓ Backend ready

App ready for use!
```

Total time: **3-7 minutes** (mostly dependency download)

## Subsequent Launches

After bootstrap:
```
Checking if backend is bootstrapped...
  ✓ config.json found
  ✓ venv exists
  ✓ Skipping bootstrap

Starting backend server...
  ✓ Backend ready in 5 seconds

App ready for use!
```

## Distribution

### Code Signing (macOS)

```bash
# Sign the app
codesign --force --deep --sign "Developer ID Application: Your Name" \
  "Fish Morphometrics.app"

# Verify signature
codesign --verify --deep --verbose "Fish Morphometrics.app"

# Notarize for Gatekeeper
xcrun notarytool submit "Fish Morphometrics.dmg" \
  --apple-id "your@email.com" \
  --team-id "YOUR_TEAM_ID" \
  --password "app-specific-password"
```

### Creating DMG (macOS)

```bash
# Create distributable DMG
hdiutil create -volname "Fish Morphometrics" \
  -srcfolder "desktop/src-tauri/target/release/bundle/dmg/" \
  -ov -format UDZO \
  "FishMorphometrics-v0.1.0.dmg"
```

### Linux AppImage

AppImage is already created by Tauri build process:
```bash
ls desktop/src-tauri/target/release/bundle/appimage/*.AppImage
```

### Windows Installer

MSI installer is created by Tauri:
```bash
dir desktop\src-tauri\target\release\bundle\msi\*.msi
```

## User Installation

### macOS

1. **Download** `FishMorphometrics-v0.1.0.dmg`
2. **Mount** the DMG
3. **Drag** Fish Morphometrics.app to Applications
4. **First Launch**: Right-click → Open (to bypass Gatekeeper)
5. **Wait** 3-7 minutes for bootstrap (only once)

### Linux

1. **Download** `FishMorphometrics-v0.1.0.AppImage`
2. **Make executable**:
   ```bash
   chmod +x FishMorphometrics-v0.1.0.AppImage
   ```
3. **Run**:
   ```bash
   ./FishMorphometrics-v0.1.0.AppImage
   ```
4. **Wait** 3-7 minutes for bootstrap (only once)

### Windows

1. **Download** `FishMorphometrics-v0.1.0.msi`
2. **Double-click** to install
3. **Launch** from Start Menu
4. **Wait** 3-7 minutes for bootstrap (only once)

## System Requirements

### Minimum Requirements

- **OS**: macOS 11.0+, Windows 10+, Ubuntu 20.04+
- **RAM**: 4 GB (8 GB recommended)
- **Disk**: 5 GB free space
  - 100 MB for app
  - 2-3 GB for Python dependencies
  - 500 MB for model weights
  - 1-2 GB for user data
- **Internet**: Required for first launch (dependency download)

### Recommended

- **RAM**: 16 GB (for large batches)
- **CPU**: 4+ cores
- **GPU**: Not required (CPU inference is fast enough for desktop use)

## Troubleshooting

### Bootstrap Fails

**Issue**: First launch hangs or fails

**Check logs**:
```bash
# macOS/Linux
tail -f ~/Library/Application\ Support/FishMorph/logs/bootstrap.log

# Windows
type %APPDATA%\FishMorph\logs\bootstrap.log
```

**Common causes**:
1. **No internet**: Dependencies can't download
2. **Firewall**: Blocks pip/conda
3. **Antivirus**: Blocks venv creation
4. **Disk full**: Not enough space for dependencies

**Solution**:
```bash
# Delete and retry
rm -rf ~/Library/Application\ Support/FishMorph
# Re-launch app
```

### Backend Won't Start

**Check backend log**:
```bash
tail -f ~/Library/Application\ Support/FishMorph/logs/backend.log
```

**Common causes**:
1. **Port in use**: Another app using port 8008
2. **Corrupt venv**: Dependencies missing
3. **Model missing**: Download failed

**Solution**:
```bash
# Force re-bootstrap
rm ~/Library/Application\ Support/FishMorph/config.json
# Re-launch app
```

### App Crashes on Launch

**Check system console**:
```bash
# macOS
log show --predicate 'process == "Fish Morphometrics"' --last 5m

# Linux
journalctl -u fish-morphometrics

# Windows
Event Viewer → Application Logs
```

## Updates

### Backend Updates

To update just the backend without rebuilding the entire app:

1. **Update backend version** in `backend/pyproject.toml`
2. **Test locally**:
   ```bash
   conda activate cavfish310
   cd backend
   pip install -e . --upgrade
   python -m cavfish_backend serve --port 8008
   ```
3. **Rebuild app** with new backend
4. **Users**: Delete config.json to force re-bootstrap with new version

### Frontend Updates

Frontend updates require full app rebuild:
```bash
./build_self_bootstrap.sh
```

## Model Management

### Adding New Models

1. **Train model** and export weights
2. **Upload** to CDN:
   ```bash
   aws s3 cp best_model.pth s3://your-bucket/models/cavfish_v2_weights.pth \
     --acl public-read
   ```
3. **Calculate checksum**:
   ```bash
   sha256sum best_model.pth
   ```
4. **Update** `bootstrap_backend.py`:
   ```python
   model_url = "https://your-cdn.com/models/cavfish_v2_weights.pth"
   model_checksum = "abc123..."
   ```
5. **Rebuild app**

### Model Versioning

Store models with version in filename:
```
models/
├── cavfish_v1_species_a.pth
├── cavfish_v1_species_b.pth
└── cavfish_v2_unified.pth
```

Configure in bootstrap:
```python
self.model_files = {
    "species_a": {
        "url": "https://cdn.com/models/cavfish_v1_species_a.pth",
        "checksum": "abc123...",
    },
    "species_b": {
        "url": "https://cdn.com/models/cavfish_v1_species_b.pth",
        "checksum": "def456...",
    }
}
```

## Analytics & Monitoring

### Usage Logs

Collect anonymous usage stats:
```python
# In backend
import logging

logging.info(f"Inference completed: {n_images} images, {duration}s")
```

Logs location:
- macOS: `~/Library/Application Support/FishMorph/logs/backend.log`
- Linux: `~/.local/share/FishMorph/logs/backend.log`
- Windows: `%APPDATA%\FishMorph\logs\backend.log`

### Error Reporting

Integrate Sentry or similar:
```python
# backend/api/app.py
import sentry_sdk

sentry_sdk.init(
    dsn="your-sentry-dsn",
    environment="production"
)
```

## Performance Optimization

### Reduce First Launch Time

1. **Pre-bundle common deps**: Include numpy, scipy in app
2. **Optimize model size**: Quantize or prune weights
3. **CDN placement**: Use geographically distributed CDN
4. **Parallel downloads**: Download deps and models concurrently

### Runtime Performance

1. **Model caching**: Keep model in memory between inferences
2. **Batch processing**: Process multiple images together
3. **Thread pool**: Use multiple CPU cores
4. **Image preprocessing**: Optimize resize/normalization

## Security Checklist

- [ ] Pin all dependency versions
- [ ] Verify model checksums
- [ ] Sign app with valid certificate
- [ ] Use HTTPS for model downloads
- [ ] Validate all user file inputs
- [ ] Sandbox file system access
- [ ] Log security events
- [ ] Keep dependencies up-to-date
- [ ] Regular security audits

## Support

### Documentation
- Architecture: `SELF_BOOTSTRAP_ARCHITECTURE.md`
- API Reference: `backend/api/README.md`
- User Guide: `docs/USER_GUIDE.md`

### Contact
- Issues: https://github.com/your-org/cavfish-inference/issues
- Email: support@yourorg.com
- Discord: https://discord.gg/yourserver

---

**Last Updated**: 2026-01-25  
**Version**: 0.1.0  
**Architecture**: Self-Bootstrapping
