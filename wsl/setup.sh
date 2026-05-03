#!/bin/bash
# CloudDriveManager WSL Setup Script
set -e

echo "=== CloudDriveManager WSL Setup ==="

# 1. Copy files
echo "[1/5] Copying files..."
cp cloud-drive-manager.exe ~/cloud-drive/bin/
cp cloud-drive-mcp.exe ~/cloud-drive/bin/
cp config/*.yaml ~/cloud-drive/config/
cp cloud-drive-manager.service ~/.config/systemd/user/
cp cloud-drive-manager-mcp.service ~/.config/systemd/user/
echo "  Files copied."

# 2. Make exe executable
echo "[2/5] Setting permissions..."
chmod +x ~/cloud-drive/bin/*.exe
echo "  Permissions set."

# 3. Reload systemd user
echo "[3/5] Reloading systemd user..."
systemctl --user daemon-reload
echo "  Reloaded."

# 4. Enable services
echo "[4/5] Enabling services..."
systemctl --user enable cloud-drive-manager.service
systemctl --user enable cloud-drive-manager-mcp.service
echo "  Enabled."

# 5. Start services
echo "[5/5] Starting services..."
systemctl --user start cloud-drive-manager.service
systemctl --user start cloud-drive-manager-mcp.service
echo "  Started."

# Status check
echo ""
echo "=== Service Status ==="
systemctl --user status cloud-drive-manager.service --no-pager
echo ""
systemctl --user status cloud-drive-manager-mcp.service --no-pager

echo ""
echo "=== Done ==="
echo "API:  http://localhost:29312"
echo "Docs: http://localhost:29312/docs"
echo "MCP:  stdio on port 29313"