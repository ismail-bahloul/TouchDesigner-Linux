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
- install the runtime without msiexec (``install <path>``: native
  extraction with innoextract/7z, so any runtime version can be tried
  quickly)
- start ``CodeMeter.exe``
- add / remove license servers in the Server Search List (Wibu's official
  ``cmu32 --add-server`` path, with a direct registry fallback)

For the full picture (server setup, port conflicts, firewall) see
``docs/codemeter.md``.
"""

import os
import shutil
import subprocess
import tempfile
import time

from .utils import ensure_dir, error, info, safe_rm, success, warning

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


# ── Native (msiexec-free) runtime installation ───────────────────────────────


def install_runtime(installer_path: str) -> bool:
    """Install the CodeMeter runtime into the Wine prefix without msiexec.

    Wibu ships the runtime as an Inno Setup ``.exe`` (CodeMeterRuntime*.exe)
    or an ``.msi``; both hang or fail under Wine's ``msiexec``. This command
    extracts the installer natively on the host (``innoextract`` for Inno
    setups, ``7z`` for MSI archives) and lifts the payload into the prefix,
    at the exact locations a real Windows install would use:

    - ``Program Files (x86)/CodeMeter`` (the runtime itself)
    - ``ProgramData/WIBU-SYSTEMS`` (configuration, if shipped)

    Bypassing msiexec makes it trivial to try multiple runtime versions —
    the leading fix for the protected ``cpsrt.dll`` loader issue (the
    runtimes 8.41a/9.10 don't map under Wine 9.0; see docs/codemeter.md).
    """
    if not os.path.isfile(installer_path):
        error(f"Installer not found: {installer_path}")
        return False

    from .wine import WINE_PREFIX

    drive_c = os.path.join(WINE_PREFIX, "drive_c")
    if not os.path.isdir(drive_c):
        error("No Wine prefix found — install TouchDesigner first (run 'td-install').")
        return False

    extract_root = tempfile.mkdtemp(prefix="td_cm_runtime_")
    try:
        info(f"Extracting {os.path.basename(installer_path)}...")
        if not _extract_installer(installer_path, extract_root):
            return False

        codemeter_root = _find_codemeter_root(extract_root)
        if not codemeter_root:
            error("No CodeMeter runtime payload found in the installer.")
            info("Expected Runtime/bin/CodeMeter.exe inside the extracted archive.")
            return False

        wibu_pd = _find_wibu_programdata(extract_root)
        _copy_payload(codemeter_root, wibu_pd, drive_c)
        _copy_system_dlls(extract_root, drive_c)
        success("CodeMeter runtime installed into the Wine prefix.")
    finally:
        safe_rm(extract_root)

    if not find_runtime_exe():
        error("Runtime installed, but CodeMeter.exe was not found afterwards.")
        return False

    info("Starting the runtime...")
    if start_runtime():
        info("Next: td-install --codemeter add-server <license-server-ip>")
    else:
        warning(
            "Runtime installed but did not stay up — under Wine 9.0 the"
            " CodeMeter service stalls during startup (see docs/codemeter.md)."
        )
    return True


def _extract_installer(installer_path: str, dest: str) -> bool:
    """Extract a CodeMeter runtime installer natively.

    Tries each available extractor in order — ``innoextract`` then ``7z``
    for Inno ``.exe`` bundles, ``7z`` then ``msiextract`` for ``.msi`` — so
    a fallback is used when the preferred tool doesn't recognize the format
    (Wibu also ships WiX bundles that innoextract rejects but 7z unwraps).
    """
    ensure_dir(dest)
    lower = installer_path.lower()

    attempts: list[list[str]] = []
    if lower.endswith(".msi"):
        if shutil.which("7z"):
            attempts.append(["7z", "x", installer_path, f"-o{dest}", "-y"])
        if shutil.which("msiextract"):
            attempts.append(["msiextract", "--directory", dest, installer_path])
    else:
        if shutil.which("innoextract"):
            attempts.append(["innoextract", "-d", dest, "-e", installer_path])
        if shutil.which("7z"):
            attempts.append(["7z", "x", installer_path, f"-o{dest}", "-y"])

    if not attempts:
        error("Need innoextract or 7z to extract the installer.")
        return False

    last_error = "no extractor produced output"
    for cmd in attempts:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600
            )
        except (subprocess.TimeoutExpired, OSError) as e:
            last_error = str(e)
            continue
        if result.returncode == 0:
            return True
        last_error = (result.stderr or result.stdout or "").strip()[-300:]
    error("Extraction failed: " + last_error)
    return False


def _find_codemeter_root(extract_dir: str) -> str | None:
    """Locate the CodeMeter payload root inside an extracted installer.

    Returns the topmost directory named ``CodeMeter`` whose tree contains
    ``Runtime/bin/CodeMeter.exe``, or None. Tolerant of the layout variations
    between Inno (``Program Files (x86)/CodeMeter``), MSI (``[0]/...``) and
    64-bit (``Program Files/CodeMeter``) installers.
    """
    for dirpath, _, filenames in os.walk(extract_dir):
        has_exe = any(f.lower() == "codemeter.exe" for f in filenames)
        if not has_exe:
            continue
        node = dirpath
        while os.path.dirname(node) != node:
            if os.path.basename(node).lower() == "codemeter":
                return node
            node = os.path.dirname(node)
    return None


def _find_wibu_programdata(extract_dir: str) -> str | None:
    """Locate the ``WIBU-SYSTEMS`` config payload (ProgramData), if any."""
    for dirpath, dirnames, _ in os.walk(extract_dir):
        for name in dirnames:
            if name.lower() == "wibu-systems":
                candidate = os.path.join(dirpath, name)
                if os.path.isdir(os.path.join(candidate, "CodeMeter")):
                    return candidate
    return None


def _copy_payload(codemeter_root: str, wibu_pd: str | None, drive_c: str) -> None:
    """Copy the extracted payload into the Wine prefix at the standard
    locations (Program Files (x86)/CodeMeter, ProgramData/WIBU-SYSTEMS)."""
    dest_root = os.path.join(drive_c, "Program Files (x86)", "CodeMeter")
    ensure_dir(os.path.dirname(dest_root))
    shutil.copytree(codemeter_root, dest_root, dirs_exist_ok=True)

    if wibu_pd:
        pd_dest = os.path.join(drive_c, "ProgramData", "WIBU-SYSTEMS")
        ensure_dir(os.path.dirname(pd_dest))
        shutil.copytree(wibu_pd, pd_dest, dirs_exist_ok=True)


def _copy_system_dlls(extract_dir: str, drive_c: str) -> None:
    """Copy the Wibu system DLLs into the Wine system directories.

    A real Windows install puts ``WibuCm64.dll`` / ``cpsrt.dll`` into
    System32 and their 32-bit counterparts into System (syswow64 under
    Wine). CodeMeter.exe loads ``cpsrt.dll`` from there, so this is
    required for it to start.
    """
    system32 = os.path.join(drive_c, "windows", "system32")
    syswow64 = os.path.join(drive_c, "windows", "syswow64")
    for dirpath, _, filenames in os.walk(extract_dir):
        base = os.path.basename(dirpath).lower()
        if base == "system32" and any(
            f.lower() == "wibucm64.dll" for f in filenames
        ):
            ensure_dir(system32)
            _copy_dir_contents(dirpath, system32)
        elif base == "system" and any(
            f.lower() == "wibucm32.dll" for f in filenames
        ):
            ensure_dir(syswow64)
            _copy_dir_contents(dirpath, syswow64)


def _copy_dir_contents(src: str, dst: str) -> None:
    """Copy every file from ``src`` into ``dst`` (merge)."""
    for name in os.listdir(src):
        s = os.path.join(src, name)
        if os.path.isfile(s):
            shutil.copy2(s, os.path.join(dst, name))


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

    if command in ("setup", "enable"):
        if not find_runtime_exe():
            status()
            return 1
        start_runtime()
        return status()

    if command == "install":
        if len(args) >= 2:
            # install <path>: native, msiexec-free runtime installation
            return 0 if install_runtime(args[1]) else 1
        # no installer path: behave like setup (runtime already present?)
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
    info("Commands: status | setup | start | install <installer-path> |")
    info("          add-server <ip> | remove-server <ip> | servers")
    return 1
