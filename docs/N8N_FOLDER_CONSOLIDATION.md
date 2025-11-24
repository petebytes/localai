# N8N Folder Consolidation Plan

## Current State (Confusing!)

N8N-related folders are scattered across the project:

```
localai/
├── n8n/                              # Empty backup directory
│   └── backup/                       # (empty)
├── n8n-data/                         # Runtime data (5.5GB - database, binary files)
├── n8n-docker/                       # Docker build context
│   ├── Dockerfile
│   ├── docker-entrypoint.sh
│   └── install-custom-nodes.sh
├── n8n-custom/                       # DELETED (obsolete Dockerfile)
├── custom_code/
│   ├── n8n/                          # Workflows and ComfyUI references
│   │   ├── workflows/                # 10 workflow JSON files
│   │   └── comfyui/                  # ComfyUI workflow references
│   └── n8n-nodes/                    # Custom node source code
│       ├── n8n-nodes-comfyui-enhanced/
│       └── n8n-nodes-llama-orchestrator/
└── shared/
    └── n8n/                          # Shared media assets (audio, images)
        ├── audio.mp3
        ├── audio-7sec.mp3
        └── peggy-cartoon.png
```

## Recommended Structure

**Principle: Separate runtime data from source-controlled configuration**

```
localai/
├── n8n-data/                         # Runtime only (NOT in git)
│   ├── database.sqlite               # 578 MB
│   ├── binaryData/                   # 5.0 GB execution artifacts
│   └── logs/                         # Runtime logs
│
└── n8n/                              # All source-controlled content
    ├── docker/                       # Build context
    │   ├── Dockerfile
    │   ├── docker-entrypoint.sh
    │   └── install-custom-nodes.sh
    │
    ├── workflows/                    # Workflow definitions
    │   ├── short-inspirational-videos.json
    │   ├── shorts-from-long-videos-n8n.json
    │   ├── llama-chat-example.json
    │   └── ...
    │
    ├── workflows-docs/               # Workflow documentation
    │   └── shorts-from-long-videos.md
    │
    ├── comfyui/                      # ComfyUI workflow references
    │   ├── README.md
    │   ├── image_to_image/
    │   └── text_to_image/
    │
    ├── custom-nodes/                 # Custom node source code
    │   ├── n8n-nodes-comfyui-enhanced/
    │   └── n8n-nodes-llama-orchestrator/
    │
    ├── shared/                       # Shared media assets
    │   ├── audio.mp3
    │   ├── audio-7sec.mp3
    │   └── peggy-cartoon.png
    │
    └── backup/                       # Backup destination
```

## Rationale

### Why Keep n8n-data/ Separate?
- **Runtime data** (database, binary files, logs) should be treated like any other service data
- Consistent with project pattern: `postgres-data/`, `redis-data/`, etc.
- Already ignored in `.gitignore`
- Large files (5.5GB) that don't belong in source control
- Mounted as Docker volume - cleaner to keep at root level

### Why Consolidate Everything Else Under n8n/?
- **Single source of truth** for all n8n configuration and custom code
- Clear hierarchy: `n8n/docker/`, `n8n/workflows/`, `n8n/custom-nodes/`
- Easy to find and understand what's n8n-related
- Better for documentation and onboarding

### What Gets Deleted?
- `n8n-custom/` - Already deleted, was replaced by `n8n-docker/`
- Empty `n8n/backup/` - Will be recreated in consolidated structure

## Migration Steps

### 1. Create New Structure
```bash
# Create consolidated n8n directory
mkdir -p n8n/{docker,workflows,workflows-docs,comfyui,custom-nodes,shared,backup}

# Move docker build context
mv n8n-docker/* n8n/docker/

# Move workflows
mv custom_code/n8n/workflows/* n8n/workflows/
mv custom_code/n8n/workflows/*.md n8n/workflows-docs/ 2>/dev/null || true

# Move ComfyUI references
mv custom_code/n8n/comfyui n8n/

# Move custom nodes
mv custom_code/n8n-nodes/* n8n/custom-nodes/

# Move shared assets
mv shared/n8n/* n8n/shared/
```

### 2. Update docker-compose.yml

Change build context (line 61):
```yaml
# Before:
build:
  context: ./n8n-docker

# After:
build:
  context: ./n8n/docker
```

Change volume mounts (lines 399-402):
```yaml
# Before:
volumes:
  - ./n8n-data:/home/node/.n8n
  - ./n8n/backup:/backup
  - ./shared:/data/shared
  - ./custom_code:/custom_code:ro

# After:
volumes:
  - ./n8n-data:/home/node/.n8n
  - ./n8n/backup:/backup
  - ./n8n/shared:/data/shared
  - ./n8n/custom-nodes:/custom_code/n8n-nodes:ro
```

### 3. Update install-custom-nodes.sh

Change paths (line 5):
```bash
# Before:
CUSTOM_NODES_SOURCE="/custom_code/n8n-nodes"

# After:
CUSTOM_NODES_SOURCE="/custom_code/n8n-nodes"  # No change needed if we mount correctly
```

Or update the mount to:
```yaml
- ./n8n/custom-nodes:/custom_code/n8n-nodes:ro
```

### 4. Update .gitignore

Ensure runtime data is ignored:
```gitignore
# N8N runtime data (not in git)
n8n-data/

# N8N source-controlled content (in git)
!n8n/
```

### 5. Update Documentation

Update references in:
- `README.md` - Update n8n folder paths
- `custom_code/shorts-generator/n8n_client.py` - No changes needed (uses webhook)
- Any docs referencing old paths

### 6. Clean Up Old Directories
```bash
# Remove old empty directories
rmdir n8n-docker
rmdir custom_code/n8n/workflows custom_code/n8n/comfyui custom_code/n8n
rmdir custom_code/n8n-nodes
rmdir shared/n8n
rmdir n8n  # Old empty backup dir

# Completely remove deleted n8n-custom
git rm -rf n8n-custom 2>/dev/null || true
```

### 7. Test
```bash
# Rebuild and restart n8n
docker-compose build n8n
docker-compose up -d n8n

# Check logs
docker-compose logs -f n8n

# Verify custom nodes installed
docker-compose exec n8n ls -la /home/node/.n8n/custom
```

## Benefits

1. **Clear Organization**: All n8n config in one place
2. **Easy Navigation**: `n8n/` contains everything except runtime data
3. **Maintainable**: New developers can understand structure quickly
4. **Consistent**: Follows pattern of separating runtime data from config
5. **Scalable**: Easy to add new n8n-related content in the future

## Migration Checklist

- [ ] Create new `n8n/` directory structure
- [ ] Move docker build context
- [ ] Move workflows and documentation
- [ ] Move ComfyUI references
- [ ] Move custom nodes
- [ ] Move shared assets
- [ ] Update `docker-compose.yml` paths
- [ ] Update `.gitignore`
- [ ] Test docker build
- [ ] Test n8n startup
- [ ] Verify custom nodes installed
- [ ] Verify workflows accessible
- [ ] Remove old directories
- [ ] Commit changes
- [ ] Update README.md
