#!/usr/bin/env python3
"""
Simple file upload and listing API for videos-to-process directory.
Runs as a lightweight FastAPI service proxied through nginx.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from datetime import datetime

app = FastAPI(title="Video Upload API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_DIR = Path("/mnt/raven-nas/videos-to-process")
PROCESSED_DIR = UPLOAD_DIR / "processed"
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10GB

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/api/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file to the videos-to-process directory."""

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Sanitize filename
    safe_filename = file.filename.replace("/", "_").replace("\\", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_filename = f"{timestamp}_{safe_filename}"

    file_path = UPLOAD_DIR / final_filename

    try:
        # Stream file to disk (efficient for large files)
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # Read 1MB at a time
                buffer.write(chunk)

        file_size = file_path.stat().st_size

        return JSONResponse(
            {
                "success": True,
                "message": "File uploaded successfully",
                "fileName": final_filename,
                "originalName": file.filename,
                "uploadTime": datetime.now().isoformat(),
                "fileSize": file_size,
                "path": str(file_path),
            }
        )

    except Exception as e:
        # Clean up partial file on error
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/api/list-videos")
async def list_videos():
    """List all video files in the videos-to-process directory."""

    video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv"}
    videos = []

    try:
        for file_path in UPLOAD_DIR.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                stat = file_path.stat()
                videos.append(
                    {
                        "filename": file_path.name,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "path": str(file_path),
                    }
                )

        # Sort by modification time (newest first)
        videos.sort(key=lambda x: x["modified"], reverse=True)

        return JSONResponse({"success": True, "videos": videos, "count": len(videos)})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list videos: {str(e)}")


@app.get("/api/list-processed")
async def list_processed():
    """List all processed video files."""

    video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv"}
    processed_videos = []

    try:
        for file_path in PROCESSED_DIR.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                stat = file_path.stat()

                # Get base name without extension
                base_name = file_path.stem

                # Transcription files are created with underscores instead of spaces
                # Convert the base_name to match the actual transcription filenames
                transcript_base_name = (
                    base_name.replace(" ", "_").replace("(", "_").replace(")", "_")
                )

                # Look for transcription files with underscored names
                txt_file = PROCESSED_DIR / f"{transcript_base_name}.txt"
                srt_file = PROCESSED_DIR / f"{transcript_base_name}.srt"
                json_file = PROCESSED_DIR / f"{transcript_base_name}.json"

                processed_videos.append(
                    {
                        "filename": file_path.name,
                        "base_name": transcript_base_name,  # Use the underscored version for download links
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "has_transcript": txt_file.exists(),
                        "has_srt": srt_file.exists(),
                        "has_json": json_file.exists(),
                    }
                )

        # Sort by modification time (newest first)
        processed_videos.sort(key=lambda x: x["modified"], reverse=True)

        return JSONResponse(
            {
                "success": True,
                "videos": processed_videos,
                "count": len(processed_videos),
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list processed videos: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "upload_dir": str(UPLOAD_DIR)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")
