# Ovi API Server

FastAPI wrapper for Ovi 11B video+audio generation - provides REST API for programmatic access and automation workflows.

## Features

- **REST API**: OpenAPI-compatible endpoints for automation
- **Lazy Model Loading**: Models load on first request (saves startup time)
- **Quality Presets**: Optimized settings for different use cases
- **n8n Integration**: Designed for workflow orchestration
- **Dual Mode**: Text-to-Video (T2V) and Image-to-Video (I2V)
- **Synchronized Audio**: Generates video with matching audio track
- **High Quality**: Up to 1920x1080 resolution, 24 FPS

## Architecture

```
┌──────────────┐
│   n8n or     │  ← REST API calls (https://ovi-api.lan)
│ Application  │
└──────┬───────┘
       │ POST /api/generate-video
       v
┌──────────────┐
│  Ovi API     │  ← FastAPI wrapper (port 8300)
│  (Container) │
└──────┬───────┘
       │ Direct Python import
       v
┌──────────────┐
│OviFusionEngine│ ← Ovi 11B twin backbone model
│  (Lazy load)  │    (loads on first request)
└──────────────┘
```

## Quick Start

### Build and Deploy

```bash
# From localai root directory
docker compose build ovi-api
docker compose up -d ovi-api

# View logs
docker compose logs -f ovi-api

# Access API documentation
https://ovi-api.lan/docs
```

### Health Check

```bash
curl https://ovi-api.lan/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "model_loaded": false,  // true after first generation
  "gpu_available": true,
  "gpu_name": "NVIDIA GeForce RTX 5090",
  "version": "1.0.0"
}
```

## API Endpoints

### 1. Generate Video

**Endpoint:** `POST /api/generate-video`

**Description:** Generate 5-second video with synchronized audio from text prompt (and optional image).

**Modes:**
- **T2V (Text-to-Video)**: Generate video from text description only
- **I2V (Image-to-Video)**: Animate a static image with text description

**Text Prompt Format:**
- Use `<S>speech text<E>` to wrap dialogue
- Use `<AUDCAP>audio description<ENDAUDCAP>` for sound effects
- Example: `A singer performs. <S>Hello world!<E> <AUDCAP>Crowd cheering<ENDAUDCAP>`

#### Request Schema

```json
{
  "text_prompt": "string (required)",
  "image_path": "string (optional, required for I2V mode)",
  "mode": "t2v | i2v (default: t2v)",

  // Video configuration
  "video_height": 1080,
  "video_width": 1920,
  "video_seed": 100,

  // Sampling parameters
  "solver_name": "unipc | euler | dpm++ (default: unipc)",
  "sample_steps": 70,  // 20-100, higher = better quality
  "shift": 5.0,  // 0.0-20.0

  // Guidance scales
  "video_guidance_scale": 8.0,  // 0.0-10.0, 7-9 recommended
  "audio_guidance_scale": 7.0,  // 0.0-10.0, 6-8 recommended

  // Advanced
  "slg_layer": 11,  // -1 to disable
  "video_negative_prompt": "jitter, bad hands, blur, distortion",
  "audio_negative_prompt": "robotic, muffled, echo, distorted",

  // Preset (overrides individual params)
  "preset": "youtube-shorts-high | youtube-shorts-balanced | youtube-shorts-fast | square | widescreen | custom"
}
```

#### Response Schema

```json
{
  "video_path": "/output/ovi_t2v_concert_20251114_123456.mp4",
  "duration_seconds": 5.0,
  "frame_count": 121,
  "resolution": "1920x1080",
  "has_audio": true,
  "metadata": {
    "seed": "42",
    "steps": "70",
    "solver": "unipc",
    "video_guidance": "8.0",
    "audio_guidance": "7.0",
    "mode": "t2v",
    "preset": "youtube-shorts-high",
    "timestamp": "20251114_123456"
  }
}
```

### 2. Health Check

**Endpoint:** `GET /api/health`

Returns service status, model state, and GPU information.

### 3. API Information

**Endpoint:** `GET /`

Returns API metadata and available endpoints.

## Quality Presets

Optimized settings for different use cases:

| Preset | Resolution | Steps | Use Case | Generation Time |
|--------|-----------|-------|----------|-----------------|
| `youtube-shorts-high` | 1080×1920 | 70 | Best quality for YouTube Shorts | ~2-3 min |
| `youtube-shorts-balanced` | 1080×1920 | 50 | Balanced quality/speed | ~1-2 min |
| `youtube-shorts-fast` | 1080×1920 | 40 | Fast generation | ~1 min |
| `square` | 960×960 | 60 | Instagram, TikTok | ~1.5 min |
| `widescreen` | 720×1280 | 60 | 16:9 videos | ~1.5 min |
| `custom` | Custom | Custom | Full control | Varies |

## Usage Examples

### 1. Basic Text-to-Video (Python)

```python
import requests

response = requests.post("https://ovi-api.lan/api/generate-video", json={
    "text_prompt": "A concert stage glows with red lights. A singer grips the microphone and shouts, <S>This is the moment we've been waiting for!<E>. <AUDCAP>Electric guitar riffs, cheering crowd.<ENDAUDCAP>",
    "preset": "youtube-shorts-high"
})

result = response.json()
print(f"Video saved to: {result['video_path']}")
print(f"Duration: {result['duration_seconds']}s")
```

### 2. Image-to-Video with Custom Settings

```python
import requests

response = requests.post("https://ovi-api.lan/api/generate-video", json={
    "text_prompt": "A person speaks warmly. <S>Welcome to the future of AI video generation.<E>",
    "image_path": "/output/portrait.png",
    "mode": "i2v",
    "video_height": 1080,
    "video_width": 1920,
    "video_seed": 42,
    "sample_steps": 60,
    "video_guidance_scale": 7.5,
    "audio_guidance_scale": 6.5
})

result = response.json()
print(f"Generated: {result['video_path']}")
```

### 3. Using httpx (Async)

```python
import httpx

async def generate_video():
    async with httpx.AsyncClient(timeout=600.0) as client:
        response = await client.post(
            "https://ovi-api.lan/api/generate-video",
            json={
                "text_prompt": "A chef in a kitchen. <S>Today we're making the perfect pasta!<E>",
                "preset": "square"
            }
        )
        return response.json()
```

### 4. n8n Integration

**HTTP Request Node:**
```json
{
  "method": "POST",
  "url": "https://ovi-api.lan/api/generate-video",
  "authentication": "none",
  "timeout": 600000,
  "jsonParameters": true,
  "bodyParameters": {
    "text_prompt": "{{ $json.prompt }}",
    "preset": "youtube-shorts-balanced"
  }
}
```

**Workflow Example:**
```
Webhook → Claude (generate script) → Ovi API (video) → Save to NocoDB
```

### 5. Batch Generation Script

```python
import requests
import time

prompts = [
    "A sunset over the ocean. <AUDCAP>Waves crashing.<ENDAUDCAP>",
    "A city at night. <AUDCAP>Traffic sounds, sirens.<ENDAUDCAP>",
    "A forest in spring. <AUDCAP>Birds chirping.<ENDAUDCAP>"
]

for i, prompt in enumerate(prompts):
    print(f"Generating video {i+1}/{len(prompts)}...")

    response = requests.post("https://ovi-api.lan/api/generate-video", json={
        "text_prompt": prompt,
        "preset": "youtube-shorts-fast",
        "video_seed": i * 100
    }, timeout=600)

    result = response.json()
    print(f"✓ Saved: {result['video_path']}")

    # Wait a bit between requests to avoid overloading
    time.sleep(5)

print("All videos generated!")
```

## Integration with Shorts Generator

Add video generation to the shorts-generator workflow:

```python
# In custom_code/shorts-generator/api.py

import httpx

@app.post("/api/generate-video-short")
async def generate_video_short(request: VideoShortRequest):
    # 1. Generate quote via n8n → Claude
    quote_response = await n8n_client.trigger_workflow(...)
    quote = quote_response["quote"]

    # 2. Generate image via ComfyUI
    image_path = await comfyui_client.generate_image(quote)

    # 3. Generate video via Ovi API (NEW!)
    async with httpx.AsyncClient(timeout=600.0) as client:
        ovi_response = await client.post(
            "http://ovi-api:8300/api/generate-video",
            json={
                "text_prompt": f"{quote} <S>{quote}<E>",
                "image_path": image_path,
                "mode": "i2v",
                "preset": "square"
            }
        )

    video_data = ovi_response.json()
    return {
        "quote": quote,
        "image_path": image_path,
        "video_path": video_data["video_path"],
        "duration": video_data["duration_seconds"]
    }
```

## Environment Variables

Configure in `docker-compose.yml`:

```yaml
environment:
  # Ovi configuration
  - OVI_DIR=/workspace/ovi
  - OVI_CPU_OFFLOAD=true  # Enable CPU offload (required for 32GB VRAM)
  - OVI_FP8=false         # Enable FP8 quantization (720x720 only)
  - OVI_QINT8=false       # Enable QINT8 quantization
  - OVI_OUTPUT_DIR=/output

  # API server configuration
  - PORT=8300
  - HOST=0.0.0.0
```

## Performance

**Hardware:** RTX 5090 32GB VRAM

| Resolution | Steps | Mode | Generation Time | VRAM Usage |
|-----------|-------|------|-----------------|------------|
| 1920×1080 | 70 | T2V | ~2-3 min | ~28GB |
| 1920×1080 | 50 | T2V | ~1.5-2 min | ~28GB |
| 1920×1080 | 40 | T2V | ~1-1.5 min | ~28GB |
| 960×960 | 60 | T2V | ~1.5 min | ~24GB |
| 720×1280 | 60 | I2V | ~1.5 min | ~26GB |

**Optimizations:**
- CPU offload enabled for 32GB VRAM mode
- Lazy model loading (2-3 min on first request)
- Automatic GPU memory cleanup between requests

## Troubleshooting

### Service not starting

```bash
# Check logs
docker compose logs ovi-api

# Verify base Ovi image exists
docker images | grep ovi

# Rebuild if needed
docker compose build ovi-api --no-cache
```

### Model loading fails

```bash
# Ensure models are downloaded
ls -lh /mnt/ai-data/code/localai/ovi/ckpts/

# Check CUDA availability
docker exec ovi-api python -c "import torch; print(torch.cuda.is_available())"
```

### Generation timeout

- Default timeout: 600s (10 minutes)
- Increase if needed: `timeout=1200` in HTTP client
- Check GPU memory: `nvidia-smi`

### Out of memory

- Ensure CPU offload is enabled: `OVI_CPU_OFFLOAD=true`
- Close Ovi Gradio UI if running simultaneously
- Reduce resolution or steps

### Image file not found (I2V mode)

- Image path must be absolute path inside container
- Use shared volume: `/output/your-image.png`
- Verify file exists: `docker exec ovi-api ls -la /output/`

## API Documentation

Interactive API documentation available at:

- **Swagger UI**: https://ovi-api.lan/docs
- **ReDoc**: https://ovi-api.lan/redoc
- **OpenAPI JSON**: https://ovi-api.lan/openapi.json

## Monitoring

```bash
# Check service status
curl https://ovi-api.lan/api/health

# View real-time logs
docker compose logs -f ovi-api

# Check GPU usage
nvidia-smi -l 1
```

## Development

### Project Structure

```
ovi-api-server/
├── ovi_api_server/
│   ├── __init__.py           # Package version
│   ├── models.py             # Pydantic schemas
│   ├── generation.py         # VideoGenerator class
│   └── main.py               # FastAPI app
├── Dockerfile                # Container build
└── README.md                 # This file
```

### Local Development

```bash
# Install dependencies (requires Ovi environment)
cd ovi-api-server
pip install fastapi uvicorn pydantic httpx python-multipart

# Run locally (requires Ovi models)
export OVI_DIR=/workspace/ovi
export OVI_OUTPUT_DIR=/output
python -m uvicorn ovi_api_server.main:app --host 0.0.0.0 --port 8300
```

### Testing

```bash
# Test health endpoint
curl https://ovi-api.lan/api/health

# Test generation (quick preset)
curl -X POST https://ovi-api.lan/api/generate-video \
  -H "Content-Type: application/json" \
  -d '{
    "text_prompt": "A test video. <S>Hello world!<E>",
    "preset": "youtube-shorts-fast"
  }'
```

## Contributing

This service follows the InfiniteTalk API pattern for consistency. When making changes:

1. Update Pydantic models for schema changes
2. Add validation in `VideoGenerator.generate()`
3. Update this README with new examples
4. Test with different presets and modes

## License

Part of the LocalAI platform.

## Related Services

- **Ovi Gradio UI**: https://ovi.lan (interactive web interface)
- **InfiniteTalk API**: https://infinitetalk-api.lan (talking head videos)
- **Shorts Generator**: https://inspirational-shorts.lan (quote images)
- **n8n**: https://n8n.lan (workflow orchestration)

## Support

- **Logs**: `docker compose logs -f ovi-api`
- **Issues**: Check GPU memory, model files, and timeouts
- **Documentation**: https://ovi-api.lan/docs
