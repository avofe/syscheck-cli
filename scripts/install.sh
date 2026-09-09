#!/usr/bin/env bash
# Установка syscheck-cli для macOS/Linux.
# Ставит из PyPI (pip install) или через pipx — нужен только Python.
#
# Одна строка для друга:
#   curl -sSL https://raw.githubusercontent.com/avofe/syscheck-cli/main/scripts/install.sh | bash
set -euo pipefail

log() { printf '\033[1;32m[syscheck]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[syscheck]\033[0m %s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || die "python3 not found — install Python or use the Windows .exe build"

if command -v pipx >/dev/null 2>&1; then
    log "installing via pipx (isolated)..."
    pipx install syscheck-cli
elif command -v pip3 >/dev/null 2>&1; then
    log "installing via pip3 --user..."
    pip3 install --user syscheck-cli
else
    log "pip not found, bootstrapping pip via ensurepip..."
    python3 -m ensurepip --user || python3 -m pip --version
    python3 -m pip install --user syscheck-cli
fi

log ""
log "DONE. Open a NEW terminal and run:"
log "  syscheck          # live dashboard (TUI)"
log "  syscheck cpu      # CPU load"
log "  syscheck --help   # all commands"