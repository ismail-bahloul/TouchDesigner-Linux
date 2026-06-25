"""TouchDesigner download, version selection, and installation."""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .utils import (
    TD_BASE_DIR,
    download_file,
    ensure_dir,
    error,
    info,
    run_optional,
    safe_rm,
    success,
    warning,
)
from .wine import WINE_PREFIX, WINETRICKS_TMP

# ── Constants ────────────────────────────────────────────────────────────────

ARCHIVE_URL = "https://derivative.ca/download/archive"
DOWNLOAD_DIR = os.path.expanduser(os.environ.get("DOWNLOAD_DIR", "~/Downloads"))
DOWNLOAD_DIR = os.path.expanduser(DOWNLOAD_DIR)

FALLBACK_VERSIONS = [
    "2025.32460",
    "2025.32280",
    "2025.32050",
    "2025.31760",
    "2025.31550",
    "2025.30000",
    "2024.10000",
    "2023.12120",
    "2022.33910",
]

TD_INSTALL_DIR = os.path.join(WINE_PREFIX, "drive_c", "Program Files", "TouchDesigner")

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"


# ── Version listing ──────────────────────────────────────────────────────────


def fetch_available_versions() -> list[str]:
    """Fetch available TouchDesigner versions from Derivative's website."""
    import tempfile

    info("Fetching available TouchDesigner versions...")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    tmp_path = tmp.name
    tmp.close()

    try:
        success = download_file(
            ARCHIVE_URL,
            tmp_path,
            "TouchDesigner archive index",
            show_progress=False,
            timeout=20,
            retries=1,
        )
    except Exception:
        success = False

    versions: list[str] = []

    if success:
        with open(tmp_path, errors="ignore") as f:
            content = f.read()
        matches = re.findall(r"20\d{2}\.\d{4,6}", content)
        versions = sorted(set(matches), reverse=True)
        os.unlink(tmp_path)

    if not versions:
        warning("Could not fetch live version list, using fallback")
        versions = list(FALLBACK_VERSIONS)

    # Limit to 10 versions
    return versions[:10]


def detect_version_from_exe(exe_path: str) -> str | None:
    """Extract version string from TouchDesigner.exe using `strings`."""
    strings = shutil.which("strings")
    if not strings:
        return None
    try:
        result = subprocess.run(
            [strings, exe_path], capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.splitlines():
            if "TouchDesigner" in line and "20" in line:
                parts = line.strip().split()
                for p in parts:
                    if re.match(r"^20\d{2}\.\d+", p):
                        return p
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        pass
    return None


def discover_installed_versions() -> list[tuple[str, str]]:
    """Return list of (install_dir, version) for each installed TD version."""
    drive_c = os.path.join(WINE_PREFIX, "drive_c")
    if not os.path.isdir(drive_c):
        return []

    results: list[tuple[str, str]] = []
    for root, dirs, files in os.walk(drive_c):
        for f in files:
            if f.lower() == "touchdesigner.exe":
                exe_path = os.path.join(root, f)
                version = detect_version_from_exe(exe_path)
                results.append((root, version or "unknown"))
    return results


# ── Version selection (interactive) ──────────────────────────────────────────


def select_version_interactive(versions: list[str]) -> str | None:
    """Show an interactive version picker. Returns the selected version or None to skip."""
    import sys
    import termios
    import tty

    installed_versions = {v for _, v in discover_installed_versions()}

    print(f"\n{'Available TouchDesigner versions':^60}")
    print(f"{'Use ↑ ↓ to navigate, Enter to select':^60}\n")

    count = len(versions)
    total = count + 2  # versions + "Use local installer" + "Skip"
    cursor = 0
    selected = None

    def _draw():
        nonlocal cursor
        lines = []
        prev_year = ""
        for i, v in enumerate(versions):
            year = v.split(".")[0]
            if year != prev_year:
                lines.append((None, f"  ── {year} ─────────────────────"))
                prev_year = year
            label = v
            if i == 0:
                label = f"{v} (Latest stable)"
            installed = " ✓ installed" if v in installed_versions else ""
            marker = "▶" if i == cursor else " "
            lines.append((i, f"  {marker}  {label:<30}{installed}"))

        lines.append((None, "  ────────────────────────────────"))
        custom_idx = count
        marker = "▶" if cursor == custom_idx else " "
        lines.append((custom_idx, f"  {marker}  Use local installer (.exe path)"))

        skip_idx = count + 1
        marker = "▶" if cursor == skip_idx else " "
        lines.append((skip_idx, f"  {marker}  Skip"))

        return lines, custom_idx, skip_idx

    lines, custom_idx, skip_idx = _draw()

    # Save terminal state
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin)

        for _, line in lines:
            print(f"\033[K{line}")
        print_count = len(lines)

        while True:
            key = sys.stdin.read(1)
            if key == "\x1b":
                seq = sys.stdin.read(2)
                if seq == "[A" or seq == "[D":  # Up or Left
                    cursor = (cursor - 1) % total
                elif seq == "[B" or seq == "[C":  # Down or Right
                    cursor = (cursor + 1) % total
            elif key == "\r":  # Enter
                if cursor == skip_idx:
                    selected = None
                elif cursor == custom_idx:
                    selected = "__custom__"
                else:
                    selected = versions[cursor]
                break

            # Redraw
            lines, _, _ = _draw()
            for _ in range(print_count):
                sys.stdout.write("\033[F")  # Move up
            for _, line in lines:
                print(f"\033[K{line}")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        print()

    return selected


# ── Download ─────────────────────────────────────────────────────────────────


def download_touchdesigner(
    version: str, installer_path: str | None = None
) -> str | None:
    """
    Download or locate a TouchDesigner installer.
    Returns the path to the installer .exe, or None if skipped.
    """
    # User provided a local installer
    if installer_path:
        installer_path = os.path.expanduser(installer_path)
        if not os.path.isfile(installer_path):
            error(f"Installer not found: {installer_path}")
            raise SystemExit(1)
        info(f"Using local installer: {installer_path}")
        return installer_path

    # Skip
    if version is None:
        return None

    # Download
    url = f"https://download.derivative.ca/TouchDesigner.{version}.exe"
    filename = os.path.basename(url)
    dest = os.path.join(DOWNLOAD_DIR, filename)

    ensure_dir(DOWNLOAD_DIR)

    if os.path.isfile(dest):
        success(f"File already downloaded: {dest}")
        return dest

    info(f"Downloading {filename} (~2 GB)...")
    if not download_file(
        url, dest, filename, show_progress=True, timeout=120, retries=3
    ):
        error("Download failed")
        safe_rm(dest)
        raise SystemExit(1)

    success("Download completed")
    return dest


# ── Installation (7z + innoextract) ──────────────────────────────────────────


def install_touchdesigner(exe_path: str) -> bool:
    """
    Extract the TouchDesigner installer into the Wine prefix using 7z + innoextract.
    Returns True on success.
    """
    if os.path.isfile(os.path.join(TD_INSTALL_DIR, "bin", "TouchDesigner.exe")):
        success(f"TouchDesigner already installed at: {TD_INSTALL_DIR}")
        return True

    # Check required tools
    if not shutil.which("7z"):
        error("7z (p7zip) is required for installation")
        info("Install it with your package manager, then re-run.")
        raise SystemExit(1)

    if not shutil.which("innoextract"):
        error("innoextract is required for installation")
        info("Install it with your package manager, then re-run.")
        raise SystemExit(1)

    ensure_dir(WINETRICKS_TMP)
    extract_root = tempfile.mkdtemp(dir=WINETRICKS_TMP, prefix="td_install_")

    try:
        # Step 1: 7z extraction
        info("Extracting TouchDesigner installer (7z)...")
        extract_7z = os.path.join(extract_root, "7z_extract")
        ensure_dir(extract_7z)

        result = subprocess.run(
            ["7z", "x", exe_path, f"-o{extract_7z}", "-y"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            error("Failed to extract 7z archive from installer")
            return False

        # Find inner Inno Setup .exe
        inner_exe = None
        for f in os.listdir(extract_7z):
            if f.lower().endswith(".exe"):
                inner_exe = os.path.join(extract_7z, f)
                break

        if not inner_exe:
            error("No inner Inno Setup installer found in the archive")
            return False

        # Step 2: innoextract
        info("Extracting TouchDesigner (innoextract)...")
        extract_inno = os.path.join(extract_root, "inno_extract")
        ensure_dir(extract_inno)

        result = subprocess.run(
            ["innoextract", "-d", extract_inno, "-e", inner_exe],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            error("Failed to extract Inno Setup installer")
            return False

        # Verify structure
        app_dir = os.path.join(extract_inno, "$", "app")
        if not os.path.isdir(app_dir):
            error("Unexpected installer structure")
            return False

        # Copy files to Wine prefix
        info("Copying TouchDesigner files to Wine prefix...")
        ensure_dir(TD_INSTALL_DIR)
        shutil.copytree(app_dir, TD_INSTALL_DIR, dirs_exist_ok=True)

        # Copy commonappdata if exists
        commonappdata = os.path.join(extract_inno, "commonappdata")
        if os.path.isdir(commonappdata):
            programdata = os.path.join(WINE_PREFIX, "drive_c", "ProgramData")
            ensure_dir(programdata)
            for item in os.listdir(commonappdata):
                src = os.path.join(commonappdata, item)
                dst = os.path.join(programdata, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)

    finally:
        # Cleanup
        safe_rm(extract_root)

    if not os.path.isfile(os.path.join(TD_INSTALL_DIR, "bin", "TouchDesigner.exe")):
        error("TouchDesigner installation failed: TouchDesigner.exe not found")
        return False

    success(f"TouchDesigner installed to: {TD_INSTALL_DIR}")
    return True
