# AI Capabilities Matrix - LocalAI Platform

**Last Updated:** 2025-11-01
**System:** Local AI Platform (Docker-based, RTX 5090 optimized)

## Executive Summary

This document provides a comprehensive overview of all AI capabilities available in the LocalAI platform, clearly distinguishing between **programmatic REST APIs** and **UI-only interfaces**.

---

## 🔌 REST/Programmatic APIs (Available)

These services provide REST APIs that can be integrated into applications, automation workflows, and scripts.

| Capability | Service | Endpoint | API Type | Model/Technology | Notes |
|------------|---------|----------|----------|------------------|-------|
| **AUDIO GENERATION** | | | | | |
| Text-to-Speech | ✅ Kokoro-FastAPI | `http://localhost:8880` | REST (OpenAI-compatible) | Kokoro-82M | Multi-language (EN/JP/CN), voice mixing, streaming, multiple formats |
| Text-to-Speech | ✅ VibeVoice API | `http://localhost:8100` | REST (FastAPI) | VibeVoice 1.5B/Large | Voice cloning, multi-speaker, LoRA support, streaming |
| **SPEECH RECOGNITION** | | | | | |
| Speech-to-Text | ✅ WhisperX | `http://localhost:8000` | REST (FastAPI) | WhisperX | Transcription, word-level timestamps, diarization |
| Speech-to-Text | ✅ YouTube Tools | `http://localhost:8456` | REST (FastAPI) | WhisperX (https://whisper.lan/docs) | YouTube download + transcription, segment extraction |
| **WEB SCRAPING** | | | | | |
| Web Crawling | ✅ Crawl4AI | `http://localhost:8000` | REST (FastAPI) + CLI | Crawl4AI v0.7.6 | LLM-friendly markdown, webhooks, job queue, GPU-accelerated |
| **IMAGE GENERATION** | | | | | |
| Text-to-Image / I2I | ✅ ComfyUI | `http://localhost:18188` | WebSocket + REST | Multiple models | Node-based workflows, comprehensive image generation |
| **WORKFLOW/DATA** | | | | | |
| Workflow Automation | ✅ n8n | `https://n8n.lan:5678` | REST + WebUI | n8n | Visual workflow builder, 400+ integrations |
| Database/CMS | ✅ NocoDB | `https://nocodb.lan:8080` | REST + WebUI | NocoDB | Airtable alternative, auto-generated REST API |

**Total REST APIs: 8 services with programmatic access**

---

## 🖥️ Web UI Only (No REST API)

These services provide powerful capabilities but **only through web interfaces** - they cannot be directly integrated into automated workflows without browser automation.

| Capability | Service | UI Access | Model/Technology | Notes |
|------------|---------|-----------|------------------|-------|
| **VIDEO GENERATION** | | | | |
| Text/Image-to-Video+Audio | 🌐 Ovi | `https://ovi.lan:7860` | Ovi 11B (twin backbone) | Gradio UI, simultaneous video+audio, 5s @24fps, 720×720 |
| Multi-Model Video Gen | 🌐 Wan2GP | `https://wan.lan:7860` | Wan 2.1/2.2, Hunyuan, LTX, Flux, Qwen | Gradio UI, queue system, LoRA support, 6GB-32GB VRAM modes |
| Audio-Driven Video Dubbing | 🌐 InfiniteTalk | `https://infinitetalk.lan:8418` | Wan2.1-I2V-14B + InfiniteTalk | Gradio UI, lip sync, unlimited length, multi-person |
| **AUDIO/MISC** | | | | |
| YouTube Downloader | 🌐 YouTube Tools | `https://yttools.lan:7860` | yt-dlp + Whisper | Gradio UI (also has API at :8456) |
| Web Interface | 🌐 Open WebUI | `https://open-webui.lan:8080` | Chat UI | TTS integration with Kokoro |

**Total UI-Only Services: 5 major services (4 video generation platforms + 1 misc)**

---

## 📊 Detailed Capability Comparison

### REST API Services (Programmable)

#### 1. **Kokoro-FastAPI** ✅ `http://localhost:8880`
- **API Type:** REST (OpenAI-compatible `/v1/audio/speech`)
- **Authentication:** None (local network)
- **Documentation:** Swagger UI at `/docs`, Web demo at `/web`
- **Features:**
  - OpenAI Python SDK compatible
  - Voice mixing with weighted combinations
  - Streaming support (300ms first token on GPU)
  - Output formats: MP3, WAV, Opus, FLAC, M4A, PCM
  - Per-word timestamped captions
  - Phoneme-based generation
- **Performance:** 35x-100x realtime on RTX 4060Ti
- **Example:**
  ```python
  from openai import OpenAI
  client = OpenAI(base_url="http://localhost:8880/v1", api_key="not-needed")
  response = client.audio.speech.create(
      model="kokoro", voice="af_bella", input="Hello world!"
  )
  response.stream_to_file("output.mp3")
  ```

#### 2. **VibeVoice API** ✅ `http://localhost:8100`
- **API Type:** REST (FastAPI)
- **Authentication:** None (local network)
- **Documentation:** Swagger UI at `/api/docs`
- **Endpoints:**
  - `POST /api/tts` - Single-speaker TTS
  - `POST /api/tts/multi-speaker` - Multi-speaker conversations
  - `POST /api/tts/stream` - Streaming TTS
  - `POST /api/models/{name}/load` - Model management
  - `GET /api/models/current` - Get loaded model
- **Features:**
  - Voice cloning from 10-60s audio samples
  - Multi-speaker conversations (2-4 speakers)
  - Model switching (1.5B, Large, Q8, Q4)
  - LoRA support for fine-tuned voices
  - Output formats: WAV, MP3, OGG
- **VRAM:** 6-20GB depending on model
- **Example:**
  ```python
  import requests, base64
  response = requests.post("http://localhost:8100/api/tts", json={
      "text": "Hello world!", "model": "VibeVoice-1.5B"
  })
  audio = base64.b64decode(response.json()["audio_base64"])
  ```

#### 3. **WhisperX** ✅ `http://localhost:8000`
- **API Type:** REST (FastAPI)
- **Authentication:** None (local network)
- **Endpoints:**
  - `POST /transcribe` - Audio/video transcription
  - `POST /transcribe-file` - File upload transcription
  - `GET /health` - Health check
- **Features:**
  - Word-level timestamps
  - Speaker diarization
  - Batch processing (batch size: 48 on RTX 5090)
  - Multiple language support
  - Video processing (extracts audio automatically)
- **Performance:** GPU-accelerated, ~3-5x realtime
- **VRAM:** ~8-12GB
- **Example:**
  ```python
  import requests
  files = {"file": open("audio.mp3", "rb")}
  response = requests.post("http://localhost:8000/transcribe-file", files=files)
  transcript = response.json()
  ```

#### 4. **YouTube Tools API** ✅ `http://localhost:8456`
- **API Type:** REST (FastAPI)
- **Authentication:** None (local network)
- **Documentation:** Swagger UI at `/docs`
- **Endpoints:**
  - `POST /api/download` - Create download task
  - `GET /api/status/{task_id}` - Check task status
  - `GET /api/download/{task_id}/audio` - Download audio
  - `GET /api/download/{task_id}/transcript_json` - Download transcript
  - `GET /api/health` - Health check
- **Features:**
  - Background task queue
  - Segment extraction with time ranges
  - Automatic Whisper transcription
  - YouTube built-in transcript fetching
  - Multiple audio formats (MP3, WAV, M4A, FLAC)
  - Transcript formats (JSON, SRT, TXT)
- **UI:** Gradio at `https://yttools.lan:7860` (also available)
- **Example:**
  ```python
  import requests, time
  response = requests.post("http://localhost:8456/api/download", json={
      "url": "https://youtube.com/watch?v=VIDEO_ID",
      "enable_whisper": True
  })
  task_id = response.json()["task_id"]
  # Poll for completion
  while True:
      status = requests.get(f"http://localhost:8456/api/status/{task_id}").json()
      if status["status"] == "completed": break
      time.sleep(5)
  ```

#### 5. **Crawl4AI** ✅ `http://localhost:8000`
- **API Type:** REST (FastAPI) + CLI + Python SDK
- **Authentication:** Optional (API key via `CRAWL4AI_API_KEY`)
- **Documentation:** Available at project site
- **Endpoints:**
  - `/crawl` - Synchronous crawling
  - `/crawl/job` - Async job queue
  - `/llm/job` - LLM extraction job queue
  - Webhook support for async notifications
- **Features:**
  - LLM-friendly markdown output
  - GPU-accelerated content processing
  - Session management, proxies, cookies
  - Custom hooks for pipeline customization
  - Adaptive site learning
  - CLI: `crwl <url> [options]`
- **Version:** v0.7.6 (latest)
- **GPU:** Uses RTX 5090 for ML models
- **Example:**
  ```bash
  # CLI
  crwl https://example.com -o markdown

  # Python
  from crawl4ai import AsyncWebCrawler
  async with AsyncWebCrawler() as crawler:
      result = await crawler.arun(url="https://example.com")
      print(result.markdown)
  ```

#### 6. **ComfyUI** ✅ `http://localhost:18188`
- **API Type:** WebSocket + REST
- **Authentication:** Optional (configurable)
- **Endpoints:**
  - WebSocket for workflow execution
  - REST API for file upload/download
  - `/object_info` - Get available nodes
  - `/prompt` - Submit workflow
  - `/history` - Get generation history
- **Features:**
  - Node-based workflow system
  - Text-to-Image, Image-to-Image
  - Inpainting, outpainting, upscaling
  - Custom nodes support
  - VibeVoice integration (custom node)
  - HiDream sampler (custom node)
- **Models:** User-configured (SD, SDXL, etc.)
- **VRAM:** Varies by model
- **Programmatic Access:** Via ComfyUI API client libraries

#### 7. **n8n** ✅ `https://n8n.lan:5678`
- **API Type:** REST + Web UI
- **Authentication:** Yes (user accounts)
- **Endpoints:**
  - REST API for workflow management
  - Webhook endpoints for triggering workflows
  - 400+ integration nodes
- **Features:**
  - Visual workflow builder
  - Connect services and APIs
  - Custom logic/branching
  - Database integration (PostgreSQL)
  - Community packages support
- **Use Case:** Orchestrate AI services together

#### 8. **NocoDB** ✅ `https://nocodb.lan:8080`
- **API Type:** REST + Web UI
- **Authentication:** Yes (user accounts)
- **Features:**
  - Auto-generated REST API from database schema
  - Forms, views, automations
  - PostgreSQL backend
  - Airtable-like interface
- **Use Case:** Data management for AI workflows

---

### UI-Only Services (Not Programmable)

#### 1. **Ovi** 🌐 `https://ovi.lan:7860`
- **Interface:** Gradio Web UI only
- **No REST API:** Cannot be programmatically controlled
- **Model:** Ovi 11B (twin backbone cross-modal fusion)
- **Capabilities:**
  - Text-to-Video+Audio (T2AV)
  - Image-to-Video+Audio (I2AV)
  - 5-second videos at 24 FPS
  - Resolution: 720×720 area (various aspect ratios up to 960×960)
  - Special tags: `<S>speech<E>`, `<AUDCAP>audio<ENDAUDCAP>`
- **VRAM:** 32GB with CPU offload (80GB full speed)
- **Performance:** ~83s for 121-frame 720×720 video
- **Automation:** Would require browser automation (Selenium/Playwright)

#### 2. **Wan2GP** 🌐 `https://wan.lan:7860`
- **Interface:** Gradio Web UI only
- **No REST API:** Cannot be programmatically controlled
- **Models Supported:**
  - Wan 2.1/2.2 (1.3B-14B params) - T2V, I2V
  - Hunyuan Video
  - LTX Video
  - Flux (image generation)
  - Qwen (image editing)
  - Chatterbox (TTS)
  - Ditto (V2V)
- **Features:**
  - Low VRAM (6GB minimum)
  - Queue system for batch processing
  - LoRA accelerators (FastWan, Lightning) - 10x speedup
  - Integrated tools: MMAudio, Mask Editor, VACE ControlNet
  - Pose/Depth/Flow extraction (DWPose, Depth Anything v2, RAFT)
  - Frame interpolation (RIFE)
  - Multiple memory profiles (6GB to 32GB+)
  - Plugin system
- **VRAM:** 6GB minimum, 32GB recommended
- **Attention:** SageAttention optimized for RTX 5090
- **Automation:** Would require browser automation

#### 3. **InfiniteTalk** 🌐 `https://infinitetalk.lan:8418`
- **Interface:** Gradio Web UI only
- **No REST API:** Cannot be programmatically controlled
- **Model:** Wan2.1-I2V-14B-480P + InfiniteTalk adapters
- **Capabilities:**
  - Audio-driven video dubbing
  - Unlimited-length video generation
  - Video-to-Video and Image-to-Video modes
  - Lip sync + head/body/expression sync
  - Single and multi-person animation
  - 480P and 720P support
  - TeaCache acceleration
  - Quantization (FP8/INT8)
- **VRAM:** 14GB minimum (lower with quantization)
- **Performance:** ~40s per generation (40 steps, 480P)
- **Automation:** Would require browser automation

#### 4. **YouTube Tools UI** 🌐 `https://yttools.lan:7860`
- **Interface:** Gradio Web UI
- **Note:** Also has REST API at `:8456` (listed above)
- **Features:** User-friendly interface for YouTube downloads
- **Automation:** Use the REST API instead

#### 5. **Open WebUI** 🌐 `https://open-webui.lan:8080`
- **Interface:** Web chat interface
- **Integration:** Connected to Kokoro TTS
- **Features:** Chat UI with audio output
- **Note:** Primarily a frontend, not an AI service itself

---

## ❌ Missing Capabilities

### Critical Missing APIs

1. **Large Language Model (LLM) Chat API**
   - **Impact:** HIGH
   - **Use Cases:** Conversational AI, text generation, code completion, question answering, RAG
   - **Recommended:** LLaMA 3.1 70B, Mistral Large 2 via vLLM/TGI
   - **API Standard:** OpenAI-compatible REST API
   - **VRAM Required:** 40-48GB (quantized)
   - **Integration:** Would connect to n8n, Crawl4AI, all workflows

2. **PDF/Document Processing API**
   - **Impact:** MEDIUM-HIGH
   - **Use Cases:** Document extraction, analysis, RAG pipelines
   - **Recommended:** Unstructured.io, LlamaParse, DocTR
   - **API:** REST
   - **VRAM Required:** Minimal (CPU-based)

3. **Music Generation API**
   - **Impact:** MEDIUM
   - **Use Cases:** Background music for videos, soundtracks
   - **Recommended:** MusicGen, Stable Audio, AudioCraft
   - **API:** REST
   - **VRAM Required:** 8-16GB

4. **OCR API**
   - **Impact:** MEDIUM
   - **Use Cases:** Text extraction from images, document digitization
   - **Recommended:** PaddleOCR, EasyOCR, Tesseract
   - **API:** REST
   - **VRAM Required:** 2-4GB (or CPU)

5. **Translation API**
   - **Impact:** MEDIUM
   - **Use Cases:** Multi-language support, content localization
   - **Recommended:** NLLB-200, M2M-100, or LLM-based
   - **API:** REST
   - **VRAM Required:** 4-16GB

6. **Video Understanding/Analysis API**
   - **Impact:** MEDIUM
   - **Use Cases:** Video QA, scene understanding, quality control
   - **Recommended:** Video-LLaVA, VideoChat, GPT-4V
   - **API:** REST
   - **VRAM Required:** 16-32GB

7. **Image-to-3D / Text-to-3D API**
   - **Impact:** MEDIUM
   - **Use Cases:** 3D asset creation, modeling
   - **Recommended:** TripoSR, Point-E, Shap-E
   - **API:** REST
   - **VRAM Required:** 12-24GB

8. **Audio Separation API**
   - **Impact:** LOW-MEDIUM
   - **Use Cases:** Vocal isolation, stem separation, noise removal
   - **Recommended:** Demucs 4, Spleeter
   - **API:** REST
   - **VRAM Required:** 4-8GB

### Missing NLU APIs (Lower Priority)

9. Named Entity Recognition (NER)
10. Sentiment Analysis
11. Text Classification
12. Summarization (could be via LLM)
13. Cross-Modal Retrieval
14. Visual Question Answering (could be via multimodal LLM)

### Missing Infrastructure

15. **Model Training/Fine-tuning API**
   - **Impact:** MEDIUM
   - **Use Cases:** Custom model adaptation, LoRA training
   - **Recommended:** Training infrastructure (Axolotl, torchtune)
   - **VRAM Required:** Varies, 24-80GB

---

## 💪 Platform Strengths

### What You Can Do Programmatically (via APIs):

1. **Audio Processing**
   - ✅ High-quality TTS with voice cloning (2 APIs)
   - ✅ Accurate STT with diarization (2 APIs)
   - ❌ Music generation (missing)
   - ❌ Audio separation (missing)

2. **Image Generation**
   - ✅ Comprehensive workflows via ComfyUI API
   - ❌ Simple REST API for T2I/I2I (ComfyUI requires workflow JSON)

3. **Video Generation**
   - ❌ No programmatic video generation APIs
   - 🌐 All video generation is UI-only (Ovi, Wan2GP, InfiniteTalk)
   - ⚠️ Would require browser automation to integrate

4. **Document/Web**
   - ✅ Excellent web scraping API (Crawl4AI)
   - ❌ No PDF/document processing

5. **Workflow**
   - ✅ Strong automation capabilities (n8n, NocoDB)
   - ✅ All APIs can be orchestrated together

---

## 🎯 Recommendations

### Immediate Priority: Add REST APIs to Video Services

**Problem:** Your most powerful services (Ovi, Wan2GP, InfiniteTalk) are UI-only. This severely limits automation and integration.

**Solution:** Wrap Gradio interfaces with FastAPI:

```python
# Example: Wrap Ovi with FastAPI
from fastapi import FastAPI
from gradio_client import Client

app = FastAPI()
gradio_client = Client("http://localhost:7860")

@app.post("/api/generate-video")
async def generate_video(prompt: str, mode: str = "t2v"):
    result = gradio_client.predict(prompt, mode, api_name="/generate")
    return {"video_url": result}
```

### Medium Priority: Add Missing Core APIs

1. **LLM API Server** (highest impact)
   - Model: LLaMA 3.1 70B or Mistral Large 2
   - Server: vLLM or Text Generation Inference
   - Endpoint: OpenAI-compatible
   - Integration: Connect to all services via n8n

2. **PDF/Document Processing**
   - Tool: Unstructured.io or LlamaParse
   - REST API for extraction
   - Integration: Feed into LLM for analysis

3. **Music Generation**
   - Model: MusicGen or Stable Audio
   - REST API
   - Integration: Background music for Wan2GP/Ovi videos

---

## 📊 Summary Tables

### REST API Count by Category

| Category | Available APIs | Missing APIs | Coverage |
|----------|----------------|--------------|----------|
| Audio Generation | 2 | 2 (music, separation) | 50% |
| Speech Recognition | 2 | 0 | 100% |
| Video Generation | 0 | 0 (all UI-only) | 0% |
| Image Generation | 1 | 0 | 100% |
| Text/LLM | 0 | 6+ (chat, NER, etc.) | 0% |
| Document | 1 | 2 (PDF, OCR) | 33% |
| 3D | 0 | 1 | 0% |
| Workflow | 2 | 0 | 100% |
| **Total** | **8** | **11+** | **42%** |

### Service Access Method

| Total Services | REST APIs | UI Only | Both |
|----------------|-----------|---------|------|
| 13 | 6 | 4 | 2 (YouTube Tools, ComfyUI) |

---

## 🔐 Authentication & Security

**Current Status:** Most services have NO authentication (designed for local network use).

**Production Recommendations:**
- Enable nginx authentication (OAuth2, JWT, Basic Auth)
- Implement API keys for programmatic access
- Add rate limiting
- Enable HTTPS everywhere (currently using self-signed certs)
- Consider VPN for remote access

---

## 🌐 Network Architecture

```
Internet → nginx (443) → Services
              ├─ /kokoro → kokoro-fastapi-gpu:8880 [REST API]
              ├─ /crawl4ai → crawl4ai:8000 [REST API]
              ├─ /comfyui → comfyui:18188 [WebSocket + REST API]
              ├─ /n8n → n8n:5678 [REST API + UI]
              ├─ /nocodb → nocodb:8080 [REST API + UI]
              ├─ /ovi → ovi:7860 [UI only]
              ├─ /wan → wan2gp:7860 [UI only]
              ├─ /infinitetalk → infinitetalk:8418 [UI only]
              └─ /yttools → yttools:7860 [UI] + :8456 [REST API]

Internal (no nginx):
  - whisperx:8000 [REST API]
  - vibevoice-api:8100 [REST API]
  - progress-tracker:5555 [internal]
  - service-status:80 [internal]
```

---

## 🔄 Version History

- **2025-11-01:** Updated with clear API vs UI-only separation
- **2025-11-01:** Initial capability matrix created

---

## 🎯 Conclusion

### Current State:
- **8 REST APIs** providing programmatic access to audio, speech, web scraping, image generation, and workflow automation
- **5 UI-only services** (including 3 major video generation platforms) that cannot be programmatically controlled
- **Strong foundation** for automation via n8n + existing APIs

### Critical Gaps:
1. **No video generation APIs** - all video services are UI-only (biggest limitation)
2. **No LLM/chat API** - limits text generation and RAG capabilities
3. **No document processing** - can't extract from PDFs

### Recommendation Priority:
1. **Add REST APIs to video services** (Ovi, Wan2GP, InfiniteTalk)
2. **Deploy LLM API** (vLLM with LLaMA/Mistral)
3. **Add document processing** (Unstructured.io or LlamaParse)
4. **Add music generation** (MusicGen/Stable Audio)

With these additions, you would have a **world-class AI API platform** covering 90%+ of modern AI use cases with full programmatic control.
