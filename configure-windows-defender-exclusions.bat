@echo off
:: Configure Windows Defender Exclusions for WSL2
:: This batch file launches the PowerShell script with Administrator privileges

echo ============================================
echo Windows Defender WSL2 Exclusion Setup
echo ============================================
echo.
echo This script will configure Windows Defender
echo to exclude your WSL2 directories for better
echo development performance.
echo.
echo You will be prompted for Administrator access.
echo.
pause

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running with administrator privileges...
    echo.
    powershell.exe -ExecutionPolicy Bypass -File "%~dp0configure-windows-defender-exclusions.ps1"
) else (
    echo Requesting administrator privileges...
    echo.
    :: Request elevation and run the PowerShell script
    powershell.exe -Command "Start-Process powershell.exe -Verb RunAs -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0configure-windows-defender-exclusions.ps1\" -NoExit'"
)

echo.
echo ============================================
echo.
pause
