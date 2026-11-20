"""Experimental Proton runner (``td-install --runner proton11``).

Runs TouchDesigner on **DAW-GE-Proton11** through umu-launcher instead of the
default Soda Wine 9. Why bother: it is the only runner where the NVIDIA CUDA
TOPs (Background, Denoise, Upscaler, RTX Video, Video Stream In/Out) and the
CodeMeter runtime work.

Credit: DAW-GE-Proton is KitsuneDev's fork of GE-Proton, with the DWrite fix
that lets TouchDesigner start on Wine 11 — https://github.com/KitsuneDev/daw-proton-ge

Design: every other module (pip, dpi, patches, CodeMeter, the launcher...)
calls ``<runner>/bin/wine64 <args>``. Proton cannot be driven that way (it
needs umu's container), so this module installs small relay scripts at those
paths that forward to ``umu-run``. Nothing else has to know about Proton.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

from .utils import (
    TD_BASE_DIR,
    download_file,
    ensure_dir,
    error,
    info,
    safe_rm,
    success,
    verify_checksum,
    warning,
)

RUNNER_SODA = "soda"
RUNNER_PROTON11 = "proton11"
RUNNER_KINDS = (RUNNER_SODA, RUNNER_PROTON11)

RUNNER_MARKER = os.path.join(TD_BASE_DIR, ".runner")
PROTON11_ENV_FILE = os.path.join(TD_BASE_DIR, "proton11.env")
PROTON11_USER_ENV_FILE = os.path.join(TD_BASE_DIR, "proton11.user.env")

# ── Pinned artifacts ─────────────────────────────────────────────────────────

PROTON11_NAME = "DAW-GE-Proton11-6c"
PROTON11_URL = (
    "https://github.com/KitsuneDev/daw-proton-ge/releases/download/"
    f"{PROTON11_NAME}/{PROTON11_NAME}.tar.gz"
)
PROTON11_SHA256 = os.environ.get(
    "PROTON11_SHA256",
    "aecf59518c1137028f6c47afc8e497064d6c5d0f206df6ea6d385dd0766f02d5",
)

# nvcuda (CUDA bridge) patched for Wine 11: maps shared handles through D3DKMT
# and no longer destroys live semaphores (see patches/ and docs/runners.md).
# Built against the exact Wine headers of DAW-GE-Proton11-6c — the wineserver
# request number is build specific — so it must not be used with another build.
NVCUDA_PATCHED_URL = os.environ.get(
    "NVCUDA_PATCHED_URL",
    "https://github.com/ismail-bahloul/TouchDesigner-Linux/releases/download/"
    f"runner-assets/nvcuda-{PROTON11_NAME}.dll.so",
)
NVCUDA_PATCHED_SHA256 = os.environ.get(
    "NVCUDA_PATCHED_SHA256",
    "825f491545d4c3b22171e3e0a521a65bf3a09c4960475b214495c06b3d91cc77",
)
_NVCUDA_REL = os.path.join(
    "files", "lib", "wine", "nvidia-libs", "nvcuda", "x86_64-windows", "nvcuda.dll.so"
)

# nvencodeapi64 (the NVENC bridge) with NvEncGetInputFormats fixed: stock, it calls
# nvEncGetInputFormatCount instead of nvEncGetInputFormats, so it never fills the array
# and the application sees no supported input format ("Encoding this pixel format is not
# supported on this GPU" in the Video Stream Out TOP). Built from the exact SveSop/nvenc
# commit bundled with DAW-GE-Proton11-6c; one line changed, see patches/README.md.
NVENC_PATCHED_URL = os.environ.get(
    "NVENC_PATCHED_URL",
    "https://github.com/ismail-bahloul/TouchDesigner-Linux/releases/download/"
    f"runner-assets/nvencodeapi64-{PROTON11_NAME}.dll.so",
)
NVENC_PATCHED_SHA256 = os.environ.get(
    "NVENC_PATCHED_SHA256",
    "5407994f542ddc92ad140278730d23bf2e9040f4f2ddf6b56b40775ba1b6844b",
)
_NVENC_REL = os.path.join(
    "files", "lib", "wine", "nvidia-libs", "nvenc", "x86_64-windows", "nvencodeapi64.dll.so"
)

# qcap (Wine's DirectShow video capture) patched to close the camera when the capture
# graph is stopped. Stock Wine keeps /dev/video0 open for the life of the filter, so
# after the first deactivation of a Video Device In TOP, or a change of format, the next
# graph fails with "Failed to set pixel format: Device or resource busy" (issue #35).
# Built from the exact Wine source of DAW-GE-Proton11-6c (plus its own qcap hotfixes), so
# only valid for that build. Source, recipe and licence: patches/README.md.
QCAP_PATCHED_URL = os.environ.get(
    "QCAP_PATCHED_URL",
    "https://github.com/ismail-bahloul/TouchDesigner-Linux/releases/download/"
    f"runner-assets/qcap-{PROTON11_NAME}.tar.gz",
)
QCAP_PATCHED_SHA256 = os.environ.get(
    "QCAP_PATCHED_SHA256",
    "3b1ed9e15e52691c4b8c5f1cb95572a1e4dc938f8db5c4190cd852f6c86721d7",
)
# (name inside the archive, path inside the runner, sha256 of the patched file)
_QCAP_FILES = (
    (
        "qcap.dll",
        os.path.join("files", "lib", "wine", "x86_64-windows", "qcap.dll"),
        "a7c20c52a122e61f86d56ca9ab7d949daee55056cf1c63521877b32a11f031ab",
    ),
    (
        "qcap.so",
        os.path.join("files", "lib", "wine", "x86_64-unix", "qcap.so"),
        "9ff591b1b9f78bd0b6d7b84893ef0ba31ac424faad950072756ffdeb5e28a2e2",
    ),
)

# NVIDIA Video Effects SDK runtime (Background / Denoise / Upscaler TOPs).
# Downloaded straight from NVIDIA, never redistributed by this project.
VFX_VERSION = "0.7.6"
VFX_URL = (
    "https://international.download.nvidia.com/Windows/broadcast/sdk/VFX/"
    "nvidia_video_effects_sdk_installer_v{version}_{arch}.exe"
)
VFX_SHA256 = {
    "turing": "d51d8789f96a82375b04bcca6914eee301ad5b6cc45137d7b86fc45ddb205f2d",
    "ampere": "93bdf4ffec7c393037936349678d1864897fef45d7ba2ab81d4b1563e1328512",
    "ada": "4761fe1579e82de6d45efec8dc09492cf2cc601867269955e129707ac8ea8546",
    "blackwell": "cef45592e16d0ea91dbff12a828b31874ab83829adf9a431466dfb88b714618d",
}
# compute capability -> installer. Strict on purpose: the SDK ships TensorRT
# engines prebuilt per architecture, so a wrong guess installs a dead SDK.
_COMPUTE_CAP_TO_ARCH = {"7.5": "turing", "8.6": "ampere", "8.9": "ada", "12.0": "blackwell"}
VFX_DIR_REL = os.path.join("drive_c", "Program Files", "NVIDIA Corporation", "NVIDIA Video Effects")
VFX_WIN_PATH = r"C:\Program Files\NVIDIA Corporation\NVIDIA Video Effects"


# ── Runner kind marker ───────────────────────────────────────────────────────


def get_runner_kind() -> str:
    """Return the installed runner kind; installs predating ``--runner`` are Soda."""
    try:
        with open(RUNNER_MARKER) as f:
            kind = f.read().strip()
    except OSError:
        return RUNNER_SODA
    return kind if kind in RUNNER_KINDS else RUNNER_SODA


def set_runner_kind(kind: str) -> None:
    ensure_dir(TD_BASE_DIR)
    with open(RUNNER_MARKER, "w") as f:
        f.write(kind + "\n")


def ensure_runner_compatible(requested: str) -> None:
    """Refuse to switch runner on top of an existing prefix.

    A Soda (Wine 9) prefix upgraded in place by Proton 11 — or the reverse —
    gives hard-to-debug breakage, and recreating it would drop the TD license.
    """
    from .wine import WINE_PREFIX

    if not os.path.isdir(os.path.join(WINE_PREFIX, "drive_c")):
        return
    existing = get_runner_kind()
    if existing == requested:
        return
    error(f"This install already uses the '{existing}' runner, not '{requested}'.")
    info("Switching runner needs a fresh prefix. Either:")
    info("  - run 'td-install --uninstall' first (this also removes your TD license activation), or")
    info(f"  - install into another directory to keep both: TD_BASE_DIR=~/td-{requested} td-install --runner {requested}")
    raise SystemExit(1)


def choose_runner(requested: str | None, interactive: bool) -> str:
    """Resolve the runner for an install.

    An explicit ``--runner`` wins; an existing prefix keeps its runner; otherwise
    an interactive install asks, and everything else gets Soda (the default).
    """
    from .wine import WINE_PREFIX

    if requested:
        return requested
    if os.path.isdir(os.path.join(WINE_PREFIX, "drive_c")):
        return get_runner_kind()
    if not interactive:
        return RUNNER_SODA
    return _pick_runner_menu()


_RUNNER_CHOICES = [
    (
        RUNNER_SODA,
        "Soda Wine 9 (default)",
        "Stable and well tested. No NVIDIA CUDA TOPs.",
    ),
    (
        RUNNER_PROTON11,
        "Proton 11 (experimental)",
        "Adds the NVIDIA CUDA TOPs (Background, Denoise, Upscaler, RTX Video)\n"
        "     and CodeMeter. Needs umu-launcher, launches are slower.",
    ),
]


def _pick_runner_menu() -> str:
    """Arrow-key menu in the style of the main menu; numbered prompt without a TTY."""
    import termios
    import tty

    from .utils import Colors

    print("\nChoose the compatibility runner")
    print("A runner cannot be switched later without a fresh install\n")

    if not sys.stdin.isatty():
        for i, (_, title, desc) in enumerate(_RUNNER_CHOICES, 1):
            print(f"  {i}. {title}")
            print(f"{Colors.accent}     {desc}{Colors.nc}\n")
        while True:
            try:
                answer = input("  Select option [1]: ").strip() or "1"
            except (EOFError, KeyboardInterrupt):
                print()
                raise SystemExit(1)
            if answer in ("1", "2"):
                return _RUNNER_CHOICES[int(answer) - 1][0]

    print("Use ↑ ↓ to navigate, Enter to select\n")
    cursor = 0

    def _draw() -> list[str]:
        lines = []
        for i, (_, title, desc) in enumerate(_RUNNER_CHOICES):
            marker = "▶" if i == cursor else " "
            lines.append(f"  {marker}  {i + 1}. {title}")
            for part in desc.split("\n"):
                lines.append(f"{Colors.accent}     {part.strip()}{Colors.nc}")
            if i < len(_RUNNER_CHOICES) - 1:
                lines.append("")
        return lines

    lines = _draw()
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()
    for line in lines:
        print(line)
    count = len(lines)

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
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
                print()
                raise SystemExit(1)
            if key == "\x1b":
                try:
                    seq = sys.stdin.read(2)
                except (EOFError, OSError):
                    seq = ""
                if seq == "[A":
                    cursor = (cursor - 1) % len(_RUNNER_CHOICES)
                elif seq == "[B":
                    cursor = (cursor + 1) % len(_RUNNER_CHOICES)
            elif key in ("1", "2"):
                cursor = int(key) - 1
            elif key in ("\r", "\n"):
                break
            lines = _draw()
            for _ in range(count):
                sys.stdout.write("\033[A")
            for line in lines:
                sys.stdout.write(f"\033[K{line}\n")
            sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
    print()
    return _RUNNER_CHOICES[cursor][0]


def describe_runner() -> str:
    """One-line runner description for --diagnose."""
    if get_runner_kind() != RUNNER_PROTON11:
        return ""
    umu = shutil.which("umu-run")
    return f"{PROTON11_NAME} via umu-launcher ({umu or 'umu-run NOT FOUND'})"


# ── umu-launcher ─────────────────────────────────────────────────────────────


def require_umu() -> str:
    path = shutil.which("umu-run")
    if path:
        return path
    error("umu-run not found: the proton11 runner needs umu-launcher.")
    info("  Arch / CachyOS:  sudo pacman -S umu-launcher")
    info("  Fedora:          sudo dnf install umu-launcher")
    info("  Other distros:   https://github.com/Open-Wine-Components/umu-launcher")
    raise SystemExit(1)


# ── Relay scripts ────────────────────────────────────────────────────────────

_RELAY_WINE64 = """#!/bin/bash
# Generated by td-install (--runner proton11). Do not edit: it is rewritten by
# 'td-install --update'. Put your own exports in proton11.user.env instead.
#
# Relays Wine commands to umu-run + Proton, so everything that calls
# "<runner>/bin/wine64 <args>" (pip, dpi, patches, CodeMeter, launcher) works
# unchanged. Each call starts umu's container, which costs about 3 seconds.
BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PROTONPATH="$BASE/runner"
export WINEPREFIX="${WINEPREFIX:-$BASE/prefix}"
export GAMEID="${GAMEID:-umu-default}"
# Keep a TD_BASE_DIR outside $HOME visible inside the container
export PRESSURE_VESSEL_FILESYSTEMS_RW="${PRESSURE_VESSEL_FILESYSTEMS_RW:+$PRESSURE_VESSEL_FILESYSTEMS_RW:}$BASE"
[ -f "$BASE/proton11.env" ] && . "$BASE/proton11.env"
[ -f "$BASE/proton11.user.env" ] && . "$BASE/proton11.user.env"
if ! command -v umu-run >/dev/null 2>&1; then
    echo "umu-run not found: install umu-launcher (needed by the proton11 runner)." >&2
    exit 127
fi
exec umu-run "$@"
"""

_RELAY_WINEBOOT = """#!/bin/bash
# Generated by td-install (--runner proton11).
exec "$(dirname "${BASH_SOURCE[0]}")/wine64" wineboot "$@"
"""

_RELAY_WINESERVER = """#!/bin/bash
# Generated by td-install (--runner proton11).
# Only the calls td-install makes: -k (kill the prefix's processes), -w (wait).
case "$1" in
    -k|--kill) exec "$(dirname "${BASH_SOURCE[0]}")/wine64" wineboot -k ;;
    -w|--wait) exit 0 ;;
    *) echo "wineserver relay: unsupported arguments: $*" >&2; exit 2 ;;
esac
"""

# Sourced by the relay scripts and by the launcher (same NVIDIA setup in both,
# otherwise Proton re-creates the prefix's NVAPI DLLs on every other call).
_PROTON11_ENV = r"""# Generated by td-install (--runner proton11); rewritten by 'td-install --update'.
# Your own settings go in proton11.user.env (never overwritten).
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L 2>/dev/null | grep -q '^GPU '; then
    # nvcuda / nvenc / nvml / nvoptix bridges bundled with the runner, plus NVAPI
    export PROTON_NVIDIA_LIBS="${PROTON_NVIDIA_LIBS-1}"
    export PROTON_ENABLE_NVAPI="${PROTON_ENABLE_NVAPI-1}"
    # Hybrid laptops: DXVK/vkd3d list GPUs in Vulkan order, where the iGPU can
    # come first, and NVIDIA Flow then creates its D3D12 device on the wrong GPU.
    # This hides the other GPUs from DXVK/vkd3d only; TouchDesigner's own
    # Vulkan device is not affected.
    export DXVK_FILTER_DEVICE_NAME="${DXVK_FILTER_DEVICE_NAME-NVIDIA}"
    export VKD3D_FILTER_DEVICE_NAME="${VKD3D_FILTER_DEVICE_NAME-NVIDIA}"
    if [ -d "$WINEPREFIX/drive_c/Program Files/NVIDIA Corporation/NVIDIA Video Effects" ]; then
        export NV_VIDEO_EFFECTS_PATH='C:\Program Files\NVIDIA Corporation\NVIDIA Video Effects'
    fi
fi
"""


def write_relay_scripts() -> None:
    from .wine import RUNNER_DIR

    bin_dir = os.path.join(RUNNER_DIR, "bin")
    ensure_dir(bin_dir)
    scripts = {
        "wine64": _RELAY_WINE64,
        "wine": _RELAY_WINE64,
        "wineboot": _RELAY_WINEBOOT,
        "wineserver": _RELAY_WINESERVER,
    }
    for name, content in scripts.items():
        path = os.path.join(bin_dir, name)
        with open(path, "w") as f:
            f.write(content)
        os.chmod(path, 0o755)
    with open(PROTON11_ENV_FILE, "w") as f:
        f.write(_PROTON11_ENV)


def _relay(args: list[str], timeout: int):
    """Run ``<runner>/bin/wine64 <args>``; None if it timed out or is missing."""
    from .wine import RUNNER_DIR

    wine64 = os.path.join(RUNNER_DIR, "bin", "wine64")
    try:
        return subprocess.run(
            [wine64] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _tail(result, lines: int = 12) -> None:
    if result is None:
        info("  (no output: the command timed out or could not start)")
        return
    for line in ((result.stdout or "") + (result.stderr or "")).strip().splitlines()[-lines:]:
        info(f"  {line}")


# ── Runner download ──────────────────────────────────────────────────────────


def download_proton11_runner() -> None:
    """Download, verify and extract DAW-GE-Proton11, then install the relay scripts."""
    from .wine import RUNNER_DIR

    require_umu()
    ensure_runner_compatible(RUNNER_PROTON11)

    installed = os.path.isfile(os.path.join(RUNNER_DIR, "proton")) and os.path.isfile(
        os.path.join(RUNNER_DIR, "files", "bin", "wine")
    )
    if installed:
        success(f"{PROTON11_NAME} already installed")
    else:
        info(f"Downloading {PROTON11_NAME} (~550 MB)...")
        tarball = os.path.join(TD_BASE_DIR, "proton11-runner.tar.gz")
        ensure_dir(TD_BASE_DIR)
        if not download_file(PROTON11_URL, tarball, PROTON11_NAME):
            error("Failed to download the Proton runner")
            safe_rm(tarball)
            raise SystemExit(1)
        if not verify_checksum(tarball, PROTON11_SHA256):
            error("Proton runner checksum mismatch; refusing to use it")
            safe_rm(tarball)
            raise SystemExit(1)

        info("Extracting the Proton runner...")
        if os.path.isdir(RUNNER_DIR):
            safe_rm(RUNNER_DIR)
        ensure_dir(RUNNER_DIR)
        try:
            subprocess.run(
                ["tar", "-xzf", tarball, "-C", RUNNER_DIR, "--strip-components=1"],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            error(f"Failed to extract the Proton runner: {e.stderr or e}")
            safe_rm(tarball)
            raise SystemExit(1)
        safe_rm(tarball)
        if not os.path.isfile(os.path.join(RUNNER_DIR, "proton")):
            error("Proton runner extraction failed: 'proton' script not found")
            raise SystemExit(1)
        success(f"{PROTON11_NAME} installed")

    write_relay_scripts()
    set_runner_kind(RUNNER_PROTON11)
    install_patched_qcap()


# ── Prefix + fonts ───────────────────────────────────────────────────────────


def _kill_prefix_processes() -> None:
    _relay(["wineboot", "-k"], timeout=120)


def setup_proton_prefix() -> None:
    from .wine import WINE_PREFIX

    drive_c = os.path.join(WINE_PREFIX, "drive_c")
    if os.path.isdir(drive_c):
        result = _relay(["cmd", "/c", "exit"], timeout=600)
        if result is not None and result.returncode == 0:
            success("Wine prefix already initialized")
            return
        warning("Existing Wine prefix looks broken, recreating...")
        _kill_prefix_processes()
        safe_rm(WINE_PREFIX)

    info("Initializing the Proton prefix...")
    info("The first run downloads the Steam Linux Runtime (a few hundred MB): this can take several minutes.")
    ensure_dir(WINE_PREFIX)
    result = _relay(["wineboot", "-u"], timeout=3600)
    if result is None or result.returncode != 0 or not os.path.isdir(drive_c):
        error("Proton prefix initialization failed")
        _tail(result)
        raise SystemExit(1)
    _kill_prefix_processes()
    success("Wine prefix initialized")


def install_proton_fonts() -> None:
    """Fonts via umu's winetricks (``allfonts``, the recipe validated on this runner).

    DXVK / vcrun are deliberately not installed: Proton manages its own DXVK and
    re-copies it on every launch, and TouchDesigner starts without vcrun here.
    """
    info("Installing fonts (winetricks allfonts)...")
    result = _relay(["winetricks", "-q", "allfonts"], timeout=3600)
    if result is None or result.returncode != 0:
        error("Font installation failed (text would not render)")
        _tail(result)
        info("Re-run the same td-install command to retry.")
        raise SystemExit(1)
    success("Fonts installed")


# ── NVIDIA support ───────────────────────────────────────────────────────────


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nvidia_driver_works() -> bool:
    if not shutil.which("nvidia-smi"):
        return False
    try:
        out = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True, timeout=15)
    except (subprocess.TimeoutExpired, OSError):
        return False
    # "nvidia-smi -L" exits 0 even when it prints "No devices found." (driver
    # loaded but the GPU dropped off), so the exit code alone proves nothing
    return out.returncode == 0 and any(line.startswith("GPU ") for line in out.stdout.splitlines())


def nvidia_compute_cap() -> str | None:
    """Compute capability of the first NVIDIA GPU (e.g. "8.6"), or None."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    lines = out.stdout.strip().splitlines() if out.returncode == 0 else []
    return lines[0].strip() if lines else None


def vfx_arch_for_compute_cap(compute_cap: str | None) -> str | None:
    """Map a compute capability to the NVIDIA Video Effects installer, or None."""
    return _COMPUTE_CAP_TO_ARCH.get((compute_cap or "").strip())


def _install_patched_lib(name: str, rel: str, url: str, sha256: str, what: str, effect: str, failure: str) -> bool:
    """Replace one library of the runner with a patched build, keeping the stock file as .orig.

    ``name`` is for messages, ``rel`` the path inside the runner. True if the patched file
    is in place.
    """
    from .wine import RUNNER_DIR

    dest = os.path.join(RUNNER_DIR, rel)
    if not os.path.isdir(os.path.dirname(dest)):
        warning(f"This Proton build has no bundled {name}; {failure}")
        return False
    if os.path.isfile(dest) and _sha256(dest) == sha256:
        success(f"Patched {name} already in place")
        return True

    info(f"Downloading the patched {what}...")
    tmp = os.path.join(TD_BASE_DIR, f"{name}-patched.dll.so")
    if not download_file(url, tmp, f"patched {name}", show_progress=False):
        warning(f"Could not download the patched {name}: {failure}")
        warning(f"  ({url})")
        safe_rm(tmp)
        return False
    if not verify_checksum(tmp, sha256):
        error(f"Patched {name} checksum mismatch; not installing it")
        safe_rm(tmp)
        return False

    dest_dir = os.path.dirname(dest)
    backup = dest + ".orig"
    try:
        os.chmod(dest_dir, 0o755)
        if os.path.isfile(dest) and not os.path.exists(backup):
            shutil.copy2(dest, backup)
        staged = dest + ".new"
        shutil.copy2(tmp, staged)
        os.chmod(staged, 0o755)
        os.replace(staged, dest)
    except OSError as e:
        warning(f"Could not install the patched {name}: {e}")
        return False
    finally:
        safe_rm(tmp)
    success(f"Patched {name} installed ({effect})")
    return True


def install_patched_nvcuda() -> bool:
    """Replace the bundled nvcuda with the Wine 11 patched build. True if in place."""
    return _install_patched_lib(
        "nvcuda", _NVCUDA_REL, NVCUDA_PATCHED_URL, NVCUDA_PATCHED_SHA256,
        what="CUDA bridge (nvcuda)", effect="CUDA TOPs enabled",
        failure="NVIDIA CUDA TOPs will not work",
    )


def install_patched_nvenc() -> bool:
    """Replace the bundled NVENC bridge with the build that lists the input formats."""
    return _install_patched_lib(
        "nvenc", _NVENC_REL, NVENC_PATCHED_URL, NVENC_PATCHED_SHA256,
        what="NVENC bridge (video encoding)", effect="Video Stream Out can encode",
        failure="the Video Stream Out TOP will report an unsupported pixel format",
    )


def install_patched_qcap() -> bool:
    """Replace the runner's qcap (PE dll + unix library) with the webcam-release build.

    Both files must match each other, so they are replaced together and rolled back
    together. Returns True when the patched pair is in place.
    """
    from .wine import RUNNER_DIR

    targets = [(name, os.path.join(RUNNER_DIR, rel), sha) for name, rel, sha in _QCAP_FILES]
    if not all(os.path.isfile(dest) for _, dest, _ in targets):
        warning("This Proton build has no qcap; the webcam fix is not installed")
        return False
    if all(_sha256(dest) == sha for _, dest, sha in targets):
        success("Patched webcam capture module (qcap) already in place")
        return True

    info("Downloading the patched webcam capture module (qcap)...")
    archive = os.path.join(TD_BASE_DIR, "qcap-patched.tar.gz")
    if not download_file(QCAP_PATCHED_URL, archive, "patched qcap", show_progress=False):
        warning("Could not download the patched qcap: a Video Device In TOP will lock the camera after its first use")
        warning(f"  ({QCAP_PATCHED_URL})")
        safe_rm(archive)
        return False
    if not verify_checksum(archive, QCAP_PATCHED_SHA256):
        error("Patched qcap checksum mismatch; not installing it")
        safe_rm(archive)
        return False

    staging = tempfile.mkdtemp(prefix=".qcap-", dir=TD_BASE_DIR)
    installed: list[str] = []
    try:
        # Read only the two expected members, by name: nothing from the archive is
        # ever written to a path it chose
        with tarfile.open(archive, "r:gz") as tar:
            for name, _, sha in targets:
                member = tar.extractfile(name)
                if member is None:
                    raise RuntimeError(f"{name} missing from the archive")
                with open(os.path.join(staging, name), "wb") as out:
                    shutil.copyfileobj(member, out)
                if _sha256(os.path.join(staging, name)) != sha:
                    raise RuntimeError(f"{name} does not match its pinned checksum")

        for _, dest, _ in targets:
            backup = dest + ".orig"
            if not os.path.exists(backup):
                shutil.copy2(dest, backup)
        for name, dest, _ in targets:
            staged = dest + ".new"
            shutil.copy2(os.path.join(staging, name), staged)
            os.chmod(staged, 0o755)
            os.replace(staged, dest)
            installed.append(dest)
    except (OSError, RuntimeError, tarfile.TarError) as e:
        for dest in installed:  # never leave a mismatched PE / unix pair
            shutil.copy2(dest + ".orig", dest)
        warning(f"Could not install the patched qcap: {e}")
        return False
    finally:
        safe_rm(staging)
        safe_rm(archive)
    success("Patched webcam capture module installed (Video Device In releases the camera)")
    return True


def install_nvidia_vfx_sdk() -> bool:
    """Download NVIDIA's Video Effects SDK runtime and unpack it into the prefix."""
    from .wine import WINE_PREFIX

    arch = vfx_arch_for_compute_cap(nvidia_compute_cap())
    if not arch:
        warning("Your GPU is not covered by the NVIDIA Video Effects SDK (needs an RTX 20 series or newer); skipping")
        return False
    target = os.path.join(WINE_PREFIX, VFX_DIR_REL)
    if os.path.isfile(os.path.join(target, "NVVideoEffects.dll")):
        success("NVIDIA Video Effects SDK already installed")
        return True
    if not shutil.which("7z"):
        warning("7z is needed to unpack the NVIDIA Video Effects SDK; skipping")
        return False

    expected = VFX_SHA256.get(arch, "")
    if not expected:
        # verify_checksum() treats an empty hash as "nothing to check"
        error(f"No pinned checksum for the {arch} NVIDIA Video Effects SDK; refusing to download it")
        return False
    url = VFX_URL.format(version=VFX_VERSION, arch=arch)
    info(f"Downloading the NVIDIA Video Effects SDK {VFX_VERSION} for {arch} (~770 MB)...")
    installer = os.path.join(TD_BASE_DIR, f"nvidia-vfx-{arch}.exe")
    if not download_file(url, installer, "NVIDIA Video Effects SDK", timeout=60):
        warning("Could not download the NVIDIA Video Effects SDK; skipping")
        safe_rm(installer)
        return False
    if not verify_checksum(installer, expected):
        error("NVIDIA Video Effects SDK checksum mismatch; not installing it")
        safe_rm(installer)
        return False

    # Extract next to the final location so the last step is a rename, not a 1.2 GB copy
    parent = os.path.dirname(target)
    ensure_dir(parent)
    staging = tempfile.mkdtemp(prefix=".vfx-", dir=parent)
    try:
        info("Unpacking the NVIDIA Video Effects SDK...")
        subprocess.run(
            ["7z", "x", installer, f"-o{staging}", "-y"],
            check=True,
            capture_output=True,
        )
        # The NSIS installer's own plumbing is not part of the SDK
        safe_rm(os.path.join(staging, "$PLUGINSDIR"))
        safe_rm(os.path.join(staging, "uninstall.exe.nsis"))
        if not os.path.isfile(os.path.join(staging, "NVVideoEffects.dll")):
            raise RuntimeError("NVVideoEffects.dll not found in the installer")
        if os.path.isdir(target):
            safe_rm(target)
        os.replace(staging, target)
        os.chmod(target, 0o755)  # mkdtemp() creates it 0700
    except (subprocess.CalledProcessError, RuntimeError, OSError) as e:
        warning(f"Could not unpack the NVIDIA Video Effects SDK: {e}")
        safe_rm(staging)
        return False
    finally:
        safe_rm(installer)
    success("NVIDIA Video Effects SDK installed")
    return True


def install_nvidia_extras(vfx: bool | None, interactive: bool) -> None:
    """NVIDIA TOP support. ``vfx``: True = install the SDK, False = skip, None = ask."""
    if not nvidia_driver_works():
        info("No working NVIDIA driver detected: skipping the NVIDIA TOP support")
        return
    info("Setting up NVIDIA CUDA and video encoding support...")
    install_patched_nvcuda()
    install_patched_nvenc()

    if vfx is None:
        if not interactive:
            info("NVIDIA Background / Denoise / Upscaler TOPs need NVIDIA's Video Effects SDK (~770 MB).")
            info("  Add it later with: td-install --runner proton11 --nvidia-vfx")
            return
        try:
            answer = input(
                "Download NVIDIA's Video Effects SDK (~770 MB) for the NVIDIA Background / Denoise / Upscaler TOPs? [y/N] "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        vfx = answer in ("y", "yes")
    if vfx:
        install_nvidia_vfx_sdk()


def update_proton_runner() -> None:
    """``--update``: refresh relay scripts / env and re-apply the nvcuda patch."""
    write_relay_scripts()
    success("Runner scripts updated")
    install_patched_qcap()
    if nvidia_driver_works():
        install_patched_nvcuda()
        install_patched_nvenc()
