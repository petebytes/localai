"""Pydantic models for shorts generator API."""

from enum import Enum

from pydantic import BaseModel, Field

# Default system prompts for quote and image generation
# ruff: noqa: E501
DEFAULT_QUOTE_PROMPT = """You are a compassionate trauma-informed writer inspired by Peggy Oliveira, MSW — focusing on healing, self-trust, boundaries, emotional regulation, and recovery from shame. You generate original, reflective, and emotionally grounded inspirational quotes (not copied or cliché).

Tone: Gentle, validating, and empowering. Avoid toxic positivity. Each quote should sound like it could comfort someone healing from trauma or self-doubt.
Style guidelines:
Write in plain, accessible language.
Keep each quote 1 sentence long.
Avoid "you should" or "just do it" advice.
Use metaphors of growth, safety, and light when natural.
Include variety: self-compassion, boundaries, grief, rest, resilience, embodiment, inner child work.
Each quote should stand alone and feel sincere, not generic.

** IMPORTANT ** generate a single sentence"""

DEFAULT_IMAGE_PROMPT = """You are an artistic director tasked with creating both visual and animated content for reflective, emotionally grounded inspirational quotes.

When provided with a quote, you must generate TWO prompts in JSON format:

1. **image_prompt**: A detailed description of a photorealistic 9:16 portrait image that represents or supports the quote. Focus on composition, lighting, mood, subject, and environment.

2. **video_prompt**: A description of how the image should be animated into a 5-second video. Describe subtle movements, camera motion, lighting changes, facial expressions, environmental elements (wind, light shifts), and emotional progression. Keep it natural and cinematic.

** IMPORTANT ** Respond ONLY with valid JSON in this exact format:
{
  "image_prompt": "detailed image description here",
  "video_prompt": "detailed animation description here. Include the quote spoken: <S>quote text<E>"
}

Ensure the video_prompt includes the quote wrapped in <S>quote<E> tags for speech generation."""


class ExecutionStatus(str, Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class GenerateRequest(BaseModel):
    """Request to generate inspirational quote image.

    Note: System prompts are hardcoded and not exposed to users.
    """

    pass


class GenerateResponse(BaseModel):
    """Response for generate request with execution status."""

    execution_id: str = Field(description="n8n workflow execution ID")
    status: ExecutionStatus = Field(description="Current execution status")
    quote: str | None = Field(default=None, description="Generated quote text")
    image_prompt: str | None = Field(default=None, description="Generated image prompt")
    image_url: str | None = Field(default=None, description="URL to download generated image")
    video_prompt: str | None = Field(default=None, description="Generated video animation prompt")
    video_url: str | None = Field(default=None, description="URL to download generated video")
    video_path: str | None = Field(
        default=None, description="Absolute path to generated video file"
    )
    error: str | None = Field(default=None, description="Error message if failed")


class GenerationItem(BaseModel):
    """Information about a single generation."""

    timestamp: str = Field(description="Generation timestamp (YYYYMMDD_HHMMSS)")
    image_filename: str | None = Field(default=None, description="Image filename")
    image_url: str | None = Field(default=None, description="URL to download image")
    video_filename: str | None = Field(default=None, description="Video filename")
    video_url: str | None = Field(default=None, description="URL to download video")
    has_image: bool = Field(default=False, description="Whether image exists")
    has_video: bool = Field(default=False, description="Whether video exists")


class ListGenerationsResponse(BaseModel):
    """Response for list generations request."""

    generations: list[GenerationItem] = Field(description="List of previous generations")
    total: int = Field(description="Total number of generations found")
