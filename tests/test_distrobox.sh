#!/bin/bash
# Distrobox test — run TouchDesigner-Linux V2 in an isolated container
# Usage: bash tests/test_distrobox.sh

set -e

echo "=== TouchDesigner-Linux V2 — Distrobox Test ==="
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

CONTAINER_NAME="td-test-v2"
IMAGE="${1:-ubuntu:24.04}"

echo "Creating container: $CONTAINER_NAME ($IMAGE)"
echo ""

# Create container if not exists
if ! distrobox list 2>/dev/null | grep -q "$CONTAINER_NAME"; then
    distrobox create \
        --name "$CONTAINER_NAME" \
        --image "$IMAGE" \
        --additional-flags "--security-opt label=disable"
fi

# Enter and test
distrobox enter "$CONTAINER_NAME" -- bash -c '
    set -e
    echo ""
    echo "=== Inside container ==="

    # Install deps
    sudo apt-get update
    sudo apt-get install -y curl wget p7zip-full innoextract python3 xz-utils cabextract unzip file

    # Clone or copy
    if [ ! -d /opt/touchdesigner-linux ]; then
        sudo git clone https://github.com/iswad-lab/TouchDesigner-Linux.git /opt/touchdesigner-linux
    fi
    cd /opt/touchdesigner-linux

    # Switch to python-rewrite branch
    sudo git checkout python-rewrite

    echo ""
    echo "=== Running static tests ==="
    python3 tests/test_static.py

    echo ""
    echo "=== Dry-run install ==="
    ./tact --install --dry-run

    echo ""
    echo "=== Diagnose ==="
    ./tact --diagnose

    echo ""
    echo "=== Tests complete ==="
'
