# Secret Rotation Quick Start

## TL;DR - Rotate Everything

```bash
cd /home/ghar/code/localai

# 1. Check health
./scripts/check-services.py

# 2. Rotate (creates automatic backup)
./scripts/rotate-secrets.py

# 3. Restart services
./scripts/restart-after-rotation.sh

# 4. Verify
./scripts/check-services.py
```

Done! All secrets rotated, services restarted.

---

## If Something Goes Wrong

```bash
# Restore from latest backup
./scripts/restore-secrets.py --latest

# Restart everything
./scripts/restart-after-rotation.sh --all

# Check status
./scripts/check-services.py
```

---

## Common Tasks

### Preview Changes (Dry Run)
```bash
./scripts/rotate-secrets.py --dry-run
```

### Rotate Specific Secrets Only
```bash
./scripts/rotate-secrets.py --secrets JWT_SECRET,POSTGRES_PASSWORD
```

### List Available Backups
```bash
./scripts/restore-secrets.py --list
```

### Restore Specific Backup
```bash
./scripts/restore-secrets.py --backup 20251031-143000
```

### Check Service Health
```bash
./scripts/check-services.py
```

### Restart All Services
```bash
./scripts/restart-after-rotation.sh --all
```

---

## What Gets Rotated?

✅ **Auto-rotated:**
- PostgreSQL password
- JWT secrets & tokens
- Encryption keys
- Dashboard password
- Internal API keys

❌ **NOT auto-rotated (user-managed):**
- OpenAI API key
- NVIDIA NGC API key

---

## Dependencies

Install Python dependencies:
```bash
pip install pyyaml
# or with uv
uv pip install pyyaml
```

---

## Files Created

- `scripts/rotate-secrets.py` - Main rotation script
- `scripts/check-services.py` - Health checker
- `scripts/restore-secrets.py` - Backup restore
- `scripts/restart-after-rotation.sh` - Service restart
- `scripts/secrets-config.yaml` - Configuration
- `backups/secrets/` - Timestamped backups (auto-created)

---

## Full Documentation

See [README-SECRET-ROTATION.md](./README-SECRET-ROTATION.md) for complete documentation.
