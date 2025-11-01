# VibeVoice API - Voice Cloning Guide

## Overview

VibeVoice API supports **voice cloning** by accepting audio samples that the model uses to generate speech in that voice. There are **two ways** to provide voice samples:

1. **Base64 encoded audio** in the JSON request body (`voice_audio_base64`)
2. **Multipart file upload** using the `voice_audio` file parameter

## How Voice Cloning Works

### Single-Speaker Voice Cloning

Use the `/api/tts` endpoint with either:
- `voice_audio_base64` field (base64 encoded audio string)
- `voice_audio` file upload (multipart/form-data)

### Multi-Speaker Voice Cloning

Use the `/api/tts/multi-speaker` endpoint with:
- `speaker1_voice`, `speaker2_voice`, `speaker3_voice`, `speaker4_voice` (base64 or file upload)

## Method 1: Base64 Encoded Audio (JSON)

### Python Example

```python
import requests
import base64

# Read your voice sample audio file
with open("my_voice_sample.wav", "rb") as f:
    voice_audio_bytes = f.read()
    voice_audio_base64 = base64.b64encode(voice_audio_bytes).decode('utf-8')

# Make API request with voice cloning
response = requests.post(
    "https://vibevoice.lan/api/tts",
    json={
        "text": "This will sound like my voice!",
        "model": "VibeVoice-1.5B",
        "voice_audio_base64": voice_audio_base64,  # Voice cloning happens here
        "seed": 42,
        "output_format": "wav"
    }
)

# Save the cloned voice output
if response.status_code == 200:
    data = response.json()
    output_audio = base64.b64decode(data["audio_base64"])
    with open("cloned_voice_output.wav", "wb") as f:
        f.write(output_audio)
    print(f"✓ Generated {data['duration_seconds']:.2f}s of cloned speech")
else:
    print(f"Error: {response.status_code}")
    print(response.json())
```

### curl Example

```bash
# First, encode your audio file to base64
VOICE_BASE64=$(base64 -w 0 my_voice_sample.wav)

# Make the API request
curl -X POST "https://vibevoice.lan/api/tts" \
  -H "Content-Type: application/json" \
  -d "{
    \"text\": \"This will sound like my voice!\",
    \"model\": \"VibeVoice-1.5B\",
    \"voice_audio_base64\": \"$VOICE_BASE64\",
    \"seed\": 42
  }" | jq -r '.audio_base64' | base64 -d > cloned_output.wav
```

### JavaScript Example

```javascript
// Read file as base64
const fs = require('fs');

const voiceAudioBuffer = fs.readFileSync('my_voice_sample.wav');
const voiceAudioBase64 = voiceAudioBuffer.toString('base64');

// Make API request
const response = await fetch('https://vibevoice.lan/api/tts', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    text: "This will sound like my voice!",
    model: "VibeVoice-1.5B",
    voice_audio_base64: voiceAudioBase64,  // Voice cloning
    seed: 42,
    output_format: "wav"
  })
});

const data = await response.json();
const audioBuffer = Buffer.from(data.audio_base64, 'base64');
fs.writeFileSync('cloned_output.wav', audioBuffer);
```

## Method 2: Multipart File Upload

This method is **better for large audio files** and doesn't require base64 encoding.

### Python Example with Multipart Upload

```python
import requests

# Prepare the multipart request
files = {
    'voice_audio': ('my_voice.wav', open('my_voice_sample.wav', 'rb'), 'audio/wav')
}

data = {
    'text': 'This will sound like my voice!',
    'model': 'VibeVoice-1.5B',
    'seed': '42',
    'output_format': 'wav'
}

response = requests.post(
    "https://vibevoice.lan/api/tts",
    files=files,
    data=data
)

if response.status_code == 200:
    result = response.json()
    # Decode and save audio
    import base64
    audio_bytes = base64.b64decode(result["audio_base64"])
    with open("cloned_output.wav", "wb") as f:
        f.write(audio_bytes)
    print("✓ Voice cloning successful!")
```

### curl Example with File Upload

```bash
curl -X POST "https://vibevoice.lan/api/tts" \
  -F "text=This will sound like my voice!" \
  -F "model=VibeVoice-1.5B" \
  -F "voice_audio=@my_voice_sample.wav" \
  -F "seed=42" \
  -F "output_format=wav"
```

## Multi-Speaker Voice Cloning

### Python Example

```python
import requests
import base64

# Read voice samples for different speakers
with open("speaker1_voice.wav", "rb") as f:
    speaker1_base64 = base64.b64encode(f.read()).decode()

with open("speaker2_voice.wav", "rb") as f:
    speaker2_base64 = base64.b64encode(f.read()).decode()

# Multi-speaker conversation text
conversation = """
[1]: Hello! How are you doing today?
[2]: I'm doing great, thanks for asking! How about you?
[1]: Pretty good! I've been working on some interesting projects.
[2]: That sounds exciting! Tell me more about them.
"""

response = requests.post(
    "https://vibevoice.lan/api/tts/multi-speaker",
    json={
        "text": conversation,
        "model": "VibeVoice-Large",  # Large model recommended for multi-speaker
        "speaker1_voice": speaker1_base64,  # Voice for [1]:
        "speaker2_voice": speaker2_base64,  # Voice for [2]:
        "seed": 42,
        "output_format": "wav"
    }
)

if response.status_code == 200:
    data = response.json()
    audio_bytes = base64.b64decode(data["audio_base64"])
    with open("conversation_cloned.wav", "wb") as f:
        f.write(audio_bytes)
    print(f"✓ Generated {data['duration_seconds']:.2f}s conversation with cloned voices")
```

## Voice Sample Requirements

### Optimal Voice Sample Characteristics

| Requirement | Recommended | Minimum | Maximum |
|-------------|-------------|---------|---------|
| **Duration** | 20-30 seconds | 10 seconds | 60 seconds |
| **Quality** | Clear, noise-free | Clean speech | - |
| **Format** | WAV, MP3, OGG | Any audio format | - |
| **Sample Rate** | 24kHz (auto-resampled) | Any (will be resampled) | - |
| **Language** | Match target text | Same as output | - |
| **Content** | Natural speech | Single speaker | - |

### Tips for Best Results

1. **Use clean audio**: Minimal background noise, echo, or music
2. **Single speaker only**: Don't use audio with multiple voices
3. **Natural speech**: Conversational tone works best
4. **Good microphone**: Higher quality input = better cloning
5. **Match language**: Voice sample should be in same language as target text
6. **Longer is better**: 20-30 seconds gives best results (but 10s minimum works)

## Request Parameters for Voice Cloning

### TTSRequest Schema

```json
{
  "text": "Text to synthesize",
  "model": "VibeVoice-1.5B",

  // Voice cloning parameter (choose one method)
  "voice_audio_base64": "base64_encoded_audio_string",  // OR use multipart upload

  // Optional parameters
  "seed": 42,
  "cfg_scale": 1.3,
  "diffusion_steps": 20,
  "voice_speed_factor": 1.0,  // 0.8-1.2 (adjust speed)
  "output_format": "wav"  // wav, mp3, or ogg
}
```

### MultiSpeakerTTSRequest Schema

```json
{
  "text": "[1]: Hello! [2]: Hi there!",
  "model": "VibeVoice-Large",

  // Voice samples for each speaker
  "speaker1_voice": "base64_encoded_audio",
  "speaker2_voice": "base64_encoded_audio",
  "speaker3_voice": "base64_encoded_audio",  // Optional
  "speaker4_voice": "base64_encoded_audio",  // Optional

  // Same optional parameters as single-speaker
  "seed": 42,
  "cfg_scale": 1.3,
  "output_format": "wav"
}
```

## Testing Voice Cloning in Swagger UI

1. Visit `https://vibevoice.lan/docs`
2. Click on `POST /api/tts` endpoint
3. Click "Try it out"
4. Fill in the request body:

```json
{
  "text": "This is a test of voice cloning",
  "model": "VibeVoice-1.5B",
  "voice_audio_base64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=",
  "seed": 42
}
```

5. Click "Execute"

**Note**: The base64 string above is a minimal example. Use your actual voice sample base64.

## Complete Working Example

Here's a complete Python script that handles everything:

```python
#!/usr/bin/env python3
"""
VibeVoice API - Voice Cloning Example
"""

import requests
import base64
from pathlib import Path

API_URL = "https://vibevoice.lan"

def clone_voice(text: str, voice_sample_path: str, output_path: str = "cloned_output.wav"):
    """
    Clone a voice and generate speech.

    Args:
        text: Text to synthesize
        voice_sample_path: Path to voice sample audio (WAV, MP3, etc.)
        output_path: Where to save the output
    """
    print(f"📁 Reading voice sample: {voice_sample_path}")

    # Read and encode voice sample
    voice_audio = Path(voice_sample_path).read_bytes()
    voice_base64 = base64.b64encode(voice_audio).decode('utf-8')

    print(f"🎤 Cloning voice for text: {text[:50]}...")

    # Make API request
    response = requests.post(
        f"{API_URL}/api/tts",
        json={
            "text": text,
            "model": "VibeVoice-1.5B",
            "voice_audio_base64": voice_base64,
            "seed": 42,
            "cfg_scale": 1.3,
            "diffusion_steps": 20,
            "output_format": "wav"
        },
        timeout=300  # 5 minute timeout for long texts
    )

    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.json())
        return False

    # Save output
    data = response.json()
    audio_bytes = base64.b64decode(data["audio_base64"])
    Path(output_path).write_bytes(audio_bytes)

    print(f"✅ Success!")
    print(f"   Duration: {data['duration_seconds']:.2f}s")
    print(f"   Model: {data['model_used']}")
    print(f"   Output: {output_path}")

    return True

if __name__ == "__main__":
    # Example usage
    clone_voice(
        text="Hello! This is a demonstration of voice cloning using VibeVoice API.",
        voice_sample_path="my_voice_sample.wav",
        output_path="cloned_speech.wav"
    )
```

## Troubleshooting

### Issue: "Voice audio not provided" or ignored

**Solution**: Make sure you're using either:
- `voice_audio_base64` in JSON body, OR
- `voice_audio` in multipart form data

### Issue: Poor voice cloning quality

**Solutions**:
- Use longer voice samples (20-30 seconds ideal)
- Ensure voice sample is clean (no background noise)
- Try increasing `diffusion_steps` to 30 or 40
- Adjust `cfg_scale` (try 1.5-2.0 for stronger guidance)

### Issue: Voice sounds too fast/slow

**Solution**: Use `voice_speed_factor`:
```json
{
  "voice_speed_factor": 0.95  // Slightly slower
  // or
  "voice_speed_factor": 1.05  // Slightly faster
}
```

### Issue: Large audio files timing out

**Solution**: Use multipart upload instead of base64, or increase request timeout in your client.

## Summary

✅ **Voice cloning is available** in VibeVoice API!

**Two methods:**
1. **JSON with base64**: `voice_audio_base64` field
2. **Multipart upload**: `voice_audio` file parameter

**Best for:**
- Creating personalized TTS voices
- Multi-speaker conversations with real voices
- Audiobook narration with consistent voice
- Voice-over generation from short samples

**Key endpoint**: `POST /api/tts` with `voice_audio_base64` or `voice_audio` file

Visit `https://vibevoice.lan/docs` to try it interactively!
