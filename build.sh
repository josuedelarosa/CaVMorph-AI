#!/bin/bash
set -e

# ==============================================================================
# Fish Morphometrics - Build Script (macOS)
# ==============================================================================
# This script builds the macOS application bundle (DMG) that uses your existing
# conda environment (cavfish310) instead of bundling Python.
# 
# Build approach:
# 1. The DMG contains:
#    - Tauri desktop app
#    - setup_first_run.py (for first-run conda env verification/creation)
#    - Backend source code (bundled in Resources)
#    - Model config files (bundled in Resources)
#    - Optionally: model weights (if present, reduces first-run download)
# 
# 2. On first launch, the app:
#    - Checks if cavfish310 conda environment exists
#    - If missing or incomplete, runs setup_first_run.py to create it
#    - Starts backend using Python from cavfish310 environment
#    - Connects frontend to backend
# 
# Prerequisites:
# - macOS with conda/miniforge installed
# - cavfish310 environment already set up (recommended)
# - Node.js and npm
# - Rust toolchain (cargo)
# - Xcode Command Line Tools
# ==============================================================================

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     Fish Morphometrics - Build Script                         ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Navigate to project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Cleanup any stale DMG mounts before building
echo "🧹 Cleaning up any previous DMG mounts..."
hdiutil detach "/Volumes/Fish Morphometrics" 2>/dev/null || true
rm -f desktop/src-tauri/target/release/bundle/dmg/*.dmg 2>/dev/null || true

# Check dependencies
echo "📋 Checking build dependencies..."

if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install it first."
    exit 1
fi
echo "  ✓ Node.js $(node --version)"

if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install it first."
    exit 1
fi
echo "  ✓ npm $(npm --version)"

if ! command -v rustc &> /dev/null; then
    echo "❌ Rust is not installed. Please install it first."
    echo "  Run: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    exit 1
fi
echo "  ✓ Rust $(rustc --version)"

if ! command -v cargo &> /dev/null; then
    echo "❌ Cargo is not installed. Please install Rust first."
    exit 1
fi
echo "  ✓ Cargo $(cargo --version | head -n1)"

# Check for model weights (optional - can be downloaded on first run)
if [ -f "models/cavfish_v1/weights.pth" ]; then
    WEIGHTS_SIZE=$(du -h "models/cavfish_v1/weights.pth" | cut -f1)
    echo "  ✓ Model weights found (${WEIGHTS_SIZE})"
    echo "    Will be bundled in app to avoid first-run download."
else
    echo "  ⚠ Model weights not found"
    echo "    Users will need to download them on first run."
fi

# Verify setup script exists
if [ ! -f "desktop/setup_first_run.py" ]; then
    echo "❌ desktop/setup_first_run.py not found!"
    exit 1
fi
echo "  ✓ Setup script found"

# Check for conda (recommended for building/testing)
if command -v conda &> /dev/null; then
    echo "  ✓ Conda found ($(conda --version))"
    if conda env list | grep -q "cavfish310"; then
        echo "  ✓ cavfish310 environment exists"
    else
        echo "  ⚠ cavfish310 environment not found (will be created on first run)"
    fi
else
    echo "  ⚠ Conda not found (required for end users)"
fi

echo ""
echo "📦 Installing frontend dependencies..."
cd desktop
npm install

echo ""
echo "🔨 Building frontend..."
npm run build

echo ""
echo "🦀 Building Tauri application..."
npm run tauri build
cd ..

echo ""
echo "✅ Build complete!"
echo ""
echo "📍 Output location:"
echo "   desktop/src-tauri/target/release/bundle/dmg/"
echo ""

# Find the DMG
DMG_PATH=$(find desktop/src-tauri/target/release/bundle/dmg -name "*.dmg" 2>/dev/null | head -n1)
if [ -n "$DMG_PATH" ]; then
    DMG_SIZE=$(du -h "$DMG_PATH" | cut -f1)
    echo "📀 DMG: $DMG_PATH"
    echo "   Size: $DMG_SIZE"
    echo ""
    echo "To install:"
    echo "1. Open the DMG file"
    echo "2. Drag Fish Morphometrics to Applications"
    echo "3. Ensure Miniforge/Conda is installed: brew install --cask miniforge"
    echo "4. Launch the app - it will:"
    echo "   - Detect/verify cavfish310 conda environment"
    echo "   - If missing: create environment, install PyTorch + mmpose + dependencies"
    echo "   - If present: use existing environment directly"
    echo "   - Start backend and show GUI"
    echo ""
    echo "Prerequisites for end users:"
    echo "  - macOS 10.15 or later (arm64 or x86_64)"
    echo "  - Conda/Miniforge installed (required)"
    echo ""
    echo "For developers:"
    echo "  - Pre-create cavfish310 env to skip first-run setup"
    echo "  - Use your existing conda setup script"
else
    echo "⚠️  DMG not found in expected location"
fi
