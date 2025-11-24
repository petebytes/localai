#!/bin/sh
# Docker entrypoint wrapper to install custom nodes before starting n8n

set -e

echo "=== n8n Custom Startup ==="

# Install custom nodes (script runs as root, handles chown internally)
if [ -d "/custom_code/n8n-nodes" ]; then
    echo "Installing custom nodes..."
    /usr/local/bin/install-custom-nodes.sh
fi

echo "=== Starting n8n ==="

# Switch to node user and start n8n
# The Dockerfile already sets USER node, so just exec directly
exec tini -- /docker-entrypoint.sh "$@"
