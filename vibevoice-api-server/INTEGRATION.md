# VibeVoice API Server - Integration Guide

## Overview

The VibeVoice API Server is **fully integrated** into the Local AI Services infrastructure. It shares models, caches, and uses the same nginx reverse proxy as other services.

## Integration Summary

### ✅ Completed Integrations

1. **Docker Compose Integration**
   - Added to `docker-compose.yml` as `vibevoice-api` service
   - Shares GPU with other services (RTX 5090 optimized)
   - Uses CUDA 12.8 for compatibility

2. **Shared Resources**
   - **Models Directory**: `/workspace/ComfyUI/models/vibevoice` (shared with ComfyUI)
   - **HuggingFace Cache**: `hf-cache` volume (prevents re-downloading)
   - **PyTorch Cache**: `torch-cache` volume (prevents re-downloading)
   - **Output Directory**: `./vibevoice-api-server/output`

3. **NGINX Configuration**
   - **Domain**: `https://vibevoice.lan`
   - **API Endpoints**: `https://vibevoice.lan/api/*`
   - **Documentation**: `https://vibevoice.lan/docs`
   - **CORS Enabled**: Full cross-origin support
   - **Timeout**: 600 seconds for long generations
   - **Max Upload Size**: 100MB for voice samples

4. **Service Directory Integration**
   - **Listed on**: `https://raven.lan` directory page
   - **Section**: Backend Services
   - **Status Monitoring**: Auto-detected health checks
   - **Features Highlighted**: Voice cloning, multi-speaker, streaming

## Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **API Documentation** | `https://vibevoice.lan/docs` | Swagger UI (auto-redirects from `/`) |
| **ReDoc** | `https://vibevoice.lan/redoc` | Alternative API documentation |
| **OpenAPI Schema** | `https://vibevoice.lan/openapi.json` | OpenAPI 3.0 schema |
| **Health Check** | `https://vibevoice.lan/api/health` | Service health status |
| **Service Directory** | `https://raven.lan` | All services overview |

## Quick Start

### 1. Ensure Models are Available

Models should be in `ComfyUI/models/vibevoice/`:

```bash
cd ComfyUI/models
mkdir -p vibevoice
cd vibevoice

# Download VibeVoice-1.5B (5.4GB - fastest)
git clone https://huggingface.co/microsoft/VibeVoice-1.5B

# Or VibeVoice-Large (18.7GB - best quality)
# git clone https://huggingface.co/microsoft/VibeVoice-Large
```

### 2. Start the Service

```bash
# From main project directory
docker-compose up -d vibevoice-api

# Check logs
docker-compose logs -f vibevoice-api
```

### 3. Test the API

```bash
# Health check
curl https://vibevoice.lan/api/health

# Generate speech
curl -X POST "https://vibevoice.lan/api/tts" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello from VibeVoice!",
    "model": "VibeVoice-1.5B"
  }' | jq -r '.audio_base64' | base64 -d > output.wav
```

## Architecture Benefits

### Shared Model Cache
- VibeVoice models downloaded once
- Shared between ComfyUI and VibeVoice API
- Saves disk space and download time

### Shared Transformers Cache
- `hf-cache` volume shared across all services
- `torch-cache` volume shared across all services
- Prevents duplicate model downloads
- Reduces startup time

### Performance Optimizations
- RTX 5090 specific CUDA 12.8
- `expandable_segments:True` for memory efficiency
- `CUDA_MODULE_LOADING=LAZY` for faster startup
- Flash Attention 2 supported (if configured)

## Service Management

### Start/Stop

```bash
# Start service
docker-compose up -d vibevoice-api

# Stop service
docker-compose stop vibevoice-api

# Restart service
docker-compose restart vibevoice-api

# View logs
docker-compose logs -f vibevoice-api
```

### Resource Usage

- **Memory**: 6-20GB VRAM (depends on model)
- **Startup Time**: 60-120 seconds (model loading)
- **Port**: 8000 (internal), 443 (external via nginx)
- **GPU**: Shared RTX 5090 (count: 1)

## API Features

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/models` | GET | List available models |
| `/api/models/{model}/load` | POST | Pre-load a specific model |
| `/api/models/{model}/unload` | POST | Unload model to free memory |
| `/api/models/current` | GET | Get currently loaded model |
| `/api/tts` | POST | Single-speaker TTS |
| `/api/tts/multi-speaker` | POST | Multi-speaker TTS |
| `/api/tts/stream` | POST | Streaming TTS (SSE) |

### Key Features

1. **Voice Cloning**: Upload 10-60s audio samples
2. **Multi-Speaker**: Up to 4 speakers with `[N]:` markers
3. **Streaming**: Server-Sent Events for low latency
4. **Model Management**: Load/unload/switch models dynamically
5. **Output Formats**: WAV, MP3, OGG
6. **LoRA Support**: Fine-tuned voice adapters

## Comparison with YouTube Downloader API

The VibeVoice API follows the same pattern as YouTube Downloader API:

| Feature | YouTube Downloader | VibeVoice API |
|---------|-------------------|---------------|
| **Framework** | FastAPI | FastAPI |
| **Domain** | `yttools.lan` | `vibevoice.lan` |
| **Ports** | 7860 (UI), 8456 (API) | 8000 (API) |
| **Documentation** | `/docs` | `/docs` |
| **Shared Cache** | ✅ `hf-cache`, `torch-cache` | ✅ `hf-cache`, `torch-cache` |
| **NGINX Proxy** | ✅ | ✅ |
| **Service Directory** | ✅ Backend Services | ✅ Backend Services |
| **Health Checks** | ✅ | ✅ |

## Troubleshooting

### Service Not Starting

```bash
# Check logs
docker-compose logs vibevoice-api

# Verify models directory
ls -la ComfyUI/models/vibevoice/

# Check GPU availability
docker-compose exec vibevoice-api nvidia-smi
```

### Model Not Found

```bash
# Ensure models are in correct directory
cd ComfyUI/models/vibevoice
git clone https://huggingface.co/microsoft/VibeVoice-1.5B

# Restart service
docker-compose restart vibevoice-api
```

### Out of Memory

```bash
# Use smaller or quantized model
# Edit DEFAULT_MODEL in docker-compose.yml:
# VibeVoice-1.5B (5.4GB)
# VibeVoice-Large-Q4 (6.6GB)
# VibeVoice-Large-Q8 (11.6GB)
```

## Production Deployment

The service is **production-ready** with:

- ✅ Health checks every 30 seconds
- ✅ Automatic restart on failure
- ✅ GPU resource limits
- ✅ Graceful shutdown
- ✅ Request logging
- ✅ CORS configuration
- ✅ SSL/TLS via NGINX
- ✅ API documentation
- ✅ Error handling

## Next Steps

1. Visit `https://raven.lan` to see the service directory
2. Click on "VibeVoice API" to view API documentation
3. Try the example requests in the API docs
4. Explore multi-speaker and voice cloning features
5. Integrate with your applications

---

**Status**: ✅ Fully Integrated and Production Ready

**Accessible at**: `https://vibevoice.lan`

**Documentation**: See full [README.md](README.md) for detailed usage examples
