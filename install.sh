#!/bin/bash
# TouchDesigner-Linux — Automated installer for TouchDesigner on Linux.
# This is a lightweight launcher that downloads and runs td-install (Python).
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/ismail-bahloul/TouchDesigner-Linux/main/install.sh | bash
#   bash install.sh
#   ./install.sh

set -e

REPO_URL="https://github.com/ismail-bahloul/TouchDesigner-Linux.git"
REPO_BRANCH="${TD_BRANCH:-main}"
INSTALL_DIR="${TD_INSTALL_DIR:-$HOME/.local/share/touchdesigner-linux}"

# Check for Linux
if [ "$(uname)" != "Linux" ]; then
    echo "Error: This installer only supports Linux systems"
    exit 1
fi

# Determine where the repo is
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd 2>/dev/null || pwd)"
if [ -f "$SCRIPT_DIR/td-install" ]; then
    # Running from a local clone
    TD_CLI="$SCRIPT_DIR/td-install"
elif command -v git &>/dev/null; then
    # Running from curl pipe — clone the repo (keeps a cached, updatable copy)
    REPO_DIR="$INSTALL_DIR/source"
    if [ ! -d "$REPO_DIR/.git" ]; then
        echo "Downloading TouchDesigner-Linux..."
        mkdir -p "$(dirname "$REPO_DIR")"
        git clone --depth 1 --branch "$REPO_BRANCH" "$REPO_URL" "$REPO_DIR"
    else
        # Pull latest if already cloned. If the clone has diverged
        # (local commit or force-pushed history), a fast-forward fails and
        # the stale installer would silently run. The clone is only a
        # cache (prefix, licenses, backups live elsewhere), so hard-reset.
        cd "$REPO_DIR"
        git fetch origin "$REPO_BRANCH" 2>/dev/null || true
        if ! git merge --ff-only "origin/$REPO_BRANCH" 2>/dev/null; then
            git reset --hard "origin/$REPO_BRANCH" 2>/dev/null || true
        fi
    fi
    TD_CLI="$REPO_DIR/td-install"
    cd "$REPO_DIR"
else
    # No git — e.g. a fresh distrobox container ships curl/wget but not git.
    # Fall back to a plain tarball download (no cache; re-downloads each run).
    if ! command -v curl &>/dev/null && ! command -v wget &>/dev/null; then
        echo "Error: need git (or curl/wget) to download the installer."
        echo "Install git with your package manager, then re-run:"
        echo "  sudo apt install git    # Debian/Ubuntu"
        echo "  sudo dnf install git    # Fedora"
        echo "  sudo pacman -S git      # Arch"
        exit 1
    fi
    echo "git not found — downloading the installer tarball instead..."
    mkdir -p "$INSTALL_DIR"
    TARBALL_URL="https://github.com/ismail-bahloul/TouchDesigner-Linux/archive/refs/heads/${REPO_BRANCH}.tar.gz"
    TARBALL_PATH="$INSTALL_DIR/source.tar.gz"
    if command -v curl &>/dev/null; then
        curl -sSL "$TARBALL_URL" -o "$TARBALL_PATH" || { echo "Error: failed to download the installer."; exit 1; }
    else
        wget -qO "$TARBALL_PATH" "$TARBALL_URL" || { echo "Error: failed to download the installer."; exit 1; }
    fi
    mkdir -p "$INSTALL_DIR/source-tmp"
    tar -xzf "$TARBALL_PATH" -C "$INSTALL_DIR/source-tmp" --strip-components=1
    rm -f "$TARBALL_PATH"
    TD_CLI="$INSTALL_DIR/source-tmp/td-install"
    cd "$INSTALL_DIR/source-tmp"
fi

# Reconnect stdin to terminal so interactive menus work through curl pipe.
# /dev/tty can exist as a device node yet fail to open (no controlling
# terminal, e.g. inside a container) — test the open, not just the node.
if [ -c /dev/tty ] && { exec 3</dev/tty; } 2>/dev/null; then
    exec 3<&-
    exec "$TD_CLI" "$@" </dev/tty
else
    exec "$TD_CLI" "$@"
fi
