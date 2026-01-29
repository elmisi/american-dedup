#!/bin/bash
# Install american-dedup

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
BIN_DIR="$HOME/.local/bin"

echo "Installing american-dedup..."

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv "$VENV_DIR"

# Install dependencies in venv
echo "Installing Python dependencies..."
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" --quiet

# Create bin directory if it doesn't exist
mkdir -p "$BIN_DIR"

# Create wrapper script
cat > "$BIN_DIR/american-dedup" << EOF
#!/bin/bash
"$VENV_DIR/bin/python" "$SCRIPT_DIR/run.py" "\$@"
EOF

chmod +x "$BIN_DIR/american-dedup"

echo ""
echo "Installation complete!"
echo ""
echo "Make sure $BIN_DIR is in your PATH."
echo "You can add this line to your ~/.bashrc or ~/.zshrc:"
echo ""
echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
echo ""
echo "Then run: american-dedup [path]"
