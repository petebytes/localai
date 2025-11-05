# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WhisperX Transcription Service - A production-ready FastAPI microservice providing audio/video transcription with word-level timestamps, speaker diarization, and intelligent chunking for large files. Part of the larger LocalAI ecosystem, optimized for RTX 5090 GPU acceleration.

**Core Technologies**: Python 3.10, FastAPI, PyTorch 2.7.1+cu128, WhisperX 3.7.2, FFmpeg

## Common Development Commands

### Running the Service

```bash
# Start via Docker Compose (recommended - includes all dependencies)
cd /home/ghar/code/localai
docker-compose up whisperx

# Build only WhisperX container
cd /home/ghar/code/localai/whisperx
docker build -t whisperx:latest .

# Run standalone for development
python3 api_server.py  # Starts on port 8000
```

### Testing

```bash
# Manual API testing
curl -X POST http://localhost:8000/transcribe \
  -F "file=@test.wav" \
  -F "model=base" \
  -F "enable_diarization=false"

# Test large file processing
curl -X POST http://localhost:8000/transcribe-large \
  -F "file=@long_video.mp4" \
  -F "model=large-v3" \
  -F "chunking_strategy=vad"

# Health check
curl http://localhost:8000/health

# View OpenAPI docs
# http://localhost:8000/docs
```

**Note**: Currently no automated test framework. When adding tests, use pytest with:
```bash
uv add --dev pytest pytest-asyncio httpx
uv run pytest tests/
```

### Development Workflow

```bash
# Install dependencies
uv venv
uv pip install -r requirements.txt

# Format code (if ruff added)
uv run ruff format .

# Type checking (if mypy added)
uv run mypy api_server.py
```

### Docker Management

```bash
# View logs
docker-compose logs -f whisperx

# Rebuild after code changes
docker-compose up --build whisperx

# Clear model cache (if needed)
docker volume rm localai_whisperx-cache

# Monitor GPU usage during processing
nvidia-smi -l 1
```

## Architecture & Design Patterns

### Three-Layer Architecture

1. **API Layer** (`api_server.py`): FastAPI endpoints, Pydantic models, request validation
2. **Processing Layer** (`ffmpeg_processor.py`, `video_segmenter.py`): Video extraction, audio chunking
3. **ML Layer**: WhisperX model loading, transcription, alignment, diarization

### Critical Design Patterns

#### Model Reuse Pattern (PERFORMANCE-CRITICAL)

**Never** load/unload models inside loops. Load once, reuse for all segments:

```python
# ✅ CORRECT - Load once, reuse
model = whisperx.load_model(...)
for segment in segments:
    result = transcribe_with_model(segment, model)  # Reuse model
del model  # Cleanup after all processing

# ❌ WRONG - Loads model 63 times for 30-min video
for segment in segments:
    model = whisperx.load_model(...)  # DON'T DO THIS
    result = transcribe_with_model(segment, model)
    del model
```

**Impact**: 30-50% speedup. See `api_server.py:723-771` and `PERFORMANCE_OPTIMIZATIONS.md` for implementation.

#### Language Detection Caching

Detect language once from first segment, pass to remaining segments (Whisper assumes single language):

```python
detected_language = None
for i, segment in enumerate(segments):
    if i == 0:
        result = transcribe(segment, language=None)  # Auto-detect
        detected_language = result['language']
    else:
        result = transcribe(segment, language=detected_language)  # Reuse
```

**Impact**: 10-15% speedup. See `api_server.py:738-746`.

#### Chunking Strategy

Use VAD-based (Voice Activity Detection) chunking for variable-length content:
- **30-second chunks** with **10-second overlap** (research-backed optimal values)
- VAD detects speech vs silence, merges into chunks
- Overlap handles phrase boundaries cleanly

See `video_segmenter.py` for implementation. Research citations in `PERFORMANCE_OPTIMIZATIONS.md`.

### GPU Optimization Requirements

**TF32 Tensor Cores**: Always enabled for RTX 5090 (20-40% speedup):
```python
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
```

**Memory Management**: Explicitly cleanup after large operations:
```python
del model
gc.collect()
torch.cuda.empty_cache()
```

## Code Organization

### Key Files

- **`api_server.py`** (900+ lines): Main FastAPI app, endpoints, response formatting
  - Pydantic models: `WordTiming`, `TranscriptionSegment`, `TranscriptionResponse`, `LargeTranscriptionResponse`
  - Endpoints: `/`, `/health`, `/transcribe`, `/transcribe-large`
  - Format generators: `generate_srt_from_segments()`, `generate_segment_srt()`, `generate_txt_from_segments()`

- **`ffmpeg_processor.py`**: Video/audio extraction with speech enhancement
  - `FFmpegProcessor.extract_audio_optimized()`: Extracts 16kHz mono WAV with filters
  - `FFmpegProcessor.get_video_info()`: Metadata extraction via ffprobe

- **`video_segmenter.py`**: Intelligent audio chunking
  - `VideoSegmenter.segment_audio()`: Main dispatcher for chunking strategies
  - Strategies: `vad` (optimal), `time` (fallback), `silence` (alternative)

### Output Formats

Every API response includes **4 formats** generated from single transcription:

1. **JSON** (`segments`): Programmatic access with word-level timing
2. **Word-level SRT** (`srt`): One word per entry (karaoke/animations)
3. **Segment-level SRT** (`segments_srt`): One phrase per entry (AI analysis, 77-90% smaller)
4. **Plain text** (`txt`): No timestamps

See `tests/README.md` for detailed format documentation and use cases.

## Version Constraints & Dependencies

### Critical Version Locks

**WhisperX 3.7.2** (PINNED):
- Last version compatible with PyTorch 2.7.1
- Later versions have breaking Pipeline import changes
- Installed via: `pip install "git+https://github.com/m-bain/whisperx.git@v3.7.2"`

**PyTorch 2.7.1+cu128** + **torchaudio 2.8.0**:
- Custom base image fixes AudioMetaData initialization issue
- CUDA 12.8 optimal for RTX 5090 (Blackwell architecture)
- CUDA 12.9/13.0 unsupported (no PyTorch wheels)

### Adding Dependencies

Use `uv` for package management:
```bash
uv add requests  # Runtime dependency
uv add --dev pytest  # Development dependency
```

Update Dockerfile after adding deps to ensure Docker image consistency.

## Testing Philosophy

**Current State**: Manual integration testing only (no pytest framework)

**When Adding Tests** (follow TDD principles from global CLAUDE.md):

1. **Test Behavior, Not Implementation**
   - Test public API endpoints, not internal functions
   - Example: Test `/transcribe` response format, not `generate_srt_from_segments()` directly

2. **Use Real Fixtures**
   - Include small test audio files (< 5 seconds)
   - Import actual Pydantic models, don't redefine schemas

3. **Mock External Dependencies**
   - Mock WhisperX model loading (expensive)
   - Mock FFmpeg calls for unit tests
   - Use real models for integration tests

4. **Test Data Pattern**
```python
def get_mock_segment(overrides: Optional[dict] = None) -> TranscriptionSegment:
    base = {
        "start": 0.0,
        "end": 1.0,
        "text": "Test",
        "words": [{"word": "Test", "start": 0.0, "end": 1.0, "score": 0.95}]
    }
    if overrides:
        base.update(overrides)
    return TranscriptionSegment(**base)
```

## Common Workflows

### Adding a New Output Format

1. Add field to `TranscriptionResponse` Pydantic model
2. Create generator function (e.g., `generate_vtt_from_segments()`)
3. Call generator in both `/transcribe` and `/transcribe-large` endpoints
4. Update `tests/README.md` with format documentation
5. Test with sample file

### Modifying Chunking Strategy

1. Add new strategy to `VideoSegmenter` class
2. Update `chunking_strategy` parameter validation in endpoint
3. Add strategy documentation to docstring
4. Test with various audio lengths (5s, 30s, 5min, 30min)
5. Benchmark performance vs existing strategies

### Debugging Transcription Issues

1. Check logs for model loading failures
2. Verify audio format (should be 16kHz mono after extraction)
3. Test with known-good audio file
4. Monitor GPU memory: `nvidia-smi -l 1`
5. Check alignment step (most common failure point)

## Integration Context

Part of LocalAI ecosystem (`/home/ghar/code/localai/`):
- **Orchestration**: `docker-compose.yml` in parent directory
- **Volumes**: Shares model cache with n8n, ComfyUI, other services
- **Called by**: n8n workflows for video transcription pipelines
- **Nginx proxy**: Accessible at `https://whisper.lan/`

### Environment Variables

Set in Docker Compose or `.env`:
```bash
HF_HOME=/data/.huggingface          # HuggingFace model cache
TRANSFORMERS_CACHE=/data/.huggingface/transformers
TORCH_HOME=/data/.torch             # PyTorch model cache
HF_TOKEN=<optional>                 # For diarization models
```

## Performance Considerations

### Optimization Checklist

When modifying transcription pipeline:
- [ ] Model loaded once and reused? (30-50% speedup)
- [ ] Language detected once? (10-15% speedup)
- [ ] TF32 enabled for GPU operations? (20-40% speedup)
- [ ] Explicit memory cleanup after processing?
- [ ] Chunking strategy optimized for use case?

### Benchmarking

Test with 30-minute video to measure full pipeline:
```bash
time curl -X POST http://localhost:8000/transcribe-large \
  -F "file=@30min_video.mp4" \
  -F "model=large-v3" \
  -o result.json

# Monitor GPU during processing
nvidia-smi dmon -s u
```

**Expected Performance** (RTX 5090):
- 30-minute video: ~2-3 minutes total (10-15x realtime)
- Model loading: ~5-10 seconds (one-time)
- Per-segment transcription: ~1-3 seconds

See `PERFORMANCE_OPTIMIZATIONS.md` for detailed benchmarks.

## Known Issues & Limitations

1. **Pyannote VAD uses old PyTorch 1.10** - TF32 disabled during VAD passes (upstream WhisperX issue)
2. **Sequential segment processing** - Could parallelize 2-4 segments with better VRAM management
3. **Single language assumption** - Language detection caching fails for multilingual content
4. **No automated tests** - Manual testing only, no regression suite

## File Paths Reference

All paths relative to repository root (`/home/ghar/code/localai/whisperx/`):

- Core: `api_server.py`, `ffmpeg_processor.py`, `video_segmenter.py`
- Docker: `Dockerfile`, `Dockerfile.base-whisperx`
- Docs: `CHANGELOG.md`, `PERFORMANCE_OPTIMIZATIONS.md`, `tests/README.md`
- Testing: `tests/test_word_timings.py`, `tests/test_segment_srt.py`
- CLI: `process-video.sh`

Parent directory Docker Compose: `/home/ghar/code/localai/docker-compose.yml`
