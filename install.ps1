#Requires -Version 5.1
<#
.SYNOPSIS
    Installer for GTFS to GPX converter (Windows)
.DESCRIPTION
    Clones repository, creates venv, installs dependencies,
    and creates desktop shortcut.
#>

$ErrorActionPreference = "Stop"

# --- Check Execution Policy ---
$execPolicy = Get-ExecutionPolicy -Scope Process
if ($execPolicy -eq "Restricted" -or $execPolicy -eq "AllSigned") {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "  WARNING: Execution Policy Blocked" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "PowerShell blocks script execution."
    Write-Host ""
    Write-Host "Run installer with:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\install.ps1" -ForegroundColor Green
    Write-Host ""
    exit 1
}

$RepoUrl = "https://github.com/whitefoxxy/spb-gtfs-gpx.git"
$AppName = "spb-gtfs-gpx"
$InstallDir = "$env:LOCALAPPDATA\$AppName"
$RepoDir = "$InstallDir\app"
$VenvDir = "$InstallDir\venv"
$LauncherDir = "$InstallDir"

function Write-Step {
    param([string]$Message)
    Write-Host "[+] $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Err {
    param([string]$Message)
    Write-Host "[ERR] $Message" -ForegroundColor Red
}

# --- 1. Check Python ---
Write-Step "Checking Python..."
try {
    $pyVer = python --version 2>&1
    if ($pyVer -match "Python (\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
            Write-Err "Python 3.10+ required. Found: $pyVer"
            Write-Host "Download from https://python.org/downloads/"
            exit 1
        }
        Write-Ok "Python $pyVer"
    }
} catch {
    Write-Err "Python not found. Install Python 3.10+ from https://python.org/downloads/"
    exit 1
}

# --- 2. Check Git ---
Write-Step "Checking Git..."
try {
    $gitVer = git --version 2>$null
    Write-Ok "$gitVer"
} catch {
    Write-Err "Git not found. Install from https://git-scm.com/download/win"
    exit 1
}

# --- 3. Create directory ---
Write-Step "Creating install directory: $InstallDir..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# --- 4. Clone repository ---
if (Test-Path "$RepoDir\.git") {
    Write-Step "Repository exists. Updating..."
    Set-Location $RepoDir
    git pull
    Set-Location -
} else {
    Write-Step "Cloning repository..."
    git clone $RepoUrl $RepoDir
}
Write-Ok "Repository ready"

# --- 5. Create virtual environment ---
Write-Step "Creating virtual environment..."
if (Test-Path $VenvDir) {
    Remove-Item -Recurse -Force $VenvDir
}
python -m venv $VenvDir
Write-Ok "Venv created"

# --- 6. Install dependencies ---
Write-Step "Installing dependencies..."
& "$VenvDir\Scripts\python.exe" -m pip install --upgrade pip | Out-Null
& "$VenvDir\Scripts\pip.exe" install -r "$RepoDir\requirements.txt"
Write-Ok "Dependencies installed"

# --- 7. Create launcher ---
$LauncherPath = "$LauncherDir\$AppName.bat"
$batContent = "@echo off`ncall `"$VenvDir\Scripts\activate.bat`"`ncd /d `"$RepoDir`"`npython main.py`npause`n"
Set-Content -Path $LauncherPath -Value $batContent -Encoding ASCII
Write-Ok "Launcher created: $LauncherPath"

# --- 8. Create desktop shortcut ---
$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = "$DesktopPath\$AppName.lnk"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "$VenvDir\Scripts\pythonw.exe"
$Shortcut.Arguments = "`"$RepoDir\main.py`""
$Shortcut.WorkingDirectory = $RepoDir
$Shortcut.IconLocation = "%SystemRoot%\System32\SHELL32.dll,14"
$Shortcut.Description = "GTFS to GPX Converter"
$Shortcut.Save()
Write-Ok "Desktop shortcut created"

# --- 9. Create PowerShell launcher ---
$PsLauncher = "$LauncherDir\$AppName.ps1"
$psContent = "& `"$VenvDir\Scripts\Activate.ps1`"`nSet-Location `"$RepoDir`"`npython main.py`n"
Set-Content -Path $PsLauncher -Value $psContent -Encoding UTF8

# --- Done ---
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Installation complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Launch:"
Write-Host "  - Double-click desktop shortcut"
Write-Host "  - Or: $LauncherPath"
Write-Host "  - Or PowerShell: $PsLauncher"
Write-Host ""
Write-Host "Uninstall: Remove-Item -Recurse -Force `"$InstallDir`""
Write-Host ""

# Offer to run
$runNow = Read-Host "Launch now? (y/n)"
if ($runNow -eq "y" -or $runNow -eq "Y") {
    & "$VenvDir\Scripts\python.exe" "$RepoDir\main.py"
}
