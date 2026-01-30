#!/bin/bash
# Test the numpy<2 fix by simulating the problematic step

set -e

CONDA_PATH=~/miniforge3/bin/conda
ENV_NAME=cavfish310_test
PYTHON_PATH=~/miniforge3/envs/${ENV_NAME}/bin/python
MIM_PATH=~/miniforge3/envs/${ENV_NAME}/bin/mim

echo "=== Testing NumPy <2 fix ==="
echo ""

# Clean up if exists
conda env remove -n ${ENV_NAME} -y 2>/dev/null || true

echo "1. Creating test environment with numpy<2..."
$CONDA_PATH create -n ${ENV_NAME} -c conda-forge python=3.10 pip numpy\<2 -y -q

echo "2. Checking initial numpy version..."
$PYTHON_PATH -c "import numpy; print(f'  NumPy: {numpy.__version__}')"

echo ""
echo "3. Installing mim and mmengine..."
$PYTHON_PATH -m pip install -q -U openmim
$MIM_PATH install -q mmengine==0.10.7

echo "4. Checking numpy after mmengine..."
$PYTHON_PATH -c "import numpy; print(f'  NumPy: {numpy.__version__}')"

echo ""
echo "5. Installing mmcv (this is where numpy typically gets upgraded)..."
$CONDA_PATH install -n ${ENV_NAME} -c conda-forge -y numpy\<2 --force-reinstall -q
$MIM_PATH install -q mmcv==2.1.0

echo "6. Checking numpy after mmcv..."
NP_VERSION=$($PYTHON_PATH -c "import numpy; print(numpy.__version__)")
echo "  NumPy: $NP_VERSION"

if [[ "$NP_VERSION" == 2.* ]]; then
    echo ""
    echo "  ⚠️  NumPy was upgraded to 2.x! Forcing downgrade..."
    $PYTHON_PATH -m pip uninstall -y numpy -q
    $PYTHON_PATH -m pip uninstall -y numpy -q
    $CONDA_PATH install -n ${ENV_NAME} -c conda-forge -y numpy\<2 --force-reinstall -q
    
    NP_VERSION=$($PYTHON_PATH -c "import numpy; print(numpy.__version__)")
    echo "  NumPy after downgrade: $NP_VERSION"
    
    if [[ "$NP_VERSION" == 2.* ]]; then
        echo "  ❌ Failed to downgrade numpy!"
        exit 1
    fi
fi

echo ""
echo "7. Testing mmcv import..."
$PYTHON_PATH -c "
import mmcv
import numpy
from mmcv.ops import nms
print(f'  ✓ mmcv {mmcv.__version__}')
print(f'  ✓ NumPy {numpy.__version__}')
print('  ✓ mmcv.ops available')
" || {
    echo "  ❌ mmcv import failed!"
    exit 1
}

echo ""
echo "✅ Test passed! NumPy <2 is maintained after mmcv installation."
echo ""
echo "Cleanup: conda env remove -n ${ENV_NAME} -y"
