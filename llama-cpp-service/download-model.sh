#!/bin/bash
# Download Qwen3-VL-30B model for llama.cpp
# Downloads to shared HF cache to prevent re-downloading across services
# Run this after starting the llama-cpp container

set -e

echo "🔽 Downloading Qwen3-VL-30B-A3B GGUF model..."
echo "   This will download ~17GB and may take 5-10 minutes"
echo "   Model will be saved to shared HuggingFace cache"
echo ""

# Check if container is running
if ! docker ps | grep -q llama-cpp; then
    echo "❌ Error: llama-cpp container is not running"
    echo "   Start it first with: docker compose up -d llama-cpp"
    exit 1
fi

# Check if model already exists
if docker exec llama-cpp test -f /data/.huggingface/hub/models--Qwen--Qwen3-VL-30B-A3B-Instruct-GGUF/snapshots/*/qwen3-vl-30b-a3b-instruct-q4_k_m.gguf 2>/dev/null; then
    echo "✅ Model already exists in shared HF cache!"
    echo "   Skipping download..."
    echo ""
else
    echo "📦 Starting download via HuggingFace CLI..."
    echo "   Downloading to: /data/.huggingface/hub/ (shared cache)"
    docker exec llama-cpp huggingface-cli download \
        Qwen/Qwen3-VL-30B-A3B-Instruct-GGUF \
        qwen3-vl-30b-a3b-instruct-q4_k_m.gguf

    echo ""
    echo "✅ Model downloaded to shared HuggingFace cache!"
fi

echo ""
echo "✅ Model downloaded successfully!"
echo ""
echo "🔄 Restarting llama-cpp service to load the model..."
docker compose restart llama-cpp

echo ""
echo "⏳ Waiting for service to be ready (this may take 30-60 seconds)..."
sleep 10

# Wait for health check
for i in {1..30}; do
    if curl -sf https://llama.lan/health > /dev/null 2>&1; then
        echo ""
        echo "✅ Service is ready!"
        echo ""
        echo "🎉 You can now use the chat endpoint:"
        echo "   https://llama.lan/v1/chat/completions"
        echo ""
        echo "📚 See documentation at:"
        echo "   custom_code/docs/LLAMA_CPP_INTEGRATION.md"
        exit 0
    fi
    echo -n "."
    sleep 2
done

echo ""
echo "⚠️  Service is taking longer than expected to start"
echo "   Check logs with: docker logs llama-cpp"
echo "   It may still be loading the model (first load can take 1-2 minutes)"
