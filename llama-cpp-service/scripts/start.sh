#!/bin/bash
set -e

echo "Starting llama.cpp server..."
echo "Model path: $MODEL_PATH"
echo "Context size: $CONTEXT_SIZE"
echo "GPU layers: $N_GPU_LAYERS"
echo "HF Home: $HF_HOME"

# Check if model exists, if not provide instructions
if [ ! -f "$MODEL_PATH" ]; then
    echo "ERROR: Model not found at $MODEL_PATH"
    echo ""
    echo "To download Qwen3-VL-30B-A3B GGUF model:"
    echo "  Run from host: ./llama-cpp-service/download-model.sh"
    echo ""
    echo "Or manually via docker exec:"
    echo "  docker exec llama-cpp huggingface-cli download \\"
    echo "    Qwen/Qwen3-VL-30B-A3B-Instruct-GGUF \\"
    echo "    qwen3-vl-30b-a3b-instruct-q4_k_m.gguf"
    echo ""
    echo "Model will be downloaded to shared HF cache at:"
    echo "  $HF_HOME/hub/models--Qwen--Qwen3-VL-30B-A3B-Instruct-GGUF/"
    echo ""
    echo "Waiting for model to be available..."
    while [ ! -f "$MODEL_PATH" ]; do
        sleep 10
    done
fi

# Enable TF32 for RTX 5090 performance boost
export CUDA_ALLOW_TF32=1

# Start llama-server with OpenAI-compatible API
cd /app/llama.cpp
exec ./build/bin/llama-server \
    --model "$MODEL_PATH" \
    --host "$HOST" \
    --port "$PORT" \
    --ctx-size "$CONTEXT_SIZE" \
    --n-gpu-layers "$N_GPU_LAYERS" \
    --parallel 1 \
    --cont-batching \
    --flash-attn \
    --metrics \
    --log-format text \
    --verbose
