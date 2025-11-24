#!/bin/bash
# Install NVIDIA Container Toolkit for Ubuntu 24.04 with RTX 5090 support
# Verified for CUDA 12.8 and driver version 570+

set -e  # Exit on error

echo "=========================================="
echo "NVIDIA Container Toolkit Installation"
echo "Ubuntu 24.04 | RTX 5090 | CUDA 12.8"
echo "=========================================="
echo ""

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run with sudo"
    echo "Usage: sudo ./install-nvidia-container-toolkit.sh"
    exit 1
fi

# Verify NVIDIA driver is installed
echo "[1/7] Verifying NVIDIA driver installation..."
if ! command -v nvidia-smi &> /dev/null; then
    echo "Error: nvidia-smi not found. Please install NVIDIA drivers first."
    exit 1
fi

DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -n1)
echo "✓ NVIDIA driver detected: $DRIVER_VERSION"

# Check driver version is 570+
DRIVER_MAJOR=$(echo $DRIVER_VERSION | cut -d'.' -f1)
if [ "$DRIVER_MAJOR" -lt 570 ]; then
    echo "Warning: RTX 5090 requires driver version 570+. Current: $DRIVER_VERSION"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo ""

# Verify Docker is installed
echo "[2/7] Verifying Docker installation..."
if ! command -v docker &> /dev/null; then
    echo "Error: Docker not found. Please install Docker first."
    exit 1
fi

DOCKER_VERSION=$(docker --version)
echo "✓ Docker detected: $DOCKER_VERSION"
echo ""

# Add NVIDIA Container Toolkit repository
echo "[3/7] Adding NVIDIA Container Toolkit repository..."
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null

echo "✓ Repository added successfully"
echo ""

# Update package lists
echo "[4/7] Updating package lists..."
apt-get update -qq
echo "✓ Package lists updated"
echo ""

# Install NVIDIA Container Toolkit
echo "[5/7] Installing NVIDIA Container Toolkit..."
apt-get install -y nvidia-container-toolkit
echo "✓ NVIDIA Container Toolkit installed"
echo ""

# Configure Docker runtime
echo "[6/7] Configuring Docker daemon for NVIDIA runtime..."
nvidia-ctk runtime configure --runtime=docker
echo "✓ Docker daemon configured"
echo ""

# Restart Docker
echo "[7/7] Restarting Docker service..."
systemctl restart docker
sleep 2
echo "✓ Docker restarted"
echo ""

# Verify installation
echo "=========================================="
echo "Testing GPU access in container..."
echo "=========================================="
echo ""

if docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi; then
    echo ""
    echo "=========================================="
    echo "✓ Installation successful!"
    echo "=========================================="
    echo ""
    echo "Your RTX 5090 is now accessible from Docker containers."
    echo "You can now run: ./start.sh"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "✗ Installation verification failed"
    echo "=========================================="
    echo ""
    echo "Please check the error messages above."
    exit 1
fi
