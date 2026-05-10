#!/bin/bash
# Build script for CloudDriveManager (WSL/Linux)

set -e

PROJECT_DIR="/mnt/d/MyCode/CloudDriveManager"
BUILD_DIR="$PROJECT_DIR/build"
DIST_DIR="$PROJECT_DIR/dist"

echo "=== CloudDriveManager Build ==="
echo "Project: $PROJECT_DIR"
echo "Python:"
python3 --version
echo "PyInstaller:"
/home/yuyutian/.local/bin/pyinstaller --version

mkdir -p "$BUILD_DIR" "$DIST_DIR"

cd "$PROJECT_DIR"

# Verify key files exist
echo ""
echo "[0/1] Verifying source files..."
for f in main.py src/config/config.py config/config_dev.yaml runtime_hook.py; do
    if [ -f "$PROJECT_DIR/$f" ]; then
        echo "  ✓ $f"
    else
        echo "  ✗ MISSING: $f"
        exit 1
    fi
done

echo ""
echo "[1/3] Building API server..."
/home/yuyutian/.local/bin/pyinstaller \
    --name "cloud-drive-manager" \
    --onefile \
    --console \
    --clean \
    --runtime-hook="runtime_hook.py" \
    --additional-hooks-dir "." \
    --hidden-import=uvicorn.logging \
    --hidden-import=uvicorn.loops \
    --hidden-import=uvicorn.loops.auto \
    --hidden-import=uvicorn.protocols \
    --hidden-import=uvicorn.protocols.http \
    --hidden-import=uvicorn.protocols.http.auto \
    --hidden-import=uvicorn.protocols.websockets \
    --hidden-import=uvicorn.protocols.websockets.auto \
    --hidden-import=uvicorn.lifespan \
    --hidden-import=uvicorn.lifespan.on \
    --hidden-import=fastapi \
    --hidden-import=fastapi.applications \
    --hidden-import=fastapi.routing \
    --hidden-import=pydantic \
    --hidden-import=pydantic.fields \
    --hidden-import=pydantic.main \
    --hidden-import=pydantic.schema \
    --hidden-import=pydantic.validators \
    --hidden-import=pydantic.env_settings \
    --hidden-import=pydantic.fields \
    --hidden-import=pymysql \
    --hidden-import=pymysql.connections \
    --hidden-import=pymysql.cursors \
    --hidden-import=cryptography \
    --hidden-import=cryptography.fernet \
    --hidden-import=yaml \
    --hidden-import=fastmcp \
    --hidden-import=fastmcp.server \
    --hidden-import=httpx \
    --add-data "config:config" \
    --paths "/home/yuyutian/.local/lib/python3.12/site-packages" \
    --distpath "$DIST_DIR" \
    --workpath "$BUILD_DIR" \
    --log-level WARN \
    main.py

echo ""
echo "[2/3] Building MCP server..."
/home/yuyutian/.local/bin/pyinstaller \
    --name "cloud-drive-mcp" \
    --onefile \
    --console \
    --clean \
    --runtime-hook="runtime_hook.py" \
    --collect-all=fastmcp \
    --collect-all=httpx \
    --collect-all=httpcore \
    --hidden-import=pydantic \
    --hidden-import=pydantic.fields \
    --hidden-import=pydantic.main \
    --hidden-import=pydantic.env_settings \
    --add-data "config:config" \
    --add-data "src:src" \
    --paths "/home/yuyutian/.local/lib/python3.12/site-packages" \
    --distpath "$DIST_DIR" \
    --workpath "$BUILD_DIR" \
    --log-level WARN \
    src/mcp/server.py

echo ""
echo "[3/3] Build complete!"
ls -lh "$DIST_DIR/"
echo ""
echo "API server:   $DIST_DIR/cloud-drive-manager"
echo "MCP server:   $DIST_DIR/cloud-drive-mcp"
echo "MCP port:     29313"
echo "API port:     29312"
