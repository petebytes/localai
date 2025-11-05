# WhisperX Word-Level Timing Tests

This directory contains tests and examples for WhisperX word-level timing and SRT subtitle generation.

## Test Files

### Test Scripts
- **test_word_timings.py** - Python test script that validates word-level timing output
- **test_segment_srt.py** - Python test script that validates segment-level SRT generation

### Test Outputs
- **test_segment_full_response.json** - Complete API response with all four formats (JSON segments, word-level SRT, segment-level SRT, and TXT)
- **test_segment_output.srt** - Example segment-level SRT subtitle file
- **test_output.srt** - Example word-level SRT subtitle file (legacy)

## Output Formats

WhisperX API provides four ready-to-use formats in every response:

### 1. JSON (segments with word-level timing)
Complete transcription data with nested word-level timing:
- Segment-level structure with `text`, `start`, `end`
- Word-level array with precise timestamps per word
- Confidence scores (0-1 range) for each word
- Suitable for programmatic processing and analysis

### 2. SRT (word-level subtitles)
Pre-formatted SubRip subtitle file for karaoke-style effects:
- One word per subtitle entry for maximum precision
- Millisecond-precision timestamps
- Perfect for word-by-word animations and karaoke apps
- Compatible with all media players and subtitle tools

### 3. Segment SRT (phrase-level subtitles) **NEW**
Traditional subtitle format optimized for AI analysis and readability:
- One complete sentence/phrase per subtitle entry
- Natural reading format with full context
- ~77-90% smaller than word-level SRT
- **Ideal for AI Agent clip identification** - dramatically reduces token usage
- Standard SRT format - ready for traditional subtitling

### 4. TXT (plain text transcript)
Clean, readable plain text:
- All transcribed text concatenated into natural paragraphs
- No timestamps or metadata
- Suitable for text processing, analysis, or simple reading
- Human-friendly format

## API Response Format

```json
{
  "filename": "audio.wav",
  "language": "en",
  "segments": [
    {
      "start": 0.031,
      "end": 5.367,
      "text": "When I was a kid...",
      "words": [
        {
          "word": "When",
          "start": 0.031,
          "end": 0.454,
          "score": 0.871
        },
        ...
      ]
    }
  ],
  "srt": "1\\n00:00:00,031 --> 00:00:00,454\\nWhen\\n\\n2\\n...",
  "segments_srt": "1\\n00:00:00,031 --> 00:00:05,367\\nWhen I was a kid...\\n\\n2\\n...",
  "txt": "When I was a kid, I feel like you heard the term, don't cry..."
}
```

## SRT Format Examples

### Word-Level SRT (for karaoke/animations)
```srt
1
00:00:00,031 --> 00:00:00,454
When

2
00:00:00,514 --> 00:00:00,555
I

3
00:00:00,615 --> 00:00:00,716
was
```

### Segment-Level SRT (for AI analysis/traditional subtitles)
```srt
1
00:00:00,031 --> 00:00:05,367
When I was a kid, I feel like you heard the term, don't cry.

2
00:00:05,387 --> 00:00:06,635
You don't need to cry.
```

## Running Tests

```bash
# Test with sample audio file
python3 test_word_timings.py

# Or test via API
curl -X POST https://whisper.lan/transcribe \
  -F "file=@woman.wav" \
  -F "model=base" \
  -F "enable_diarization=false" \
  --insecure
```

## Use Cases

1. **Video Subtitles** - Import .srt files into video editors
2. **Karaoke** - Word-by-word timing for karaoke applications
3. **Language Learning** - Precise word timing for pronunciation practice
4. **Accessibility** - Accurate closed captions for accessibility
5. **Animation** - Sync animated text to speech

## API Endpoints

### `/transcribe`
Basic transcription for shorter audio files (< 10 minutes)

### `/transcribe-large`
Optimized for long audio/video files with automatic chunking

Both endpoints now return four formats ready to use:
- **JSON** - Complete segments with word-level timing data
- **SRT** - Pre-formatted word-level subtitle file (for karaoke/animations)
- **Segments SRT** - Pre-formatted segment-level subtitle file (for AI analysis/traditional subtitles)
- **TXT** - Plain text transcript

## Recommended Usage

### For AI Agent Clip Identification (n8n shorts workflow)
Use `segments_srt` instead of `srt`:
- **77-90% token reduction** compared to word-level SRT
- Natural sentence structure makes content analysis easier
- AI can better identify compelling clips from readable text
- Much faster processing and lower costs

### For Text Overlays in Video Rendering
Use word-level data from JSON `segments[].words[]`:
- Extract precise word timings for the identified clip range
- Apply word-by-word overlays with millisecond accuracy
- Create karaoke-style or animated text effects

### Example Workflow
1. **Stage 1 - Clip Identification**: Pass `segments_srt` to AI Agent → identifies 15-60s clip ranges
2. **Stage 2 - Video Rendering**: Extract word timings from JSON for those ranges → apply precise text overlays
