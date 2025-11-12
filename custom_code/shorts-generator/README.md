# Inspirational Shorts Generator

Gradio web interface for generating inspirational quote images using n8n workflow orchestration.

## Features

- **Customizable Prompts**: Adjust quote generation and image prompt styles through the UI
- **TDD Implementation**: Comprehensive test suite with 25 passing tests
- **n8n Integration**: Triggers existing n8n workflow with custom parameters
- **Real-time Status**: Polls execution status with streaming updates
- **Docker Ready**: Containerized with health checks

## Architecture

```
┌──────────────┐
│  Gradio UI   │  ← User customizes prompts and clicks "Generate"
│  (Port 7860) │
└──────┬───────┘
       │
       v
┌──────────────┐
│  FastAPI     │  ← Triggers n8n workflow with custom prompts
│  (Port 8000) │
└──────┬───────┘
       │
       v
┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│     n8n      │────>│   Claude    │────>│   ComfyUI    │
│   Workflow   │     │  Sonnet 4.5 │     │  + HiDream   │
└──────────────┘     └─────────────┘     └──────────────┘
       │
       │ Returns quote, image prompt, and generated image
       v
┌──────────────┐
│  Downloads/  │  ← Image saved locally
└──────────────┘
```

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
# Required: n8n workflow ID (get from n8n UI)
SHORTS_WORKFLOW_ID=your_workflow_id_here

# Optional: Override defaults
N8N_API_URL=http://n8n:5678
COMFYUI_OUTPUT_PATH=/workspace/ComfyUI/output
```

**To get your workflow ID:**
1. Open n8n UI at https://n8n.lan
2. Open the "short-inspirational-videos" workflow
3. Click Settings → Copy workflow ID
4. Add to `.env`: `SHORTS_WORKFLOW_ID=<paste-id-here>`

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
2. (Optional) Customize the system prompts:
   - **Quote Generation Prompt**: Adjust tone, style, topics
   - **Image Prompt Generation**: Adjust visual style, aesthetics
3. Click "Generate Quote & Image"
4. Wait 30-60 seconds for generation
5. View results and download image

## n8n Workflow Changes

The workflow has been updated to accept custom prompts via webhook:

**Changed:** Manual Trigger → Webhook Trigger
**Accepts:** POST to `/webhook/shorts-generate` with JSON:
```json
{
  "quote_system_prompt": "Your custom quote instructions...",
  "image_system_prompt": "Your custom image instructions..."
}
```

**Returns:** Execution data with:
- Generated quote text
- Image prompt description
- ComfyUI output filename

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
