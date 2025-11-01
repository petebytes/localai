"""VibeVoice API Server - FastAPI application."""

import logging
import os
from pathlib import Path
from typing import Optional
import torch
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Depends
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic_settings import BaseSettings

from .models import (
    TTSRequest,
    TTSResponse,
    MultiSpeakerTTSRequest,
    ModelsListResponse,
    HealthResponse,
    StreamChunk,
)
from .model_manager import ModelManager
from .generation import TTSGenerator
from .audio_processing import AudioProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Dependency for handling both JSON and Form data
async def parse_tts_request(request: Request) -> dict:
    """Parse TTS request from either JSON or Form data."""
    content_type = request.headers.get("Content-Type", "")

    if "application/json" in content_type:
        # Handle JSON request
        try:
            return await request.json()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON data: {e}")
    elif "multipart/form-data" in content_type:
        # Handle Form data request
        try:
            form = await request.form()
            # Convert form data to dict, excluding file fields
            data = {}
            for key, value in form.items():
                if not isinstance(value, UploadFile):
                    data[key] = value
            return data
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid Form data: {e}")
    else:
        raise HTTPException(
            status_code=400,
            detail="Content-Type must be application/json or multipart/form-data",
        )


class Settings(BaseSettings):
    """Application settings."""

    models_dir: Path = Path(os.getenv("MODELS_DIR", "./models/vibevoice"))
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    default_model: str = os.getenv("DEFAULT_MODEL", "VibeVoice-1.5B")
    enable_cors: bool = os.getenv("ENABLE_CORS", "true").lower() == "true"
    api_version: str = "1.0.0"

    class Config:
        env_file = ".env"


settings = Settings()

# Setup templates
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# Global instances
model_manager: Optional[ModelManager] = None
tts_generator: Optional[TTSGenerator] = None
audio_processor: Optional[AudioProcessor] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global model_manager, tts_generator, audio_processor

    logger.info("Starting VibeVoice API Server...")

    # Initialize managers
    model_manager = ModelManager(settings.models_dir)
    tts_generator = TTSGenerator(model_manager)
    audio_processor = AudioProcessor()

    logger.info(f"Models directory: {settings.models_dir}")
    logger.info(f"CUDA available: {torch.cuda.is_available()}")

    # Scan for available models
    models = model_manager.scan_available_models()
    logger.info(f"Found {len(models)} models")

    yield

    # Cleanup
    logger.info("Shutting down...")
    if model_manager:
        model_manager.free_memory()


app = FastAPI(
    title="VibeVoice API Server",
    description="""
# VibeVoice Text-to-Speech API

Microsoft VibeVoice TTS with **voice cloning**, multi-speaker support, and streaming.

## 🎤 Voice Cloning

Clone any voice from a short audio sample (10-60 seconds):

**Method 1: Base64 encoded audio**
```python
import base64
voice_base64 = base64.b64encode(open("my_voice.wav", "rb").read()).decode()
requests.post("/api/tts", json={
    "text": "Hello world",
    "voice_audio_base64": voice_base64
})
```

**Method 2: Multipart file upload**
```bash
curl -X POST "/api/tts" \\
  -F "text=Hello world" \\
  -F "voice_audio=@my_voice.wav"
```

## 🎭 Features

- **Voice Cloning**: Clone any voice from short samples
- **Multi-Speaker**: Up to 4 speakers with distinct voices
- **Streaming**: Server-Sent Events for low latency
- **Model Management**: Load, unload, switch models
- **Output Formats**: WAV, MP3, OGG
- **GPU Accelerated**: CUDA 12.8 optimized

## 📚 Quick Links

- Try the interactive docs below
- See example requests in each endpoint
- Voice samples: 10-60 seconds (20-30s optimal)
""",
    version=settings.api_version,
    lifespan=lifespan,
)

# CORS middleware
if settings.enable_cors:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root(request: Request):
    """Serve the VibeVoice UI."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        model_loaded=model_manager.is_model_loaded() if model_manager else False,
        gpu_available=torch.cuda.is_available(),
        version=settings.api_version,
    )


@app.get("/api/models", response_model=ModelsListResponse)
async def list_models():
    """List available models."""
    if not model_manager:
        raise HTTPException(status_code=500, detail="Model manager not initialized")

    models = model_manager.scan_available_models()
    current_model = model_manager.current_model_name

    return ModelsListResponse(models=models, current_model=current_model)


@app.post("/api/models/{model_name}/load")
async def load_model(
    model_name: str,
    attention_type: str = "auto",
    quantize_llm: str = "full precision",
    diffusion_steps: int = 20,
):
    """Load a specific model."""
    if not model_manager:
        raise HTTPException(status_code=500, detail="Model manager not initialized")

    try:
        from .models import AttentionType, QuantizationType

        attn = AttentionType(attention_type)
        quant = QuantizationType(quantize_llm)

        model_manager.load_model(
            model_name=model_name,
            attention_type=attn,
            quantize_llm=quant,
            diffusion_steps=diffusion_steps,
        )

        return {"status": "success", "model": model_name, "loaded": True}

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load model: {e}")


@app.post("/api/models/{model_name}/unload")
async def unload_model(model_name: str):
    """Unload current model and free memory."""
    if not model_manager:
        raise HTTPException(status_code=500, detail="Model manager not initialized")

    if model_manager.current_model_name != model_name:
        raise HTTPException(
            status_code=400,
            detail=f"Model {model_name} is not loaded",
        )

    model_manager.free_memory()
    return {"status": "success", "model": model_name, "loaded": False}


@app.get("/api/models/current")
async def get_current_model():
    """Get currently loaded model info."""
    if not model_manager:
        raise HTTPException(status_code=500, detail="Model manager not initialized")

    if not model_manager.is_model_loaded():
        return {"current_model": None}

    return {
        "current_model": model_manager.current_model_name,
        "device": str(model_manager.current_device),
    }


@app.post("/api/tts", response_model=TTSResponse)
async def generate_tts(
    request: Request,
    request_data: dict = Depends(parse_tts_request),
):
    """Generate single-speaker text-to-speech.

    Accepts voice sample as either:
    - JSON body with optional voice_audio_base64 field
    - Multipart form data with optional voice_audio file
    """
    if not all([model_manager, tts_generator, audio_processor]):
        raise HTTPException(status_code=500, detail="Server not initialized")

    try:
        # Parse and validate the TTS request
        tts_request = TTSRequest(**request_data)

        # Check for voice_audio file in form data
        voice_audio = None
        content_type = request.headers.get("Content-Type", "")
        if "multipart/form-data" in content_type:
            form = await request.form()
            voice_audio = form.get("voice_audio")

        # Load model if needed
        if not model_manager.is_model_loaded():
            logger.info(f"Loading default model: {tts_request.model}")
            model_manager.load_model(
                model_name=tts_request.model,
                attention_type=tts_request.attention_type,
                quantize_llm=tts_request.quantize_llm,
                diffusion_steps=tts_request.diffusion_steps,
            )
        elif model_manager.current_model_name != tts_request.model:
            logger.info(f"Switching to model: {tts_request.model}")
            model_manager.load_model(
                model_name=tts_request.model,
                attention_type=tts_request.attention_type,
                quantize_llm=tts_request.quantize_llm,
                diffusion_steps=tts_request.diffusion_steps,
            )

        # Prepare voice sample if provided
        voice_tensor = None
        if voice_audio:
            # Read from uploaded file
            audio_bytes = await voice_audio.read()
            import base64

            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            voice_tensor, _ = audio_processor.prepare_voice_sample(
                audio_base64, tts_request.voice_speed_factor
            )
        elif tts_request.voice_audio_base64:
            # Use base64 from request
            voice_tensor, _ = audio_processor.prepare_voice_sample(
                tts_request.voice_audio_base64, tts_request.voice_speed_factor
            )

        # Apply LoRA if configured
        if tts_request.lora_config:
            model_manager.apply_lora(tts_request.lora_config.model_dump())

        # Generate audio
        logger.info(f"Generating TTS for text: {tts_request.text[:50]}...")
        audio_tensor = tts_generator.generate_single_speaker(
            text=tts_request.text,
            voice_audio=voice_tensor,
            seed=tts_request.seed,
            cfg_scale=tts_request.cfg_scale,
            diffusion_steps=tts_request.diffusion_steps,
            use_sampling=tts_request.use_sampling,
            temperature=tts_request.temperature,
            top_p=tts_request.top_p,
            voice_speed_factor=tts_request.voice_speed_factor,
            max_words_per_chunk=tts_request.max_words_per_chunk,
        )

        # Convert to base64
        audio_base64 = audio_processor.tensor_to_base64(
            audio_tensor,
            audio_processor.TARGET_SAMPLE_RATE,
            tts_request.output_format,
        )

        duration = audio_processor.get_duration(
            audio_tensor, audio_processor.TARGET_SAMPLE_RATE
        )

        return TTSResponse(
            audio_base64=audio_base64,
            sample_rate=audio_processor.TARGET_SAMPLE_RATE,
            format=tts_request.output_format,
            duration_seconds=duration,
            model_used=model_manager.current_model_name,
            metadata={
                "seed": str(tts_request.seed),
                "cfg_scale": str(tts_request.cfg_scale),
            },
        )

    except Exception as e:
        logger.error(f"TTS generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")


@app.post("/api/tts/multi-speaker", response_model=TTSResponse)
async def generate_multi_speaker_tts(
    multi_tts_request: MultiSpeakerTTSRequest,
    speaker1_voice: Optional[UploadFile] = File(None),
    speaker2_voice: Optional[UploadFile] = File(None),
    speaker3_voice: Optional[UploadFile] = File(None),
    speaker4_voice: Optional[UploadFile] = File(None),
):
    """Generate multi-speaker text-to-speech."""
    if not all([model_manager, tts_generator, audio_processor]):
        raise HTTPException(status_code=500, detail="Server not initialized")

    try:
        # Load model if needed
        if (
            not model_manager.is_model_loaded()
            or model_manager.current_model_name != multi_tts_request.model
        ):
            logger.info(f"Loading model: {multi_tts_request.model}")
            model_manager.load_model(
                model_name=multi_tts_request.model,
                attention_type=multi_tts_request.attention_type,
                quantize_llm=multi_tts_request.quantize_llm,
                diffusion_steps=multi_tts_request.diffusion_steps,
            )

        # Prepare speaker voices
        speaker_voices = {}
        import base64

        for speaker_id in range(1, 5):
            # Check uploaded file
            uploaded_file = locals().get(f"speaker{speaker_id}_voice")
            base64_audio = getattr(
                multi_tts_request, f"speaker{speaker_id}_voice", None
            )

            if uploaded_file:
                audio_bytes = await uploaded_file.read()
                audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                voice_tensor, _ = audio_processor.prepare_voice_sample(
                    audio_b64, multi_tts_request.voice_speed_factor
                )
                speaker_voices[speaker_id] = voice_tensor
            elif base64_audio:
                voice_tensor, _ = audio_processor.prepare_voice_sample(
                    base64_audio, multi_tts_request.voice_speed_factor
                )
                speaker_voices[speaker_id] = voice_tensor
            else:
                speaker_voices[speaker_id] = None

        # Generate multi-speaker audio
        logger.info("Generating multi-speaker TTS...")
        audio_tensor = tts_generator.generate_multi_speaker(
            text=multi_tts_request.text,
            speaker_voices=speaker_voices,
            seed=multi_tts_request.seed,
            cfg_scale=multi_tts_request.cfg_scale,
            diffusion_steps=multi_tts_request.diffusion_steps,
            use_sampling=multi_tts_request.use_sampling,
            temperature=multi_tts_request.temperature,
            top_p=multi_tts_request.top_p,
            voice_speed_factor=multi_tts_request.voice_speed_factor,
            max_words_per_chunk=multi_tts_request.max_words_per_chunk,
        )

        # Convert to base64
        audio_base64 = audio_processor.tensor_to_base64(
            audio_tensor,
            audio_processor.TARGET_SAMPLE_RATE,
            multi_tts_request.output_format,
        )

        duration = audio_processor.get_duration(
            audio_tensor, audio_processor.TARGET_SAMPLE_RATE
        )

        return TTSResponse(
            audio_base64=audio_base64,
            sample_rate=audio_processor.TARGET_SAMPLE_RATE,
            format=multi_tts_request.output_format,
            duration_seconds=duration,
            model_used=model_manager.current_model_name,
            metadata={"type": "multi-speaker"},
        )

    except Exception as e:
        logger.error(f"Multi-speaker TTS failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")


@app.post("/api/tts/stream")
async def stream_tts(stream_request: TTSRequest):
    """Stream single-speaker TTS generation."""
    if not all([model_manager, tts_generator, audio_processor]):
        raise HTTPException(status_code=500, detail="Server not initialized")

    try:
        # Load model if needed
        if (
            not model_manager.is_model_loaded()
            or model_manager.current_model_name != stream_request.model
        ):
            model_manager.load_model(
                model_name=stream_request.model,
                attention_type=stream_request.attention_type,
                quantize_llm=stream_request.quantize_llm,
                diffusion_steps=stream_request.diffusion_steps,
            )

        # Prepare voice sample
        voice_tensor = None
        if stream_request.voice_audio_base64:
            voice_tensor, _ = audio_processor.prepare_voice_sample(
                stream_request.voice_audio_base64, stream_request.voice_speed_factor
            )

        async def generate_chunks():
            """Generate and stream audio chunks."""
            async for chunk_data in tts_generator.generate_single_speaker_stream(
                text=stream_request.text,
                voice_audio=voice_tensor,
                seed=stream_request.seed,
                cfg_scale=stream_request.cfg_scale,
                diffusion_steps=stream_request.diffusion_steps,
                use_sampling=stream_request.use_sampling,
                temperature=stream_request.temperature,
                top_p=stream_request.top_p,
                voice_speed_factor=stream_request.voice_speed_factor,
                max_words_per_chunk=stream_request.max_words_per_chunk,
            ):
                if chunk_data["is_final"]:
                    # Send final marker
                    yield f"data: {StreamChunk(chunk_index=chunk_data['chunk_index'], audio_base64='', is_final=True).model_dump_json()}\n\n"
                else:
                    # Convert audio to base64
                    audio_base64 = audio_processor.tensor_to_base64(
                        chunk_data["audio"],
                        audio_processor.TARGET_SAMPLE_RATE,
                        stream_request.output_format,
                    )

                    chunk = StreamChunk(
                        chunk_index=chunk_data["chunk_index"],
                        audio_base64=audio_base64,
                        is_final=False,
                        text_segment=chunk_data["text_segment"],
                    )

                    yield f"data: {chunk.model_dump_json()}\n\n"

        return StreamingResponse(
            generate_chunks(),
            media_type="text/event-stream",
        )

    except Exception as e:
        logger.error(f"Streaming TTS failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Streaming failed: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
