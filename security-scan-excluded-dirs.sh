#!/bin/bash
# Security scan for Windows Defender excluded directories
# Run this periodically to check for suspicious activity

set -euo pipefail

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Directories to scan (from our exclusions)
SCAN_DIRS=(
    "/home/ghar"
    "/home/ghar/code"
    "/mnt/d"
    "/mnt/e"
)

echo -e "${CYAN}=========================================="
echo -e "Security Scan for Excluded Directories"
echo -e "==========================================${NC}"
echo -e "Started: $(date)"
echo ""

# Function to print section header
section_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to print finding
finding() {
    local severity=$1
    local message=$2
    case $severity in
        "HIGH")
            echo -e "${RED}[!] HIGH: $message${NC}"
            ;;
        "MEDIUM")
            echo -e "${YELLOW}[!] MEDIUM: $message${NC}"
            ;;
        "INFO")
            echo -e "${GREEN}[✓] INFO: $message${NC}"
            ;;
    esac
}

# 1. Check for recently modified executables
section_header "1. Recently Modified Executables (last 7 days)"
echo "Checking for suspicious executable files..."
SUSPICIOUS_EXECS=0
for dir in "${SCAN_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo ""
        echo -e "${YELLOW}Scanning: $dir${NC}"
        while IFS= read -r file; do
            finding "MEDIUM" "Executable modified: $file"
            ((SUSPICIOUS_EXECS++))
        done < <(find "$dir" -type f \( -perm -u+x -o -perm -g+x -o -perm -o+x \) -mtime -7 2>/dev/null | grep -v -E '\.git/|node_modules/|\.venv/|venv/|__pycache__/' | head -20)
    fi
done
if [ $SUSPICIOUS_EXECS -eq 0 ]; then
    finding "INFO" "No recently modified executables found"
fi

# 2. Check for large files (potential data exfiltration or malware)
section_header "2. Large Files (>100MB)"
echo "Checking for unusually large files..."
LARGE_FILES=0
for dir in "${SCAN_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo ""
        echo -e "${YELLOW}Scanning: $dir${NC}"
        while IFS= read -r line; do
            finding "INFO" "$line"
            ((LARGE_FILES++))
        done < <(find "$dir" -type f -size +100M 2>/dev/null | grep -v -E '\.git/|AI_Models/|SteamLibrary/|Videos/|\.iso$|\.vhdx$|\.vmdk$' | head -10)
    fi
done
if [ $LARGE_FILES -eq 0 ]; then
    finding "INFO" "No suspicious large files found"
fi

# 3. Check for hidden executable files
section_header "3. Hidden Executable Files"
echo "Checking for hidden executables (potential malware)..."
HIDDEN_EXECS=0
for dir in "${SCAN_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo ""
        echo -e "${YELLOW}Scanning: $dir${NC}"
        while IFS= read -r file; do
            finding "HIGH" "Hidden executable: $file"
            ((HIDDEN_EXECS++))
        done < <(find "$dir" -type f -name ".*" \( -perm -u+x -o -perm -g+x -o -perm -o+x \) 2>/dev/null | head -20)
    fi
done
if [ $HIDDEN_EXECS -eq 0 ]; then
    finding "INFO" "No hidden executables found"
fi

# 4. Check for suspicious file extensions
section_header "4. Suspicious File Extensions"
echo "Checking for potentially dangerous file types..."
SUSPICIOUS_EXTS=0
DANGEROUS_PATTERNS='\.exe$|\.dll$|\.scr$|\.vbs$|\.bat$|\.cmd$|\.ps1$|\.msi$'
for dir in "${SCAN_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo ""
        echo -e "${YELLOW}Scanning: $dir${NC}"
        while IFS= read -r file; do
            finding "MEDIUM" "Windows executable: $file"
            ((SUSPICIOUS_EXTS++))
        done < <(find "$dir" -type f -regextype posix-extended -regex ".*($DANGEROUS_PATTERNS)" -mtime -30 2>/dev/null | grep -v -E 'node_modules/|\.venv/|venv/|AI_Models/' | head -15)
    fi
done
if [ $SUSPICIOUS_EXTS -eq 0 ]; then
    finding "INFO" "No suspicious Windows executables found (last 30 days)"
fi

# 5. Check for files with suspicious names
section_header "5. Suspicious Filenames"
echo "Checking for common malware naming patterns..."
SUSPICIOUS_NAMES=0
MALWARE_PATTERNS='(crack|keygen|patch|activator|hack|exploit|payload|backdoor|trojan|ransomware)'
for dir in "${SCAN_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo ""
        echo -e "${YELLOW}Scanning: $dir${NC}"
        while IFS= read -r file; do
            finding "HIGH" "Suspicious name: $file"
            ((SUSPICIOUS_NAMES++))
        done < <(find "$dir" -type f -regextype posix-extended -iregex ".*$MALWARE_PATTERNS.*" 2>/dev/null | head -10)
    fi
done
if [ $SUSPICIOUS_NAMES -eq 0 ]; then
    finding "INFO" "No suspicious filenames found"
fi

# 6. NPM Security Audit (if npm is available)
section_header "6. NPM Security Audit"
if command -v npm &> /dev/null; then
    echo "Checking for vulnerable npm packages in code directories..."
    VULN_PROJECTS=0
    find /home/ghar/code -name "package.json" -not -path "*/node_modules/*" 2>/dev/null | while read -r pkg; do
        dir=$(dirname "$pkg")
        if [ -f "$dir/package-lock.json" ]; then
            echo ""
            echo -e "${YELLOW}Auditing: $dir${NC}"
            cd "$dir"
            audit_output=$(npm audit --parseable 2>&1 || true)
            if echo "$audit_output" | grep -q "high\|critical"; then
                finding "HIGH" "Vulnerabilities found in $dir"
                echo "$audit_output" | grep -E "high|critical" | head -5
                ((VULN_PROJECTS++))
            else
                finding "INFO" "No high/critical vulnerabilities in $dir"
            fi
        fi
    done
else
    finding "INFO" "npm not found - skipping npm audit"
fi

# 7. Python Security Audit (if pip-audit is available)
section_header "7. Python Security Audit"
if command -v pip-audit &> /dev/null; then
    echo "Checking for vulnerable Python packages..."
    # Scan common venv locations
    find /home/ghar/code -type d -name ".venv" -o -name "venv" 2>/dev/null | head -5 | while read -r venv_dir; do
        if [ -f "$venv_dir/bin/activate" ]; then
            echo ""
            echo -e "${YELLOW}Auditing: $venv_dir${NC}"
            # Activate venv and run pip-audit
            (
                source "$venv_dir/bin/activate"
                audit_output=$(pip-audit --format=json 2>&1 || echo '{"vulnerabilities":[]}')
                vuln_count=$(echo "$audit_output" | grep -o '"vulnerabilities"' | wc -l)
                if [ "$vuln_count" -gt 0 ]; then
                    finding "HIGH" "Vulnerabilities found in $venv_dir"
                    echo "$audit_output" | head -10
                else
                    finding "INFO" "No vulnerabilities found"
                fi
            )
        fi
    done
else
    finding "INFO" "pip-audit not found - skipping Python audit (install with: pip install pip-audit)"
fi

# 8. Check for SUID/SGID files (potential privilege escalation)
section_header "8. SUID/SGID Files"
echo "Checking for files with elevated privileges..."
SUID_FILES=0
for dir in "${SCAN_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo ""
        echo -e "${YELLOW}Scanning: $dir${NC}"
        while IFS= read -r file; do
            finding "MEDIUM" "SUID/SGID file: $file"
            ((SUID_FILES++))
        done < <(find "$dir" -type f \( -perm -4000 -o -perm -2000 \) 2>/dev/null | head -10)
    fi
done
if [ $SUID_FILES -eq 0 ]; then
    finding "INFO" "No SUID/SGID files found"
fi

# 9. Check for world-writable files
section_header "9. World-Writable Files"
echo "Checking for files writable by anyone..."
WRITABLE_FILES=0
for dir in "${SCAN_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo ""
        echo -e "${YELLOW}Scanning: $dir${NC}"
        while IFS= read -r file; do
            finding "MEDIUM" "World-writable: $file"
            ((WRITABLE_FILES++))
        done < <(find "$dir" -type f -perm -002 2>/dev/null | grep -v -E '/mnt/[de]/' | head -10)
    fi
done
if [ $WRITABLE_FILES -eq 0 ]; then
    finding "INFO" "No concerning world-writable files found"
fi

# 10. Check for recently modified files in system directories
section_header "10. Recent Changes in Home Directory"
echo "Files modified in last 24 hours (excluding common dev directories)..."
RECENT_CHANGES=0
find /home/ghar -type f -mtime -1 2>/dev/null | \
    grep -v -E '\.git/|node_modules/|\.venv/|venv/|__pycache__|\.cache/|\.local/share/|\.config/|\.npm/|\.cargo/' | \
    head -20 | while read -r file; do
        finding "INFO" "Modified: $file"
        ((RECENT_CHANGES++))
    done

# Summary
section_header "SCAN SUMMARY"
echo -e "${CYAN}Scan completed: $(date)${NC}"
echo ""
echo -e "${YELLOW}Recommendations:${NC}"
echo "1. Review any HIGH severity findings immediately"
echo "2. Investigate MEDIUM severity findings"
echo "3. Run npm audit fix / pip-audit --fix for vulnerable dependencies"
echo "4. Delete any files you don't recognize"
echo "5. Run this scan weekly or after installing new packages"
echo ""
echo -e "${GREEN}✓ Scan complete${NC}"
echo ""
