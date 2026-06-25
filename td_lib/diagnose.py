"""System health check (--diagnose)."""

import os
import shutil
import subprocess

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
    print_banner("2.0-dev")
    print(f"\n{Colors.bold}System Health Check{Colors.nc}\n")
    print_hr()

    _check_os()
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
    prefix_dir = os.path.join(TD_BASE_DIR, "prefix")
    drive_c = os.path.join(prefix_dir, "drive_c")

    if not os.path.isdir(drive_c):
        warning("  No TouchDesigner installation found")
        print()
        return

    found = False
    for root, dirs, files in os.walk(drive_c):
        for f in files:
            if f.lower() == "touchdesigner.exe":
                found = True
                version = _detect_td_version(os.path.join(root, f))
                install_dir = os.path.relpath(root, drive_c)
                version_str = version or "(unknown version)"
                print(f"  {install_dir} → {version_str}")

    if not found:
        warning("  No TouchDesigner.exe found in Wine prefix")

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
    info("IDS Peak SDK patch status:")
    prefix_dir = os.path.join(TD_BASE_DIR, "prefix")
    ids_dlls = [
        "ids_peak_ipl.dll",
        "ids_peak_afl.dll",
        "ids_peak_ifl.dll",
        "ids_peak_comfort_c.dll",
    ]

    found_any = False
    for dll in ids_dlls:
        dll_path = _find_file(prefix_dir, dll)
        if dll_path:
            found_any = True
            patched = _is_ids_patched(dll_path)
            status = (
                f"{Colors.green}patched{Colors.nc}"
                if patched
                else f"{Colors.red}not patched{Colors.nc}"
            )
            print(f"  {dll}: {status}")

    if not found_any:
        info("  No IDS Peak SDK DLLs found (not installed or already removed)")

    print()


def _find_file(base_dir: str, filename: str) -> str | None:
    """Walk a directory and return the first match for filename."""
    if not os.path.isdir(base_dir):
        return None
    for root, dirs, files in os.walk(base_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None


def _is_ids_patched(dll_path: str) -> bool:
    """Check if AddressOfEntryPoint is already zeroed (patched)."""
    import struct

    try:
        with open(dll_path, "rb") as f:
            data = bytearray(f.read())
        e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
        ep_offset = e_lfanew + 4 + 20 + 16
        ep = struct.unpack_from("<I", data, ep_offset)[0]
        return ep == 0
    except (IOError, struct.error, IndexError):
        return False
