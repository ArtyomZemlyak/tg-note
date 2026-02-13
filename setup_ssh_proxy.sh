#!/bin/bash
# Setup SSH tunnel as SOCKS5 proxy for HuggingFace downloads
# This script creates a SOCKS5 proxy via SSH to bypass regional restrictions

echo "═══════════════════════════════════════════════════════════════"
echo "Setup SSH Tunnel as SOCKS5 Proxy"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if SSH is available
if ! command -v ssh &> /dev/null; then
    echo "❌ SSH not found! Please install openssh-client"
    exit 1
fi

echo "This script will:"
echo "  1. Create SSH tunnel to your VPS/server"
echo "  2. Setup SOCKS5 proxy on localhost:1080"
echo "  3. Configure environment for HuggingFace downloads"
echo ""

# Get SSH details
read -p "Enter SSH host (e.g., user@your-vps.com): " SSH_HOST
read -p "Enter SSH port (default 22): " SSH_PORT
SSH_PORT=${SSH_PORT:-22}

read -p "Enter local SOCKS5 port (default 1080): " SOCKS_PORT
SOCKS_PORT=${SOCKS_PORT:-1080}

echo ""
echo "Configuration:"
echo "  SSH Host: $SSH_HOST"
echo "  SSH Port: $SSH_PORT"
echo "  SOCKS5 Port: localhost:$SOCKS_PORT"
echo ""

read -p "Continue? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "Cancelled"
    exit 0
fi

echo ""
echo "───────────────────────────────────────────────────────────────"
echo "Starting SSH tunnel..."
echo "───────────────────────────────────────────────────────────────"
echo ""

# Start SSH tunnel in background
ssh -f -N -D $SOCKS_PORT -p $SSH_PORT $SSH_HOST

if [ $? -eq 0 ]; then
    echo "✅ SSH tunnel started on localhost:$SOCKS_PORT"
    echo ""
    
    # Create environment script
    cat > /tmp/huggingface_proxy_env.sh << EOF
#!/bin/bash
# Environment variables for HuggingFace downloads via proxy

export HTTP_PROXY="socks5://localhost:$SOCKS_PORT"
export HTTPS_PROXY="socks5://localhost:$SOCKS_PORT"
export ALL_PROXY="socks5://localhost:$SOCKS_PORT"
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_DOWNLOAD_TIMEOUT=600

echo "✅ Proxy environment configured"
echo "   HTTP_PROXY=\$HTTP_PROXY"
echo "   HTTPS_PROXY=\$HTTPS_PROXY"
EOF
    
    chmod +x /tmp/huggingface_proxy_env.sh
    
    echo "═══════════════════════════════════════════════════════════════"
    echo "✅ Setup complete!"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "To use the proxy for downloads:"
    echo ""
    echo "  1. Source the environment:"
    echo "     source /tmp/huggingface_proxy_env.sh"
    echo ""
    echo "  2. Download models:"
    echo "     huggingface-cli download docling-project/docling-layout-heron-101 \\"
    echo "         --local-dir ./layout \\"
    echo "         --local-dir-use-symlinks False"
    echo ""
    echo "  3. Test proxy:"
    echo "     curl --proxy socks5://localhost:$SOCKS_PORT https://ipinfo.io/json"
    echo ""
    echo "To stop the SSH tunnel:"
    echo "  pkill -f 'ssh.*-D $SOCKS_PORT'"
    echo ""
    
else
    echo "❌ Failed to start SSH tunnel"
    echo ""
    echo "Possible issues:"
    echo "  - Wrong SSH credentials"
    echo "  - SSH key not configured"
    echo "  - Firewall blocking SSH"
    echo "  - Server not reachable"
    echo ""
    echo "Try manual SSH connection first:"
    echo "  ssh -p $SSH_PORT $SSH_HOST"
    exit 1
fi
