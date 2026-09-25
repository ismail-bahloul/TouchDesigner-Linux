"""TouchDesigner UI scaling (LogPixels DPI).

TouchDesigner ignores the DPI that Wine reports: changing it through ``winecfg``
or ``winetricks`` has no effect, because TD only reads the ``LogPixels`` value
from ``HKEY_CURRENT_CONFIG\\Software\\Fonts`` at startup. This module reads and
writes that value directly.

A choice made here is recorded in ``prefix/.td_dpi`` so the launcher reapplies it
(session override via ``TD_DPI``) instead of overwriting it with its first-launch
auto-detection.
"""

import os
import re
import shutil
import subprocess

from .utils import ensure_dir, error, info, safe_rm, success, warning
from .wine import RUNNER_DIR, WINE_PREFIX

LOG_PIXELS_KEY = "HKEY_CURRENT_CONFIG\\Software\\Fonts"
# Persisted DPI choice, read by the launcher (see td_lib/launcher.py and the AUR
# launcher). Stored next to the prefix's init flag so the two live together.
DPI_PIN_PATH = os.path.join(WINE_PREFIX, ".td_dpi")

# LogPixels -> display scale: 96=100%, 120=125%, 144=150%, 192=200%.
DPI_PRESETS = (96, 120, 144, 192)


def _find_wine64() -> str | None:
    """Find the wine64 binary (Soda runner, AUR, or system PATH)."""
    candidates = [
        os.path.join(RUNNER_DIR, "bin", "wine64"),
        "/opt/touchdesigner/wine/bin/wine64",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return shutil.which("wine64")


def _wine_env() -> dict:
    """Build a minimal Wine environment for registry commands."""
    wine64 = _find_wine64()
    if not wine64:
        error("wine64 not found. Install TouchDesigner first (run 'td-install').")
        raise SystemExit(1)

    env = os.environ.copy()
    env.update(
        {
            "WINEPREFIX": WINE_PREFIX,
            "WINEARCH": "win64",
            "WINEDEBUG": "fixme-all,warn-all",
            "PATH": f"{os.path.dirname(wine64)}:{env.get('PATH', '')}",
        }
    )
    return {"wine64": wine64, "env": env}


def _preset(value: int) -> int:
    """Round a raw DPI to the nearest standard preset."""
    if value < 108:
        return 96
    if value < 132:
        return 120
    if value < 168:
        return 144
    return 192


def detect_logical_dpi() -> int | None:
    """Detect the display's logical DPI from Xft.dpi or xdpyinfo.

    Returns a standard preset (96/120/144/192) or None if neither tool reports
    a usable value. This already accounts for the user's display scale factor.
    """
    try:
        result = subprocess.run(
            ["xrdb", "-query"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.split("\n"):
            if line.strip().startswith("Xft.dpi"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    val = int(parts[1].strip())
                    if 72 <= val <= 240:
                        return _preset(val)
    except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
        pass

    try:
        result = subprocess.run(
            ["xdpyinfo"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.split("\n"):
            if "resolution" in line:
                m = re.search(r"(\d+)x(\d+)", line)
                if m:
                    val = int(m.group(1))
                    if 72 <= val <= 240:
                        return _preset(val)
    except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
        pass

    return None


def pinned_dpi() -> int | None:
    """Return the DPI recorded by ``td-install --dpi``, or None if unset."""
    try:
        with open(DPI_PIN_PATH) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def _pin(dpi: int) -> None:
    ensure_dir(os.path.dirname(DPI_PIN_PATH))
    with open(DPI_PIN_PATH, "w") as f:
        f.write(f"{dpi}\n")


def _unpin() -> None:
    safe_rm(DPI_PIN_PATH)


def read_logpixels() -> int | None:
    """Read the LogPixels value currently stored in the prefix, or None."""
    env = _wine_env()
    try:
        result = subprocess.run(
            [env["wine64"], "reg", "query", LOG_PIXELS_KEY, "/v", "LogPixels"],
            env=env["env"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if result.returncode != 0:
        return None
    m = re.search(r"LogPixels\s+REG_DWORD\s+0x([0-9a-fA-F]+)", result.stdout)
    return int(m.group(1), 16) if m else None


def write_logpixels(dpi: int) -> bool:
    """Write LogPixels into the prefix and verify it landed."""
    env = _wine_env()
    try:
        result = subprocess.run(
            [
                env["wine64"],
                "reg",
                "add",
                LOG_PIXELS_KEY,
                "/v",
                "LogPixels",
                "/t",
                "REG_DWORD",
                "/d",
                str(dpi),
                "/f",
            ],
            env=env["env"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    if result.returncode != 0:
        return False
    return read_logpixels() == dpi


def run_dpi(arg: str) -> int:
    """Handle ``td-install --dpi [value]``.

    - no value / ``show``: print the DPI currently in effect
    - ``auto``: re-detect from the display (and stop pinning a value)
    - an integer: pin that LogPixels value and apply it now
    """
    value = (arg or "").strip().lower()

    if value in ("", "show"):
        current = pinned_dpi()
        source = "pinned"
        if current is None:
            current = read_logpixels()
            source = "from the prefix"
        if current is None:
            warning(
                "No UI scaling value set yet; the launcher auto-detects it on "
                "first launch."
            )
            return 0
        print(f"UI scaling: LogPixels={current} ({source})")
        print("Change it with: td-install --dpi <96|120|144|192|auto>")
        return 0

    if value == "auto":
        dpi = detect_logical_dpi()
        if dpi is None:
            warning("Could not detect the display DPI; leaving it unchanged.")
            return 1
        pin = False
        note = "auto-detected"
    else:
        try:
            dpi = int(value)
        except ValueError:
            error(f"Invalid DPI '{arg}'. Use 96, 120, 144, 192 or 'auto'.")
            return 2
        if not 72 <= dpi <= 240:
            error(f"DPI {dpi} is out of range (72-240).")
            return 2
        pin = True
        note = "pinned"

    if not os.path.isdir(os.path.join(WINE_PREFIX, "drive_c")):
        error("Wine prefix not found. Install TouchDesigner first (run 'td-install').")
        return 1

    if not write_logpixels(dpi):
        error("Failed to write LogPixels to the Wine registry.")
        return 1

    # Only record the choice once it is actually applied, so a failed run never
    # clobbers a previously pinned value.
    if pin:
        _pin(dpi)
    else:
        _unpin()

    success(f"UI scaling set to LogPixels={dpi} ({note})")
    if pin:
        info("This is remembered across launches and updates.")
    info("Relaunch TouchDesigner for the change to take effect.")
    return 0
