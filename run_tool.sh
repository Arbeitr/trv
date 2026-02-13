#!/usr/bin/env bash
# Train Route Visualizer Launcher (Linux/macOS)
# Auto-creates virtual environment and installs dependencies (PEP 668 compliant)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Check if python3-venv is available (NOT pre-installed on Ubuntu 24.04)
if ! python3 -m venv --help &> /dev/null; then
    echo "❌ python3-venv is not installed."
    echo ""
    echo "   On Ubuntu/Debian, install it with:"
    echo "   sudo apt install python3-venv"
    echo ""
    echo "   On other systems, ensure Python venv module is available."
    exit 1
fi

# Auto-create venv on first run
if [ ! -d "$VENV_DIR" ]; then
    echo "🔧 First run — setting up virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Install dependencies only if requirements.txt changed
if [ ! -f "$VENV_DIR/.deps_installed" ] || \
   [ "$SCRIPT_DIR/requirements.txt" -nt "$VENV_DIR/.deps_installed" ]; then
    echo "📦 Installing dependencies..."
    pip install --upgrade pip --quiet
    pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
    touch "$VENV_DIR/.deps_installed"
    echo "✓ Dependencies installed"
fi

# Run the application
echo ""
echo "🚂 Starting Train Route Visualizer..."
echo ""
python3 "$SCRIPT_DIR/app.py"
