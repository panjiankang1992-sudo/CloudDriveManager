#!/bin/bash
# CloudDriveManager WSL Setup Script
# Deploys to /opt/CloudDriveManager if possible, otherwise ~/cloud-drive

set -e

# Try /opt first, fall back to home directory
if [ -w /opt ] 2>/dev/null; then
    DEPLOY_DIR="/opt/CloudDriveManager"
else
    DEPLOY_DIR="$HOME/cloud-drive"
fi

BIN_DIR="$DEPLOY_DIR/bin"
CONFIG_DIR="$DEPLOY_DIR/config"
LOG_DIR="$DEPLOY_DIR/log"
DATA_DIR="$DEPLOY_DIR/data"

echo "=== CloudDriveManager WSL Setup ==="
echo "Deploy directory: $DEPLOY_DIR"

# 1. Create directory structure
echo ""
echo "[1/5] Creating directory structure..."
mkdir -p "$BIN_DIR" "$CONFIG_DIR" "$LOG_DIR" "$DATA_DIR"
echo "  Directories created."

# 2. Copy binaries
echo ""
echo "[2/5] Copying binaries..."
cp dist/cloud-drive-manager "$BIN_DIR/"
cp dist/cloud-drive-mcp "$BIN_DIR/"
chmod +x "$BIN_DIR"/*
echo "  Binaries copied."

# 3. Copy config files
echo ""
echo "[3/5] Copying config files..."
cp config/config_prod.yaml "$CONFIG_DIR/"
# Optionally copy dev config for debugging
if [ -f config/config_dev.yaml ]; then
    cp config/config_dev.yaml "$CONFIG_DIR/"
fi
echo "  Config files copied."

# 4. Install systemd services
echo ""
echo "[4/5] Installing systemd services..."
mkdir -p ~/.config/systemd/user
cp wsl/cloud-drive-manager.service ~/.config/systemd/user/
cp wsl/cloud-drive-manager-mcp.service ~/.config/systemd/user/
# Update service files with actual deploy dir
sed -i "s|/opt/CloudDriveManager|$DEPLOY_DIR|g" ~/.config/systemd/user/cloud-drive-manager.service
sed -i "s|/opt/CloudDriveManager|$DEPLOY_DIR|g" ~/.config/systemd/user/cloud-drive-manager-mcp.service
systemctl --user daemon-reload
echo "  Services installed."

# 5. Enable and start services
echo ""
echo "[5/5] Starting services..."
systemctl --user enable cloud-drive-manager.service
systemctl --user enable cloud-drive-manager-mcp.service
systemctl --user start cloud-drive-manager.service
systemctl --user start cloud-drive-manager-mcp.service
echo "  Services started."

# Status check
echo ""
echo "=== Service Status ==="
systemctl --user status cloud-drive-manager.service --no-pager || true
echo ""
systemctl --user status cloud-drive-manager-mcp.service --no-pager || true

echo ""
echo "=== Deployment Complete ==="
echo "API:  http://localhost:29312"
echo "Docs: http://localhost:29312/docs"
echo "MCP:  stdio on port 29313"
echo "Logs: journalctl --user -u cloud-drive-manager -f"
