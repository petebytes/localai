#!/bin/bash
# Check Windows Defender exclusions from WSL

echo "=========================================="
echo "Windows Defender Exclusions Check"
echo "=========================================="
echo ""
echo "Checking WSL-related exclusions..."
echo ""

# Run PowerShell command to get exclusions
powershell.exe -Command "Get-MpPreference | Select-Object -ExpandProperty ExclusionPath | Where-Object { \$_ -match 'wsl|ubuntu|mnt|^[DE]:' } | Sort-Object" 2>/dev/null

echo ""
echo "=========================================="
echo "Looking for these key paths:"
echo "=========================================="
echo "✓ D:\\"
echo "✓ E:\\"
echo "✓ \\\\wsl.localhost\\ubuntu-24-04\\home\\ghar"
echo "✓ ext4.vhdx (WSL virtual disk)"
echo "✓ /mnt/d and /mnt/e paths"
echo ""
