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

DEFAULT_IMAGE_PROMPT = """You are an artistic director tasked with visualizing reflective, and emotionally grounded inspirational quotes. When provided with a prompt you create a description of what the image representing or supporting the quote should look like. The image being generated must be photorealistic will be used in 9:16 format.

** IMPORTANT ** Generate a single paragraph."""


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
    error: str | None = Field(default=None, description="Error message if failed")
