"""Voice cloning example."""

import requests
import base64
from pathlib import Path

API_URL = "http://localhost:8000"


def clone_voice(text: str, voice_sample_path: str, output_file: str = "cloned.wav"):
    """Clone a voice and generate speech.

    Args:
        text: Text to synthesize
        voice_sample_path: Path to voice sample audio (10-60 seconds)
        output_file: Output audio file path
    """
    print(f"Loading voice sample: {voice_sample_path}")

    # Read voice sample
    voice_path = Path(voice_sample_path)
    if not voice_path.exists():
        print(f"Error: Voice sample not found: {voice_sample_path}")
        return

    voice_audio_base64 = base64.b64encode(voice_path.read_bytes()).decode()

    print("Generating speech with cloned voice...")
    print(f"Text: {text[:50]}...")

    response = requests.post(
        f"{API_URL}/api/tts",
        json={
            "text": text,
            "model": "VibeVoice-1.5B",
            "voice_audio_base64": voice_audio_base64,
            "seed": 42,
            "cfg_scale": 1.3,
            "diffusion_steps": 20,
            "output_format": "wav",
        },
    )

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.json())
        return

    data = response.json()
    audio_bytes = base64.b64decode(data["audio_base64"])

    output_path = Path(output_file)
    output_path.write_bytes(audio_bytes)

    print(f"✓ Cloned voice audio saved to: {output_path}")
    print(f"  Duration: {data['duration_seconds']:.2f}s")


if __name__ == "__main__":
    # Example usage
    text = "This speech will sound like the voice in your sample."
    voice_sample = "path/to/your/voice_sample.wav"  # Replace with actual path

    clone_voice(text, voice_sample, "cloned_voice_output.wav")
