"""Pip wrapper — install Python packages into TouchDesigner's embedded Python.

TouchDesigner ships its own embedded Python with pip available. This module
wraps ``wine64 python.exe -m pip <args>`` so users can install packages into
TD's Python environment without manually juggling Wine paths.

Usage::

    td-install --pip install numpy
    td-install --pip install torch --index-url https://download.pytorch.org/whl/cpu
    td-install --pip list
    td-install --pip uninstall <package>
"""

import os
import shutil
import subprocess

from .utils import error, info, success, warning
from .wine import RUNNER_DIR, WINE_PREFIX


def find_td_python() -> str | None:
    """Return the path to TouchDesigner's embedded ``python.exe``.

    Searches these locations in order:
    1. Standard curl install: ``$WINE_PREFIX/drive_c/Program Files/TouchDesigner*/``
    2. AUR install: ``/opt/touchdesigner/td/``

    Returns the first ``python.exe`` found, or ``None``.
    """
    candidates: list[str] = []

    # 1. Standard curl install (in Wine prefix)
    program_files = os.path.join(WINE_PREFIX, "drive_c", "Program Files")
    if os.path.isdir(program_files):
        try:
            for entry in os.listdir(program_files):
                if entry.startswith("TouchDesigner"):
                    for p in [
                        os.path.join(program_files, entry, "bin", "python.exe"),
                        os.path.join(program_files, entry, "python.exe"),
                        os.path.join(
                            program_files, entry, "bin", "python", "python.exe"
                        ),
                    ]:
                        if os.path.isfile(p):
                            candidates.append(p)
        except PermissionError:
            pass

    # 2. AUR install path
    for aur_path in [
        "/opt/touchdesigner/td/bin/python.exe",
        "/opt/touchdesigner/td/python.exe",
    ]:
        if os.path.isfile(aur_path):
            candidates.append(aur_path)

    # 3. Broader fallback search in Wine prefix
    if not candidates and os.path.isdir(program_files):
        for root, dirs, files in os.walk(program_files):
            for f in files:
                if f.lower() == "python.exe" and "touchdesigner" in root.lower():
                    candidates.append(os.path.join(root, f))

    return candidates[0] if candidates else None


def _find_wine64() -> str | None:
    """Find the wine64 binary.

    Checks in order:
    1. Soda Wine runner (curl install): ``~/.local/share/.../runner/bin/wine64``
    2. AUR install: ``/opt/touchdesigner/wine/bin/wine64``
    3. System PATH

    Returns the path or ``None``.
    """
    candidates = [
        os.path.join(RUNNER_DIR, "bin", "wine64"),
        "/opt/touchdesigner/wine/bin/wine64",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    # Fallback: check PATH
    return shutil.which("wine64")


def _wine_env() -> dict:
    """Build the Wine environment dict for running TD's Python."""
    wine64 = _find_wine64()
    if not wine64:
        error("wine64 not found. Install TouchDesigner first (run 'td-install').")
        raise SystemExit(1)

    runner_bin = os.path.dirname(wine64)
    env = os.environ.copy()
    env.update(
        {
            "WINEPREFIX": WINE_PREFIX,
            "WINEARCH": "win64",
            "WINEDLLOVERRIDES": "mscoree=",
            "WINEDEBUG": "fixme-all,warn-all",
            # Disable Intel OpenMP thread affinity (fixes torch under Wine TkG)
            "KMP_AFFINITY": "disabled",
            "PATH": f"{runner_bin}:{env.get('PATH', '')}",
        }
    )
    return {"wine64": wine64, "env": env}


def run_pip(pip_args: list[str]) -> int:
    """Run ``pip <args>`` inside TouchDesigner's embedded Python.

    Args:
        pip_args: List of pip arguments (e.g. ``["install", "numpy"]``).

    Returns:
        The return code from the pip command (0 on success).
    """
    python_exe = find_td_python()

    if not python_exe:
        error(
            "TouchDesigner Python not found. "
            "Make sure TouchDesigner is installed first (run 'td-install')."
        )
        return 1

    # Verify pip is available in TD's Python
    wine = _wine_env()
    check_result = subprocess.run(
        [wine["wine64"], python_exe, "-m", "pip", "--version"],
        env=wine["env"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if check_result.returncode != 0:
        error("pip is not available in TouchDesigner's Python environment.")
        info("This TouchDesigner version may not ship with pip.")
        info("Output: " + (check_result.stderr or check_result.stdout).strip())
        return 1

    # Build the pip command
    cmd = [wine["wine64"], python_exe, "-m", "pip"] + pip_args
    pip_cmd_str = " ".join(
        f'"{a}"' if " " in a else a for a in ["pip"] + pip_args
    )

    info(f"Running: {pip_cmd_str}")
    info(f"Python: {python_exe}")

    # Show torch-specific info when installing or running
    if pip_args:
        for arg in pip_args:
            if "torch" in arg.lower():
                info(
                    "Note: if torch fails with 'OMP: Error #179' (GetNumaNodeProcessorMaskEx),"
                )
                info(
                    "  set KMP_AFFINITY=disabled in the environment and relaunch."
                )
                info(
                    "  This is built into the --pip wrapper automatically."
                )
                break

    try:
        result = subprocess.run(
            cmd,
            env=wine["env"],
            capture_output=False,  # Let pip output through to the terminal
            timeout=600,  # 10 min for potentially large downloads
        )
    except subprocess.TimeoutExpired:
        error("pip command timed out after 10 minutes.")
        return 1
    except FileNotFoundError:
        error(
            f"wine64 not found at {wine['wine64']}. "
            "Is the Wine runner installed?"
        )
        return 1

    if result.returncode == 0:
        success(f"pip {' '.join(pip_args)} completed successfully")
    else:
        error(f"pip failed with exit code {result.returncode}")

    return result.returncode
