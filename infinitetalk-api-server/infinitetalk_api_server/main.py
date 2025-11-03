"""InfiniteTalk API Server - FastAPI wrapper for audio-driven video generation."""

import argparse
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

import torch
from fastapi import FastAPI, HTTPException

# Add InfiniteTalk to Python path
INFINITETALK_DIR = os.environ.get("INFINITETALK_DIR", "/workspace")
sys.path.insert(0, INFINITETALK_DIR)

from infinitetalk_api_server import __version__  # noqa: E402
from infinitetalk_api_server.file_utils import validate_file_exists  # noqa: E402
from infinitetalk_api_server.generation import VideoGenerator  # noqa: E402
from infinitetalk_api_server.models import (  # noqa: E402
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


def parse_args_from_env():
    """Parse configuration from environment variables.

    Returns:
        argparse.Namespace with configuration
    """
    args = argparse.Namespace()

    # Model paths
    args.ckpt_dir = os.environ.get("CKPT_DIR", "/workspace/weights/Wan2.1-I2V-14B-480P")
    args.wav2vec_dir = os.environ.get(
        "WAV2VEC_DIR", "/workspace/weights/chinese-wav2vec2-base"
    )
    args.infinitetalk_dir = os.environ.get(
        "INFINITETALK_DIR",
        "/workspace/weights/InfiniteTalk/single/infinitetalk.safetensors",
    )
    args.quant_dir = os.environ.get("QUANT_DIR", None)
    args.lora_dir = os.environ.get("LORA_DIR", None)
    args.lora_scale = float(os.environ.get("LORA_SCALE", "1.0"))
    args.quant = os.environ.get("QUANT", None)

    # Task configuration
    args.task = os.environ.get("TASK", "infinitetalk-14B")

    # Generation parameters
    args.frame_num = int(os.environ.get("FRAME_NUM", "81"))
    args.mode = os.environ.get("MODE", "streaming")
    args.motion_frame = int(os.environ.get("MOTION_FRAME", "9"))
    args.num_persistent_param_in_dit = int(
        os.environ.get("NUM_PERSISTENT_PARAM_IN_DIT", "0")
    )

    # Sampling parameters
    args.sample_shift = None  # Will be auto-set based on resolution
    args.sample_steps = None  # Will be set per request

    # Other parameters
    args.offload_model = False
    args.color_correction_strength = 1.0
    args.dit_path = None
    args.base_seed = 42
    args.save_file = None
    args.audio_save_dir = "save_audio/api"

    # Distributed training parameters (single GPU for API)
    args.ulysses_size = 1
    args.ring_size = 1
    args.t5_fsdp = False
    args.t5_cpu = False
    args.dit_fsdp = False

    # TeaCache acceleration (default disabled)
    args.use_teacache = os.environ.get("USE_TEACACHE", "false").lower() == "true"
    args.teacache_thresh = float(os.environ.get("TEACACHE_THRESH", "0.2"))

    # APG (Adaptive Projected Guidance) - default disabled
    args.use_apg = os.environ.get("USE_APG", "false").lower() == "true"
    args.apg_momentum = float(os.environ.get("APG_MOMENTUM", "-0.75"))
    args.apg_norm_threshold = float(os.environ.get("APG_NORM_THRESHOLD", "55"))

    # Validate paths
    if not os.path.exists(args.ckpt_dir):
        raise FileNotFoundError(f"Checkpoint directory not found: {args.ckpt_dir}")
    if not os.path.exists(args.wav2vec_dir):
        raise FileNotFoundError(f"Wav2Vec2 directory not found: {args.wav2vec_dir}")
    if not os.path.exists(args.infinitetalk_dir):
        raise FileNotFoundError(
            f"InfiniteTalk checkpoint not found: {args.infinitetalk_dir}"
        )

    logger.info("Configuration loaded:")
    logger.info(f"  Checkpoint: {args.ckpt_dir}")
    logger.info(f"  Wav2Vec2: {args.wav2vec_dir}")
    logger.info(f"  InfiniteTalk: {args.infinitetalk_dir}")
    logger.info(
        f"  VRAM management: num_persistent_param={args.num_persistent_param_in_dit}"
    )

    return args


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global video_generator

    logger.info("Starting InfiniteTalk API Server...")
    logger.info(f"Version: {__version__}")
    logger.info(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"CUDA device: {torch.cuda.get_device_name(0)}")
        logger.info(f"CUDA version: {torch.version.cuda}")

    # Initialize generator (models will load lazily on first request)
    try:
        args = parse_args_from_env()
        video_generator = VideoGenerator(args)
        logger.info("Video generator initialized (models will load on first request)")
    except Exception as e:
        logger.error(f"Failed to initialize video generator: {e}")
        raise

    yield

    logger.info("Shutting down InfiniteTalk API Server...")
    # Cleanup if needed
    if video_generator and torch.cuda.is_available():
        torch.cuda.empty_cache()


# Create FastAPI app
app = FastAPI(
    title="InfiniteTalk API Server",
    description="Audio-driven talking head video generation using InfiniteTalk",
    version=__version__,
    lifespan=lifespan,
)


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint.

    Returns:
        HealthResponse with service status
    """
    model_loaded = False
    if video_generator:
        model_loaded = video_generator.wan_i2v is not None

    return HealthResponse(
        status="healthy",
        model_loaded=model_loaded,
        gpu_available=torch.cuda.is_available(),
        version=__version__,
    )


@app.post("/api/generate-video", response_model=VideoGenerationResponse)
async def generate_video(request: VideoGenerationRequest):
    """Generate talking head video from audio and image.

    Args:
        request: VideoGenerationRequest with audio_path, image_path, and parameters

    Returns:
        VideoGenerationResponse with video_path and metadata

    Raises:
        HTTPException: If generation fails
    """
    if not video_generator:
        raise HTTPException(status_code=500, detail="Video generator not initialized")

    try:
        # Validate input files
        logger.info("Validating input files...")
        validate_file_exists(request.audio_path, "Audio file")
        validate_file_exists(request.image_path, "Image file")

        # Set resolution-specific parameters
        if request.resolution == "infinitetalk-480":
            sample_shift = 7
        elif request.resolution == "infinitetalk-720":
            sample_shift = 11
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported resolution: {request.resolution}. Use 'infinitetalk-480' or 'infinitetalk-720'",
            )

        # Update generator args for this request
        video_generator.args.sample_shift = sample_shift

        # Generate video
        logger.info("Starting video generation...")
        logger.info(f"  Audio: {request.audio_path}")
        logger.info(f"  Image: {request.image_path}")
        logger.info(f"  Resolution: {request.resolution}")
        logger.info(f"  Steps: {request.diffusion_steps}")

        video_path, result_metadata = video_generator.generate(
            audio_path=request.audio_path,
            image_path=request.image_path,
            prompt=request.prompt,
            resolution=request.resolution,
            seed=request.seed,
            diffusion_steps=request.diffusion_steps,
            text_guide_scale=request.text_guide_scale,
            audio_guide_scale=request.audio_guide_scale,
            motion_frame=request.motion_frame,
            use_color_correction=request.use_color_correction,
            output_dir="/output",
        )

        logger.info(f"Video generation completed: {video_path}")

        return VideoGenerationResponse(
            video_path=video_path,
            duration_seconds=result_metadata["duration_seconds"],
            resolution=result_metadata["resolution"],
            frame_count=result_metadata["frame_count"],
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
        "name": "InfiniteTalk API Server",
        "version": __version__,
        "description": "Audio-driven talking head video generation",
        "endpoints": {"health": "/api/health", "generate": "/api/generate-video"},
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8200"))
    host = os.environ.get("HOST", "0.0.0.0")

    uvicorn.run(
        "infinitetalk_api_server.main:app", host=host, port=port, log_level="info"
    )
