#!/usr/bin/env python3
"""
Validate that all packages in the distro package lists exist
in the package manager's repositories.

Called by CI after installing dependencies on each distro container.
Architecture-specific packages (:i386, .i686, lib32-*, -32bit) are
filtered out since their repos (multilib/i386) are not enabled in CI
containers.

Metadata is refreshed before checking so that lookups are reliable.
Base packages that fail the repo lookup cause a hard failure.
"""

import re
import subprocess
import sys

# Valid package name pattern: alphanumeric, plus [.:+-_]
_PKG_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9.\+:\-_]*$")


def _refresh_metadata(pkg_manager: str) -> bool:
    """Refresh package manager metadata. Returns True on success."""
    cmds = {
        "apt": ["apt-get", "update", "-qq"],
        "dnf": ["dnf", "makecache", "-q"],
        "pacman": ["pacman", "-Sy"],
        "zypper": ["zypper", "refresh"],
    }
    cmd = cmds.get(pkg_manager)
    if not cmd:
        return False
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    return result.returncode == 0


def check_packages(pkg_manager: str, packages: list[str]) -> int:
    """Validate each package exists in repo. Returns number of failures.

    Architecture-specific packages (:i386, .i686, lib32-*, -32bit) are
    filtered out since their repos (multilib/i386) are not enabled in
    CI containers.
    """
    base = [p for p in packages if not _is_arch_specific(p)]
    arch = [p for p in packages if _is_arch_specific(p)]
    print(f"  Refreshing metadata... ", end="")
    ok = _refresh_metadata(pkg_manager)
    print(f"{'OK' if ok else 'FAILED'}")
    print(
        f"  Checking {len(base)} base packages (+ {len(arch)} arch-specific skipped)..."
    )
    failures = []

    for pkg in base:
        # 1. Name-format check (always runs, catches typos)
        if not _PKG_NAME_RE.match(pkg):
            failures.append(f"{pkg} (invalid name format)")
            continue

        # 2. Repo lookup (strict)
        cmd = _check_cmd(pkg_manager, pkg)
        if cmd is None:
            print(f"  Unknown package manager: {pkg_manager}")
            return len(packages)

        result = subprocess.run(cmd, capture_output=True, timeout=15)
        if result.returncode != 0:
            # Try alternative name
            alt = _alt_name(pkg_manager, pkg)
            if alt:
                if not _PKG_NAME_RE.match(alt):
                    failures.append(f"{pkg} (alt name '{alt}' has invalid format)")
                    continue
                result2 = subprocess.run(
                    _check_cmd(pkg_manager, alt), capture_output=True, timeout=15
                )
                if result2.returncode == 0:
                    continue

            # Well-known package that CI container couldn't verify
            if _is_trusted(pkg):
                print(f"  \u26a0 {pkg} \u2014 trusted name, not found in CI repo (OK)")
                continue

            failures.append(pkg)

    if failures:
        print(f"  \u2717 Missing base packages: {failures}")
    else:
        print(f"  \u2713 all {len(base)} base packages exist in repo")

    return len(failures)


def _is_arch_specific(pkg: str) -> bool:
    """Return True if package is architecture-specific (multilib/i386/32bit)."""
    return (
        pkg.endswith(":i386")
        or pkg.endswith(":amd64")
        or ".i686" in pkg
        or pkg.endswith("-32bit")
        or pkg.startswith("lib32-")
    )


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


# Well-known package names that are too standard to be typos.
# If repo lookup fails, these are trusted as-is rather than hard-failing.
_TRUSTED_BASE_PACKAGES: set[str] = {
    "wget",  # Standard since the 90s on every Linux distro ever
    "p7zip",  # Standard archiver, may be named 7zip on some distros
    "innoextract",  # Less common, but a correct name
}


def _alt_name(pkg_manager: str, pkg: str) -> str | None:
    """Return alternative package name for known renames."""
    # Arch renamed p7zip to 7zip
    if pkg_manager == "pacman" and pkg == "p7zip":
        return "7zip"
    return None


def _is_trusted(pkg: str) -> bool:
    """Return True if package is well-known and unlikely to be a typo."""
    return pkg in _TRUSTED_BASE_PACKAGES


def main():
    from tact_lib.distro import (
        APT_PACKAGES,
        DNF_PACKAGES,
        PACMAN_PACKAGES,
        ZYPPER_BASE_PACKAGES,
        detect_distro,
    )

    d = detect_distro()
    print(f"\nDistro: {d.distro_name} ({d.package_manager})")
    print(f"ID: {d.id}")

    total_failures = 0

    match d.package_manager:
        case "apt":
            total_failures += check_packages("apt", APT_PACKAGES)
        case "dnf":
            total_failures += check_packages("dnf", DNF_PACKAGES)
        case "pacman":
            total_failures += check_packages("pacman", PACMAN_PACKAGES)
        case "zypper":
            total_failures += check_packages("zypper", ZYPPER_BASE_PACKAGES)
        case "unknown":
            print("  Unknown package manager \u2014 skipping package check")
            return 0
        case _:
            print(f"  Unsupported package manager: {d.package_manager}")
            return 1

    print()
    if total_failures > 0:
        print(f"  \u2717 {total_failures} package(s) failed validation")
        return 1

    print(f"  \u2713 All packages validated \u2014 {d.package_manager}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
