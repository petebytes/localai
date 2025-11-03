# Step 1: YouTube Audio Extraction

## Overview
This step extracts a 30-second audio segment (40-70 second mark) from a YouTube video using the yttools API service.

## Files
- **n8n Workflow**: `n8n/workflows/step1-youtube-audio-extraction.json`
- **Test Script**: `test-step1-audio-extraction.sh`

## Workflow Details

### Input (POST webhook)
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=ao8f3qyMoLM",
  "segment_start": 40,
  "segment_end": 70
}
```

### Webhook Endpoint
```
POST https://n8n.lan/webhook/extract-youtube-audio
```

### Processing Flow
1. **Validate Input** - Check YouTube URL and segment parameters
2. **Submit to yttools** - POST to yttools `/api/download` endpoint
3. **Extract Task ID** - Get task_id from yttools response
4. **Wait 3s** - Initial delay before first status check
5. **Check Status** - GET yttools `/api/status/{task_id}`
6. **Check Completion** - Parse status and decide to continue polling or download
7. **Is Complete?** - Branch: if complete → download, else → wait and poll again
8. **Download Audio** - GET yttools `/api/download/{task_id}/audio`
9. **Prepare Response** - Format final response with metadata
10. **Respond Success** - Return JSON with audio file info

### Output
```json
{
  "success": true,
  "message": "Audio extracted successfully",
  "task_id": "abc123...",
  "file_name": "youtube_audio_abc123.mp3",
  "segment_start": 40,
  "segment_end": 70,
  "duration_seconds": 30,
  "youtube_url": "https://www.youtube.com/watch?v=ao8f3qyMoLM",
  "download_time": "2025-11-01T12:34:56.789Z"
}
```

## Setup Instructions

### 1. Import Workflow to n8n

**Option A: Via n8n UI**
1. Open n8n at `https://n8n.lan`
2. Click "Workflows" → "Import from File"
3. Select `n8n/workflows/step1-youtube-audio-extraction.json`
4. Click "Import"
5. Activate the workflow (toggle switch in top right)

**Option B: Via n8n CLI** (if available)
```bash
n8n import:workflow --input=n8n/workflows/step1-youtube-audio-extraction.json
```

**Option C: Copy to n8n directory**
```bash
# If n8n watches a workflows directory
cp n8n/workflows/step1-youtube-audio-extraction.json /path/to/n8n/workflows/
```

### 2. Verify yttools Service

Check that yttools is running:
```bash
curl -k https://yttools.lan/api/health
```

Expected response:
```json
{"status": "healthy"}
```

### 3. Run Test

```bash
./test-step1-audio-extraction.sh
```

This will:
- Submit a request to extract audio from the test YouTube URL
- Poll for completion
- Download the audio file to `/tmp/test-audio/`
- Verify the audio duration matches expected 30 seconds

### 4. Verify Audio Quality

Listen to the extracted audio:
```bash
# macOS
open /tmp/test-audio/extracted_audio.mp3

# Linux with GUI
xdg-open /tmp/test-audio/extracted_audio.mp3

# Linux with mpv
mpv /tmp/test-audio/extracted_audio.mp3
```

Check that:
- ✅ Audio is approximately 30 seconds long
- ✅ Audio contains content from 40-70 second mark of the video
- ✅ Audio quality is clear (no distortion)
- ✅ Audio format is MP3

## Testing with Different Videos

You can test with different YouTube URLs and segments:

```bash
YOUTUBE_URL="https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
SEGMENT_START=10 \
SEGMENT_END=40 \
./test-step1-audio-extraction.sh
```

## Troubleshooting

### Error: "Missing required parameter: youtube_url"
- Check request body includes `youtube_url` field
- Verify JSON is properly formatted

### Error: "Invalid YouTube URL"
- URL must contain `youtube.com` or `youtu.be`
- Example valid URLs:
  - `https://www.youtube.com/watch?v=ao8f3qyMoLM`
  - `https://youtu.be/ao8f3qyMoLM`

### Error: "Task timeout after 60 attempts"
- yttools may be overloaded or the video is very long
- Check yttools logs: `docker logs yttools`
- Try a different YouTube video

### Error: "yttools task failed"
- Video may be age-restricted or unavailable
- Video may not be downloadable (copyright restrictions)
- Check yttools API for specific error message

### HTTP 404 on webhook
- Workflow is not active in n8n
- Workflow path doesn't match (check it's `/extract-youtube-audio`)
- n8n service is not running

### Audio file is not 30 seconds
- Check `segment_start` and `segment_end` parameters
- Video may be shorter than expected
- yttools may have clipped to video boundaries

## API Reference

### yttools API

**Submit Download**
```
POST https://yttools.lan/api/download
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=...",
  "format": "mp3",
  "extract_segment": true,
  "segment_start": 40,
  "segment_end": 70
}

Response: {"task_id": "abc123..."}
```

**Check Status**
```
GET https://yttools.lan/api/status/{task_id}

Response: {
  "status": "processing|completed|failed",
  "progress": 0-100
}
```

**Download Audio**
```
GET https://yttools.lan/api/download/{task_id}/audio

Response: Binary MP3 file
```

## Next Steps

Once Step 1 is working correctly:
1. ✅ Verify you can extract 30s audio from YouTube (40-70s mark)
2. ✅ Audio file is saved and playable
3. ✅ Audio quality is acceptable for voice cloning

**Proceed to**: Step 2 - Voice Cloning and TTS (vibevoice)

---

## Notes

- Default segment: 40-70 seconds (30s duration)
- Maximum segment duration: 60 seconds
- Polling interval: 3 seconds
- Maximum polling time: 3 minutes (60 polls)
- Output format: MP3
- yttools also provides transcription endpoints (not used in this step)
