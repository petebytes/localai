#!/bin/bash
# Install optional security scanning tools

set -euo pipefail

echo "=========================================="
echo "Security Tools Installer"
echo "=========================================="
echo ""

# Check if running on Ubuntu/Debian
if ! command -v apt &> /dev/null; then
    echo "❌ This script requires apt (Ubuntu/Debian)"
    exit 1
fi

echo "This script will install:"
echo "  1. pip-audit - Python package vulnerability scanner"
echo "  2. ClamAV (optional) - Antivirus scanner"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

# Install pip-audit
echo ""
echo "📦 Installing pip-audit..."
if command -v uv &> /dev/null; then
    echo "Using uv to install pip-audit..."
    uv tool install pip-audit
    echo "✓ pip-audit installed via uv"
elif command -v pipx &> /dev/null; then
    echo "Using pipx to install pip-audit..."
    pipx install pip-audit
    echo "✓ pip-audit installed via pipx"
else
    echo "Installing pipx first..."
    sudo apt update
    sudo apt install -y pipx
    pipx ensurepath
    pipx install pip-audit
    echo "✓ pip-audit installed via pipx"
fi

# Ask about ClamAV
echo ""
echo "=========================================="
read -p "Install ClamAV antivirus? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📦 Installing ClamAV (this may take a few minutes)..."
    sudo apt update
    sudo apt install -y clamav clamav-daemon

    echo "📥 Updating virus definitions..."
    sudo systemctl stop clamav-freshclam || true
    sudo freshclam
    sudo systemctl start clamav-freshclam || true

    echo "✓ ClamAV installed"
    echo ""
    echo "To scan with ClamAV:"
    echo "  clamscan -r ~/code              # Scan code directory"
    echo "  clamscan -r --infected ~/code   # Show only infected files"
else
    echo "⏭️  Skipping ClamAV installation"
fi

echo ""
echo "=========================================="
echo "✓ Installation Complete"
echo "=========================================="
echo ""
echo "Installed tools:"
command -v pip-audit &> /dev/null && echo "  ✓ pip-audit: $(which pip-audit)"
command -v clamscan &> /dev/null && echo "  ✓ ClamAV: $(which clamscan)"
echo ""
echo "Run the security scan now:"
echo "  ~/code/localai/security-scan-excluded-dirs.sh"
echo ""
