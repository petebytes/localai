# Shared Cache Optimization

## Overview

The llama.cpp service uses the shared HuggingFace cache (`hf-cache` Docker volume) to store models. This prevents re-downloading models that may already exist for other services.

## How It Works

### Shared Volume Architecture

```
┌─────────────────────────────────────────────┐
│         hf-cache (Docker Volume)            │
├─────────────────────────────────────────────┤
│  /data/.huggingface/hub/                    │
│    ├── models--Qwen--Qwen3-VL-30B-...       │
│    ├── models--openai--whisper-large-v3     │
│    ├── models--stabilityai--...             │
│    └── ... (all HuggingFace models)         │
└─────────────────────────────────────────────┘
         ▲           ▲           ▲
         │           │           │
    ┌────┴───┐  ┌───┴────┐  ┌───┴────┐
    │ llama  │  │whisperx│  │  ovi   │
    │  .cpp  │  │        │  │  api   │
    └────────┘  └────────┘  └────────┘
```

All services mount the same `hf-cache` volume at `/data/.huggingface`, so models downloaded by any service are available to all others.

## Benefits

1. **No Re-downloading**: If Qwen3-VL-30B is already downloaded for another service, llama.cpp uses the existing copy
2. **Disk Space Savings**: One copy of each model instead of duplicates per service
3. **Faster Setup**: Skip downloads when models already exist
4. **Consistent Versioning**: All services use the same model version

## File Structure

Models are stored using HuggingFace's cache structure:

```
/data/.huggingface/
└── hub/
    └── models--Qwen--Qwen3-VL-30B-A3B-Instruct-GGUF/
        ├── blobs/
        │   └── <hash>  (actual model file)
        ├── refs/
        │   └── main
        └── snapshots/
            └── <commit-hash>/
                └── qwen3-vl-30b-a3b-instruct-q4_k_m.gguf  (symlink to blob)
```

## Configuration

### docker-compose.yml

```yaml
llama-cpp:
  volumes:
    - hf-cache:/data/.huggingface  # Shared with all services
    - torch-cache:/data/.torch      # Shared PyTorch cache
  environment:
    - HF_HOME=/data/.huggingface
    - MODEL_PATH=/data/.huggingface/hub/models--Qwen--Qwen3-VL-30B-A3B-Instruct-GGUF/snapshots/latest/qwen3-vl-30b-a3b-instruct-q4_k_m.gguf
```

### Download Script

The download script checks if the model exists before downloading:

```bash
# Check if already downloaded
if docker exec llama-cpp test -f /data/.huggingface/hub/models--Qwen--Qwen3-VL-30B-A3B-Instruct-GGUF/snapshots/*/qwen3-vl-30b-a3b-instruct-q4_k_m.gguf 2>/dev/null; then
    echo "✅ Model already exists in shared HF cache!"
    exit 0
fi
```

## Verification

### Check What's in the Cache

```bash
# List all models in shared cache
docker exec llama-cpp ls -la /data/.huggingface/hub/

# Check specific model
docker exec llama-cpp ls -la /data/.huggingface/hub/models--Qwen--Qwen3-VL-30B-A3B-Instruct-GGUF/

# Check cache size
docker exec llama-cpp du -sh /data/.huggingface/
```

### Verify Model is Accessible

```bash
# Check if llama.cpp can see the model
docker exec llama-cpp test -f "$MODEL_PATH" && echo "✅ Model found" || echo "❌ Model not found"

# Check symlink resolution
docker exec llama-cpp readlink -f /data/.huggingface/hub/models--Qwen--Qwen3-VL-30B-A3B-Instruct-GGUF/snapshots/latest/qwen3-vl-30b-a3b-instruct-q4_k_m.gguf
```

## Docker Volume Management

### Backup the Cache

```bash
# Create backup of entire HF cache
docker run --rm -v hf-cache:/data -v $(pwd):/backup ubuntu tar czf /backup/hf-cache-backup.tar.gz /data/.huggingface
```

### Restore from Backup

```bash
# Restore HF cache
docker run --rm -v hf-cache:/data -v $(pwd):/backup ubuntu tar xzf /backup/hf-cache-backup.tar.gz -C /
```

### Clean Old Models

```bash
# List cache size per model
docker exec llama-cpp du -sh /data/.huggingface/hub/*

# Remove specific model
docker exec llama-cpp rm -rf /data/.huggingface/hub/models--old--model-name
```

## Troubleshooting

### Model Not Found After Download

**Problem**: Download succeeds but llama.cpp can't find the model

**Solution**: The snapshot path may differ. Find the actual path:

```bash
# Find the actual snapshot hash
docker exec llama-cpp find /data/.huggingface/hub/models--Qwen--Qwen3-VL-30B-A3B-Instruct-GGUF/snapshots/ -name "*.gguf"

# Update MODEL_PATH in docker-compose.yml with the actual hash
# Or create a symlink:
docker exec llama-cpp ln -sf /data/.huggingface/hub/models--Qwen--Qwen3-VL-30B-A3B-Instruct-GGUF/snapshots/<actual-hash> /data/.huggingface/hub/models--Qwen--Qwen3-VL-30B-A3B-Instruct-GGUF/snapshots/latest
```

### Permission Errors

**Problem**: Cannot write to cache

**Solution**: Fix permissions on the volume:

```bash
# Check current permissions
docker exec llama-cpp ls -ld /data/.huggingface

# Fix if needed
docker exec -u root llama-cpp chown -R $(id -u):$(id -g) /data/.huggingface
```

### Cache Corruption

**Problem**: Downloads fail or models are incomplete

**Solution**: Clear and re-download:

```bash
# Remove the specific model
docker exec llama-cpp rm -rf /data/.huggingface/hub/models--Qwen--Qwen3-VL-30B-A3B-Instruct-GGUF

# Re-download
./llama-cpp-service/download-model.sh
```

## Best Practices

1. **Always use HuggingFace CLI for downloads** - It handles caching correctly
2. **Don't manually copy models** - Use the CLI to maintain proper symlinks
3. **Monitor cache size** - HF cache can grow large with many models
4. **Backup before major changes** - Cache corruption can be time-consuming to fix
5. **Use the same HF_HOME across all services** - Ensures cache sharing works

## Services Using Shared Cache

All these services use the `hf-cache` volume:

- **llama-cpp** - Qwen3-VL-30B GGUF models
- **whisperx** - Whisper large-v3, diarization models
- **ovi** - Ovi-11B video generation models
- **wan2gp** - Multiple video generation models (1.3B-14B)
- **infinitetalk** - Audio-driven dubbing models
- **vibevoice-api** - TTS voice cloning models
- **youtube-tools** - Uses WhisperX models
- **shorts-generator** - Uses various models

## Performance Impact

- **First download**: Normal speed (depends on internet)
- **Subsequent services**: Instant (model already cached)
- **Disk I/O**: Minimal overhead from symlinks
- **Memory**: No impact (each service loads its own copy into VRAM)

## Related Documentation

- [llama.cpp Service README](./README.md)
- [Docker Compose Configuration](../docker-compose.yml)
- [Integration Guide](../custom_code/docs/LLAMA_CPP_INTEGRATION.md)
