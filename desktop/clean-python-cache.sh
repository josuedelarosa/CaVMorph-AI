#!/bin/bash
# Clean Python bytecode and cache files from the built app bundle
# This prevents AMFI from marking the app as damaged after code signing

set -e

APP_PATH="src-tauri/target/release/bundle/macos/PhenoAI.app"

if [ ! -d "$APP_PATH" ]; then
    echo "⚠️  App bundle not found at: $APP_PATH"
    echo "Skipping cache cleanup (build may not be complete yet)"
    exit 0
fi

echo "🧹 Cleaning Python bytecode from app bundle..."

# Remove __pycache__ directories
PYCACHE_COUNT=$(find "$APP_PATH" -type d -name "__pycache__" 2>/dev/null | wc -l | tr -d ' ')
if [ "$PYCACHE_COUNT" -gt 0 ]; then
    echo "   Removing $PYCACHE_COUNT __pycache__ directories..."
    find "$APP_PATH" -type d -name "__pycache__" -prune -exec rm -rf {} \; 2>/dev/null || true
fi

# Remove .pyc files
PYC_COUNT=$(find "$APP_PATH" -type f -name "*.pyc" 2>/dev/null | wc -l | tr -d ' ')
if [ "$PYC_COUNT" -gt 0 ]; then
    echo "   Removing $PYC_COUNT .pyc files..."
    find "$APP_PATH" -type f -name "*.pyc" -delete 2>/dev/null || true
fi

# Remove .pyo files (optimized bytecode)
PYO_COUNT=$(find "$APP_PATH" -type f -name "*.pyo" 2>/dev/null | wc -l | tr -d ' ')
if [ "$PYO_COUNT" -gt 0 ]; then
    echo "   Removing $PYO_COUNT .pyo files..."
    find "$APP_PATH" -type f -name "*.pyo" -delete 2>/dev/null || true
fi

echo "✅ Python cache cleanup complete!"
echo ""
