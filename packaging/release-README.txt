syscheck 0.6.1 — diagnostic CLI/TUI utility
=============================================

How to run:
  Windows:   syscheck .\syscheck.exe watch
  Linux:     ./syscheck watch
  macOS:     ./syscheck watch

Help:       syscheck --help
Dashboard:  syscheck watch
All in one: syscheck all
JSON mode:  syscheck all --json,  watch --json

These binaries are standalone — Python is not required.

Documentation and source: https://github.com/avofe/syscheck-cli
Install via one-liner (no manual download):
  Windows (PowerShell):
    irm https://raw.githubusercontent.com/avofe/syscheck-cli/main/install.ps1 | iex
  macOS / Linux:
    curl -fsSL https://raw.githubusercontent.com/avofe/syscheck-cli/main/install.sh | bash