#!/bin/bash
# Installation script for MCP Server on VPS

set -e

echo "=========================================="
echo "MCP SERVER VPS - INSTALLATION"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Please run as root or with sudo"
  exit 1
fi

# Variables
INSTALL_DIR="/opt/mcp_server_meetings"
SERVICE_FILE="/etc/systemd/system/mcp-server-meetings.service"
LOG_FILE="/var/log/mcp_server_meetings.log"
PYTHON_BIN="/usr/bin/python3"

echo "📦 Installation directory: $INSTALL_DIR"
echo "📝 Log file: $LOG_FILE"
echo ""

# Create installation directory
echo "1️⃣  Creating installation directory..."
mkdir -p $INSTALL_DIR
cp mcp_server_meetings_vps.py $INSTALL_DIR/mcp_server_meetings.py
chmod +x $INSTALL_DIR/mcp_server_meetings.py
echo "   ✅ Files copied"

# Install Python dependencies
echo ""
echo "2️⃣  Installing Python dependencies..."
pip3 install psycopg2-binary qdrant-client requests || {
    echo "   ⚠️  Failed to install dependencies, trying with --user"
    pip3 install --user psycopg2-binary qdrant-client requests
}
echo "   ✅ Dependencies installed"

# Create log file
echo ""
echo "3️⃣  Creating log file..."
touch $LOG_FILE
chmod 666 $LOG_FILE
echo "   ✅ Log file created"

# Create systemd service
echo ""
echo "4️⃣  Creating systemd service..."
cat > $SERVICE_FILE << EOF
[Unit]
Description=MCP Server for Meetings Transcriptions
After=network.target postgresql.service docker.service
Wants=postgresql.service docker.service

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$PYTHON_BIN $INSTALL_DIR/mcp_server_meetings.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOF

echo "   ✅ Service file created"

# Reload systemd
echo ""
echo "5️⃣  Reloading systemd..."
systemctl daemon-reload
echo "   ✅ Systemd reloaded"

# Enable service
echo ""
echo "6️⃣  Enabling service..."
systemctl enable mcp-server-meetings.service
echo "   ✅ Service enabled (will start on boot)"

# Start service
echo ""
echo "7️⃣  Starting service..."
systemctl start mcp-server-meetings.service
echo "   ✅ Service started"

# Check status
echo ""
echo "=========================================="
echo "INSTALLATION COMPLETE!"
echo "=========================================="
echo ""
echo "📊 Service Status:"
systemctl status mcp-server-meetings.service --no-pager || true
echo ""
echo "=========================================="
echo "USEFUL COMMANDS:"
echo "=========================================="
echo ""
echo "# Check service status:"
echo "sudo systemctl status mcp-server-meetings"
echo ""
echo "# View logs:"
echo "sudo journalctl -u mcp-server-meetings -f"
echo "or"
echo "tail -f $LOG_FILE"
echo ""
echo "# Restart service:"
echo "sudo systemctl restart mcp-server-meetings"
echo ""
echo "# Stop service:"
echo "sudo systemctl stop mcp-server-meetings"
echo ""
echo "=========================================="
echo "NEXT STEPS:"
echo "=========================================="
echo ""
echo "1. Verify service is running:"
echo "   sudo systemctl status mcp-server-meetings"
echo ""
echo "2. Configure Claude Desktop on your PC:"
echo "   See: CLAUDE_DESKTOP_SSH_CONFIG.md"
echo ""
echo "3. Test connection from your PC via SSH tunnel"
echo ""
echo "=========================================="
