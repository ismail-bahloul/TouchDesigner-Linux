#!/bin/bash
# TouchDesigner-Linux — Automated installer for TouchDesigner on Linux.
# This is a lightweight launcher that downloads and runs td-install (Python).
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/iswad-lab/TouchDesigner-Linux/main/install.sh | bash
#   bash install.sh
#   ./install.sh

set -e

REPO_URL="https://github.com/iswad-lab/TouchDesigner-Linux.git"
REPO_BRANCH="${TD_BRANCH:-main}"
INSTALL_DIR="${TD_INSTALL_DIR:-$HOME/.local/share/touchdesigner-linux}"

# Check for Linux
if [ "$(uname)" != "Linux" ]; then
    echo "Error: This installer only supports Linux systems"
    exit 1
fi

# Check for git
if ! command -v git &>/dev/null; then
    echo "Error: git is required to download the installer."
    echo "Install git with your package manager, then re-run:"
    echo "  sudo pacman -S git      # Arch"
    echo "  sudo apt install git    # Debian/Ubuntu"
    echo "  sudo dnf install git    # Fedora"
    exit 1
fi

# Determine where the repo is
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd 2>/dev/null || pwd)"
if [ -f "$SCRIPT_DIR/td-install" ]; then
    # Running from a local clone
    TD_CLI="$SCRIPT_DIR/td-install"
else
    # Running from curl pipe — clone the repo
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
fi

# Reconnect stdin to terminal so interactive menus work through curl pipe
if [ -c /dev/tty ]; then
    exec "$TD_CLI" "$@" </dev/tty
else
    exec "$TD_CLI" "$@"
fi
