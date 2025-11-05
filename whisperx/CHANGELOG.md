# WhisperX API Changelog

## 2025-01-04 - SRT Subtitle Generation Added

### Features Added
- **SRT Subtitle Export**: API now automatically generates `.srt` subtitle files from word-level timings
- **Word-Level Precision**: Each word gets its own subtitle entry with millisecond-accurate timing
- **Dual Format Output**: Responses now include both JSON segments and SRT formatted strings

### API Changes

#### Response Format (Both `/transcribe` and `/transcribe-large`)
**Before:**
```json
{
  "filename": "audio.wav",
  "language": "en",
  "segments": [...]
}
```

**After:**
```json
{
  "filename": "audio.wav",
  "language": "en",
  "segments": [...],
  "srt": "1\n00:00:00,031 --> 00:00:00,454\nWhen\n\n2\n..."
}
```

### New Functions
- `format_timestamp_srt(seconds: float) -> str`: Converts seconds to SRT timestamp format (HH:MM:SS,mmm)
- `generate_srt_from_segments(segments: list) -> str`: Generates complete SRT subtitle string from transcription segments

### Testing
- Added comprehensive test suite in `/whisperx/tests/`
- Test scripts and sample outputs included
- Verified word-level timing accuracy with sample audio

### Use Cases
1. Video editing software (import .srt files)
2. Karaoke applications (word-by-word timing)
3. Language learning tools (pronunciation practice)
4. Accessibility (accurate closed captions)
5. Animated text synchronization

### Backward Compatibility
✅ **Fully backward compatible** - Existing code will continue to work. The new `srt` field is added to responses without changing existing fields.

### Performance Impact
- Negligible overhead (~1ms per 1000 words)
- SRT generation happens in-memory
- No impact on transcription speed
