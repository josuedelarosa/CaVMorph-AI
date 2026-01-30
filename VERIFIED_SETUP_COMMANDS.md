# Verified Setup Commands

These commands have been tested and verified to work for first-time setup of the CaVFish environment.

## Complete Setup Sequence

```bash
# 1. Create environment with Python 3.10 and pip
conda create -p ~/miniforge3/envs/cavfish310 python=3.10 pip -y

# 2. Activate environment
conda activate cavfish310

# 3. Upgrade pip and core tools
python -m pip install -U pip setuptools wheel

# 4. Install numpy<2 (important: must be <2)
python -m pip uninstall -y numpy || true
conda install -c conda-forge -y "numpy<2"

# 5. Install xtcocotools
python -m pip install xtcocotools

# 6. Install PyTorch with CPU-only support
conda install pytorch torchvision cpuonly -c pytorch -y

# 7. Install OpenMIM (MM ecosystem package manager)
python -m pip install -U openmim

# 8. Install fsspec (file system spec)
python -m pip install fsspec

# 9. Install mmengine (specific version)
mim install "mmengine==0.10.7"

# 10. Install mmcv (specific version)
mim install "mmcv==2.1.0"

# 11. Install chumpy (for some pose estimation utilities)
conda install -c conda-forge -y chumpy

# 12. Clone CaVFish repository
git clone git@github.com:josuedelarosa/CaVFish.git
cd CaVFish

# 13. Checkout specific commit
git checkout f050defcddcaed1699c1fcaf2711e59da5ab25a7

# 14. Install CaVFish requirements
python -m pip install -r requirements.txt

# 15. Install CaVFish package in editable mode
python -m pip install -e .

# 16. Install mmpretrain (specific version)
mim install "mmpretrain==1.2.0"

# 17. Install mmdet (specific version)
mim install 'mmdet==3.3.0'

# 18. Force reinstall numpy<2 to fix any conflicts
python -m pip uninstall -y numpy
conda install -c conda-forge -y "numpy<2" --force-reinstall

# 19. Force reinstall PyTorch to ensure compatibility
conda install -c pytorch -y pytorch torchvision cpuonly --force-reinstall

# 20. Reinstall mmcv to fix any conflicts
python -m pip uninstall -y mmcv mmcv-lite mmcv-full
mim install "mmcv==2.1.0"

# 21. Final numpy reinstall
python -m pip uninstall -y numpy
conda install -c conda-forge -y "numpy<2" --force-reinstall

# 22. Final mmcv reinstall with --no-deps
python -m pip uninstall -y mmcv mmcv-lite mmcv-full
python -m pip install --no-deps "mmcv==2.1.0"
```

## Additional Application Dependencies

After the above setup, install the application-specific dependencies:

```bash
# FastAPI and server
pip install fastapi
pip install uvicorn[standard]
pip install pydantic

# Image processing
pip install opencv-python
pip install Pillow
```

## Why These Specific Steps?

### Multiple numpy reinstalls
- CaVFish and MM packages have complex numpy version requirements
- Force reinstalling ensures no version conflicts
- numpy 2.x breaks compatibility with mmcv 2.1.0

### Multiple mmcv reinstalls
- First install gets mmcv with dependencies
- Second reinstall ensures compatibility after PyTorch reinstall
- Final `--no-deps` install prevents pip from pulling wrong dependencies

### Specific package versions
- `mmengine==0.10.7`: Last stable version compatible with mmcv 2.1.0
- `mmcv==2.1.0`: Required by CaVFish's custom modules
- `mmpretrain==1.2.0`: Compatible with the ViT backbone used
- `mmdet==3.3.0`: Required for detection components

### CPU-only PyTorch
- Simplifies installation by avoiding CUDA/MPS complexity
- Sufficient for inference workloads
- Can be changed to GPU version if needed

### Git checkout specific commit
- `f050defcddcaed1699c1fcaf2711e59da5ab25a7`: Known working commit
- Ensures reproducibility across setups

## Verification

After setup, verify the installation:

```bash
python -c "
import torch
print(f'PyTorch: {torch.__version__}')

import mmpose
print(f'mmpose: {mmpose.__version__}')

import mmcv
print(f'mmcv: {mmcv.__version__}')

import mmengine
print(f'mmengine: {mmengine.__version__}')

import numpy as np
print(f'numpy: {np.__version__}')

print('\n✅ All packages installed correctly!')
"
```

## Troubleshooting

### "No module named 'mmcv'"
Run the final mmcv reinstall steps (20-22).

### "numpy version conflict"
Run the final numpy reinstall step (21).

### "AttributeError in mmpose"
Verify you're using the exact commit: `f050defcddcaed1699c1fcaf2711e59da5ab25a7`

### "Import error with torch"
Force reinstall PyTorch (step 19).

## Notes

- Total install time: ~15-30 minutes depending on internet speed
- Disk space required: ~5-7 GB for the environment
- This setup has been verified on macOS with miniforge
- For other platforms, adjust PyTorch installation as needed
