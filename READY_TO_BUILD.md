# ✅ Setup Script Updated - Ready to Build

## What Was Done

Your `setup_first_run.py` script has been updated to match **exactly** the installation sequence that works on your machine.

## Changes Summary

### Core Changes

1. ✅ Updated `step_install_pytorch()` to use your exact sequence
2. ✅ Updated `step_install_mm_packages()` to use your exact sequence  
3. ✅ All pip commands now use `python -m pip` for consistency
4. ✅ Conda channels explicitly specified: `-c conda-forge`, `-c pytorch`
5. ✅ numpy forced reinstall from conda-forge (not pip)
6. ✅ mmpose installed from source in editable mode
7. ✅ All version locks preserved: mmengine==0.10.7, mmcv==2.1.0, mmpretrain==1.2.0

### Files Modified

- [desktop/setup_first_run.py](desktop/setup_first_run.py) - Source script
- [desktop/src-tauri/setup_first_run.py](desktop/src-tauri/setup_first_run.py) - Bundled version (identical)

### Files Created

- [MMPOSE_INSTALLATION.md](MMPOSE_INSTALLATION.md) - Detailed installation documentation
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Troubleshooting guide
- [SETUP_UPDATES_SUMMARY.md](SETUP_UPDATES_SUMMARY.md) - Complete change documentation
- [install_reference.sh](install_reference.sh) - Manual installation reference script
- [test_setup_config.py](test_setup_config.py) - Validation test script

## ✅ Validation Results

All tests passed:

```
✓ PASS: Import
✓ PASS: Configuration  
✓ PASS: Functions
✓ PASS: Installation Sequence
```

The setup script is correctly configured!

## Next Steps

### 1. Build the App

```bash
./build.sh
```

This will:
- Install frontend dependencies
- Build the Vue/Tauri app
- Bundle the updated setup script
- Create a DMG in `desktop/src-tauri/target/release/bundle/dmg/`

### 2. Test First-Run Setup

Option A: **Test via the built app** (recommended)
```bash
# Install the DMG from desktop/src-tauri/target/release/bundle/dmg/
# Launch the app - it will automatically run first-time setup
```

Option B: **Test the script directly** (for debugging)
```bash
cd desktop
python3 setup_first_run.py --backend-dir ../backend
```

### 3. Monitor Installation

Watch the setup progress:
```bash
tail -f ~/Library/Application\ Support/FishMorph/logs/bootstrap.log
```

### 4. Verify Installation

After setup completes:
```bash
conda activate cavfish310

# Check all packages
python -c "import torch; print(f'torch: {torch.__version__}')"
python -c "import mmcv; print(f'mmcv: {mmcv.__version__}')"
python -c "import mmengine; print(f'mmengine: {mmengine.__version__}')"
python -c "import mmpose; print(f'mmpose: {mmpose.__version__}')"

# Check backend
python -c "from cavfish import infer; print('Backend OK')"
```

## Installation Sequence (Your Exact Order)

The script now follows this exact sequence:

1. Create conda environment: `cavfish310` with Python 3.10
2. Upgrade pip, setuptools, wheel via `python -m pip`
3. **Force uninstall numpy** (critical for mmcv compatibility)
4. Install numpy<2 via `conda install -c conda-forge`
5. Install xtcocotools
6. Install PyTorch via `conda install -c pytorch pytorch torchvision cpuonly`
7. Install OpenMIM via `python -m pip`
8. Install fsspec
9. Install mmengine==0.10.7 via `mim install`
10. Install mmcv==2.1.0 via `mim install`
11. Install chumpy via `conda install -c conda-forge`
12. Clone mmpose from GitHub
13. Install mmpose requirements
14. **Install mmpose in editable mode** (`-e`)
15. Install mmpretrain==1.2.0 via `mim install`

## Expected Timing

- **First run setup**: 10-15 minutes
- **Model download**: 2-5 minutes (1GB, if configured)
- **Subsequent launches**: 5-10 seconds (just env activation)

## Troubleshooting

If you encounter any issues:

1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common problems
2. View logs: `~/Library/Application Support/FishMorph/logs/bootstrap.log`
3. Verify conda: `which conda`
4. Try clean reinstall:
   ```bash
   conda env remove -n cavfish310 -y
   rm -rf ~/Library/Application\ Support/FishMorph
   # Then launch app again
   ```

## Configuration

You can customize setup with environment variables:

```bash
export FISH_MODEL_URL="https://your-server.com/weights.pth"
export FISH_MODEL_SHA256="your_sha256_checksum_here"
```

Then build/run the app.

## Distribution

When you distribute the built DMG:

1. Users install the app
2. On first launch, they see a setup progress screen
3. The app automatically:
   - Detects/finds conda
   - Creates the environment
   - Installs all dependencies (in the correct order)
   - Downloads model weights
   - Sets up the backend
4. Setup is **one-time only** (~15 minutes)
5. Subsequent launches are fast (~5-10 seconds)

## Requirements for Users

Users need:
- **macOS** (Apple Silicon or Intel)
- **Conda/Miniforge** installed (app will detect it)
  - If not installed: `brew install --cask miniforge`
- **~4GB disk space** for the environment
- **~1GB for model weights** (downloaded automatically)
- **Internet connection** for first-run setup

## Support

- Full installation docs: [MMPOSE_INSTALLATION.md](MMPOSE_INSTALLATION.md)
- Troubleshooting: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Change details: [SETUP_UPDATES_SUMMARY.md](SETUP_UPDATES_SUMMARY.md)
- Manual reference: [install_reference.sh](install_reference.sh)

## Quick Commands

```bash
# Build the app
./build.sh

# Test setup directly
cd desktop && python3 setup_first_run.py --backend-dir ../backend

# Validate configuration
python3 test_setup_config.py

# Watch logs
tail -f ~/Library/Application\ Support/FishMorph/logs/bootstrap.log

# Verify environment
conda activate cavfish310 && python -c "import torch, mmpose, mmcv; print('All OK')"

# Clean reinstall
conda env remove -n cavfish310 -y && rm -rf ~/Library/Application\ Support/FishMorph
```

---

## 🎉 You're Ready!

Your setup script now uses the **exact installation sequence** from your working environment. Just run `./build.sh` to create the distributable DMG!

The app will handle the complex mmpose installation automatically for your users. 🚀
