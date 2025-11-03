# Windows Defender WSL2 Exclusions Setup

## Quick Start

### Option 1: Double-click (Easiest)
1. Navigate to `D:\` or wherever your project is in Windows Explorer
2. Right-click `configure-windows-defender-exclusions.bat`
3. Select **"Run as administrator"**

### Option 2: PowerShell
1. Open PowerShell **as Administrator** (Right-click Start → Windows PowerShell (Admin))
2. Navigate to this directory:
   ```powershell
   cd D:\path\to\localai  # or wherever this script is
   ```
3. Run the script:
   ```powershell
   .\configure-windows-defender-exclusions.ps1
   ```

### Option 3: From WSL
1. Get the Windows path:
   ```bash
   wslpath -w ~/code/localai
   ```
2. Open PowerShell as Admin and navigate to that path
3. Run the `.ps1` script

## What Gets Excluded

- **WSL2 Virtual Disk**: `ext4.vhdx` file
- **Your WSL home**: `/home/ghar`
- **Your code directory**: `/home/ghar/code`
- **D: Drive**: Entire drive + WSL mount at `/mnt/d`
- **E: Drive**: Entire drive + WSL mount at `/mnt/e`
- **AI Models**: `D:\AI_Models` specifically

## Verification

After running, the script will display all current WSL-related exclusions.

To manually verify later:
```powershell
Get-MpPreference | Select-Object -ExpandProperty ExclusionPath | Where-Object { $_ -match "wsl|ubuntu|mnt" }
```

## Troubleshooting

**"Execution Policy" error?**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Script not running?**
- Make sure you're running PowerShell **as Administrator**
- Check that Windows Defender is your active antivirus

## Security Note

These exclusions disable real-time scanning for development directories. Only use for directories containing code you write or trust.
