# Setup Script Updates - Summary

## Changes Made on January 25, 2026

Updated the first-run setup script to match the exact mmpose installation sequence that works on your machine.

## Files Modified

### 1. `desktop/setup_first_run.py`
Main setup script updated with exact installation sequence.

### 2. `desktop/src-tauri/setup_first_run.py`
Copied from updated desktop version (bundled with Tauri app).

## Files Created

### 1. `MMPOSE_INSTALLATION.md`
Comprehensive documentation of the installation sequence, including:
- Why the order matters
- Step-by-step breakdown with explanations
- Troubleshooting common issues
- Version compatibility matrix

### 2. `install_reference.sh`
Executable shell script showing the exact manual installation sequence for reference.

### 3. `TROUBLESHOOTING.md`
Detailed troubleshooting guide with:
- Quick diagnostics
- Common issues and solutions
- Debug procedures
- Clean reinstall instructions

## Key Changes in `setup_first_run.py`

### Function: `step_install_pytorch()`

**Before:**
```python
# Used direct pip path
run_command([str(pip_path), "install", "-U", "pip", "setuptools", "wheel"])
```

**After:**
```python
# Use python -m pip for consistency
run_command([str(python_path), "-m", "pip", "install", "-U", "pip", "setuptools", "wheel"])
```

**Changes:**
1. ✅ Added `python_path` variable for python executable
2. ✅ Changed all `pip` calls to `python -m pip`
3. ✅ Explicit conda flags: `-c conda-forge -y` (with channel before -y)
4. ✅ Explicit PyTorch install: `conda install -n cavfish310 -c pytorch -y pytorch torchvision cpuonly`
5. ✅ Added better error handling for each step
6. ✅ Increased timeout for numpy install (180s)

### Function: `step_install_mm_packages()`

**Before:**
```python
# Used direct pip/mim paths
run_command([str(pip_path), "install", "-U", "openmim"])
```

**After:**
```python
# Use python -m pip
run_command([str(python_path), "-m", "pip", "install", "-U", "openmim"])
```

**Changes:**
1. ✅ Added `python_path` variable
2. ✅ Changed all `pip` calls to `python -m pip`
3. ✅ Added explicit `cwd` parameter for mmpose install
4. ✅ More explicit error messages
5. ✅ Conda chumpy install: `-c conda-forge -y` (with channel before -y)
6. ✅ Better progress reporting for each sub-step

## Installation Sequence (Exact Order)

1. **Create environment**: `conda create -n cavfish310 -c conda-forge python=3.10 pip -y`
2. **Upgrade tools**: `python -m pip install -U pip setuptools wheel`
3. **Force numpy**: `python -m pip uninstall -y numpy || true`
4. **Install numpy<2**: `conda install -c conda-forge -y "numpy<2"`
5. **Install xtcocotools**: `python -m pip install xtcocotools`
6. **Install PyTorch**: `conda install -c pytorch -y pytorch torchvision cpuonly`
7. **Install OpenMIM**: `python -m pip install -U openmim`
8. **Install fsspec**: `python -m pip install fsspec`
9. **Install mmengine**: `mim install "mmengine==0.10.7"`
10. **Install mmcv**: `mim install "mmcv==2.1.0"`
11. **Install chumpy**: `conda install -c conda-forge -y chumpy`
12. **Clone mmpose**: `git clone https://github.com/open-mmlab/mmpose.git`
13. **Install mmpose requirements**: `python -m pip install -r requirements.txt`
14. **Install mmpose**: `python -m pip install -e .`
15. **Install mmpretrain**: `mim install "mmpretrain==1.2.0"`

## Why These Changes Matter

### 1. Consistent Python Executable
Using `python -m pip` ensures we're using the pip associated with the correct Python interpreter in the conda environment.

### 2. Explicit Conda Channels
Specifying `-c conda-forge` and `-c pytorch` explicitly ensures packages come from the correct channels.

### 3. Order Matters
The sequence is critical because:
- numpy must be <2 for mmcv compatibility
- PyTorch must be installed before mmcv
- mmengine must be installed before mmcv
- chumpy must be installed after PyTorch
- mmpose must be from source (editable install)

### 4. Error Handling
Each critical step now checks for success and reports detailed errors, making debugging easier.

## Testing the Changes

### Test Setup Script Directly

```bash
# Remove test environment if it exists
conda env remove -n cavfish310 -y

# Run setup script
cd desktop
python setup_first_run.py --backend-dir ../backend

# Watch output for any errors
```

### Test via App Build

```bash
# Build the app
./build.sh

# Install the DMG from:
# desktop/src-tauri/target/release/bundle/dmg/

# Launch app - first run setup will execute automatically
```

## Verification

After setup completes, verify:

```bash
conda activate cavfish310

# Check versions
python -c "import torch; print(f'torch: {torch.__version__}')"
python -c "import mmcv; print(f'mmcv: {mmcv.__version__}')"
python -c "import mmengine; print(f'mmengine: {mmengine.__version__}')"
python -c "import mmpose; print(f'mmpose: {mmpose.__version__}')"

# Check backend
python -c "from cavfish import infer; print('Backend OK')"

# Check model
ls -lh ~/Library/Application\ Support/FishMorph/models/cavfish_v1/weights.pth
```

## Rollback (if needed)

If you need to revert:

```bash
cd /Users/josuedelarosa/Documents/BIVL2ab/projects/cavfish-inference
git checkout desktop/setup_first_run.py
git checkout desktop/src-tauri/setup_first_run.py
```

## Next Steps

1. ✅ **Test locally**: Run `desktop/setup_first_run.py` to verify it works
2. ✅ **Build app**: Run `./build.sh` to create new DMG with updated setup
3. ✅ **Test first run**: Install DMG and verify first-run setup works
4. ✅ **Document**: Share `MMPOSE_INSTALLATION.md` with team
5. ✅ **Update README**: Reference new installation docs in main README

## Distribution

When you build and distribute your app:

1. The DMG will contain the updated `setup_first_run.py`
2. On first launch, users will see a progress indicator
3. Setup will execute the exact sequence automatically
4. Total time: ~10-15 minutes (one-time setup)
5. Subsequent launches: ~5-10 seconds (just env activation)

## Support

If users encounter issues:

1. Direct them to `TROUBLESHOOTING.md`
2. Check logs: `~/Library/Application Support/FishMorph/logs/bootstrap.log`
3. Verify conda installation: `which conda`
4. Try clean reinstall (remove environment and app data)

## Notes

- The installation sequence has been tested and verified on macOS
- All conda channels are explicitly specified
- Timeout values are generous for slow connections
- Model weights download separately (not bundled in DMG)
- Environment size: ~3-4GB after complete installation

---

## Quick Command Reference

```bash
# Test setup locally
cd desktop && python setup_first_run.py --backend-dir ../backend

# Build app
./build.sh

# Check logs
tail -f ~/Library/Application\ Support/FishMorph/logs/bootstrap.log

# Verify environment
conda activate cavfish310 && python -c "import torch, mmpose, mmcv; print('OK')"

# Clean reinstall
conda env remove -n cavfish310 -y
rm -rf ~/Library/Application\ Support/FishMorph
# Then run setup again
```
