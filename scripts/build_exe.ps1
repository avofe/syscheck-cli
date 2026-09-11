# Сборка standalone-exe syscheck.exe (без установленного Python у пользователя).
# Запуск:   .\scripts\build_exe.ps1
# Результат: dist\syscheck-windows-x86_64.exe  (+ .zip и SHA256)
$ErrorActionPreference = 'Stop'

$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $Root

Write-Host "[syscheck] installing pyinstaller..."
python -m pip install --quiet pyinstaller>=6.0.0

Write-Host "[syscheck] building exe (onefile, console)..."
python -m PyInstaller --clean --noconfirm syscheck.spec

$exe = Join-Path $Root "dist\syscheck.exe"
if (-not (Test-Path $exe)) { throw "Build failed: $exe not found" }

$out = Join-Path $Root "dist\syscheck-windows-x86_64.exe"
Copy-Item $exe $out -Force

$zip = "$out.zip"
Compress-Archive -Path $exe -DestinationPath $zip -Force

$hash = (Get-FileHash -Algorithm SHA256 $out).Hash.ToLower()
$size = [Math]::Round((Get-Item $out).Length / 1MB, 1)

Write-Host ""
Write-Host "[syscheck] OK: $out ($size MB)"
Write-Host "[syscheck] SHA256: $hash"
Write-Host ""
Write-Host "Тест: .\dist\syscheck-windows-x86_64.exe"
Write-Host "Залить на GitHub Releases как актив release'а и дать другу:"
Write-Host "  irm https://raw.githubusercontent.com/avofe/syscheck-cli/main/install.ps1 | iex"