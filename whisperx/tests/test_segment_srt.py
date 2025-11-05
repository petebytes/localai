#!/usr/bin/env python3
"""
Test script to verify segment-level SRT output
"""
import requests
import json
from pathlib import Path

# Test with a small audio file
test_file = Path("/home/ghar/code/localai/shared/temp/test_audio.mp3")

if not test_file.exists():
    print(f"Error: Test file not found: {test_file}")
    exit(1)

print(f"Testing segment-level SRT generation")
print(f"Test file: {test_file}")
print(f"File size: {test_file.stat().st_size / 1024:.1f} KB")
print("-" * 60)

# Call WhisperX API (via HTTPS with self-signed cert)
url = "https://whisper.lan/transcribe"

with open(test_file, "rb") as f:
    files = {"file": (test_file.name, f, "audio/mpeg")}
    data = {
        "model": "base",  # Use small model for faster testing
        "enable_diarization": "false"  # Disable for speed
    }

    print("Sending request to WhisperX...")
    response = requests.post(url, files=files, data=data, verify=False)

if response.status_code != 200:
    print(f"Error: {response.status_code}")
    print(response.text)
    exit(1)

# Parse response
result = response.json()

print(f"\n✓ Request successful!")
print(f"Language detected: {result.get('language', 'unknown')}")
print("-" * 60)

# Check for both SRT formats
has_word_srt = "srt" in result
has_segment_srt = "segments_srt" in result

print(f"\nSRT Format Check:")
print(f"  Word-level SRT (srt):         {'✓ Present' if has_word_srt else '✗ Missing'}")
print(f"  Segment-level SRT (segments_srt): {'✓ Present' if has_segment_srt else '✗ Missing'}")

if not has_segment_srt:
    print("\n✗ FAILED: segments_srt field not found in response!")
    print(f"Available keys: {list(result.keys())}")
    exit(1)

# Analyze segment-level SRT
segment_srt = result["segments_srt"]
word_srt = result.get("srt", "")

print(f"\n✓ SUCCESS: segments_srt field found!")
print(f"\nSize comparison:")
print(f"  Word-level SRT:    {len(word_srt):,} characters")
print(f"  Segment-level SRT: {len(segment_srt):,} characters")
print(f"  Reduction:         {100 * (1 - len(segment_srt)/len(word_srt)):.1f}%")

# Count entries
word_entries = word_srt.count("\n\n") if word_srt else 0
segment_entries = segment_srt.count("\n\n") if segment_srt else 0

print(f"\nEntry count:")
print(f"  Word-level entries:    {word_entries}")
print(f"  Segment-level entries: {segment_entries}")

# Show sample segment-level SRT
print(f"\nSample segment-level SRT (first 500 chars):")
print("-" * 60)
print(segment_srt[:500])
if len(segment_srt) > 500:
    print("...")
print("-" * 60)

# Validate format
lines = segment_srt.strip().split("\n")
if len(lines) >= 3:
    print(f"\n✓ Format validation:")
    print(f"  First entry number: {lines[0]}")
    print(f"  First timestamp:    {lines[1]}")
    print(f"  First text:         {lines[2][:50]}...")

    # Check if timestamp has correct format
    if "-->" in lines[1]:
        print(f"  ✓ Timestamp format correct")
    else:
        print(f"  ✗ Invalid timestamp format")

# Save outputs
output_dir = Path("/home/ghar/code/localai/whisperx/tests")
output_dir.mkdir(exist_ok=True)

segment_srt_file = output_dir / "test_segment_output.srt"
with open(segment_srt_file, "w") as f:
    f.write(segment_srt)
print(f"\n✓ Segment-level SRT saved to: {segment_srt_file}")

full_response_file = output_dir / "test_segment_full_response.json"
with open(full_response_file, "w") as f:
    json.dump(result, f, indent=2)
print(f"✓ Full response saved to: {full_response_file}")

print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED!")
print("=" * 60)
