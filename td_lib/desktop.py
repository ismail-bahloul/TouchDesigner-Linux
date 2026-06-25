"""Desktop integration: shortcuts, icons, MIME types, font fix."""

import os
import re
import shutil
import subprocess

from .touchdesigner import discover_installed_versions
from .utils import (
    TD_BASE_DIR,
    download_file,
    ensure_dir,
    info,
    run_optional,
    success,
    warning,
)
from .wine import WINE_PREFIX

# ── Paths ────────────────────────────────────────────────────────────────────

DESKTOP_DIR = os.path.expanduser(
    os.environ.get(
        "DESKTOP_DIR",
        subprocess.run(
            ["xdg-user-dir", "DESKTOP"], capture_output=True, text=True
        ).stdout.strip()
        or os.path.expanduser("~/Desktop"),
    )
)

APPLICATIONS_DIR = os.path.expanduser("~/.local/share/applications")
LAUNCHER_PATH = os.path.expanduser("~/.local/bin/launch-touchdesigner.sh")
MIME_DIR = os.path.expanduser("~/.local/share/mime/packages")
MIME_ICON_DIR = os.path.expanduser("~/.local/share/icons/hicolor/scalable/mimetypes")

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ASSETS_URL = (
    "https://raw.githubusercontent.com/iswad-lab/TouchDesigner-Linux/main/Assets"
)


# ── Icons ────────────────────────────────────────────────────────────────────


def install_icons() -> str:
    """Install SVG icons for TouchDesigner, .toe, .tox files.
    Returns the path to the main TouchDesigner icon."""
    icon_path = "touchdesigner"  # fallback icon name
    ensure_dir(TD_BASE_DIR)

    # Main TouchDesigner app icon
    local_svg = os.path.join(SCRIPT_DIR, "Assets", "Icons", "TouchDesigner.svg")
    dest_svg = os.path.join(TD_BASE_DIR, "TouchDesigner.svg")

    if os.path.isfile(local_svg):
        shutil.copy2(local_svg, dest_svg)
        icon_path = dest_svg
    elif download_file(
        f"{REPO_ASSETS_URL}/Icons/TouchDesigner.svg",
        dest_svg,
        "TouchDesigner.svg",
        show_progress=False,
    ):
        icon_path = dest_svg

    # MIME type icons (.toe, .tox)
    ensure_dir(MIME_ICON_DIR)
    for icon_name in ["TouchDesigner-toe", "TouchDesigner-tox"]:
        short_name = "toe" if "toe" in icon_name else "tox"
        local_icon = os.path.join(SCRIPT_DIR, "Assets", "Icons", f"{icon_name}.svg")
        dest_icon = os.path.join(MIME_ICON_DIR, f"{icon_name}.svg")

        if os.path.isfile(local_icon):
            shutil.copy2(local_icon, dest_icon)
        else:
            download_file(
                f"{REPO_ASSETS_URL}/Icons/{icon_name}.svg",
                dest_icon,
                f"{icon_name}.svg",
                show_progress=False,
            )

        # Copy to TD_BASE_DIR too
        shutil.copy2(dest_icon, os.path.join(TD_BASE_DIR, f"{short_name}.svg"))

    return icon_path


# ── Desktop shortcuts ────────────────────────────────────────────────────────


def create_shortcuts(icon_path: str) -> None:
    """Create desktop + application menu shortcuts."""
    ensure_dir(DESKTOP_DIR)
    ensure_dir(APPLICATIONS_DIR)

    # Remove existing shortcuts to avoid duplicates
    for d in [DESKTOP_DIR, APPLICATIONS_DIR]:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.startswith("TouchDesigner") or f.startswith("touchdesigner"):
                if f.endswith(".desktop"):
                    os.remove(os.path.join(d, f))

    # Desktop shortcut
    desktop_file = os.path.join(DESKTOP_DIR, "TouchDesigner.desktop")
    _write_desktop_file(desktop_file, icon_path, LAUNCHER_PATH)
    _trust_desktop_file(desktop_file)

    # Application menu shortcut
    app_file = os.path.join(APPLICATIONS_DIR, "touchdesigner.desktop")
    _write_desktop_file(app_file, icon_path, LAUNCHER_PATH)

    _update_desktop_database()

    success(f"Shortcuts created (Desktop + Application menu)")


def create_versioned_shortcuts(icon_path: str) -> None:
    """Create version-specific shortcuts when 2+ versions are installed."""
    versions = discover_installed_versions()
    if len(versions) < 2:
        return

    for install_dir, version in versions:
        safe_version = re.sub(r"[^a-zA-Z0-9._-]", "-", version)
        label = f"TouchDesigner {version}"
        td_exe = os.path.join(install_dir, "bin", "TouchDesigner.exe")
        if not os.path.isfile(td_exe):
            td_exe = os.path.join(install_dir, "TouchDesigner.exe")
        if not os.path.isfile(td_exe):
            continue

        exec_cmd = f'{LAUNCHER_PATH} --exe "{td_exe}"'

        # Desktop
        desktop_file = os.path.join(
            DESKTOP_DIR, f"TouchDesigner-{safe_version}.desktop"
        )
        _write_desktop_file(
            desktop_file,
            icon_path,
            exec_cmd,
            name=label,
            comment=f"Version {version}",
        )
        _trust_desktop_file(desktop_file)

        # Application menu
        app_file = os.path.join(
            APPLICATIONS_DIR, f"touchdesigner-{safe_version}.desktop"
        )
        _write_desktop_file(
            app_file,
            icon_path,
            exec_cmd,
            name=label,
            comment=f"Version {version}",
        )

    _update_desktop_database()


def _write_desktop_file(
    path: str,
    icon: str,
    exec_cmd: str,
    name: str = "TouchDesigner",
    comment: str = "Real-time visual development platform",
) -> None:
    """Write a .desktop file."""
    content = (
        "[Desktop Entry]\n"
        "Version=1.0\n"
        "Type=Application\n"
        f"Name={name}\n"
        f"Comment={comment}\n"
        f"Exec={exec_cmd}\n"
        f"Icon={icon}\n"
        "Terminal=false\n"
        "StartupNotify=true\n"
        "Categories=Graphics;\n"
    )
    with open(path, "w") as f:
        f.write(content)
    os.chmod(path, 0o755)


def _trust_desktop_file(path: str) -> None:
    """Mark a .desktop file as trusted (GNOME/KDE)."""
    if not os.path.isfile(path):
        return
    if shutil.which("gio"):
        subprocess.run(
            ["gio", "set", path, "metadata::trusted", "true"],
            capture_output=True,
        )


def _update_desktop_database() -> None:
    """Update the desktop database if available."""
    if shutil.which("update-desktop-database"):
        subprocess.run(
            ["update-desktop-database", APPLICATIONS_DIR],
            capture_output=True,
        )


# ── MIME types (file associations) ──────────────────────────────────────────


def register_mime_types() -> None:
    """Register .toe and .tox MIME types and associate with TouchDesigner."""
    ensure_dir(MIME_DIR)

    # Write MIME XML
    mime_xml = os.path.join(MIME_DIR, "touchdesigner.xml")
    with open(mime_xml, "w") as f:
        f.write(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">\n'
            '  <mime-type type="application/x-touchdesigner-toe">\n'
            "    <comment>TouchDesigner project file</comment>\n"
            '    <glob pattern="*.toe" priority="100"/>\n'
            '    <icon name="TouchDesigner-toe"/>\n'
            "  </mime-type>\n"
            '  <mime-type type="application/x-touchdesigner-tox">\n'
            "    <comment>TouchDesigner component file</comment>\n"
            '    <glob pattern="*.tox" priority="100"/>\n'
            '    <icon name="TouchDesigner-tox"/>\n'
            "  </mime-type>\n"
            "</mime-info>\n"
        )

    # Update MIME database
    if shutil.which("update-mime-database"):
        subprocess.run(
            ["update-mime-database", os.path.dirname(MIME_DIR)],
            capture_output=True,
        )


def associate_files() -> None:
    """Associate .toe/.tox files with TouchDesigner launcher."""
    register_mime_types()
    ensure_dir(APPLICATIONS_DIR)

    # File handler desktop entry
    file_handler = os.path.join(APPLICATIONS_DIR, "touchdesigner-file.desktop")
    with open(file_handler, "w") as f:
        f.write(
            "[Desktop Entry]\n"
            "Version=1.0\n"
            "Type=Application\n"
            "Name=TouchDesigner\n"
            f"Exec={LAUNCHER_PATH} %u\n"
            "MimeType=application/x-touchdesigner-toe;application/x-touchdesigner-tox;\n"
            "NoDisplay=true\n"
            "Icon=TouchDesigner\n"
            "StartupNotify=true\n"
            "Categories=Graphics;\n"
        )

    # Set default application
    if shutil.which("xdg-mime"):
        subprocess.run(
            [
                "xdg-mime",
                "default",
                "touchdesigner-file.desktop",
                "application/x-touchdesigner-toe",
            ],
            capture_output=True,
        )
        subprocess.run(
            [
                "xdg-mime",
                "default",
                "touchdesigner-file.desktop",
                "application/x-touchdesigner-tox",
            ],
            capture_output=True,
        )

    success(".toe and .tox files associated with TouchDesigner")


# ── Font fix (wine_ui_fixes.tox) ────────────────────────────────────────────


def install_font_fix() -> str | None:
    """Install wine_ui_fixes.tox to TD_BASE_DIR.
    Returns the path to the .tox file, or None if not found."""
    dest = os.path.join(TD_BASE_DIR, "wine_ui_fixes.tox")
    ensure_dir(TD_BASE_DIR)

    # Try local copies first
    for src in [
        os.path.join(SCRIPT_DIR, "wine_ui_fixes.tox"),
        os.path.join(SCRIPT_DIR, "Assets", "wine_ui_fixes.tox"),
    ]:
        if os.path.isfile(src):
            shutil.copy2(src, dest)
            return dest

    # Download from repo
    if download_file(
        f"{REPO_ASSETS_URL}/wine_ui_fixes.tox",
        dest,
        "wine_ui_fixes.tox",
        show_progress=False,
        timeout=20,
        retries=2,
    ):
        return dest

    safe_rm(dest)
    return None


def distribute_font_fix() -> list[str]:
    """Copy wine_ui_fixes.tox to Wine-visible locations.
    Returns a list of installed locations."""
    src = os.path.join(TD_BASE_DIR, "wine_ui_fixes.tox")
    if not os.path.isfile(src):
        return []

    locations = [src]
    drive_c = os.path.join(WINE_PREFIX, "drive_c")
    if not os.path.isdir(drive_c):
        return locations

    # Wine Desktop
    wine_desktop = os.path.join(drive_c, "users", "steamuser", "Desktop")
    ensure_dir(os.path.dirname(wine_desktop))
    dest1 = os.path.join(wine_desktop, "wine_ui_fixes.tox")
    shutil.copy2(src, dest1)
    locations.append(dest1)

    # Wine Palette
    wine_palette = os.path.join(
        drive_c, "users", "steamuser", "Documents", "Derivative", "Palette"
    )
    ensure_dir(os.path.dirname(wine_palette))
    dest2 = os.path.join(wine_palette, "wine_ui_fixes.tox")
    shutil.copy2(src, dest2)
    locations.append(dest2)

    return locations


# ── Full integration ─────────────────────────────────────────────────────────


def run_desktop_integration(
    create_shortcuts_flag: bool = True,
    associate_flag: bool = True,
) -> None:
    """Run all desktop integration steps."""
    # Install icons
    info("Installing icons...")
    icon_path = install_icons()
    if icon_path != "touchdesigner":
        info(f"Icon installed: {icon_path}")

    # Shortcuts
    if create_shortcuts_flag:
        info("Creating shortcuts...")
        create_shortcuts(icon_path)
        create_versioned_shortcuts(icon_path)

    # Font fix
    info("Installing font/UI fix...")
    fix_path = install_font_fix()
    if fix_path:
        distribute_font_fix()

    # File associations
    if associate_flag:
        info("Associating .toe & .tox files...")
        associate_files()
