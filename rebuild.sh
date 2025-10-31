#!/bin/bash
# Rebuild all Local AI Docker images
# Use this when:
#   - You've modified Dockerfiles
#   - You need to update dependencies
#   - Build cache is corrupted

set -e

echo "========================================"
echo "Local AI - Rebuild Images"
echo "========================================"
echo ""

# Check for required profile argument
if [ -z "$1" ]; then
    echo "Error: GPU profile required"
    echo "Usage: ./rebuild.sh [cpu|gpu-nvidia|gpu-amd]"
    echo ""
    echo "Examples:"
    echo "  ./rebuild.sh gpu-nvidia  # For NVIDIA GPUs"
    echo "  ./rebuild.sh gpu-amd     # For AMD GPUs (Linux only)"
    echo "  ./rebuild.sh cpu         # CPU-only mode"
    exit 1
fi

PROFILE=$1

# Validate profile
if [[ ! "$PROFILE" =~ ^(cpu|gpu-nvidia|gpu-amd)$ ]]; then
    echo "Error: Invalid profile '$PROFILE'"
    echo "Valid profiles: cpu, gpu-nvidia, gpu-amd"
    exit 1
fi

echo "Rebuilding images with profile: $PROFILE"
echo ""
echo "This will:"
echo "  1. Pull latest base images"
echo "  2. Rebuild all service images"
echo "  3. Download any new models"
echo ""

# Optional: clear build cache if requested
if [ "$2" == "--clean" ]; then
    echo "Clearing Docker build cache first..."
    docker builder prune -af
    echo ""
fi

# Update Supabase repository
if [ -d "supabase" ]; then
    echo "Updating Supabase repository..."
    cd supabase
    git pull
    cd ..
fi

# Rebuild all images using the new build script
./build.sh "$PROFILE"

echo ""
echo "========================================"
echo "Rebuild Complete!"
echo "========================================"
echo ""
echo "Images rebuilt successfully."
echo "Restart services with: ./stop.sh && ./start.sh $PROFILE"
echo ""
