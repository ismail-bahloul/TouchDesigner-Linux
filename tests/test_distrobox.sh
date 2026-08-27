#!/bin/bash
# Distrobox container-mode test — run the TouchDesigner-Linux flow inside an
# isolated container, host untouched.
# Usage: bash tests/test_distrobox.sh [IMAGE]

set -e

echo "=== TouchDesigner-Linux — Distrobox container-mode test ==="
echo ""

# Check distrobox
if ! command -v distrobox &>/dev/null; then
    echo "Distrobox not found. Install it first:"
    echo "  curl -sSL https://distrobox.it/install | sh"
    exit 1
fi

if ! command -v podman &>/dev/null && ! command -v docker &>/dev/null; then
    echo "Need podman or docker for distrobox."
    exit 1
fi

IMAGE="${1:-ubuntu:24.04}"
export TD_CONTAINER_IMAGE="$IMAGE"

# The container shares $HOME, so keep a repo copy where both sides see it
# (this is also what install.sh does for curl installs).
SOURCE_DIR="$HOME/.local/share/touchdesigner-linux/source"
if [ ! -f "$SOURCE_DIR/td-install" ]; then
    echo "Cloning repo into $SOURCE_DIR (shared with the container)..."
    mkdir -p "$(dirname "$SOURCE_DIR")"
    git clone --depth 1 https://github.com/ismail-bahloul/TouchDesigner-Linux.git "$SOURCE_DIR"
fi

echo ""
echo "=== 1. Bootstrap container (td-install --container --diagnose) ==="
"$SOURCE_DIR/td-install" --container --diagnose --non-interactive

echo ""
echo "=== 2. Dry-run install inside the container ==="
"$SOURCE_DIR/td-install" --container --install --dry-run --headless --non-interactive

echo ""
echo "=== 3. Static test suite inside the container ==="
distrobox enter touchdesigner-linux -- python3 "$SOURCE_DIR/tests/test_static.py"

echo ""
echo "=== 4. Cleanup: remove the test container ==="
"$SOURCE_DIR/td-install" --container-remove --non-interactive

echo ""
echo "=== Tests complete ==="
