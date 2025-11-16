"""Pydantic models for Ovi API request/response validation."""

from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field


class VideoGenerationRequest(BaseModel):
    """Request schema for video generation endpoint."""

    text_prompt: str = Field(
        ...,
        description="Text prompt describing the video scene. Use <S>speech<E> for dialogue and <AUDCAP>audio description<ENDAUDCAP> for sound effects.",
        min_length=1,
        max_length=2000,
    )
    image_path: Optional[str] = Field(
        None,
        description="Path to image file for Image-to-Video mode. If None, uses Text-to-Video mode.",
    )
    mode: Literal["t2v", "i2v"] = Field(
        "t2v",
        description="Generation mode: 't2v' for Text-to-Video or 'i2v' for Image-to-Video",
    )

    # Video configuration
    video_height: int = Field(
        1080,
        ge=128,
        le=2048,
        description="Video height in pixels (must be divisible by 32)",
    )
    video_width: int = Field(
        1920,
        ge=128,
        le=2048,
        description="Video width in pixels (must be divisible by 32)",
    )
    video_seed: int = Field(
        100, ge=0, le=100000, description="Random seed for reproducibility"
    )

    # Sampling parameters
    solver_name: Literal["unipc", "euler", "dpm++"] = Field(
        "unipc", description="Diffusion solver algorithm"
    )
    sample_steps: int = Field(
        70,
        ge=20,
        le=100,
        description="Number of sampling steps. Higher = better quality but slower (60-80 recommended)",
    )
    shift: float = Field(
        5.0, ge=0.0, le=20.0, description="Flow shift parameter for noise scheduling"
    )

    # Guidance scales
    video_guidance_scale: float = Field(
        8.0,
        ge=0.0,
        le=10.0,
        description="Video guidance scale (CFG). 7-9 recommended for best quality",
    )
    audio_guidance_scale: float = Field(
        7.0,
        ge=0.0,
        le=10.0,
        description="Audio guidance scale. 6-8 recommended for best sync",
    )

    # Advanced parameters
    slg_layer: int = Field(
        11, ge=-1, le=30, description="Skip-layer guidance layer (-1 to disable)"
    )
    video_negative_prompt: str = Field(
        "jitter, bad hands, blur, distortion",
        description="Negative prompt for video quality control",
        max_length=500,
    )
    audio_negative_prompt: str = Field(
        "robotic, muffled, echo, distorted",
        description="Negative prompt for audio quality control",
        max_length=500,
    )

    # Quality presets
    preset: Optional[
        Literal[
            "youtube-shorts-high",
            "youtube-shorts-balanced",
            "youtube-shorts-fast",
            "square",
            "widescreen",
            "custom",
        ]
    ] = Field(
        None,
        description="Quality preset. If provided, overrides individual parameters.",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "text_prompt": "A concert stage glows with red lights. A singer grips the microphone and shouts, <S>This is the moment we've been waiting for!<E>. <AUDCAP>Electric guitar riffs, cheering crowd.<ENDAUDCAP>",
                "mode": "t2v",
                "video_height": 1080,
                "video_width": 1920,
                "video_seed": 42,
                "solver_name": "unipc",
                "sample_steps": 70,
                "shift": 5.0,
                "video_guidance_scale": 8.0,
                "audio_guidance_scale": 7.0,
                "slg_layer": 11,
                "preset": "youtube-shorts-high",
            }
        }


class VideoGenerationResponse(BaseModel):
    """Response schema for video generation endpoint."""

    video_path: str = Field(..., description="Path to generated video file")
    duration_seconds: float = Field(..., description="Video duration in seconds")
    frame_count: int = Field(..., description="Total number of frames")
    resolution: str = Field(..., description="Actual video resolution (WxH)")
    has_audio: bool = Field(..., description="Whether video contains audio track")
    metadata: Dict[str, str] = Field(
        ..., description="Generation metadata (seed, steps, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "video_path": "/output/ovi_t2v_concert_20251114_123456.mp4",
                "duration_seconds": 5.0,
                "frame_count": 121,
                "resolution": "1920x1080",
                "has_audio": True,
                "metadata": {
                    "seed": "42",
                    "steps": "70",
                    "solver": "unipc",
                    "video_guidance": "8.0",
                    "audio_guidance": "7.0",
                },
            }
        }


class HealthResponse(BaseModel):
    """Response schema for health check endpoint."""

    status: str = Field(..., description="Service health status")
    model_loaded: bool = Field(..., description="Whether Ovi model is loaded in memory")
    gpu_available: bool = Field(..., description="Whether CUDA GPU is available")
    gpu_name: Optional[str] = Field(None, description="GPU device name if available")
    version: str = Field(..., description="API server version")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "model_loaded": True,
                "gpu_available": True,
                "gpu_name": "NVIDIA GeForce RTX 5090",
                "version": "1.0.0",
            }
        }
