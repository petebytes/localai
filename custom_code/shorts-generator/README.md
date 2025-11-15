# Inspirational Shorts Generator

Gradio web interface for generating inspirational quote videos using n8n workflow orchestration with ComfyUI and Ovi 11B.

## Features

- **End-to-End Video Generation**: Quote → Image → Video with synchronized audio
- **Human-in-the-Loop Approval**: Review and edit AI-generated quotes before committing GPU resources
- **AI-Powered Pipeline**: Claude Sonnet 4.5 + ComfyUI (HiDream) + Ovi 11B
- **TDD Implementation**: Comprehensive test suite with passing tests
- **n8n Integration**: Triggers existing n8n workflow via webhook with Wait node approval
- **Real-time Status**: Polls execution status with streaming updates
- **Browse Gallery**: View and download previous generations (images + videos)
- **Docker Ready**: Containerized with health checks and NAS storage integration
- **Multi-Modal Output**: Generates both static images (9:16) and animated videos (10s with audio)

## Architecture

```
┌────────────────────────────────────────┐
│         Gradio UI (Port 7860)          │
│  ┌──────────────┐  ┌────────────────┐  │
│  │ Generate New │  │ Browse Previous│  │  ← Two-tab interface
│  └──────────────┘  └────────────────┘  │
└──────────┬─────────────────────────────┘
           │
           v
┌──────────────────────┐
│  FastAPI (Port 8000) │  ← REST API (generate, status, download, list)
└──────────┬───────────┘
           │
           v
┌──────────────────────┐
│   n8n Workflow       │  ← Webhook trigger + orchestration
└──┬────┬────┬─────────┘
   │    │    │
   │    │    └──────────────────┐
   │    │                       │
   v    v                       v
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Claude    │  │  ComfyUI    │  │  Ovi 11B    │
│ Sonnet 4.5  │  │ + HiDream   │  │ Video+Audio │
└─────────────┘  └─────────────┘  └─────────────┘
   │                   │                 │
   │ Quote             │ Image           │ Video (10s)
   │ + Prompts         │ (9:16)          │ + Audio
   │                   │                 │
   └───────────────────┴─────────────────┘
                       │
                       v
          ┌────────────────────────┐
          │   NAS Storage          │  ← Images + Videos saved
          │  /mnt/raven-nas/...    │
          └────────────────────────┘
                       │
                       v
          ┌────────────────────────┐
          │  Local downloads/      │  ← UI cache
          └────────────────────────┘
```

**Pipeline Steps:**
1. **Quote Generation** (Claude): Generates compassionate, trauma-informed quote
2. **Human Approval** (Wait Node): User reviews/edits/approves quote before proceeding
3. **Prompt Generation** (Claude): Creates image and video animation descriptions
4. **Image Generation** (ComfyUI + HiDream): Renders 9:16 portrait image
5. **Video Generation** (Ovi 11B): Animates image with synchronized speech and audio
6. **Delivery**: Downloads image and video to user

## TDD Workflow

Following strict TDD principles (Red-Green-Refactor):

1. **Red**: Write failing tests first
   - `test_models.py` - Pydantic schema validation (7 tests)
   - `test_n8n_client.py` - n8n API interaction (9 async tests)
   - `test_api.py` - FastAPI endpoints (6 tests)
   - **Total: 22 tests**

2. **Green**: Implement to pass tests
   - `models.py` - Request/response schemas + default prompts
   - `n8n_client.py` - Async n8n API client (webhook + polling)
   - `api.py` - FastAPI REST endpoints (generate, status, download, list)

3. **Refactor**: Clean up with type checking
   - `mypy` in strict mode (0 errors)
   - `ruff` linting (all checks passed)

## Setup

### Environment Variables

Required environment variables (set in `.env` or docker-compose.yml):

```bash
# n8n Configuration
N8N_API_URL=http://n8n:5678              # n8n instance URL
N8N_WEBHOOK_PATH=/webhook/shorts-generate # Webhook endpoint (no workflow ID needed)
N8N_API_KEY=your_api_key_here            # Required for execution status polling

# Output paths (mounted from NAS in production)
COMFYUI_OUTPUT_PATH=/workspace/ComfyUI/output  # Images (read-only)
OVI_OUTPUT_PATH=/output                        # Videos (read-only)

# API configuration
API_BASE_URL=http://localhost:8000       # FastAPI backend URL (for Gradio)
```

**Key Points:**
- Workflow triggered via webhook (no workflow ID needed)
- Output paths are read-only mounts in production (NAS storage)
- API key required for polling execution status
- Downloads cached locally in `downloads/` directory

### Docker Deployment

The service is configured with NAS storage integration in `docker-compose.yml`:

```yaml
shorts-generator:
  volumes:
    - /mnt/raven-nas/inspirational-shorts/generated-images:/workspace/ComfyUI/output:ro
    - /mnt/raven-nas/inspirational-shorts/generated-videos:/output:ro
    - ./custom_code/shorts-generator/downloads:/app/downloads
```

**Commands:**

```bash
# Build and start
docker-compose up -d shorts-generator

# View logs
docker-compose logs -f shorts-generator

# Check health
docker-compose exec shorts-generator python -c \
  "import httpx; print(httpx.get('http://localhost:8000/api/health').json())"

# Access UI
https://inspirational-shorts.lan  # Gradio UI (port 7860)
```

**Volume Mounts:**
- ComfyUI outputs (images): Read-only from NAS
- Ovi outputs (videos): Read-only from NAS
- Local downloads: Read-write cache for UI

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

### Generate New Content

1. Navigate to https://inspirational-shorts.lan
2. Go to the **"Generate New"** tab
3. **Optional**: Enter a custom quote in the "Custom Quote" field
   - Leave empty to generate an AI-powered trauma-informed quote (default)
   - Or provide your own quote to use instead
4. Click "Generate Quote, Image & Video"
5. **Quote Approval** (~5 seconds for quote generation):
   - The AI generates a quote (or uses your custom quote)
   - Review the generated quote in the approval section
   - Choose one of three actions:
     - **✓ Approve**: Continue with the quote as-is
     - **✎ Edit & Approve**: Modify the quote text and continue
     - **✗ Reject**: Cancel the workflow (saves GPU time)
6. Wait 3-5 minutes for generation (after approval):
   - Image generation: ~30-60 seconds (ComfyUI + HiDream)
   - Video generation: ~2-4 minutes (Ovi 11B - 10-second video with synchronized audio)
7. View results:
   - **Quote**: Displayed in text box (approved/edited version)
   - **Image**: 9:16 portrait (downloadable)
   - **Video**: 10-second clip with synchronized audio (downloadable)

### Browse Previous Generations

1. Go to the **"Browse Previous"** tab
2. Click "Refresh List" to load recent generations
3. Select a generation from the dropdown (sorted by timestamp, newest first)
4. View and download the associated image and/or video
5. Previous generations are automatically matched (video + image pairs)

## n8n Workflow

The workflow orchestrates a complete video generation pipeline:

**Trigger:** Webhook at `/webhook/shorts-generate`

**Accepts:** POST with JSON:
```json
{
  "quote_system_prompt": "Quote generation instructions...",
  "image_system_prompt": "Image + video prompt generation instructions...",
  "custom_quote": "Optional custom quote to use instead of AI generation"
}
```

**Note:** System prompts are hardcoded in `models.py` for consistency:
- `DEFAULT_QUOTE_PROMPT`: Trauma-informed compassionate quote generation (inspired by Peggy Oliveira, MSW)
- `DEFAULT_IMAGE_PROMPT`: Photorealistic 9:16 image + video animation prompt generation
- Users cannot customize prompts via UI (by design for quality control)
- `custom_quote` (optional): When provided, the workflow skips AI quote generation and uses the custom quote instead

**Pipeline Steps:**
1. **Check for Custom Quote**: Conditionally routes based on whether custom quote was provided
   - If custom quote provided: Formats and uses it directly (skips step 2)
   - If not provided: Proceeds to AI quote generation (step 2)
2. **Quote Writer** (Claude Sonnet 4.5): Generates inspirational quote (skipped if custom quote provided)
3. **Wait for Quote Approval** (n8n Wait Node): Pauses workflow for human review
   - User can approve, edit, or reject the quote
   - Workflow resumes via webhook when user makes a decision
4. **Handle Approval Response**: Processes user decision
   - If approved/edited: Continue with the final quote
   - If rejected: Stop workflow immediately
5. **Image & Video Prompt Generator** (Claude Sonnet 4.5): Creates JSON with:
   - `image_prompt`: Description for static image
   - `video_prompt`: Description for animation + speech tags
6. **Parse Prompts**: Extracts prompts from JSON response
7. **ComfyUI Generate Image**: Creates 9:16 portrait using HiDream model
8. **VRAM Management**: Frees GPU memory and waits for availability
9. **Ovi Generate Video**: Animates image with synchronized audio

**Returns:** Execution data with:
- Generated quote text
- Image prompt description
- Video prompt description
- ComfyUI output filename (image)
- Ovi output path (video with audio)

## Testing

```bash
# Run all tests (22 tests total)
uv run pytest -v

# Run tests by module
uv run pytest tests/test_models.py -v      # 7 tests (schema validation)
uv run pytest tests/test_n8n_client.py -v  # 9 tests (async n8n API)
uv run pytest tests/test_api.py -v         # 6 tests (FastAPI endpoints)

# Type checking
uv run mypy *.py

# Linting
uv run ruff check *.py
uv run ruff format *.py --check
```

## Troubleshooting

### Service not starting
```bash
# Check logs
docker-compose logs shorts-generator

# Verify dependencies are running
docker-compose ps n8n comfyui

# Check health endpoint
curl http://localhost:8000/api/health
```

### Webhook trigger fails
- Verify `N8N_WEBHOOK_PATH=/webhook/shorts-generate` is correct
- Check n8n workflow is active and webhook node is configured
- Review n8n logs: `docker-compose logs n8n`

### Cannot poll execution status
- Ensure `N8N_API_KEY` is set in environment
- Verify API key has correct permissions in n8n
- Check execution ID is valid

### Generation timeout
- Normal generation takes 3-5 minutes
- Check n8n workflow execution logs in UI
- Verify ComfyUI has GPU memory available (use `nvidia-smi`)
- Verify Ovi service is running and has VRAM available
- Check Claude API credits/rate limits

### File download fails
- Verify volume mounts are correct in docker-compose.yml
- Check file permissions on NAS paths:
  - `/mnt/raven-nas/inspirational-shorts/generated-images`
  - `/mnt/raven-nas/inspirational-shorts/generated-videos`
- Ensure `downloads/` directory exists and is writable

### Browse Previous shows no generations
- Click "Refresh List" button
- Verify output paths contain files (check NAS mounts)
- Check API logs: `docker-compose logs shorts-generator | grep list-generations`

## API Endpoints

The FastAPI backend (port 8000) provides the following endpoints:

### Generation Endpoints
- **POST /api/generate**: Trigger new quote/image/video generation
  - Returns: `{ execution_id, status }`

- **GET /api/status/{execution_id}**: Poll execution status
  - Returns: `{ execution_id, status, quote?, image_url?, video_url?, error? }`

### Approval Endpoints
- **POST /api/approve-quote**: Approve, edit, or reject a generated quote
  - Body: `{ execution_id, action: "approve"|"edit"|"reject", edited_quote? }`
  - Returns: `{ success, message }`
  - Resumes the n8n Wait node via webhook

### File Management
- **GET /api/download/{filename}**: Download generated image or video
  - Searches ComfyUI output path (images) and Ovi output path (videos)
  - Returns: File with appropriate media type

- **GET /api/list-generations?limit=50**: List previous generations
  - Returns: `{ generations: [...], total }`
  - Automatically matches videos with preceding images (within 5 minutes)
  - Sorted by timestamp (newest first)

### Health Check
- **GET /api/health**: Service health status
  - Returns: `{ status, n8n_url, webhook_path }`

## Project Structure

```
custom_code/shorts-generator/
├── models.py           # Pydantic schemas (GenerateRequest, GenerateResponse, etc.)
├── n8n_client.py       # n8n API client (async)
├── api.py              # FastAPI endpoints (generate, status, download, list)
├── gradio_ui.py        # Gradio interface (Generate New + Browse Previous tabs)
├── app.py              # Unified launcher (FastAPI + Gradio)
├── downloads/          # Local cache for downloaded files
├── tests/
│   ├── test_models.py
│   ├── test_n8n_client.py
│   └── test_api.py
├── Dockerfile
├── pyproject.toml      # uv dependencies
├── README.md
└── HUMAN_IN_THE_LOOP.md  # Human-in-the-loop approval documentation
```

## Tech Stack

- **Python 3.12** with uv package manager
- **FastAPI 0.120+** - Async REST API backend
- **Gradio 5.49+** - Web UI with two-tab interface and streaming updates
- **Pydantic 2.11+** - Schema validation with settings management
- **httpx** - Async HTTP client for n8n integration
- **uvicorn** - ASGI server with threading support
- **pytest 8.4+** - TDD testing framework with async support
- **pytest-mock** - Mocking for isolated unit tests
- **mypy 1.18+** - Strict type checking
- **ruff 0.14+** - Fast linting and formatting

### Service Architecture
- **Unified Launcher**: `app.py` runs FastAPI (port 8000) and Gradio (port 7860) together
- **FastAPI Backend**: Handles workflow triggers, polling, and file serving
- **Gradio Frontend**: Two-tab interface (Generate New + Browse Previous)
- **Storage**: NAS integration with local download cache

## License

Part of the localai project.
