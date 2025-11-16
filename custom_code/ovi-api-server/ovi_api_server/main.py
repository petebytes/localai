"""Ovi API Server - FastAPI wrapper for Ovi video+audio generation."""

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import torch
from fastapi import FastAPI, HTTPException

from ovi_api_server import __version__
from ovi_api_server.generation import VideoGenerator
from ovi_api_server.models import (
    HealthResponse,
    VideoGenerationRequest,
    VideoGenerationResponse,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global video generator instance
video_generator: Optional[VideoGenerator] = None


def parse_config_from_env():
    """Parse configuration from environment variables.

    Returns:
        Dictionary with configuration settings
    """
    config = {
        "cpu_offload": os.environ.get("OVI_CPU_OFFLOAD", "true").lower() == "true",
        "fp8": os.environ.get("OVI_FP8", "false").lower() == "true",
        "qint8": os.environ.get("OVI_QINT8", "false").lower() == "true",
        "output_dir": os.environ.get("OVI_OUTPUT_DIR", "/output"),
    }

    logger.info("Configuration loaded:")
    logger.info(f"  CPU Offload: {config['cpu_offload']}")
    logger.info(f"  FP8 Quantization: {config['fp8']}")
    logger.info(f"  QINT8 Quantization: {config['qint8']}")
    logger.info(f"  Output Directory: {config['output_dir']}")

    return config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global video_generator

    logger.info("Starting Ovi API Server...")
    logger.info(f"Version: {__version__}")
    logger.info(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"CUDA device: {torch.cuda.get_device_name(0)}")
        logger.info(f"CUDA version: {torch.version.cuda}")

    # Initialize generator (models will load lazily on first request)
    try:
        config = parse_config_from_env()
        video_generator = VideoGenerator(
            cpu_offload=config["cpu_offload"],
            fp8=config["fp8"],
            qint8=config["qint8"],
        )
        logger.info("Video generator initialized (model will load on first request)")
    except Exception as e:
        logger.error(f"Failed to initialize video generator: {e}")
        raise

    yield

    logger.info("Shutting down Ovi API Server...")
    # Cleanup if needed
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# Create FastAPI app
app = FastAPI(
    title="Ovi API Server",
    description="Text/Image-to-Video+Audio generation using Ovi 11B fusion model",
    version=__version__,
    lifespan=lifespan,
)


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint.

    Returns:
        HealthResponse with service status, model state, and GPU info
    """
    model_loaded = False
    gpu_name = None

    if video_generator:
        model_loaded = video_generator.ovi_engine is not None

    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)

    return HealthResponse(
        status="healthy",
        model_loaded=model_loaded,
        gpu_available=torch.cuda.is_available(),
        gpu_name=gpu_name,
        version=__version__,
    )


@app.post("/api/generate-video", response_model=VideoGenerationResponse)
async def generate_video(request: VideoGenerationRequest):
    """Generate video with audio from text prompt (and optional image).

    This endpoint supports both Text-to-Video (T2V) and Image-to-Video (I2V) modes.

    **T2V Mode:** Generate a 5-second video with audio from a text description.

    **I2V Mode:** Animate a static image with audio based on text description.

    **Text Prompt Format:**
    - Use `<S>speech text<E>` to wrap dialogue that should be spoken
    - Use `<AUDCAP>audio description<ENDAUDCAP>` to describe sound effects
    - Example: `A singer performs. <S>Hello world!<E> <AUDCAP>Crowd cheering<ENDAUDCAP>`

    **Quality Presets:**
    - `youtube-shorts-high`: 1080x1920, 70 steps (best quality, ~2-3 min)
    - `youtube-shorts-balanced`: 1080x1920, 50 steps (balanced, ~1-2 min)
    - `youtube-shorts-fast`: 1080x1920, 40 steps (fastest, ~1 min)
    - `square`: 960x960, 60 steps (Instagram, TikTok)
    - `widescreen`: 720x1280, 60 steps (16:9 format)
    - `custom`: Use individual parameters

    Args:
        request: VideoGenerationRequest with text prompt and generation parameters

    Returns:
        VideoGenerationResponse with video path, duration, and metadata

    Raises:
        HTTPException: If generation fails or inputs are invalid
    """
    if not video_generator:
        raise HTTPException(status_code=500, detail="Video generator not initialized")

    try:
        # Get output directory from config
        config = parse_config_from_env()
        output_dir = config["output_dir"]

        # Validate image path for I2V mode
        if request.mode == "i2v" and not request.image_path:
            raise HTTPException(
                status_code=400,
                detail="image_path is required for Image-to-Video (i2v) mode",
            )

        # Log request
        logger.info("Starting video generation...")
        logger.info(f"  Mode: {request.mode.upper()}")
        logger.info(f"  Prompt: {request.text_prompt[:100]}...")
        if request.image_path:
            logger.info(f"  Image: {request.image_path}")
        if request.preset:
            logger.info(f"  Preset: {request.preset}")
        logger.info(f"  Resolution: {request.video_width}x{request.video_height}")
        logger.info(f"  Steps: {request.sample_steps}")

        # Generate video
        video_path, result_metadata = video_generator.generate(
            text_prompt=request.text_prompt,
            image_path=request.image_path,
            mode=request.mode,
            video_height=request.video_height,
            video_width=request.video_width,
            video_seed=request.video_seed,
            solver_name=request.solver_name,
            sample_steps=request.sample_steps,
            shift=request.shift,
            video_guidance_scale=request.video_guidance_scale,
            audio_guidance_scale=request.audio_guidance_scale,
            slg_layer=request.slg_layer,
            video_negative_prompt=request.video_negative_prompt,
            audio_negative_prompt=request.audio_negative_prompt,
            preset=request.preset,
            output_dir=output_dir,
        )

        logger.info(f"Video generation completed: {video_path}")

        return VideoGenerationResponse(
            video_path=video_path,
            duration_seconds=result_metadata["duration_seconds"],
            frame_count=result_metadata["frame_count"],
            resolution=result_metadata["resolution"],
            has_audio=result_metadata["has_audio"],
            metadata=result_metadata["metadata"],
        )

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Video generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Video generation failed: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Ovi API Server",
        "version": __version__,
        "description": "Text/Image-to-Video+Audio generation using Ovi 11B",
        "model": "Ovi 11B (twin backbone cross-modal fusion)",
        "capabilities": [
            "Text-to-Video+Audio (T2V)",
            "Image-to-Video+Audio (I2V)",
            "5-second videos at 24 FPS",
            "Up to 1920x1080 resolution",
            "Synchronized audio generation",
        ],
        "endpoints": {
            "health": "/api/health",
            "generate": "/api/generate-video",
            "docs": "/docs",
        },
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8300"))
    host = os.environ.get("HOST", "0.0.0.0")

    uvicorn.run("ovi_api_server.main:app", host=host, port=port, log_level="info")
