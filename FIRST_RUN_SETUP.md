# Fish Morphometrics - First Run Setup Guide

This document explains how the first-run setup works and how to troubleshoot common issues.

## How It Works

When you first launch Fish Morphometrics, the app detects that the required Python environment is not yet set up. It will automatically:

1. **Check System** - Verify that conda (Miniforge) is installed
2. **Create Environment** - Set up a Python 3.10 environment named `cavfish310`
3. **Install PyTorch** - Install PyTorch with MPS support for Apple Silicon Macs
4. **Install MM Packages** - Install mmpose, mmengine, and mmcv using `mim`
5. **Install Dependencies** - Install FastAPI, uvicorn, OpenCV, and other packages
6. **Download Model** - Download the ~1GB model weights file
7. **Finalize** - Verify installation and save configuration

This process takes approximately **10-20 minutes** depending on your internet speed.

## Prerequisites

### Miniforge (conda)

You must have Miniforge installed before launching the app. Install it via Homebrew:

```bash
brew install --cask miniforge
```

Or download directly from: https://github.com/conda-forge/miniforge/releases

After installation, restart your terminal or computer.

### Verify Installation

```bash
# Check conda is available
which conda

# Should output something like:
# /Users/yourname/miniforge3/bin/conda
```

## Setup UI

The setup screen shows:

- **Progress Steps** - 7 steps with checkmarks when complete
- **Log Output** - Real-time output from the installation process
- **Status Bar** - Overall progress percentage
- **Action Buttons** - Retry (on error) or Start Application (when complete)

## Data Locations

After setup, the following directories are created:

```
~/Library/Application Support/FishMorph/
├── config.json          # App configuration
├── backend/             # Python backend source
├── models/
│   └── cavfish_v1/
│       ├── weights.pth  # Model weights (~1GB)
│       ├── meta.json    # Keypoint definitions
│       └── *.py         # Config files
└── logs/                # Setup and runtime logs
```

## Conda Environment

The setup creates a conda environment with these key packages:

| Package | Version | Purpose |
|---------|---------|---------|
| Python | 3.10 | Runtime |
| PyTorch | Latest | Deep learning framework |
| mmpose | ≥1.0.0 | Pose estimation library |
| mmengine | Latest | MM ecosystem engine |
| mmcv | ≥2.0.0 | MM computer vision library |
| FastAPI | Latest | Backend API server |
| uvicorn | Latest | ASGI server |
| OpenCV | Latest | Image processing |

To activate this environment manually:

```bash
conda activate cavfish310
```

## Troubleshooting

### "Conda not found"

**Problem**: The app cannot find your conda installation.

**Solutions**:
1. Install Miniforge: `brew install --cask miniforge`
2. Restart your computer after installation
3. Verify with: `which conda`

### Setup Stuck at "Installing mmpose"

**Problem**: The mmpose installation takes a long time.

**This is normal!** The mmpose package is large and has many dependencies. It can take 5-10 minutes.

### Setup Fails with Network Error

**Problem**: Download failed or timeout error.

**Solutions**:
1. Check your internet connection
2. Disable VPN if using one
3. Click "Retry Setup" button
4. If on corporate network, you may need to configure proxy

### Disk Space Error

**Problem**: Not enough disk space.

**Solution**: Ensure you have at least 5GB free space:
- Conda environment: ~2GB
- Model weights: ~1GB
- App and dependencies: ~1GB

### Python Package Conflicts

**Problem**: Package installation fails with dependency errors.

**Solutions**:
1. The setup will try to remove and recreate the environment
2. Click "Retry Setup"
3. If persists, manually remove the environment:
   ```bash
   conda env remove -n cavfish310
   ```

### Model Download Failed

**Problem**: Cannot download model weights.

**Temporary Workaround**: 
If you have the weights file from another source, copy it to:
```
~/Library/Application Support/FishMorph/models/cavfish_v1/weights.pth
```

## Re-running Setup

To force a fresh setup:

1. Remove the app data directory:
   ```bash
   rm -rf ~/Library/Application\ Support/FishMorph
   ```

2. Remove the conda environment:
   ```bash
   conda env remove -n cavfish310
   ```

3. Launch the app again

## Manual Environment Setup

If automatic setup fails, you can set up the environment manually:

```bash
# Create environment
conda create -n cavfish310 python=3.10 -y
conda activate cavfish310

# Install PyTorch (for Apple Silicon)
pip install torch torchvision torchaudio

# Install MM packages
pip install -U openmim
mim install mmengine
mim install mmcv>=2.0.0
mim install mmpose>=1.0.0
mim install mmpretrain>=1.0.0

# Install other dependencies
pip install fastapi uvicorn[standard] opencv-python numpy Pillow pydantic

# Create app data directory
mkdir -p ~/Library/Application\ Support/FishMorph/models/cavfish_v1

# Copy model files (you need to obtain these)
# cp /path/to/weights.pth ~/Library/Application\ Support/FishMorph/models/cavfish_v1/
```

## Getting Help

If setup continues to fail:

1. Check the log output in the setup UI
2. Click "View Full Logs" to open the logs directory
3. Check for error messages in the logs
4. Report issues with the log content

## Technical Details

### Setup Script Location

The setup script is bundled with the app:
- In app bundle: `Fish Morphometrics.app/Contents/Resources/setup_first_run.py`

### Setup Script Arguments

The setup script accepts:
- `--backend-dir`: Path to backend source code
- `--bundled-model`: Path to bundled model weights (if included)

### Configuration File

The `config.json` contains:
```json
{
  "setup_complete": true,
  "conda_env": "cavfish310",
  "conda_path": "/path/to/conda",
  "backend_dir": "/path/to/backend",
  "models_dir": "/path/to/models",
  "version": "0.1.0"
}
```

The app checks this file on startup to determine if setup is needed.
