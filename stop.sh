#!/bin/bash
# Stop all Local AI and Supabase services
# Modern approach: Let Docker Compose handle cleanup

set -e  # Exit on error

echo "Stopping all Local AI services..."

# Build compose file list for main AI services
COMPOSE_FILES="-f docker-compose.yml"

# Add host-cache file if it exists
if [ -f docker-compose.host-cache.yml ]; then
    COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.host-cache.yml"
    echo "Including host-cache configuration"
fi

# Parse arguments for destructive operations
if [ "$1" = "--volumes" ] || [ "$1" = "-v" ]; then
    echo ""
    echo "WARNING: This will DELETE all data volumes (including Supabase data)!"
    read -p "Are you sure? (yes/no): " -r
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        # Stop main AI services with volumes
        docker compose -p localai $COMPOSE_FILES down -v
        echo "Main AI services: Containers, networks, and volumes removed."

        # Stop Supabase with volumes
        echo "Stopping Supabase services..."
        (cd supabase/docker && docker compose down -v)
        echo "Supabase: Containers, networks, and volumes removed."
    else
        echo "Cancelled."
        exit 0
    fi
else
    # Normal stop - keeps volumes (data persists)
    echo "Stopping main AI services..."
    docker compose -p localai $COMPOSE_FILES down
    echo "Main AI services: Containers and networks removed. Volumes preserved."

    echo "Stopping Supabase services..."
    (cd supabase/docker && docker compose down)
    echo "Supabase: Containers and networks removed. Volumes preserved."
fi

echo ""
echo "To restart services: ./start.sh"
echo "To view remaining volumes: docker volume ls | grep -E 'localai|supabase'"
echo "To rebuild images: ./build.sh"
