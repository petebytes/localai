# llama.cpp + Model Orchestrator Setup

Quick setup guide for the new chat endpoint with multimodal support.

## What Was Added

1. **llama.cpp service** - High-performance LLM server (compiled from source for RTX 5090)
2. **model-orchestrator** - GPU memory management API
3. **Qwen3-VL-30B** - Multimodal chat model (17GB VRAM, vision + tool calling)

## Quick Start

### 1. Build and Start Services

```bash
# Build llama.cpp from source (takes ~5 minutes)
docker compose build llama-cpp

# Build orchestrator
docker compose build model-orchestrator

# Start both services
docker compose up -d llama-cpp model-orchestrator

# Restart nginx to pick up new routes
docker compose restart nginx
```

### 2. Download the Model

```bash
# Run the download script
./llama-cpp-service/download-model.sh
```

This will:
- Download Qwen3-VL-30B (4-bit, ~17GB) to shared HF cache
- Skip download if model already exists (shared across services)
- Restart llama-cpp to load the model
- Wait for service to be ready

**Note**: The model is stored in the `hf-cache` Docker volume, shared with all other AI services (WhisperX, Ovi, etc.) to prevent re-downloading.

### 3. Test the Setup

```bash
# Check GPU status
curl https://orchestrator.lan/models/status | jq

# Test chat endpoint
curl https://llama.lan/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-vl-30b",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }' | jq
```

## Service URLs

- **Chat API**: `https://llama.lan/v1/chat/completions`
- **Orchestrator**: `https://orchestrator.lan/models/status`
- **API Docs**: `https://orchestrator.lan/docs`

## n8n Integration

Import the example workflow:
1. Open n8n: `https://n8n.lan`
2. Import: `custom_code/n8n/workflows/llama-chat-example.json`
3. Test the workflow

## File Structure

```
llama-cpp-service/
├── Dockerfile              # Builds llama.cpp from source
├── scripts/start.sh        # Startup script
├── download-model.sh       # Model download helper
└── README.md              # Service documentation

model-orchestrator/
├── Dockerfile             # FastAPI service
├── requirements.txt       # Python dependencies
├── app/main.py           # Orchestrator API
└── README.md             # Service documentation

custom_code/
└── docs/
    └── LLAMA_CPP_INTEGRATION.md  # Complete integration guide
└── n8n/workflows/
    └── llama-chat-example.json   # Example n8n workflow
```

## Configuration

All configuration in `docker-compose.yml`:

```yaml
llama-cpp:
  environment:
    - MODEL_PATH=/models/qwen3-vl-30b-q4_k_m.gguf
    - CONTEXT_SIZE=8192  # Increase for longer contexts
    - N_GPU_LAYERS=99    # All layers on GPU
```

## Memory Usage

- **Qwen3-VL-30B**: 17GB VRAM
- **Leaves**: 15GB free for other services
- **Compatible with**: WhisperX, smaller models
- **Not compatible with**: Wan2.1-14B (unload first)

## Troubleshooting

### Build fails
```bash
# Check CUDA version
docker run --rm --gpus all nvidia/cuda:12.8.0-devel-ubuntu22.04 nvcc --version

# Rebuild with verbose output
docker compose build --no-cache --progress=plain llama-cpp
```

### Model download fails
```bash
# Manual download (will use shared HF cache)
docker exec llama-cpp huggingface-cli download \
  Qwen/Qwen3-VL-30B-A3B-Instruct-GGUF \
  qwen3-vl-30b-a3b-instruct-q4_k_m.gguf

# Then restart to load the model
docker compose restart llama-cpp
```

### Service won't start
```bash
# Check logs
docker logs llama-cpp

# Check GPU access
docker exec llama-cpp nvidia-smi

# Verify model exists in shared cache
docker exec llama-cpp ls -la /data/.huggingface/hub/models--Qwen--Qwen3-VL-30B-A3B-Instruct-GGUF/
```

### Out of memory
```bash
# Check what's using GPU
nvidia-smi

# Unload other services
curl -X POST https://orchestrator.lan/models/unload \
  -H "Content-Type: application/json" \
  -d '{"model": "wan2.1-14b"}'
```

## Next Steps

1. ✅ Build and start services
2. ✅ Download model
3. ✅ Test chat endpoint
4. ✅ Import n8n example workflow
5. 📖 Read full documentation: `custom_code/docs/LLAMA_CPP_INTEGRATION.md`
6. 🔧 Customize for your use case

## Performance Notes

- **First request**: 2-5s (model loading)
- **Subsequent requests**: <1s for short responses
- **Context window**: 8K tokens (expandable to 256K)
- **Speed**: ~1.8x faster than Ollama (built from source)
- **Flash Attention**: Enabled automatically
- **TF32 Tensor Cores**: Active on RTX 5090

## Documentation

- **Integration Guide**: `custom_code/docs/LLAMA_CPP_INTEGRATION.md`
- **llama.cpp Service**: `llama-cpp-service/README.md`
- **Model Orchestrator**: `model-orchestrator/README.md`
- **Example Workflow**: `custom_code/n8n/workflows/llama-chat-example.json`

## Support

Check logs for issues:
```bash
docker logs llama-cpp
docker logs model-orchestrator
docker logs nginx | grep llama
```

GPU status:
```bash
nvidia-smi
curl https://orchestrator.lan/models/status
```
