# syscheck installer for Windows (no admin, no Python required).
#
# One-liner:
#   irm https://raw.githubusercontent.com/avofe/syscheck-cli/main/install.ps1 | iex
#
# Installs the standalone syscheck.exe from the latest GitHub release into
# %LOCALAPPDATA%\syscheck\bin and adds it to the *current user* PATH.
# Run again later to update.

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

$ASSET = "syscheck-windows-x86_64.exe"
$OWNER = "avofe"
$REPO  = "syscheck-cli"
$URL   = "https://github.com/$OWNER/$REPO/releases/latest/download/$ASSET"

$InstallDir  = Join-Path $env:LOCALAPPDATA "syscheck\bin"
$Target      = Join-Path $InstallDir "syscheck.exe"

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

Write-Host "syscheck: downloading $ASSET ..." -ForegroundColor Cyan
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
try {
    Invoke-WebRequest -Uri $URL -OutFile $Target -UseBasicParsing
} catch {
    Write-Host "install failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

$size = (Get-Item $Target).Length
if ($size -lt 1MB) {
    Remove-Item -LiteralPath $Target -Force -ErrorAction SilentlyContinue
    Write-Host "install failed: downloaded file is too small (possibly an error page)." -ForegroundColor Red
    exit 1
}

if (-not ($env:PATH -split ';' | Where-Object { $_.TrimEnd('\') -ieq $InstallDir.TrimEnd('\') })) {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $newPath = ($userPath.TrimEnd(';') + ";" + $InstallDir).TrimStart(';')
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "added $InstallDir to your user PATH." -ForegroundColor Cyan
}

Write-Host ""
Write-Host "syscheck installed: $Target" -ForegroundColor Green
Write-Host "version: $( & $Target --version )" -ForegroundColor Green
Write-Host ""
Write-Host "Open a NEW terminal window and run:" -ForegroundColor White
Write-Host "  syscheck watch" -ForegroundColor Cyan
Write-Host ""
Write-Host "Current shell fallback: & $Target watch" -ForegroundColor Gray