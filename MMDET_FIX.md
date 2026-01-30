# Quick Fix: Add mmdet to Existing Installation

## Problem
Your app crashes with: `ModuleNotFoundError: No module named 'mmdet'`

## Solution

If you already have the `cavfish310` environment set up, just add mmdet:

```bash
# Activate your environment
conda activate cavfish310

# Install mmdet (version 3.3.0)
mim install "mmdet==3.3.0"

# Verify installation
python -c "import mmdet; print(f'mmdet: {mmdet.__version__}')"
```

Then restart your app - it should work now!

## For Fresh Installation

The setup script has been updated to include mmdet. If you're doing a fresh install:

```bash
# Remove the old environment
conda env remove -n cavfish310 -y

# Remove app data
rm -rf ~/Library/Application\ Support/FishMorph

# Rebuild and reinstall the app
./build.sh
# Then install the new DMG
```

## What Changed

Added mmdet (MMDetection) to the installation sequence:

**Step 5** (new): `mim install "mmdet==3.3.0"`

This is installed after mmcv and before mmpose, as it's a required dependency for the cavfish backend.

## Verify Complete Installation

After adding mmdet, verify all packages:

```bash
conda activate cavfish310

# Core packages
python -c "import torch; print(f'torch: {torch.__version__}')"
python -c "import mmcv; print(f'mmcv: {mmcv.__version__}')"
python -c "import mmengine; print(f'mmengine: {mmengine.__version__}')"
python -c "import mmdet; print(f'mmdet: {mmdet.__version__}')"
python -c "import mmpose; print(f'mmpose: {mmpose.__version__}')"

# Backend module
python -c "from cavfish import infer; print('Backend OK')"
```

All should import successfully without errors.

## Updated Installation Sequence

The complete sequence now includes mmdet:

1. Create conda environment
2. Upgrade pip, setuptools, wheel
3. Uninstall/reinstall numpy<2
4. Install xtcocotools
5. Install PyTorch
6. Install OpenMIM
7. Install fsspec
8. Install mmengine==0.10.7
9. Install mmcv==2.1.0
10. **Install mmdet==3.3.0** ← NEW
11. Install chumpy
12. Clone and install mmpose
13. Install mmpretrain==1.2.0

---

**Quick command to fix your current environment:**
```bash
conda activate cavfish310 && mim install "mmdet==3.3.0"
```
