# VibeVoice API Server

A production-ready REST API server for [Microsoft VibeVoice](https://microsoft.github.io/VibeVoice/) text-to-speech with voice cloning, multi-speaker support, and streaming capabilities.

## Features

- **Single-Speaker TTS** with optional voice cloning from audio samples
- **Multi-Speaker Conversations** (2-4 speakers) with distinct voices
- **Streaming Audio Output** for low-latency playback
- **Model Management** - Load, unload, and switch between models
- **Voice Cloning** from 10-60 second audio samples
- **LoRA Support** for fine-tuned voices
- **Multiple Output Formats** - WAV, MP3, OGG
- **Docker Support** with CUDA for GPU acceleration
- **Auto-Generated API Docs** via Swagger UI

## Architecture

Based on the proven [xtts-api-server](https://github.com/daswer123/xtts-api-server) architecture pattern, adapted for VibeVoice.

## Quick Start

### Prerequisites

- Python 3.10+
- CUDA 12.1+ (for GPU acceleration)
- Docker & Docker Compose (for containerized deployment)
- 6-20GB VRAM depending on model choice

### Installation

#### Option 1: Docker (Recommended)

1. **Clone the repository:**
```bash
git clone <repository-url>
cd vibevoice-api-server
```

2. **Download VibeVoice models:**

Place models in `./models/vibevoice/` directory:

```bash
# Example: Download VibeVoice-1.5B
mkdir -p models/vibevoice
cd models/vibevoice
git clone https://huggingface.co/microsoft/VibeVoice-1.5B
```

Available models:
- `VibeVoice-1.5B` (5.4GB) - Fast, single-speaker
- `VibeVoice-Large` (18.7GB) - Best quality, multi-speaker
- `VibeVoice-Large-Q8` (11.6GB) - Quantized, 12GB GPUs
- `VibeVoice-Large-Q4` (6.6GB) - Quantized, 8GB GPUs

3. **Start the server:**
```bash
docker-compose up -d
```

The API will be available at `http://localhost:8000`

#### Option 2: Local Installation

1. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env to set MODELS_DIR and other settings
```

4. **Run the server:**
```bash
python -m uvicorn vibevoice_api_server.main:app --host 0.0.0.0 --port 8000
```

## API Documentation

Once the server is running, visit:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Core Endpoints

#### Health Check
```bash
GET /api/health
```

#### List Available Models
```bash
GET /api/models
```

#### Load a Model
```bash
POST /api/models/{model_name}/load
```

#### Single-Speaker TTS
```bash
POST /api/tts
```

#### Multi-Speaker TTS
```bash
POST /api/tts/multi-speaker
```

#### Streaming TTS
```bash
POST /api/tts/stream
```

## Usage Examples

### 1. Basic Text-to-Speech

**Python:**
```python
import requests
import base64

response = requests.post(
    "http://localhost:8000/api/tts",
    json={
        "text": "Hello, this is a test of VibeVoice text to speech.",
        "model": "VibeVoice-1.5B",
        "seed": 42,
        "output_format": "wav"
    }
)

data = response.json()
audio_bytes = base64.b64decode(data["audio_base64"])

with open("output.wav", "wb") as f:
    f.write(audio_bytes)
```

**cURL:**
```bash
curl -X POST "http://localhost:8000/api/tts" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world!",
    "model": "VibeVoice-1.5B"
  }' | jq -r '.audio_base64' | base64 -d > output.wav
```

### 2. Voice Cloning

**Python:**
```python
import requests
import base64

# Read voice sample
with open("voice_sample.wav", "rb") as f:
    voice_audio_base64 = base64.b64encode(f.read()).decode()

response = requests.post(
    "http://localhost:8000/api/tts",
    json={
        "text": "This will sound like the voice sample.",
        "model": "VibeVoice-1.5B",
        "voice_audio_base64": voice_audio_base64,
        "seed": 42
    }
)

audio_bytes = base64.b64decode(response.json()["audio_base64"])
with open("cloned_voice.wav", "wb") as f:
    f.write(audio_bytes)
```

**Multipart File Upload:**
```bash
curl -X POST "http://localhost:8000/api/tts" \
  -F "text=This is cloned speech." \
  -F "model=VibeVoice-1.5B" \
  -F "voice_audio=@voice_sample.wav"
```

### 3. Multi-Speaker Conversation

**Python:**
```python
import requests
import base64

text = """
[1]: Hello! How are you today?
[2]: I'm doing great, thanks for asking! How about you?
[1]: Pretty good! The weather is nice.
[2]: Yes, it's a beautiful day!
"""

response = requests.post(
    "http://localhost:8000/api/tts/multi-speaker",
    json={
        "text": text,
        "model": "VibeVoice-Large",
        "seed": 42
    }
)

audio_bytes = base64.b64decode(response.json()["audio_base64"])
with open("conversation.wav", "wb") as f:
    f.write(audio_bytes)
```

### 4. Streaming TTS

**Python:**
```python
import requests
import json
import base64

response = requests.post(
    "http://localhost:8000/api/tts/stream",
    json={
        "text": "This is a longer text that will be streamed in chunks.",
        "model": "VibeVoice-1.5B"
    },
    stream=True
)

audio_chunks = []

for line in response.iter_lines():
    if line.startswith(b"data: "):
        data = json.loads(line[6:])
        if not data["is_final"]:
            chunk_bytes = base64.b64decode(data["audio_base64"])
            audio_chunks.append(chunk_bytes)
            print(f"Received chunk {data['chunk_index']}")

# Combine all chunks
with open("streamed_output.wav", "wb") as f:
    for chunk in audio_chunks:
        f.write(chunk)
```

### 5. Model Management

**Load a specific model:**
```python
import requests

requests.post(
    "http://localhost:8000/api/models/VibeVoice-Large/load",
    json={
        "attention_type": "flash_attention_2",
        "quantize_llm": "8bit",
        "diffusion_steps": 20
    }
)
```

**Get current model:**
```python
response = requests.get("http://localhost:8000/api/models/current")
print(response.json())
```

**Unload model to free memory:**
```python
requests.post("http://localhost:8000/api/models/VibeVoice-Large/unload")
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODELS_DIR` | `./models/vibevoice` | Directory containing models |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `DEFAULT_MODEL` | `VibeVoice-1.5B` | Model to load on first request |
| `ENABLE_CORS` | `true` | Enable CORS for cross-origin requests |

### Request Parameters

#### Single-Speaker TTS

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | string | required | Text to synthesize |
| `model` | string | `VibeVoice-1.5B` | Model name |
| `voice_audio_base64` | string | null | Base64 voice sample for cloning |
| `seed` | integer | `42` | Random seed |
| `cfg_scale` | float | `1.3` | Classifier-free guidance scale |
| `diffusion_steps` | integer | `20` | Number of diffusion steps |
| `use_sampling` | boolean | `false` | Use sampling vs greedy |
| `temperature` | float | `0.95` | Sampling temperature |
| `top_p` | float | `0.95` | Nucleus sampling |
| `voice_speed_factor` | float | `1.0` | Speed adjustment (0.8-1.2) |
| `max_words_per_chunk` | integer | `250` | Max words per chunk |
| `output_format` | string | `wav` | Output format (wav/mp3/ogg) |

#### Multi-Speaker TTS

Same as single-speaker, plus:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `speaker1_voice` | string | null | Voice sample for speaker 1 |
| `speaker2_voice` | string | null | Voice sample for speaker 2 |
| `speaker3_voice` | string | null | Voice sample for speaker 3 |
| `speaker4_voice` | string | null | Voice sample for speaker 4 |

**Text format:** Use `[N]:` markers for speakers (N=1-4):
```
[1]: First speaker says this.
[2]: Second speaker responds.
[1]: First speaker again.
```

## Performance Tips

1. **Model Selection:**
   - Use `VibeVoice-1.5B` for fast, single-speaker generation
   - Use `VibeVoice-Large` for best quality multi-speaker
   - Use quantized models (Q8/Q4) for limited VRAM

2. **GPU Optimization:**
   - Enable Flash Attention 2: `attention_type: "flash_attention_2"`
   - Use 8-bit quantization: `quantize_llm: "8bit"`

3. **Chunking:**
   - Adjust `max_words_per_chunk` for long texts
   - Smaller chunks = faster first response, more processing

4. **Pre-load Models:**
   - Use `/api/models/{model_name}/load` before generating
   - Avoids cold start on first request

## Troubleshooting

### CUDA Out of Memory

- Try a smaller model (1.5B or Q4)
- Enable quantization: `quantize_llm: "8bit"`
- Reduce `diffusion_steps` to 15

### Slow Generation

- Enable Flash Attention 2 (requires supported GPU)
- Use quantized models (Q8/Q4)
- Pre-load models before generation

### Voice Cloning Quality

- Use 20-30 second voice samples (min 10s)
- Ensure clean audio (no background noise)
- Match language of voice sample to target text

## Development

### Running Tests

```bash
pytest tests/
```

### Code Structure

```
vibevoice-api-server/
├── vibevoice_api_server/
│   ├── main.py              # FastAPI app & routes
│   ├── models.py            # Pydantic models
│   ├── model_manager.py     # Model loading/management
│   ├── generation.py        # TTS generation logic
│   └── audio_processing.py  # Audio utilities
├── vvembed/                 # VibeVoice core
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## References

- [Microsoft VibeVoice](https://microsoft.github.io/VibeVoice/)
- [xtts-api-server](https://github.com/daswer123/xtts-api-server) - Architecture inspiration
- [Coqui TTS](https://github.com/coqui-ai/TTS) - TTS patterns

## License

This project wraps Microsoft VibeVoice (MIT License). See the original repository for details.

## Contributing

Contributions welcome! Please open an issue or pull request.

## Support

For issues or questions, please open a GitHub issue.

---

**Note:** VibeVoice is intended for research purposes. Please review Microsoft's usage guidelines before deploying in production.
