#!/bin/bash
#
# Service Restart Orchestration Script
#
# Gracefully restarts Docker services after secret rotation.
# Respects service dependencies and performs health checks.
#
# Usage:
#   ./scripts/restart-after-rotation.sh [options]
#
# Options:
#   --all              Restart all services (default: only affected services)
#   --no-healthcheck   Skip health checks after restart
#   --timeout SECONDS  Wait timeout for services to become healthy (default: 120)
#

set -euo pipefail

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default options
RESTART_ALL=false
SKIP_HEALTHCHECK=false
TIMEOUT=120

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            RESTART_ALL=true
            shift
            ;;
        --no-healthcheck)
            SKIP_HEALTHCHECK=true
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --help)
            head -n 20 "$0" | tail -n +3 | sed 's/^# //g; s/^#//g'
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}" >&2
            exit 1
            ;;
    esac
done

# Change to project root
cd "$PROJECT_ROOT"

echo -e "${BOLD}${BLUE}Service Restart After Secret Rotation${NC}"
echo -e "${BLUE}======================================${NC}\n"

# Function to check if a service is running
is_service_running() {
    local service=$1
    docker compose ps --format json "$service" 2>/dev/null | \
        jq -r '.State' 2>/dev/null | grep -q "running"
}

# Function to wait for service to be healthy
wait_for_healthy() {
    local service=$1
    local timeout=$2
    local elapsed=0
    local interval=2

    echo -e "${CYAN}  Waiting for ${service} to become healthy...${NC}"

    while [ $elapsed -lt $timeout ]; do
        # Check if service has health check
        local health=$(docker compose ps --format json "$service" 2>/dev/null | \
                      jq -r '.Health' 2>/dev/null)

        if [ "$health" = "healthy" ] || [ "$health" = "null" ] || [ -z "$health" ]; then
            echo -e "${GREEN}  ✓ ${service} is healthy${NC}"
            return 0
        fi

        if [ "$health" = "unhealthy" ]; then
            echo -e "${RED}  ✗ ${service} is unhealthy${NC}"
            return 1
        fi

        sleep $interval
        elapsed=$((elapsed + interval))
    done

    echo -e "${YELLOW}  ⚠ ${service} health check timeout${NC}"
    return 1
}

# Function to restart a service
restart_service() {
    local service=$1

    echo -e "${BLUE}Restarting ${service}...${NC}"

    # Check if service exists
    if ! docker compose config --services | grep -q "^${service}$"; then
        echo -e "${YELLOW}  ⊘ Service ${service} not found in compose file${NC}"
        return 0
    fi

    # Restart the service
    if docker compose restart "$service" 2>&1; then
        echo -e "${GREEN}  ✓ ${service} restarted${NC}"

        # Wait for health check if not skipped
        if [ "$SKIP_HEALTHCHECK" = false ]; then
            wait_for_healthy "$service" "$TIMEOUT" || true
        fi

        return 0
    else
        echo -e "${RED}  ✗ Failed to restart ${service}${NC}"
        return 1
    fi
}

# Get list of services to restart
if [ "$RESTART_ALL" = true ]; then
    echo -e "${YELLOW}Restarting ALL services...${NC}\n"

    # Define restart order based on dependencies
    # Core infrastructure first
    RESTART_ORDER=(
        # Supabase core
        "supabase-db"
        "supabase-vector"
        "supabase-analytics"

        # Supabase services
        "supabase-auth"
        "supabase-rest"
        "supabase-realtime"
        "supabase-meta"
        "supabase-storage"
        "supabase-imgproxy"
        "supabase-edge-functions"
        "supabase-pooler"
        "supabase-kong"
        "supabase-studio"

        # Application services
        "n8n"
        "nocodb"
        "backup"

        # AI services
        "crawl4ai"
        "whisperx"
        "kokoro-fastapi-gpu"
        "open-webui"
        "comfyui"
        "ovi"
        "wan2gp"
        "infinitetalk"
        "yttools"

        # Infrastructure
        "nginx"
        "progress-tracker"
        "service-status"
    )
else
    # Check if there's a recent backup with metadata
    BACKUP_DIR="$PROJECT_ROOT/backups/secrets"
    LATEST_BACKUP=$(find "$BACKUP_DIR" -maxdepth 1 -type d -name "secrets-backup-*" 2>/dev/null | sort -r | head -n 1)

    if [ -n "$LATEST_BACKUP" ] && [ -f "$LATEST_BACKUP/metadata.json" ]; then
        echo -e "${BLUE}Reading affected services from latest backup metadata...${NC}\n"

        # Extract affected services from metadata
        AFFECTED_SERVICES=$(jq -r '.affected_services[]?' "$LATEST_BACKUP/metadata.json" 2>/dev/null || echo "")

        if [ -z "$AFFECTED_SERVICES" ]; then
            echo -e "${YELLOW}No affected services found in metadata${NC}"
            echo -e "${YELLOW}Use --all to restart all services${NC}"
            exit 0
        fi

        # Convert to array and deduplicate
        mapfile -t RESTART_ORDER < <(echo "$AFFECTED_SERVICES" | sort -u)

        echo -e "${CYAN}Affected services (${#RESTART_ORDER[@]})${NC}:"
        printf '  • %s\n' "${RESTART_ORDER[@]}"
        echo
    else
        echo -e "${YELLOW}No recent backup metadata found${NC}"
        echo -e "${YELLOW}Use --all to restart all services${NC}"
        exit 1
    fi
fi

# Save pre-restart state
echo -e "${BLUE}Saving pre-restart service state...${NC}"
STATE_FILE="$PROJECT_ROOT/backups/service-state-$(date +%Y%m%d-%H%M%S).json"
"$SCRIPT_DIR/check-services.py" --save "$STATE_FILE" > /dev/null 2>&1 || true
echo

# Restart services in order
FAILED_SERVICES=()
RESTARTED_COUNT=0

for service in "${RESTART_ORDER[@]}"; do
    if restart_service "$service"; then
        RESTARTED_COUNT=$((RESTARTED_COUNT + 1))
    else
        FAILED_SERVICES+=("$service")
    fi
    echo
done

# Print summary
echo -e "${BOLD}${BLUE}========================================${NC}"
echo -e "${BOLD}Restart Summary${NC}"
echo -e "${BOLD}${BLUE}========================================${NC}\n"

echo -e "${GREEN}Successfully restarted: ${RESTARTED_COUNT}${NC}"

if [ ${#FAILED_SERVICES[@]} -gt 0 ]; then
    echo -e "${RED}Failed to restart: ${#FAILED_SERVICES[@]}${NC}"
    for service in "${FAILED_SERVICES[@]}"; do
        echo -e "  ${RED}• ${service}${NC}"
    done
    echo
fi

# Run health check
if [ "$SKIP_HEALTHCHECK" = false ]; then
    echo -e "${BLUE}Running post-restart health check...${NC}\n"

    if "$SCRIPT_DIR/check-services.py" --compare "$STATE_FILE"; then
        echo -e "${GREEN}✓ All services healthy after restart${NC}\n"
    else
        echo -e "${YELLOW}⚠ Some services may need attention${NC}\n"
    fi
fi

# Next steps
echo -e "${BOLD}Next Steps:${NC}"
echo -e "  1. Verify services: ${CYAN}./scripts/check-services.py${NC}"
echo -e "  2. Check logs: ${CYAN}docker compose logs -f [service-name]${NC}"

if [ ${#FAILED_SERVICES[@]} -gt 0 ]; then
    echo -e "  3. ${YELLOW}Investigate failed services or restore from backup${NC}"
    echo -e "     ${CYAN}./scripts/restore-secrets.py --latest${NC}"
fi

echo

# Exit with error if any services failed
if [ ${#FAILED_SERVICES[@]} -gt 0 ]; then
    exit 1
fi

exit 0
