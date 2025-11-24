# Step 1: YouTube Audio Extraction - Quick Start Guide

## Goal
Extract 30 seconds of audio (40-70s mark) from a YouTube video using yttools API.

## Files Created
- ✅ `n8n/workflows/step1-youtube-audio-extraction.json` - Complete workflow
- ✅ `test-step1-audio-extraction.sh` - Test script
- ✅ `import-step1-workflow.sh` - Import helper
- ✅ `STEP1-AUDIO-EXTRACTION.md` - Detailed documentation

## Quick Start (3 Steps)

### Step 1: Import Workflow to n8n

**Option A: Via Web UI (Easiest)**
```bash
# Open n8n
open https://n8n.lan
# Or visit in browser: https://n8n.lan

# Then:
# 1. Click "Workflows" in left sidebar
# 2. Click "Add workflow" → "Import from file"
# 3. Select: /home/ghar/code/localai/n8n/workflows/step1-youtube-audio-extraction.json
# 4. Click "Import"
# 5. Click "Active" toggle (top right) to activate workflow
```

**Option B: Copy to n8n workflows directory (if file-watching is enabled)**
```bash
# Find your n8n workflows directory and copy
cp n8n/workflows/step1-youtube-audio-extraction.json /path/to/n8n/workflows/
```

### Step 2: Verify yttools is Running

```bash
curl -k https://yttools.lan/api/health
# Expected: {"status": "healthy"}
```

### Step 3: Test the Workflow

```bash
chmod +x test-step1-audio-extraction.sh
./test-step1-audio-extraction.sh
```

This will:
- Submit the test YouTube URL to n8n webhook
- Poll yttools until audio extraction completes
- Download the 30-second MP3 file
- Verify the duration matches expected 30 seconds

## Expected Output

```
=== Step 1: YouTube Audio Extraction Test ===

Configuration:
  N8N Webhook: https://n8n.lan/webhook/extract-youtube-audio
  YouTube URL: https://www.youtube.com/watch?v=ao8f3qyMoLM
  Segment: 40s - 70s (30s)
  Output Dir: /tmp/test-audio

✅ Request successful!

Response:
{
  "success": true,
  "message": "Audio extracted successfully",
  "task_id": "abc123...",
  "file_name": "youtube_audio_abc123.mp3",
  "segment_start": 40,
  "segment_end": 70,
  "duration_seconds": 30,
  "youtube_url": "https://www.youtube.com/watch?v=ao8f3qyMoLM"
}

✅ Audio file downloaded successfully!
  File: /tmp/test-audio/extracted_audio.mp3
  Size: 0.47 MB
  Actual Duration (ffprobe): 30s

✅ Audio duration verified!

=== Step 1 Test PASSED ===
```

## Troubleshooting

### Error: "404 Not Found" when calling webhook
**Solution**: Workflow is not active in n8n
- Open n8n UI
- Find "Step 1: YouTube Audio Extraction" workflow
- Toggle "Active" switch to ON

### Error: "Connection refused" to yttools
**Solution**: yttools service is not running
```bash
docker ps | grep yttools
# If not running:
cd /home/ghar/code/localai
docker-compose up -d yttools
```

### Error: "Task timeout after 60 attempts"
**Solution**: yttools may be slow or video is very long
- Check yttools logs: `docker logs yttools`
- Try a different/shorter YouTube video
- Increase timeout in workflow (change `max_polls: 60` to higher value)

### Audio file is wrong duration
**Solution**: Check segment parameters
- Default is 40-70s (30 seconds total)
- Override with environment variables:
```bash
SEGMENT_START=10 SEGMENT_END=40 ./test-step1-audio-extraction.sh
```

## What's Next?

Once Step 1 is working:
- ✅ You have a 30-second audio file extracted from YouTube
- ➡️ **Next**: Step 2 - Use vibevoice to clone the voice and TTS your script

## Manual Testing

If you prefer to test manually without the script:

```bash
# 1. Submit request
curl -k -X POST https://n8n.lan/webhook/extract-youtube-audio \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=ao8f3qyMoLM",
    "segment_start": 40,
    "segment_end": 70
  }'

# 2. You should get a response like:
# {
#   "success": true,
#   "task_id": "abc123...",
#   "duration_seconds": 30,
#   ...
# }

# 3. Download the audio file
curl -k "https://yttools.lan/api/download/abc123.../audio" -o audio.mp3

# 4. Play it
mpv audio.mp3
# or
open audio.mp3
```

## Workflow Details

### Nodes (11 total)
1. **Webhook** - Receives POST requests
2. **Validate Input** - Checks YouTube URL and segment parameters
3. **Submit to yttools** - POST to yttools download API
4. **Extract Task ID** - Parse task_id from response
5. **Wait 3s** - Initial delay before polling
6. **Check Status** - GET status from yttools
7. **Check Completion** - Parse status and increment poll counter
8. **Is Complete?** - Branch: complete → download, or loop back to wait
9. **Download Audio** - GET audio file as binary
10. **Prepare Response** - Format JSON response with metadata
11. **Respond Success** - Return to webhook caller

### Polling Loop
- Polls every 3 seconds
- Maximum 60 polls (3 minutes total)
- Loops back to "Wait 3s" if not complete
- Proceeds to download when status=completed

### Input Parameters
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=...",
  "segment_start": 40,    // optional, default 40
  "segment_end": 70       // optional, default 70
}
```

### Output
```json
{
  "success": true,
  "message": "Audio extracted successfully",
  "task_id": "...",
  "file_name": "youtube_audio_....mp3",
  "segment_start": 40,
  "segment_end": 70,
  "duration_seconds": 30,
  "youtube_url": "...",
  "download_time": "2025-11-01T..."
}
```

## Summary

**Step 1 provides**:
- ✅ HTTP webhook endpoint for audio extraction
- ✅ Automatic polling until completion
- ✅ 30-second audio segment extraction
- ✅ JSON response with task metadata

**Ready for Step 2** when:
- ✅ Workflow is active in n8n
- ✅ Test script passes
- ✅ Audio file plays correctly
- ✅ Duration is ~30 seconds

---

**Questions?** See `STEP1-AUDIO-EXTRACTION.md` for detailed documentation.
