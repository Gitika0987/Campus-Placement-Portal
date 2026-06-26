#!/bin/bash
# =============================================================
#   EC2 INSTANCE SETUP SCRIPT — ec2_setup.sh
# =============================================================
#   WHAT IS THIS?
#   Run this script on each EC2 instance to install Docker,
#   build the Flask container, and start the backend.
#
#   HOW TO USE:
#   1. SSH into your EC2 instance
#   2. Upload project files (or git clone)
#   3. chmod +x ec2_setup.sh && ./ec2_setup.sh
# =============================================================

set -e  # Stop on any error

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   Placement Portal — EC2 Setup               ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── Step 1: Update system packages ──────────────────
echo "▶ Updating system..."
sudo yum update -y

# ── Step 2: Install Docker ──────────────────────────
echo "▶ Installing Docker..."
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user

# Allow ec2-user to run docker without sudo for this session
sudo chmod 666 /var/run/docker.sock

echo "✓ Docker installed and running"
docker --version

# ── Step 3: Build Docker image ──────────────────────
echo ""
echo "▶ Building Docker image..."
docker build -t placement-portal .
echo "✓ Docker image built successfully"

# ── Step 4: Stop any existing container ─────────────
echo ""
echo "▶ Cleaning up old containers..."
docker stop placement-backend 2>/dev/null || true
docker rm placement-backend 2>/dev/null || true

# ── Step 5: Run Flask container ─────────────────────
# Port 5000 inside container → Port 5000 on EC2
echo "▶ Starting Flask container..."
docker run -d \
    --name placement-backend \
    --restart unless-stopped \
    -p 5000:5000 \
    -e PORT=5000 \
    placement-portal

echo ""
echo "✓ Container started!"

# ── Step 6: Verify ──────────────────────────────────
sleep 3
echo "▶ Health check..."
if curl -s http://localhost:5000/health | grep -q "ok"; then
    echo "✓ Backend is healthy!"
    echo ""
    echo "╔══════════════════════════════════════════════╗"
    echo "║   ✓ EC2 Setup Complete!                      ║"
    echo "║                                              ║"
    echo "║   Backend running on port 5000               ║"
    echo "║   Health: http://<EC2-PUBLIC-IP>:5000/health  ║"
    echo "╚══════════════════════════════════════════════╝"
else
    echo "✗ Health check failed. Check docker logs:"
    echo "  docker logs placement-backend"
fi
