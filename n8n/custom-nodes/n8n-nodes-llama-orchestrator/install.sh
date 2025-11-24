#!/bin/bash
# Install n8n-nodes-llama-orchestrator into running n8n container

set -e

echo "🔨 Building n8n-nodes-llama-orchestrator..."

# Install dependencies and build
pnpm install
pnpm build

echo ""
echo "✅ Build complete!"
echo ""
echo "📦 To install in n8n:"
echo ""
echo "Option 1 - Auto-installation (if n8n is configured to auto-install):"
echo "  - n8n will detect this node in /custom_code/n8n-nodes/"
echo "  - Restart n8n: docker compose restart n8n"
echo ""
echo "Option 2 - Manual installation in n8n container:"
echo "  docker exec -it n8n sh -c 'cd /custom_code/n8n-nodes/n8n-nodes-llama-orchestrator && npm install'"
echo "  docker compose restart n8n"
echo ""
echo "Option 3 - Install from n8n UI:"
echo "  Settings → Community Nodes → Install"
echo "  Enter package name: /custom_code/n8n-nodes/n8n-nodes-llama-orchestrator"
echo ""
echo "After installation, the 'Llama Orchestrator' node will appear in the node palette."
