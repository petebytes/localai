# Model Consolidation Plan: wan2gp ↔ ComfyUI

## Current State

**wan2gp models**: `/workspace/ckpts` (volume: `wan2gp-models`)
- Wan 2.1/2.2 models (57GB total)
- VAE, text encoders, audio models
- Located: `docker volume wan2gp-models`

**ComfyUI models**: `/workspace/ComfyUI/models` (volume: `comfyui-models`)
- Separate volume
- No Wan models currently

## Problem
- Wan models duplicated if we download them for ComfyUI
- 57GB+ waste of disk space
- Slower downloads/startup

## Solution: Share wan2gp models with ComfyUI

### Option 1: Mount wan2gp models into ComfyUI (RECOMMENDED)

**Changes to docker-compose.yml**:
```yaml
comfyui:
  volumes:
    - ./ComfyUI:/workspace/ComfyUI
    - comfyui-models:/workspace/ComfyUI/models
    - hf-cache:/data/.huggingface
    - torch-cache:/data/.torch
    # ADD THESE:
    - wan2gp-models:/workspace/ComfyUI/models/diffusion_models:ro  # Wan models
    - wan2gp-models:/workspace/ComfyUI/models/vae:ro               # VAE models
```

**Benefits**:
- ✅ No model duplication
- ✅ ComfyUI can access all Wan models
- ✅ Read-only mount (safe - wan2gp won't be affected)
- ✅ Minimal changes

**Drawbacks**:
- Models in `/workspace/ckpts/` but ComfyUI expects them in subdirectories
- May need symlinks or custom node paths

### Option 2: Create shared model volume

**Changes**:
1. Create new shared volume: `wan-shared-models`
2. Mount in both containers:
   - wan2gp: `/workspace/ckpts` → `wan-shared-models`
   - ComfyUI: `/workspace/ComfyUI/models/diffusion_models` → `wan-shared-models`

**Benefits**:
- ✅ Clean separation
- ✅ Both can read/write

**Drawbacks**:
- Requires migrating existing wan2gp models
- More complex setup

### Option 3: Symlinks within containers

**Implementation**:
```bash
# In ComfyUI container
ln -s /workspace/wan-models /workspace/ComfyUI/models/diffusion_models/wan
```

Mount wan2gp models at `/workspace/wan-models` in ComfyUI

**Benefits**:
- ✅ Flexible
- ✅ No volume changes

**Drawbacks**:
- Requires container modification
- Symlinks may not persist across restarts

## Recommended Approach: Option 1 with Subdirectory Mapping

### Implementation Steps:

1. **Check current wan2gp model structure**:
```bash
docker exec wan2gp ls -la /workspace/ckpts/
```

2. **Map specific models to ComfyUI paths**:
```yaml
comfyui:
  volumes:
    # Existing volumes
    - ./ComfyUI:/workspace/ComfyUI
    - comfyui-models:/workspace/ComfyUI/models
    # Shared Wan models
    - wan2gp-models:/workspace/shared-wan-models:ro
```

3. **Create custom ComfyUI node or use model path override**:
- ComfyUI allows custom model paths via `extra_model_paths.yaml`
- Configure it to look in `/workspace/shared-wan-models/`

4. **Restart ComfyUI**:
```bash
docker-compose restart comfyui
```

## Testing

After consolidation:
```bash
# Verify ComfyUI can see Wan models
curl http://localhost:18188/object_info | jq '.UNETLoader.input.required.unet_name[0]'

# Should include wan2.1_text2video_14B_quanto_mbf16_int8.safetensors
```

## File: extra_model_paths.yaml

Create `/home/ghar/code/localai/ComfyUI/extra_model_paths.yaml`:
```yaml
wan_models:
  base_path: /workspace/shared-wan-models/
  diffusion_models: ""
  vae: ""
  clip: umt5-xxl/
```

---

## Next Steps (After Consolidation)

1. ✅ Update docker-compose.yml
2. ✅ Create extra_model_paths.yaml
3. ✅ Restart ComfyUI
4. ✅ Verify model access
5. ✅ Create single-frame Wan workflow
6. ✅ Integrate with n8n Step 3
