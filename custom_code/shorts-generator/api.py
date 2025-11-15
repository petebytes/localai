"""FastAPI backend for shorts generator."""

import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse

from models import (
    GenerateRequest,
    GenerateResponse,
    GenerationItem,
    ListGenerationsResponse,
    QuoteApprovalRequest,
    QuoteApprovalResponse,
)
from n8n_client import N8nClient, N8nError

# Configuration from environment
N8N_API_URL = os.getenv("N8N_API_URL", "http://n8n:5678")
N8N_WEBHOOK_PATH = os.getenv("N8N_WEBHOOK_PATH", "/webhook/shorts-generate")
N8N_API_KEY = os.getenv("N8N_API_KEY")
COMFYUI_OUTPUT_PATH = Path(os.getenv("COMFYUI_OUTPUT_PATH", "/workspace/ComfyUI/output"))
OVI_OUTPUT_PATH = Path(os.getenv("OVI_OUTPUT_PATH", "/output"))

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
    """Download generated image or video file.

    Args:
        filename: Name of file to download

    Returns:
        File response with image or video

    Raises:
        HTTPException: If file not found
    """
    # Security: Only allow alphanumeric, underscore, hyphen, and dot
    if not all(c.isalnum() or c in "._-" for c in filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Try ComfyUI output path first (for images)
    file_path = COMFYUI_OUTPUT_PATH / filename
    media_type = "image/png"

    # If not found, try Ovi output path (for videos)
    if not file_path.exists() or not file_path.is_file():
        file_path = OVI_OUTPUT_PATH / filename
        media_type = "video/mp4"

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # Determine media type from extension if possible
    if filename.endswith(".mp4"):
        media_type = "video/mp4"
    elif filename.endswith((".png", ".jpg", ".jpeg")):
        media_type = "image/png"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
    )


@app.get("/api/list-generations", response_model=ListGenerationsResponse)
async def list_generations(limit: int = 50) -> ListGenerationsResponse:
    """List previous generations (images and videos).

    Args:
        limit: Maximum number of generations to return (default: 50)

    Returns:
        List of previous generations with available files

    Raises:
        HTTPException: If listing fails
    """
    try:
        from datetime import datetime

        # Collect all video files with their timestamps
        video_files: list[tuple[str, str, float]] = []  # (timestamp, filename, mtime)
        if OVI_OUTPUT_PATH.exists():
            for video_file in OVI_OUTPUT_PATH.glob("*.mp4"):
                # Extract timestamp from filename (e.g., ovi_i2v_..._20251115_033415.mp4)
                parts = video_file.stem.split("_")
                if len(parts) >= 2:
                    timestamp = f"{parts[-2]}_{parts[-1]}"
                    mtime = video_file.stat().st_mtime
                    video_files.append((timestamp, video_file.name, mtime))

        # Collect all image files with their modification times
        image_files: list[tuple[str, float]] = []  # (filename, mtime)
        if COMFYUI_OUTPUT_PATH.exists():
            for image_file in COMFYUI_OUTPUT_PATH.glob("hidream_test_*.png"):
                mtime = image_file.stat().st_mtime
                image_files.append((image_file.name, mtime))

        # Sort both lists by time (newest first)
        video_files.sort(key=lambda x: x[2], reverse=True)
        image_files.sort(key=lambda x: x[1], reverse=True)

        # Create generation sets by matching videos with closest preceding images
        generations: list[GenerationItem] = []

        for timestamp, video_filename, video_mtime in video_files:
            # Find the image file created just before this video (within 5 minutes)
            matched_image = None
            for image_filename, image_mtime in image_files:
                # Image should be created before video, within 5 minutes (300 seconds)
                time_diff = video_mtime - image_mtime
                if 0 <= time_diff <= 300:
                    matched_image = image_filename
                    # Remove matched image to avoid duplicate matching
                    image_files.remove((image_filename, image_mtime))
                    break

            # Create generation item
            gen_item = GenerationItem(
                timestamp=timestamp,
                video_filename=video_filename,
                video_url=f"/download/{video_filename}",
                has_video=True,
            )

            if matched_image:
                gen_item.image_filename = matched_image
                gen_item.image_url = f"/download/{matched_image}"
                gen_item.has_image = True

            generations.append(gen_item)

        # Add any remaining unmatched images as separate entries
        for image_filename, image_mtime in image_files:
            dt = datetime.fromtimestamp(image_mtime)
            timestamp = dt.strftime("%Y%m%d_%H%M%S")

            gen_item = GenerationItem(
                timestamp=timestamp,
                image_filename=image_filename,
                image_url=f"/download/{image_filename}",
                has_image=True,
                has_video=False,
            )
            generations.append(gen_item)

        # Sort by video timestamp/creation time and limit
        generations.sort(key=lambda x: x.timestamp, reverse=True)
        limited_generations = generations[:limit]

        return ListGenerationsResponse(
            generations=limited_generations, total=len(limited_generations)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list generations: {str(e)}")


@app.post("/api/approve-quote", response_model=QuoteApprovalResponse)
async def approve_quote(
    request: QuoteApprovalRequest,
    client: N8nClient = Depends(get_n8n_client),
) -> QuoteApprovalResponse:
    """Approve, edit, or reject a generated quote.

    This resumes the n8n workflow execution that is waiting for user approval.

    Args:
        request: Approval request with execution ID, action, and resume_url from n8n
        client: n8n client dependency

    Returns:
        Response indicating success or failure

    Raises:
        HTTPException: If approval fails
    """
    try:
        # Use the resume_url provided by n8n (passed from frontend)
        # This is more reliable than constructing the URL manually
        await client.approve_quote_with_url(request)
        await client.close()

        action_msg = {
            "approve": "Quote approved",
            "edit": "Quote edited and approved",
            "reject": "Quote rejected",
        }
        message = action_msg.get(request.action.value, "Action processed")

        return QuoteApprovalResponse(success=True, message=message)
    except N8nError as e:
        raise HTTPException(status_code=500, detail=str(e))
