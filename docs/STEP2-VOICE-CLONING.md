# Step 2: Voice Cloning and TTS

## Overview
Clone a voice from reference audio and generate Text-to-Speech of your 8-second script using the vibevoice API.

## Prerequisites
- ✅ Step 1 completed (or have reference audio file)
- ✅ vibevoice API running at http://vibevoice-api:8100

## Files
- **n8n Workflow**: `n8n/workflows/step2-voice-cloning-tts.json`
- **Test Script**: `test-step2-voice-clone.sh`

## Workflow Details

### Input (POST webhook)

**Option A: Using Step 1 task_id**
```json
{
  "script": "Your 8-second script here",
  "reference_task_id": "abc123..."
}
```

**Option B: Upload audio file**
```bash
curl -X POST https://n8n.lan/webhook/voice-clone-tts \
  -F "script=Your script here" \
  -F "reference_audio=@/path/to/audio.mp3"
```

**Option C: Provide audio URL**
```json
{
  "script": "Your script here",
  "reference_url": "https://example.com/audio.mp3"
}
```

### Webhook Endpoint
```
POST https://n8n.lan/webhook/voice-clone-tts
```

### Processing Flow
1. **Validate Input** - Check script and reference audio source
2. **Has Task ID?** - Branch based on audio source
3. **Download Reference Audio** - If task_id provided, get from yttools
4. **Prepare TTS Request** - Format vibevoice API request
5. **Call Vibevoice TTS** - POST to vibevoice with multipart form data
6. **Prepare Response** - Format final response with cloned audio
7. **Respond Success** - Return JSON with TTS audio file

### Output
```json
{
  "success": true,
  "message": "Voice cloned and TTS generated successfully",
  "file_name": "cloned_voice_2025-11-01T12-34-56.mp3",
  "script": "Your script here",
  "model": "F5-TTS",
  "output_format": "mp3",
  "generation_time": "2025-11-01T12:34:56.789Z"
}
```

## Setup Instructions

### 1. Import Workflow to n8n

```bash
# Via helper script
./import-step1-workflow.sh

# Or manually via n8n UI:
# 1. Open https://n8n.lan
# 2. Workflows → Import from File
# 3. Select: n8n/workflows/step2-voice-cloning-tts.json
# 4. Activate workflow
```

### 2. Verify vibevoice Service

```bash
curl http://vibevoice-api:8100/api/health
# or
curl https://vibevoice.lan/api/health
```

Expected response:
```json
{"status": "healthy"}
```

### 3. Run Test

**Using Step 1 output**:
```bash
# After running Step 1, use the task_id:
STEP1_TASK_ID="abc123..." ./test-step2-voice-clone.sh
```

**Using local audio file**:
```bash
REF_AUDIO="/tmp/test-audio/extracted_audio.mp3" ./test-step2-voice-clone.sh
```

**Custom script**:
```bash
SCRIPT_TEXT="This is my custom 8-second video script" ./test-step2-voice-clone.sh
```

## Integration with Step 1

To chain Step 1 → Step 2 automatically, you can:

### Option 1: Manual Chaining
```bash
# Run Step 1
./test-step1-audio-extraction.sh > step1_output.json
TASK_ID=$(jq -r '.task_id' step1_output.json)

# Run Step 2 with Step 1's task_id
STEP1_TASK_ID="$TASK_ID" SCRIPT_TEXT="Your script" ./test-step2-voice-clone.sh
```

### Option 2: Combined n8n Workflow (Future)
Create a combined workflow that:
1. Extracts audio from YouTube (Step 1)
2. Passes task_id to voice cloning (Step 2)
3. Continues to image generation (Step 3)
4. Finishes with video generation (Step 4)

## Vibevoice API Details

### Endpoint
```
POST http://vibevoice-api:8100/api/tts
```

### Request (multipart/form-data)
```
text: "Your script text"
reference_audio: <binary audio file>
output_format: "mp3" (optional, default: wav)
model: "F5-TTS" (optional, default: F5-TTS)
```

### Response
Binary audio file (MP3 or WAV)

### Models Available
- `F5-TTS` - Default, best quality (recommended)
- `E2-TTS` - Faster, good quality

### Supported Formats
- Input: MP3, WAV, M4A, FLAC, OGG
- Output: MP3, WAV, OGG

### Voice Cloning Tips
- **Reference audio length**: 10-60 seconds ideal
  - Too short (<10s): Poor voice quality
  - Too long (>60s): Slower processing, no quality gain
- **Audio quality**: Clear voice, minimal background noise
- **Language**: Works best with same language as script
- **Speaking style**: Reference and script should match style

## Troubleshooting

### Error: "Missing reference audio"
- Provide either `reference_task_id`, `reference_url`, or upload audio file
- If using task_id, ensure Step 1 completed successfully

### Error: "No reference audio available"
- Reference audio binary data is missing
- Check that yttools task_id is valid
- Verify audio file uploaded correctly

### Error: vibevoice timeout
- TTS generation can take 30-60 seconds
- Workflow timeout is set to 120 seconds
- For longer scripts, may need to increase timeout

### TTS audio quality is poor
- Check reference audio quality (should be clear)
- Try longer reference audio (20-30 seconds ideal)
- Ensure reference audio has minimal background noise
- Use same language for reference and script

### Voice doesn't match reference
- Reference audio may be too short (<10s)
- Background music/noise interfering with voice
- Try extracting different segment from source video

## Performance Notes

- **Processing time**: 20-60 seconds depending on script length
- **Reference audio**: 10-30s recommended for best results
- **Script length**: Up to 500 characters (adjust as needed)
- **Output size**: ~100-200KB for 8-second audio

## Next Steps

Once Step 2 is working:
1. ✅ Verify cloned voice sounds like reference
2. ✅ Confirm TTS audio is clear and understandable
3. ✅ Audio file is returned successfully

**Proceed to**: Step 3 - Image Generation (Wan 2.1)

---

## Notes

- vibevoice uses F5-TTS model by default (best quality)
- Supports voice cloning from any clear audio
- Can generate multi-speaker conversations (future enhancement)
- Streaming TTS available via `/api/tts/stream` endpoint (future enhancement)
