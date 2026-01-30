#!/bin/bash
# Quick reference script for the exact mmpose installation sequence
# This is for reference - the actual installation is handled by setup_first_run.py

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Cavfish MMPose Installation - Manual Reference           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "This script shows the exact installation sequence."
echo "The actual first-run setup is automated in setup_first_run.py"
echo ""

# Step 1: Create environment
echo "Step 1: Creating conda environment..."
conda create -n cavfish310 -c conda-forge python=3.10 pip -y

# Step 2: Activate environment
echo "Step 2: Activating environment..."
conda activate cavfish310

# Step 3: Upgrade pip tools
echo "Step 3: Upgrading pip, setuptools, wheel..."
python -m pip install -U pip setuptools wheel

# Step 4: Force numpy reinstall
echo "Step 4: Force reinstalling numpy<2..."
python -m pip uninstall -y numpy || true
conda install -c conda-forge -y "numpy<2"

# Step 5: Install xtcocotools
echo "Step 5: Installing xtcocotools..."
python -m pip install xtcocotools

# Step 6: Install PyTorch
echo "Step 6: Installing PyTorch (CPU-only)..."
conda install pytorch torchvision cpuonly -c pytorch -y

# Step 7: Install OpenMIM
echo "Step 7: Installing OpenMIM..."
python -m pip install -U openmim

# Step 8: Install fsspec
echo "Step 8: Installing fsspec..."
python -m pip install fsspec

# Step 9: Install mmengine
echo "Step 9: Installing mmengine==0.10.7..."
mim install "mmengine==0.10.7"

# Step 10: Install mmcv
echo "Step 10: Installing mmcv==2.1.0..."
mim install "mmcv==2.1.0"

# Step 11: Install mmdet
echo "Step 11: Installing mmdet==3.3.0..."
mim install "mmdet==3.3.0"

# Step 12: Install chumpy
echo "Step 12: Installing chumpy..."
conda install -c conda-forge -y chumpy

# Step 13: Clone and install mmpose
echo "Step 13: Cloning and installing mmpose..."
git clone https://github.com/open-mmlab/mmpose.git
cd mmpose
python -m pip install -r requirements.txt
python -m pip install -e .
cd ..

# Step 14: Install mmpretrain
echo "Step 14: Installing mmpretrain==1.2.0..."
mim install "mmpretrain==1.2.0"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Installation Complete!                                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Verify with:"
echo "  python -c 'import torch; import mmpose; import mmcv; print(\"OK\")'"
echo ""
