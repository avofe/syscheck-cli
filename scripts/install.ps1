# Установка syscheck для Windows БЕЗ Python.
# Скачивает standalone exe из GitHub Releases, кладёт в %LOCALAPPDATA%\syscheck,
# добавляет в PATH (переменная пользователя). Обновление: запустить снова.
#
# Одна строка для друга:
#   powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/avofe/syscheck-cli/main/scripts/install.ps1 | iex"
$ErrorActionPreference = 'Stop'

# --- настрой: свой GitHub и имя файла с релиза ---
$Repo    = "avofe/syscheck-cli"
$Asset   = "syscheck-windows-x86_64.exe"  # имя файла на release
$Version = "latest"                       # или тег, напр. "v0.2.0"

$Dest   = Join-Path $env:LOCALAPPDATA "syscheck"
$Exe    = Join-Path $Dest "syscheck.exe"
$Url    = "https://github.com/$Repo/releases/download/$Version/$Asset"

Write-Host "[syscheck] download: $Url"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null

# PowerShell 5.1: iwr с ProgressPreference=SilentlyContinue ускоряет скачивание
$old = $ProgressPreference; $ProgressPreference = 'SilentlyContinue'
try { Invoke-WebRequest -Uri $Url -OutFile $Exe } finally { $ProgressPreference = $old }

if (-not $?) { throw "Download failed: $Url" }

# PATH пользователя
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$parts = $userPath -split ';' | Where-Object { $_ -ne '' }
if ($parts -notcontains $Dest) {
    $newPath = (@($parts) + $Dest) -join ';'
    [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
    Write-Host "[syscheck] PATH updated. Restart terminal."
} else {
    Write-Host "[syscheck] PATH already ok."
}

Write-Host ""
Write-Host "[syscheck] DONE. Open a NEW terminal and run:"
Write-Host "  syscheck          # живой дашборд (TUI)"
Write-Host "  syscheck cpu      # нагрузка CPU"
Write-Host "  syscheck --help   # все команды"