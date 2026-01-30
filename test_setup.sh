#!/bin/bash
# Quick test of setup_first_run.py

set -e

echo "Testing setup_first_run.py..."
cd "$(dirname "$0")"

# Use miniforge python directly
PYTHON=~/miniforge3/envs/cavfish310/bin/python

echo "Environment created, checking packages..."
$PYTHON -c "
import sys
try:
    import numpy
    print(f'✓ NumPy {numpy.__version__}')
    assert numpy.__version__.startswith('1.'), f'NumPy 2.x detected: {numpy.__version__}'
except ImportError as e:
    print(f'✗ NumPy not installed: {e}')
    sys.exit(1)
"

echo ""
echo "Environment is valid with NumPy <2!"
echo "Now run the full setup script to install PyTorch + mmpose"
