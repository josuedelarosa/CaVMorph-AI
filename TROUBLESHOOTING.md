# First Run Setup - Troubleshooting Guide

## Quick Diagnostics

If the app fails during first-run setup, check these in order:

### 1. Is Conda Installed?

```bash
which conda
# Should return a path like: /Users/username/miniforge3/bin/conda
```

If not found, install Miniforge:
```bash
brew install --cask miniforge
```

### 2. Can We Create the Environment?

```bash
conda create -n cavfish310_test -c conda-forge python=3.10 -y
conda activate cavfish310_test
python --version  # Should show Python 3.10.x
conda env remove -n cavfish310_test -y
```

### 3. Test the Setup Script Manually

```bash
cd /Users/josuedelarosa/Documents/BIVL2ab/projects/cavfish-inference/desktop
python setup_first_run.py --backend-dir ../backend
```

Watch for errors in the output. The script reports progress as JSON.

## Common Issues

### Issue: "Conda not found"

**Symptom:** Setup fails immediately with "conda not found" error.

**Solution:**
```bash
# Install Miniforge
brew install --cask miniforge

# Verify installation
which conda
conda --version
```

### Issue: "numpy version conflict"

**Symptom:** Import errors mentioning numpy compatibility

**Solution:**
```bash
conda activate cavfish310
python -m pip uninstall -y numpy
conda install -c conda-forge -y "numpy<2"
python -c "import numpy; print(numpy.__version__)"  # Should be < 2.0
```

### Issue: "mmcv installation failed"

**Symptom:** Setup fails at mmcv==2.1.0 installation

**Root causes:**
1. mmengine not installed first
2. PyTorch not installed via conda
3. Build tools missing

**Solution:**
```bash
conda activate cavfish310

# Verify mmengine is installed
python -c "import mmengine; print(mmengine.__version__)"  # Should be 0.10.7

# Verify PyTorch is installed
python -c "import torch; print(torch.__version__)"

# Retry mmcv install
mim install "mmcv==2.1.0"
```

### Issue: "mmpose import error"

**Symptom:** `ImportError: cannot import name 'mmpose'`

**Solution:**
```bash
conda activate cavfish310

# Check if mmpose is installed
pip list | grep mmpose

# If missing, reinstall from source
cd /tmp
git clone https://github.com/open-mmlab/mmpose.git
cd mmpose
python -m pip install -r requirements.txt
python -m pip install -e .

# Verify
python -c "import mmpose; print(mmpose.__version__)"
```

### Issue: "Model weights download failed"

**Symptom:** Setup completes but model files are missing

**Location:** `~/Library/Application Support/FishMorph/models/cavfish_v1/`

**Solution:**
1. Check if the model URL is configured correctly in `setup_first_run.py`
2. Download manually and place in the correct location:

```bash
cd ~/Library/Application\ Support/FishMorph/models/cavfish_v1/
# Download your weights.pth file here
# Or copy from your training location
cp /path/to/your/weights.pth ./weights.pth
```

### Issue: "Backend server won't start"

**Symptom:** App opens but shows "Backend connection failed"

**Diagnosis:**
```bash
# Check if environment exists
conda env list | grep cavfish310

# Activate and test imports
conda activate cavfish310
python -c "import torch, mmpose, mmcv, fastapi; print('All imports OK')"

# Try running backend manually
cd ~/Library/Application\ Support/FishMorph/backend
python -m cavfish_backend.server
```

### Issue: "Permission denied" errors

**Symptom:** Setup fails with permission errors

**Solution:**
```bash
# Fix app data directory permissions
chmod -R u+w ~/Library/Application\ Support/FishMorph/

# Try setup again
```

### Issue: "Timeout during installation"

**Symptom:** Setup fails with "Command timed out" error

**Root cause:** Slow network or package mirrors

**Solution:**
Edit `setup_first_run.py` and increase timeout values:

```python
# Line ~230 (PyTorch install)
timeout=600  # Change to 1200 for slower connections

# Line ~260 (mmcv install)
timeout=600  # Change to 1200 for slower connections
```

## Debugging the Setup Process

### Enable Verbose Logging

The setup script logs to: `~/Library/Application Support/FishMorph/logs/bootstrap.log`

To watch setup in real-time:
```bash
tail -f ~/Library/Application\ Support/FishMorph/logs/bootstrap.log
```

### Check Setup Status

```bash
# Check if setup completed
cat ~/Library/Application\ Support/FishMorph/config.json

# Should show:
# {
#   "setup_complete": true,
#   "conda_env": "cavfish310",
#   ...
# }
```

### Manual Verification

Test each component individually:

```bash
conda activate cavfish310

# 1. Python version
python --version  # Should be 3.10.x

# 2. Core packages
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import mmengine; print(f'mmengine: {mmengine.__version__}')"
python -c "import mmcv; print(f'mmcv: {mmcv.__version__}')"
python -c "import mmpose; print(f'mmpose: {mmpose.__version__}')"

# 3. Backend packages
python -c "import fastapi; print('FastAPI OK')"
python -c "import uvicorn; print('Uvicorn OK')"
python -c "import cv2; print('OpenCV OK')"

# 4. Backend module
python -c "from cavfish import infer; print('Cavfish module OK')"
```

## Clean Reinstall

If all else fails, start fresh:

```bash
# 1. Remove the environment
conda env remove -n cavfish310 -y

# 2. Remove app data
rm -rf ~/Library/Application\ Support/FishMorph

# 3. Run setup again (via app or manually)
cd /Users/josuedelarosa/Documents/BIVL2ab/projects/cavfish-inference/desktop
python setup_first_run.py --backend-dir ../backend
```

## Performance Optimization

### Faster Installation

Use mamba instead of conda for faster package resolution:

```bash
brew install --cask miniforge  # Comes with mamba

# Then use mamba in setup_first_run.py:
# Replace: conda install ...
# With: mamba install ...
```

### Reduce Download Size

The setup downloads:
- PyTorch CPU (~200MB)
- mmcv (~100MB)
- mmpose source (~50MB)
- Model weights (~1GB)

Total: ~1.35GB

To reduce:
1. Cache packages between installations
2. Host model weights on a faster CDN
3. Use a local conda package cache

## Getting Help

When reporting issues, include:

1. **System Info:**
```bash
sw_vers  # macOS version
python --version
conda --version
```

2. **Setup Log:**
```bash
cat ~/Library/Application\ Support/FishMorph/logs/bootstrap.log
```

3. **Environment Info (if created):**
```bash
conda activate cavfish310
conda list
```

4. **Error Message:** Exact error text from the app or terminal

## Advanced Debugging

### Test Installation Script Isolated

```bash
# Create a test environment
conda create -n test_install python=3.10 -y
conda activate test_install

# Run each step from install_reference.sh manually
# This helps identify which specific step fails
```

### Check Network/Proxy Issues

```bash
# Test conda channels
conda search pytorch -c pytorch

# Test pip access
python -m pip install --dry-run openmim

# Test GitHub access
git clone --depth 1 https://github.com/open-mmlab/mmpose.git /tmp/test_clone
```

### Inspect Setup Script Output

The setup script outputs JSON for progress tracking:

```json
{"type": "progress", "step": 2, "message": "Installing PyTorch...", "level": "info"}
{"type": "progress", "step": 2, "message": "PyTorch installed successfully", "level": "success"}
{"type": "complete"}
```

If you see `{"type": "error", "message": "..."}`, that's the failure point.

## Reference: Working Installation

A successful installation should result in:

```bash
conda activate cavfish310
pip list | grep -E "(torch|mmcv|mmpose|mmengine|fastapi)"

# Should show:
# mmcv                    2.1.0
# mmengine                0.10.7
# mmpose                  1.3.x (or similar)
# mmpretrain              1.2.0
# torch                   2.x.x+cpu
# torchvision             0.x.x+cpu
# fastapi                 0.x.x
```

Environment size: ~3-4GB
Setup time: ~10-15 minutes (first run)
Subsequent starts: ~5-10 seconds (just activating env)
