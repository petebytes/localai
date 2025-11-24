# Security Scanning Guide for Excluded Directories

## Quick Start

Run the security scan anytime:
```bash
cd ~/code/localai
./security-scan-excluded-dirs.sh
```

Or from anywhere:
```bash
~/code/localai/security-scan-excluded-dirs.sh
```

## What It Checks

### 🔴 HIGH Severity
1. **Hidden Executables** - Malware often hides as `.filename`
2. **Suspicious Filenames** - Files with names like "crack", "keygen", "backdoor"
3. **Vulnerable Dependencies** - Critical/high severity npm/pip packages

### 🟡 MEDIUM Severity
1. **Recently Modified Executables** - New/changed binary files (last 7 days)
2. **Windows Executables** - `.exe`, `.dll`, `.ps1`, `.bat` files (last 30 days)
3. **SUID/SGID Files** - Files with elevated privileges
4. **World-Writable Files** - Files anyone can modify

### 🟢 INFO
1. **Large Files** - Files >100MB (potential data exfiltration)
2. **Recent Changes** - Files modified in last 24 hours
3. **Dependency Status** - Security audit results

## Scanned Locations

- `/home/ghar` - Your WSL home directory
- `/home/ghar/code` - All your Git repositories
- `/mnt/d` - D: drive (excluding AI_Models, Steam, Videos)
- `/mnt/e` - E: drive

## Setup Weekly Automatic Scan

### Option 1: Cron (Linux/WSL)

Add to your crontab:
```bash
crontab -e
```

Add this line (runs every Sunday at 9 AM):
```cron
0 9 * * 0 /home/ghar/code/localai/security-scan-excluded-dirs.sh >> /home/ghar/security-scan.log 2>&1
```

Or run daily at 2 AM:
```cron
0 2 * * * /home/ghar/code/localai/security-scan-excluded-dirs.sh >> /home/ghar/security-scan.log 2>&1
```

View logs:
```bash
cat ~/security-scan.log
```

### Option 2: Manual Reminder

Set a calendar reminder to run weekly:
```bash
# Every Monday morning
./security-scan-excluded-dirs.sh | tee ~/security-scan-$(date +%Y%m%d).log
```

## Responding to Findings

### HIGH Severity Findings

**Hidden Executables:**
```bash
# Investigate the file
file /path/to/hidden/executable
ls -la /path/to/hidden/executable

# Check what created it
stat /path/to/hidden/executable

# If suspicious, delete
rm /path/to/hidden/executable
```

**Suspicious Filenames:**
```bash
# Check file type and contents
file /path/to/suspicious/file
head -n 20 /path/to/suspicious/file

# Check file origin (if it's tracked in git)
cd /path/to/repo
git log --all -- relative/path/to/file

# Delete if malicious
rm /path/to/suspicious/file
```

**Vulnerable Dependencies:**
```bash
# NPM packages
cd /path/to/project
npm audit
npm audit fix              # Auto-fix vulnerabilities
npm audit fix --force      # Force update to latest (may break)

# Python packages
cd /path/to/project
source .venv/bin/activate
pip-audit
pip-audit --fix            # Auto-fix vulnerabilities
```

### MEDIUM Severity Findings

**Recently Modified Executables:**
- Review if you recognize them
- Check if they're part of a legitimate install
- Verify with `git status` if in a repo

**Windows Executables in WSL:**
- Usually safe if you downloaded them intentionally
- Suspicious if you didn't download them
- Check with VirusTotal if unsure

**SUID/SGID Files:**
- Normal for some system binaries
- Suspicious in your code directories
- Investigate and remove if unrecognized

### INFO Findings

**Large Files:**
- Often legitimate (datasets, models, videos)
- Suspicious if they appeared unexpectedly
- Check with `file` command to verify type

**Recent Changes:**
- Normal during active development
- Review if you don't recognize the changes

## Additional Security Tools

### Install Security Scanners

```bash
# Python security scanner
pip install pip-audit

# Node.js security scanner (included with npm)
npm audit

# ClamAV antivirus (optional)
sudo apt install clamav clamav-daemon
sudo freshclam                    # Update virus definitions
clamscan -r /home/ghar/code      # Scan code directory
```

### Manual Checks

```bash
# Find all executables
find ~/code -type f -executable -ls

# Find files modified today
find ~/code -type f -mtime 0

# Find files by specific extension
find ~/code -type f -name "*.exe" -o -name "*.dll"

# Check for files with no owner (suspicious)
find ~/code -nouser -o -nogroup

# Find files larger than 1GB
find ~/code -type f -size +1G
```

## Best Practices

### Before Installing Packages

```bash
# NPM: Check package info
npm info package-name
npm view package-name repository

# Python: Check package info
pip show package-name
# Check PyPI page for reputation

# Check package on Socket.dev (security scanner)
# https://socket.dev/
```

### Before Cloning Repos

```bash
# Check GitHub repo stats
# - Stars, forks, recent activity
# - Contributors (trusted?)
# - Open issues (security concerns?)

# Clone and review before running
git clone <repo>
cd <repo>
# Review package.json, setup.py, Makefile
# Review any install scripts
# Then install dependencies
```

### Regular Maintenance

```bash
# Weekly: Run security scan
~/code/localai/security-scan-excluded-dirs.sh

# Monthly: Update dependencies
cd /path/to/project
npm update                    # Node.js
uv pip install --upgrade -r requirements.txt  # Python

# Quarterly: Review exclusions
~/code/localai/check-defender-exclusions.sh
```

## Scan Schedule Recommendation

| Frequency | When | Command |
|-----------|------|---------|
| Weekly | Sunday 9 AM | Automated via cron |
| After new package install | Immediately | Manual run |
| After cloning new repo | Immediately | Manual run |
| Before important commits | Before commit | Manual run |
| Random spot check | Monthly | Manual run |

## Emergency: Suspected Compromise

If you suspect malware:

1. **Immediately run full scan:**
   ```bash
   ./security-scan-excluded-dirs.sh | tee ~/emergency-scan.log
   ```

2. **Temporarily re-enable Windows Defender:**
   ```powershell
   # Remove D: and E: exclusions temporarily
   Remove-MpPreference -ExclusionPath "D:\"
   Remove-MpPreference -ExclusionPath "E:\"

   # Run full scan
   Start-MpScan -ScanType FullScan
   ```

3. **Check running processes:**
   ```bash
   ps aux | grep -v "\[" | head -20
   top
   ```

4. **Check network connections:**
   ```bash
   netstat -tupn | grep ESTABLISHED
   ```

5. **After cleanup, re-add exclusions:**
   ```powershell
   cd D:\
   .\configure-windows-defender-exclusions.ps1
   ```

## Questions?

- Script location: `~/code/localai/security-scan-excluded-dirs.sh`
- Log output to file: `./security-scan-excluded-dirs.sh > scan.log 2>&1`
- Run specific sections: Edit script and comment out sections you don't need

Stay safe! 🔒
