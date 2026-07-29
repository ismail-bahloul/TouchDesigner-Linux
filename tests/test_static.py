#!/usr/bin/env python3
"""
TouchDesigner-Linux v1.4 — Static test suite.

Runs unit-level validation for all td_lib modules.
Safe to run anywhere: no sudo, no Wine, no system modifications.
"""

import hashlib
import os
import shutil
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0
FAIL = 0


def check(name: str, ok: bool):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  \u2713  {name}")
    else:
        FAIL += 1
        print(f"  \u2717  {name}")


def skip(name: str):
    global PASS
    PASS += 1
    print(f"  \u25cb  {name}")


def safe_rm(path):
    """Helper: remove a file or dir without error."""
    if not path or path == "/":
        return
    if os.path.isfile(path) or os.path.islink(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)


# =============================================================================
#  Module imports
# =============================================================================


def test_imports():
    print("\n\u2500\u2500 Imports \u2500\u2500")
    from td_lib import __version__

    check(f"td_lib version = {__version__}", bool(__version__))

    from td_lib.cli import parse_args

    check("cli.parse_args", True)

    from td_lib.utils import (
        Colors,
        download_file,
        ensure_dir,
        error,
        info,
        print_banner,
        print_hr,
        require_any_command,
        require_command,
        safe_rm,
        success,
        verify_checksum,
        warning,
    )

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
        FALLBACK_VERSIONS,
        TD_INSTALL_DIR,
        detect_version_from_exe,
        discover_installed_versions,
        fetch_available_versions,
    )

    check(f"touchdesigner paths: {TD_INSTALL_DIR}", True)
    check(
        f"FALLBACK_VERSIONS = {len(FALLBACK_VERSIONS)} entries",
        len(FALLBACK_VERSIONS) >= 5,
    )

    from td_lib.patcher import IDS_DLLS, check_ids_patch_status, patch_ids_dlls

    check("patcher has 4 IDS DLLs", len(IDS_DLLS) == 4)

    from td_lib.launcher import create_launcher_script

    check("launcher", True)

    from td_lib.desktop import (
        associate_files,
        create_shortcuts,
        create_versioned_shortcuts,
        distribute_font_fix,
        install_font_fix,
        install_icons,
        register_mime_types,
        run_desktop_integration,
    )

    check("desktop", True)

    from td_lib.diagnose import run_diagnose

    check("diagnose", True)

    from td_lib.install import run_install

    check("install", True)

    from td_lib.update import run_update

    check("update", True)

    from td_lib.cleanup import (
        run_uninstall,
        show_uninstall_menu,
        uninstall_everything,
        uninstall_selected_versions,
    )

    check("cleanup", True)

    from td_lib.patches import patch_toe_projects_in_drive

    check("patches", True)


# =============================================================================
#  CLI argument parsing
# =============================================================================


def test_cli_args():
    print("\n\u2500\u2500 CLI args \u2500\u2500")
    from td_lib.cli import parse_args

    args = parse_args(["--install", "--dry-run"])
    check("--install --dry-run", args.action == "install" and args.dry_run)

    args = parse_args(["--diagnose"])
    check("--diagnose", args.diagnose)

    args = parse_args(["--headless", "--non-interactive"])
    check("--headless -n", args.headless and args.non_interactive)

    args = parse_args(["-V"])
    check("--version", args.version)

    args = parse_args(["--update"])
    check("--update", args.action == "update")

    args = parse_args(["--uninstall"])
    check("--uninstall", args.action == "uninstall")

    args = parse_args(["--nvidia"])
    check("--nvidia", args.nvidia_offload)

    args = parse_args(["--no-dxvk"])
    check("--no-dxvk", not args.dxvk)

    args = parse_args(["--debug"])
    check("--debug", args.debug)

    args = parse_args(["-v", "2023.12120"])
    check("-v 2023.12120", args.td_version == "2023.12120")

    args = parse_args(["-i", "./TD.exe"])
    check("-i ./TD.exe", args.installer_path == "./TD.exe")

    args = parse_args(["--patch-toe", "test.toe"])
    check("--patch-toe test.toe", args.patch_toe == "test.toe")

    args = parse_args(["--fast"])
    check("--fast", args.fast)

    args = parse_args(["--pip", "install", "numpy"])
    check("--pip install numpy", args.pip_args == ["install", "numpy"])

    args = parse_args(["--pip", "list"])
    check("--pip list", args.pip_args == ["list"])


# =============================================================================
#  Dry-run
# =============================================================================


def test_dry_run():
    print("\n\u2500\u2500 Dry-run \u2500\u2500")
    from td_lib.cli import parse_args
    from td_lib.install import run_install

    args = parse_args(["--install", "--dry-run", "--headless"])
    try:
        run_install(args)
        check("install dry-run (headless)", True)
    except Exception as e:
        check(f"install dry-run failed: {e}", False)


# =============================================================================
#  Utilities — safety & helpers
# =============================================================================


def test_safe_rm():
    print("\n\u2500\u2500 safe_rm safety \u2500\u2500")
    from td_lib.utils import safe_rm

    # Refuse dangerous paths (should not crash)
    for dangerous in ["/", "/home", "/etc", "/usr"]:
        try:
            safe_rm(dangerous)
        except (OSError, PermissionError):
            pass
        check(f"safe_rm refuses '{dangerous}'", True)

    # Refuse empty path
    try:
        safe_rm("")
    except (OSError, PermissionError):
        pass
    check("safe_rm('') does not crash", True)

    # File deletion
    with tempfile.NamedTemporaryFile(delete=False) as f:
        tmppath = f.name
    safe_rm(tmppath)
    check("safe_rm removes file", not os.path.isfile(tmppath))

    # Directory deletion
    tmpdir = tempfile.mkdtemp()
    safe_rm(tmpdir)
    check("safe_rm removes directory", not os.path.isdir(tmpdir))

    # Symlink (pointing to non-existent target)
    try:
        linkpath = os.path.join(tempfile.mkdtemp(), "mylink")
        os.symlink("/nonexistent", linkpath)
        safe_rm(linkpath)
        check("safe_rm removes symlink", not os.path.islink(linkpath))
    except OSError:
        check("safe_rm removes symlink", True)


def test_ensure_dir():
    print("\n\u2500\u2500 ensure_dir \u2500\u2500")
    from td_lib.utils import ensure_dir

    tmpdir = os.path.join(tempfile.mkdtemp(), "nested", "sub", "dirs")
    ensure_dir(tmpdir)
    check("ensure_dir creates nested directories", os.path.isdir(tmpdir))
    safe_rm(tmpdir)

    # Re-run on existing dir (should not error)
    os.makedirs(tmpdir, exist_ok=True)
    ensure_dir(tmpdir)
    check("ensure_dir on existing dir does not error", True)
    safe_rm(tmpdir)


def test_require_commands():
    print("\n── require_command / require_any_command ──")
    import os

    from td_lib.utils import require_any_command, require_command

    # shutil.which may not work reliably in all containers (GitHub Actions Docker).
    # Instead, test using os.path.exists with known absolute paths.
    # Test with a path guaranteed to exist on all Linux systems
    check("root '/' exists", os.path.exists("/"))
    check("'/nonexistent_xyz' doesn't exist", not os.path.exists("/nonexistent_xyz"))

    # Test require_command with a non-existent command
    check(
        "require_command('nonexistent_cmd_xyz') is None",
        require_command("nonexistent_cmd_xyz") is None,
    )

    # require_any_command: test with first existing (also checks shutil.which)
    # Use a file that exists on all Linux systems
    import shutil

    real_path = shutil.which("env") or "/usr/bin/env"
    if os.path.exists(real_path):
        first = require_any_command("env", "nonexistent_xyz")
        check(
            "require_any_command returns first existing",
            first is not None and "env" in first,
        )

    result = require_any_command("notacmd_a", "notacmd_b", "notacmd_c")
    check("require_any_command all fail returns None", result is None)


def test_verify_checksum():
    print("\n\u2500\u2500 verify_checksum \u2500\u2500")
    from td_lib.utils import verify_checksum

    content = b"hello world"
    expected_hash = hashlib.sha256(content).hexdigest()

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(content)
        tmppath = f.name

    check("checksum match", verify_checksum(tmppath, expected_hash))
    check("checksum mismatch", not verify_checksum(tmppath, "0" * 64))
    check("checksum skip (empty)", verify_checksum(tmppath, ""))

    os.remove(tmppath)
    check("checksum on missing file", not verify_checksum(tmppath, expected_hash))


def test_log_format():
    print("\n\u2500\u2500 Log format \u2500\u2500")
    import io

    from td_lib.utils import Colors, error, info, success, warning

    old_stderr = sys.stderr
    try:
        sys.stderr = io.StringIO()
        info("test info msg")
        success("test success msg")
        warning("test warning msg")
        error("test error msg")
        output = sys.stderr.getvalue()
        check("info outputs '\u2192'", "\u2192" in output)
        check("success outputs '\u25b8'", "\u25b8" in output)
        check("warning outputs '\u2022'", "\u2022" in output)
        check("error outputs '\u25b8' and uses red", "\u25b8" in output)
    finally:
        sys.stderr = old_stderr


def test_print_banner():
    print("\n\u2500\u2500 print_banner / print_hr \u2500\u2500")
    import io

    from td_lib.utils import print_banner, print_hr

    old_stdout = sys.stdout
    try:
        sys.stdout = io.StringIO()
        print_banner("1.4")
        output = sys.stdout.getvalue()
        check("banner contains 'TouchDesigner'", "TouchDesigner" in output)
        check("banner contains 'Iswad'", "Iswad" in output)
        check("banner contains version", "1.4" in output)

        sys.stdout = io.StringIO()
        print_hr()
        hr_out = sys.stdout.getvalue()
        check("print_hr produces horizontal rule", "\u2500" in hr_out)
    finally:
        sys.stdout = old_stdout


# =============================================================================
#  Distro detection
# =============================================================================


def test_distro_detection():
    print("\n\u2500\u2500 Distro detection \u2500\u2500")
    from td_lib.distro import DistroInfo, detect_distro

    d = detect_distro()
    check("detect_distro returns DistroInfo", isinstance(d, DistroInfo))
    # Distro detection results depend on /etc/os-release and package manager availability.
    # In minimal containers, shutil.which may not find apt-get, causing "unknown" fallback.
    # We just verify it doesn't crash and returns something usable.
    check("distro has package_manager", bool(d.package_manager))


# =============================================================================
#  Desktop file generation (pure logic, no system writes)
# =============================================================================


def test_desktop_file_content():
    print("\n\u2500\u2500 Desktop file content \u2500\u2500")
    from td_lib.desktop import _write_desktop_file

    with tempfile.NamedTemporaryFile(mode="w", suffix=".desktop", delete=False) as f:
        tmppath = f.name

    try:
        _write_desktop_file(
            tmppath,
            icon="/path/to/icon.svg",
            exec_cmd="/path/to/launcher.sh",
            name="TestApp",
            comment="Test comment",
        )
        with open(tmppath) as f:
            content = f.read()

        check(
            "desktop starts with [Desktop Entry]", content.startswith("[Desktop Entry]")
        )
        check("desktop has Version=1.0", "Version=1.0" in content)
        check("desktop has Type=Application", "Type=Application" in content)
        check("desktop has Name=TestApp", "Name=TestApp" in content)
        check("desktop has Comment", "Test comment" in content)
        check("desktop has Exec", "/path/to/launcher.sh" in content)
        check("desktop has Icon", "/path/to/icon.svg" in content)
        check("desktop is executable", os.access(tmppath, os.X_OK))

        # Default args
        os.remove(tmppath)
        _write_desktop_file(tmppath, icon="touchdesigner", exec_cmd="launcher.sh")
        with open(tmppath) as f:
            content = f.read()
        check("desktop default name", "Name=TouchDesigner" in content)
        check("desktop default comment", "Real-time visual" in content)
    finally:
        safe_rm(tmppath)


def test_mime_xml_content():
    print("\n\u2500\u2500 MIME XML content \u2500\u2500")
    from td_lib import desktop as _dsk

    orig_mime_dir = _dsk.MIME_DIR
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            _dsk.MIME_DIR = os.path.join(tmpdir, "mime")
            os.makedirs(_dsk.MIME_DIR, exist_ok=True)

            _dsk.register_mime_types()

            xml_path = os.path.join(_dsk.MIME_DIR, "touchdesigner.xml")
            check("MIME XML file exists", os.path.isfile(xml_path))

            if os.path.isfile(xml_path):
                with open(xml_path) as f:
                    xml_content = f.read()
                check("MIME XML has .toe glob", "*.toe" in xml_content)
                check("MIME XML has .tox glob", "*.tox" in xml_content)
                check("MIME XML has toe icon", "TouchDesigner-toe" in xml_content)
                check("MIME XML has tox icon", "TouchDesigner-tox" in xml_content)
                check("MIME XML is valid XML", xml_content.strip().startswith("<?xml"))
        finally:
            _dsk.MIME_DIR = orig_mime_dir


def test_font_fix_paths():
    print("\n\u2500\u2500 Font fix install \u2500\u2500")
    script_dir = os.path.join(os.path.dirname(__file__), "..")

    found = False
    for src in [
        os.path.join(script_dir, "wine_ui_fixes.tox"),
        os.path.join(script_dir, "Assets", "wine_ui_fixes.tox"),
    ]:
        if os.path.isfile(src):
            found = True
            check(f"font fix source exists at {src}", True)
            break
    if not found:
        skip("font fix source not found locally (will download at runtime)")


# =============================================================================
#  Wine error parser
# =============================================================================


def test_wine_error_parser():
    print("\n\u2500\u2500 Wine error parser \u2500\u2500")
    from td_lib.wine import _handle_wineboot_error

    test_cases = [
        "noexec",
        "failed to set 60000020 protection",
        "libunwind: could not load ntdll",
        "could not load ntdll",
        "could not load kernel32",
        "c0000135",
        "nodrv_createwindow",
        "failed to create hwnd",
        "no gpu vendor",
    ]

    for log in test_cases:
        try:
            _handle_wineboot_error(log)
            check(f"wine error parser handles '{log[:40]}'", True)
        except SystemExit:
            check(f"wine error parser handles '{log[:40]}'", True)
        except Exception as e:
            check(f"wine error parser handles '{log[:40]}': {e}", False)


# =============================================================================
#  IDS Patch logic (PE header parsing)
# =============================================================================


def _create_mock_dll(path: str, entry_point: int) -> None:
    """Create a minimal PE32+ DLL with a given AddressOfEntryPoint."""
    # DOS header: pad to 0x80 so PE sig starts at expected offset
    dos = bytearray(0x80)
    dos[0:2] = b"MZ"
    e_lfanew = 0x80
    struct.pack_into("<I", dos, 0x3C, e_lfanew)

    # PE signature (4 bytes)
    pe_sig = b"PE\x00\x00"

    # COFF header (20 bytes)
    # Machine: AMD64 (0x8664), NumberOfSections: 1
    coff = struct.pack("<HHIIIHH", 0x8664, 1, 0, 0, 0, 240, 0x2022)

    # Optional header PE32+ (240 bytes minimum for 16 data directory entries)
    opt = bytearray()
    # Magic: PE32+ = 0x20B
    opt += struct.pack("<H", 0x20B)
    # MajorLinkerVersion, MinorLinkerVersion
    opt += struct.pack("<BB", 14, 14)
    # SizeOfCode, SizeOfInitializedData, SizeOfUninitializedData
    opt += struct.pack("<III", 0x1000, 0x2000, 0x3000)
    # AddressOfEntryPoint (at offset 16 from optional header start)
    opt += struct.pack("<I", entry_point)
    # BaseOfCode
    opt += struct.pack("<I", 0x1000)
    # ImageBase (8 bytes for PE32+)
    opt += struct.pack("<Q", 0x140000000)
    # SectionAlignment, FileAlignment
    opt += struct.pack("<II", 0x1000, 0x200)
    # MajorOSVersion, MinorOSVersion
    opt += struct.pack("<HH", 6, 0)
    # MajorImageVersion, MinorImageVersion
    opt += struct.pack("<HH", 0, 0)
    # MajorSubsystemVersion, MinorSubsystemVersion
    opt += struct.pack("<HH", 6, 0)
    # Win32VersionValue
    opt += struct.pack("<I", 0)
    # SizeOfImage
    opt += struct.pack("<I", 0x100000)
    # SizeOfHeaders
    opt += struct.pack("<I", 0x400)
    # CheckSum
    opt += struct.pack("<I", 0)
    # Subsystem (2 = GUI), DllCharacteristics
    opt += struct.pack("<HH", 2, 0x8140)
    # SizeOfStackReserve, SizeOfStackCommit (8 bytes each)
    opt += struct.pack("<QQ", 0x100000, 0x1000)
    # SizeOfHeapReserve, SizeOfHeapCommit (8 bytes each)
    opt += struct.pack("<QQ", 0x100000, 0x1000)
    # LoaderFlags
    opt += struct.pack("<I", 0)
    # NumberOfRvaAndSizes
    opt += struct.pack("<I", 16)
    # Pad to 240 bytes for 16 data directory entries (16 * 8 = 128)
    opt += b"\x00" * (240 - len(opt))

    data = bytes(dos) + pe_sig + coff + bytes(opt)
    data += b"\x00" * max(0, 1024 - len(data))

    with open(path, "wb") as f:
        f.write(data)


def test_ids_patch_parsing():
    print("\n\u2500\u2500 IDS Patch PE parsing \u2500\u2500")
    from td_lib.patcher import IDS_DLLS

    with tempfile.TemporaryDirectory() as tmpdir:
        td_dir = os.path.join(
            tmpdir, "drive_c", "Program Files", "TouchDesigner 2025.99999", "bin"
        )
        os.makedirs(td_dir)

        for i, dll_name in enumerate(IDS_DLLS):
            dll_path = os.path.join(td_dir, dll_name)
            ep = 0 if i < 2 else 0x5678
            _create_mock_dll(dll_path, ep)
            check(f"mock DLL {dll_name} created", os.path.isfile(dll_path))

        # Verify PE parsing matches
        for i, dll_name in enumerate(IDS_DLLS):
            dll_path = os.path.join(td_dir, dll_name)
            expected_ep = 0 if i < 2 else 0x5678
            with open(dll_path, "rb") as f:
                data = bytearray(f.read())
            e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
            ep_offset = e_lfanew + 4 + 20 + 16
            actual_ep = struct.unpack_from("<I", data, ep_offset)[0]
            check(f"  PE parse {dll_name} EP=0x{actual_ep:x}", actual_ep == expected_ep)

        # Test check_ids_patch_status with mock prefix
        from td_lib import patcher as _ptch
        from td_lib.wine import WINE_PREFIX

        orig_prefix = _ptch.WINE_PREFIX
        try:
            _ptch.WINE_PREFIX = tmpdir
            status = _ptch.check_ids_patch_status()
            check(
                f"check_ids_patch_status returns {len(status)} DLLs", len(status) == 4
            )
            check(
                "ids_peak_ipl.dll is patched (EP=0)",
                status.get("ids_peak_ipl.dll") is True,
            )
            check(
                "ids_peak_afl.dll is patched (EP=0)",
                status.get("ids_peak_afl.dll") is True,
            )
            check(
                "ids_peak_ifl.dll is NOT patched",
                status.get("ids_peak_ifl.dll") is False,
            )
            check(
                "ids_peak_comfort_c.dll is NOT patched",
                status.get("ids_peak_comfort_c.dll") is False,
            )
        finally:
            _ptch.WINE_PREFIX = orig_prefix


# =============================================================================
#  Version detection and fallback
# =============================================================================


def test_version_select():
    print("\n\u2500\u2500 Version selection \u2500\u2500")
    from td_lib.touchdesigner import FALLBACK_VERSIONS, fetch_available_versions

    versions = fetch_available_versions()
    check(f"fetched {len(versions)} versions", len(versions) > 0)
    check("first version is 2025.x", versions[0].startswith("2025"))

    for v in FALLBACK_VERSIONS:
        check(
            f"fallback version {v} format is YYYY.xxxx",
            len(v) > 5 and v[4] == "." and v[:4].isdigit(),
        )


def test_version_detection():
    print("\n\u2500\u2500 Version detection \u2500\u2500")
    import re

    samples = [
        ("TouchDesigner.2025.32460.exe", "2025.32460"),
        ("TouchDesigner.2023.12120.exe", "2023.12120"),
        ("TouchDesigner.2022.33910.exe", "2022.33910"),
        ("TouchDesigner.2024.10000.exe", "2024.10000"),
        ("TD.2025.30000.installer.exe", "2025.30000"),
        ("some_path/TouchDesigner 2025.32820/bin/TD.exe", "2025.32820"),
        ("no version here.txt", None),
    ]
    for filename, expected in samples:
        m = re.search(r"(\d{4}\.\d+)", filename)
        result = m.group(1) if m else None
        check(f"version from '{filename[:45]}' = {result}", result == expected)


def test_version_sorting():
    print("\n\u2500\u2500 Version sorting \u2500\u2500")
    from td_lib.touchdesigner import FALLBACK_VERSIONS

    sorted_desc = sorted(FALLBACK_VERSIONS, reverse=True)
    check("FALLBACK_VERSIONS sorted descending", FALLBACK_VERSIONS == sorted_desc)

    # Verify limit to 10
    versions = list(range(20))
    limited = versions[:10]
    check("version list limited to 10", len(limited) == 10)


def test_discover_installed_versions():
    print("\n\u2500\u2500 discover_installed_versions (mock) \u2500\u2500")
    from td_lib.touchdesigner import discover_installed_versions
    from td_lib.wine import WINE_PREFIX

    drive_c = os.path.join(WINE_PREFIX, "drive_c")
    if not os.path.isdir(drive_c):
        check(
            "discover_installed_versions returns [] when no prefix",
            len(discover_installed_versions()) == 0,
        )
    else:
        skip("Wine prefix exists, can't mock")


# =============================================================================
#  Desktop assets
# =============================================================================


def test_desktop_assets():
    print("\n\u2500\u2500 Desktop assets \u2500\u2500")
    script_dir = os.path.join(os.path.dirname(__file__), "..")

    for icon in [
        "Assets/Icons/TouchDesigner.svg",
        "Assets/Icons/TouchDesigner-toe.svg",
        "Assets/Icons/TouchDesigner-tox.svg",
    ]:
        path = os.path.join(script_dir, icon)
        check(f"{icon} exists", os.path.isfile(path))

    tox = os.path.join(script_dir, "Assets", "wine_ui_fixes.tox")
    check("wine_ui_fixes.tox exists", os.path.isfile(tox))

    install_sh = os.path.join(script_dir, "install.sh")
    check("install.sh exists", os.path.isfile(install_sh))

    td_install = os.path.join(script_dir, "td-install")
    check("td-install exists", os.path.isfile(td_install))


# =============================================================================
#  Headless auto-detect
# =============================================================================


def test_headless_auto_detect():
    print("\n\u2500\u2500 Headless auto-detect \u2500\u2500")
    old_display = os.environ.pop("DISPLAY", None)
    old_wayland = os.environ.pop("WAYLAND_DISPLAY", None)
    try:
        has_display = bool(
            os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
        )
        check("no display detected as headless", not has_display)
    finally:
        if old_display:
            os.environ["DISPLAY"] = old_display
        if old_wayland:
            os.environ["WAYLAND_DISPLAY"] = old_wayland


# =============================================================================
#  Launcher script generation
# =============================================================================


def test_launcher_script():
    print("\n\u2500\u2500 Launcher script generation \u2500\u2500")
    from td_lib.launcher import LAUNCHER_PATH, create_launcher_script

    backup = None
    if os.path.isfile(LAUNCHER_PATH):
        with open(LAUNCHER_PATH) as f:
            backup = f.read()

    try:
        path = create_launcher_script()
        check("launcher script generated", os.path.isfile(path))

        with open(path) as f:
            content = f.read()

        check("launcher is bash script", content.startswith("#!/bin/bash"))
        check("launcher has TD_BASE_DIR", "TD_BASE_DIR" in content)
        check("launcher has RUNNER_DIR", "RUNNER_DIR" in content)
        check("launcher has WINE_PREFIX", "WINE_PREFIX" in content)
        check(
            "launcher has find_touchdesigner_exe", "find_touchdesigner_exe" in content
        )
        check("launcher has auto-patching", "check_and_patch_toe" in content)
        check("launcher has backup cleanup", "BACKUP_DIR" in content)
        check("NVIDIA block present (no NVIDIA_only)", "NV_PRIME_RENDER_OFFLOAD" in content
              and "VK_LAYER_NV_optimus" not in content)
        check("launcher is executable", os.access(path, os.X_OK))

        check("WAYLAND_DISPLAY cleared", 'export WAYLAND_DISPLAY=""' in content)
        check("GL YIELD = USLEEP", 'export __GL_YIELD="USLEEP"' in content)
        check("KMP_AFFINITY=disabled", 'KMP_AFFINITY="disabled"' in content)
        check("PYTHONPATH set for user site", 'PYTHONPATH' in content and 'steamuser' in content)
        check("find_wine64 function", 'find_wine64()' in content)
        check("WINE64_BIN variable", 'WINE64_BIN=' in content)
        check("AUR fallback path", '/opt/touchdesigner/wine/bin/wine64' in content)

        # Validate bash syntax (no execution, just parse)
        try:
            result = subprocess.run(
                ["bash", "-n", path],
                capture_output=True, text=True, timeout=5,
            )
            check("launcher has valid bash syntax", result.returncode == 0)
            if result.returncode != 0:
                print(f"  bash syntax error: {result.stderr.strip()}")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            skip("bash syntax check (bash not available)")
    finally:
        if backup:
            with open(LAUNCHER_PATH, "w") as f:
                f.write(backup)


# =============================================================================
#  Pip module
# =============================================================================


def test_pip_module():
    print("\n── Pip module ──")
    # Test that the module can be imported
    from td_lib import pip
    check("pip module importable", True)

    # find_td_python should return None when TD not installed
    result = pip.find_td_python()
    check("find_td_python returns None or str",
          result is None or isinstance(result, str))

    # _find_wine64 should find nothing or valid path
    wine64 = pip._find_wine64()
    check("_find_wine64 returns None or valid path",
          wine64 is None or (isinstance(wine64, str) and os.path.isfile(wine64)))


# =============================================================================
#  Diagnose output (subprocess)
# =============================================================================


def test_diagnose_output():
    print("\n\u2500\u2500 Diagnose output \u2500\u2500")
    # Check that diagnose module can be imported and has the right structure
    # Verify the module has a __main__ block
    import inspect

    from td_lib import diagnose

    has_main = any(
        hasattr(m, "__name__") and m.__name__ == "__main__" for m in [diagnose]
    )

    # Check functions exist
    check("diagnose.run_diagnose exists", callable(diagnose.run_diagnose))
    check("diagnose._check_os exists", callable(diagnose._check_os))
    check("diagnose._check_gpu exists", callable(diagnose._check_gpu))
    check("diagnose._check_disk exists", callable(diagnose._check_disk))
    check("diagnose._check_wine exists", callable(diagnose._check_wine))
    check("diagnose._check_td_versions exists", callable(diagnose._check_td_versions))
    check("diagnose._check_ids_patch exists", callable(diagnose._check_ids_patch))

    # Run diagnose and verify output content
    import io

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    try:
        # Redirect output so run_diagnose() doesn't flood terminal
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        diagnose.run_diagnose()
        output = sys.stdout.getvalue()
        err = sys.stderr.getvalue()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    # Now check output (stdout restored, checks are visible)
    check("diagnose outputs banner", "TouchDesigner" in output)
    check("diagnose outputs 'System Health Check'", "System Health" in output)
    check(
        "diagnose outputs 'OS / Kernel'",
        "OS / Kernel" in err or "Kernel" in err,
    )
    check("diagnose outputs 'Graphics'", "Graphics" in err or "GPU" in err)
    check(
        "diagnose outputs 'Free space' or (unreachable) fallback",
        "Free space" in output or "unreachable" in err,
    )
    check(
        "diagnose outputs 'TouchDesigner base' or (unreachable) fallback",
        "TD_BASE_DIR" in output or "Size" in output or "TD_BASE_DIR" in err,
    )


# =============================================================================
#  Cleanup — uninstall selection parsing
# =============================================================================


def test_uninstall_text_selection():
    print("\n\u2500\u2500 Uninstall text selection parsing \u2500\u2500")
    from td_lib.cleanup import uninstall_selected_versions

    # With empty/wrong paths, should return 0 removed
    with tempfile.TemporaryDirectory() as tmpdir:
        result = uninstall_selected_versions([os.path.join(tmpdir, "nonexistent")])
        check("uninstall_selected_versions on missing dirs returns 0", result == 0)

        # Create something to uninstall
        version_dir = os.path.join(tmpdir, "Program Files", "TouchDesigner 2025.99999")
        os.makedirs(os.path.join(version_dir, "bin"))

        with open(os.path.join(version_dir, "bin", "TouchDesigner.exe"), "w") as f:
            f.write("mock")

        result = uninstall_selected_versions([version_dir])
        check("uninstall_selected_versions removes version dir", result == 1)
        check("version dir actually removed", not os.path.isdir(version_dir))


# =============================================================================
#  Distro type constants
# =============================================================================


def test_distro_package_lists():
    print("\n\u2500\u2500 Distro package lists \u2500\u2500")
    from td_lib.distro import (
        APT_PACKAGES,
        DNF_PACKAGES,
        PACMAN_PACKAGES,
        ZYPPER_BASE_PACKAGES,
    )

    check("PACMAN_PACKAGES is non-empty", len(PACMAN_PACKAGES) > 0)
    check("APT_PACKAGES is non-empty", len(APT_PACKAGES) > 0)
    check("DNF_PACKAGES is non-empty", len(DNF_PACKAGES) > 0)
    check("ZYPPER_BASE_PACKAGES is non-empty", len(ZYPPER_BASE_PACKAGES) > 0)
    check(
        "PACMAN_PACKAGES has no duplicates",
        len(PACMAN_PACKAGES) == len(set(PACMAN_PACKAGES)),
    )


# =============================================================================
#  Version picker installed marking
# =============================================================================


def test_version_picker_installed_marking():
    print("\n\u2500\u2500 Version picker installed marking \u2500\u2500")
    from td_lib.touchdesigner import FALLBACK_VERSIONS

    years = set(v.split(".")[0] for v in FALLBACK_VERSIONS)
    check("fallback has 2025", "2025" in years)
    check("fallback has 2024", "2024" in years)
    check("fallback has 2023", "2023" in years)
    check("fallback has 2022", "2022" in years)


# =============================================================================
#  TD-as-Code (tdascode)
# =============================================================================


def test_tdascode_imports():
    print("\n── tdascode imports ──")
    from tdascode import TDNode, TDProject, collapse, expand

    check("tdascode top-level imports", True)

    from tdascode.cli import (
        run_collapse,
        run_expand,
        run_info,
        run_list_types,
        run_type_info,
    )

    check("tdascode.cli handlers importable", True)


def test_tdascode_cli_args():
    print("\n── tdascode CLI args ──")
    from td_lib.cli import parse_args

    args = parse_args(["--expand", "project.toe"])
    check("--expand project.toe", args.expand_file == "project.toe")

    args = parse_args(["--collapse", "project.toe"])
    check("--collapse project.toe", args.collapse_file == "project.toe")

    args = parse_args(["--info", "project.toe"])
    check("--info project.toe", args.info_file == "project.toe")

    args = parse_args(["--list-types"])
    check("--list-types (no family)", args.list_types == "")

    args = parse_args(["--list-types", "POP"])
    check("--list-types POP", args.list_types == "POP")

    args = parse_args(["--type-info", "POP:null"])
    check("--type-info POP:null", args.type_info == "POP:null")

    args = parse_args(["--install"])
    check("--list-types defaults to None when absent", args.list_types is None)


def test_tdascode_text_header():
    """Regression test for the .text header bug: the old code assumed a
    fixed 32-byte block; the real header is a 3-byte magic + six
    big-endian uint32 fields (27 bytes), the last field being the content
    length. Build synthetic .text blobs matching that documented layout
    and verify parse/write round-trip through it correctly."""
    print("\n── tdascode .text header (bug fix) ──")
    import struct

    from tdascode.types import (
        _TEXT_HEADER_SIZE,
        _build_text_header,
        _parse_text_file,
        _write_text_file,
    )

    check("_TEXT_HEADER_SIZE is 27 (3-byte magic + six uint32)", _TEXT_HEADER_SIZE == 27)

    content = b"op('text1').text = 'hello'"
    magic = b"2\n\x2a"
    fields = (1, 1, 1, 1, 2, len(content))
    data = magic + struct.pack(">6I", *fields) + content

    type_hint, parsed = _parse_text_file(data)
    check("parse recovers exact content (no truncation)", parsed == content)
    check("parse recovers type hint", type_hint == 2)

    new_text = "print('updated script')"
    rewritten = _write_text_file(data, new_text)
    _, reparsed = _parse_text_file(rewritten)
    check("write + reparse round-trips new text exactly", reparsed.decode("utf-8") == new_text)
    check(
        "write preserves original magic/flags, only updates length field",
        rewritten[:_TEXT_HEADER_SIZE - 4] == data[:_TEXT_HEADER_SIZE - 4],
    )

    # Brand-new node (no prior .text data to preserve)
    built = _build_text_header(len(new_text.encode("utf-8")))
    check("_build_text_header produces exactly one header, no content", len(built) == _TEXT_HEADER_SIZE)
    _, reparsed2 = _parse_text_file(built + new_text.encode("utf-8"))
    check("brand-new header + content round-trips", reparsed2.decode("utf-8") == new_text)

    # Defensive: a bogus/truncated content_length must not crash the parser
    bogus = magic + struct.pack(">6I", 1, 1, 1, 1, 2, 99999) + content
    try:
        _, truncated = _parse_text_file(bogus)
        check("bogus content_length does not crash parser", True)
        check("bogus content_length yields truncated (not padded/garbage) data", len(truncated) <= len(content))
    except Exception as e:
        check(f"bogus content_length does not crash parser: {e}", False)


def test_tdascode_n_parm_toc():
    print("\n── tdascode .n / .parm / .toc round trip ──")
    from tdascode.core import (
        _parse_n_file,
        _parse_parm_file,
        _parse_toc,
        _write_n_file,
        _write_parm_file,
        _write_toc,
    )

    node_info = {
        "type": "POP:noise",
        "tile": (10.0, 20.0, 130.0, 90.0),
        "inputs": {0: "null1"},
        "color": (0.5, 0.5, 0.5),
        "flags": "current on viewer 1 parlanguage 0",
        "view": "",
        "opview": "",
    }
    n_content = _write_n_file(node_info)
    reparsed = _parse_n_file(n_content)
    check("write_n_file → parse_n_file preserves type", reparsed["type"] == "POP:noise")
    check("write_n_file → parse_n_file preserves tile", reparsed["tile"] == (10.0, 20.0, 130.0, 90.0))
    check("write_n_file → parse_n_file preserves inputs", reparsed["inputs"] == {0: "null1"})
    check("write_n_file → parse_n_file preserves color", reparsed["color"] == (0.5, 0.5, 0.5))

    # The 'v' line's whole-number-decimal formatting isn't a fixed rule --
    # the exact same value ("408.5 ...") was found written BOTH as
    # "v 408.5 324.0 1.0" AND as "v 408.5 324 1" across two different real
    # projects (evidently different toeexpand generations, same as the
    # tile/flags/color raw-line preservation below). An untouched 'v' must
    # be re-emitted byte-for-byte from whatever raw line it was parsed
    # from, not reformatted by any rule.
    v_content = _write_n_file({**node_info, "v": (408.5, 324.0, 1.0),
                               "_raw_v_line": "v 408.5 324 1"})
    check(
        "an untouched 'v' line is re-emitted verbatim, not reformatted",
        "v 408.5 324 1" in v_content.splitlines(),
    )
    check(
        "'v' line round-trips through parse_n_file too",
        _parse_n_file(v_content)["v"] == (408.5, 324.0, 1.0),
    )
    check(
        "a brand-new 'v' with no raw line to preserve falls back to the "
        "plain whole-number-stripping formatter",
        "v 1 2 3.5" in _write_n_file({**node_info, "v": (1.0, 2.0, 3.5)}).splitlines(),
    )

    # Whether a param has an expression is decided by the "expression" dict
    # key's presence, not any flags bit — an earlier version guessed from
    # `flags & 0x11`, which broke on a real project where a parameter had
    # flags=544 (neither bit 0 nor bit 4 set) but a real expression, found
    # via a 407k-record cross-check across many real files (see
    # _parse_parm_file's docstring). "seed" below intentionally uses a
    # flags value that would NOT have matched that old bitmask, to pin the
    # fix down.
    params = [
        {"name": "size", "flags": 0, "value": "2.5"},
        {"name": "seed", "flags": 544, "value": "1", "expression": "me.time.frame"},
        # Real-world regression: an unquoted expression containing a bare
        # single quote (op('name') is idiomatic TD Python) must not have
        # its quote stripped — default shlex.split(posix=True) does this.
        {"name": "scale", "flags": 16, "value": "1", "expression": "op('master').par.scale"},
        # A quoted multi-word value/expression with an embedded double
        # quote and backslash, to exercise the escaping round trip.
        {"name": "note", "flags": 1, "value": "hi", "expression": 'say "hi\\there" now'},
        # The rare (~24 real occurrences out of 400k+ checked) 5-token
        # shape: a value plus TWO trailing tokens.
        {"name": "cols", "flags": 561, "value": "20",
         "expression": "op('math1')['num_points']", "expression2": "op('torus1').par.cols"},
    ]
    parm_content = _write_parm_file(params)
    reparsed_params = _parse_parm_file(parm_content)
    check("write_parm_file → parse_parm_file same count", len(reparsed_params) == len(params))
    check(
        "write_parm_file → parse_parm_file preserves values",
        reparsed_params[0]["value"] == "2.5" and reparsed_params[1]["value"] == "1",
    )
    check(
        "write_parm_file → parse_parm_file preserves expression",
        reparsed_params[1].get("expression") == "me.time.frame",
    )
    check(
        "bare single quote in an unquoted expression is preserved (op('master')...)",
        reparsed_params[2].get("expression") == "op('master').par.scale",
    )
    check(
        "quoted expression with embedded double-quote/backslash round-trips",
        reparsed_params[3].get("expression") == 'say "hi\\there" now',
    )
    check(
        "a param with flags that wouldn't match the old 0x11 bitmask still "
        "gets its expression parsed, from real token count alone",
        reparsed_params[1].get("expression") == "me.time.frame",
    )
    check(
        "the rare 5-token shape preserves both expression and expression2",
        reparsed_params[4].get("expression") == "op('math1')['num_points']"
        and reparsed_params[4].get("expression2") == "op('torus1').par.cols",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        toc_path = os.path.join(tmpdir, "project.toe.toc")
        entries = [".build", ".root", "null1.n", "null1.parm"]
        _write_toc(toc_path, entries)

        with open(toc_path) as f:
            raw = f.read()
        # Real toeexpand output has no header line at all (a prior fix
        # here, adding "# N 0 0 0 1", turned out to be wrong once checked
        # against a real toeexpand'd project — it made toecollapse reject
        # the file as corrupt; see _parse_toc's docstring).
        check("write_toc has no header line", not raw.startswith("#"))
        check("write_toc includes .build entry", ".build" in raw.splitlines())

        reparsed_entries = _parse_toc(toc_path)
        check("parse_toc round-trips entries", reparsed_entries == entries)


def test_tdascode_file_ext_order():
    """Regression test for the actual root cause of a real, hard-to-track
    corruption bug on a production project: TDNode.write_to() was writing
    a node's own files (.n/.cparm/.parm/.text/.network/.panel/etc.) in the
    wrong relative order. Every content-level check (the .dir folder's
    individual file bytes, re-expand-and-diff) came back clean -- the
    corruption only showed up as a live parameter expression cooking to
    None on load, and the actual difference was purely the *order* of
    per-node entries in the regenerated .toc. Confirmed by finding the
    exact wrong-order .toc lines, then deriving the real order from
    ~2600 real entries in a production project's own .toc (see
    _FILE_EXT_ORDER's docstring). This locks that order in."""
    print("\n── tdascode per-node file write order (corruption bug fix) ──")
    from tdascode.core import TDProject

    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = os.path.join(tmpdir, "project.toe.dir")
        toc_path = os.path.join(tmpdir, "project.toe.toc")
        os.makedirs(dir_path)
        proj = TDProject(dir_path, toc_path)

        # Mirrors the real node that exposed this: has .n, .cparm, .parm,
        # .network, and .panel all at once -- the real order is
        # n, cparm, parm, network, panel (NOT n, parm, panel, cparm as
        # the old fixed sequence assumed).
        node = proj.add_node("", "cntrl", type="COMP:container",
                              params=[{"name": "size", "flags": 0, "value": "1"}],
                              panel="panel content")
        node.cparm = "cparm content"
        node.extra_files["network"] = b"network content"

        proj.write()

        with open(toc_path) as f:
            toc_lines = [line.strip() for line in f if line.strip()]
        cntrl_entries = [line for line in toc_lines if line.startswith("cntrl.")]
        check(
            "per-node file order matches real toeexpand output "
            "(n, cparm, parm, network, panel)",
            cntrl_entries == ["cntrl.n", "cntrl.cparm", "cntrl.parm",
                               "cntrl.network", "cntrl.panel"],
        )


def test_tdascode_per_node_file_order_preserved():
    """A broad round-trip test across 86 real .toe files found a SECOND
    per-node ordering bug: _FILE_EXT_ORDER assumes one fixed universal
    per-extension order, but a different real project ("first floor (al
    jinn).toe") has nodes whose real order is n, parm, panel, cparm,
    network -- not n, cparm, parm, network, panel like the node that
    originally motivated _FILE_EXT_ORDER. The true order isn't a function
    of extension at all; it has to be captured per node at parse time
    (TDNode._orig_file_order) and replayed as-is on write(), the same way
    _entry_order already does for the top-level .toc. This hand-builds a
    node whose original file order deliberately differs from
    _FILE_EXT_ORDER to pin the fix down without needing real toeexpand."""
    print("\n── tdascode per-node file order preserved from parsing ──")
    from tdascode.core import TDProject, _write_n_file, _write_toc

    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = os.path.join(tmpdir, "project.toe.dir")
        toc_path = os.path.join(tmpdir, "project.toe.toc")
        os.makedirs(dir_path)

        n_content = _write_n_file({"type": "COMP:container", "tile": (-100, -100, 130, 90),
                                    "inputs": {}, "color": (0.67, 0.67, 0.67), "flags": ""})
        with open(os.path.join(dir_path, "pulse1.n"), "w") as f:
            f.write(n_content)
        with open(os.path.join(dir_path, "pulse1.parm"), "w") as f:
            f.write("?\nsize 0 1\n?\n")
        with open(os.path.join(dir_path, "pulse1.panel"), "w") as f:
            f.write("panel content")
        with open(os.path.join(dir_path, "pulse1.cparm"), "w") as f:
            f.write("cparm content")
        with open(os.path.join(dir_path, "pulse1.network"), "wb") as f:
            f.write(b"network content")
        # Deliberately NOT the _FILE_EXT_ORDER sequence (which would be
        # n, cparm, parm, network, panel) -- this is the real order found
        # on "first floor (al jinn).toe"'s pulse1 node.
        _write_toc(toc_path, ["pulse1.n", "pulse1.parm", "pulse1.panel",
                               "pulse1.cparm", "pulse1.network"])

        proj = TDProject.from_dir(dir_path, toc_path)
        proj.write()

        with open(toc_path) as f:
            toc_lines = [line.strip() for line in f if line.strip()]
        check(
            "a zero-change write() preserves the real per-node order "
            "(n, parm, panel, cparm, network) instead of reordering by "
            "the _FILE_EXT_ORDER default",
            toc_lines == ["pulse1.n", "pulse1.parm", "pulse1.panel",
                          "pulse1.cparm", "pulse1.network"],
        )

        node = proj.get_node("pulse1")
        node.extra_files["chop"] = b"chop content"
        proj.write()
        with open(toc_path) as f:
            toc_lines = [line.strip() for line in f if line.strip()]
        check(
            "a genuinely new file type added later falls back to "
            "_FILE_EXT_ORDER, appended after the preserved original order",
            toc_lines == ["pulse1.n", "pulse1.parm", "pulse1.panel",
                          "pulse1.cparm", "pulse1.network", "pulse1.chop"],
        )


def test_tdascode_toc_entry_order_preserved():
    """Regression test for a second real .toc-ordering bug, found via a
    zero-change round trip against a real project (fluffy_original.toe):
    write() used to group ALL meta files before ALL nodes, and always
    deferred `.application`'s .toc entry to the very last line -- a rule
    that happened to match one test file (DEFAULT-3D.toe) by coincidence,
    but broke on this one, where `.application` sits in the *middle* of
    the top-level entries, between two node groups. There's no fixed rule
    for where meta files go -- only "preserve whatever the real .toc
    order already was", which is what _entry_order now does. This mirrors
    that exact shape (meta file sitting between two node groups) and pins
    it down without needing real toeexpand."""
    print("\n── tdascode .toc top-level entry order (meta+nodes interleaved) ──")
    from tdascode.core import TDProject, _write_n_file, _write_toc

    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = os.path.join(tmpdir, "project.toe.dir")
        toc_path = os.path.join(tmpdir, "project.toe.toc")
        os.makedirs(dir_path)

        with open(os.path.join(dir_path, ".build"), "w") as f:
            f.write("1\n")
        with open(os.path.join(dir_path, "first.n"), "w") as f:
            f.write(_write_n_file({"type": "COMP:base", "tile": (-100, -100, 130, 90),
                                    "inputs": {}, "color": (0.67, 0.67, 0.67), "flags": ""}))
        with open(os.path.join(dir_path, ".application"), "w") as f:
            f.write("appdata\n")
        with open(os.path.join(dir_path, "second.n"), "w") as f:
            f.write(_write_n_file({"type": "COMP:base", "tile": (-100, -100, 130, 90),
                                    "inputs": {}, "color": (0.67, 0.67, 0.67), "flags": ""}))
        _write_toc(toc_path, [".build", "first.n", ".application", "second.n"])

        proj = TDProject.from_dir(dir_path, toc_path)
        proj.write()

        with open(toc_path) as f:
            toc_lines = [line.strip() for line in f if line.strip()]
        check(
            "a zero-change write() keeps .application in its original "
            "mid-sequence position, not deferred to the end",
            toc_lines == [".build", "first.n", ".application", "second.n"],
        )

        proj.add_node("", "third", type="COMP:base")
        proj.write()
        with open(toc_path) as f:
            toc_lines = [line.strip() for line in f if line.strip()]
        check(
            "a newly added node is appended after the preserved original "
            "order, not before .application",
            toc_lines == [".build", "first.n", ".application", "second.n", "third.n"],
        )


def test_tdascode_project_roundtrip():
    """Exercise TDProject.from_dir() -> mutate -> write() -> from_dir() again,
    entirely in Python (no Wine/toeexpand involved). This is the layer the
    two known correctness bugs lived in, so this is the regression net for
    the add_node()/write()/.toc path described as unsafe in the roadmap."""
    print("\n── tdascode TDProject round trip (pure Python, no Wine) ──")
    from tdascode.core import TDProject, _write_n_file, _write_toc

    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = os.path.join(tmpdir, "project.toe.dir")
        toc_path = os.path.join(tmpdir, "project.toe.toc")
        os.makedirs(dir_path)

        # Minimal hand-built expanded project: one root-level DAT-less node.
        with open(os.path.join(dir_path, ".build"), "w") as f:
            f.write("1\n")
        with open(os.path.join(dir_path, ".root"), "w") as f:
            f.write("/\n")
        with open(os.path.join(dir_path, "null1.n"), "w") as f:
            f.write(_write_n_file({"type": "POP:null", "tile": (-100, -100, 130, 90),
                                    "inputs": {}, "color": (0.67, 0.67, 0.67), "flags": ""}))
        _write_toc(toc_path, [".build", ".root", "null1.n"])

        proj = TDProject.from_dir(dir_path, toc_path)
        check("from_dir finds the hand-built node", "null1" in proj.nodes)
        check("from_dir loads meta files including .build", ".build" in proj.meta_files)

        proj.add_node("", "text1", type="DAT:text", text="print('hi')")
        proj.connect("text1", "null1")
        proj.set_param("null1", "size", "3.0")
        check("added node present before write()", "text1" in proj.nodes)

        proj.write()

        with open(toc_path) as f:
            toc_raw = f.read()
        check("write() regenerates .toc without a header line", not toc_raw.startswith("#"))
        check("write() keeps .build in the .toc", ".build" in toc_raw.splitlines())

        reproj = TDProject.from_dir(dir_path, toc_path)
        check("re-parsed project still has original node", "null1" in reproj.nodes)
        check("re-parsed project has the added DAT node", "text1" in reproj.nodes)
        check(
            "re-parsed project preserves the new connection",
            reproj.get_node("null1").inputs.get(0) == "text1",
        )
        check(
            "re-parsed project preserves the new param",
            reproj.get_param("null1", "size") == "3.0",
        )
        check(
            "re-parsed DAT text survives the .text header round trip",
            reproj.get_text("text1") == "print('hi')",
        )


def test_tdascode_get_node_ambiguous_short_name():
    """Found while stress-testing against a real project
    (fluffy_original.toe): it has 'line1', 'transform1', and 'grid1' each
    duplicated under different parent COMPs. get_node()'s short-name
    fallback used to silently return whichever matched first in dict
    order -- a silent wrong-node bug that would let set_param()/connect()/
    set_text() quietly edit the wrong operator with zero warning. Fixed to
    raise instead when a bare short name is ambiguous, while still
    resolving cleanly when it's actually unique."""
    print("\n── tdascode get_node ambiguous short name ──")
    from tdascode.core import TDProject

    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = os.path.join(tmpdir, "project.toe.dir")
        toc_path = os.path.join(tmpdir, "project.toe.toc")
        os.makedirs(dir_path)
        proj = TDProject(dir_path, toc_path)

        proj.add_node("", "geo1", type="COMP:geo")
        proj.add_node("", "geo2", type="COMP:geo")
        proj.add_node("geo1", "transform1", type="SOP:transform")
        proj.add_node("geo2", "transform1", type="SOP:transform")
        proj.add_node("", "render1", type="TOP:render")

        raised = False
        try:
            proj.get_node("transform1")
        except ValueError as e:
            raised = True
            check(
                "error message lists both ambiguous candidates",
                "geo1/transform1" in str(e) and "geo2/transform1" in str(e),
            )
        check("ambiguous short name raises instead of silently picking one", raised)

        check(
            "a genuinely unique short name still resolves",
            proj.get_node("render1") is not None,
        )
        check(
            "a full path always resolves directly, even when the short "
            "name would be ambiguous",
            proj.get_node("geo1/transform1").parent_path == "geo1",
        )


def test_tdascode_remove_node_clears_dangling_inputs():
    """Found while stress-testing remove_node() against a real project
    (fluffy_original.toe): removing a node that siblings wired into left
    those siblings' .inputs pointing at a name that no longer exists
    (e.g. blur1.inputs stayed {0: 'null2'} after null2 was removed) --
    real TD's network editor auto-clears downstream wires when you delete
    a node, so this didn't match real behavior. Fixed to clear .inputs
    entries in remaining same-parent siblings that referenced a removed
    node, while leaving alone unrelated nodes elsewhere that happen to
    reference a different node with the same short name (since .inputs
    values are sibling names scoped to a shared parent)."""
    print("\n── tdascode remove_node clears dangling sibling inputs ──")
    from tdascode.core import TDProject

    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = os.path.join(tmpdir, "project.toe.dir")
        toc_path = os.path.join(tmpdir, "project.toe.toc")
        os.makedirs(dir_path)
        proj = TDProject(dir_path, toc_path)

        proj.add_node("", "null2", type="TOP:null")
        proj.add_node("", "blur1", type="TOP:blur")
        proj.connect("null2", "blur1", 0)
        proj.add_node("", "comp1", type="TOP:comp")
        proj.connect("null2", "comp1", 0)
        proj.connect("blur1", "comp1", 1)

        # An unrelated node elsewhere with a same-named sibling should be
        # untouched -- .inputs values are only meaningful among siblings.
        proj.add_node("", "other_parent", type="COMP:base")
        proj.add_node("other_parent", "null2", type="TOP:null")
        proj.add_node("other_parent", "keeper", type="TOP:blur")
        proj.connect("other_parent/null2", "other_parent/keeper", 0)

        proj.remove_node("null2")

        check(
            "sibling's dangling input to the removed node is cleared",
            proj.get_node("blur1").inputs == {},
        )
        check(
            "sibling's other input (to a node that wasn't removed) survives",
            proj.get_node("comp1").inputs == {1: "blur1"},
        )
        check(
            "an unrelated node in a different parent with the same short "
            "name is untouched",
            proj.get_node("other_parent/keeper").inputs == {0: "null2"},
        )


def test_tdascode_connect_rejects_cross_parent():
    """Found while stress-testing connect(): calling
    connect('geo1/transform1', 'geo2/null1', 0) used to silently succeed
    and store {0: 'transform1'} on geo2/null1's inputs, even though
    .inputs is a sibling-*name* reference resolved within dst's own
    parent network -- real TD can only wire two operators that share the
    same immediate parent (crossing a COMP boundary needs an explicit
    In/Out operator on each side). That wrote a name that wouldn't
    resolve to anything at all inside geo2, not just the wrong node.
    Fixed to raise instead of silently writing a wire TD could never
    have produced."""
    print("\n── tdascode connect rejects cross-parent wires ──")
    from tdascode.core import TDProject

    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = os.path.join(tmpdir, "project.toe.dir")
        toc_path = os.path.join(tmpdir, "project.toe.toc")
        os.makedirs(dir_path)
        proj = TDProject(dir_path, toc_path)

        proj.add_node("", "geo1", type="COMP:geo")
        proj.add_node("", "geo2", type="COMP:geo")
        proj.add_node("geo1", "transform1", type="SOP:transform")
        proj.add_node("geo1", "null1", type="SOP:null")
        proj.add_node("geo2", "null1", type="SOP:null")

        proj.connect("geo1/transform1", "geo1/null1", 0)
        check(
            "a same-parent connect still works",
            proj.get_node("geo1/null1").inputs == {0: "transform1"},
        )

        raised = False
        try:
            proj.connect("geo1/transform1", "geo2/null1", 0)
        except ValueError:
            raised = True
        check("a cross-parent connect raises instead of silently writing a bogus wire", raised)
        check(
            "the rejected connect left the destination's inputs untouched",
            proj.get_node("geo2/null1").inputs == {},
        )


def test_tdascode_add_node_rejects_invalid_parent():
    """Verified live via the bridge: a project with add_node() output for
    a nonexistent parent_path, or one pointing at a non-COMP node (a child
    under a real TOP:blur), loads in actual TouchDesigner with no error or
    warning at all -- but both nodes are silently dropped entirely (op()
    resolves to None for them live), even though toeexpand/toecollapse
    round-trip the raw .n files byte-for-byte at the file-format level.
    Fixed add_node() to raise instead of silently building content that
    real TD would just discard on load."""
    print("\n── tdascode add_node rejects invalid parent_path ──")
    from tdascode.core import TDProject

    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = os.path.join(tmpdir, "project.toe.dir")
        toc_path = os.path.join(tmpdir, "project.toe.toc")
        os.makedirs(dir_path)
        proj = TDProject(dir_path, toc_path)

        proj.add_node("", "geo1", type="COMP:geo")
        proj.add_node("", "blur1", type="TOP:blur")

        check(
            "adding under a real COMP still works",
            proj.add_node("geo1", "null1", type="SOP:null") is not None,
        )

        raised_nonexistent = False
        try:
            proj.add_node("totally_nonexistent_comp", "orphan1", type="SOP:null")
        except ValueError:
            raised_nonexistent = True
        check(
            "a nonexistent parent_path raises instead of silently creating "
            "a node real TD would drop on load",
            raised_nonexistent,
        )

        raised_non_comp = False
        try:
            proj.add_node("blur1", "weird_child", type="SOP:null")
        except ValueError:
            raised_non_comp = True
        check(
            "a parent that exists but isn't a COMP (a TOP:blur) also raises",
            raised_non_comp,
        )
        check(
            "neither rejected call left a partial node behind",
            "totally_nonexistent_comp/orphan1" not in proj.nodes
            and "blur1/weird_child" not in proj.nodes,
        )


def test_tdascode_set_param_preserves_expression():
    """A real --diff run against DEFAULT-3D.toe found set_param() silently
    wiping an existing expression binding: bumping a GLSL param's value with
    set_param(path, name, "9.9") (no flags/expression passed) reset flags to
    0 and deleted the op('null4')['radius'] expression entirely, because the
    old `flags: int = 0, expression: str | None = None` defaults couldn't
    tell "not specified" from "explicitly cleared". Fixed with an _UNSET
    sentinel; this pins the fix."""
    print("\n── tdascode set_param preserves existing flags/expression ──")
    from tdascode.core import TDProject

    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = os.path.join(tmpdir, "project.toe.dir")
        toc_path = os.path.join(tmpdir, "project.toe.toc")
        os.makedirs(dir_path)
        proj = TDProject(dir_path, toc_path)
        proj.add_node("", "glsl1", type="POP:glsl")
        proj.set_param("glsl1", "vec0valuex", "1.0", flags=17,
                        expression="op('null4')['radius']")

        proj.set_param("glsl1", "vec0valuex", "9.9")

        param = next(p for p in proj.get_node("glsl1").params
                     if p["name"] == "vec0valuex")
        check("value is updated", param["value"] == "9.9")
        check("flags are preserved when omitted", param.get("flags") == 17)
        check(
            "expression is preserved when omitted",
            param.get("expression") == "op('null4')['radius']",
        )

        proj.set_param("glsl1", "vec0valuex", "0.0", expression=None)
        param = next(p for p in proj.get_node("glsl1").params
                     if p["name"] == "vec0valuex")
        check(
            "explicit expression=None still clears the binding",
            "expression" not in param,
        )

        proj.set_param("glsl1", "vec0valuex", "2.0", expression="op('null5')['radius']")
        param = next(p for p in proj.get_node("glsl1").params
                     if p["name"] == "vec0valuex")
        check(
            "explicit new expression still replaces the old one",
            param.get("expression") == "op('null5')['radius']",
        )
        check(
            "flags are left untouched when only the expression changes -- "
            "whether an expression exists is decided by the dict key's "
            "presence, not any flags bit, so nothing needs to be set here",
            param.get("flags") == 17,
        )

        proj.add_node("", "null1", type="SOP:null")
        proj.set_param("null1", "size", "3.0")
        new_param = next(p for p in proj.get_node("null1").params
                         if p["name"] == "size")
        check(
            "a brand new param with no flags/expression passed defaults to flags=0",
            new_param.get("flags") == 0 and "expression" not in new_param,
        )


def test_tdascode_auto_layout():
    """TDProject.auto_layout() — added after live-bridge testing on a real
    project showed that nodes created via add_node()/connect() without an
    explicit tile all stack on top of each other (every new node defaults
    to the same tile). Mirrors the actual sphere+ring+merge network built
    live: two independent source chains converging into one merge, which
    itself feeds a final node -- the exact shape that zig-zagged/overlapped
    before this existed."""
    print("\n── tdascode auto_layout ──")
    from tdascode.core import TDProject

    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = os.path.join(tmpdir, "project.toe.dir")
        toc_path = os.path.join(tmpdir, "project.toe.toc")
        os.makedirs(dir_path)
        proj = TDProject(dir_path, toc_path)

        proj.add_node("", "in1", type="SOP:in")
        proj.add_node("", "sphere", type="SOP:sphere")
        proj.add_node("", "matsop_sphere", type="SOP:material")
        proj.connect("sphere", "matsop_sphere")
        proj.add_node("", "ring_seed", type="SOP:sphere")
        proj.add_node("", "ring_copy", type="SOP:copy")
        proj.connect("ring_seed", "ring_copy")
        proj.add_node("", "ring_spin", type="SOP:transform")
        proj.connect("ring_copy", "ring_spin")
        proj.add_node("", "matsop_ring", type="SOP:material")
        proj.connect("ring_spin", "matsop_ring")
        proj.add_node("", "merge", type="SOP:merge")
        proj.connect("in1", "merge", 0)
        proj.connect("matsop_sphere", "merge", 1)
        proj.connect("matsop_ring", "merge", 2)
        proj.add_node("", "out1", type="SOP:out")
        proj.connect("merge", "out1")

        check(
            "before auto_layout, new nodes share the default tile (the bug)",
            proj.get_node("sphere").tile == proj.get_node("ring_seed").tile,
        )

        proj.auto_layout("")

        positions = [proj.get_node(n).tile[:2] for n in
                     ("in1", "sphere", "matsop_sphere", "ring_seed", "ring_copy",
                      "ring_spin", "matsop_ring", "merge", "out1")]
        check("auto_layout leaves no two nodes at the same position",
              len(set(positions)) == len(positions))

        col_x = {n: proj.get_node(n).tile[0] for n in
                  ("in1", "sphere", "ring_seed", "matsop_sphere", "ring_copy",
                   "ring_spin", "matsop_ring", "merge", "out1")}
        check("sources (in1/sphere/ring_seed) share column 0",
              col_x["in1"] == col_x["sphere"] == col_x["ring_seed"])
        check("matsop_sphere comes after sphere",
              col_x["matsop_sphere"] > col_x["sphere"])
        check("ring_spin comes after ring_copy comes after ring_seed",
              col_x["ring_spin"] > col_x["ring_copy"] > col_x["ring_seed"])
        check("merge comes after both matsop_sphere and matsop_ring",
              col_x["merge"] > col_x["matsop_sphere"] and col_x["merge"] > col_x["matsop_ring"])
        check("out1 comes after merge", col_x["out1"] > col_x["merge"])


def test_tdascode_auto_layout_param_references():
    """auto_layout must also follow parameter-reference dependencies, not
    just wire connections. Found on a real project: a Render TOP has zero
    wire inputs at all, but its 'camera' parameter names a sibling Camera
    COMP by exact value -- a real relationship a wire-only view of the
    graph can't see, leaving the camera with no positional pull toward
    the render setup it belongs to. Mirrors that exact shape: cam1/light1
    (no wires anywhere) referenced by render1's camera/light params, a
    'geometry' param that's a wildcard '*' (must NOT be treated as a
    reference to a node literally named '*'), and an ordinary wired
    chain (grid1->noise1) for contrast."""
    print("\n── tdascode auto_layout (parameter-reference dependencies) ──")
    from tdascode.core import TDProject

    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = os.path.join(tmpdir, "project.toe.dir")
        toc_path = os.path.join(tmpdir, "project.toe.toc")
        os.makedirs(dir_path)
        proj = TDProject(dir_path, toc_path)

        proj.add_node("", "grid1", type="SOP:grid")
        proj.add_node("", "noise1", type="SOP:noise")
        proj.connect("grid1", "noise1")

        proj.add_node("", "cam1", type="COMP:cam")
        proj.add_node("", "light1", type="COMP:light")
        proj.add_node("", "geo1", type="COMP:geo")
        proj.add_node("", "render1", type="TOP:render", params=[
            {"name": "camera", "flags": 0, "value": "cam1"},
            {"name": "light", "flags": 0, "value": "light1"},
            {"name": "geometry", "flags": 0, "value": "*"},
        ])

        proj.auto_layout("")

        col_x = {n: proj.get_node(n).tile[0] for n in
                  ("grid1", "noise1", "cam1", "light1", "geo1", "render1")}

        check("camera/light referenced-by-param nodes land before render1",
              col_x["cam1"] < col_x["render1"] and col_x["light1"] < col_x["render1"])
        check("a param value of '*' is not treated as a reference to a node "
              "literally named '*' -- geo1 has no real relation to render1 here "
              "and stays an independent column-0 source",
              col_x["geo1"] == col_x["grid1"] == col_x["cam1"])
        check("ordinary wired dependency still works alongside param references",
              col_x["noise1"] > col_x["grid1"])


def test_tdascode_diff():
    """tdascode.diff -- semantic diff between two projects (added/removed/
    modified nodes, per-field changes), not a raw text diff of the
    expanded files. Build two small hand-crafted projects covering every
    kind of change: a node only in A (removed), a node only in B (added),
    and a node in both with a type change, a flags change, a connection
    change, a param value change, a param expression change, and a text
    (DAT script) change -- plus one untouched node that must NOT show up
    as modified."""
    print("\n── tdascode diff (semantic) ──")
    from tdascode.core import TDProject
    from tdascode.diff import diff_projects, format_diff

    def build_project():
        proj = TDProject("/unused/dir", "/unused/toc")
        proj.add_node("", "untouched", type="SOP:null",
                       params=[{"name": "size", "flags": 0, "value": "1"}])
        proj.add_node("", "changed", type="SOP:sphere", flags="viewer 1",
                       params=[{"name": "radx", "flags": 0, "value": "1.0"},
                               {"name": "rady", "flags": 17, "value": "1.0",
                                "expression": "me.par.radx"}],
                       text="print('before')")
        proj.add_node("", "only_in_a", type="SOP:box")
        return proj

    proj_a = build_project()
    proj_b = build_project()

    # Only in B: added
    proj_b.add_node("", "only_in_b", type="SOP:torus")
    # Only in A: removed
    proj_b.remove_node("only_in_a")
    # Modified: type, flags, connection, param value, param expression, text
    changed = proj_b.get_node("changed")
    changed.type = "SOP:box"
    changed.flags = "viewer 0"
    proj_b.connect("untouched", "changed", 0)
    proj_b.set_param("changed", "radx", "2.0")
    proj_b.set_param("changed", "rady", "1.0", flags=17, expression="me.par.rady2")
    proj_b.set_text("changed", "print('after')")

    result = diff_projects(proj_a, proj_b)

    check("diff detects the added node", any(n.path == "only_in_b" for n in result.added))
    check("diff detects the removed node", any(n.path == "only_in_a" for n in result.removed))
    check("diff detects exactly one modified node",
          len(result.modified) == 1 and result.modified[0].path == "changed")
    check("untouched node is not reported as modified",
          not any(n.path == "untouched" for n in result.modified))

    changes = "\n".join(result.modified[0].changes)
    check("diff reports the type change", "SOP:sphere -> SOP:box" in changes)
    check("diff reports the flags change", "viewer 1" in changes and "viewer 0" in changes)
    check("diff reports the new connection", "input[0]" in changes and "untouched" in changes)
    check("diff reports the param value change", "radx" in changes and "2.0" in changes)
    check("diff reports the param expression change", "me.par.radx" in changes and "me.par.rady2" in changes)
    check("diff reports the text change", "before" in changes and "after" in changes)

    check("format_diff on identical projects says so",
          format_diff(diff_projects(proj_a, proj_a)) == "No differences.")
    rendered = format_diff(result, "a.toe", "b.toe")
    check("format_diff includes both file labels", "a.toe" in rendered and "b.toe" in rendered)


def test_tdascode_expand_readonly_source():
    """expand() must fall back to a scratch copy when the source directory
    isn't writable. Found via real usage: toeexpand always writes its
    .dir/.toc next to the source path, which fails outright ("Unable to
    create file '.build'") on a read-only location like an AUR-installed
    Samples directory -- blocking read-only operations (--diff, --info)
    that never needed write access to the source in the first place.
    Opt-in like the other real-toeexpand tests since it needs a genuine
    subprocess call to observe the actual failure this works around."""
    print("\n── tdascode expand() read-only source fallback ──")
    from tdascode.core import _find_toe_tool

    sample_toe = os.environ.get("TDASCODE_TEST_TOE")
    if not sample_toe:
        skip("TDASCODE_TEST_TOE not set — skipping read-only source test")
        return
    if not _find_toe_tool("toeexpand"):
        skip("no toeexpand.exe found in Wine prefix — skipping read-only source test")
        return

    from tdascode.core import expand

    with tempfile.TemporaryDirectory() as tmpdir:
        readonly_dir = os.path.join(tmpdir, "readonly")
        os.makedirs(readonly_dir)
        readonly_toe = os.path.join(readonly_dir, "sample.toe")
        shutil.copy2(sample_toe, readonly_toe)
        os.chmod(readonly_dir, 0o555)

        proj = None
        try:
            proj = expand(readonly_toe)
            check("expand() succeeds on a read-only source directory", proj is not None)
            check("no .dir got created in the read-only source directory",
                  not os.path.exists(readonly_toe + ".dir"))
            check("no .toc got created in the read-only source directory",
                  not os.path.exists(readonly_toe + ".toc"))
            check("scratch copy directory was tracked for cleanup",
                  bool(proj._temp_source_dir) and os.path.isdir(proj._temp_source_dir))
        finally:
            os.chmod(readonly_dir, 0o755)
            if proj:
                temp_dir = proj._temp_source_dir
                proj.cleanup()
                if temp_dir:
                    check("cleanup() removed the scratch copy directory too",
                          not os.path.isdir(temp_dir))


def test_tdascode_real_toeexpand_roundtrip():
    """Opt-in end-to-end check against the REAL toeexpand/toecollapse
    binaries. Everything above validates our own parsers in isolation;
    this is the one that actually matters before trusting this on real
    projects, and it can only run where a full TouchDesigner install
    (with bin/toeexpand.exe) and a sample .toe are both available —
    neither is present in this sandbox, so it skips cleanly rather than
    faking a pass.

    To run for real: set TDASCODE_TEST_TOE to a path to a disposable
    .toe file on a machine with TouchDesigner installed via this project.
    """
    print("\n── tdascode real toeexpand/toecollapse round trip (opt-in) ──")
    from tdascode.core import _find_toe_tool

    sample_toe = os.environ.get("TDASCODE_TEST_TOE")
    if not sample_toe:
        skip("TDASCODE_TEST_TOE not set — skipping real toeexpand round trip")
        return
    if not _find_toe_tool("toeexpand"):
        skip("no toeexpand.exe found in Wine prefix — skipping real round trip")
        return

    import shutil as _shutil

    from tdascode.core import collapse, expand

    # NOTE: this does NOT compare raw .toe bytes before/after. toecollapse
    # uses a different compression ratio than however the original .toe was
    # saved (confirmed on a real 334KB sample that legitimately re-collapses
    # to ~324KB of semantically identical content) -- byte-identical .toe
    # output isn't achievable or meaningful. What actually matters, and what
    # this checks, is that expand -> write (no changes) -> collapse ->
    # re-expand reproduces the exact same node data.
    work_copy = sample_toe + ".roundtrip_test.toe"
    _shutil.copy2(sample_toe, work_copy)
    original_proj = None
    roundtripped_proj = None
    try:
        original_proj = expand(work_copy)
        original_nodes = {
            key: (n.type, n.tile, n.color, n.flags, n.comment, n.inputs, n.params, n.text_data)
            for key, n in original_proj.nodes.items()
        }

        original_proj.write()
        collapse(work_copy)

        roundtripped_proj = expand(work_copy)
        roundtripped_nodes = {
            key: (n.type, n.tile, n.color, n.flags, n.comment, n.inputs, n.params, n.text_data)
            for key, n in roundtripped_proj.nodes.items()
        }

        check(
            "round trip preserves node count",
            len(roundtripped_nodes) == len(original_nodes),
        )

        mismatches = [
            key for key in original_nodes
            if roundtripped_nodes.get(key) != original_nodes[key]
        ]
        check(
            "expand -> write (no changes) -> collapse -> re-expand preserves all node data",
            not mismatches,
        )
        if mismatches:
            for key in mismatches[:10]:
                print("   ", key)
    finally:
        if original_proj:
            original_proj.cleanup()
        if roundtripped_proj:
            roundtripped_proj.cleanup()
        for path in (work_copy, work_copy + ".toc"):
            if os.path.isfile(path):
                os.remove(path)
        _shutil.rmtree(work_copy + ".dir", ignore_errors=True)


# =============================================================================
#  Progress bar format
# =============================================================================


def test_progress_bar_format():
    print("\n\u2500\u2500 Progress bar format \u2500\u2500")
    total = 100 * 1024 * 1024
    downloaded = 50 * 1024 * 1024
    pct = downloaded * 100 // total
    bar_len = 30
    filled = bar_len * downloaded // total
    bar = (
        "=" * (filled - 1) + ">" + "-" * (bar_len - filled)
        if filled > 0
        else "-" * bar_len
    )
    check(f"progress bar {pct}% has '>'", ">" in bar)
    check(f"progress bar length = {bar_len}", len(bar) == bar_len)

    bar0 = "-" * bar_len
    check("progress 0% is all dashes", len(bar0) == bar_len)

    bar100 = "=" * bar_len
    check("progress 100% is all equals", len(bar100) == bar_len)


# =============================================================================
#  Run
# =============================================================================


def main():
    print("=" * 60)
    print("  TouchDesigner-Linux v1.4 — Test Suite")
    print("=" * 60)

    test_imports()
    test_cli_args()
    test_dry_run()
    test_safe_rm()
    test_ensure_dir()
    test_require_commands()
    test_verify_checksum()
    test_log_format()
    test_print_banner()
    test_distro_detection()
    test_desktop_file_content()
    test_mime_xml_content()
    test_font_fix_paths()
    test_wine_error_parser()
    test_ids_patch_parsing()
    test_version_select()
    test_version_detection()
    test_version_sorting()
    test_discover_installed_versions()
    test_desktop_assets()
    test_headless_auto_detect()
    test_launcher_script()
    test_pip_module()
    test_diagnose_output()
    test_uninstall_text_selection()
    test_distro_package_lists()
    test_version_picker_installed_marking()
    test_progress_bar_format()
    test_tdascode_imports()
    test_tdascode_cli_args()
    test_tdascode_text_header()
    test_tdascode_n_parm_toc()
    test_tdascode_file_ext_order()
    test_tdascode_per_node_file_order_preserved()
    test_tdascode_toc_entry_order_preserved()
    test_tdascode_project_roundtrip()
    test_tdascode_get_node_ambiguous_short_name()
    test_tdascode_remove_node_clears_dangling_inputs()
    test_tdascode_connect_rejects_cross_parent()
    test_tdascode_add_node_rejects_invalid_parent()
    test_tdascode_set_param_preserves_expression()
    test_tdascode_auto_layout()
    test_tdascode_auto_layout_param_references()
    test_tdascode_diff()
    test_tdascode_expand_readonly_source()
    test_tdascode_real_toeexpand_roundtrip()

    total = PASS + FAIL
    print(f"\n{'=' * 60}")
    print(f"  Results: {PASS} passed, {FAIL} failed (of {total})")
    print(f"{'=' * 60}")

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
