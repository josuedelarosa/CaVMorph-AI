#!/bin/bash
# Build script for Fish Morphometrics Desktop App
# Requires: conda environment 'cavfish310' to be active

set -e

echo "🔨 Building Fish Morphometrics Desktop App"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Activate conda environment
activate_conda_env() {
    echo -e "${BLUE}Activating conda environment 'cavfish310'...${NC}"
    eval "$(conda shell.bash hook)"
    if ! conda activate cavfish310 2>/dev/null; then
        echo -e "${RED}❌ Failed to activate conda environment 'cavfish310'${NC}"
        echo "Please ensure conda is installed and the environment exists:"
        echo "  conda env list"
        exit 1
    fi
    echo -e "${GREEN}✓ Conda environment activated${NC}"
}

# Check prerequisites
check_prerequisites() {
    echo -e "${BLUE}Checking prerequisites...${NC}"
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        echo -e "${YELLOW}⚠️  Node.js not found. Please install Node.js 16+${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Node.js $(node --version)${NC}"
    
    # Check Python in conda env
    if ! command -v python3 &> /dev/null; then
        echo -e "${YELLOW}⚠️  Python 3 not found in conda environment${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Python $(python3 --version)${NC}"
    
    # Check Rust/Cargo
    if ! command -v cargo &> /dev/null; then
        echo -e "${YELLOW}⚠️  Rust/Cargo not found. Please install Rust 1.60+${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Cargo $(cargo --version)${NC}"
}

# Build backend binary
build_backend() {
    echo ""
    echo -e "${BLUE}Building backend binary with PyInstaller...${NC}"
    
    if [ ! -f "backend/api/cli.spec" ]; then
        echo -e "${YELLOW}⚠️  cli.spec not found${NC}"
        return 1
    fi
    
    python3 -m pip install pyinstaller -q
    python3 -m pyinstaller backend/api/cli.spec --distpath dist || return 1
    
    echo -e "${GREEN}✓ Backend binary created${NC}"
}

# Build frontend
build_frontend() {
    echo ""
    echo -e "${BLUE}Building frontend...${NC}"
    
    cd desktop
    npm install || return 1
    npm run build || return 1
    cd ..
    
    echo -e "${GREEN}✓ Frontend built${NC}"
}

# Build Tauri app
build_tauri() {
    echo ""
    echo -e "${BLUE}Building Tauri application...${NC}"
    
    cd desktop/src-tauri
    cargo tauri build || return 1
    cd ../..
    
    echo -e "${GREEN}✓ Tauri app built${NC}"
}

# Main build flow
main() {
    activate_conda_env
    check_prerequisites
    build_backend || { echo -e "${YELLOW}Backend build failed${NC}"; return 1; }
    build_frontend || { echo -e "${YELLOW}Frontend build failed${NC}"; return 1; }
    build_tauri || { echo -e "${YELLOW}Tauri build failed${NC}"; return 1; }
    
    echo ""
    echo -e "${GREEN}=========================================="
    echo "✓ Build successful!"
    echo "=========================================${NC}"
    echo ""
    echo "📦 Packages created in:"
    echo "  - target/release/bundle/"
    echo ""
    echo "For more details, see DEPLOYMENT.md"
}

main
