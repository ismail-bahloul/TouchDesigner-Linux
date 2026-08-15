"""Distribution detection and system package installation."""

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass

from .utils import Colors, debug, error, info, run_optional, success, warning

# ── Distro detection ─────────────────────────────────────────────────────────


@dataclass
class DistroInfo:
    """Detected distribution information."""

    id: str
    name: str
    package_manager: str  # pacman | apt | dnf | zypper
    distro_name: str  # Human-readable distro name


# Known distro IDs mapped to package manager + display name
KNOWN_DISTROS: dict[str, tuple[str, str]] = {
    "arch": ("pacman", "Arch Linux"),
    "manjaro": ("pacman", "Manjaro"),
    "endeavouros": ("pacman", "EndeavourOS"),
    "garuda": ("pacman", "Garuda Linux"),
    "garudalinux": ("pacman", "Garuda Linux"),
    "artix": ("pacman", "Artix Linux"),
    "rebornos": ("pacman", "RebornOS"),
    "archcraft": ("pacman", "Archcraft"),
    "cachyos": ("pacman", "CachyOS"),
    "steamos": ("pacman", "SteamOS"),
    "ubuntu": ("apt", "Ubuntu"),
    "linuxmint": ("apt", "Linux Mint"),
    "pop": ("apt", "Pop!_OS"),
    "pop_os": ("apt", "Pop!_OS"),
    "debian": ("apt", "Debian"),
    "zorin": ("apt", "Zorin OS"),
    "elementary": ("apt", "elementary OS"),
    "neon": ("apt", "KDE Neon"),
    "kali": ("apt", "Kali Linux"),
    "parrot": ("apt", "Parrot OS"),
    "mx": ("apt", "MX Linux"),
    "lmde": ("apt", "Linux Mint Debian Edition"),
    "fedora": ("dnf", "Fedora"),
    "rocky": ("dnf", "Rocky Linux"),
    "rocky-linux": ("dnf", "Rocky Linux"),
    "almalinux": ("dnf", "AlmaLinux"),
    "alma": ("dnf", "AlmaLinux"),
    "centos": ("dnf", "CentOS"),
}


def detect_distro() -> DistroInfo:
    """Detect the Linux distribution and package manager."""

    os_id = ""
    os_id_like = ""
    os_name = "Unknown Linux"

    if os.path.isfile("/etc/os-release"):
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("ID="):
                    os_id = line.split("=", 1)[1].strip().strip('"').lower()
                elif line.startswith("ID_LIKE="):
                    os_id_like = line.split("=", 1)[1].strip().strip('"').lower()
                elif line.startswith("PRETTY_NAME="):
                    os_name = line.split("=", 1)[1].strip().strip('"')

    # Direct match
    if os_id in KNOWN_DISTROS:
        pm, display = KNOWN_DISTROS[os_id]
        return DistroInfo(os_id, os_name, pm, display)

    # openSUSE (supports version suffixes like opensuse-leap, opensuse-tumbleweed)
    if re.match(r"opensuse|suse", os_id):
        return DistroInfo(os_id, os_name, "zypper", "openSUSE/SUSE")

    # Fallback by ID_LIKE
    if os_id_like:
        if "arch" in os_id_like:
            return DistroInfo(os_id, os_name, "pacman", "Arch-based Linux")
        if "ubuntu" in os_id_like or "debian" in os_id_like:
            return DistroInfo(os_id, os_name, "apt", "Ubuntu/Debian-based Linux")
        if "fedora" in os_id_like or "rhel" in os_id_like:
            return DistroInfo(os_id, os_name, "dnf", "Fedora/RHEL-based Linux")
        if "suse" in os_id_like:
            return DistroInfo(os_id, os_name, "zypper", "SUSE-based Linux")

    # Last resort: detect by available package manager binary
    if shutil.which("pacman"):
        return DistroInfo(os_id, os_name, "pacman", "Pacman-based Linux")
    if shutil.which("dnf"):
        return DistroInfo(os_id, os_name, "dnf", "DNF-based Linux")
    if shutil.which("apt-get"):
        return DistroInfo(os_id, os_name, "apt", "APT-based Linux")
    if shutil.which("zypper"):
        return DistroInfo(os_id, os_name, "zypper", "openSUSE/SUSE")

    info(f"Unsupported distribution: {os_name}")
    return DistroInfo(os_id, os_name, "unknown", "Unknown Linux")


# ── Package installation ─────────────────────────────────────────────────────

PACMAN_PACKAGES = [
    "curl",
    "wget",
    "tar",
    "xz",
    "cabextract",
    "unzip",
    "p7zip",
    "innoextract",
    "mesa-utils",
    "vulkan-tools",
    "vulkan-icd-loader",
    "lib32-vulkan-icd-loader",
    "lib32-glib2",
    "lib32-gcc-libs",
    "lib32-libx11",
    "libx11",
    "lib32-libxext",
    "lib32-libxrender",
    "lib32-libxrandr",
    "lib32-libxi",
    "lib32-libxcursor",
    "lib32-libxfixes",
    "lib32-libxinerama",
    "lib32-libxxf86vm",
    "lib32-libxcomposite",
    "lib32-libunwind",
    "lib32-gnutls",
    "lib32-freetype2",
    "lib32-fontconfig",
    "lib32-alsa-lib",
    "xorg-xwayland",
]

APT_PACKAGES = [
    "curl",
    "wget",
    "tar",
    "xz-utils",
    "cabextract",
    "unzip",
    "p7zip-full",
    "innoextract",
    "libvulkan1",
    "libvulkan1:i386",
    "vulkan-tools",
    "libglib2.0-0",
    "libglib2.0-0:i386",
    "libx11-6",
    "libx11-6:i386",
    "libxext6",
    "libxext6:i386",
    "libxrender1",
    "libxrender1:i386",
    "libxrandr2",
    "libxrandr2:i386",
    "libxi6",
    "libxi6:i386",
    "libxcursor1",
    "libxcursor1:i386",
    "libxfixes3",
    "libxfixes3:i386",
    "libxinerama1",
    "libxinerama1:i386",
    "libxxf86vm1",
    "libxxf86vm1:i386",
    "libgl1",
    "libgl1:i386",
    "libegl1",
    "libegl1:i386",
    "libc6",
    "libc6:i386",
    "libunwind8",
    "libunwind8:i386",
    "libfreetype6",
    "libfreetype6:i386",
    "libfontconfig1",
    "libfontconfig1:i386",
    "libgcc-s1",
    "libgcc-s1:i386",
    "libstdc++6",
    "libstdc++6:i386",
    "mesa-utils",
    "xwayland",
]

DNF_PACKAGES = [
    "curl",
    "wget",
    "tar",
    "xz",
    "cabextract",
    "unzip",
    "p7zip",
    "innoextract",
    "vulkan-loader",
    "vulkan-loader.i686",
    "mesa-vulkan-drivers",
    "vulkan-tools",
    "mesa-demos",
    "xorg-x11-server-Xwayland",
    "libunwind",
    "libunwind.i686",
    "glibc",
    "glibc.i686",
    "libgcc",
    "libgcc.i686",
    "libstdc++",
    "libstdc++.i686",
    "gnutls",
    "gnutls.i686",
    "freetype",
    "freetype.i686",
    "fontconfig",
    "fontconfig.i686",
    "alsa-lib",
    "alsa-lib.i686",
    "libX11",
    "libX11.i686",
    "libXext",
    "libXext.i686",
    "libXcomposite",
    "libXcomposite.i686",
    "libXrender",
    "libXrender.i686",
    "libXrandr",
    "libXrandr.i686",
    "libXi",
    "libXi.i686",
    "libXcursor",
    "libXcursor.i686",
    "libXfixes",
    "libXfixes.i686",
    "libXinerama",
    "libXinerama.i686",
    "libXxf86vm",
    "libXxf86vm.i686",
    "mesa-libGL",
    "mesa-libGL.i686",
    "mesa-libGLU",
    "mesa-libGLU.i686",
    "mesa-libEGL",
    "mesa-libEGL.i686",
    "glib2",
    "glib2.i686",
    "mesa-vulkan-drivers.i686",
]

ZYPPER_BASE_PACKAGES = [
    "curl",
    "wget",
    "tar",
    "xz",
    "cabextract",
    "unzip",
    "p7zip",
    "libvulkan1",
    "libvulkan1-32bit",
    "vulkan-tools",
]

# Zypper package name aliases (try first, fallback to second)
ZYPPER_ALIASES: dict[str, list[str]] = {
    "Mesa-demo-x": ["Mesa-demo-x"],
    "libglib-2_0-0": ["libglib-2_0-0", "glib2"],
    "libglib-2_0-0-32bit": ["libglib-2_0-0-32bit", "glib2-32bit"],
    "libX11-6": ["libX11-6"],
    "libX11-6-32bit": ["libX11-6-32bit"],
    "libXext6": ["libXext6"],
    "libXext6-32bit": ["libXext6-32bit"],
    "libXrender1": ["libXrender1"],
    "libXrender1-32bit": ["libXrender1-32bit"],
    "libXrandr2": ["libXrandr2"],
    "libXrandr2-32bit": ["libXrandr2-32bit"],
    "libXi6": ["libXi6"],
    "libXi6-32bit": ["libXi6-32bit"],
    "libXcursor1": ["libXcursor1"],
    "libXcursor1-32bit": ["libXcursor1-32bit"],
    "libXfixes3": ["libXfixes3"],
    "libXfixes3-32bit": ["libXfixes3-32bit"],
    "libXinerama1": ["libXinerama1"],
    "libXinerama1-32bit": ["libXinerama1-32bit"],
    "libXxf86vm1": ["libXxf86vm1"],
    "libXxf86vm1-32bit": ["libXxf86vm1-32bit"],
    "libXcomposite1": ["libXcomposite1"],
    "libXcomposite1-32bit": ["libXcomposite1-32bit"],
    "libunwind8": ["libunwind8", "libunwind"],
    "libunwind8-32bit": ["libunwind8-32bit", "libunwind-32bit"],
    "libgnutls30": ["libgnutls30", "gnutls"],
    "libgnutls30-32bit": ["libgnutls30-32bit", "gnutls-32bit"],
    "libfreetype6": ["libfreetype6", "freetype2"],
    "libfreetype6-32bit": ["libfreetype6-32bit", "freetype2-32bit"],
    "libfontconfig1": ["libfontconfig1", "fontconfig"],
    "libfontconfig1-32bit": ["libfontconfig1-32bit", "fontconfig-32bit"],
    "libasound2": ["libasound2", "alsa"],
    "libasound2-32bit": ["libasound2-32bit", "alsa-32bit"],
    "libgcc_s1": ["libgcc_s1"],
    "libgcc_s1-32bit": ["libgcc_s1-32bit"],
    "libstdc++6": ["libstdc++6"],
    "libstdc++6-32bit": ["libstdc++6-32bit"],
    "libGL1": ["libGL1", "Mesa-libGL1"],
    "libGL1-32bit": ["libGL1-32bit", "Mesa-libGL1-32bit"],
    "libEGL1": ["libEGL1", "Mesa-libEGL1"],
    "libEGL1-32bit": ["libEGL1-32bit", "Mesa-libEGL1-32bit"],
    "innoextract": ["innoextract"],
}

ARCH_RUNTIME_CHECK = [
    "xorg-xwayland",
    "vulkan-icd-loader",
    "lib32-vulkan-icd-loader",
    "lib32-glib2",
    "lib32-gcc-libs",
    "lib32-libx11",
    "lib32-libxext",
    "lib32-libxrender",
    "lib32-libxrandr",
    "lib32-libxi",
    "lib32-libxcursor",
    "lib32-libxfixes",
    "lib32-libxinerama",
    "lib32-libxxf86vm",
    "lib32-libxcomposite",
    "lib32-libunwind",
    "lib32-gnutls",
    "lib32-freetype2",
    "lib32-fontconfig",
    "lib32-alsa-lib",
]


def install_packages(distro: DistroInfo) -> None:
    """Install system packages required for TouchDesigner."""

    match distro.package_manager:
        case "pacman":
            _install_pacman()
            _check_arch_runtime()
        case "apt":
            _install_apt()
        case "dnf":
            _install_dnf()
        case "zypper":
            _install_zypper()
        case _:
            raise SystemExit(f"Unsupported package manager: {distro.package_manager}")

    success("System packages installed")


# ── Pacman ───────────────────────────────────────────────────────────────────


def _install_pacman() -> None:
    # SteamOS (and forks like HoloISO) ship a read-only root filesystem:
    # pacman cannot write until it is disabled. The signal is the
    # distro-specific tool itself, not the ID — keying on it covers every
    # SteamOS-like system. Must run before touching /etc/pacman.conf.
    if shutil.which("steamos-readonly"):
        info("Read-only root detected (SteamOS): disabling it to install packages...")
        try:
            subprocess.run(
                ["sudo", "steamos-readonly", "disable"],
                check=True,
            )
        except subprocess.CalledProcessError:
            error("Could not disable the read-only filesystem (steamos-readonly disable)")
            info("Run it manually, then re-run the installer: sudo steamos-readonly disable")
            raise SystemExit(1)

    info("Enabling multilib repository if needed...")
    _enable_pacman_multilib()

    info("Installing required packages...")
    try:
        subprocess.run(
            ["sudo", "pacman", "-S", "--needed", "--noconfirm", "--quiet"]
            + PACMAN_PACKAGES,
            check=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        error("Failed to install packages. Try: sudo pacman -Syu")
        raise SystemExit(1)


def _enable_pacman_multilib() -> None:
    """Uncomment [multilib] section in pacman.conf."""
    conf_path = "/etc/pacman.conf"
    if not os.path.isfile(conf_path):
        return

    with open(conf_path) as f:
        content = f.read()

    if "#[multilib]" not in content:
        return

    # Uncomment the [multilib] section header and its Include line
    content = content.replace("#[multilib]", "[multilib]", 1)
    content = content.replace(
        "#Include = /etc/pacman.d/mirrorlist",
        "Include = /etc/pacman.d/mirrorlist",
        1,
    )

    # Write back using sudo
    try:
        subprocess.run(
            ["sudo", "tee", conf_path],
            input=content.encode(),
            check=True,
        )
    except subprocess.CalledProcessError:
        warning("Could not enable multilib (may already be enabled)")


def _check_arch_runtime() -> None:
    """Check and install missing Arch runtime dependencies."""
    info("Checking Arch runtime dependencies...")

    try:
        missing: list[str] = []
        for pkg in ARCH_RUNTIME_CHECK:
            result = subprocess.run(
                ["pacman", "-Q", pkg],
                capture_output=True,
            )
            if result.returncode != 0:
                missing.append(pkg)

        # NVIDIA-specific packages
        if shutil.which("nvidia-smi"):
            for pkg in ["lib32-libglvnd", "lib32-nvidia-utils"]:
                result = subprocess.run(
                    ["pacman", "-Q", pkg],
                    capture_output=True,
                )
                if result.returncode != 0:
                    missing.append(pkg)

        if not missing:
            success("Arch runtime dependency check passed")
            return
    except KeyboardInterrupt:
        print()
        raise

    warning(f"Missing {len(missing)} runtime package(s), installing...")
    try:
        subprocess.run(
            ["sudo", "pacman", "-S", "--needed", "--noconfirm"] + missing,
            check=True,
            capture_output=True,
        )
        success("Arch runtime dependencies repaired")
    except subprocess.CalledProcessError:
        error("Unable to install Arch runtime packages")
        info(f"Try: sudo pacman -S --needed {' '.join(missing)}")
        raise SystemExit(1)
    except KeyboardInterrupt:
        print()
        raise


# ── APT ──────────────────────────────────────────────────────────────────────


def _install_apt() -> None:
    info("Enabling 32-bit architecture...")
    run_optional(["sudo", "dpkg", "--add-architecture", "i386"])

    info("Refreshing apt package index...")
    try:
        subprocess.run(
            ["sudo", "apt-get", "update"],
            check=True,
        )
    except subprocess.CalledProcessError:
        error("Failed to refresh apt package index")
        info("Try: sudo apt-get update")
        raise SystemExit(1)

    # Resolve libasound package name (different on Ubuntu 24.04+)
    asound_pkg = _apt_resolve_asound()

    packages = list(APT_PACKAGES)

    if asound_pkg:
        packages.append(asound_pkg)
        asound_i386 = f"{asound_pkg}:i386"
        if _apt_has_candidate(asound_i386):
            packages.append(asound_i386)

    info("Installing required packages...")
    try:
        subprocess.run(
            ["sudo", "apt-get", "install", "-y"] + packages,
            check=True,
        )
    except subprocess.CalledProcessError:
        error("Failed to install packages")
        info("Try: sudo apt-get update && sudo apt-get upgrade")
        raise SystemExit(1)


def _apt_resolve_asound() -> str | None:
    """Return the correct libasound package name for this Debian/Ubuntu version."""
    if _apt_has_candidate("libasound2"):
        return "libasound2"
    if _apt_has_candidate("libasound2t64"):
        return "libasound2t64"
    return None


def _apt_has_candidate(pkg: str) -> bool:
    """Check if apt has an install candidate for a package."""
    result = subprocess.run(
        ["apt-cache", "policy", pkg],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    for line in result.stdout.splitlines():
        if "Candidate:" in line:
            candidate = line.split(":", 1)[1].strip()
            return bool(candidate) and candidate != "(none)"
    return False


# ── DNF ──────────────────────────────────────────────────────────────────────


def _install_dnf() -> None:
    # Enable RPM Fusion on Fedora
    _enable_rpm_fusion()

    info("Installing required packages...")
    try:
        subprocess.run(
            ["sudo", "dnf", "install", "-y"] + DNF_PACKAGES,
            check=True,
        )
    except subprocess.CalledProcessError:
        error("Failed to install packages")
        info("Try: sudo dnf upgrade --refresh")
        raise SystemExit(1)


def _enable_rpm_fusion() -> None:
    """Enable RPM Fusion free repository on Fedora."""
    try:
        result = subprocess.run(
            ["rpm", "-E", "%fedora"],
            capture_output=True,
            text=True,
        )
        fedora_ver = result.stdout.strip()
        if not fedora_ver.isdigit():
            return

        url = (
            f"https://mirrors.rpmfusion.org/free/fedora/"
            f"rpmfusion-free-release-{fedora_ver}.noarch.rpm"
        )
        subprocess.run(
            ["sudo", "dnf", "install", "-y", url],
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass  # Non-fatal


# ── Zypper ───────────────────────────────────────────────────────────────────


def _install_zypper() -> None:
    info("Installing required packages...")
    packages = list(ZYPPER_BASE_PACKAGES)

    for key, aliases in ZYPPER_ALIASES.items():
        pkg = _zypper_resolve(aliases)
        if pkg:
            packages.append(pkg)

    try:
        subprocess.run(
            ["sudo", "zypper", "install", "-y"] + packages,
            check=True,
        )
    except subprocess.CalledProcessError:
        error("Failed to install packages")
        info("Try: sudo zypper refresh && sudo zypper update")
        raise SystemExit(1)


def _zypper_resolve(aliases: list[str]) -> str | None:
    """Try each package alias and return the first installed or available one."""
    for pkg in aliases:
        # RPM check
        result = subprocess.run(
            ["rpm", "-q", pkg],
            capture_output=True,
        )
        if result.returncode == 0:
            return pkg

        # Zypper search
        result = subprocess.run(
            ["zypper", "-x", "search", "--match-exact", "--type", "package", pkg],
            capture_output=True,
            text=True,
        )
        if f'name="{pkg}"' in result.stdout:
            return pkg

    warning(f"Could not resolve package: {' / '.join(aliases)}")
    return None
