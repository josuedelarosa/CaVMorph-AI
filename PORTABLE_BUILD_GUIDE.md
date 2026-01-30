# Portable Build Guide - Fish Morphometrics Desktop App

## Overview
This guide explains how to build a truly portable, production-ready desktop application for fish morphometrics that users can install with zero technical setup.

## What Changed for Portability

### 1. PyInstaller Configuration (backend/api/cli.spec)
- **Changed from**: One-file bundle (all libraries in single executable)
- **Changed to**: One-folder bundle (executable + dependencies folder)
- **Why**: macOS requires dynamic libraries to be properly linked. One-folder mode creates a portable bundle with all dependencies included.

### 2. Build Script (build.sh)
- Creates `fish_backend/` folder containing the executable and all dependencies
- Creates a wrapper script `fish_backend-aarch64-apple-darwin` that launches the bundled backend
- The wrapper ensures proper library paths are set

### 3. Tauri Configuration (desktop/src-tauri/tauri.conf.json)
- Moved backend from `externalBin` to `resources`
- Backend folder is bundled as app resource, not as sidecar
- This ensures all dependencies travel with the app

### 4. Rust Launch Code (desktop/src-tauri/src/main.rs)
- Uses `app.path_resolver().resource_dir()` to find bundled backend
- Launches backend using `std::process::Command` with proper environment
- Monitors backend output for debugging

## Build Process

### Prerequisites
```bash
# 1. Conda environment with all dependencies
conda activate cavfish310

# 2. Install PyInstaller if not already installed
pip install pyinstaller

# 3. Ensure Rust/Cargo is available
source ~/.cargo/env
```

### Build Steps
```bash
# Run the automated build script
./build.sh
```

This will:
1. ✅ Activate conda environment
2. ✅ Check prerequisites (Node.js, Python, Cargo)
3. ✅ Build backend with PyInstaller (onedir mode)
4. ✅ Create wrapper script for macOS
5. ✅ Build frontend with Vite
6. ✅ Build Tauri app bundle

### Output
```
desktop/src-tauri/target/release/bundle/
├── dmg/
│   └── Fish Morphometrics_0.1.0_aarch64.dmg    # macOS installer
└── macos/
    └── Fish Morphometrics.app/                  # macOS app bundle
        └── Contents/
            ├── MacOS/
            │   ├── Fish Morphometrics           # Main executable
            │   └── fish_backend-aarch64-apple-darwin  # Backend wrapper
            └── Resources/
                └── fish_backend/                # Backend bundle
                    ├── fish_backend             # Python executable
                    ├── _internal/               # All dependencies
                    ├── models/                  # ML models
                    └── phenolosses/             # Config files
```

## Testing the Build

### Development Mode
```bash
cd desktop/src-tauri
cargo tauri dev
```
- Uses Python backend from conda environment
- Hot reload enabled
- Fast iteration

### Production Mode
```bash
# Build the app
./build.sh

# Test the built app
open "desktop/src-tauri/target/release/bundle/macos/Fish Morphometrics.app"
```

### Debugging Production Issues
```bash
# Run from terminal to see backend logs
cd "/Applications/Fish Morphometrics.app/Contents/MacOS"
./Fish\ Morphometrics
```

Look for:
- `[Tauri] Starting production backend on port XXXXX`
- `[Backend] INFO: Started server process...`
- `[Backend] INFO: Uvicorn running on http://127.0.0.1:XXXXX`

## Distribution

### For macOS Users
1. **DMG Installer** (Recommended)
   - File: `Fish Morphometrics_0.1.0_aarch64.dmg`
   - Users drag to Applications folder
   - Double-click to run
   - **No Python, CUDA, or ML libraries required**

2. **.app Bundle**
   - File: `Fish Morphometrics.app`
   - Can be zipped and shared directly
   - Users unzip to Applications
   - Same zero-dependency experience

### System Requirements
- **macOS**: 11.0+ (Big Sur or later)
- **CPU**: Apple Silicon (M1/M2/M3) or Intel
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 2GB free space

### User Experience
1. Download `Fish Morphometrics_0.1.0_aarch64.dmg`
2. Open DMG, drag app to Applications
3. Open "Fish Morphometrics" from Applications
4. Grant file access permissions if prompted
5. **That's it!** No Python, no terminal, no setup.

## Features Included

### Multi-Profile Support
- Create custom fish profiles (e.g., "Standard Fish", "Compressed Fish")
- Select which keypoints to include per profile
- Each profile can have different phenotype calculations
- Settings persist across app restarts

### Batch Processing
- Upload folders of fish images per profile
- Process multiple profiles simultaneously
- Real-time progress tracking
- Preview results for each image

### Export Options
- **CSV**: All keypoints and phenotypes in spreadsheet format
- **JSON**: Complete data with metadata for further analysis
- **Annotated Images**: Visual overlays of keypoints and measurements

### UI Highlights
- 3-column layout: Image preview | Details | Image list
- Dark/Light mode toggle
- Profile-specific image filtering
- Interactive canvas with keypoint visualization
- Scrollable image list with thumbnails

## Troubleshooting

### Backend Fails to Start
**Symptoms**: App shows "Backend: Connecting..." forever

**Debug**:
```bash
# Run backend manually
cd "/Applications/Fish Morphometrics.app/Contents/MacOS"
./fish_backend/fish_backend --port 8008
```

**Common Issues**:
- Missing system libraries (check stderr for "Library not loaded")
- Port already in use (try different port)
- Permissions issue (check Console.app logs)

### Images Not Loading
**Symptoms**: "path not allowed on the configured scope"

**Fix**: Check `tauri.conf.json` fs.scope includes user directories:
```json
"scope": ["$APPCONFIG", "$APPCONFIG/**", "$HOME", "$HOME/**"]
```

### CSV Export Fails
**Symptoms**: "TypeError: float() argument must be a string or a real number"

**Fix**: Ensure keypoints data structure is correct (arrays, not nested arrays)

## Development Notes

### Hot Reload Issues
If Tauri keeps recompiling:
```bash
# Stop watching tauri.conf.json
cd desktop/src-tauri
echo "tauri.conf.json" >> .gitignore  # If not already ignored
```

### Profile Configuration Storage
- Location: `~/Library/Application Support/com.cavfish.morphometrics/fish_morphometrics_config.json`
- Format: JSON with profiles array
- Persists across app launches

### Backend API
- Runs on dynamic port (8008 or next available)
- Endpoints:
  - `GET /model/info` - Model metadata
  - `POST /predict/single` - Single image inference
  - `POST /export/csv` - CSV export
  - `POST /export/json` - JSON export
  - `POST /export/images` - Annotated images

## Next Steps

### For Users
1. Install the app from DMG
2. Create fish profiles in Settings (⚙️)
3. Upload image folders
4. Click "Analyze All"
5. Export results

### For Developers
1. Modify models in `models/` directory
2. Update phenotype pairs in backend config
3. Rebuild with `./build.sh`
4. Test in production mode
5. Distribute new DMG

## Credits
- **Architecture**: Tauri (Rust) + Vue 3 (Frontend) + FastAPI (Backend)
- **ML Stack**: PyTorch + MMPose + ViTPose
- **Packaging**: PyInstaller (onedir mode for portability)

---

**Version**: 0.1.0  
**Last Updated**: January 2025  
**Platform**: macOS (Apple Silicon + Intel)
