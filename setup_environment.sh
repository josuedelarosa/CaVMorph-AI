#!/bin/bash
# ============================================================================
# Fish Morphometrics - Environment Setup Script
# ============================================================================
# This script sets up the conda environment required to run Fish Morphometrics.
# It handles the tricky installation of mmpose and related packages.
#
# Usage:
#   ./setup_environment.sh
#
# Prerequisites:
#   - conda (miniforge, mambaforge, miniconda, or anaconda)
# ============================================================================

set -e

# Configuration
ENV_NAME="cavfish310"
PYTHON_VERSION="3.10"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Fish Morphometrics Environment Setup${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Find conda
find_conda() {
    # Check common locations
    for conda_path in \
        "$HOME/miniforge3/bin/conda" \
        "$HOME/mambaforge/bin/conda" \
        "$HOME/miniconda3/bin/conda" \
        "$HOME/anaconda3/bin/conda" \
        "/opt/homebrew/Caskroom/miniforge/base/bin/conda" \
        "/usr/local/Caskroom/miniforge/base/bin/conda"
    do
        if [ -x "$conda_path" ]; then
            echo "$conda_path"
            return 0
        fi
    done
    
    # Try PATH
    if command -v conda &> /dev/null; then
        which conda
        return 0
    fi
    
    return 1
}

CONDA_EXE=$(find_conda) || {
    echo -e "${RED}❌ conda not found!${NC}"
    echo ""
    echo "Please install conda first. We recommend miniforge:"
    echo "  https://github.com/conda-forge/miniforge"
    echo ""
    echo "On macOS with Homebrew:"
    echo "  brew install --cask miniforge"
    exit 1
}

echo -e "${GREEN}✓ Found conda: $CONDA_EXE${NC}"

# Get conda base directory
CONDA_BASE=$(dirname $(dirname "$CONDA_EXE"))

# Initialize conda for this shell
eval "$("$CONDA_EXE" shell.bash hook)"

# Check if environment exists
if conda env list | grep -q "^${ENV_NAME} "; then
    echo -e "${YELLOW}⚠ Environment '${ENV_NAME}' already exists.${NC}"
    read -p "Do you want to recreate it? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Removing existing environment...${NC}"
        conda env remove -n "$ENV_NAME" -y
    else
        echo -e "${GREEN}✓ Using existing environment${NC}"
        conda activate "$ENV_NAME"
        
        # Verify packages
        echo -e "${BLUE}Verifying required packages...${NC}"
        python -c "import torch; import mmpose; import fastapi; print('All packages OK')" && {
            echo -e "${GREEN}✓ Environment is ready!${NC}"
            exit 0
        } || {
            echo -e "${RED}❌ Some packages are missing. Recreating environment...${NC}"
            conda env remove -n "$ENV_NAME" -y
        }
    fi
fi

# Create environment with pip
echo -e "${BLUE}Creating conda environment '${ENV_NAME}' with Python ${PYTHON_VERSION}...${NC}"
conda create -p ~/miniforge3/envs/cavfish310 python=3.10 pip -y

# Activate environment
echo -e "${BLUE}Activating environment...${NC}"
conda activate cavfish310

# Upgrade pip and core tools
echo -e "${BLUE}Upgrading pip, setuptools, wheel...${NC}"
python -m pip install -U pip setuptools wheel

# Uninstall and reinstall numpy properly
echo -e "${BLUE}Installing numpy<2...${NC}"
python -m pip uninstall -y numpy || true
conda install -c conda-forge -y "numpy<2"

# Install xtcocotools
echo -e "${BLUE}Installing xtcocotools...${NC}"
python -m pip install xtcocotools

# Install PyTorch with CPU-only
echo -e "${BLUE}Installing PyTorch (CPU-only)...${NC}"
conda install pytorch torchvision cpuonly -c pytorch -y

# Install OpenMIM for MM ecosystem
echo -e "${BLUE}Installing OpenMIM...${NC}"
python -m pip install -U openmim

# Install fsspec
echo -e "${BLUE}Installing fsspec...${NC}"
python -m pip install fsspec

# Install mmengine and mmcv with specific versions
echo -e "${BLUE}Installing mmengine==0.10.7...${NC}"
mim install "mmengine==0.10.7"

echo -e "${BLUE}Installing mmcv==2.1.0...${NC}"
mim install "mmcv==2.1.0"

# Install chumpy
echo -e "${BLUE}Installing chumpy...${NC}"
conda install -c conda-forge -y chumpy

# Clone and install CaVFish
echo -e "${BLUE}Cloning CaVFish repository...${NC}"
CAVFISH_DIR="$HOME/Documents/BIVL2ab/projects/cavfish/CaVFish"
if [ ! -d "$CAVFISH_DIR" ]; then
    git clone git@github.com:josuedelarosa/CaVFish.git "$CAVFISH_DIR"
fi

cd "$CAVFISH_DIR"
echo -e "${BLUE}Checking out specific commit...${NC}"
git checkout f050defcddcaed1699c1fcaf2711e59da5ab25a7

echo -e "${BLUE}Installing CaVFish requirements...${NC}"
python -m pip install -r requirements.txt

echo -e "${BLUE}Installing CaVFish package...${NC}"
python -m pip install -e .

# Install mmpretrain
echo -e "${BLUE}Installing mmpretrain==1.2.0...${NC}"
mim install "mmpretrain==1.2.0"

# Install mmdet
echo -e "${BLUE}Installing mmdet==3.3.0...${NC}"
mim install 'mmdet==3.3.0'

# Force reinstall numpy to fix conflicts
echo -e "${BLUE}Force reinstalling numpy<2...${NC}"
python -m pip uninstall -y numpy
conda install -c conda-forge -y "numpy<2" --force-reinstall

# Force reinstall PyTorch
echo -e "${BLUE}Force reinstalling PyTorch...${NC}"
conda install -c pytorch -y pytorch torchvision cpuonly --force-reinstall

# Reinstall mmcv to fix any conflicts
echo -e "${BLUE}Reinstalling mmcv==2.1.0...${NC}"
python -m pip uninstall -y mmcv mmcv-lite mmcv-full
mim install "mmcv==2.1.0"

# Final numpy reinstall
echo -e "${BLUE}Final numpy<2 reinstall...${NC}"
python -m pip uninstall -y numpy
conda install -c conda-forge -y "numpy<2" --force-reinstall

# Final mmcv reinstall with --no-deps
echo -e "${BLUE}Final mmcv==2.1.0 reinstall (no deps)...${NC}"
python -m pip uninstall -y mmcv mmcv-lite mmcv-full
python -m pip install --no-deps "mmcv==2.1.0"

# Install other dependencies
echo -e "${BLUE}Installing additional dependencies...${NC}"
pip install \
    fastapi \
    uvicorn[standard] \
    pydantic \
    opencv-python \
    Pillow

# Install the backend package
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/backend/pyproject.toml" ]; then
    echo -e "${BLUE}Installing cavfish-inference backend...${NC}"
    pip install -e "$SCRIPT_DIR/backend"
fi

# Verify installation
echo ""
echo -e "${BLUE}Verifying installation...${NC}"
python -c "
import sys
print(f'Python: {sys.version}')

import torch
print(f'PyTorch: {torch.__version__}')
if torch.backends.mps.is_available():
    print('  MPS (Apple Silicon): Available')
elif torch.cuda.is_available():
    print(f'  CUDA: Available ({torch.cuda.get_device_name(0)})')
else:
    print('  Device: CPU only')

import mmpose
print(f'mmpose: {mmpose.__version__}')

import mmengine
print(f'mmengine: {mmengine.__version__}')

import fastapi
print(f'FastAPI: {fastapi.__version__}')

print()
print('All packages installed successfully!')
"

# Create config file for the app
CONFIG_DIR="$HOME/Library/Application Support/FishMorph"
mkdir -p "$CONFIG_DIR"
cat > "$CONFIG_DIR/config.json" << EOF
{
    "backend_dir": "$SCRIPT_DIR",
    "conda_env": "$ENV_NAME",
    "setup_complete": true
}
EOF

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Setup Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "To use the environment manually:"
echo "  conda activate $ENV_NAME"
echo ""
echo "To run the backend directly:"
echo "  cd $SCRIPT_DIR"
echo "  python -m backend.api.cli"
echo ""
echo "You can now run the Fish Morphometrics app!"
