# Shorts Generator

Gradio web interface for generating inspirational quote images using n8n workflow orchestration.

## Architecture

- **Backend**: FastAPI with async n8n workflow execution
- **Frontend**: Gradio with customizable prompt inputs
- **Integration**: Triggers existing n8n workflow via REST API
- **Storage**: Generated images served from shared volume

## Workflow

1. User customizes quote style and image prompts
2. FastAPI triggers n8n workflow with parameters
3. n8n orchestrates:
   - Claude Sonnet 4.5 (quote generation)
   - Claude Sonnet 4.5 (image prompt generation)
   - ComfyUI + HiDream model (image generation)
4. Poll n8n execution status
5. Retrieve and display generated content

## Key Files

- `models.py`: Pydantic schemas (request/response)
- `n8n_client.py`: n8n API client
- `api.py`: FastAPI endpoints
- `gradio_ui.py`: Gradio interface
- `app.py`: Unified launcher

## Testing

TDD approach with pytest:
- Mock n8n API responses
- Test workflow trigger + polling
- Validate Pydantic schemas

## Environment

- `N8N_API_URL`: n8n instance (default: http://n8n:5678)
- `N8N_WORKFLOW_ID`: Workflow to trigger
- `COMFYUI_OUTPUT_PATH`: Path to ComfyUI output directory
