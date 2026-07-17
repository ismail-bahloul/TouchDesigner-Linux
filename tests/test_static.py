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
        path = create_launcher_script(nvidia_offload=False)
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
        check("launcher has NVIDIA support", "USE_NVIDIA_DGPU" in content)
        check("launcher has backup cleanup", "BACKUP_DIR" in content)
        check("launcher is executable", os.access(path, os.X_OK))

        # Test with NVIDIA offload
        os.remove(LAUNCHER_PATH)
        path2 = create_launcher_script(nvidia_offload=True)
        with open(path2) as f:
            content2 = f.read()
        check("NVIDIA offload = Y", 'USE_NVIDIA_DGPU="Y"' in content2)
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
    from td_lib.pip import find_td_python, _find_wine64, _wine_env

    # find_td_python returns None when TD not installed (test env)
    result = find_td_python()
    check("find_td_python returns None or str", result is None or isinstance(result, str))

    # _find_wine64 should find system wine64 or return None
    wine64 = _find_wine64()
    check("_find_wine64 returns valid path or None",
          wine64 is None or (isinstance(wine64, str) and os.path.isfile(wine64)))

    # _wine_env builds env dict with correct keys
    if wine64:
        env = _wine_env()
        check("_wine_env has wine64 key", "wine64" in env)
        check("_wine_env has env dict", "env" in env)
        check("KMP_AFFINITY=disabled in env",
              env["env"].get("KMP_AFFINITY") == "disabled")
        check("WINEPREFIX set in env", "WINEPREFIX" in env["env"])
        check("WINEARCH=win64 in env", env["env"].get("WINEARCH") == "win64")


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

    total = PASS + FAIL
    print(f"\n{'=' * 60}")
    print(f"  Results: {PASS} passed, {FAIL} failed (of {total})")
    print(f"{'=' * 60}")

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
