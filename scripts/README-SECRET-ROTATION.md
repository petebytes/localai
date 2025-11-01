# Secret Rotation System

Automated secret rotation for the Local AI environment with backup, restore, and health checking capabilities.

## Overview

This system provides simple, script-based secret rotation for all infrastructure secrets including:
- PostgreSQL passwords
- JWT secrets and tokens
- Encryption keys
- API keys (internal services only)
- Dashboard credentials

**External API keys** (OpenAI, NVIDIA NGC) are **NOT** auto-rotated as they're user-managed.

## Quick Start

```bash
# 1. Check current service health
./scripts/check-services.py

# 2. Perform rotation (creates automatic backup)
./scripts/rotate-secrets.py

# 3. Restart affected services
./scripts/restart-after-rotation.sh

# 4. Verify everything is working
./scripts/check-services.py
```

## Scripts

### 1. `rotate-secrets.py` - Main Rotation Script

Generates new cryptographically secure secrets and updates .env files.

**Basic usage:**
```bash
# Dry run - preview changes without applying
./scripts/rotate-secrets.py --dry-run

# Rotate all auto-rotatable secrets
./scripts/rotate-secrets.py

# Rotate specific secrets only
./scripts/rotate-secrets.py --secrets JWT_SECRET,POSTGRES_PASSWORD

# Skip backup (NOT RECOMMENDED)
./scripts/rotate-secrets.py --skip-backup
```

**What it does:**
- Generates cryptographically secure random values
- Regenerates Supabase JWT tokens (ANON_KEY, SERVICE_ROLE_KEY) when JWT_SECRET changes
- Creates timestamped backup before making any changes
- Updates `.env` and `supabase/docker/.env` atomically
- Validates all changes before applying
- Tracks which services need restart

**Options:**
- `--dry-run` - Preview changes without applying
- `--secrets SECRET1,SECRET2` - Rotate only specific secrets
- `--skip-backup` - Skip creating backup (not recommended)
- `--config PATH` - Custom config file path

### 2. `check-services.py` - Service Health Checker

Checks health status of all Docker Compose services.

**Basic usage:**
```bash
# Check current health
./scripts/check-services.py

# Save health state for later comparison
./scripts/check-services.py --save backups/pre-rotation-state.json

# Compare current state with saved state
./scripts/check-services.py --compare backups/pre-rotation-state.json

# Verbose output with error details
./scripts/check-services.py --verbose
```

**Exit codes:**
- `0` - All services healthy
- `1` - Some services unhealthy or degraded

### 3. `restore-secrets.py` - Backup Restore

Restore secrets from a timestamped backup if rotation causes issues.

**Basic usage:**
```bash
# List all available backups
./scripts/restore-secrets.py --list

# Restore from latest backup
./scripts/restore-secrets.py --latest

# Restore from specific backup
./scripts/restore-secrets.py --backup 20251031-143000

# Preview restore without applying
./scripts/restore-secrets.py --latest --dry-run
```

**What it does:**
- Lists available backups with timestamps and metadata
- Restores .env files from backup
- Preserves file permissions (600)
- Shows which secrets were rotated in that backup

### 4. `restart-after-rotation.sh` - Service Restart Orchestration

Gracefully restarts services after secret rotation.

**Basic usage:**
```bash
# Restart affected services only (from metadata)
./scripts/restart-after-rotation.sh

# Restart all services
./scripts/restart-after-rotation.sh --all

# Skip health checks
./scripts/restart-after-rotation.sh --no-healthcheck

# Custom health check timeout
./scripts/restart-after-rotation.sh --timeout 180
```

**What it does:**
- Reads affected services from backup metadata
- Restarts services in correct dependency order
- Waits for services to become healthy
- Compares post-restart health with pre-restart state
- Reports any services that failed to restart

## Configuration

### `secrets-config.yaml`

Defines all rotatable secrets and their properties:

```yaml
secrets:
  SECRET_NAME:
    type: random|jwt-token|static
    length: 32              # For random type
    role: anon              # For jwt-token type
    depends_on: JWT_SECRET  # For jwt-token type
    files:
      - .env
      - supabase/docker/.env
    auto_rotate: true       # false for user-managed secrets
    description: "Human-readable description"
    restart_services:
      - service1
      - service2
```

**Secret types:**
- `random` - Cryptographically secure random string
- `jwt-token` - Supabase-compatible JWT token (depends on JWT_SECRET)
- `static` - User-managed, not auto-rotated

## Workflow Examples

### Standard Rotation

```bash
# 1. Save current state
./scripts/check-services.py --save backups/pre-rotation.json

# 2. Preview rotation
./scripts/rotate-secrets.py --dry-run

# 3. Perform rotation
./scripts/rotate-secrets.py

# 4. Restart services
./scripts/restart-after-rotation.sh

# 5. Verify health
./scripts/check-services.py --compare backups/pre-rotation.json
```

### Emergency Rollback

If rotation causes issues:

```bash
# 1. Restore from latest backup
./scripts/restore-secrets.py --latest

# 2. Restart all services
./scripts/restart-after-rotation.sh --all

# 3. Verify services recovered
./scripts/check-services.py
```

### Rotate Specific Secrets Only

To rotate just JWT-related secrets:

```bash
./scripts/rotate-secrets.py --secrets JWT_SECRET,ANON_KEY,SERVICE_ROLE_KEY
./scripts/restart-after-rotation.sh
```

### Check Services Before Rotation

Always check service health before rotating:

```bash
# This will exit with error if services are unhealthy
if ./scripts/check-services.py; then
    echo "Services healthy, proceeding with rotation..."
    ./scripts/rotate-secrets.py
else
    echo "Services unhealthy, aborting rotation"
    exit 1
fi
```

## Backups

### Automatic Backups

Every rotation automatically creates a timestamped backup:
- Location: `backups/secrets/secrets-backup-YYYYMMDD-HHMMSS/`
- Contents: All affected .env files + metadata
- Permissions: 600 (owner read/write only)
- Retention: 90 days (configurable in `secrets-config.yaml`)

### Backup Structure

```
backups/secrets/secrets-backup-20251031-143000/
├── .env                      # Backed up .env file
├── supabase/
│   └── docker/
│       └── .env              # Backed up supabase .env
└── metadata.json             # Rotation metadata
```

### Metadata Format

```json
{
  "timestamp": "20251031-143000",
  "rotated_secrets": [
    "JWT_SECRET",
    "ANON_KEY",
    "SERVICE_ROLE_KEY",
    "POSTGRES_PASSWORD"
  ],
  "affected_services": [
    "supabase-auth",
    "supabase-rest",
    "supabase-db"
  ]
}
```

## Security Considerations

### Permissions

All backup files are created with restrictive permissions:
- `.env` files: `600` (owner read/write only)
- Backup directories: `700` (owner full access only)
- Metadata: `600` (owner read/write only)

### Git Ignore

Backup directories are automatically git-ignored to prevent accidental commits:
```
backups/secrets/
backups/service-state-*.json
```

### Secret Generation

Secrets are generated using Python's `secrets` module (cryptographically secure):
- Random secrets: Alphanumeric characters (a-zA-Z0-9)
- Minimum lengths enforced per secret type
- No weak or predictable patterns

### JWT Tokens

Supabase JWT tokens are generated with:
- HS256 algorithm
- Long expiration (5+ years)
- Proper base64url encoding
- HMAC-SHA256 signatures

## Troubleshooting

### Services Won't Start After Rotation

```bash
# 1. Check service logs
docker compose logs -f [service-name]

# 2. Restore from backup
./scripts/restore-secrets.py --latest

# 3. Restart services
./scripts/restart-after-rotation.sh --all
```

### Invalid JWT Tokens

If ANON_KEY or SERVICE_ROLE_KEY are invalid:

```bash
# Regenerate JWT tokens with current JWT_SECRET
./scripts/rotate-secrets.py --secrets ANON_KEY,SERVICE_ROLE_KEY
./scripts/restart-after-rotation.sh
```

### Missing Dependencies (Python)

The scripts require Python 3.7+ with these packages:
- `pyyaml` - For config file parsing

Install with:
```bash
pip install pyyaml
# or with uv
uv pip install pyyaml
```

### Permission Denied

Make scripts executable:
```bash
chmod +x scripts/*.py scripts/*.sh
```

### Backup Not Found

List available backups:
```bash
./scripts/restore-secrets.py --list
```

## Advanced Usage

### Custom Config File

```bash
./scripts/rotate-secrets.py --config custom-secrets-config.yaml
```

### Scheduled Rotation (Optional)

To set up automated rotation (not configured by default):

```bash
# Add to crontab (example: monthly on 1st at 2am)
0 2 1 * * cd /home/ghar/code/localai && ./scripts/rotate-secrets.py && ./scripts/restart-after-rotation.sh
```

### Integration with Monitoring

```bash
# Send alert if rotation fails
./scripts/rotate-secrets.py || \
    curl -X POST https://monitoring.example.com/alert \
         -d "Secret rotation failed"
```

### Pre-rotation Health Gate

Prevent rotation if services are unhealthy:

```bash
#!/bin/bash
set -e

# Only rotate if all services healthy
./scripts/check-services.py

# Proceed with rotation
./scripts/rotate-secrets.py
./scripts/restart-after-rotation.sh

# Verify health after rotation
./scripts/check-services.py
```

## Service Dependencies

Services are restarted in dependency order:

1. **Core Infrastructure**
   - `supabase-db` (PostgreSQL)
   - `supabase-vector` (Log collection)
   - `supabase-analytics` (Logflare)

2. **Supabase Services**
   - `supabase-auth` (GoTrue)
   - `supabase-rest` (PostgREST)
   - `supabase-realtime`
   - `supabase-meta`
   - `supabase-storage`
   - `supabase-edge-functions`
   - `supabase-pooler` (Supavisor)
   - `supabase-kong` (API Gateway)
   - `supabase-studio` (Dashboard)

3. **Application Services**
   - `n8n` (Workflows)
   - `nocodb` (Database GUI)
   - `backup` (Volume backup)

4. **AI Services**
   - `crawl4ai`, `whisperx`, `kokoro-fastapi-gpu`
   - `open-webui`, `comfyui`
   - `ovi`, `wan2gp`, `infinitetalk`
   - `yttools`

## What Gets Rotated

### Auto-Rotated (Infrastructure)
- PostgreSQL password
- JWT secrets and derived tokens
- Encryption keys (Vault, PG Meta, Realtime)
- Dashboard password
- Logflare tokens
- Crawl4AI API key
- n8n secrets

### NOT Auto-Rotated (User-Managed)
- OpenAI API key
- NVIDIA NGC API key
- Dashboard username
- Any third-party service credentials

## Support

For issues or questions:
1. Check service logs: `docker compose logs -f [service]`
2. Review backup metadata: `cat backups/secrets/[latest]/metadata.json`
3. Verify config: `cat scripts/secrets-config.yaml`
4. Run health check: `./scripts/check-services.py --verbose`

## Future Enhancements

Possible improvements (not currently implemented):
- Zero-downtime rotation with rolling restarts
- Integration with HashiCorp Vault
- Automatic scheduled rotation
- Slack/email notifications
- Certificate rotation (currently separate)
- Multi-environment support
