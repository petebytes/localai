"""Streaming TTS example."""

import requests
import json
import base64
from pathlib import Path
import wave

API_URL = "http://localhost:8000"


def stream_tts(text: str, output_file: str = "streamed_output.wav"):
    """Stream TTS generation and save to file.

    Args:
        text: Text to synthesize
        output_file: Output audio file path
    """
    print(f"Streaming TTS for: {text[:50]}...")
    print("Receiving audio chunks...")

    response = requests.post(
        f"{API_URL}/api/tts/stream",
        json={
            "text": text,
            "model": "VibeVoice-1.5B",
            "seed": 42,
            "output_format": "wav",
        },
        stream=True,
    )

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return

    audio_chunks = []
    chunk_count = 0

    # Process Server-Sent Events
    for line in response.iter_lines():
        if line.startswith(b"data: "):
            try:
                data = json.loads(line[6:])

                if data["is_final"]:
                    print(f"\n✓ Received all {chunk_count} chunks")
                    break

                # Decode audio chunk
                chunk_bytes = base64.b64decode(data["audio_base64"])
                audio_chunks.append(chunk_bytes)
                chunk_count += 1

                # Show progress
                text_preview = data.get("text_segment", "")[:30]
                print(f"  Chunk {data['chunk_index']}: {text_preview}...")

            except json.JSONDecodeError as e:
                print(f"Error decoding chunk: {e}")

    if not audio_chunks:
        print("No audio chunks received")
        return

    # Save combined audio
    output_path = Path(output_file)
    with output_path.open("wb") as f:
        for chunk in audio_chunks:
            f.write(chunk)

    print(f"✓ Streamed audio saved to: {output_path}")


def stream_tts_with_playback(text: str):
    """Stream TTS and play chunks as they arrive.

    Note: Requires pyaudio for real-time playback.

    Args:
        text: Text to synthesize
    """
    try:
        import pyaudio
        import io
    except ImportError:
        print("pyaudio not installed. Install with: pip install pyaudio")
        print("Falling back to file-based streaming...")
        stream_tts(text)
        return

    print("Streaming TTS with real-time playback...")

    response = requests.post(
        f"{API_URL}/api/tts/stream",
        json={
            "text": text,
            "model": "VibeVoice-1.5B",
            "seed": 42,
            "output_format": "wav",
        },
        stream=True,
    )

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return

    # Initialize audio player
    p = pyaudio.PyAudio()
    stream = None

    for line in response.iter_lines():
        if line.startswith(b"data: "):
            data = json.loads(line[6:])

            if data["is_final"]:
                print("\n✓ Playback complete")
                break

            # Decode audio chunk
            chunk_bytes = base64.b64decode(data["audio_base64"])

            # Read WAV header and data
            with wave.open(io.BytesIO(chunk_bytes), "rb") as wf:
                if stream is None:
                    # Initialize stream with first chunk's parameters
                    stream = p.open(
                        format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True,
                    )

                # Play audio
                audio_data = wf.readframes(wf.getnframes())
                stream.write(audio_data)

            print(f"  Playing chunk {data['chunk_index']}...")

    # Cleanup
    if stream:
        stream.stop_stream()
        stream.close()
    p.terminate()


if __name__ == "__main__":
    long_text = """
    Streaming text-to-speech allows you to start playing audio before the entire
    generation is complete. This is particularly useful for long texts, as it
    significantly reduces the time to first audio. The system automatically
    chunks the text at natural boundaries like sentences and paragraphs,
    generating and streaming each chunk sequentially. This approach provides
    a much better user experience for interactive applications.
    """

    # Example 1: Stream to file
    stream_tts(long_text, "streamed_long_text.wav")

    # Example 2: Stream with real-time playback (requires pyaudio)
    # stream_tts_with_playback(long_text)
