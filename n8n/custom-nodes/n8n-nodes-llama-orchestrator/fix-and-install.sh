#!/bin/bash
# Fix and install n8n-nodes-llama-orchestrator

set -e

echo "🧹 Cleaning up node_modules and lock files..."
rm -rf node_modules package-lock.json

echo ""
echo "📦 Installing dependencies with npm (legacy peer deps)..."
npm install --legacy-peer-deps

echo ""
echo "🔨 Building the node..."
npm run build

echo ""
echo "✅ Build complete! Now restarting n8n..."
docker compose restart n8n

echo ""
echo "⏳ Waiting for n8n to start..."
sleep 20

echo ""
echo "📋 Checking n8n logs..."
docker logs n8n --tail 30 | grep -A 3 "llama-orchestrator"

echo ""
echo "✅ Done! The 'Llama Orchestrator' node should now be available in n8n."
echo ""
echo "🌐 Open n8n at: https://n8n.lan"
echo ""
echo "To verify the node is loaded:"
echo "  1. Open n8n in your browser"
echo "  2. Create a new workflow"
echo "  3. Search for 'Llama Orchestrator' in the node panel"
