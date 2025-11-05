#!/usr/bin/env python3
"""
Test script to verify WhisperX word-level timing output
"""
import requests
import json
from pathlib import Path

# Test with a small audio file
test_file = Path("/home/ghar/code/localai/shared/temp/test_audio.mp3")

if not test_file.exists():
    print(f"Error: Test file not found: {test_file}")
    exit(1)

print(f"Testing with: {test_file}")
print(f"File size: {test_file.stat().st_size / 1024:.1f} KB")
print("-" * 60)

# Call WhisperX API
url = "http://localhost:8000/transcribe"

with open(test_file, "rb") as f:
    files = {"file": (test_file.name, f, "audio/mpeg")}
    data = {
        "model": "base",  # Use small model for faster testing
        "enable_diarization": "false"  # Disable for speed
    }

    print("Sending request to WhisperX...")
    response = requests.post(url, files=files, data=data)

if response.status_code != 200:
    print(f"Error: {response.status_code}")
    print(response.text)
    exit(1)

# Parse response
result = response.json()

print(f"\n✓ Request successful!")
print(f"Language detected: {result.get('language', 'unknown')}")
print(f"Number of segments: {len(result.get('segments', []))}")
print("-" * 60)

# Check for word-level timings
segments = result.get("segments", [])
if not segments:
    print("⚠ No segments found in response")
    exit(1)

# Check first segment
first_segment = segments[0]
print(f"\nFirst segment structure:")
print(f"  Keys: {list(first_segment.keys())}")
print(f"  Text: {first_segment.get('text', '(no text)')}")
print(f"  Start: {first_segment.get('start', 'N/A')}s")
print(f"  End: {first_segment.get('end', 'N/A')}s")

# Check for words array
if "words" in first_segment:
    words = first_segment["words"]
    print(f"\n✓ Word-level timings FOUND!")
    print(f"  Number of words: {len(words)}")

    # Show first few words
    print(f"\n  Sample words:")
    for i, word in enumerate(words[:5]):
        print(f"    {i+1}. '{word.get('word', '?')}' "
              f"[{word.get('start', '?'):.2f}s - {word.get('end', '?'):.2f}s]")

    # Verify all words have timing
    words_with_timing = sum(1 for w in words if 'start' in w and 'end' in w)
    print(f"\n  Words with timing: {words_with_timing}/{len(words)}")

    if words_with_timing == len(words):
        print("\n✓ SUCCESS: All words have timing information!")
    else:
        print(f"\n⚠ WARNING: {len(words) - words_with_timing} words missing timing")
else:
    print(f"\n✗ FAILED: No 'words' array found in segment!")
    print(f"  Available keys: {list(first_segment.keys())}")

# Save full response for inspection
output_file = Path("/home/ghar/code/localai/test_word_timings_output.json")
with open(output_file, "w") as f:
    json.dump(result, f, indent=2)

print(f"\nFull response saved to: {output_file}")
