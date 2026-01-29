#!/bin/bash
# Uninstall american-dedup

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
BIN_DIR="$HOME/.local/bin"

echo "Uninstalling american-dedup..."

# Remove wrapper script
rm -f "$BIN_DIR/american-dedup"

# Remove virtual environment
rm -rf "$VENV_DIR"

echo "Uninstallation complete!"
