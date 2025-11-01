"""Multi-speaker conversation example."""

import requests
import base64
from pathlib import Path

API_URL = "http://localhost:8000"


def generate_conversation(output_file: str = "conversation.wav"):
    """Generate a multi-speaker conversation.

    Args:
        output_file: Output audio file path
    """
    # Multi-speaker text with [N]: markers
    conversation_text = """
[1]: Hello! Welcome to the podcast. Today we're talking about AI and voice synthesis.
[2]: Thanks for having me! It's great to be here.
[1]: So, tell us about your work in this field. What got you interested?
[2]: Well, I've always been fascinated by how technology can help people communicate more effectively.
[1]: That's really interesting. How do you see voice synthesis evolving in the next few years?
[2]: I think we'll see much more natural and expressive voices, like what we're using right now!
[1]: Absolutely. The quality is really impressive. Thanks for sharing your insights!
[2]: My pleasure. Thank you for having me on the show!
"""

    print("Generating multi-speaker conversation...")
    print(f"Text length: {len(conversation_text)} characters")

    response = requests.post(
        f"{API_URL}/api/tts/multi-speaker",
        json={
            "text": conversation_text,
            "model": "VibeVoice-Large",  # Large model recommended for multi-speaker
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

    print(f"✓ Conversation saved to: {output_path}")
    print(f"  Duration: {data['duration_seconds']:.2f}s")
    print(f"  Model: {data['model_used']}")


def generate_conversation_with_voices(
    speaker1_voice: str,
    speaker2_voice: str,
    output_file: str = "conversation_with_voices.wav",
):
    """Generate conversation with custom voices for each speaker.

    Args:
        speaker1_voice: Path to voice sample for speaker 1
        speaker2_voice: Path to voice sample for speaker 2
        output_file: Output audio file path
    """
    # Load voice samples
    speaker1_audio = base64.b64encode(Path(speaker1_voice).read_bytes()).decode()
    speaker2_audio = base64.b64encode(Path(speaker2_voice).read_bytes()).decode()

    conversation_text = """
[1]: Hi there! How's your day going?
[2]: Pretty good, thanks! Just been working on some interesting projects.
[1]: Oh yeah? What kind of projects?
[2]: AI-related stuff, mostly voice synthesis and natural language processing.
[1]: That sounds really cool! I'd love to hear more about it.
[2]: Sure! Maybe we can chat more about it over coffee sometime.
"""

    print("Generating conversation with custom voices...")

    response = requests.post(
        f"{API_URL}/api/tts/multi-speaker",
        json={
            "text": conversation_text,
            "model": "VibeVoice-Large",
            "speaker1_voice": speaker1_audio,
            "speaker2_voice": speaker2_audio,
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

    print(f"✓ Conversation with custom voices saved to: {output_path}")
    print(f"  Duration: {data['duration_seconds']:.2f}s")


if __name__ == "__main__":
    # Example 1: Generate conversation with default voices
    generate_conversation()

    # Example 2: Generate conversation with custom voices (uncomment and provide paths)
    # generate_conversation_with_voices(
    #     speaker1_voice="path/to/speaker1_sample.wav",
    #     speaker2_voice="path/to/speaker2_sample.wav"
    # )
