#!/bin/bash
# First-time setup for Local AI services
# This script clones repositories, builds images, and downloads models

set -e

echo "========================================"
echo "Local AI - First-Time Setup"
echo "========================================"
echo ""
echo "This script will:"
echo "  1. Clone required repositories"
echo "  2. Build all Docker images"
echo "  3. Download required models"
echo ""
echo "This may take 30-60 minutes depending on your internet connection."
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 1
fi

# Check for required profile argument
if [ -z "$1" ]; then
    echo "Error: GPU profile required"
    echo "Usage: ./setup.sh [cpu|gpu-nvidia|gpu-amd]"
    echo ""
    echo "Examples:"
    echo "  ./setup.sh gpu-nvidia  # For NVIDIA GPUs (RTX 3090, 4090, 5090, etc)"
    echo "  ./setup.sh gpu-amd     # For AMD GPUs (Linux only)"
    echo "  ./setup.sh cpu         # CPU-only mode"
    exit 1
fi

PROFILE=$1

# Validate profile
if [[ ! "$PROFILE" =~ ^(cpu|gpu-nvidia|gpu-amd)$ ]]; then
    echo "Error: Invalid profile '$PROFILE'"
    echo "Valid profiles: cpu, gpu-nvidia, gpu-amd"
    exit 1
fi

echo ""
echo "Starting setup with profile: $PROFILE"
echo ""

# Clone Supabase repository if needed
if [ ! -d "supabase" ]; then
    echo "Cloning Supabase repository..."
    git clone --filter=blob:none --no-checkout https://github.com/supabase/supabase.git
    cd supabase
    git sparse-checkout init --cone
    git sparse-checkout set docker
    git checkout master
    cd ..
fi

# Copy environment configuration
if [ -f ".env" ] && [ ! -f "supabase/docker/.env" ]; then
    echo "Setting up Supabase environment..."
    cp .env supabase/docker/.env
fi

# Build all images
echo "Building Docker images..."
./build.sh "$PROFILE"

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Start services: ./start.sh $PROFILE"
echo "  2. Stop services:  ./stop.sh"
echo ""
echo "Services will be available at https://*.lan domains"
echo "(You may need to update your /etc/hosts file on first run)"
echo ""
