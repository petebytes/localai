# VibeVoice API Server - Quick Start Guide

Get up and running with VibeVoice API in 5 minutes!

## 🚀 Quick Start (Docker)

### 1. Download a Model

First, download a VibeVoice model from HuggingFace:

```bash
# Create models directory
mkdir -p models/vibevoice
cd models/vibevoice

# Download VibeVoice-1.5B (fastest, 5.4GB)
git clone https://huggingface.co/microsoft/VibeVoice-1.5B

# Or download VibeVoice-Large for best quality (18.7GB)
# git clone https://huggingface.co/microsoft/VibeVoice-Large

cd ../..
```

### 2. Start the Server

```bash
docker-compose up -d
```

Wait 30-60 seconds for the server to start. Check logs:
```bash
docker-compose logs -f
```

### 3. Test the API

**Check health:**
```bash
curl http://localhost:8000/api/health
```

**Generate your first speech:**
```bash
curl -X POST "http://localhost:8000/api/tts" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello! This is VibeVoice speaking.",
    "model": "VibeVoice-1.5B"
  }' | jq -r '.audio_base64' | base64 -d > hello.wav
```

**Play the audio:**
```bash
# Linux
aplay hello.wav

# Mac
afplay hello.wav

# Windows
start hello.wav
```

### 4. Explore the API

Open the auto-generated documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📚 Example Scripts

We've included Python example scripts in the `examples/` directory:

### Basic TTS
```bash
python examples/basic_tts.py
```

### Voice Cloning
```bash
# First, get a voice sample (10-60 seconds of clear audio)
# Then run:
python examples/voice_cloning.py
```

### Multi-Speaker Conversation
```bash
python examples/multi_speaker.py
```

### Streaming TTS
```bash
python examples/streaming_tts.py
```

### Model Management
```bash
python examples/model_management.py
```

## 🔧 Common Commands

**Stop the server:**
```bash
docker-compose down
```

**View logs:**
```bash
docker-compose logs -f vibevoice-api
```

**Restart the server:**
```bash
docker-compose restart
```

**Update the code:**
```bash
git pull
docker-compose build
docker-compose up -d
```

## ⚙️ Configuration

Edit `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
nano .env
```

Key settings:
- `MODELS_DIR` - Where models are stored
- `PORT` - API port (default: 8000)
- `DEFAULT_MODEL` - Model to load on first request

## 💡 Tips

### GPU Memory Issues?

Use a smaller or quantized model:
- `VibeVoice-1.5B` - 5.4GB (single speaker)
- `VibeVoice-Large-Q8` - 11.6GB (quantized, high quality)
- `VibeVoice-Large-Q4` - 6.6GB (quantized, good quality)

### Faster Generation?

Enable Flash Attention 2 or 8-bit quantization:
```bash
POST /api/models/VibeVoice-1.5B/load
{
  "attention_type": "flash_attention_2",
  "quantize_llm": "8bit"
}
```

### Voice Cloning Not Working?

Make sure your voice sample:
- Is 10-60 seconds long (20-30s optimal)
- Has clear audio (no background noise)
- Is in the same language as your target text

## 🐛 Troubleshooting

**Server won't start:**
```bash
# Check if port 8000 is already in use
sudo lsof -i :8000

# View detailed logs
docker-compose logs vibevoice-api
```

**CUDA errors:**
```bash
# Make sure nvidia-docker is installed
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

**Model not found:**
```bash
# List models directory
ls -la models/vibevoice/

# Check permissions
chmod -R 755 models/
```

## 📖 Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore the [examples/](examples/) directory
- Visit the API docs at http://localhost:8000/docs
- Check out the [VibeVoice paper](https://microsoft.github.io/VibeVoice/) for technical details

## 🆘 Getting Help

- Check the [README.md](README.md) for detailed documentation
- Review logs: `docker-compose logs vibevoice-api`
- Open an issue on GitHub

---

Happy synthesizing! 🎙️
