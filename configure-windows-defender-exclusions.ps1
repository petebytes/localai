# Configure Windows Defender Exclusions for WSL2
# Run this script as Administrator in PowerShell

Write-Host "Configuring Windows Defender exclusions for WSL2..." -ForegroundColor Cyan

# Get current username
$username = $env:USERNAME
Write-Host "Detected Windows user: $username" -ForegroundColor Green

# WSL2 Exclusions
$exclusions = @(
    # WSL2 Virtual Disk (ext4.vhdx)
    "C:\Users\$username\AppData\Local\Packages\CanonicalGroupLimited.Ubuntu*\LocalState\ext4.vhdx",

    # WSL Distribution paths
    "\\wsl.localhost\ubuntu-24-04\home\ghar",
    "\\wsl$\ubuntu-24-04\home\ghar",

    # Specific code directory
    "\\wsl.localhost\ubuntu-24-04\home\ghar\code",
    "\\wsl$\ubuntu-24-04\home\ghar\code",

    # D: Drive (Windows path and WSL mount)
    "D:\",
    "\\wsl.localhost\ubuntu-24-04\mnt\d",
    "\\wsl$\ubuntu-24-04\mnt\d",

    # E: Drive (Windows path and WSL mount)
    "E:\",
    "\\wsl.localhost\ubuntu-24-04\mnt\e",
    "\\wsl$\ubuntu-24-04\mnt\e",

    # AI Models directory on D:
    "D:\AI_Models"
)

# Add each exclusion
foreach ($path in $exclusions) {
    try {
        Write-Host "Adding exclusion: $path" -ForegroundColor Yellow
        Add-MpPreference -ExclusionPath $path -ErrorAction Stop
        Write-Host "  ✓ Added successfully" -ForegroundColor Green
    }
    catch {
        if ($_.Exception.Message -like "*already exists*") {
            Write-Host "  ℹ Already excluded" -ForegroundColor Gray
        }
        else {
            Write-Host "  ✗ Failed: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

Write-Host "`n================================================" -ForegroundColor Cyan
Write-Host "Configuration complete!" -ForegroundColor Green
Write-Host "================================================`n" -ForegroundColor Cyan

# Display current exclusions
Write-Host "Current Windows Defender Exclusions:" -ForegroundColor Cyan
Write-Host "------------------------------------" -ForegroundColor Cyan
try {
    $currentExclusions = Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
    foreach ($exclusion in $currentExclusions | Sort-Object) {
        if ($exclusion -match "wsl|ubuntu|/mnt/[de]|^[DE]:\\") {
            Write-Host "  $exclusion" -ForegroundColor White
        }
    }
}
catch {
    Write-Host "  Unable to retrieve exclusions: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n================================================" -ForegroundColor Cyan
Write-Host "IMPORTANT NOTES:" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "1. These exclusions reduce security scanning for development files" -ForegroundColor White
Write-Host "2. Only exclude directories you trust (your own development files)" -ForegroundColor White
Write-Host "3. Performance improvements are most noticeable for:" -ForegroundColor White
Write-Host "   - Docker operations" -ForegroundColor Gray
Write-Host "   - npm/yarn/pnpm installs" -ForegroundColor Gray
Write-Host "   - Python virtual environments" -ForegroundColor Gray
Write-Host "   - Git operations" -ForegroundColor Gray
Write-Host "   - File watching (webpack, vite, etc.)" -ForegroundColor Gray
Write-Host "`n" -ForegroundColor White
