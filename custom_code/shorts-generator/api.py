"""FastAPI backend for shorts generator."""

import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse

from models import GenerateRequest, GenerateResponse
from n8n_client import N8nClient, N8nError

# Configuration from environment
N8N_API_URL = os.getenv("N8N_API_URL", "http://n8n:5678")
N8N_WEBHOOK_PATH = os.getenv("N8N_WEBHOOK_PATH", "/webhook/shorts-generate")
N8N_API_KEY = os.getenv("N8N_API_KEY")
COMFYUI_OUTPUT_PATH = Path(os.getenv("COMFYUI_OUTPUT_PATH", "/workspace/ComfyUI/output"))

app = FastAPI(title="Shorts Generator API")


def get_n8n_client() -> N8nClient:
    """Dependency to get n8n client."""
    return N8nClient(base_url=N8N_API_URL, webhook_path=N8N_WEBHOOK_PATH, api_key=N8N_API_KEY)


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "n8n_url": N8N_API_URL,
        "webhook_path": N8N_WEBHOOK_PATH,
    }


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(
    request: GenerateRequest,
    client: N8nClient = Depends(get_n8n_client),
) -> GenerateResponse:
    """Trigger workflow to generate inspirational quote image.

    Args:
        request: Generate request with custom system prompts
        client: n8n client dependency

    Returns:
        Response with execution ID and initial status

    Raises:
        HTTPException: If workflow trigger fails
    """
    try:
        execution_id = await client.trigger_workflow(request)
        await client.close()

        return GenerateResponse(
            execution_id=execution_id,
            status="pending",  # type: ignore[arg-type]
        )
    except N8nError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{execution_id}", response_model=GenerateResponse)
async def get_status(
    execution_id: str,
    client: N8nClient = Depends(get_n8n_client),
) -> GenerateResponse:
    """Get execution status and results.

    Args:
        execution_id: n8n execution ID
        client: n8n client dependency

    Returns:
        Response with current status and results if completed

    Raises:
        HTTPException: If status retrieval fails
    """
    try:
        response = await client.get_execution_status(execution_id)
        await client.close()
        return response
    except N8nError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/{filename}")
async def download_file(filename: str) -> FileResponse:
    """Download generated image file.

    Args:
        filename: Name of file to download

    Returns:
        File response with image

    Raises:
        HTTPException: If file not found
    """
    # Security: Only allow alphanumeric, underscore, hyphen, and dot
    if not all(c.isalnum() or c in "._-" for c in filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = COMFYUI_OUTPUT_PATH / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(file_path),
        media_type="image/png",
        filename=filename,
    )
