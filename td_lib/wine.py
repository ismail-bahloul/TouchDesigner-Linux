"""Wine runner download, prefix setup, winetricks, and DXVK installation."""

import os
import shutil
import subprocess
import tarfile
import tempfile
import threading
import time

from .utils import (
    TD_BASE_DIR,
    download_file,
    ensure_dir,
    error,
    info,
    run,
    run_optional,
    safe_rm,
    success,
    verify_checksum,
    warning,
)

# ── Paths ────────────────────────────────────────────────────────────────────

RUNNER_DIR = os.path.join(TD_BASE_DIR, "runner")
WINE_PREFIX = os.path.join(TD_BASE_DIR, "prefix")
WINETRICKS_BIN = os.path.join(TD_BASE_DIR, "winetricks")
WINETRICKS_TMP = os.path.join(TD_BASE_DIR, "tmp")
LOG_DIR = os.path.join(TD_BASE_DIR, "logs")

WINE_DLL_OVERRIDES = "mscoree="

SODA_URL = "https://github.com/bottlesdevs/wine/releases/download/soda-9.0-1/soda-9.0-1-x86_64.tar.xz"
SODA_SHA256 = os.environ.get("SODA_SHA256", "")

DXVK_VERSION = "2.4"
DXVK_URL = f"https://github.com/doitsujin/dxvk/releases/download/v{DXVK_VERSION}/dxvk-{DXVK_VERSION}.tar.gz"
DXVK_SHA256 = os.environ.get("DXVK_SHA256", "")

WINETRICKS_URL = (
    "https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks"
)
WINETRICKS_SHA256 = os.environ.get("WINETRICKS_SHA256", "")


# ── Runner download ──────────────────────────────────────────────────────────


def download_soda_runner() -> None:
    """Download and extract the Soda Wine runner if not already present."""
    wine64 = os.path.join(RUNNER_DIR, "bin", "wine64")
    if os.path.isfile(wine64):
        success("Compatibility runtime already installed")
        return

    info("Downloading Soda Wine runtime (~300 MB)...")
    tarball = os.path.join(TD_BASE_DIR, "soda-runner.tar.xz")
    ensure_dir(TD_BASE_DIR)

    if not download_file(SODA_URL, tarball, "Soda Wine runtime"):
        error("Failed to download compatibility runtime")
        safe_rm(tarball)
        raise SystemExit(1)

    if not verify_checksum(tarball, SODA_SHA256):
        safe_rm(tarball)
        raise SystemExit(1)

    info("Extracting compatibility runtime...")
    ensure_dir(RUNNER_DIR)
    try:
        subprocess.run(
            ["tar", "-xJf", tarball, "-C", RUNNER_DIR, "--strip-components=1"],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        error(f"Failed to extract soda runner: {e.stderr or e}")
        safe_rm(tarball)
        raise SystemExit(1)

    safe_rm(tarball)

    if not os.path.isfile(wine64):
        error(f"Wine runner extraction failed: {wine64} not found")
        for entry in os.listdir(RUNNER_DIR):
            info(f"  {entry}")
        raise SystemExit(1)

    # Make wine binaries executable
    for binary in ["wine", "wine64"]:
        path = os.path.join(RUNNER_DIR, "bin", binary)
        if os.path.isfile(path):
            os.chmod(path, 0o755)

    success("Soda Wine runner installed")


# ── Wine prefix ──────────────────────────────────────────────────────────────


def setup_wine_prefix(headless: bool = False) -> None:
    """Initialize the Wine prefix (Windows environment)."""
    drive_c = os.path.join(WINE_PREFIX, "drive_c")

    if os.path.isdir(drive_c):
        # Test if prefix is functional
        env = _wine_env()
        result = subprocess.run(
            [env["wine64"], "cmd", "/c", "exit"],
            env=env["env"],
            capture_output=True,
        )
        if result.returncode == 0:
            success("Wine prefix already initialized")
            return

        warning("Existing Wine prefix looks broken, recreating...")
        _kill_wineserver()
        safe_rm(WINE_PREFIX)

    if headless:
        warning("Skipping Wine prefix initialization (requires graphical session)")
        return

    info("Initializing Wine prefix (win64)...")
    ensure_dir(WINE_PREFIX)

    env = _wine_env()

    try:
        result = subprocess.run(
            [env["wine64"], "wineboot", "--init"],
            env=env["env"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            _handle_wineboot_error(result.stdout + result.stderr)
    except FileNotFoundError:
        error("wineboot not found — is the Wine runner installed?")
        raise SystemExit(1)

    # Let wineboot finish
    import time

    time.sleep(2)
    _kill_wineserver()

    if not os.path.isdir(drive_c):
        error("Wine prefix initialization failed")
        raise SystemExit(1)

    success("Wine prefix initialized")


def _wine_env() -> dict:
    """Build Wine environment dict."""
    wine64 = os.path.join(RUNNER_DIR, "bin", "wine64")
    env = os.environ.copy()
    env.update(
        {
            "WINEPREFIX": WINE_PREFIX,
            "WINEARCH": "win64",
            "WINEDLLOVERRIDES": WINE_DLL_OVERRIDES,
            "PATH": f"{os.path.join(RUNNER_DIR, 'bin')}:{env.get('PATH', '')}",
        }
    )
    return {"wine64": wine64, "env": env}


def _kill_wineserver() -> None:
    """Kill the Wine server for the current prefix."""
    env = _wine_env()
    wineserver = os.path.join(RUNNER_DIR, "bin", "wineserver")
    subprocess.run([wineserver, "-k"], env=env["env"], capture_output=True)


def _handle_wineboot_error(log: str) -> None:
    """Parse wineboot errors and print helpful messages."""
    log_lower = log.lower()

    if "noexec" in log_lower or "failed to set 60000020 protection" in log_lower:
        warning("Wine prefix path is on a noexec filesystem")
        info(f"  Current path: {WINE_PREFIX}")
        info("  Try: TD_BASE_DIR=/var/tmp/$USER/touchdesigner-linux td-install")

    if "libunwind" in log_lower or "could not load ntdll" in log_lower:
        warning("Wine runtime dependency issue detected (missing libunwind/ntdll)")
        info(
            "  On Fedora: sudo dnf install -y libunwind libunwind.i686 libgcc libgcc.i686 libstdc++ libstdc++.i686"
        )

    if "could not load kernel32" in log_lower or "c0000135" in log_lower:
        warning("Wine runtime dependency issue (kernel32 load failure)")
        info(
            "  Ensure all 32-bit libraries are installed by re-running distro package installation"
        )

    if (
        "nodrv_createwindow" in log_lower
        or "failed to create hwnd" in log_lower
        or "no gpu vendor" in log_lower
    ):
        warning("Display/GPU bridge issue detected")
        info("  On Wayland: ensure Xwayland is installed and relogin")

    error("Wine prefix initialization failed")
    raise SystemExit(1)


# ── Winetricks ───────────────────────────────────────────────────────────────


def download_winetricks() -> None:
    """Download the winetricks script."""
    if os.path.isfile(WINETRICKS_BIN) and os.access(WINETRICKS_BIN, os.X_OK):
        success("Winetricks already available")
        return

    info("Downloading winetricks...")
    ensure_dir(TD_BASE_DIR)

    if not download_file(
        WINETRICKS_URL, WINETRICKS_BIN, "winetricks", show_progress=False
    ):
        error("Failed to download winetricks")
        raise SystemExit(1)

    os.chmod(WINETRICKS_BIN, 0o755)
    success("Winetricks downloaded")


def install_windows_deps() -> None:
    """Install Windows compatibility libraries via winetricks."""
    info("Installing compatibility libraries...")
    info("This can take several minutes depending on your network and disk speed.")

    # Kill stale Wine processes before checking prefix
    _kill_wineserver()

    # Check Wine prefix health
    env = _wine_env()
    try:
        result = subprocess.run(
            [env["wine64"], "cmd.exe", "/c", "echo %AppData%"],
            env=env["env"],
            capture_output=True,
            text=True,
        )
        appdata = result.stdout.strip().strip("\r\n\x00")
        if not appdata or appdata == "%AppData%":
            warning("Wine runtime check failed, repairing prefix...")
            setup_wine_prefix(headless=False)
            result = subprocess.run(
                [env["wine64"], "cmd.exe", "/c", "echo %AppData%"],
                env=env["env"],
                capture_output=True,
                text=True,
            )
            appdata = result.stdout.strip()
            if not appdata or appdata == "%AppData%":
                error("Wine runtime is still unhealthy after repair")
                raise SystemExit(1)
    except KeyboardInterrupt:
        print()
        error("Installation cancelled")
        raise SystemExit(1)

    ensure_dir(WINETRICKS_TMP)

    import tempfile

    wt_log = tempfile.NamedTemporaryFile(delete=False, suffix=".log", mode="w")
    wt_log_path = wt_log.name
    wt_log.close()

    wt_env = env["env"].copy()
    wt_env.update(
        {
            "TMPDIR": WINETRICKS_TMP,
            "TMP": WINETRICKS_TMP,
            "TEMP": WINETRICKS_TMP,
            "WINEDEBUG": "-all",
            "WINE": env["wine64"],
        }
    )

    def _run_wt(args: list[str], label: str) -> str:
        """Run a winetricks command with heartbeat logging."""
        stop_heartbeat = threading.Event()

        def _heartbeat():
            start = time.time()
            last_line = ""
            while not stop_heartbeat.is_set():
                elapsed = int(time.time() - start)
                if elapsed > 0 and elapsed % 10 == 0:
                    try:
                        with open(wt_log_path) as f:
                            lines = f.readlines()
                        if lines:
                            current = lines[-1].strip()
                            if current and current != last_line:
                                last_line = current[:80]
                                info(f"Winetricks ({elapsed}s): {last_line}")
                            else:
                                info(f"Winetricks still working... ({elapsed}s)")
                        else:
                            info(f"Winetricks still working... ({elapsed}s)")
                    except OSError:
                        info(f"Winetricks still working... ({elapsed}s)")
                time.sleep(1)

        thread = threading.Thread(target=_heartbeat, daemon=True)
        thread.start()

        info(f"Running winetricks ({label})...")
        try:
            with open(wt_log_path, "w") as log:
                subprocess.run(
                    ["bash", WINETRICKS_BIN] + args,
                    env=wt_env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=True,
                )
            content = ""
            try:
                with open(wt_log_path) as f:
                    content = f.read()
            except OSError:
                pass
            return content
        except subprocess.CalledProcessError:
            error(f"Winetricks failed ({label})")
            info("Last output:")
            try:
                with open(wt_log_path) as f:
                    for line in f.readlines()[-10:]:
                        info(line.strip())
            except OSError:
                pass
            info("Retry with --debug for verbose logs")
            raise SystemExit(1)
        except KeyboardInterrupt:
            print()
            error("Installation cancelled")
            raise SystemExit(1)
        finally:
            stop_heartbeat.set()

    # Step 1: packages with no known conflicts
    _run_wt(["-q", "corefonts", "d3dx11_43"], "corefonts, d3dx11_43")

    # Step 2: vcrun2022 with --force to gracefully override any existing vcrun2019
    _run_wt(["-q", "--force", "vcrun2022"], "vcrun2022")

    safe_rm(wt_log_path)

    success("Windows dependencies installed")


# ── DXVK ─────────────────────────────────────────────────────────────────────


def install_dxvk(enable: bool = True) -> None:
    """Download and install DXVK for DirectX 9/10/11 to Vulkan translation."""
    if not enable:
        return

    sys32 = os.path.join(WINE_PREFIX, "drive_c", "windows", "system32")
    d3d11 = os.path.join(sys32, "d3d11.dll")

    # Check if already installed by looking for a PE32 d3d11.dll
    if os.path.isfile(d3d11):
        result = subprocess.run(
            ["file", d3d11],
            capture_output=True,
            text=True,
        )
        if "PE32" in result.stdout:
            success("DXVK already installed")
            return

    info(f"Downloading DXVK {DXVK_VERSION}...")
    tarball = os.path.join(TD_BASE_DIR, "dxvk.tar.gz")

    if not download_file(DXVK_URL, tarball, "DXVK archive"):
        warning("Failed to download DXVK, skipping (optional)")
        safe_rm(tarball)
        return

    if not verify_checksum(tarball, DXVK_SHA256):
        safe_rm(tarball)
        return

    # Extract to temp dir
    dxvk_dir = tempfile.mkdtemp(prefix="dxvk_")
    try:
        with tarfile.open(tarball, "r:gz") as tar:
            tar.extractall(path=dxvk_dir, filter="data")
    except tarfile.TarError as e:
        warning(f"Failed to extract DXVK: {e}")
        safe_rm(tarball)
        safe_rm(dxvk_dir)
        return

    safe_rm(tarball)

    # Find the actual DXVK directory (first subdirectory)
    extracted_items = os.listdir(dxvk_dir)
    if extracted_items:
        dxvk_root = os.path.join(dxvk_dir, extracted_items[0])
    else:
        dxvk_root = dxvk_dir

    info("Installing DXVK...")
    env = _wine_env()
    setup_script = os.path.join(dxvk_root, "setup_dxvk.sh")

    if os.path.isfile(setup_script):
        script_env = env["env"].copy()
        script_env["WINE"] = env["wine64"]
        result = subprocess.run(
            ["bash", setup_script, "install"],
            env=script_env,
            capture_output=True,
        )
        if result.returncode != 0:
            warning("DXVK setup script failed, installing DLLs manually...")
            _install_dxvk_manual(dxvk_root, env)
    else:
        _install_dxvk_manual(dxvk_root, env)

    safe_rm(dxvk_dir)
    success("DXVK installed")


def _install_dxvk_manual(dxvk_root: str, wine_env: dict) -> None:
    """Manually copy DXVK DLLs and register overrides."""
    sys32 = os.path.join(WINE_PREFIX, "drive_c", "windows", "system32")
    syswow64 = os.path.join(WINE_PREFIX, "drive_c", "windows", "syswow64")

    ensure_dir(sys32)
    ensure_dir(syswow64)

    x64 = os.path.join(dxvk_root, "x64")
    x32 = os.path.join(dxvk_root, "x32")

    if os.path.isdir(x64):
        for dll in os.listdir(x64):
            if dll.endswith(".dll"):
                shutil.copy2(os.path.join(x64, dll), os.path.join(sys32, dll))

    if os.path.isdir(x32):
        for dll in os.listdir(x32):
            if dll.endswith(".dll"):
                shutil.copy2(os.path.join(x32, dll), os.path.join(syswow64, dll))

    # Register DLL overrides
    for dll in ["d3d9", "d3d10core", "d3d11", "dxgi"]:
        subprocess.run(
            [
                wine_env["wine64"],
                "reg",
                "add",
                "HKEY_CURRENT_USER\\Software\\Wine\\DllOverrides",
                "/v",
                dll,
                "/t",
                "REG_SZ",
                "/d",
                "native",
                "/f",
            ],
            env=wine_env["env"],
            capture_output=True,
        )
