# InfiniteTalk API Server

FastAPI wrapper for InfiniteTalk audio-driven talking head video generation.

## Overview

This service provides a REST API for generating 8-second talking head videos from audio and portrait images using the InfiniteTalk model.

## API Endpoints

### Health Check

```bash
GET /api/health
```

Response:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "gpu_available": true,
  "version": "1.0.0"
}
```

### Generate Video

```bash
POST /api/generate-video
Content-Type: application/json

{
  "audio_path": "/data/shared/audio/sample.wav",
  "image_path": "/data/shared/images/portrait.png",
  "prompt": "A professional speaker presenting content",
  "resolution": "infinitetalk-480",
  "seed": 42,
  "diffusion_steps": 40,
  "text_guide_scale": 5.0,
  "audio_guide_scale": 4.0,
  "motion_frame": 9,
  "use_color_correction": true
}
```

Response (after 3-5 minutes):
```json
{
  "video_path": "/output/infinitetalk_infinitetalk-480_A_professional_speaker_20251102_143022.mp4",
  "duration_seconds": 8.0,
  "resolution": "1024x576",
  "frame_count": 200,
  "metadata": {
    "seed": "42",
    "diffusion_steps": "40",
    "text_guide_scale": "5.0",
    "audio_guide_scale": "4.0",
    "resolution_bucket": "infinitetalk-480",
    "actual_resolution": "1024x576",
    "motion_frame": "9",
    "color_correction": "true",
    "timestamp": "20251102_143022"
  }
}
```

## Docker Usage

The service runs as part of the localai docker-compose stack:

```bash
# Build service (uses shared cuda-base image)
docker compose build infinitetalk-api

# Start service
docker compose up -d infinitetalk-api

# View logs
docker compose logs -f infinitetalk-api

# Restart service
docker compose restart infinitetalk-api
```

### Build Optimization

The Dockerfile uses several optimizations to reduce downloads and disk usage:

- **Shared base image**: Builds from `cuda-base:runtime-12.8` (saves ~5.7GB download)
- **Shared pip cache**: Uses `pip-cache-shared` mount (shares with other services)
- **Volume mounts**: InfiniteTalk source mounted from `./InfiniteTalk` (no code duplication)
- **Shared model cache**: `hf-cache` and `torch-cache` volumes shared across services

## Configuration

Environment variables (set in docker-compose.yml):

- `CKPT_DIR`: Path to Wan2.1-I2V-14B-480P checkpoint
- `WAV2VEC_DIR`: Path to Wav2Vec2 audio encoder
- `INFINITETALK_DIR`: Path to InfiniteTalk weights
- `NUM_PERSISTENT_PARAM_IN_DIT`: VRAM management (0 = minimum memory)
- `MOTION_FRAME`: Overlap frames for streaming (default: 9)
- `PORT`: API port (default: 8200)

## Model Loading

Models use lazy loading to allow fast startup:
- Container starts immediately without loading models
- Models load on first generation request (~2-3 minutes)
- Models stay in memory for subsequent requests

## Processing Time

- 8-second video @ 480P: ~3-5 minutes
- Resolution: 1024x576 (480P) or 1280x720 (720P)
- Frame rate: 25fps (200 frames for 8 seconds)

## GPU Requirements

- VRAM: ~24GB with `NUM_PERSISTENT_PARAM_IN_DIT=0`
- Compatible with RTX 5090 (32GB VRAM)
- CUDA 12.8 required

## File Sharing

Input files should be placed in shared volumes:
- Audio: `/data/shared/audio/`
- Images: `/data/shared/images/`

Output videos are saved to:
- `/output/` (mounted to host)

## Integration with n8n

The API is designed for n8n workflow integration:

1. Steps 1-2-3 provide audio and image paths
2. Step 4 calls `/api/generate-video` with paths
3. n8n waits for synchronous response (3-5 min)
4. Response includes video path for download

## Example Test

```bash
curl -X POST http://localhost:8200/api/generate-video \
  -H "Content-Type: application/json" \
  -d '{
    "audio_path": "/data/shared/audio/voice_cloned.wav",
    "image_path": "/data/shared/images/portrait.png",
    "prompt": "A professional speaker presenting",
    "resolution": "infinitetalk-480",
    "seed": 42
  }'
```

## Troubleshooting

### Models Not Loading

Check logs:
```bash
docker compose logs infinitetalk-api | grep -i "error\|failed"
```

### GPU Not Available

Verify CUDA access:
```bash
docker compose exec infinitetalk-api python3 -c "import torch; print(torch.cuda.is_available())"
```

### Out of Memory

Reduce VRAM usage:
- Set `NUM_PERSISTENT_PARAM_IN_DIT=0` (already default)
- Use 480P instead of 720P
- Ensure other GPU services free memory with `torch.cuda.empty_cache()`
