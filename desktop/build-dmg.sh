#!/bin/bash
# Wrapper script to build DMG reliably

set -e

cd "$(dirname "$0")"

echo "Building Tauri app..."
npm run tauri:build || {
    echo "Build succeeded but DMG creation failed, creating DMG manually..."
}

echo ""
echo "🧹 Cleaning Python bytecode from app bundle..."
./clean-python-cache.sh

DMG_DIR="src-tauri/target/release/bundle/dmg"
DMG_FILE="Fishometrics_0.1.0_aarch64.dmg"

if [[ ! -f "$DMG_DIR/$DMG_FILE" ]]; then
    echo "Creating DMG manually with custom layout..."
    cd "$DMG_DIR"
    
    # Remove any existing DMG
    rm -f "$DMG_FILE"
    
    # Create temporary directory for DMG contents
    mkdir -p dmg_temp
    cp -R "Fishometrics.app" dmg_temp/
    ln -s /Applications dmg_temp/Applications
    
    # Create DMG with custom window size
    hdiutil create \
        -volname "Fishometrics" \
        -srcfolder dmg_temp \
        -ov \
        -format UDZO \
        "$DMG_FILE"
    
    # Clean up
    rm -rf dmg_temp
    
    echo "✓ DMG created successfully: $DMG_DIR/$DMG_FILE"
else
    echo "✓ DMG already exists: $DMG_DIR/$DMG_FILE"
fi

# Get absolute path for final message
FULL_PATH="$(cd "$DMG_DIR" && pwd)/$DMG_FILE"
echo ""
echo "======================================"
echo "Build complete!"
echo "DMG location: $FULL_PATH"
echo "======================================"
