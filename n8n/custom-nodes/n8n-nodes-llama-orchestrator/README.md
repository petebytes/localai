# n8n-nodes-llama-orchestrator

n8n community node for interacting with llama.cpp chat service and managing GPU memory via the model orchestrator.

## Features

### Llama.cpp Chat Operations
- **Chat Completion**: Send messages to Qwen3-VL-30B with multimodal support (text + images)
- **Chat with Tools**: Function calling / tool use support
- **Health Check**: Verify llama.cpp service status

### Model Orchestrator Operations
- **Get GPU Status**: Real-time VRAM usage and loaded models
- **Load Model**: Explicitly load models into GPU memory
- **Unload Model**: Free VRAM by unloading models

## Installation

1. Navigate to n8n custom nodes directory:
   ```bash
   cd /path/to/n8n-data/.n8n/custom
   ```

2. Install the package:
   ```bash
   npm install /path/to/n8n-nodes-llama-orchestrator
   ```

3. Restart n8n

## Usage

### Example: Chat with Qwen3-VL

1. Add "Llama Orchestrator" node to workflow
2. Select Service: "Llama.cpp Chat"
3. Select Chat Operation: "Chat Completion"
4. Enter your message
5. (Optional) Add image URL for multimodal input
6. Execute

### Example: GPU Memory Management

1. Add "Llama Orchestrator" node
2. Select Service: "Model Orchestrator"
3. Select Operation: "Get GPU Status"
4. Execute to see VRAM usage

### Example: Workflow Pattern

```
[Manual Trigger]
    ↓
[Orchestrator: Get GPU Status]
    ↓
[IF: VRAM > 18GB available?]
    ↓ Yes
[Llama Chat: Ask question]
    ↓
[Code: Process response]
    ↓
[Orchestrator: Unload Model] (optional)
```

## Credentials

The node supports optional credentials for custom base URLs:

- **Llama.cpp Base URL**: Default `http://llama-cpp:8000`
- **Orchestrator Base URL**: Default `http://model-orchestrator:8000`

These defaults work within the localai Docker network.

## Node Properties

### Llama Chat
- **Model**: Model name (default: `qwen3-vl-30b`)
- **Message**: User message text
- **System Prompt**: System context
- **Temperature**: Sampling temperature (0-2)
- **Max Tokens**: Maximum response length
- **Image URL**: Optional image for multimodal input
- **Tools JSON**: Function definitions for tool calling

### Orchestrator
- **Model Name**: Model to load/unload
- **Service Name**: Service that runs the model
- **Priority**: Load priority (1-10)
- **Force Unload**: Force unload even if in use

## Output Format

### Chat Completion
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "qwen3-vl-30b",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Response text"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 56,
    "completion_tokens": 31,
    "total_tokens": 87
  }
}
```

### GPU Status
```json
{
  "total_mb": 32768,
  "used_mb": 17234,
  "free_mb": 15534,
  "utilization_percent": 45.2,
  "loaded_models": {
    "qwen3-vl-30b": {
      "model": "qwen3-vl-30b",
      "service": "llama-cpp",
      "loaded_at": "2025-01-15T10:30:00",
      "status": "loaded"
    }
  }
}
```

## Development

### Build
```bash
pnpm install
pnpm build
```

### Watch Mode
```bash
pnpm dev
```

### Lint
```bash
pnpm lint
pnpm lintfix
```

## Links

- [llama.cpp Documentation](https://github.com/ggerganov/llama.cpp)
- [Integration Guide](../../docs/LLAMA_CPP_INTEGRATION.md)
- [n8n Community Nodes](https://docs.n8n.io/integrations/community-nodes/)

## License

MIT

## Author

Pete - LocalAI Project
