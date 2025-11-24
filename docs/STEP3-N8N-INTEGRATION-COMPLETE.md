# Step 3: n8n Integration - COMPLETE

## Overview

Successfully integrated Step 3 (Portrait Generation) into the n8n workflow, creating a complete Steps 1-2-3 pipeline that:

1. **Step 1**: Extracts audio from YouTube video
2. **Step 2**: Clones voice and generates TTS audio
3. **Step 3**: Generates portrait image using ComfyUI + Wan 2.2

## Workflow File

**Location**: `n8n/workflows/step1-2-3-audio-voice-portrait.json`

**Webhook Endpoint**: `POST /webhook/generate-video-step1-2-3`

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     n8n Workflow (Steps 1-2-3)                  │
│             Webhook: /webhook/generate-video-step1-2-3          │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: YouTube Audio Extraction (yttools)                      │
│ - Submit download request                                       │
│ - Poll for completion (3s intervals, max 60 polls)              │
│ - Download reference audio                                      │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: Voice Cloning + TTS (vibevoice-api)                     │
│ - Submit TTS request with reference audio                       │
│ - Generate cloned voice audio                                   │
│ - Store audio in binary data                                    │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: Portrait Generation (ComfyUI)                           │
│ - Load workflow template from /data/shared/comfyui/             │
│ - Generate portrait prompt from script                          │
│ - Submit to ComfyUI API                                         │
│ - Poll for completion (5s intervals, max 60 polls)              │
│ - Download generated portrait image                             │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                    Returns: JSON + Audio + Image
```

## Workflow Nodes

### Input & Validation
1. **Webhook Step 1-2-3** - Receives POST requests
2. **Validate Input** - Validates YouTube URL, script, and parameters

### Step 1: Audio Extraction
3. **Submit to yttools** - POST to yttools API
4. **Extract Task ID** - Extract task_id and prepare for polling
5. **Wait 3s (Step 1)** - Wait before status check
6. **Check Status (Step 1)** - GET status from yttools
7. **Check Completion (Step 1)** - Evaluate completion status
8. **Is Complete? (Step 1)** - Branch: complete → download, not complete → loop
9. **Download Reference Audio** - Download audio file as binary

### Step 2: Voice Cloning
10. **Prepare for Voice Cloning** - Prepare audio binary for TTS
11. **Voice Clone & TTS** - POST multipart form to vibevoice-api
12. **Prepare for Portrait Gen** - Convert base64 audio to binary, generate portrait prompt

### Step 3: Portrait Generation
13. **Load ComfyUI Template** - Read workflow template using Read/Write Files node
14. **Prepare ComfyUI Workflow** - Load workflow template, update prompt & seed
15. **Submit to ComfyUI** - POST workflow to ComfyUI /prompt endpoint
16. **Extract Prompt ID** - Extract prompt_id for polling
17. **Wait 5s (Step 3)** - Wait before status check
18. **Check ComfyUI Status** - GET /history/{prompt_id}
19. **Check Completion (Step 3)** - Evaluate completion, extract image info
20. **Is Complete? (Step 3)** - Branch: complete → download, not complete → loop
21. **Download Portrait Image** - GET /view with filename/subfolder/type

### Response
22. **Prepare Final Response** - Format JSON response with metadata + binary data
23. **Respond Success** - Return JSON + audio + image to caller

## Key Implementation Details

### ComfyUI Workflow Loading

The workflow template is stored at `/data/shared/comfyui/wan-portrait-api-format.json` (inside n8n container).

**Node 13: Load ComfyUI Template** (Read/Write Files from Disk)
```javascript
{
  "fileSelector": "/data/shared/comfyui/wan-portrait-api-format.json",
  "options": {}
}
```

**Node 14: Prepare ComfyUI Workflow** (Code)
```javascript
// Get the loaded workflow template from previous node
const item = $input.first();
const binaryKey = Object.keys(item.binary)[0];
const binaryData = item.binary[binaryKey];

// Convert binary buffer to string, then parse JSON
let workflowTemplate;
try {
  let jsonString;
  if (binaryData.data) {
    // It's base64 encoded
    jsonString = Buffer.from(binaryData.data, 'base64').toString('utf8');
  } else {
    // It might already be a Buffer
    jsonString = binaryData.toString('utf8');
  }
  workflowTemplate = JSON.parse(jsonString);
} catch (error) {
  throw new Error(`Failed to parse ComfyUI workflow template: ${error.message}`);
}

// Update positive prompt (node 6)
workflow['6'].inputs.text = portraitPrompt;

// Randomize seed (node 3)
workflow['3'].inputs.seed = Math.floor(Math.random() * 2147483647);
```

### Portrait Prompt Generation

If no custom `portrait_prompt` is provided, it's automatically generated from the script:

```javascript
const finalPortraitPrompt = portraitPrompt ||
  `Professional portrait photograph of a speaker presenting the following content: "${script.substring(0, 100)}". Studio lighting, high resolution, centered composition, neutral background, photorealistic, detailed facial features, professional attire, confident expression, business setting`;
```

### ComfyUI Polling Logic

```javascript
// Check if outputs exist (node 49 = SaveImage node)
if (promptHistory.outputs && promptHistory.outputs['49']) {
  const imageInfo = promptHistory.outputs['49'].images[0];
  return {
    status: 'completed',
    ready_to_download: true,
    image_filename: imageInfo.filename,
    image_subfolder: imageInfo.subfolder,
    image_type: imageInfo.type
  };
}
```

### Image Download

```
GET http://comfyui:18188/view?filename={filename}&subfolder={subfolder}&type={type}
```

## API Usage

### Request

```bash
curl -X POST https://n8n.lan/webhook/generate-video-step1-2-3 \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=ao8f3qyMoLM",
    "script": "Welcome to our presentation on AI.",
    "segment_start": 40,
    "segment_end": 70,
    "portrait_prompt": "Professional portrait of a speaker"
  }'
```

### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `youtube_url` | string | ✅ Yes | - | YouTube video URL |
| `script` | string | ✅ Yes | - | 8-second script for TTS (max 500 chars) |
| `segment_start` | number | No | 40 | Start time in seconds |
| `segment_end` | number | No | 70 | End time in seconds (max 60s duration) |
| `portrait_prompt` | string | No | Auto-generated | Custom portrait prompt |
| `cfg_scale` | number | No | 1.5 | TTS CFG scale |
| `diffusion_steps` | number | No | 30 | TTS diffusion steps |
| `temperature` | number | No | 0.75 | TTS temperature |
| `top_p` | number | No | 0.85 | TTS top-p sampling |
| `use_sampling` | boolean | No | true | TTS use sampling |

### Response

```json
[
  {
    "json": {
      "success": true,
      "message": "Steps 1-2-3 completed: Audio extracted, voice cloned, and portrait generated",
      "step1": {
        "task_id": "abc123",
        "youtube_url": "https://www.youtube.com/watch?v=...",
        "segment_start": 40,
        "segment_end": 70
      },
      "step2": {
        "script": "Welcome to our presentation...",
        "audio_file_name": "cloned_voice_2025-11-02T15-30-00.mp3",
        "model": "VibeVoice-Large",
        "duration_seconds": 8.5
      },
      "step3": {
        "prompt_id": "def456",
        "portrait_prompt": "Professional portrait photograph...",
        "seed": 1234567890,
        "image_file_name": "portrait_1234567890_2025-11-02T15-32-00.png",
        "comfyui_filename": "wan-portraits/portrait_00001_.png",
        "comfyui_subfolder": ""
      },
      "completion_time": "2025-11-02T15:32:15.000Z",
      "ready_for_step4": true
    },
    "binary": {
      "audio": {
        "data": "base64_encoded_mp3_data...",
        "fileName": "cloned_voice_2025-11-02T15-30-00.mp3",
        "mimeType": "audio/mpeg"
      },
      "image": {
        "data": "base64_encoded_png_data...",
        "fileName": "portrait_1234567890_2025-11-02T15-32-00.png",
        "mimeType": "image/png"
      }
    }
  }
]
```

## Processing Times

| Step | Service | Typical Time | Max Polling |
|------|---------|--------------|-------------|
| Step 1 | yttools | 30-60 seconds | 3 minutes (60 polls × 3s) |
| Step 2 | vibevoice-api | 60-120 seconds | 3 minutes (timeout in HTTP request) |
| Step 3 | ComfyUI | 50-90 seconds | 5 minutes (60 polls × 5s) |
| **Total** | **End-to-End** | **2.5-4.5 minutes** | **~11 minutes max** |

## File Locations

### Host System
- **Workflow**: `/home/ghar/code/localai/n8n/workflows/step1-2-3-audio-voice-portrait.json`
- **ComfyUI Template**: `/home/ghar/code/localai/shared/comfyui/wan-portrait-api-format.json`
- **Test Script**: `/home/ghar/code/localai/test-step1-2-3-pipeline.sh`

### Inside n8n Container
- **ComfyUI Template**: `/data/shared/comfyui/wan-portrait-api-format.json`
- **Shared Storage**: `/data/shared/`

### Inside ComfyUI Container
- **Output Images**: `/opt/ComfyUI/output/wan-portraits/`
- **Models**: `/opt/storage/stable_diffusion/models/`

## Testing

### Test Script

```bash
bash test-step1-2-3-pipeline.sh
```

**Optional parameters**:
```bash
bash test-step1-2-3-pipeline.sh \
  "https://www.youtube.com/watch?v=VIDEO_ID" \
  "Your custom script text here" \
  40 \  # segment_start
  70    # segment_end
```

### Expected Output

```
==================================================
Steps 1-2-3 Pipeline Test
==================================================

Testing complete pipeline:
  Step 1: YouTube Audio Extraction
  Step 2: Voice Cloning + TTS
  Step 3: Portrait Image Generation

Parameters:
  YouTube URL: https://www.youtube.com/watch?v=ao8f3qyMoLM
  Script: Welcome to our presentation...
  Segment: 40s - 70s

n8n Webhook: https://n8n.lan/webhook/generate-video-step1-2-3

[1/3] Submitting request to n8n workflow...
✅ Workflow completed successfully!

Total execution time: 3m 25s

[2/3] Parsing response...
Message: Steps 1-2-3 completed: Audio extracted, voice cloned, and portrait generated

Step 1 (YouTube Audio Extraction):
  Task ID: abc123
  Source: https://www.youtube.com/watch?v=ao8f3qyMoLM

Step 2 (Voice Cloning + TTS):
  Script: Welcome to our presentation...
  Audio file: cloned_voice_2025-11-02T15-30-00.mp3
  Model: VibeVoice-Large
  Duration: 8.5s

Step 3 (Portrait Generation):
  Prompt ID: def456
  Image file: portrait_1234567890_2025-11-02T15-32-00.png
  Seed: 1234567890
  Prompt: Professional portrait photograph...

[3/3] Extracting binary data...
✅ Audio data found
   Saved to: ./test-outputs/step123/cloned_voice_2025-11-02T15-30-00.mp3
   Size: 256KiB
   Duration: 8.5s

✅ Portrait image found
   Saved to: ./test-outputs/step123/portrait_1234567890_2025-11-02T15-32-00.png
   Size: 339KiB
   Dimensions: 1024x576

==================================================
✅ Steps 1-2-3 Pipeline Test Complete!
==================================================

Summary:
  Total time: 3m 25s
  Step 1 task: abc123
  Step 3 prompt: def456

Output files:
  Audio: ./test-outputs/step123/cloned_voice_2025-11-02T15-30-00.mp3
  Image: ./test-outputs/step123/portrait_1234567890_2025-11-02T15-32-00.png

Ready for Step 4 (Video Generation)!
```

## Import Instructions

### 1. Import Workflow into n8n

Via n8n UI:
1. Open n8n: https://n8n.lan
2. Click **Workflows** → **Import from File**
3. Select: `n8n/workflows/step1-2-3-audio-voice-portrait.json`
4. Click **Import**
5. Click **Save** to activate webhook

### 2. Verify ComfyUI Workflow Template

The template should already be in place at:
```bash
/home/ghar/code/localai/shared/comfyui/wan-portrait-api-format.json
```

This is accessible inside n8n container at:
```
/data/shared/comfyui/wan-portrait-api-format.json
```

### 3. Test the Workflow

```bash
bash test-step1-2-3-pipeline.sh
```

## Troubleshooting

### Error: "Failed to load ComfyUI workflow"

**Cause**: ComfyUI workflow template not found

**Solution**:
```bash
# Verify file exists
ls -l /home/ghar/code/localai/shared/comfyui/wan-portrait-api-format.json

# If missing, copy from source
mkdir -p /home/ghar/code/localai/shared/comfyui
cp /home/ghar/code/localai/n8n/comfyui/wan-portrait-api-format.json \
   /home/ghar/code/localai/shared/comfyui/
```

### Error: "ComfyUI did not return prompt_id"

**Cause**: ComfyUI workflow submission failed

**Solution**:
- Check ComfyUI is running: `curl http://localhost:18188/`
- Verify workflow JSON is valid
- Check ComfyUI logs: `docker logs comfyui`

### Error: "ComfyUI timeout after 60 attempts"

**Cause**: Image generation taking > 5 minutes

**Solution**:
- Check ComfyUI UI for errors: http://localhost:18188
- Verify GPU is available
- Check ComfyUI logs for CUDA/memory errors
- Increase `max_polls_step3` in workflow if needed

### Warning: "No image binary data found"

**Cause**: Image download failed

**Solution**:
- Verify image was generated in ComfyUI
- Check image path: `image_filename`, `image_subfolder`, `image_type`
- Test direct download: `curl "http://comfyui:18188/view?filename=...&subfolder=...&type=..."`

## Next Steps

This workflow is **ready for Step 4 integration**:

1. **Step 4**: InfiniteTalk API wrapper
   - Create FastAPI wrapper for InfiniteTalk
   - Accept audio + image inputs
   - Generate 8-second talking head video

2. **Final Workflow**: Steps 1-2-3-4
   - Extend current workflow
   - Add InfiniteTalk nodes
   - Output final video

## Status

✅ **COMPLETE** - Step 3 n8n integration working

- ✅ Workflow created and tested
- ✅ ComfyUI template accessible
- ✅ Test script created
- ✅ Documentation complete
- ✅ Ready for Step 4

**Last Updated**: 2025-11-02
**Status**: Production Ready (pending user testing)
