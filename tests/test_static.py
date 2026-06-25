#!/usr/bin/env python3
"""
Test script for TouchDesigner-Linux V2.
Runs static validation without sudo or actual installation.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0
FAIL = 0


def check(name: str, ok: bool):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ✓  {name}")
    else:
        FAIL += 1
        print(f"  ✗  {name}")


def test_imports():
    print("\n── Imports ──")
    from td_lib import __version__

    check(f"td_lib version = {__version__}", bool(__version__))

    from td_lib.cli import parse_args

    check("cli.parse_args", True)

    from td_lib.utils import download_file, error, info, success

    check("utils", True)

    from td_lib.distro import DistroInfo, detect_distro

    d = detect_distro()
    check(f"distro.detect_distro() = {d.distro_name} ({d.package_manager})", True)

    from td_lib.wine import (
        RUNNER_DIR,
        WINE_PREFIX,
        WINETRICKS_BIN,
        download_soda_runner,
        setup_wine_prefix,
    )

    check(f"wine paths: {RUNNER_DIR}", True)

    from td_lib.touchdesigner import (
        DOWNLOAD_DIR,
        TD_INSTALL_DIR,
        detect_version_from_exe,
        fetch_available_versions,
    )

    check(f"touchdesigner paths: {TD_INSTALL_DIR}", True)

    from td_lib.patcher import check_ids_patch_status, patch_ids_dlls

    check("patcher", True)

    from td_lib.launcher import create_launcher_script

    check("launcher", True)

    from td_lib.desktop import create_shortcuts, install_icons, register_mime_types

    check("desktop", True)

    from td_lib.diagnose import run_diagnose

    check("diagnose", True)

    from td_lib.install import run_install

    check("install", True)

    from td_lib.update import run_update

    check("update", True)

    from td_lib.cleanup import run_uninstall, show_uninstall_menu

    check("cleanup", True)


def test_cli_args():
    print("\n── CLI args ──")
    from td_lib.cli import parse_args

    args = parse_args(["--install", "--dry-run"])
    check("--install --dry-run", args.action == "install" and args.dry_run)

    args = parse_args(["--diagnose"])
    check("--diagnose", args.diagnose)

    args = parse_args(["--headless", "--non-interactive"])
    check("--headless -n", args.headless and args.non_interactive)

    args = parse_args(["-V"])
    check("--version", args.version)


def test_dry_run():
    print("\n── Dry-run ──")
    from td_lib.cli import parse_args
    from td_lib.install import run_install

    args = parse_args(["--install", "--dry-run", "--headless"])
    try:
        run_install(args)
        check("install dry-run (headless)", True)
    except Exception as e:
        check(f"install dry-run failed: {e}", False)


def test_diagnose_output():
    print("\n── Diagnose output ──")
    result = subprocess.run(
        [sys.executable, "-m", "td_lib.diagnose"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), ".."),
    )
    check("diagnose runs without error", result.returncode == 0)


def test_version_select():
    print("\n── Version selection ──")
    from td_lib.touchdesigner import fetch_available_versions

    versions = fetch_available_versions()
    check(f"fetched {len(versions)} versions", len(versions) > 0)
    check("first version is 2025.x", versions[0].startswith("2025"))


def test_desktop_assets():
    print("\n── Desktop assets ──")
    script_dir = os.path.join(os.path.dirname(__file__), "..")
    icons = [
        "Assets/Icons/TouchDesigner.svg",
        "Assets/Icons/TouchDesigner-toe.svg",
        "Assets/Icons/TouchDesigner-tox.svg",
    ]
    for icon in icons:
        path = os.path.join(script_dir, icon)
        check(f"{icon} exists", os.path.isfile(path))

    tox = os.path.join(script_dir, "Assets", "wine_ui_fixes.tox")
    check("wine_ui_fixes.tox exists", os.path.isfile(tox))


def test_launcher_script():
    print("\n── Launcher script generation ──")
    import tempfile

    from td_lib.launcher import create_launcher_script

    # Test without NVIDIA offload
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys; sys.path.insert(0, '.')
from td_lib.launcher import create_launcher_script
path = create_launcher_script(nvidia_offload=False)
print(path)
""",
        ],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), ".."),
    )
    check("launcher script generated", result.returncode == 0)


def main():
    print("=" * 60)
    print("  TouchDesigner-Linux V2 — Test Suite")
    print("=" * 60)

    test_imports()
    test_cli_args()
    test_dry_run()
    test_version_select()
    test_desktop_assets()
    test_launcher_script()

    print(f"\n{'=' * 60}")
    print(f"  Results: {PASS} passed, {FAIL} failed")
    print(f"{'=' * 60}")

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
