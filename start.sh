#!/bin/bash
# Start all Local AI services
# Modern approach: Simple, declarative, lets Docker Compose handle orchestration
#
# For first-time setup: ./setup.sh
# To rebuild images: ./build.sh
# To stop: ./stop.sh

set -e  # Exit on error

# Default profile
PROFILE="${1:-gpu-nvidia}"

echo "Starting Local AI services with profile: $PROFILE"
echo ""

# Set BuildKit
export DOCKER_BUILDKIT=1

# Start Supabase first (in its own project)
echo "Starting Supabase services..."
(cd supabase/docker && docker compose up -d)
echo ""

# Compose file list for main AI services
COMPOSE_FILES="-f docker-compose.yml"

if [ -f docker-compose.host-cache.yml ]; then
    COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.host-cache.yml"
    echo "Using host-level cache (/opt/ai-cache)"
fi

# Start main AI services with selected profile
# Docker Compose handles:
# - Network creation
# - Service orchestration via depends_on
# - Health checks
# - Proper startup order
echo "Starting main AI services..."
if [ "$PROFILE" = "none" ]; then
    docker compose -p localai $COMPOSE_FILES up -d
else
    docker compose -p localai $COMPOSE_FILES --profile "$PROFILE" up -d
fi

echo ""
echo "Services starting... This may take 1-2 minutes."
echo ""
echo "View logs: docker compose -p localai logs -f"
echo "View status: docker compose -p localai ps"
echo ""
echo "Services will be available at:"
echo "  - https://raven.lan - Main Dashboard"
echo "  - https://n8n.lan - n8n Automation"
echo "  - https://openwebui.lan - Open WebUI"
echo "  - https://studio.lan - Supabase Studio"
echo "  - https://comfyui.lan - ComfyUI"
echo "  (See CLAUDE.md for complete list)"
