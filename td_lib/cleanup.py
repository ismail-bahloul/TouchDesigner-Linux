"""Cleanup and uninstall workflows."""

import os
import re
import shutil
import subprocess

from . import __version__
from .launcher import LAUNCHER_PATH
from .touchdesigner import detect_version_from_exe, discover_installed_versions
from .utils import (
    TD_BASE_DIR,
    Colors,
    error,
    info,
    print_banner,
    print_hr,
    safe_rm,
    success,
    warning,
)
from .wine import WINE_PREFIX

DESKTOP_DIR = os.path.expanduser(
    subprocess.run(
        ["xdg-user-dir", "DESKTOP"], capture_output=True, text=True
    ).stdout.strip()
    if shutil.which("xdg-user-dir")
    else "",
) or os.path.expanduser("~/Desktop")
APPLICATIONS_DIR = os.path.expanduser("~/.local/share/applications")
MIME_ICON_DIR = os.path.expanduser("~/.local/share/icons/hicolor/scalable/mimetypes")
MIME_DIR = os.path.expanduser("~/.local/share/mime/packages")


# ── Uninstall single versions ───────────────────────────────────────────────


def uninstall_selected_versions(selected_roots: list[str]) -> int:
    """Remove selected TouchDesigner version directories.
    Returns the number of successfully removed versions."""
    removed = 0

    for root in selected_roots:
        if not os.path.isdir(root):
            warning(f"Already missing: {root}")
            continue

        pretty = root.replace(WINE_PREFIX + "/drive_c/", "")
        info(f"Removing: {pretty}")
        safe_rm(root)
        removed += 1

        # Remove version-specific shortcuts
        version = detect_version_from_exe(
            os.path.join(root, "bin", "TouchDesigner.exe")
        )
        if version:
            safe_version = re.sub(r"[^a-zA-Z0-9._-]", "-", version)
            for d in [DESKTOP_DIR, APPLICATIONS_DIR]:
                for f in [
                    f"TouchDesigner-{safe_version}.desktop",
                    f"touchdesigner-{safe_version}.desktop",
                ]:
                    path = os.path.join(d, f)
                    if os.path.isfile(path):
                        safe_rm(path)

    # If <= 1 version remains, remove all version-specific shortcuts
    remaining = discover_installed_versions()
    if len(remaining) <= 1:
        for d in [DESKTOP_DIR, APPLICATIONS_DIR]:
            if not os.path.isdir(d):
                continue
            for f in os.listdir(d):
                if f.startswith("TouchDesigner-") and f.endswith(".desktop"):
                    safe_rm(os.path.join(d, f))
                if f.startswith("touchdesigner-") and f[14:].lstrip("-")[0:1].isdigit():
                    safe_rm(os.path.join(d, f))

    return removed


# ── Full uninstall ───────────────────────────────────────────────────────────

# License activation lives in the shared prefix, so only a full uninstall deletes it.
LICENSE_DIR = os.path.join(WINE_PREFIX, "drive_c", "ProgramData", "Derivative")


def _warn_license_loss() -> None:
    """Warn when a full uninstall will delete the TouchDesigner license activation."""
    if not os.path.isdir(LICENSE_DIR):
        return
    warning(
        "This will delete your TouchDesigner license activation "
        "(drive_c/ProgramData/Derivative/ins*.dat)"
    )
    info("You will need to re-enter your license key after reinstalling.")


def uninstall_everything() -> None:
    """Completely remove TouchDesigner, runner, prefix, launcher, desktop entries."""
    info("Removing centralised backups...")
    backups = os.path.join(TD_BASE_DIR, "backups")
    if os.path.isdir(backups):
        safe_rm(backups)
        success("Centralised backups removed")

    info("Removing Wine prefix and runner...")
    if os.path.isdir(TD_BASE_DIR):
        safe_rm(TD_BASE_DIR)
        success("Wine prefix and runner removed")

    info("Removing launcher script...")
    for path in [LAUNCHER_PATH, os.path.expanduser("~/launch-touchdesigner.sh")]:
        if os.path.isfile(path):
            safe_rm(path)
            success(f"Launcher removed: {path}")

    info("Removing desktop shortcuts...")
    for d in [DESKTOP_DIR, APPLICATIONS_DIR]:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.startswith("TouchDesigner") and f.endswith(".desktop"):
                safe_rm(os.path.join(d, f))
            if f.startswith("touchdesigner") and f.endswith(".desktop"):
                safe_rm(os.path.join(d, f))
    success("Desktop shortcuts removed")

    info("Removing MIME types and icons...")
    mime_xml = os.path.join(MIME_DIR, "touchdesigner.xml")
    if os.path.isfile(mime_xml):
        safe_rm(mime_xml)
        if shutil.which("update-mime-database"):
            subprocess.run(
                ["update-mime-database", os.path.dirname(MIME_DIR)],
                capture_output=True,
            )
        success("MIME types removed")

    for icon in ["TouchDesigner-toe.svg", "TouchDesigner-tox.svg"]:
        path = os.path.join(MIME_ICON_DIR, icon)
        if os.path.isfile(path):
            safe_rm(path)

    # Remove editor bridge configuration
    try:
        from .editor import remove_editor_config
        remove_editor_config()
    except ImportError:
        pass

    _update_desktop_database()
    print_hr()
    success("Uninstall Complete")
    info("TouchDesigner has been completely removed.")


def _update_desktop_database() -> None:
    """Update desktop database if available."""
    if shutil.which("update-desktop-database"):
        subprocess.run(
            ["update-desktop-database", APPLICATIONS_DIR],
            capture_output=True,
        )


# ── Interactive menu ─────────────────────────────────────────────────────────


def _process_uninstall_text_selection(selection: str, versions: list) -> None:
    """Handle text-based uninstall selection (non-TTY fallback)."""
    if selection == "0":
        info("Uninstall cancelled")
        return

    if selection == str(len(versions) + 1):
        _warn_license_loss()
        uninstall_everything()
        return

    selected_roots: list[str] = []
    for token in selection.replace(",", " ").split():
        if not token.isdigit():
            error(f"Invalid selection: {token}")
            return
        idx = int(token) - 1
        if idx < 0 or idx >= len(versions):
            error(f"Selection out of range: {token}")
            return
        root = versions[idx][0]
        if root not in selected_roots:
            selected_roots.append(root)

    if not selected_roots:
        warning("No versions selected")
        return

    try:
        confirm = (
            input(f"Remove {len(selected_roots)} selected version(s)? [Y/n]: ")
            .strip()
            .lower()
        )
    except (EOFError, KeyboardInterrupt):
        confirm = "n"

    if confirm in ("y", "yes", ""):
        removed = uninstall_selected_versions(selected_roots)
        success(f"Removed {removed} TouchDesigner version(s)")
    else:
        info("Uninstall cancelled")


def show_uninstall_menu() -> bool:
    """Show interactive uninstall menu for selecting versions or full removal.

    Returns True if something was actually done (version removed, everything nuked).
    Returns False if the user cancelled (Back) or no action was taken.
    """
    import sys
    import termios
    import tty

    versions = discover_installed_versions()
    if sys.stdout.isatty():
        print("\033[2J\033[H", end="")
    print_banner(__version__)
    print(f"\n{Colors.bold}{Colors.white}Uninstall TouchDesigner{Colors.nc}\n")

    if not versions:
        warning("No installed TouchDesigner versions detected")
        print("\n  1  Uninstall everything (prefix, runner, launcher, desktop entries)")
        print("  0  Cancel\n")

        try:
            choice = input("Select option [0]: ").strip() or "0"
        except (EOFError, KeyboardInterrupt):
            choice = "0"

        if choice == "1":
            _warn_license_loss()
            uninstall_everything()
            return True
        else:
            info("Uninstall cancelled")
            return False

    print(f"\nDetected versions in Wine prefix:\n")

    # Build options list: versions + Uninstall Everything + Cancel
    options = []
    for install_dir, version in versions:
        pretty = install_dir.replace(WINE_PREFIX + "/drive_c/", "")
        label = f"TouchDesigner {version}" if version != "unknown" else "TouchDesigner"
        options.append(("version", label, pretty, install_dir))
    options.append(
        (
            "everything",
            "Uninstall EVERYTHING",
            "prefix, runner, launcher, desktop entries, TD license",
            None,
        )
    )
    options.append(("cancel", "Back", None, None))

    total_opts = len(options)
    cursor = 0

    # Fall back to text input when not a TTY
    if not sys.stdin.isatty():
        for i, (typ, label, desc, _) in enumerate(options):
            num = str(i + 1) if typ != "cancel" else "0"
            print(f"  {num}. {label}")
            if desc:
                print(f"     {Colors.accent}{desc}{Colors.nc}")
            print()
        try:
            selection = (
                input("Select one or multiple versions (e.g. 1,3) [0]: ").strip() or "0"
            )
        except (EOFError, KeyboardInterrupt):
            selection = "0"
        _process_uninstall_text_selection(selection, versions)
        return False

    def _draw_versions():
        lines = []
        for i, (typ, label, desc, _) in enumerate(options):
            num = str(i + 1) if typ != "cancel" else "0"
            marker = "▶" if i == cursor else " "
            lines.append(f"  {marker}  {num}. {label}")
            if desc:
                lines.append(f"     {Colors.accent}{desc}{Colors.nc}")
            lines.append("")
        return lines

    lines = _draw_versions()
    sys.stdout.write("\033[?25l")  # Hide cursor
    sys.stdout.flush()
    for line in lines:
        print(line)
    print_count = len(lines)

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        new = termios.tcgetattr(fd)
        new[tty.LFLAG] &= ~(termios.ICANON | termios.ECHO)
        new[tty.CC][termios.VMIN] = 1
        new[tty.CC][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSADRAIN, new)

        while True:
            try:
                key = sys.stdin.read(1)
            except (EOFError, KeyboardInterrupt):
                key = "\x03"

            if key == "\x03":
                info("\nUninstall cancelled")
                sys.stdout.write("\033[?25h")
                return False

            if key == "\x1b":
                seq = ""
                try:
                    seq = sys.stdin.read(2)
                except (EOFError, OSError):
                    pass
                if seq == "[A":
                    cursor = (cursor - 1) % total_opts
                elif seq == "[B":
                    cursor = (cursor + 1) % total_opts
            elif key in ("\r", "\n"):
                typ = options[cursor][0]
                if typ == "cancel":
                    break
                elif typ == "everything":
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    sys.stdout.write("\033[?25h")
                    print()
                    _warn_license_loss()
                    confirm = (
                        input(f"Remove everything? [Y/n]: ").strip().lower() or "y"
                    )
                    if confirm in ("y", "yes"):
                        uninstall_everything()
                        return True
                    return False
                elif typ == "version":
                    install_dir = options[cursor][3]
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    sys.stdout.write("\033[?25h")
                    print()
                    confirm = (
                        input(f"Remove this version? [Y/n]: ").strip().lower() or "y"
                    )
                    if confirm in ("y", "yes"):
                        uninstall_selected_versions([install_dir])
                        return True
                    return False

            # Redraw
            lines = _draw_versions()
            for _ in range(print_count):
                sys.stdout.write("\033[A")
            for line in lines:
                sys.stdout.write(f"\033[K{line}\n")
            sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

    # Print cancelled message AFTER terminal restoration
    print()
    info("Uninstall cancelled")
    return False


# ── CLI entrypoint ───────────────────────────────────────────────────────────


def run_uninstall(args) -> bool:
    """Entrypoint for --uninstall. Returns True if something was removed."""
    return show_uninstall_menu()
