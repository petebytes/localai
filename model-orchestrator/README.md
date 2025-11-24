# Model Orchestrator

FastAPI service for managing GPU memory and model lifecycle across LocalAI services.

## Features

- Real-time GPU memory monitoring via NVML
- Explicit model load/unload tracking
- Service health verification
- OpenAPI documentation at `/docs`

## API Endpoints

### `GET /models/status`

Get current GPU memory usage and loaded models.

**Response:**
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

### `POST /models/load`

Load a model into GPU memory.

**Request:**
```json
{
  "model": "qwen3-vl-30b",
  "service": "llama-cpp",
  "priority": 10
}
```

**Response:**
```json
{
  "model": "qwen3-vl-30b",
  "service": "llama-cpp",
  "loaded_at": "2025-01-15T10:30:00",
  "status": "loaded"
}
```

### `POST /models/unload`

Unload a model from GPU memory.

**Request:**
```json
{
  "model": "qwen3-vl-30b",
  "force": false
}
```

**Response:**
```json
{
  "status": "unload_requested",
  "model": "qwen3-vl-30b",
  "service": "llama-cpp",
  "note": "Stop llama-cpp container to fully free VRAM"
}
```

## Usage in n8n Workflows

### Pattern: Load → Use → Unload

```javascript
// 1. Check current GPU status
const statusResponse = await fetch('http://orchestrator:8000/models/status');
const status = await statusResponse.json();
console.log(`Free VRAM: ${status.free_mb}MB`);

// 2. Load model if needed
const loadResponse = await fetch('http://orchestrator:8000/models/load', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    model: 'qwen3-vl-30b',
    service: 'llama-cpp',
    priority: 10
  })
});

// 3. Use the model
const chatResponse = await fetch('http://llama-cpp:8000/v1/chat/completions', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    model: 'qwen3-vl-30b',
    messages: [{role: 'user', content: 'Hello!'}]
  })
});

// 4. Unload when done (optional - can keep loaded for next request)
await fetch('http://orchestrator:8000/models/unload', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({model: 'qwen3-vl-30b'})
});
```

## Supported Services

| Service | Model | VRAM (4-bit) | Notes |
|---------|-------|--------------|-------|
| llama-cpp | qwen3-vl-30b | ~17GB | Multimodal + tool calling |
| whisperx | large-v3 | ~6GB | Transcription |
| ovi | ovi-11b | ~22GB | Video generation |
| wan | wan2.1-14b | ~28GB | Video generation |
| infinitetalk | infinitefalk | ~8GB | Audio-driven dubbing |

## VRAM Budget Guidelines

With RTX 5090 (32GB total):

- **Qwen3-VL alone**: 17GB used, 15GB free for other tasks
- **Qwen3-VL + WhisperX**: 23GB used, 9GB free
- **Wan2.1-14B alone**: 28GB used, 4GB free (tight!)
- **Ovi alone**: 22GB used, 10GB free

**Recommendation**: Keep only 1-2 large models loaded simultaneously. Use orchestrator to explicitly unload before loading heavy models.

## Environment Variables

- `HOST`: Server host (default: `0.0.0.0`)
- `PORT`: Server port (default: `8000`)

## Docker Integration

The orchestrator runs as a sidecar service monitoring GPU state. It doesn't directly control containers (that's Docker's job), but provides:

1. **Visibility**: Track which models are expected to be loaded
2. **Coordination**: n8n workflows query before starting GPU tasks
3. **Safety**: Check free VRAM before loading heavy models

## Development

### Local Testing

```bash
cd model-orchestrator
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### API Documentation

Once running, visit: `http://localhost:8000/docs`

## Troubleshooting

### NVML not available
- Ensure NVIDIA drivers installed
- Check container has GPU access: `docker run --gpus all`

### Service health check fails
- Verify service is running: `docker ps`
- Check service logs: `docker logs <service>`
- Test endpoint manually: `curl http://<service>:port/health`

### Models not unloading
- llama-cpp requires container stop to free VRAM fully
- Other services may lazy-unload after timeout
- Use `nvidia-smi` to verify actual GPU memory usage
