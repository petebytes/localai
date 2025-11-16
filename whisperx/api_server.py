#!/usr/bin/env python3
"""
WhisperX API Server
A FastAPI-based transcription service using WhisperX for word-level timestamps and speaker diarization.
Enhanced with chunking support for large files and video processing.
"""

import os
import gc
import torch
import whisperx
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, List
from pathlib import Path
from pydantic import BaseModel, Field
import logging
import time
import requests

# Import our custom modules
from ffmpeg_processor import FFmpegProcessor
from video_segmenter import VideoSegmenter, AudioSegment


# Pydantic models for API documentation
class WordTiming(BaseModel):
    """Individual word timing information"""

    word: str = Field(..., description="The word text")
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    score: float = Field(..., description="Confidence score (0-1)")

    class Config:
        json_schema_extra = {
            "example": {"word": "Hello,", "start": 0.031, "end": 0.432, "score": 0.894}
        }


class TranscriptionSegment(BaseModel):
    """Transcription segment with optional word-level timing"""

    start: float = Field(..., description="Segment start time in seconds")
    end: float = Field(..., description="Segment end time in seconds")
    text: str = Field(..., description="Transcribed text for this segment")
    words: Optional[List[WordTiming]] = Field(
        None, description="Word-level timing array (available after alignment)"
    )
    speaker: Optional[str] = Field(
        None, description="Speaker label (e.g., 'SPEAKER_00') if diarization enabled"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "start": 0.031,
                "end": 3.381,
                "text": " Hello, this is a test.",
                "words": [
                    {"word": "Hello,", "start": 0.031, "end": 0.432, "score": 0.894},
                    {"word": "this", "start": 0.693, "end": 0.833, "score": 0.999},
                ],
            }
        }


class TranscriptionResponse(BaseModel):
    """Standard transcription response with four output formats"""

    filename: str = Field(..., description="Original filename")
    language: str = Field(..., description="Detected or specified language code")
    segments: List[TranscriptionSegment] = Field(
        ..., description="Array of transcription segments with word-level timing"
    )
    srt: str = Field(
        ...,
        description="Pre-formatted word-level SRT subtitles (one word per entry, for karaoke/animations)",
    )
    segments_srt: str = Field(
        ...,
        description="Pre-formatted segment-level SRT subtitles (one phrase per entry, ideal for AI analysis)",
    )
    txt: str = Field(..., description="Plain text transcript without timestamps")

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "audio.wav",
                "language": "en",
                "segments": [
                    {
                        "start": 0.031,
                        "end": 3.381,
                        "text": " Hello, this is a test.",
                        "words": [
                            {
                                "word": "Hello,",
                                "start": 0.031,
                                "end": 0.432,
                                "score": 0.894,
                            },
                            {
                                "word": "this",
                                "start": 0.693,
                                "end": 0.833,
                                "score": 0.999,
                            },
                        ],
                    }
                ],
                "srt": "1\n00:00:00,031 --> 00:00:00,432\nHello,\n\n2\n00:00:00,693 --> 00:00:00,833\nthis\n\n",
                "segments_srt": "1\n00:00:00,031 --> 00:00:03,381\nHello, this is a test.\n\n",
                "txt": "Hello, this is a test.",
            }
        }


class LargeTranscriptionResponse(TranscriptionResponse):
    """Extended response for large file transcription with performance metadata"""

    duration: float = Field(..., description="Total audio duration in seconds")
    num_segments: int = Field(..., description="Number of transcription segments")
    num_chunks: int = Field(..., description="Number of processing chunks used")
    chunking_strategy: str = Field(
        ..., description="Chunking strategy used (auto/vad/time/silence)"
    )
    processing_time: float = Field(..., description="Total processing time in seconds")
    realtime_factor: float = Field(
        ...,
        description="Processing speed relative to audio duration (higher is faster)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "long-video.mp4",
                "duration": 1834.5,
                "language": "en",
                "num_segments": 156,
                "num_chunks": 12,
                "chunking_strategy": "vad",
                "processing_time": 89.3,
                "realtime_factor": 20.5,
                "segments": [],
                "srt": "1\n00:00:00,031 --> 00:00:00,432\nHello,\n\n",
                "segments_srt": "1\n00:00:00,031 --> 00:00:05,381\nHello, this is a test.\n\n",
                "txt": "Full transcript text...",
            }
        }


class VideoInfo(BaseModel):
    """Video file metadata"""

    format: str = Field(..., description="Video container format")
    duration: float = Field(..., description="Video duration in seconds")
    size_bytes: int = Field(..., description="File size in bytes")
    video_codec: str = Field(..., description="Video codec")
    resolution: str = Field(..., description="Video resolution (e.g., '1920x1080')")
    audio_codec: str = Field(..., description="Audio codec")


class VideoTranscriptionResponse(LargeTranscriptionResponse):
    """Video processing response with video metadata"""

    video_info: VideoInfo = Field(..., description="Video file metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "video.mp4",
                "language": "en",
                "duration": 120.5,
                "num_segments": 45,
                "num_chunks": 4,
                "chunking_strategy": "auto",
                "processing_time": 12.3,
                "realtime_factor": 9.8,
                "segments": [],
                "srt": "...",
                "segments_srt": "...",
                "txt": "...",
                "video_info": {
                    "format": "mp4",
                    "duration": 120.5,
                    "size_bytes": 15728640,
                    "video_codec": "h264",
                    "resolution": "1920x1080",
                    "audio_codec": "aac",
                },
            }
        }


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="WhisperX Transcription API",
    description="Audio transcription with word-level timestamps and speaker diarization",
    version="1.0.0",
)

# Configuration
UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# GPU configuration
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "float16" if DEVICE == "cuda" else "int8")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "16"))

# Enable TF32 for RTX 5090 Blackwell optimization (20-40% speedup on 5th-gen Tensor Cores)
# TF32 provides significant performance boost with minimal accuracy loss
if DEVICE == "cuda":
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    logger.info("TF32 enabled for Tensor Core acceleration")

# Initialize processors
# Enable hw_accel for RTX 5090's 9th-gen NVENC/NVDEC - provides significant speedup for video processing
ffmpeg_processor = FFmpegProcessor(use_hw_accel=True, enhance_speech=True)
video_segmenter = VideoSegmenter(chunk_duration=30, overlap_duration=10)

# Shared directory for file processing
SHARED_DIR = Path("/app/shared")
TEMP_DIR = SHARED_DIR / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

logger.info(
    f"Starting WhisperX API Server on {DEVICE} with compute type {COMPUTE_TYPE}"
)


def format_timestamp_srt(seconds: float) -> str:
    """
    Convert seconds to SRT timestamp format (HH:MM:SS,mmm).

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt_from_segments(segments: list) -> str:
    """
    Generate SRT subtitle content from transcription segments.

    Creates word-level subtitles where each word appears individually
    with precise timing.

    Args:
        segments: List of segment dictionaries with 'words' arrays

    Returns:
        SRT formatted string
    """
    srt_lines = []
    counter = 1

    for segment in segments:
        words = segment.get("words", [])

        for word_obj in words:
            word_text = word_obj.get("word", "").strip()
            start = word_obj.get("start")
            end = word_obj.get("end")

            if not word_text or start is None or end is None:
                continue

            # SRT format:
            # Counter
            # Start --> End
            # Text
            # (blank line)
            srt_lines.append(f"{counter}")
            srt_lines.append(
                f"{format_timestamp_srt(start)} --> {format_timestamp_srt(end)}"
            )
            srt_lines.append(word_text)
            srt_lines.append("")  # Blank line between entries

            counter += 1

    return "\n".join(srt_lines)


def generate_segment_srt(segments: list) -> str:
    """
    Generate SRT subtitle content from segments (not words).
    Creates segment-level subtitles where each subtitle shows
    the full text of a segment.

    Args:
        segments: List of segment dictionaries with 'start', 'end', and 'text' fields

    Returns:
        SRT formatted string with segment-level subtitles
    """
    srt_lines = []
    counter = 1

    for segment in segments:
        text = segment.get("text", "").strip()
        start = segment.get("start")
        end = segment.get("end")

        if not text or start is None or end is None:
            continue

        srt_lines.append(f"{counter}")
        srt_lines.append(
            f"{format_timestamp_srt(start)} --> {format_timestamp_srt(end)}"
        )
        srt_lines.append(text)
        srt_lines.append("")  # Blank line between entries

        counter += 1

    return "\n".join(srt_lines)


def generate_txt_from_segments(segments: list) -> str:
    """
    Generate plain text transcript from transcription segments.

    Concatenates all segment texts into a readable paragraph format.

    Args:
        segments: List of segment dictionaries with 'text' fields

    Returns:
        Plain text transcript
    """
    text_lines = []

    for segment in segments:
        text = segment.get("text", "").strip()
        if text:
            text_lines.append(text)

    return " ".join(text_lines)


def send_progress_callback(
    callback_url: str,
    job_id: str,
    progress: int,
    stage: str,
    message: str,
    segment_info: dict = None,
):
    """
    Send progress update to callback URL.
    Fails silently if callback fails to not interrupt transcription.
    """
    if not callback_url or not job_id:
        return

    try:
        payload = {
            "job_id": job_id,
            "status": "processing",
            "progress": progress,
            "stage": stage,
            "message": message,
        }

        if segment_info:
            payload["segment_info"] = segment_info

        response = requests.post(callback_url, json=payload, timeout=5)
        if response.status_code == 200:
            logger.debug(f"Progress callback sent: {progress}% - {message}")
        else:
            logger.warning(
                f"Progress callback failed with status {response.status_code}"
            )
    except Exception as e:
        logger.warning(f"Failed to send progress callback: {e}")


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "WhisperX Transcription API",
        "version": "1.0.0",
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE,
        "status": "ready",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker"""
    return {
        "status": "healthy",
        "device": DEVICE,
        "gpu_available": torch.cuda.is_available(),
    }


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(
    file: UploadFile = File(...),
    model: str = Form(default="large-v3"),
    language: Optional[str] = Form(default=None),
    enable_diarization: bool = Form(default=True),
    min_speakers: Optional[int] = Form(default=None),
    max_speakers: Optional[int] = Form(default=None),
    hf_token: Optional[str] = Form(default=None),
):
    """
    Transcribe audio file with word-level timestamps and optional speaker diarization.

    **Example Request (curl):**
    ```bash
    curl -X POST https://whisper.lan/transcribe \\
      -F "file=@audio.wav" \\
      -F "model=large-v3" \\
      -F "enable_diarization=false" \\
      --insecure
    ```

    **Parameters:**
    - file: Audio file (mp3, wav, m4a, etc.)
    - model: Whisper model size (tiny, base, small, medium, large-v2, large-v3, large-v3-turbo)
    - language: Language code (auto-detect if None)
    - enable_diarization: Enable speaker diarization (requires hf_token)
    - min_speakers: Minimum number of speakers (for diarization)
    - max_speakers: Maximum number of speakers (for diarization)
    - hf_token: HuggingFace token for diarization models

    **Returns JSON with four ready-to-use formats:**
    - segments: Array of segments with word-level timing (segments[].words[])
    - srt: Pre-formatted word-level subtitles (one word per entry, for karaoke/animations)
    - segments_srt: Pre-formatted segment-level subtitles (one phrase per entry, ideal for AI analysis)
    - txt: Plain text transcript (no timestamps)

    **Example Response:**
    ```json
    {
      "filename": "audio.wav",
      "language": "en",
      "segments": [
        {
          "start": 0.031,
          "end": 3.381,
          "text": " Hello, this is a test.",
          "words": [
            {"word": "Hello,", "start": 0.031, "end": 0.432, "score": 0.894},
            {"word": "this", "start": 0.693, "end": 0.833, "score": 0.999}
          ]
        }
      ],
      "srt": "1\\n00:00:00,031 --> 00:00:00,432\\nHello,\\n\\n2\\n...",
      "segments_srt": "1\\n00:00:00,031 --> 00:00:03,381\\nHello, this is a test.\\n\\n",
      "txt": "Hello, this is a test."
    }
    ```
    """

    temp_file = None

    try:
        # Save uploaded file
        temp_file = UPLOAD_DIR / file.filename
        logger.info(f"Processing file: {file.filename}")

        with open(temp_file, "wb") as f:
            content = await file.read()
            f.write(content)

        # Load model
        logger.info(f"Loading Whisper model: {model}")
        model_obj = whisperx.load_model(
            model, device=DEVICE, compute_type=COMPUTE_TYPE, language=language
        )

        # Transcribe with whisperx
        logger.info("Starting transcription...")
        audio = whisperx.load_audio(str(temp_file))
        result = model_obj.transcribe(audio, batch_size=BATCH_SIZE)

        # Cleanup model to free VRAM
        del model_obj
        gc.collect()
        torch.cuda.empty_cache()

        # Align whisper output for word-level timestamps
        logger.info("Aligning timestamps...")
        detected_language = result.get("language", language)

        try:
            model_a, metadata = whisperx.load_align_model(
                language_code=detected_language, device=DEVICE
            )
            result = whisperx.align(
                result["segments"],
                model_a,
                metadata,
                audio,
                DEVICE,
                return_char_alignments=False,
            )

            # Cleanup alignment model
            del model_a
            gc.collect()
            torch.cuda.empty_cache()

        except Exception as e:
            logger.warning(
                f"Alignment failed: {e}. Continuing without word-level timestamps."
            )

        # Speaker diarization (optional)
        if enable_diarization:
            if not hf_token:
                hf_token = os.getenv("HF_TOKEN")

            if hf_token:
                logger.info("Running speaker diarization...")
                try:
                    diarize_model = whisperx.DiarizationPipeline(
                        use_auth_token=hf_token, device=DEVICE
                    )

                    diarize_segments = diarize_model(
                        audio, min_speakers=min_speakers, max_speakers=max_speakers
                    )

                    result = whisperx.assign_word_speakers(diarize_segments, result)

                    # Cleanup diarization model
                    del diarize_model
                    gc.collect()
                    torch.cuda.empty_cache()

                except Exception as e:
                    logger.warning(
                        f"Diarization failed: {e}. Continuing without speaker labels."
                    )
            else:
                logger.warning(
                    "Diarization requested but no HF_TOKEN provided. Skipping diarization."
                )

        # DEBUG: Log result structure after alignment
        logger.info(
            f"Result keys after alignment: {result.keys() if isinstance(result, dict) else 'Not a dict'}"
        )
        if isinstance(result, dict) and "segments" in result and result["segments"]:
            first_seg = result["segments"][0]
            logger.info(f"First segment keys: {first_seg.keys()}")
            if "words" in first_seg:
                logger.info(
                    f"✓ Words array present with {len(first_seg['words'])} words"
                )
                logger.info(
                    f"Sample word: {first_seg['words'][0] if first_seg['words'] else 'Empty'}"
                )
            else:
                logger.warning("✗ NO 'words' array in segment after alignment!")

        # Prepare response
        # Note: word-level timestamps are in segments[].words[] after alignment
        segments = result.get("segments", [])

        # Generate SRT subtitle content and plain text
        srt_content = generate_srt_from_segments(segments)
        segment_srt_content = generate_segment_srt(segments)
        txt_content = generate_txt_from_segments(segments)

        response = {
            "filename": file.filename,
            "language": detected_language,
            "segments": segments,
            "srt": srt_content,
            "segments_srt": segment_srt_content,
            "txt": txt_content,
        }

        logger.info(f"Transcription completed for {file.filename}")
        return JSONResponse(content=response)

    except Exception as e:
        logger.error(f"Transcription error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    finally:
        # Cleanup temp file
        if temp_file and temp_file.exists():
            temp_file.unlink()

        # Final cleanup
        gc.collect()
        torch.cuda.empty_cache()


def transcribe_audio_segment(
    audio_path: str,
    segment: AudioSegment,
    model,  # Pre-loaded model instance
    language: Optional[str] = None,
) -> dict:
    """
    Transcribe a single audio segment using a pre-loaded model.

    Args:
        audio_path: Path to full audio file
        segment: AudioSegment object with start/end times
        model: Pre-loaded WhisperX model instance (avoids reloading)
        language: Optional language code (if known, skips auto-detection)

    Returns:
        Dictionary with transcription results
    """
    try:
        # Load full audio
        audio = whisperx.load_audio(audio_path)

        # Extract segment
        sample_rate = 16000
        start_sample = int(segment.start * sample_rate)
        end_sample = int(segment.end * sample_rate)
        segment_audio = audio[start_sample:end_sample]

        # Transcribe with pre-loaded model (no model loading overhead!)
        result = model.transcribe(
            segment_audio, batch_size=BATCH_SIZE, language=language
        )

        # Adjust timestamps to absolute time
        for seg in result.get("segments", []):
            seg["start"] += segment.start
            seg["end"] += segment.start

        return {
            "segment_id": segment.segment_id,
            "start": segment.start,
            "end": segment.end,
            "segments": result.get("segments", []),
            "language": result.get("language", language),
        }

    except Exception as e:
        logger.error(f"Error transcribing segment {segment.segment_id}: {e}")
        return {
            "segment_id": segment.segment_id,
            "start": segment.start,
            "end": segment.end,
            "error": str(e),
            "segments": [],
        }


@app.post("/transcribe-large", response_model=LargeTranscriptionResponse)
async def transcribe_large(
    file: UploadFile = File(...),
    model: str = Form(default="large-v3"),
    language: Optional[str] = Form(default=None),
    chunking_strategy: str = Form(default="auto"),
    enable_diarization: bool = Form(default=True),
    hf_token: Optional[str] = Form(default=None),
    callback_url: Optional[str] = Form(default=None),
    job_id: Optional[str] = Form(default=None),
):
    """
    Transcribe large audio/video files with automatic chunking.

    Uses VAD-based chunking for optimal performance (12x speedup per research).
    Automatically segments files >10 minutes for efficient processing.

    **Example Request (curl):**
    ```bash
    curl -X POST https://whisper.lan/transcribe-large \\
      -F "file=@long-video.mp4" \\
      -F "model=large-v3" \\
      -F "chunking_strategy=vad" \\
      -F "enable_diarization=true" \\
      -F "hf_token=hf_xxxxx" \\
      --insecure
    ```

    **Parameters:**
    - file: Audio or video file
    - model: Whisper model (default: large-v3)
    - language: Language code (auto-detect if None)
    - chunking_strategy: 'auto', 'vad', 'time', or 'silence'
    - enable_diarization: Enable speaker diarization
    - hf_token: HuggingFace token for diarization
    - callback_url: Optional URL to POST progress updates
    - job_id: Optional job ID for progress tracking

    **Returns JSON with four ready-to-use formats:**
    - segments: Array of stitched segments with word-level timing (segments[].words[])
    - srt: Pre-formatted word-level subtitles (one word per entry, for karaoke/animations)
    - segments_srt: Pre-formatted segment-level subtitles (one phrase per entry, ideal for AI analysis)
    - txt: Plain text transcript (no timestamps)

    Plus metadata: duration, processing_time, realtime_factor, num_chunks, chunking_strategy

    **Example Response:**
    ```json
    {
      "filename": "long-video.mp4",
      "duration": 1834.5,
      "language": "en",
      "num_segments": 156,
      "num_chunks": 12,
      "chunking_strategy": "vad",
      "processing_time": 89.3,
      "realtime_factor": 20.5,
      "segments": [...],
      "srt": "1\\n00:00:00,031 --> 00:00:00,432\\nHello,\\n\\n...",
      "segments_srt": "1\\n00:00:00,031 --> 00:00:05,381\\nHello, this is a test.\\n\\n...",
      "txt": "Full transcript text..."
    }
    ```
    """
    temp_file = None
    audio_file = None

    try:
        start_time = time.time()

        # Save uploaded file
        temp_file = TEMP_DIR / f"{time.time()}_{file.filename}"
        logger.info(f"Processing large file: {file.filename}")

        with open(temp_file, "wb") as f:
            content = await file.read()
            f.write(content)

        # Extract audio if video file
        if temp_file.suffix.lower() in [".mp4", ".avi", ".mkv", ".mov", ".webm"]:
            logger.info("Detected video file, extracting audio...")
            audio_file = TEMP_DIR / f"{temp_file.stem}.wav"
            ffmpeg_processor.extract_audio_optimized(str(temp_file), str(audio_file))
        else:
            audio_file = temp_file

        # Get audio duration
        info = ffmpeg_processor.get_video_info(str(audio_file))
        duration = info.get("duration", 0)
        logger.info(f"Audio duration: {duration:.1f}s")

        # Segment audio
        segments = video_segmenter.segment_audio(
            str(audio_file), strategy=chunking_strategy
        )
        logger.info(
            f"Created {len(segments)} segments using '{chunking_strategy}' strategy"
        )

        # Load Whisper model ONCE and reuse for all segments (major optimization!)
        # Best practice from 2025: "Most time is taken by model initialization"
        logger.info(f"Loading Whisper model: {model}")
        model_obj = whisperx.load_model(
            model,
            device=DEVICE,
            compute_type=COMPUTE_TYPE,
            language=language,  # Pre-set language if provided
        )

        # Detect language once from first segment if not provided (optimization)
        # Whisper design: language detected once, reused for all segments
        all_segments = []
        detected_language = language

        if not detected_language and len(segments) > 0:
            logger.info("Detecting language from first segment...")
            first_result = transcribe_audio_segment(
                str(audio_file), segments[0], model_obj, language=None
            )
            detected_language = first_result.get("language", "en")
            all_segments.extend(first_result.get("segments", []))
            logger.info(f"Detected language: {detected_language}")
            start_idx = 1  # Skip first segment since we already processed it
        else:
            start_idx = 0

        # Transcribe remaining segments with cached model and detected language
        for i in range(start_idx, len(segments)):
            seg = segments[i]
            logger.info(
                f"Transcribing segment {i + 1}/{len(segments)} ({seg.start:.1f}s - {seg.end:.1f}s)"
            )

            # Calculate progress: 20-80% range for transcription phase
            segment_progress = 20 + int((i / len(segments)) * 60)

            # Send progress callback before processing segment
            send_progress_callback(
                callback_url=callback_url,
                job_id=job_id,
                progress=segment_progress,
                stage="transcription",
                message=f"Transcribing segment {i + 1}/{len(segments)}",
                segment_info={
                    "current": i + 1,
                    "total": len(segments),
                    "time_range": f"{seg.start:.1f}s - {seg.end:.1f}s",
                },
            )

            # Reuse model and detected language (no reload, no re-detection!)
            result = transcribe_audio_segment(
                str(audio_file), seg, model_obj, language=detected_language
            )
            all_segments.extend(result.get("segments", []))

        # Cleanup model after all segments processed
        del model_obj
        gc.collect()
        torch.cuda.empty_cache()

        # Align for word-level timestamps
        logger.info("Aligning timestamps across all segments...")
        send_progress_callback(
            callback_url=callback_url,
            job_id=job_id,
            progress=80,
            stage="alignment",
            message="Aligning word-level timestamps...",
        )

        audio = whisperx.load_audio(str(audio_file))

        try:
            model_a, metadata = whisperx.load_align_model(
                language_code=detected_language or "en", device=DEVICE
            )
            result = whisperx.align(
                all_segments,
                model_a,
                metadata,
                audio,
                DEVICE,
                return_char_alignments=False,
            )
            all_segments = result.get("segments", all_segments)

            del model_a
            gc.collect()
            torch.cuda.empty_cache()

        except Exception as e:
            logger.warning(f"Alignment failed: {e}")

        # Diarization (optional)
        if enable_diarization:
            if not hf_token:
                hf_token = os.getenv("HF_TOKEN")

            if hf_token:
                logger.info("Running speaker diarization...")
                send_progress_callback(
                    callback_url=callback_url,
                    job_id=job_id,
                    progress=85,
                    stage="diarization",
                    message="Identifying speakers...",
                )

                try:
                    diarize_model = whisperx.DiarizationPipeline(
                        use_auth_token=hf_token, device=DEVICE
                    )
                    diarize_segments = diarize_model(audio)
                    all_segments = whisperx.assign_word_speakers(
                        diarize_segments, {"segments": all_segments}
                    )["segments"]

                    del diarize_model
                    gc.collect()
                    torch.cuda.empty_cache()

                except Exception as e:
                    logger.warning(f"Diarization failed: {e}")

        processing_time = time.time() - start_time
        realtime_factor = duration / processing_time if processing_time > 0 else 0

        # Generate SRT subtitle content
        srt_content = generate_srt_from_segments(all_segments)
        segment_srt_content = generate_segment_srt(all_segments)
        txt_content = generate_txt_from_segments(all_segments)

        response = {
            "filename": file.filename,
            "duration": duration,
            "language": detected_language,
            "num_segments": len(all_segments),
            "num_chunks": len(segments),
            "chunking_strategy": chunking_strategy,
            "processing_time": processing_time,
            "realtime_factor": realtime_factor,
            "segments": all_segments,
            "srt": srt_content,
            "segments_srt": segment_srt_content,
            "txt": txt_content,
        }

        logger.info(
            f"Large file transcription completed in {processing_time:.1f}s ({realtime_factor:.1f}x realtime)"
        )
        return JSONResponse(content=response)

    except Exception as e:
        logger.error(f"Large file transcription error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    finally:
        # Cleanup temp files
        if temp_file and temp_file.exists():
            temp_file.unlink()
        if audio_file and audio_file != temp_file and audio_file.exists():
            audio_file.unlink()

        gc.collect()
        torch.cuda.empty_cache()


@app.post("/process-video", response_model=VideoTranscriptionResponse)
async def process_video(
    file: UploadFile = File(...),
    model: str = Form(default="large-v3"),
    language: Optional[str] = Form(default=None),
    enhance_audio: bool = Form(default=True),
    enable_diarization: bool = Form(default=True),
    hf_token: Optional[str] = Form(default=None),
):
    """
    Process video file: extract audio, enhance, and transcribe.

    Optimized workflow for video transcription with speech enhancement.

    **Example Request (curl):**
    ```bash
    curl -X POST https://whisper.lan/process-video \\
      -F "file=@video.mp4" \\
      -F "model=large-v3" \\
      -F "enhance_audio=true" \\
      --insecure
    ```

    **Parameters:**
    - file: Video file (mp4, avi, mkv, etc.)
    - model: Whisper model
    - language: Language code
    - enhance_audio: Apply speech enhancement filters
    - enable_diarization: Enable speaker diarization
    - hf_token: HuggingFace token

    **Returns JSON with four ready-to-use formats:**
    - segments: Array of segments with word-level timing (segments[].words[])
    - srt: Pre-formatted word-level subtitles (one word per entry, for karaoke/animations)
    - segments_srt: Pre-formatted segment-level subtitles (one phrase per entry, ideal for AI analysis)
    - txt: Plain text transcript (no timestamps)

    Plus video metadata: format, duration, size, codecs, resolution

    **Example Response:**
    ```json
    {
      "filename": "video.mp4",
      "language": "en",
      "segments": [...],
      "srt": "...",
      "segments_srt": "...",
      "txt": "...",
      "video_info": {
        "format": "mp4",
        "duration": 120.5,
        "size_bytes": 15728640,
        "video_codec": "h264",
        "resolution": "1920x1080",
        "audio_codec": "aac"
      }
    }
    ```
    """
    temp_video = None
    temp_audio = None

    try:
        # Save video
        temp_video = TEMP_DIR / f"{time.time()}_{file.filename}"
        logger.info(f"Processing video: {file.filename}")

        with open(temp_video, "wb") as f:
            content = await file.read()
            f.write(content)

        # Get video info
        video_info = ffmpeg_processor.get_video_info(str(temp_video))

        # Extract and enhance audio
        temp_audio = TEMP_DIR / f"{temp_video.stem}.wav"

        if enhance_audio:
            logger.info("Extracting and enhancing audio...")
            ffmpeg_processor.extract_audio_optimized(str(temp_video), str(temp_audio))
        else:
            # Basic extraction without enhancement
            ffmpeg_processor.extract_audio_optimized(
                str(temp_video), str(temp_audio), sample_rate=16000, channels=1
            )

        # Use the large file endpoint for transcription
        # (This reuses the chunking logic)
        logger.info("Transcribing extracted audio...")

        # Create a mock UploadFile for internal processing
        with open(temp_audio, "rb") as audio_file:
            audio_content = audio_file.read()

            # Process through large file transcription
            class MockUploadFile:
                def __init__(self, filename, content):
                    self.filename = filename
                    self._content = content

                async def read(self):
                    return self._content

            mock_file = MockUploadFile(temp_audio.name, audio_content)

            # Transcribe using large file endpoint logic
            transcription_result = await transcribe_large(
                file=mock_file,
                model=model,
                language=language,
                chunking_strategy="auto",
                enable_diarization=enable_diarization,
                hf_token=hf_token,
            )

            # Add video metadata to response
            result_data = transcription_result.body.decode("utf-8")
            import json

            transcription_data = json.loads(result_data)

            transcription_data["video_info"] = {
                "format": video_info.get("format", ""),
                "duration": video_info.get("duration", 0),
                "size_bytes": video_info.get("size_bytes", 0),
                "video_codec": video_info.get("video_codec", ""),
                "resolution": f"{video_info.get('video_width', 0)}x{video_info.get('video_height', 0)}",
                "audio_codec": video_info.get("audio_codec", ""),
            }

            return JSONResponse(content=transcription_data)

    except Exception as e:
        logger.error(f"Video processing error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Video processing failed: {str(e)}"
        )

    finally:
        # Cleanup
        if temp_video and temp_video.exists():
            temp_video.unlink()
        if temp_audio and temp_audio.exists():
            temp_audio.unlink()

        gc.collect()
        torch.cuda.empty_cache()


@app.get("/models")
async def list_models():
    """List available Whisper models"""
    return {
        "models": [
            "tiny",
            "base",
            "small",
            "medium",
            "large-v2",
            "large-v3",
            "large-v3-turbo",
        ],
        "recommended_for_rtx5090": ["large-v3", "large-v3-turbo"],
        "note": "large-v3 provides best accuracy, large-v3-turbo is 6x faster with similar quality",
        "rtx5090_features": "32GB VRAM, 5th-gen Tensor Cores with FP4/INT4, 3,352 AI TOPS",
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
