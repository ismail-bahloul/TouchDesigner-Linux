r"""Native external editor support for TouchDesigner under Wine.

TouchDesigner has a built-in preference (in DATs preferences) to set an
external text editor. When pressing Ctrl+E on a Text DAT, TD passes the
file path to this editor. This module sets that preference to use
winebrowser.exe, which is Wine's official bridge to native Linux desktop
applications via xdg-open.

How it works:
1. TouchDesigner stores preferences in pref.txt. We set the key
   dats.texteditor to C:\windows\system32\winebrowser.exe
2. When TouchDesigner calls the editor (Ctrl+E), it runs winebrowser.exe
   with the temp file path, which calls xdg-open on the Linux side.
3. xdg-open opens the file in the user's default text editor.
4. The user configures their preferred editor via xdg-mime:
   - VSCode:       xdg-mime default code.desktop text/plain
   - Codium:       xdg-mime default codium.desktop text/plain
   - Sublime Text: xdg-mime default sublime-text.desktop text/plain
   - Or any other editor registered via xdg-mime.

A convenience script (td-editor) is also installed in ~/.local/bin/ for
manual use on the Linux side, respecting TD_EDITOR or EDITOR env vars.
"""

import os
import shutil

from .utils import TD_BASE_DIR, ensure_dir, info, success, warning
from .wine import WINE_PREFIX

# TD pref.txt uses tab-separated key\tvalue format
PREF_KEY = "dats.texteditor"
PREF_VALUE = r"C:\windows\system32\winebrowser.exe"

# Fallback for AUR installs
AUR_PREFIX = os.path.expanduser("~/.local/share/touchdesigner-linux/prefix")


def _find_prefix() -> str:
    """Find the Wine prefix directory."""
    if os.path.isdir(os.path.join(WINE_PREFIX, "drive_c")):
        return WINE_PREFIX
    if os.path.isdir(os.path.join(AUR_PREFIX, "drive_c")):
        return AUR_PREFIX
    return WINE_PREFIX


def _pref_path() -> str | None:
    """Get the path to TouchDesigner's pref.txt file."""
    prefix = _find_prefix()
    # Common pref locations for different TD versions
    candidates = [
        os.path.join(
            prefix,
            "drive_c",
            "users",
            "steamuser",
            "AppData",
            "Local",
            "Derivative",
            "TouchDesigner099",
            "pref.txt",
        ),
        os.path.join(
            prefix,
            "drive_c",
            "users",
            "steamuser",
            "AppData",
            "Local",
            "Derivative",
            "TouchDesigner",
            "pref.txt",
        ),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    # If no pref file exists yet, create it at the most likely location
    ensure_dir(os.path.dirname(candidates[0]))
    return candidates[0]


def _apply_pref() -> bool:
    """Write winebrowser.exe as the external text editor in pref.txt.

    TouchDesigner's pref.txt uses tab-separated format:
        key\tvalue
    """
    pref_path = _pref_path()
    if not pref_path:
        warning("Could not determine pref.txt path")
        return False

    try:
        # Read existing pref if it exists
        lines = []
        found = False
        sep = "\t"  # TD uses tab separator in pref.txt
        if os.path.isfile(pref_path):
            with open(pref_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith(PREF_KEY + sep) or stripped.startswith(
                        PREF_KEY + "="
                    ):
                        lines.append(f"{PREF_KEY}{sep}{PREF_VALUE}\n")
                        found = True
                    else:
                        lines.append(line)

        # If key wasn't found, add it
        if not found:
            lines.append(f"{PREF_KEY}{sep}{PREF_VALUE}\n")

        with open(pref_path, "w", encoding="utf-8", newline="\r\n") as f:
            f.writelines(lines)

        success(f"Editor preference set in pref.txt: {PREF_KEY} -> {PREF_VALUE}")
        return True

    except OSError as e:
        warning(f"Failed to write editor preference: {e}")
        return False


def _install_td_editor_script() -> str | None:
    """Install the td-editor Linux wrapper script in ~/.local/bin/.

    This script allows users to open files from the terminal with the
    configured editor. It respects the TD_EDITOR environment variable
    (or EDITOR as fallback, or xdg-open as default).

    Usage: td-editor <file_path>

    Returns the path to the installed script, or None on failure.
    """
    bin_dir = os.path.expanduser("~/.local/bin")
    ensure_dir(bin_dir)

    editor_path = os.path.join(bin_dir, "td-editor")

    content = """#!/bin/bash
# TouchDesigner Linux Editor Bridge
# Opens a file in the configured Linux editor.
# Usage: td-editor <file_path>
#
# Configuration (in order of precedence):
#   TD_EDITOR environment variable (e.g. TD_EDITOR=code)
#   EDITOR environment variable
#   Default: xdg-open

TD_EDITOR="${TD_EDITOR:-${EDITOR:-xdg-open}}"

if [ $# -eq 0 ]; then
    echo "Usage: td-editor <file_path>" >&2
    exit 1
fi

FILE_PATH="$1"

# Handle Wine-style paths (z: or Z: prefix)
case "$FILE_PATH" in
    [zZ]:*)
        FILE_PATH="${FILE_PATH#??}"
        if command -v winepath &>/dev/null; then
            CONVERTED=$(winepath -u "$FILE_PATH" 2>/dev/null)
            [ -n "$CONVERTED" ] && FILE_PATH="$CONVERTED"
        fi
        ;;
    [cCdD]:*)
        # Drive letter path - try winepath
        if command -v winepath &>/dev/null; then
            CONVERTED=$(winepath -u "$FILE_PATH" 2>/dev/null)
            [ -n "$CONVERTED" ] && FILE_PATH="$CONVERTED"
        fi
        ;;
esac

if [ ! -f "$FILE_PATH" ]; then
    echo "td-editor: File not found: $FILE_PATH" >&2
    exit 1
fi

# Launch editor in background (detached, non-blocking)
exec nohup "$TD_EDITOR" "$FILE_PATH" &>/dev/null &
"""

    try:
        with open(editor_path, "w") as f:
            f.write(content)
        os.chmod(editor_path, 0o755)
        success(f"td-editor script installed: {editor_path}")
        return editor_path
    except OSError as e:
        warning(f"Failed to install td-editor script: {e}")
        return None


def _restore_notepad_backup() -> None:
    """Restore the original Wine notepad.exe if we replaced it earlier.
    Cleanup from the previous approach.
    """
    prefix = _find_prefix()
    win_dir = os.path.join(prefix, "drive_c", "windows")
    notepad_path = os.path.join(win_dir, "notepad.exe")
    backup_path = os.path.join(win_dir, "notepad.exe.td-bak")

    if os.path.isfile(backup_path):
        try:
            shutil.copy2(backup_path, notepad_path)
            os.unlink(backup_path)
            info("Restored original Wine notepad.exe")
        except OSError:
            pass


def setup_native_editor() -> bool:
    """Set up the native external editor bridge for TouchDesigner.

    This is the main entry point called during install/update.
    It:
    1. Restores the original Wine notepad.exe (cleanup from old approach)
    2. Installs the td-editor Linux wrapper in ~/.local/bin/
    3. Writes the editor preference in TouchDesigner's pref.txt
    4. Prints configuration hints for the user

    Returns True on success.
    """
    info("Setting up native external editor support...")

    prefix = _find_prefix()
    if not os.path.isdir(os.path.join(prefix, "drive_c")):
        warning(
            "Wine environment not fully set up yet."
            " Editor bridge will be configured after Wine is installed."
        )
        return False

    # Cleanup: restore original notepad.exe from previous approach
    _restore_notepad_backup()

    # Install td-editor convenience script
    _install_td_editor_script()

    # Write editor preference in pref.txt
    if not _apply_pref():
        return False

    _show_editor_info()

    success("Native external editor support configured")
    return True


def _show_editor_info() -> None:
    """Print configuration hints for the user."""
    info("")
    info("Native external editor support is configured!")
    info("")
    info("  TouchDesigner will now open Text DATs in your Linux editor")
    info("  when you press Ctrl+E.")
    info("")
    info("  Your default text editor is determined by xdg-mime.")
    info("  To use a specific editor, run in a terminal:")
    info("    VSCode:       xdg-mime default code.desktop text/plain")
    info("    Codium:       xdg-mime default codium.desktop text/plain")
    info("    Sublime Text: xdg-mime default sublime-text.desktop text/plain")
    info("    Kate:         xdg-mime default kate.desktop text/plain")
    info("    Gedit:        xdg-mime default org.gnome.gedit.desktop text/plain")
    info("    VSCodium:     xdg-mime default vscodium.desktop text/plain")
    info("")
    info("  Or set TD_EDITOR in ~/.bashrc:")
    info('    export TD_EDITOR="code"')
    info("")
    info("  The editor preference is stored in TD's pref.txt.")
    info("  You can also change it manually in TD: Edit > Preferences > DATs")


def remove_editor_config() -> None:
    """Remove the editor bridge configuration from the Wine prefix.

    Called during uninstall. Removes the editor preference from pref.txt
    and removes the td-editor script.
    """
    # Remove editor preference from pref.txt
    pref_path = _pref_path()
    if pref_path and os.path.isfile(pref_path):
        try:
            lines = []
            with open(pref_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped.startswith(PREF_KEY + "\t") and not stripped.startswith(
                        PREF_KEY + "="
                    ):
                        lines.append(line)
            with open(pref_path, "w", encoding="utf-8", newline="\r\n") as f:
                f.writelines(lines)
            info("Editor preference removed from pref.txt")
        except OSError:
            pass

    # Remove td-editor script
    editor_script = os.path.expanduser("~/.local/bin/td-editor")
    if os.path.isfile(editor_script):
        try:
            os.unlink(editor_script)
            info("td-editor script removed")
        except OSError:
            pass

    success("Native external editor configuration removed")
