#!/bin/bash
# Update Local AI services to latest versions
# This will:
#   1. Pull latest git repositories
#   2. Pull pre-built images from Docker Hub
#   3. Rebuild custom images
#   4. Restart all services

set -e

echo "========================================"
echo "Local AI - Update System"
echo "========================================"
echo ""

# Check for required profile argument
if [ -z "$1" ]; then
    echo "Error: GPU profile required"
    echo "Usage: ./update.sh [cpu|gpu-nvidia|gpu-amd]"
    echo ""
    echo "Examples:"
    echo "  ./update.sh gpu-nvidia  # For NVIDIA GPUs"
    echo "  ./update.sh gpu-amd     # For AMD GPUs (Linux only)"
    echo "  ./update.sh cpu         # CPU-only mode"
    exit 1
fi

PROFILE=$1

# Validate profile
if [[ ! "$PROFILE" =~ ^(cpu|gpu-nvidia|gpu-amd)$ ]]; then
    echo "Error: Invalid profile '$PROFILE'"
    echo "Valid profiles: cpu, gpu-nvidia, gpu-amd"
    exit 1
fi

echo "Updating system with profile: $PROFILE"
echo ""

# Step 1: Stop services
echo "Step 1/4: Stopping services..."
./stop.sh
echo ""

# Step 2: Pull pre-built images
echo "Step 2/4: Pulling latest pre-built images..."
docker compose -p localai -f docker-compose.yml -f supabase/docker/docker-compose.yml pull
echo ""

# Step 3: Rebuild custom images (includes git pull)
echo "Step 3/4: Rebuilding custom images..."
python start_services.py --profile "$PROFILE" --build-only
echo ""

# Step 4: Restart services
echo "Step 4/4: Starting services..."
./start.sh
echo ""

echo "========================================"
echo "Update Complete!"
echo "========================================"
echo ""
echo "All services updated and restarted."
echo ""
