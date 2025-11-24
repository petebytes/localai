# Steps 1-2 Combined: Audio Extraction + Voice Cloning

## Overview
Single workflow that extracts audio from YouTube and clones the voice for TTS - all in one request.

## What Changed
✅ **Before**: Step 1 and Step 2 were separate webhooks
✅ **Now**: Single workflow that runs Steps 1 → 2 automatically

## Files
- **Workflow**: `n8n/workflows/step1-2-audio-extraction-voice-clone.json`
- **Test Script**: `test-step1-2-combined.sh`

## Input (Single Request)
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=ao8f3qyMoLM",
  "script": "Your 8-second script here",
  "segment_start": 40,
  "segment_end": 70
}
```

## Webhook Endpoint
```
POST https://n8n.lan/webhook/generate-video-step1-2
```

## Flow
1. **Validate Input** - Check YouTube URL and script
2. **Submit to yttools** - Request audio extraction
3. **Poll yttools** - Wait for completion (3s intervals, 3min max)
4. **Download Reference Audio** - Get extracted audio file
5. **Prepare for Voice Cloning** - Format data for vibevoice
6. **Voice Clone & TTS** - Generate TTS with cloned voice
7. **Respond** - Return JSON with both step results

## Output
```json
{
  "success": true,
  "message": "Steps 1-2 completed: Audio extracted and voice cloned",
  "step1": {
    "task_id": "abc123...",
    "youtube_url": "https://...",
    "segment_start": 40,
    "segment_end": 70
  },
  "step2": {
    "script": "Your script...",
    "tts_file_name": "cloned_voice_2025-11-01T12-34-56.mp3",
    "model": "F5-TTS",
    "output_format": "mp3"
  },
  "completion_time": "2025-11-01T12:34:56.789Z"
}
```

## Import & Test

### 1. Import Workflow
```bash
# Via n8n UI:
# 1. Open https://n8n.lan
# 2. Workflows → Import from File
# 3. Select: n8n/workflows/step1-2-audio-extraction-voice-clone.json
# 4. Activate workflow
```

### 2. Test It
```bash
./test-step1-2-combined.sh
```

### 3. Custom Test
```bash
YOUTUBE_URL="https://www.youtube.com/watch?v=YOUR_VIDEO" \
SCRIPT_TEXT="Your custom 8-second script" \
./test-step1-2-combined.sh
```

## Expected Timeline
- **Step 1**: 30-120 seconds (YouTube download + extraction)
- **Step 2**: 20-60 seconds (voice cloning + TTS)
- **Total**: 1-3 minutes

## Services Used
- ✅ yttools (http://yttools:8456) - Audio extraction
- ✅ vibevoice (http://vibevoice-api:8100) - Voice cloning

## Next: Steps 3-4

Once Steps 1-2 work, we need to add:
- **Step 3**: Image generation (Wan 2.1 T2I) - **Needs API**
- **Step 4**: Video generation (InfiniteTalk) - **Needs API**

Both services currently only have Gradio UIs, no REST APIs.

## Advantages of Combined Workflow
1. **Single request** - User provides YouTube URL + script once
2. **Automatic flow** - No manual task_id passing
3. **Atomic operation** - Either both steps succeed or fail together
4. **Progress tracking** - Single execution to monitor in n8n
5. **Easier testing** - One script tests both steps

## Troubleshooting

### Error: "Missing required parameter: script"
- New combined workflow requires `script` in initial request
- Old Step 1 workflow doesn't need script

### TTS takes too long
- Normal! Voice cloning is compute-intensive
- Timeout set to 120 seconds (2 minutes)
- Check vibevoice logs if it times out

### Audio quality issues
- Check reference audio from yttools (should be clear)
- Try different YouTube segment (different speakers/sections)
- Ensure segment has minimal background music/noise

---

**Status**: ✅ Ready for Testing
**Next**: Import workflow and test Steps 1-2 combined
