# Step 3: Speaker Image Generation - Implementation Plan

## Research Summary

### Original Question
User asked: "Do we really need to use video adaptation?" and pointed to Alibaba Cloud's Wan text-to-image API.

### Findings

#### Option 1: Alibaba Cloud Wan Text-to-Image API
- **Endpoint**: `https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis`
- **Model**: `wan2.5-t2i-preview`
- **Pros**:
  - Purpose-built for image generation
  - Simple async API (similar to Steps 1-2)
  - No local infrastructure needed
  - Well-documented
- **Cons**:
  - Requires Alibaba Cloud account and API key
  - Image URLs expire after 24 hours
  - External dependency/cloud costs
  - Not self-hosted

#### Option 2: Local Self-Hosted Wan 2.2 (CHOSEN APPROACH)
- **Model**: Wan 2.2 T2V 14B (text-to-video with frames=1)
- **Implementation**: ComfyUI + WanVideoWrapper custom node
- **Pros**:
  - ✅ Fully self-hosted (no external dependencies)
  - ✅ Models already downloaded (wan2gp-models volume, 57GB)
  - ✅ Same infrastructure as other steps
  - ✅ No API key/cloud costs
  - ✅ Images stored locally (no 24h expiration)
  - ✅ Open source (Apache 2.0 license)
- **Cons**:
  - Higher setup complexity
  - GPU memory required (14B model)
  - Longer generation time (~2-3 minutes)

### How Wan Text-to-Image Works

**Key Insight**: "Generating high-quality videos is what it is known for. But if you set the video frame to 1, you get an image!" - [Stable Diffusion Art](https://stable-diffusion-art.com/wan-2-2-text-to-image/)

Wan 2.2 is a video generation model trained on diverse video datasets, which gives it rich visual understanding. When configured to generate a single frame, it produces high-quality images.

This is NOT a hack - it's the official approach for Wan image generation.

---

## Implementation Plan

### Architecture

```
n8n Webhook (Step 1-2 output)
  ↓
[Step 3: Image Generation]
  ↓ Submit prompt to ComfyUI
ComfyUI API (http://comfyui:18188/prompt)
  ↓ Queue workflow
Wan 2.2 T2V Model (frames=1)
  ↓ Generate single-frame image
ComfyUI saves to /workspace/ComfyUI/output/
  ↓ Poll for completion
n8n downloads image
  ↓
[Step 4: Video Generation with InfiniteTalk]
```

### Step 3 Workflow Details

**Input** (from Step 2):
- `voice_cloned_audio_url`: URL of the generated TTS audio
- `script`: The 8-second script text
- `youtube_url`: Original YouTube URL (for reference)

**Processing**:
1. Extract speaker description from script or use default
2. Submit ComfyUI workflow with:
   - Model: `wan2.2_text2video_14B_high_quanto_mbf16_int8.safetensors`
   - Frames: `1` (single image)
   - Size: `832x480` (matching video aspect ratio)
   - Prompt: "Professional speaker portrait, [description], high quality, studio lighting"
3. Poll ComfyUI for completion (check `/history` endpoint)
4. Download generated image
5. Return image URL for Step 4

**Output**:
- `speaker_image_url`: URL of generated speaker image
- `speaker_image_path`: Local file path
- All previous data (voice_cloned_audio_url, script, etc.)

---

## ComfyUI Workflow Configuration

### Based on Official Wan T2V Workflow

Key modifications from `text_to_video_wan.json`:
1. **EmptyHunyuanLatentVideo**: Set frames to `1` (was `33`)
2. **UNETLoader**: Use `wan2.2_text2video_14B_high_quanto_mbf16_int8.safetensors`
3. **VAELoader**: Use `Wan2.2_VAE.safetensors`
4. **CLIPLoader**: Use `umt5-xxl` text encoder
5. **SaveImage**: Save as PNG instead of SaveAnimatedWEBP
6. **Size**: Keep at `832x480` for landscape orientation

### Model Files (Already Available)

Located in `/workspace/shared-wan-models/` (symlinked to `/workspace/ComfyUI/models/`):

- ✅ Checkpoint: `wan2.2_text2video_14B_high_quanto_mbf16_int8.safetensors` (14GB)
- ✅ VAE: `Wan2.2_VAE.safetensors` (2.7GB)
- ✅ Text Encoder: `umt5-xxl/models_t5_umt5-xxl-enc-quanto_int8.safetensors`

---

## Current Status

### Completed ✅
1. Docker volume sharing (wan2gp-models → ComfyUI)
2. Model symlinks created in ComfyUI directories
3. ComfyUI-WanVideoWrapper cloned to `/opt/ComfyUI/custom_nodes/`
4. Research confirming local Wan 2.2 approach is valid

### In Progress 🔄
1. Installing WanVideoWrapper dependencies (large CUDA libraries downloading)

### Next Steps 📋
1. Wait for pip install to complete
2. Restart ComfyUI to load Wan custom nodes
3. Verify Wan nodes available via API: `GET http://localhost:18188/object_info`
4. Adapt official workflow JSON for single-frame generation
5. Create n8n nodes for Step 3 (submit → poll → download)
6. Test end-to-end

---

## Testing Plan

### Manual Test
```bash
# 1. Check Wan nodes loaded
curl -s http://localhost:18188/object_info | jq 'keys[]' | grep -i wan

# 2. Submit test workflow (via n8n or direct API)
curl -X POST http://localhost:18188/prompt \
  -H "Content-Type: application/json" \
  -d @step3-workflow.json

# 3. Poll for completion
curl http://localhost:18188/history/{prompt_id}

# 4. Verify image saved
ls -lh /workspace/ComfyUI/output/
```

### Expected Output
- Single PNG image (832x480)
- File size: ~500KB-2MB
- Generation time: 2-3 minutes on GPU
- Quality: High-res portrait suitable for video generation

---

## Alternative Approaches Considered

### ❌ Wan2gp Gradio UI
- Rejected because Gradio API client would need to handle video models
- Complexity similar to ComfyUI but less documentation

### ❌ Alibaba Cloud API
- Rejected because we want fully self-hosted solution
- Would introduce external dependency and costs

### ✅ ComfyUI + Wan2.2 (Selected)
- Best balance of quality, control, and self-hosting
- Existing infrastructure and models
- Strong community support and documentation

---

**Decision**: Proceed with ComfyUI + Wan 2.2 T2V (frames=1) for Step 3 image generation.
