# llama.cpp + Model Orchestrator Integration Guide

This guide covers the integration of the llama.cpp chat service and model orchestrator into the LocalAI platform.

## Overview

Two new services have been added to provide local multimodal chat capabilities with explicit GPU memory management:

1. **llama.cpp** - High-performance LLM inference server with multimodal support
2. **model-orchestrator** - GPU memory management and model lifecycle tracking

## Architecture

```
┌─────────────┐
│    n8n      │  Workflow orchestration
└──────┬──────┘
       │
       ├──────────────────────────────────────┐
       │                                      │
       ▼                                      ▼
┌──────────────────┐                 ┌────────────────┐
│ Model            │◄────monitors────┤ llama.cpp      │
│ Orchestrator     │                 │ (Qwen3-VL-30B) │
└──────┬───────────┘                 └────────┬───────┘
       │                                      │
       │                                      │
       └──────────────┬───────────────────────┘
                      │
                      ▼
               ┌──────────────┐
               │  RTX 5090    │
               │  (32GB VRAM) │
               └──────────────┘
```

## Services

### llama.cpp Service

**Purpose**: OpenAI-compatible chat endpoint with multimodal (vision) and tool calling support

**Model**: Qwen3-VL-30B-A3B (4-bit quantized)
- **Parameters**: 30.5B total, 3.3B active (MoE architecture)
- **VRAM**: ~17GB when loaded
- **Context**: 8K tokens (expandable to 256K)
- **Capabilities**:
  - Multimodal (text + images + video)
  - Tool/function calling
  - 32 languages

**Endpoints**:
- `https://llama.lan/v1/chat/completions` - OpenAI-compatible chat
- `https://llama.lan/v1/models` - List available models
- `https://llama.lan/health` - Health check
- `https://llama.lan/metrics` - Prometheus metrics

**Performance**:
- Built from source with CUDA 12.8 optimizations for RTX 5090
- ~1.8x faster than Ollama
- Flash attention enabled
- TF32 tensor cores active

### Model Orchestrator Service

**Purpose**: Track GPU memory usage and coordinate model loading/unloading

**Endpoints**:
- `https://orchestrator.lan/models/status` - Current GPU status
- `https://orchestrator.lan/models/load` - Load a model
- `https://orchestrator.lan/models/unload` - Unload a model
- `https://orchestrator.lan/health` - Health check
- `https://orchestrator.lan/docs` - OpenAPI documentation

**Capabilities**:
- Real-time VRAM monitoring via NVML
- Model lifecycle tracking
- Service health verification
- n8n workflow integration

## Getting Started

### 1. Download Model

Before starting the services, download the Qwen3-VL-30B model. The model is downloaded to the shared HuggingFace cache (`hf-cache` Docker volume), which is shared across all AI services to prevent re-downloading.

```bash
# Start the llama-cpp container first (it will wait for the model)
docker compose up -d llama-cpp

# Download the model (recommended method)
./llama-cpp-service/download-model.sh
```

The model will take ~5 minutes to download (~17GB) and will be stored in:
```
/data/.huggingface/hub/models--Qwen--Qwen3-VL-30B-A3B-Instruct-GGUF/
```

**Note**: If you've already downloaded this model for another service, it's already in the shared cache and won't be re-downloaded.

### 2. Start Services

```bash
# Start all services (including llama.cpp and orchestrator)
./start.sh

# Or start individually
docker compose up -d llama-cpp model-orchestrator
```

### 3. Verify Services

```bash
# Check llama.cpp is running
curl https://llama.lan/health

# Check orchestrator
curl https://orchestrator.lan/models/status
```

## Usage Examples

### Basic Chat Request

```bash
curl https://llama.lan/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-vl-30b",
    "messages": [
      {"role": "user", "content": "Explain quantum computing in simple terms"}
    ],
    "temperature": 0.7,
    "max_tokens": 500
  }'
```

### Multimodal Request (with Image)

```bash
curl https://llama.lan/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-vl-30b",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "What is in this image?"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
      ]
    }],
    "max_tokens": 300
  }'
```

### Tool Calling Request

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
        "description": "Get current weather for a location",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "City name"
            }
          },
          "required": ["location"]
        }
      }
    }],
    "tool_choice": "auto"
  }'
```

## n8n Workflow Integration

### Pattern: Explicit Model Management

```javascript
// Node 1: Check GPU Status
const statusResponse = await $http.get('http://model-orchestrator:8000/models/status');
const gpuStatus = statusResponse.json();

console.log(`Free VRAM: ${gpuStatus.free_mb}MB`);

// If VRAM < 18GB, unload other models first
if (gpuStatus.free_mb < 18000) {
  // Unload heavy models
  await $http.post('http://model-orchestrator:8000/models/unload', {
    json: { model: 'wan2.1-14b' }
  });
}

// Node 2: Load Model
await $http.post('http://model-orchestrator:8000/models/load', {
  json: {
    model: 'qwen3-vl-30b',
    service: 'llama-cpp',
    priority: 10
  }
});

// Node 3: Use Chat Endpoint
const chatResponse = await $http.post('http://llama-cpp:8000/v1/chat/completions', {
  json: {
    model: 'qwen3-vl-30b',
    messages: [
      { role: 'user', content: 'Analyze this workflow step' }
    ],
    temperature: 0.3
  }
});

const answer = chatResponse.json().choices[0].message.content;

// Node 4: Unload When Done (optional)
await $http.post('http://model-orchestrator:8000/models/unload', {
  json: { model: 'qwen3-vl-30b' }
});

return { answer };
```

### Example n8n Nodes Setup

1. **HTTP Request** → `GET http://model-orchestrator:8000/models/status`
2. **IF** → Check if `free_mb < 18000`
3. **HTTP Request** (conditional) → Unload other models
4. **HTTP Request** → Load Qwen3-VL
5. **HTTP Request** → Chat completion
6. **Code** → Process response
7. **HTTP Request** (optional) → Unload model

### Pre-built n8n Workflow

See `custom_code/n8n/workflows/llama-chat-example.json` for a complete example.

## VRAM Budget Guidelines

With RTX 5090 (32GB total):

| Configuration | VRAM Used | Free VRAM | Notes |
|---------------|-----------|-----------|-------|
| Qwen3-VL only | 17GB | 15GB | Plenty of room for other tasks |
| Qwen3-VL + WhisperX | 23GB | 9GB | Good for transcription + chat |
| Qwen3-VL + Ovi | 39GB | **-7GB** | ❌ Won't fit! Unload one first |
| Wan2.1-14B only | 28GB | 4GB | Tight, but works |

**Recommendation**:
- Keep Qwen3-VL loaded for quick chat responses
- Explicitly unload before starting Ovi/Wan2.1-14B
- Use orchestrator to verify VRAM before loading heavy models

## Performance Tuning

### Increase Context Window

```yaml
# docker-compose.yml
environment:
  - CONTEXT_SIZE=32768  # Up to 256K supported
```

Larger context uses more VRAM: 8K = 17GB, 32K = 19GB, 128K = 24GB

### Reduce VRAM Usage

```yaml
environment:
  - N_GPU_LAYERS=40  # Only offload some layers to GPU
  - CONTEXT_SIZE=4096  # Smaller context
```

### Optimize for Throughput

```yaml
environment:
  - CONTEXT_SIZE=8192
  - N_GPU_LAYERS=99  # All layers on GPU
  - CUDA_ALLOW_TF32=1  # Already enabled
```

## Monitoring

### Real-time GPU Usage

```bash
# Watch GPU memory
watch -n 1 nvidia-smi

# Or via orchestrator API
watch -n 1 'curl -s https://orchestrator.lan/models/status | jq'
```

### Service Logs

```bash
# llama.cpp logs
docker logs -f llama-cpp

# Orchestrator logs
docker logs -f model-orchestrator

# Check for errors
docker logs llama-cpp 2>&1 | grep -i error
```

### Prometheus Metrics

llama.cpp exposes metrics at `https://llama.lan/metrics`:

- `llamacpp_tokens_generated_total` - Total tokens generated
- `llamacpp_prompt_tokens_total` - Total prompt tokens processed
- `llamacpp_requests_total` - Total requests
- `llamacpp_requests_duration_seconds` - Request latency

## Troubleshooting

### Model Not Loading

**Symptom**: Container starts but health check fails

**Solutions**:
1. Check model exists in shared HF cache:
   ```bash
   docker exec llama-cpp ls -la /data/.huggingface/hub/models--Qwen--Qwen3-VL-30B-A3B-Instruct-GGUF/
   ```
2. Check logs: `docker logs llama-cpp`
3. Verify HF_HOME is set correctly: `docker exec llama-cpp env | grep HF_HOME`
4. Download model manually: `./llama-cpp-service/download-model.sh`

### Out of Memory

**Symptom**: `CUDA out of memory` in logs

**Solutions**:
1. Check what else is using GPU: `nvidia-smi`
2. Unload other models via orchestrator
3. Reduce `N_GPU_LAYERS` or `CONTEXT_SIZE`
4. Use orchestrator to coordinate: don't start llama-cpp while Wan2.1 is running

### Slow Inference

**Symptom**: Responses take >30s for short prompts

**Solutions**:
1. Verify GPU is being used: `nvidia-smi` should show llama-server process
2. Check Flash Attention is enabled in logs
3. Ensure TF32 is active: `CUDA_ALLOW_TF32=1` in environment
4. Try reducing context size if using very large contexts

### Service Not Reachable

**Symptom**: `502 Bad Gateway` from nginx

**Solutions**:
1. Check service is running: `docker ps | grep llama-cpp`
2. Check health: `docker exec llama-cpp curl localhost:8000/health`
3. Restart service: `docker compose restart llama-cpp`
4. Check nginx logs: `docker logs nginx | grep llama`

## API Reference

### llama.cpp OpenAI-Compatible API

Full OpenAI Chat Completions API supported:

**POST /v1/chat/completions**

Request body:
```json
{
  "model": "qwen3-vl-30b",
  "messages": [...],
  "temperature": 0.7,
  "max_tokens": 1000,
  "top_p": 0.9,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0,
  "stream": false,
  "tools": [...],
  "tool_choice": "auto"
}
```

Response:
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "qwen3-vl-30b",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Response text",
      "tool_calls": [...]
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 56,
    "completion_tokens": 31,
    "total_tokens": 87
  }
}
```

### Model Orchestrator API

**GET /models/status**

Response:
```json
{
  "total_mb": 32768,
  "used_mb": 17234,
  "free_mb": 15534,
  "utilization_percent": 45.2,
  "loaded_models": {
    "qwen3-vl-30b": {
      "model": "qwen3-vl-30b",
      "service": "llama-cpp",
      "loaded_at": "2025-01-15T10:30:00",
      "status": "loaded"
    }
  }
}
```

**POST /models/load**

Request:
```json
{
  "model": "qwen3-vl-30b",
  "service": "llama-cpp",
  "priority": 10
}
```

**POST /models/unload**

Request:
```json
{
  "model": "qwen3-vl-30b",
  "force": false
}
```

## Best Practices

1. **Always check VRAM before loading heavy models** - Use orchestrator status endpoint
2. **Explicitly unload models when done with long tasks** - Free VRAM for other services
3. **Keep llama.cpp loaded for interactive chat** - 2-5s cold start delay otherwise
4. **Use appropriate context sizes** - Larger context = more VRAM + slower inference
5. **Monitor via orchestrator** - Better visibility than guessing with nvidia-smi
6. **Coordinate in n8n workflows** - Add orchestrator calls before GPU-heavy tasks
7. **Use health checks** - Verify service is ready before sending requests

## Future Enhancements

- [ ] Automatic model downloading on first start
- [ ] Support for multiple GGUF models (Llama 3.2 3B for fast tool calling)
- [ ] LoRA adapter support
- [ ] Automatic VRAM-based model unloading (LRU policy)
- [ ] n8n custom nodes for orchestrator integration
- [ ] Grafana dashboard for GPU metrics

## Related Documentation

- [llama.cpp Service README](../../llama-cpp-service/README.md)
- [Model Orchestrator README](../../model-orchestrator/README.md)
- [Webhook Callback Pattern](./WEBHOOK_CALLBACK_PATTERN.md)
- [AI Capabilities Matrix](../../AI_CAPABILITIES_MATRIX.md)

## Support

For issues or questions:
1. Check logs: `docker logs llama-cpp` or `docker logs model-orchestrator`
2. Verify GPU access: `docker exec llama-cpp nvidia-smi`
3. Check orchestrator status: `curl https://orchestrator.lan/models/status`
4. Review this documentation
5. Open an issue with logs and configuration details
