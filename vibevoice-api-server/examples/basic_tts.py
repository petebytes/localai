"""Basic text-to-speech example."""

import requests
import base64
from pathlib import Path

API_URL = "http://localhost:8000"


def generate_speech(text: str, output_file: str = "output.wav"):
    """Generate speech from text.

    Args:
        text: Text to synthesize
        output_file: Output audio file path
    """
    print(f"Generating speech for: {text[:50]}...")

    response = requests.post(
        f"{API_URL}/api/tts",
        json={
            "text": text,
            "model": "VibeVoice-1.5B",
            "seed": 42,
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

    print(f"✓ Audio saved to: {output_path}")
    print(f"  Duration: {data['duration_seconds']:.2f}s")
    print(f"  Sample rate: {data['sample_rate']}Hz")
    print(f"  Format: {data['format']}")


if __name__ == "__main__":
    text = "Hello! This is a demonstration of VibeVoice text-to-speech API."
    generate_speech(text)
