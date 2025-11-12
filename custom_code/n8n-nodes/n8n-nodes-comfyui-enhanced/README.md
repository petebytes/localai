![Banner image](https://user-images.githubusercontent.com/10284570/173569848-c624317f-42b1-45a6-ab09-f0ea3c247648.png)

# n8n-nodes-comfyui-enhanced

Enhanced n8n node for [ComfyUI](https://github.com/comfyanonymous/ComfyUI) with VRAM management and advanced operations.

This package extends the original n8n-nodes-comfyui with powerful new features designed for workflow automation and resource management.

## Features

### Core Features
- ✅ Execute ComfyUI workflows directly from n8n
- ✅ Support for workflow JSON import (API Export format)
- ✅ Automatic image retrieval from workflow outputs
- ✅ Progress monitoring and error handling
- ✅ Support for API key authentication
- ✅ Configurable timeout settings

### Enhanced Features (New!)
- 🆕 **VRAM Management**: Free GPU memory on demand or automatically after workflow completion
- 🆕 **System Monitoring**: Get VRAM usage and system stats
- 🆕 **Queue Management**: Check current queue status
- 🆕 **Execution Control**: Interrupt running workflows
- 🆕 **Multi-Operation Support**: Choose from 5 different operations in a single node
- 🆕 **Workflow Chaining**: Designed for image → video pipelines with explicit VRAM control

## Prerequisites

- n8n (version 1.0.0 or later)
- ComfyUI instance running and accessible
- Node.js 18.10 or newer
- pnpm 9.1 or newer (for development)

## Installation

### For Local Development (Recommended for this project)

```bash
cd n8n-custom/n8n-nodes-comfyui-enhanced
pnpm install
pnpm run build
```

### For n8n Instance

Copy the `dist` folder to your n8n custom nodes directory, or install via n8n's Community Nodes feature.

## Node Configuration

### Credentials Setup

1. In n8n, go to **Credentials** → **New**
2. Search for "ComfyUI API"
3. Configure:
   - **API URL**: `http://comfyui:8188` (or your ComfyUI instance URL)
   - **API Key**: Leave empty unless you've enabled authentication in ComfyUI

### Operations

The node supports 5 different operations:

#### 1. Execute Workflow

Execute a ComfyUI workflow and retrieve generated images.

**Parameters:**
- **Workflow JSON**: The ComfyUI workflow in JSON format (use "File → Export (API)" in ComfyUI)
- **Output Format**: JPEG or PNG
- **JPEG Quality**: 1-100 (only for JPEG)
- **Timeout**: Maximum time in minutes to wait for completion (default: 30)
- **Auto Free VRAM After Completion**: Automatically free GPU memory when done (default: false)

**Outputs:**
- Array of generated images with:
  - `filename`: Name of the generated image file
  - `subfolder`: Subfolder path if any
  - `data`: Base64 encoded image data
  - Binary data for direct use in n8n

#### 2. Get System Stats

Get VRAM usage and system information from ComfyUI.

**Parameters:** None

**Outputs:**
- System statistics including:
  - VRAM usage
  - System memory
  - Device information

#### 3. Free VRAM

Manually free GPU memory by clearing the model cache.

**Parameters:** None

**Outputs:**
- Success status and confirmation message

#### 4. Get Queue

Get the current queue status from ComfyUI.

**Parameters:** None

**Outputs:**
- Queue information including pending and running tasks

#### 5. Interrupt

Interrupt the currently running execution.

**Parameters:** None

**Outputs:**
- Success status and confirmation message

## Usage Examples

### Example 1: Basic Image Generation

1. In ComfyUI, create your workflow (e.g., Flux text-to-image)
2. Export via **File → Export (API)** to get the JSON
3. In n8n:
   - Add **ComfyUI Enhanced** node
   - Select operation: **Execute Workflow**
   - Paste the workflow JSON
   - Configure API URL credentials
   - Run!

### Example 2: Image → Video Pipeline with VRAM Management

This is the primary use case for the enhanced features:

```
1. [ComfyUI Enhanced] Execute Workflow (Flux image generation)
   - Operation: Execute Workflow
   - Auto Free VRAM: true ✓

2. [ComfyUI Enhanced] Free VRAM (explicit)
   - Operation: Free VRAM

3. [HTTP Request] Call Wan2GP/Ovi Video API
   - Use image from step 1
   - Generate video

4. [ComfyUI Enhanced] Check Stats
   - Operation: Get System Stats
   - Verify VRAM is freed
```

### Example 3: Monitor VRAM Before Generation

```
1. [ComfyUI Enhanced] Get System Stats
   - Check available VRAM

2. [IF] Check if VRAM > 10GB

3a. [ComfyUI Enhanced] Execute Workflow
    - If yes: proceed with generation

3b. [ComfyUI Enhanced] Free VRAM
    - If no: free VRAM first, then generate
```

### Example 4: Queue Multiple Generations

```
1. [Loop] Over multiple prompts

2. [ComfyUI Enhanced] Execute Workflow
   - Generate image for each prompt
   - Auto Free VRAM: false (keep loaded)

3. [ComfyUI Enhanced] Free VRAM (after loop)
   - Free once at the end
```

## ComfyUI API Endpoints Used

This node uses the following ComfyUI API endpoints:

- `GET /system_stats` - Get system statistics and VRAM usage
- `POST /prompt` - Queue a workflow for execution
- `GET /history/{prompt_id}` - Check execution status
- `GET /view` - Download generated images
- `POST /free` - Free GPU memory
- `GET /queue` - Get queue status
- `POST /interrupt` - Interrupt execution

## Error Handling

The node includes comprehensive error handling for:
- API connection issues
- Invalid workflow JSON
- Execution failures
- Timeout conditions (configurable, default 30 minutes)
- VRAM management errors (logged as warnings)

## Best Practices

### VRAM Management Strategy

1. **For Single Operations**: Enable "Auto Free VRAM" after workflow completion
2. **For Pipelines**: Use explicit "Free VRAM" operation between stages (e.g., after image generation, before video generation)
3. **For Batch Processing**: Keep models loaded during the loop, free once at the end
4. **For Monitoring**: Use "Get System Stats" to check VRAM before heavy operations

### Workflow Export

Always use **File → Export (API)** in ComfyUI, not **Export**. The API format is required for proper execution.

### Timeouts

- Image generation: 5-10 minutes usually sufficient
- Video generation: 20-30 minutes recommended
- Complex workflows: Adjust based on your hardware

## Development

```bash
# Install dependencies
pnpm install

# Build (compile TypeScript)
pnpm run build

# Development mode (watch for changes)
pnpm run dev

# Lint
pnpm run lint

# Fix linting issues
pnpm run lintfix

# Format code
pnpm run format
```

### Project Structure

```
n8n-nodes-comfyui-enhanced/
├── nodes/
│   └── ComfyUI/
│       ├── Comfyui.node.ts    # Main node implementation
│       └── comfyui.svg         # Node icon
├── credentials/
│   └── ComfyUIApi.credentials.ts  # Credentials definition
├── dist/                       # Compiled output (generated)
├── package.json
├── tsconfig.json
└── README.md
```

## Troubleshooting

### Node doesn't appear in n8n

1. Check that the build was successful: `pnpm run build`
2. Verify `dist` folder exists and contains compiled JS files
3. Restart n8n after building
4. Check n8n logs for errors

### "Failed to get prompt ID"

- Verify ComfyUI is running and accessible
- Check the API URL in credentials (should be `http://comfyui:8188` for Docker setup)
- Ensure workflow JSON is in API export format

### "Execution timeout"

- Increase the timeout value in the node settings
- Check ComfyUI logs for errors
- Verify GPU is working properly

### VRAM not freeing

- The `/free` endpoint may not be available in older ComfyUI versions
- Update ComfyUI to the latest version
- Check ComfyUI console for error messages

## Credits

Based on [n8n-nodes-comfyui](https://github.com/mason276752/n8n-nodes-comfyui) by mason276752.

Enhanced with VRAM management and additional operations for workflow automation.

## License

[MIT](LICENSE.md)
 