"""CodeMeter runtime support: dongles and network-shared licenses.

TouchDesigner's licensing is built on Wibu-Systems CodeMeter. On Windows, the
CodeMeter Runtime is installed alongside TouchDesigner (the installer's
"Install Runtime for Dongle Licensing" option) and provides:

- local license access (CmDongles, CmActLicenses, cloud containers)
- the network *client* that borrows licenses from a CodeMeter license server
  on the LAN (UDP/TCP port 22350)
- the network *server* that shares a locally attached dongle or license with
  other machines

Under Wine, everything except raw USB access is plain user-space network I/O,
so the client/server side works. The main gotcha is that Wine does not
auto-start Windows services, so ``CodeMeter.exe`` must be launched manually.

This module provides the ``td-install --codemeter`` command:

- detect the runtime inside the Wine prefix
- start ``CodeMeter.exe``
- add / remove license servers in the Server Search List (Wibu's official
  ``cmu32 --add-server`` path, with a direct registry fallback)

For the full picture (server setup, port conflicts, firewall) see
``docs/codemeter.md``.
"""

import os
import shutil
import subprocess
import time

from .utils import error, info, success, warning

# ── Paths ────────────────────────────────────────────────────────────────────

_RUNTIME_DIRS = [
    os.path.join("Program Files (x86)", "CodeMeter"),
    os.path.join("Program Files", "CodeMeter"),
]
_CODEMETER_EXE = os.path.join("Runtime", "bin", "CodeMeter.exe")
_CMU32_EXE = os.path.join("Runtime", "bin", "cmu32.exe")

# Server Search List registry location (Windows client). Each entry is a
# subkey Server1, Server2, ... carrying a REG_SZ value "Address" with the
# license server's IP/hostname.
_SERVER_LIST_KEY = (
    r"HKLM\SOFTWARE\WIBU-SYSTEMS\CodeMeter\Server\CurrentVersion"
    r"\ServerSearchList"
)

# Port used by the CodeMeter license server protocol (discovery + transport).
CODEMETER_PORT = 22350


def _find_wine64() -> str | None:
    """Find the wine64 binary (Soda runner, AUR, or system PATH)."""
    from .wine import RUNNER_DIR

    candidates = [
        os.path.join(RUNNER_DIR, "bin", "wine64"),
        "/opt/touchdesigner/wine/bin/wine64",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return shutil.which("wine64")


def _wine_env() -> dict:
    """Build a minimal Wine environment for CodeMeter commands."""
    wine64 = _find_wine64()
    if not wine64:
        error(
            "wine64 not found. Install TouchDesigner first "
            "(run 'td-install')."
        )
        raise SystemExit(1)

    from .wine import WINE_PREFIX

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


# ── Detection ────────────────────────────────────────────────────────────────


def find_runtime_dir(prefix: str | None = None) -> str | None:
    """Return the CodeMeter install directory inside the prefix, or None."""
    from .wine import WINE_PREFIX

    prefix = prefix or WINE_PREFIX
    drive_c = os.path.join(prefix, "drive_c")
    for sub in _RUNTIME_DIRS:
        candidate = os.path.join(drive_c, sub)
        if os.path.isdir(candidate):
            return candidate
    return None


def find_runtime_exe(prefix: str | None = None) -> str | None:
    """Return the path to ``CodeMeter.exe`` inside the prefix, or None."""
    runtime_dir = find_runtime_dir(prefix)
    if not runtime_dir:
        return None
    exe = os.path.join(runtime_dir, _CODEMETER_EXE)
    return exe if os.path.isfile(exe) else None


def find_cmu32(prefix: str | None = None) -> str | None:
    """Return the path to the CodeMeter command-line tool, or None.

    The 32-bit runtime ships ``cmu32.exe``, the 64-bit runtime ships
    ``cmu.exe``; check both.
    """
    runtime_dir = find_runtime_dir(prefix)
    if not runtime_dir:
        return None
    bin_dir = os.path.join(runtime_dir, "Runtime", "bin")
    for name in ("cmu32.exe", "cmu.exe"):
        exe = os.path.join(bin_dir, name)
        if os.path.isfile(exe):
            return exe
    return None


def is_running() -> bool:
    """Check whether a CodeMeter runtime process is already up.

    Uses a host-side ``pgrep`` with an exact process-name match (Wine names
    the host process after the Windows image, e.g. ``CodeMeter.exe``). A
    ``-f`` full-command-line match is avoided on purpose: it would also match
    any shell/script whose command line merely mentions the name. Falls back
    to ``wine64 tasklist``.
    """
    if shutil.which("pgrep"):
        try:
            result = subprocess.run(
                ["pgrep", "-x", "CodeMeter.exe"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, OSError):
            pass  # fall through to tasklist

    wine = _wine_env()
    try:
        result = subprocess.run(
            [wine["wine64"], "tasklist"],
            env=wine["env"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return "CodeMeter.exe" in (result.stdout or "")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def start_runtime(timeout: float = 12.0) -> bool:
    """Start ``CodeMeter.exe`` in the prefix and wait for it to come up.

    Windows services don't auto-start under Wine, so this must be called
    before launching TouchDesigner (the generated launcher does this too).
    """
    exe = find_runtime_exe()
    if not exe:
        error("CodeMeter runtime not found in the Wine prefix.")
        return False

    if is_running():
        success("CodeMeter runtime already running")
        return True

    wine = _wine_env()
    info(f"Starting CodeMeter runtime: {exe}")
    try:
        subprocess.Popen(
            [wine["wine64"], exe],
            env=wine["env"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as e:
        error(f"Failed to start CodeMeter runtime: {e}")
        return False

    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_running():
            success("CodeMeter runtime started")
            return True
        time.sleep(0.5)

    warning(
        "CodeMeter runtime did not report running within "
        f"{timeout:.0f}s (may still initialize)."
    )
    return False


def stop_runtime(timeout: float = 10.0) -> bool:
    """Stop ``CodeMeter.exe`` (used after changing the Server Search List)."""
    wine = _wine_env()
    try:
        subprocess.run(
            [wine["wine64"], "taskkill", "/IM", "CodeMeter.exe", "/F"],
            env=wine["env"],
            capture_output=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    deadline = time.time() + timeout
    while time.time() < deadline:
        if not is_running():
            return True
        time.sleep(0.5)
    return not is_running()


# ── Server Search List ───────────────────────────────────────────────────────


def _restart_runtime() -> None:
    """Stop then start the runtime so config changes take effect.

    No-op when the runtime isn't installed; ``add-server``/``remove-server``
    are pure config operations and must stay usable (and quiet) without it.
    """
    if not find_runtime_exe():
        return
    info("Restarting CodeMeter runtime...")
    stop_runtime()
    start_runtime()


def add_server(server: str) -> bool:
    """Add a license server to the client's Server Search List.

    Prefers Wibu's official ``cmu32 --add-server`` tool, falling back to a
    direct registry write. Either way the runtime is restarted afterwards so
    the entry is picked up.
    """
    server = server.strip().strip('"')
    if not server:
        error("No server address given.")
        return False

    wine = _wine_env()

    # Path 1: official tool (writes the registry for us)
    cmu32 = find_cmu32()
    if cmu32:
        try:
            result = subprocess.run(
                [wine["wine64"], cmu32, "--add-server", server],
                env=wine["env"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                success(f"Added license server: {server}")
                _restart_runtime()
                return True
            info(
                "cmu32 --add-server failed, falling back to registry: "
                + (result.stderr or result.stdout or "").strip()[-200:]
            )
        except (subprocess.TimeoutExpired, OSError):
            info("cmu32 --add-server unavailable, using registry directly.")

    # Path 2: write the registry key directly (same location WebAdmin uses)
    index = _next_server_index(wine)
    key = rf"{_SERVER_LIST_KEY}\Server{index}"
    try:
        result = subprocess.run(
            [
                wine["wine64"],
                "reg",
                "add",
                key,
                "/v",
                "Address",
                "/t",
                "REG_SZ",
                "/d",
                server,
                "/f",
            ],
            env=wine["env"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            error(
                "Failed to write Server Search List: "
                + (result.stderr or result.stdout or "").strip()
            )
            return False
    except (subprocess.TimeoutExpired, OSError) as e:
        error(f"Failed to write Server Search List: {e}")
        return False

    success(f"Added license server: {server} (Server{index})")
    _restart_runtime()
    return True


def remove_server(server: str) -> bool:
    """Remove a license server from the client's Server Search List."""
    server = server.strip().strip('"')
    if not server:
        error("No server address given.")
        return False

    wine = _wine_env()
    entries = list_servers(wine=wine)
    removed = False
    for index, address in entries:
        if address.lower() == server.lower():
            key = rf"{_SERVER_LIST_KEY}\Server{index}"
            try:
                subprocess.run(
                    [wine["wine64"], "reg", "delete", key, "/f"],
                    env=wine["env"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                success(f"Removed license server: {address}")
                removed = True
            except (subprocess.TimeoutExpired, OSError):
                error(f"Failed to remove {address} (Server{index}).")

    if not removed:
        info(f"No entry found for: {server}")
    _restart_runtime()
    return removed


def list_servers(wine: dict | None = None) -> list[tuple[int, str]]:
    """Return [(index, address), ...] from the Server Search List.

    Probes ``Server1``, ``Server2``, … directly: Wine's ``reg query`` wraps
    long key paths at 80 columns, which makes parsing the parent key's
    subkey listing unreliable. Probing each index avoids that entirely.
    Stops after three consecutive misses (indices are dense in practice).

    ``wine`` is the dict returned by :func:`_wine_env` (kept as a parameter
    so callers can reuse one environment).
    """
    wine = wine or _wine_env()
    entries: list[tuple[int, str]] = []
    index = 1
    misses = 0
    while index <= 100:
        address = _read_server_address(wine, index)
        if address:
            entries.append((index, address))
            misses = 0
        else:
            misses += 1
            if misses >= 3:
                break
        index += 1
    return entries


def _next_server_index(wine: dict) -> int:
    """Return the first free ServerN index (1-based, per CodeMeter)."""
    indices = [i for i, _ in list_servers(wine=wine)]
    index = 1
    while index in indices:
        index += 1
    return index


def _read_server_address(wine: dict, index: int) -> str | None:
    """Read the Address value of one ServerSearchList entry."""
    key = rf"{_SERVER_LIST_KEY}\Server{index}"
    try:
        result = subprocess.run(
            [wine["wine64"], "reg", "query", key, "/v", "Address"],
            env=wine["env"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None

    for line in (result.stdout or "").splitlines():
        parts = line.split()
        # wine reg query: <value>  <type>  <data>
        if len(parts) >= 3 and parts[0].lower() == "address":
            return parts[-1]
    return None


# ── Status / CLI ─────────────────────────────────────────────────────────────


def status() -> int:
    """Print a human-readable report and return 0."""
    exe = find_runtime_exe()
    cmu32 = find_cmu32()

    print()
    info("CodeMeter status")
    print()

    if not exe:
        warning("CodeMeter runtime is NOT installed in the Wine prefix.")
        info("It is installed by the TouchDesigner installer (the option")
        info('  "Install Runtime for Dongle Licensing" (checked by default).')
        info("If your installation skipped it (e.g. silent extraction), the")
        info("runtime can be installed manually; see docs/codemeter.md.")
        print()
        info("Note: software licenses (ins*.dat) do NOT need the runtime;")
        info("it is only required for dongles and network-shared licenses.")
        info("See docs/codemeter.md for the current status of the network path.")
        return 0

    info(f"Runtime:     {exe}")
    info(f"cmu tool:    {cmu32 or '(not found)'}")
    info(f"Running:     {'yes' if is_running() else 'no'}")

    entries = list_servers()
    if entries:
        info("Server Search List:")
        for index, address in entries:
            info(f"  Server{index}: {address}")
    else:
        info("Server Search List: empty (automatic LAN search is used)")

    print()
    info("Next steps:")
    if not is_running():
        info("  Start the runtime:   td-install --codemeter start")
        info("    (if it fails to stay up, see docs/codemeter.md: the")
        info("     CodeMeter service currently does not start under Wine)")
    info("  Add a license server: td-install --codemeter add-server <ip>")
    info("  Manage via WebAdmin:  http://127.0.0.1:22350 (once running)")
    print()
    return 0


def run_codemeter(args: list[str]) -> int:
    """Entry point for ``td-install --codemeter [command]``."""
    command = args[0] if args else "status"

    if command in ("status", "info", "check"):
        return status()

    if command in ("setup", "install", "enable"):
        if not find_runtime_exe():
            status()
            return 1
        start_runtime()
        return status()

    if command in ("start", "run"):
        if not find_runtime_exe():
            error("CodeMeter runtime not found in the Wine prefix.")
            error("See: td-install --codemeter status")
            return 1
        return 0 if start_runtime() else 1

    if command == "add-server":
        if len(args) < 2:
            error("Usage: td-install --codemeter add-server <ip-or-hostname>")
            return 1
        return 0 if add_server(args[1]) else 1

    if command == "remove-server":
        if len(args) < 2:
            error("Usage: td-install --codemeter remove-server <ip-or-hostname>")
            return 1
        return 0 if remove_server(args[1]) else 1

    if command == "servers":
        entries = list_servers()
        if not entries:
            info("Server Search List is empty (automatic LAN search is used).")
            return 0
        for index, address in entries:
            info(f"Server{index}: {address}")
        return 0

    error(f"Unknown --codemeter command: {command}")
    info("Commands: status | setup | start | add-server <ip> |")
    info("          remove-server <ip> | servers")
    return 1
