#!/usr/bin/env bash
# syscheck installer for macOS / Linux (no Python required).
#
# One-liner:
#   curl -fsSL https://raw.githubusercontent.com/avofe/syscheck-cli/main/install.sh | bash
#
# Downloads the standalone syscheck binary from the latest GitHub release
# into ~/.local/bin and prints a PATH hint if needed. Run again to update.

set -euo pipefail

OWNER="avofe"
REPO="syscheck-cli"
BASE="https://raw.githubusercontent.com/$OWNER/$REPO/main"
BIN_DIR="${SYSCHECK_INSTALL_DIR:-$HOME/.local/bin}"

case "$(uname -s)-$(uname -m)" in
  Linux-x86_64)          ASSET="syscheck-linux-x86_64" ;;
  Darwin-arm64)          ASSET="syscheck-macos-arm64" ;;
  Darwin-x86_64)         ASSET="syscheck-macos-arm64" ;;
  *)
    echo "syscheck: unsupported platform: $(uname -s) $(uname -m)" >&2
    exit 1
    ;;
esac

URL="https://github.com/$OWNER/$REPO/releases/latest/download/$ASSET"

echo "syscheck: downloading $ASSET ..."
mkdir -p "$BIN_DIR"
curl -fsSL "$URL" -o "$BIN_DIR/syscheck"
chmod +x "$BIN_DIR/syscheck"

SIZE=$(stat -c%s "$BIN_DIR/syscheck" 2>/dev/null || stat -f%z "$BIN_DIR/syscheck" 2>/dev/null || 0)
if [ "$SIZE" -lt 1000000 ]; then
  rm -f "$BIN_DIR/syscheck"
  echo "syscheck: install failed: downloaded file is too small." >&2
  exit 1
fi

echo ""
echo "syscheck installed: $BIN_DIR/syscheck"
echo "version: $($BIN_DIR/syscheck --version)"

if ! printf '%s' "$PATH" | tr ':' '\n' | grep -qx "$BIN_DIR"; then
  echo ""
  echo "Add $BIN_DIR to your PATH, then open a new terminal:"
  echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
echo ""
echo "Run it:"
echo "  syscheck watch"
echo ""
echo "If this shell cannot find it yet: $BIN_DIR/syscheck watch"