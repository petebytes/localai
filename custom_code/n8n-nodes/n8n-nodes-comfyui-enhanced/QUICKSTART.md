# Quick Start Guide: n8n-nodes-comfyui-enhanced

## Installation

### Step 1: Build the Node

```bash
cd /home/ghar/code/localai/n8n-custom/n8n-nodes-comfyui-enhanced
pnpm install
pnpm run build
```

### Step 2: Copy to n8n Custom Nodes

You have two options:

**Option A: Docker Volume Mount (Recommended)**

Add to your `docker-compose.yml` for n8n:

```yaml
n8n:
  volumes:
    - ./n8n-custom/n8n-nodes-comfyui-enhanced:/home/node/.n8n/custom
```

**Option B: Manual Copy**

```bash
# Find your n8n custom nodes directory
# Usually ~/.n8n/custom or /home/node/.n8n/custom in Docker

# Copy the built node
cp -r dist/* /path/to/n8n/custom/
```

### Step 3: Restart n8n

```bash
docker compose restart n8n
# OR if running locally
n8n stop && n8n start
```

## First Usage

### 1. Configure Credentials

1. Open n8n UI
2. Go to **Credentials** → **New**
3. Search for "ComfyUI API"
4. Configure:
   - **API URL**: `http://comfyui:8188`
   - **API Key**: (leave empty unless you enabled auth)
5. Click **Save**

### 2. Test Connection

Create a simple workflow:

1. Add a **Manual Trigger** node
2. Add **ComfyUI Enhanced** node
3. Select operation: **Get System Stats**
4. Select your credentials
5. Execute!

You should see VRAM usage and system information.

### 3. Try Image Generation

1. In ComfyUI, create a Flux text-to-image workflow
2. **File → Export (API)** - copy the JSON
3. In n8n:
   - Add **ComfyUI Enhanced** node
   - Operation: **Execute Workflow**
   - Paste the JSON
   - Enable **Auto Free VRAM After Completion**
4. Execute!

## Common Workflows

### Image → Video Pipeline

```
[Manual Trigger]
    ↓
[ComfyUI Enhanced] - Execute Workflow (Flux image)
    ↓ Auto Free VRAM: true
[ComfyUI Enhanced] - Free VRAM (explicit, optional)
    ↓
[HTTP Request] - Call Ovi/Wan2GP API
    ↓ (pass image from step 1)
[ComfyUI Enhanced] - Get System Stats (verify VRAM freed)
```

### Batch Image Generation with VRAM Control

```
[Manual Trigger]
    ↓
[Set] - Define array of prompts
    ↓
[Loop] - For each prompt
    ↓
[ComfyUI Enhanced] - Execute Workflow
    ↓ Auto Free VRAM: false (keep loaded)
[Loop End]
    ↓
[ComfyUI Enhanced] - Free VRAM (once at the end)
```

## Troubleshooting

### Node doesn't appear in n8n

Check the build output:
```bash
ls -la dist/
# Should see compiled .js files
```

Check n8n logs:
```bash
docker compose logs n8n | grep -i error
```

### Cannot connect to ComfyUI

Test the connection manually:
```bash
curl http://comfyui:8188/system_stats
```

### Workflow fails to execute

1. Verify the JSON is from **File → Export (API)** (not regular Export)
2. Check ComfyUI logs for errors
3. Increase timeout if generation is slow
4. Check VRAM availability with **Get System Stats** operation

## Next Steps

- Create reusable workflow templates in n8n
- Set up webhooks for automated generation
- Integrate with other services (Discord, Telegram, etc.)
- Experiment with different ComfyUI workflows (ControlNet, LoRA, etc.)

## Support

For issues or questions:
1. Check the [README.md](README.md) for detailed documentation
2. Check ComfyUI logs: `docker compose logs comfyui`
3. Check n8n logs: `docker compose logs n8n`
