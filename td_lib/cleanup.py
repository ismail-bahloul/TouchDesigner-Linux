"""Cleanup and uninstall workflows."""

import os
import shutil
import subprocess

from .launcher import LAUNCHER_PATH
from .touchdesigner import detect_version_from_exe, discover_installed_versions
from .utils import (
    TD_BASE_DIR,
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
    or os.path.expanduser("~/Desktop")
)
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
            for f in os.listdir(d):
                if f.startswith("TouchDesigner-") and f.endswith(".desktop"):
                    safe_rm(os.path.join(d, f))
                if f.startswith("touchdesigner-") and f[14:].lstrip("-")[0:1].isdigit():
                    safe_rm(os.path.join(d, f))

    return removed


# ── Full uninstall ───────────────────────────────────────────────────────────


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


def show_uninstall_menu() -> None:
    """Show interactive uninstall menu for selecting versions or full removal."""
    import sys

    versions = discover_installed_versions()
    print_banner("1.4")
    print("\nUninstall TouchDesigner:\n")

    if not versions:
        warning("No installed TouchDesigner versions detected")
        print("\n  1  Uninstall everything (prefix, runner, launcher, desktop entries)")
        print("  0  Cancel\n")

        try:
            choice = input("Select option [0]: ").strip() or "0"
        except (EOFError, KeyboardInterrupt):
            choice = "0"

        if choice == "1":
            uninstall_everything()
        else:
            info("Uninstall cancelled")
        return

    print("Detected versions in Wine prefix:\n")
    for i, (install_dir, version) in enumerate(versions, 1):
        pretty = install_dir.replace(WINE_PREFIX + "/drive_c/", "")
        label = f"TouchDesigner {version}" if version != "unknown" else "TouchDesigner"
        print(f"  {i}  {label}")
        print(f"      {pretty}")

    print(
        f"\n  {len(versions) + 1}  Uninstall EVERYTHING (prefix, runner, launcher, desktop entries)"
    )
    print("\n  0  Cancel\n")

    try:
        selection = (
            input("Select one or multiple versions (e.g. 1,3) [0]: ").strip() or "0"
        )
    except (EOFError, KeyboardInterrupt):
        selection = "0"

    if selection == "0":
        info("Uninstall cancelled")
        return

    if selection == str(len(versions) + 1):
        uninstall_everything()
        return

    # Parse multi-selection
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


# ── CLI entrypoint ───────────────────────────────────────────────────────────


def run_uninstall(args) -> None:
    """Entrypoint for --uninstall."""
    show_uninstall_menu()
