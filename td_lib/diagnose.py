"""System health check (--diagnose)."""

import os
import shutil
import subprocess
import sys

from . import __version__
from .utils import (
    TD_BASE_DIR,
    Colors,
    error,
    info,
    print_banner,
    print_hr,
    success,
    warning,
)


def run_diagnose():
    """Print a full system health report."""
    if sys.stdout.isatty():
        print("\033[2J\033[H", end="")
    print_banner(__version__)
    print(f"\n{Colors.bold}System Health Check{Colors.nc}\n")
    print_hr()

    _check_os()
    _check_container()
    _check_gpu()
    _check_disk()
    _check_td_base()
    _check_wine()
    _check_td_versions()
    _check_ids_patch()

    print_hr()
    print(
        f"\n  {Colors.green}Done.{Colors.nc} Paste this output if reporting an issue.\n"
    )


def _check_os():
    info("OS / Kernel:")
    os_info = _read_os_release()
    print(f"  Distro: {os_info}")
    print(f"  Kernel: {os.uname().release}")
    print(f"  Arch:   {os.uname().machine}")
    print()


def _read_os_release() -> str:
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return "Unknown"


def _check_container():
    info("Container mode:")
    from .container import (
        CONTAINER_NAME,
        container_exists,
        find_backend,
        find_distrobox,
        is_inside_distrobox,
    )

    if is_inside_distrobox():
        print("  location:  inside the container")
        print("  (distrobox itself only exists on the host — this is normal)")
        print()
        return

    distrobox = find_distrobox()
    if not distrobox:
        print("  distrobox: not installed (container mode unavailable)")
        print("  Install: curl -sSL https://distrobox.it/install | sh")
    else:
        print(f"  distrobox: {distrobox}")
        print(f"  backend:   {find_backend() or 'none — install podman or docker'}")
        if container_exists(CONTAINER_NAME):
            print(f"  container '{CONTAINER_NAME}': created")
            print("  usage:     td-install --container <action>")
        else:
            print(f"  container '{CONTAINER_NAME}': not created")
            print("  usage:     td-install --container install")
    print()


def _check_gpu():
    info("Graphics:")
    # lspci
    try:
        result = subprocess.run(["lspci"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.splitlines():
            if any(x in line.lower() for x in ["vga", "3d controller", "display"]):
                print(f"  GPU: {line.strip()}")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # NVIDIA
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        try:
            result = subprocess.run(
                [nvidia_smi, "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.stdout.strip():
                print(f"  NVIDIA: {result.stdout.strip()}")
        except subprocess.TimeoutExpired:
            pass

    # Vulkan
    vulkaninfo = shutil.which("vulkaninfo")
    if vulkaninfo:
        try:
            result = subprocess.run(
                [vulkaninfo, "--summary"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if "Vulkan Instance" in result.stdout:
                success("  Vulkan: available")
            else:
                warning("  Vulkan: not detected")
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            warning("  Vulkan: not detected")
    else:
        warning("  vulkaninfo not found")

    print()


def _check_disk():
    info("Disk:")
    td_dir = TD_BASE_DIR
    try:
        stat = os.statvfs(td_dir)
        free_gb = (stat.f_frsize * stat.f_bfree) / (1024**3)
        print(f"  TD_BASE_DIR: {td_dir}")
        print(f"  Free space:  {free_gb:.1f} GB")
    except OSError:
        warning(f"  TD_BASE_DIR: {td_dir} (unreachable)")
    print()


def _check_td_base():
    info("TouchDesigner base directory:")
    td_dir = TD_BASE_DIR

    if not os.path.isdir(td_dir):
        warning(f"  {td_dir} — not found")
        print()
        return

    total_size = 0
    for root, dirs, files in os.walk(td_dir):
        for f in files:
            try:
                total_size += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass

    size_mb = total_size / (1024**2)
    print(f"  Path: {td_dir}")
    print(f"  Size: {size_mb:.0f} MB")
    print()


def _check_wine():
    info("Wine environment:")
    runner_dir = os.path.join(TD_BASE_DIR, "runner")
    prefix_dir = os.path.join(TD_BASE_DIR, "prefix")

    wine64 = os.path.join(runner_dir, "bin", "wine64")
    if os.path.isfile(wine64):
        try:
            result = subprocess.run(
                [wine64, "--version"], capture_output=True, text=True, timeout=5
            )
            print(f"  Runner: {result.stdout.strip()}")
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            warning("  Runner: Soda Wine (version check failed)")

    if os.path.isdir(prefix_dir):
        print(f"  Prefix: {prefix_dir}")
    else:
        warning("  Prefix: not initialized")

    print()


def _check_td_versions():
    info("Installed TouchDesigner versions:")
    found = False

    # Check Wine prefix (curl install method)
    drive_c = os.path.join(TD_BASE_DIR, "prefix", "drive_c")
    if os.path.isdir(drive_c):
        for root, dirs, files in os.walk(drive_c):
            for f in files:
                if f.lower() == "touchdesigner.exe":
                    found = True
                    version = _detect_td_version(os.path.join(root, f))
                    install_dir = os.path.relpath(root, drive_c)
                    version_str = version or "(unknown version)"
                    print(f"  {install_dir} \u2192 {version_str}")

    # Check AUR package path
    aur_td = "/opt/touchdesigner/td"
    if os.path.isdir(aur_td):
        for root, dirs, files in os.walk(aur_td):
            for f in files:
                if f.lower() == "touchdesigner.exe":
                    found = True
                    version = _detect_td_version(os.path.join(root, f))
                    version_str = version or "(unknown version)"
                    print(f"  /opt/touchdesigner/td/ \u2192 {version_str}")

    if not found:
        warning(
            "  No TouchDesigner.exe found (checked Wine prefix and /opt/touchdesigner)"
        )

    print()


def _detect_td_version(exe_path: str) -> str | None:
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
                    if p.startswith("20") and "." in p:
                        return p
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        pass
    return None


def _check_ids_patch():
    """Check IDS Peak SDK patch status."""
    info("IDS Peak SDK patch status:")
    from .patcher import check_ids_patch_status

    status = check_ids_patch_status()

    if not status:
        info("  No IDS Peak SDK DLLs found (not installed or already removed)")
        print()
        return

    for dll_name, patched in status.items():
        status_str = (
            f"{Colors.green}patched{Colors.nc}"
            if patched
            else f"{Colors.red}not patched{Colors.nc}"
        )
        print(f"  {dll_name}: {status_str}")

    print()
