#!/bin/bash
# Build all Docker images for Local AI services
# Modern practice: Build separately from starting services
#
# Usage:
#   ./build.sh              # Build with default (CPU) profile
#   ./build.sh gpu-nvidia   # Build with NVIDIA GPU support
#   ./build.sh gpu-amd      # Build with AMD GPU support

set -e  # Exit on error

# Parse profile argument
PROFILE="${1:-cpu}"

echo "Building Local AI services with profile: $PROFILE"
echo "This may take 10-30 minutes depending on your system..."
echo ""

# Set BuildKit for faster, better builds
export DOCKER_BUILDKIT=1

# Compose file list
COMPOSE_FILES="-f docker-compose.yml"

# Add host-cache file if it exists
if [ -f docker-compose.host-cache.yml ]; then
    COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.host-cache.yml"
    echo "Using host-level cache (/opt/ai-cache)"
fi

# Build command with profile
if [ "$PROFILE" = "none" ]; then
    docker compose -p localai $COMPOSE_FILES build
else
    docker compose -p localai $COMPOSE_FILES --profile "$PROFILE" build
fi

echo ""
echo "Build complete!"
echo "To start services, run: ./start.sh"
