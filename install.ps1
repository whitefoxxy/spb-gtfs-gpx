#Requires -Version 5.1
<#
.SYNOPSIS
    Установщик GTFS → GPX конвертера для Windows
.DESCRIPTION
    Клонирует репозиторий, создаёт виртуальное окружение, устанавливает зависимости
    и создаёт ярлык для запуска.
#>

$ErrorActionPreference = "Stop"

# --- Проверка Execution Policy ---
$execPolicy = Get-ExecutionPolicy -Scope Process
if ($execPolicy -eq "Restricted" -or $execPolicy -eq "AllSigned") {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "  ВНИМАНИЕ: Политика выполнения скриптов" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "PowerShell блокирует выполнение скриптов."
    Write-Host ""
    Write-Host "Запустите установку одной из команд:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  1. С обходом политики (рекомендуется):" -ForegroundColor White
    Write-Host "     powershell -ExecutionPolicy Bypass -File .\install.ps1" -ForegroundColor Green
    Write-Host ""
    Write-Host "  2. Или измените политику для текущего пользователя:" -ForegroundColor White
    Write-Host "     Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Green
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

# --- 1. Проверка Python ---
Write-Step "Проверка Python..."
try {
    $pyVer = python --version 2>&1
    if ($pyVer -match "Python (\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
            Write-Err "Требуется Python 3.10+. Установлен: $pyVer"
            Write-Host "Скачайте с https://python.org/downloads/"
            exit 1
        }
        Write-Ok "Python $pyVer"
    }
} catch {
    Write-Err "Python не найден. Установите Python 3.10+ с https://python.org/downloads/"
    exit 1
}

# --- 2. Проверка Git ---
Write-Step "Проверка Git..."
try {
    $gitVer = git --version 2>$null
    Write-Ok "$gitVer"
} catch {
    Write-Err "Git не найден. Установите Git с https://git-scm.com/download/win"
    exit 1
}

# --- 3. Создание директории ---
Write-Step "Создание директории установки: $InstallDir..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# --- 4. Клонирование репозитория ---
if (Test-Path "$RepoDir\.git") {
    Write-Step "Репозиторий уже существует. Обновление..."
    Set-Location $RepoDir
    git pull
    Set-Location -
} else {
    Write-Step "Клонирование репозитория..."
    git clone $RepoUrl $RepoDir
}
Write-Ok "Репозиторий готов"

# --- 5. Создание виртуального окружения ---
Write-Step "Создание виртуального окружения..."
if (Test-Path $VenvDir) {
    Remove-Item -Recurse -Force $VenvDir
}
python -m venv $VenvDir
Write-Ok "Venv создан"

# --- 6. Установка зависимостей ---
Write-Step "Установка зависимостей..."
& "$VenvDir\Scripts\python.exe" -m pip install --upgrade pip | Out-Null
& "$VenvDir\Scripts\pip.exe" install -r "$RepoDir\requirements.txt"
Write-Ok "Зависимости установлены"

# --- 7. Создание лаунчера ---
$LauncherPath = "$LauncherDir\$AppName.bat"
@"
@echo off
call "$VenvDir\Scripts\activate.bat"
cd /d "$RepoDir"
python main.py
pause
"@ | Set-Content -Path $LauncherPath -Encoding ASCII
Write-Ok "Лаунчер создан: $LauncherPath"

# --- 8. Создание ярлыка на рабочем столе ---
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
Write-Ok "Ярлык на рабочем столе создан"

# --- 9. Создание PowerShell-лаунчера (опционально) ---
$PsLauncher = "$LauncherDir\$AppName.ps1"
@"
& "$VenvDir\Scripts\Activate.ps1"
Set-Location "$RepoDir"
python main.py
"@ | Set-Content -Path $PsLauncher -Encoding UTF8

# --- Готово ---
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Установка завершена!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Запуск:"
Write-Host "  - Двойной клик по ярлыку на рабочем столе"
Write-Host "  - Или: $LauncherPath"
Write-Host "  - Или PowerShell: $PsLauncher"
Write-Host ""
Write-Host "Удаление: удалите папку $InstallDir"
Write-Host ""

# Предложение запустить
$runNow = Read-Host "Запустить сейчас? (y/n)"
if ($runNow -eq "y" -or $runNow -eq "Y") {
    & "$VenvDir\Scripts\python.exe" "$RepoDir\main.py"
}
