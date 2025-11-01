"""Pydantic models for request/response validation."""

from enum import Enum
from typing import Optional, Dict, List
from pydantic import BaseModel, Field, field_validator


class AttentionType(str, Enum):
    """Available attention mechanisms."""

    AUTO = "auto"
    EAGER = "eager"
    SDPA = "sdpa"
    FLASH_ATTENTION_2 = "flash_attention_2"
    SAGE = "sage"


class QuantizationType(str, Enum):
    """LLM quantization options."""

    FULL_PRECISION = "full precision"
    FOUR_BIT = "4bit"
    EIGHT_BIT = "8bit"


class OutputFormat(str, Enum):
    """Audio output formats."""

    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"


class LoRAConfig(BaseModel):
    """LoRA configuration."""

    lora_name: str = Field(..., description="Name of the LoRA adapter")
    llm_strength: float = Field(1.0, ge=0.0, le=2.0, description="LoRA strength")
    enable_llm: bool = Field(True, description="Apply to LLM component")
    enable_diffusion_head: bool = Field(True, description="Apply to diffusion head")
    enable_acoustic_connector: bool = Field(
        True, description="Apply to acoustic connector"
    )
    enable_semantic_connector: bool = Field(
        True, description="Apply to semantic connector"
    )


class TTSRequest(BaseModel):
    """
    Text-to-speech request with optional voice cloning.

    **Voice Cloning**: Provide a voice sample (10-60 seconds) using either:
    - `voice_audio_base64`: Base64 encoded audio string (WAV, MP3, OGG)
    - `voice_audio` file upload: Use multipart/form-data instead of JSON

    **Example with voice cloning**:
    ```python
    import base64
    voice_base64 = base64.b64encode(open("my_voice.wav", "rb").read()).decode()
    response = requests.post("/api/tts", json={
        "text": "Hello world",
        "voice_audio_base64": voice_base64
    })
    ```
    """

    text: str = Field(..., min_length=1, description="Text to synthesize")
    model: str = Field(
        "VibeVoice-1.5B",
        description="Model to use (VibeVoice-1.5B, VibeVoice-Large, VibeVoice-Large-Q8, VibeVoice-Large-Q4)",
    )

    # Voice cloning
    voice_audio_base64: Optional[str] = Field(
        None,
        description="**VOICE CLONING**: Base64 encoded audio file (WAV/MP3/OGG, 10-60 seconds) to clone the voice. Leave empty for default voice. Alternative: upload 'voice_audio' file via multipart/form-data.",
        examples=["UklGRiQAAABXQVZFZm10IBAAAAABAAEA..."],
    )

    # Generation parameters
    seed: int = Field(42, ge=0, description="Random seed for reproducibility")
    cfg_scale: float = Field(
        1.3, ge=0.0, le=10.0, description="Classifier-free guidance scale"
    )
    diffusion_steps: int = Field(
        20, ge=1, le=100, description="Number of diffusion steps"
    )

    # Sampling options
    use_sampling: bool = Field(
        False, description="Use sampling instead of deterministic generation"
    )
    temperature: float = Field(0.95, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: float = Field(0.95, ge=0.0, le=1.0, description="Nucleus sampling parameter")

    # Advanced options
    attention_type: AttentionType = Field(
        AttentionType.AUTO, description="Attention mechanism"
    )
    quantize_llm: QuantizationType = Field(
        QuantizationType.FULL_PRECISION, description="LLM quantization"
    )
    voice_speed_factor: float = Field(
        1.0, ge=0.8, le=1.2, description="Voice speed adjustment"
    )
    max_words_per_chunk: int = Field(
        250, ge=10, le=1000, description="Max words per chunk"
    )

    # LoRA
    lora_config: Optional[LoRAConfig] = Field(None, description="LoRA configuration")

    # Output
    output_format: OutputFormat = Field(
        OutputFormat.WAV, description="Audio output format"
    )


class MultiSpeakerTTSRequest(BaseModel):
    """
    Multi-speaker text-to-speech with voice cloning.

    **How to use**:
    1. Format text with speaker markers: `[1]: Hello!` `[2]: Hi there!`
    2. Optionally provide voice samples (base64 or file upload) for each speaker
    3. Supports 2-4 speakers in a single conversation

    **Example**:
    ```python
    response = requests.post("/api/tts/multi-speaker", json={
        "text": "[1]: Hello! [2]: Hi there!",
        "speaker1_voice": base64.b64encode(open("voice1.wav", "rb").read()).decode(),
        "speaker2_voice": base64.b64encode(open("voice2.wav", "rb").read()).decode()
    })
    ```
    """

    text: str = Field(
        ...,
        min_length=1,
        description="Text with speaker markers. Format: `[1]: First speaker text` `[2]: Second speaker text`. Supports [1] through [4].",
        examples=["[1]: Hello! How are you? [2]: I'm doing great, thanks!"],
    )
    model: str = Field(
        "VibeVoice-Large",
        description="Model to use. VibeVoice-Large recommended for best multi-speaker quality.",
    )

    # Speaker voice samples (base64 encoded)
    speaker1_voice: Optional[str] = Field(
        None,
        description="**VOICE CLONING**: Base64 encoded audio for speaker [1] (10-60 seconds). Leave empty for default voice.",
        examples=["UklGRiQAAABXQVZFZm10IBAAAAABAAEA..."],
    )
    speaker2_voice: Optional[str] = Field(
        None,
        description="**VOICE CLONING**: Base64 encoded audio for speaker [2] (10-60 seconds). Leave empty for default voice.",
    )
    speaker3_voice: Optional[str] = Field(
        None,
        description="**VOICE CLONING**: Base64 encoded audio for speaker [3] (10-60 seconds). Leave empty for default voice.",
    )
    speaker4_voice: Optional[str] = Field(
        None,
        description="**VOICE CLONING**: Base64 encoded audio for speaker [4] (10-60 seconds). Leave empty for default voice.",
    )

    # Generation parameters (same as single speaker)
    seed: int = Field(42, ge=0, description="Random seed")
    cfg_scale: float = Field(1.3, ge=0.0, le=10.0, description="CFG scale")
    diffusion_steps: int = Field(20, ge=1, le=100, description="Diffusion steps")

    use_sampling: bool = Field(False, description="Use sampling")
    temperature: float = Field(0.95, ge=0.0, le=2.0, description="Temperature")
    top_p: float = Field(0.95, ge=0.0, le=1.0, description="Top-p")

    attention_type: AttentionType = Field(
        AttentionType.AUTO, description="Attention type"
    )
    quantize_llm: QuantizationType = Field(
        QuantizationType.FULL_PRECISION, description="Quantization"
    )
    voice_speed_factor: float = Field(1.0, ge=0.8, le=1.2, description="Speed factor")
    max_words_per_chunk: int = Field(250, ge=10, le=1000, description="Chunk size")

    lora_config: Optional[LoRAConfig] = Field(None, description="LoRA config")
    output_format: OutputFormat = Field(OutputFormat.WAV, description="Output format")

    @field_validator("text")
    @classmethod
    def validate_speaker_markers(cls, v: str) -> str:
        """Validate that text contains speaker markers."""
        import re

        if not re.search(r"\[\d\]:", v):
            raise ValueError(
                "Multi-speaker text must contain [N]: markers (e.g., '[1]: Hello')"
            )
        return v


class TTSResponse(BaseModel):
    """TTS generation response."""

    audio_base64: str = Field(..., description="Base64 encoded audio")
    sample_rate: int = Field(..., description="Audio sample rate")
    format: OutputFormat = Field(..., description="Audio format")
    duration_seconds: float = Field(..., description="Audio duration")
    model_used: str = Field(..., description="Model name")
    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ModelInfo(BaseModel):
    """Model information."""

    model_id: str = Field(..., description="Model identifier")
    display_name: str = Field(..., description="Human-readable name")
    size_gb: Optional[float] = Field(None, description="Approximate size in GB")
    loaded: bool = Field(..., description="Whether model is currently loaded")
    quantized: bool = Field(False, description="Whether model is pre-quantized")
    recommended_for: List[str] = Field(
        default_factory=list, description="Recommended use cases"
    )


class ModelsListResponse(BaseModel):
    """List of available models."""

    models: List[ModelInfo] = Field(..., description="Available models")
    current_model: Optional[str] = Field(None, description="Currently loaded model")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    model_loaded: bool = Field(..., description="Whether a model is loaded")
    gpu_available: bool = Field(..., description="CUDA availability")
    version: str = Field(..., description="API version")


class ErrorResponse(BaseModel):
    """Error response."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    request_id: Optional[str] = Field(None, description="Request identifier")


class StreamChunk(BaseModel):
    """Streaming audio chunk."""

    chunk_index: int = Field(..., description="Chunk sequence number")
    audio_base64: str = Field(..., description="Base64 encoded audio chunk")
    is_final: bool = Field(False, description="Whether this is the final chunk")
    text_segment: Optional[str] = Field(None, description="Text segment for this chunk")
