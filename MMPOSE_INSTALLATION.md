# MMPose Installation Sequence

## Overview

This document explains the exact installation sequence used for setting up the cavfish-inference environment with mmpose and all its dependencies. The order of operations is **critical** and must be followed exactly.

## Why This Specific Sequence?

The mmpose ecosystem has complex dependencies with specific version requirements:
- **numpy** must be `<2.0` for mmcv compatibility
- **PyTorch** must be installed via conda (not pip) for proper binaries
- **mmcv** has strict version requirements with mmengine
- **chumpy** must be installed after PyTorch to avoid conflicts
- **mmpose** must be installed from source in editable mode

## Installation Sequence

The installation is broken down into these steps:

### Step 1: Create Conda Environment

```bash
conda create -n cavfish310 -c conda-forge python=3.10 pip -y
conda activate cavfish310
```

This creates a clean Python 3.10 environment with pip from conda-forge.

### Step 2: Upgrade Core Python Tools

```bash
python -m pip install -U pip setuptools wheel
```

Ensures we have the latest pip, setuptools, and wheel for proper package installation.

### Step 3: Force Reinstall numpy<2

```bash
python -m pip uninstall -y numpy || true
conda install -c conda-forge -y "numpy<2"
```

**Critical:** Uninstall any existing numpy, then install numpy<2 via conda (not pip). mmcv requires numpy<2.

### Step 4: Install xtcocotools

```bash
python -m pip install xtcocotools
```

Required for COCO dataset format support (used by mmpose).

### Step 5: Install PyTorch via Conda

```bash
conda install pytorch torchvision cpuonly -c pytorch -y
```

**Critical:** PyTorch must be installed via conda (not pip) to get proper CPU binaries. Using cpuonly for smaller size and faster install.

### Step 6: Install OpenMIM

```bash
python -m pip install -U openmim
```

OpenMIM is the package manager for mmlab projects. Required for installing mmengine, mmcv, and mmpretrain.

### Step 7: Install fsspec

```bash
python -m pip install fsspec
```

Filesystem spec - required for mmengine file operations.

### Step 8: Install mmengine

```bash
mim install "mmengine==0.10.7"
```

**Version locked:** Must use exactly 0.10.7 for compatibility with mmcv 2.1.0.

### Step 9: Install mmcv

```bash
mim install "mmcv==2.1.0"
```

**Version locked:** Must use exactly 2.1.0 for compatibility with mmpose and mmengine.

### Step 10: Install chumpy

```bash
conda install -c conda-forge -y chumpy
```

Chumpy is a numerical optimization library. Must be installed after PyTorch to avoid conflicts.

### Step 11: Clone and Install mmpose

```bash
git clone https://github.com/open-mmlab/mmpose.git
cd mmpose
python -m pip install -r requirements.txt
python -m pip install -e .
```

**Critical:** mmpose must be installed from source in editable mode (`-e`). This allows:
- Custom modifications if needed
- Proper integration with the codebase
- Access to all mmpose features and configs

### Step 12: Install mmpretrain

```bash
mim install "mmpretrain==1.2.0"
```

**Version locked:** Used for pretrained backbones in pose estimation models.

## Integration with First-Run Setup

The above sequence is implemented in two places:

1. **`desktop/setup_first_run.py`** - The source script
2. **`desktop/src-tauri/setup_first_run.py`** - Bundled with the Tauri app

When the app is built and distributed, the setup script is included in the app bundle. On first launch, if the conda environment doesn't exist, the app will:

1. Detect/find conda installation (looks for Miniforge, Miniconda, Anaconda)
2. Execute the installation sequence above
3. Download model weights
4. Copy backend files to app data directory
5. Save configuration

## Modified Functions

### `step_install_pytorch()`

Updated to:
- Use `python -m pip` instead of direct pip calls
- Explicitly uninstall numpy before conda install
- Use exact conda flags: `-c conda-forge -y "numpy<2"`
- Install PyTorch with exact channel: `-c pytorch -y`

### `step_install_mm_packages()`

Updated to:
- Use `python -m pip` for consistency
- Add explicit cwd parameter for mmpose install
- Add better error handling and status reporting
- Follow exact order: openmim → fsspec → mmengine → mmcv → chumpy → mmpose → mmpretrain

## Building the App

To build the app with the updated installation sequence:

```bash
# From project root
./build.sh

# Or manually:
cd desktop
npm install
npm run build
npm run tauri build
```

The DMG will be created in: `desktop/src-tauri/target/release/bundle/dmg/`

## Testing the Setup

To test the installation sequence locally:

```bash
# Remove existing environment (if testing)
conda env remove -n cavfish310

# Run setup script manually
cd desktop
python setup_first_run.py --backend-dir ../backend
```

This will execute the same sequence the app uses on first run.

## Troubleshooting

### numpy version conflicts

If you see errors about numpy versions:
```bash
conda activate cavfish310
python -m pip uninstall -y numpy
conda install -c conda-forge -y "numpy<2"
```

### mmcv build failures

If mmcv fails to install:
- Ensure PyTorch is installed first via conda
- Ensure mmengine==0.10.7 is installed
- Try: `mim install --no-cache mmcv==2.1.0`

### mmpose import errors

If mmpose can't be imported:
```bash
cd /tmp/mmpose_build/mmpose
conda activate cavfish310
python -m pip install -e .
```

### Conda not found

The app looks for conda in these locations:
- `~/miniforge3/bin/conda`
- `~/mambaforge/bin/conda`
- `~/miniconda3/bin/conda`
- `~/anaconda3/bin/conda`
- `/opt/homebrew/Caskroom/miniforge/base/bin/conda`
- System PATH

To install Miniforge (recommended):
```bash
brew install --cask miniforge
```

## Environment Variables

You can customize the setup with these environment variables:

- `FISH_MODEL_URL` - URL for model weights download
- `FISH_MODEL_SHA256` - Optional checksum for model verification

Example:
```bash
export FISH_MODEL_URL="https://your-server.com/weights.pth"
export FISH_MODEL_SHA256="abc123..."
```

## Performance Notes

- Total install time: ~10-15 minutes (depending on network speed)
- Model download: ~1GB (~2-5 minutes depending on connection)
- Environment size: ~3-4GB after complete installation
- First launch after install: ~30 seconds (loading models into memory)

## Version Compatibility Matrix

| Package | Version | Why This Version |
|---------|---------|------------------|
| Python | 3.10 | Required by mmpose and mmcv |
| numpy | <2.0 | mmcv not compatible with numpy 2.x |
| torch | latest (cpu) | Latest CPU build from conda |
| mmengine | 0.10.7 | Required by mmcv 2.1.0 |
| mmcv | 2.1.0 | Required by mmpose |
| mmpretrain | 1.2.0 | Compatible with mmpose |

## Changes Made

### Files Modified

1. **`desktop/setup_first_run.py`**
   - Updated `step_install_pytorch()` to match exact sequence
   - Updated `step_install_mm_packages()` to match exact sequence
   - Changed pip calls to `python -m pip` for consistency
   - Added explicit conda channel flags

2. **`desktop/src-tauri/setup_first_run.py`**
   - Copied from updated desktop version
   - Bundled with Tauri app during build

### Key Changes

- ✅ Use `python -m pip` instead of direct `pip` calls
- ✅ Force numpy uninstall before reinstall
- ✅ Install numpy via conda-forge (not pip)
- ✅ Explicit conda channel flags: `-c conda-forge`, `-c pytorch`
- ✅ Install mmpose with explicit `cwd` parameter
- ✅ Better error handling and progress reporting
- ✅ Exact order preserved as in working manual installation

## Next Steps

After these changes, your app build will:

1. Bundle the updated setup script
2. On first launch, execute the exact installation sequence
3. Create a working mmpose environment identical to your manual setup
4. Download models and be ready to run

To rebuild and test:

```bash
./build.sh
# Install the DMG from desktop/src-tauri/target/release/bundle/dmg/
# Launch the app - it will run first-time setup automatically
```
