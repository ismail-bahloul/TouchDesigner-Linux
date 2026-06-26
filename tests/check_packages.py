#!/usr/bin/env python3
"""
Validate that all packages in the distro package lists exist
in the package manager's repositories.

Called by CI after installing dependencies on each distro container.
"""
import subprocess
import sys


def check_packages(pkg_manager: str, packages: list[str]) -> int:
    """Check each package exists. Returns number of missing packages."""
    print(f"  Checking {len(packages)} packages with {pkg_manager}...")
    missing = []

    for pkg in packages:
        cmd = _check_cmd(pkg_manager, pkg)
        if cmd is None:
            print(f"  Unknown package manager: {pkg_manager}")
            return len(packages)

        result = subprocess.run(cmd, capture_output=True, timeout=15)
        if result.returncode != 0:
            # Try alternative name
            alt = _alt_name(pkg_manager, pkg)
            if alt:
                result2 = subprocess.run(
                    _check_cmd(pkg_manager, alt), capture_output=True, timeout=15
                )
                if result2.returncode == 0:
                    continue

            missing.append(pkg)

    if missing:
        print(f"  Missing packages: {missing}")
    else:
        print(f"  OK — all {len(packages)} packages found")

    return len(missing)


def _check_cmd(pkg_manager: str, pkg: str) -> list[str] | None:
    match pkg_manager:
        case "apt":
            return ["apt-cache", "show", pkg]
        case "dnf":
            return ["dnf", "info", pkg]
        case "pacman":
            return ["pacman", "-Si", pkg]
        case "zypper":
            return ["zypper", "--non-interactive", "info", pkg]
        case _:
            return None


def _alt_name(pkg_manager: str, pkg: str) -> str | None:
    """Return alternative package name for known renames."""
    # Arch: p7zip -> 7zip
    if pkg_manager == "pacman" and pkg == "p7zip":
        return "7zip"
    return None


def main():
    from td_lib.distro import (
        APT_PACKAGES,
        DNF_PACKAGES,
        PACMAN_PACKAGES,
        ZYPPER_BASE_PACKAGES,
        detect_distro,
    )

    d = detect_distro()

    print(f"\nDistro: {d.distro_name} ({d.package_manager})")
    print(f"ID: {d.id}")

    total_missing = 0

    match d.package_manager:
        case "apt":
            total_missing += check_packages("apt", APT_PACKAGES)
        case "dnf":
            total_missing += check_packages("dnf", DNF_PACKAGES)
        case "pacman":
            total_missing += check_packages("pacman", PACMAN_PACKAGES)
        case "zypper":
            total_missing += check_packages("zypper", ZYPPER_BASE_PACKAGES)
        case "unknown":
            print("  Unknown package manager — skipping package check")
            return 0
        case _:
            print(f"  Unsupported package manager: {d.package_manager}")
            return 1

    print()
    if total_missing > 0:
        print(f"  ✗ {total_missing} package(s) missing")
        return 1

    print(f"  ✓ All packages validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
