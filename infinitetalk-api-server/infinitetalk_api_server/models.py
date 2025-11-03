"""Pydantic models for InfiniteTalk API requests and responses."""

from pydantic import BaseModel, Field
from typing import Dict


class VideoGenerationRequest(BaseModel):
    """Request model for video generation endpoint."""

    audio_path: str = Field(
        ...,
        description="Path to audio file (WAV, MP3, OGG, or video file with audio track)",
    )
    image_path: str = Field(..., description="Path to image or video file to animate")
    prompt: str = Field(
        default="", description="Optional text description of the video scene"
    )
    resolution: str = Field(
        default="infinitetalk-480",
        description="Output resolution (infinitetalk-480 or infinitetalk-720)",
    )
    seed: int = Field(
        default=42, ge=0, description="Random seed for reproducible generation"
    )
    diffusion_steps: int = Field(
        default=40,
        ge=1,
        le=100,
        description="Number of diffusion sampling steps (40 for quality, 8 with LoRA)",
    )
    text_guide_scale: float = Field(
        default=5.0,
        ge=0.0,
        le=20.0,
        description="Text guidance scale for classifier-free guidance",
    )
    audio_guide_scale: float = Field(
        default=4.0,
        ge=0.0,
        le=20.0,
        description="Audio guidance scale for classifier-free guidance",
    )
    motion_frame: int = Field(
        default=9,
        ge=1,
        description="Number of overlap frames between chunks for streaming mode",
    )
    use_color_correction: bool = Field(
        default=True,
        description="Apply color correction to prevent drift in long videos",
    )


class VideoGenerationResponse(BaseModel):
    """Response model for successful video generation."""

    video_path: str = Field(description="Path to generated video file")
    duration_seconds: float = Field(
        description="Duration of generated video in seconds"
    )
    resolution: str = Field(description="Output resolution (WxH)")
    frame_count: int = Field(description="Total number of frames in the video")
    metadata: Dict[str, str] = Field(description="Additional generation metadata")


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(description="Service status (healthy/unhealthy)")
    model_loaded: bool = Field(description="Whether models are loaded in memory")
    gpu_available: bool = Field(description="Whether GPU is accessible")
    version: str = Field(description="API server version")
