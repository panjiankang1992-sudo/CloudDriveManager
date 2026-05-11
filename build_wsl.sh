#!/bin/bash
# Build script for CloudDriveManager (WSL/Linux)
# Uses cloud-drive-manager.spec for reproducible builds

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$PROJECT_DIR/build"
DIST_DIR="$PROJECT_DIR/dist"

# Add local bin to PATH if pyinstaller not found
if ! command -v pyinstaller &> /dev/null; then
    export PATH="$HOME/.local/bin:$HOME/global-py/bin:$PATH"
fi

echo "=== CloudDriveManager Build ==="
echo "Project: $PROJECT_DIR"
echo "Python:"
python3 --version
echo "PyInstaller:"
pyinstaller --version

mkdir -p "$BUILD_DIR" "$DIST_DIR"

cd "$PROJECT_DIR"

# Verify key files exist
echo ""
echo "[1/4] Verifying source files..."
REQUIRED_FILES=(
    "main.py"
    "src/mcp/server.py"
    "src/core/config.py"
    "config/config_dev.yaml"
    "config/config_prod.yaml"
    "runtime_hook.py"
    "cloud-drive-manager.spec"
)

all_ok=true
for f in "${REQUIRED_FILES[@]}"; do
    if [ -f "$PROJECT_DIR/$f" ]; then
        echo "  ✓ $f"
    else
        echo "  ✗ MISSING: $f"
        all_ok=false
    fi
done

if [ "$all_ok" = false ]; then
    echo ""
    echo "ERROR: Missing required files"
    exit 1
fi

echo ""
echo "[2/4] Cleaning old build artifacts..."
rm -rf "$BUILD_DIR"/*
rm -f "$DIST_DIR"/cloud-drive-manager
rm -f "$DIST_DIR"/cloud-drive-mcp

echo ""
echo "[3/4] Building with PyInstaller (using .spec file)..."
$HOME/.local/bin/pyinstaller cloud-drive-manager.spec --clean --noconfirm

echo ""
echo "[4/4] Build complete!"
echo ""
echo "=== Generated binaries ==="
ls -lh "$DIST_DIR/"
echo ""
echo "API server:   $DIST_DIR/cloud-drive-manager"
echo "MCP server:   $DIST_DIR/cloud-drive-mcp"
echo "API port:     29312"
echo "MCP port:     29313"
