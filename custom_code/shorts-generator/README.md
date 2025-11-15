# Inspirational Shorts Generator

Gradio web interface for generating inspirational quote videos using n8n workflow orchestration with ComfyUI and Ovi 11B.

## Features

- **End-to-End Video Generation**: Quote → Image → Video with synchronized audio
- **AI-Powered Pipeline**: Claude Sonnet 4.5 + ComfyUI (HiDream) + Ovi 11B
- **TDD Implementation**: Comprehensive test suite with passing tests
- **n8n Integration**: Triggers existing n8n workflow with custom parameters
- **Real-time Status**: Polls execution status with streaming updates
- **Docker Ready**: Containerized with health checks
- **Multi-Modal Output**: Generates both static images and animated videos

## Architecture

```
┌──────────────┐
│  Gradio UI   │  ← User clicks "Generate"
│  (Port 7860) │
└──────┬───────┘
       │
       v
┌──────────────┐
│  FastAPI     │  ← Triggers n8n workflow
│  (Port 8000) │
└──────┬───────┘
       │
       v
┌──────────────┐
│     n8n      │  ← Orchestrates AI pipeline
│   Workflow   │
└──┬───┬───┬───┘
   │   │   │
   │   │   └─────────────────┐
   │   │                     │
   v   v                     v
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Claude     │  │   ComfyUI    │  │   Ovi 11B    │
│ Sonnet 4.5   │  │  + HiDream   │  │  Video+Audio │
└──────────────┘  └──────────────┘  └──────────────┘
   │                     │                  │
   │ Quote               │ Image            │ Video (10s)
   │ + Prompts           │ (9:16)           │ + Audio
   │                     │                  │
   └─────────────────────┴──────────────────┘
                         │
                         v
                  ┌──────────────┐
                  │  Downloads/  │  ← Image + Video saved locally
                  └──────────────┘
```

**Pipeline Steps:**
1. **Quote Generation** (Claude): Generates compassionate, trauma-informed quote
2. **Prompt Generation** (Claude): Creates image and video animation descriptions
3. **Image Generation** (ComfyUI + HiDream): Renders 9:16 portrait image
4. **Video Generation** (Ovi 11B): Animates image with synchronized speech and audio
5. **Delivery**: Downloads image and video to user

## TDD Workflow

Following strict TDD principles (Red-Green-Refactor):

1. **Red**: Write failing tests first
   - `test_models.py` - Pydantic schema validation (9 tests)
   - `test_n8n_client.py` - n8n API interaction (8 tests)
   - `test_api.py` - FastAPI endpoints (8 tests)

2. **Green**: Implement to pass tests
   - `models.py` - Request/response schemas
   - `n8n_client.py` - Async n8n API client
   - `api.py` - FastAPI REST endpoints

3. **Refactor**: Clean up with type checking
   - mypy in strict mode (0 errors)
   - ruff linting (all checks passed)

## Setup

### Environment Variables

Add to `.env` or docker-compose.yml:

```bash
# n8n Configuration
N8N_API_URL=http://n8n:5678
N8N_WEBHOOK_PATH=/webhook/shorts-generate
N8N_API_KEY=your_api_key_here

# Output paths
COMFYUI_OUTPUT_PATH=/workspace/ComfyUI/output  # Images
OVI_OUTPUT_PATH=/output  # Videos

# API configuration
API_BASE_URL=http://localhost:8000
```

**Note:** The workflow is triggered via webhook, no workflow ID needed.

### Docker Deployment

```bash
# Build and start
docker-compose up -d shorts-generator

# View logs
docker-compose logs -f shorts-generator

# Access UI
https://inspirational-shorts.lan
```

### Local Development

```bash
cd custom_code/shorts-generator

# Install dependencies
uv sync

# Run tests
uv run pytest -v

# Type check
uv run mypy *.py

# Lint
uv run ruff check *.py

# Run locally (requires n8n and comfyui running)
uv run python app.py
```

## Usage

1. Navigate to https://inspirational-shorts.lan
2. Click "Generate Quote, Image & Video"
3. Wait 3-5 minutes for generation:
   - Quote generation: ~5 seconds
   - Image generation: ~30-60 seconds
   - Video generation: ~2-4 minutes (10-second video)
4. View results:
   - **Quote**: Displayed in text box
   - **Image**: 9:16 portrait (downloadable)
   - **Video**: 10-second clip with synchronized audio (downloadable)

## n8n Workflow

The workflow orchestrates a complete video generation pipeline:

**Trigger:** Webhook at `/webhook/shorts-generate`

**Accepts:** POST with JSON:
```json
{
  "quote_system_prompt": "Quote generation instructions...",
  "image_system_prompt": "Image + video prompt generation instructions..."
}
```

**Pipeline Steps:**
1. **Quote Writer** (Claude Sonnet 4.5): Generates inspirational quote
2. **Image & Video Prompt Generator** (Claude Sonnet 4.5): Creates JSON with:
   - `image_prompt`: Description for static image
   - `video_prompt`: Description for animation + speech tags
3. **Parse Prompts**: Extracts prompts from JSON response
4. **ComfyUI Generate Image**: Creates 9:16 portrait using HiDream model
5. **VRAM Management**: Frees GPU memory and waits for availability
6. **Ovi Generate Video**: Animates image with synchronized audio

**Returns:** Execution data with:
- Generated quote text
- Image prompt description
- Video prompt description
- ComfyUI output filename (image)
- Ovi output path (video with audio)

## Testing

```bash
# Run all tests
uv run pytest -v

# Test coverage by module
uv run pytest tests/test_models.py -v     # 9 tests
uv run pytest tests/test_n8n_client.py -v  # 8 tests
uv run pytest tests/test_api.py -v         # 8 tests
```

## Troubleshooting

### Service not starting
```bash
# Check logs
docker-compose logs shorts-generator

# Verify n8n and comfyui are running
docker-compose ps n8n comfyui
```

### Missing workflow ID error
Add `SHORTS_WORKFLOW_ID` to your environment (see Setup section above)

### Generation timeout
- Check n8n workflow execution logs
- Verify ComfyUI has GPU memory available
- Check Claude API credits

### Image download fails
- Verify ComfyUI output volume is mounted correctly
- Check file permissions on `/workspace/ComfyUI/output`

## Project Structure

```
custom_code/shorts-generator/
├── models.py           # Pydantic schemas (GenerateRequest, GenerateResponse)
├── n8n_client.py       # n8n API client (async)
├── api.py              # FastAPI endpoints
├── gradio_ui.py        # Gradio interface
├── app.py              # Unified launcher (FastAPI + Gradio)
├── tests/
│   ├── test_models.py
│   ├── test_n8n_client.py
│   └── test_api.py
├── Dockerfile
├── pyproject.toml      # uv dependencies
└── README.md
```

## Tech Stack

- **Python 3.12** with uv package manager
- **FastAPI** - Async REST API
- **Gradio 5.49** - Web UI with streaming updates
- **Pydantic 2.11** - Schema validation
- **httpx** - Async HTTP client
- **pytest** - Testing with mocks
- **mypy** - Strict type checking
- **ruff** - Fast linting

## License

Part of the localai project.
