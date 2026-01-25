#!/bin/bash
# Verification script to ensure all systems are ready

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔍 Fish Morphometrics - Setup Verification"
echo "=========================================="
echo ""

# Check conda environment
echo "1️⃣  Checking conda environment..."
eval "$(conda shell.bash hook)"
if conda activate cavfish310 2>/dev/null; then
    echo -e "${GREEN}✓ cavfish310 environment activated${NC}"
else
    echo -e "${RED}✗ Failed to activate cavfish310${NC}"
    exit 1
fi

# Check Python
echo ""
echo "2️⃣  Checking Python..."
PYTHON_VERSION=$(python3 --version 2>&1)
if [[ $PYTHON_VERSION == *"3.10"* ]]; then
    echo -e "${GREEN}✓ Python ${PYTHON_VERSION}${NC}"
else
    echo -e "${YELLOW}⚠ Python ${PYTHON_VERSION} (expected 3.10+)${NC}"
fi

# Check required packages
echo ""
echo "3️⃣  Checking required packages..."
PACKAGES=("torch" "mmpose" "fastapi" "uvicorn" "cv2" "numpy")
for pkg in "${PACKAGES[@]}"; do
    if python3 -c "import ${pkg}" 2>/dev/null; then
        echo -e "${GREEN}✓ ${pkg}${NC}"
    else
        echo -e "${RED}✗ ${pkg} missing${NC}"
    fi
done

# Check Node.js
echo ""
echo "4️⃣  Checking Node.js..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js ${NODE_VERSION}${NC}"
else
    echo -e "${RED}✗ Node.js not found${NC}"
fi

# Check Rust/Cargo
echo ""
echo "5️⃣  Checking Rust..."
if command -v cargo &> /dev/null; then
    CARGO_VERSION=$(cargo --version)
    echo -e "${GREEN}✓ ${CARGO_VERSION}${NC}"
else
    echo -e "${RED}✗ Cargo not found${NC}"
fi

# Check backend CLI
echo ""
echo "6️⃣  Checking backend CLI..."
cd "$(dirname "$0")"
if python3 -m backend.api.cli --help &>/dev/null; then
    echo -e "${GREEN}✓ Backend CLI works${NC}"
else
    echo -e "${RED}✗ Backend CLI failed${NC}"
fi

# Check model files
echo ""
echo "7️⃣  Checking model files..."
if [ -f "models/cavfish_v1/config.py" ] && [ -f "models/cavfish_v1/weights.pth" ] && [ -f "models/cavfish_v1/meta.json" ]; then
    echo -e "${GREEN}✓ All model files present${NC}"
else
    echo -e "${RED}✗ Model files missing${NC}"
fi

# Test backend startup
echo ""
echo "8️⃣  Testing backend startup..."
BACKEND_LOG=$(mktemp)
python3 -m backend.api.cli --port 8892 > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
sleep 4

if python3 -c "
import urllib.request
import json
try:
    response = urllib.request.urlopen('http://127.0.0.1:8892/health', timeout=2)
    data = json.loads(response.read().decode())
    print('✓ Backend API responds:', json.dumps(data, indent=2))
except Exception as e:
    print('✗ Backend not responding:', e)
" 2>/dev/null; then
    echo -e "${GREEN}✓ Backend API operational${NC}"
else
    echo -e "${RED}✗ Backend API failed${NC}"
fi

# Clean up backend process
kill $BACKEND_PID 2>/dev/null || true
wait $BACKEND_PID 2>/dev/null || true
rm -f "$BACKEND_LOG"

# Check build files
echo ""
echo "9️⃣  Checking build files..."
BUILD_FILES=("build.sh" "backend/api/cli.spec" "desktop/package.json" "desktop/src-tauri/Cargo.toml")
for file in "${BUILD_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ ${file}${NC}"
    else
        echo -e "${RED}✗ ${file} missing${NC}"
    fi
done

# Check documentation
echo ""
echo "🔟 Checking documentation..."
DOCS=("README.md" "QUICK_START.md" "ARCHITECTURE.md" "DEPLOYMENT.md" "00_START_HERE.md")
for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        echo -e "${GREEN}✓ ${doc}${NC}"
    else
        echo -e "${RED}✗ ${doc} missing${NC}"
    fi
done

# Summary
echo ""
echo "=========================================="
echo -e "${GREEN}✅ Setup verification complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Make sure cavfish310 is active: conda activate cavfish310"
echo "2. Run backend: python3 -m backend.api.cli --port 8008"
echo "3. In another terminal: cd desktop/src-tauri && cargo tauri dev"
echo "4. Or build: ./build.sh"
echo ""
