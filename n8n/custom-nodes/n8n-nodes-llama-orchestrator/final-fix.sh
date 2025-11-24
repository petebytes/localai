#!/bin/bash
# Final fix - remove node_modules and let n8n install fresh

set -e

echo "🧹 Removing node_modules and lock files completely..."
rm -rf node_modules package-lock.json

echo ""
echo "✅ Cleaned! Now n8n will install fresh when it starts."
echo ""
echo "🔄 Restarting n8n..."
cd /mnt/ai-data/code/localai
docker compose restart n8n

echo ""
echo "⏳ Waiting for n8n to start (30 seconds)..."
sleep 30

echo ""
echo "📋 Checking if installation succeeded..."
docker logs n8n 2>&1 | tail -30 | grep -A 3 "llama-orchestrator"

echo ""
echo "If you see '✓ n8n-nodes-llama-orchestrator installed successfully', it worked!"
echo "Otherwise, check the full logs with: docker logs n8n"
