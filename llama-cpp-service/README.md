# llama.cpp Service

High-performance llama.cpp server compiled from source with CUDA 12.8 optimizations for RTX 5090.

## Features

- Built with CUDA support (sm_120 architecture for RTX 5090 Blackwell)
- OpenAI-compatible API at `/v1/chat/completions`
- Flash attention enabled for faster inference
- Continuous batching for better throughput
- Metrics endpoint for monitoring

## Model Management

### Download Qwen3-VL-30B Model

The model is automatically downloaded to the shared HuggingFace cache (`hf-cache` volume), which is shared across all AI services to prevent re-downloading.

```bash
# From host machine - recommended method
./llama-cpp-service/download-model.sh

# Or manually via docker exec
docker exec llama-cpp huggingface-cli download \
  Qwen/Qwen3-VL-30B-A3B-Instruct-GGUF \
  qwen3-vl-30b-a3b-instruct-q4_k_m.gguf
```

The model will be stored at:
```
/data/.huggingface/hub/models--Qwen--Qwen3-VL-30B-A3B-Instruct-GGUF/
```

### Model Requirements

- **Qwen3-VL-30B (4-bit)**: ~17GB VRAM
- **Context**: 8192 tokens (configurable via CONTEXT_SIZE env var)
- **Inference**: ~3B active parameters (MoE architecture)

## API Usage

### OpenAI-Compatible Chat Completion

```bash
curl https://llama.lan/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-vl-30b",
    "messages": [
      {"role": "user", "content": "What is in this image?", "images": ["base64_image_data"]}
    ],
    "temperature": 0.7,
    "max_tokens": 1000
  }'
```

### With Tools/Functions

```bash
curl https://llama.lan/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-vl-30b",
    "messages": [
      {"role": "user", "content": "What is the weather in San Francisco?"}
    ],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get weather for a location",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {"type": "string"}
          },
          "required": ["location"]
        }
      }
    }]
  }'
```

## Environment Variables

- `MODEL_PATH`: Path to GGUF model file in HF cache (default: `/data/.huggingface/hub/models--Qwen--Qwen3-VL-30B-A3B-Instruct-GGUF/snapshots/latest/qwen3-vl-30b-a3b-instruct-q4_k_m.gguf`)
- `HOST`: Server host (default: `0.0.0.0`)
- `PORT`: Server port (default: `8000`)
- `CONTEXT_SIZE`: Context window size (default: `8192`)
- `N_GPU_LAYERS`: GPU layers to offload (default: `99` = all)
- `HF_HOME`: HuggingFace cache directory

## Performance Tuning

### For Larger Context Windows

```yaml
environment:
  - CONTEXT_SIZE=32768  # Up to 256K supported by Qwen3-VL
```

### For Lower VRAM Usage

```yaml
environment:
  - N_GPU_LAYERS=40  # Offload only some layers to GPU
  - CONTEXT_SIZE=4096  # Reduce context size
```

## Monitoring

- **Health**: `GET /health`
- **Metrics**: `GET /metrics` (Prometheus format)
- **Models**: `GET /v1/models`

## Integration with Model Orchestrator

The orchestrator service manages loading/unloading via:

```python
# Load model (llama.cpp loads on startup automatically)
# Just ensure container is running

# Unload model (stop container to free VRAM)
requests.post("http://orchestrator.lan/models/unload", json={"model": "qwen3-vl-30b"})
```

## Troubleshooting

### Model not loading
Check logs: `docker logs llama-cpp`
Ensure model file exists in shared HF cache:
```bash
docker exec llama-cpp ls -la /data/.huggingface/hub/models--Qwen--Qwen3-VL-30B-A3B-Instruct-GGUF/
```

### Out of memory
- Reduce `N_GPU_LAYERS` or `CONTEXT_SIZE`
- Use model orchestrator to unload other services first

### Slow inference
- Verify GPU is being used: check `nvidia-smi` shows llama-server process
- Check Flash Attention is enabled in logs
- Ensure TF32 is enabled (automatic on RTX 5090)
