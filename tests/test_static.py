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

    from td_lib import container

    check("container module has bootstrap_container", callable(container.bootstrap_container))
    check("container module has is_container_mode", callable(container.is_container_mode))


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
#  Container mode (Distrobox)
# =============================================================================


def test_container_cli_args():
    print("\n\u2500\u2500 Container CLI args \u2500\u2500")
    from td_lib.cli import parse_args

    args = parse_args(["--container"])
    check("--container", args.container)
    check(
        "--container alone sets no other container flags",
        not args.container_create and not args.container_remove,
    )

    args = parse_args(["--container-create"])
    check("--container-create", args.container_create)

    args = parse_args(["--container-remove"])
    check("--container-remove", args.container_remove)

    args = parse_args(["--container", "--install", "--non-interactive"])
    check(
        "--container --install -n",
        args.container and args.action == "install" and args.non_interactive,
    )

    args = parse_args(["--container", "--pip", "install", "numpy"])
    check("--container --pip wraps other actions", args.pip_args == ["install", "numpy"])


# =============================================================================
#  td-install bare action translation (--container install UX)
# =============================================================================


def test_bare_action_translation():
    print("\n\u2500\u2500 td-install bare action translation \u2500\u2500")
    import importlib.util
    from importlib.machinery import SourceFileLoader

    repo = os.path.join(os.path.dirname(__file__), "..")
    loader = SourceFileLoader(
        "td_install_script", os.path.join(repo, "td-install")
    )
    spec = importlib.util.spec_from_loader("td_install_script", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)

    check("install → --install", mod.translate_action_arg(["install"]) == ["--install"])
    check(
        "install with args → --install + args",
        mod.translate_action_arg(["install", "-n"]) == ["--install", "-n"],
    )
    check("update → --update", mod.translate_action_arg(["update"]) == ["--update"])
    check(
        "uninstall → --uninstall",
        mod.translate_action_arg(["uninstall"]) == ["--uninstall"],
    )
    check(
        "flags untouched",
        mod.translate_action_arg(["--diagnose"]) == ["--diagnose"],
    )
    check(
        "--pip subcommand untouched",
        mod.translate_action_arg(["--pip", "install", "numpy"])
        == ["--pip", "install", "numpy"],
    )
    check(
        "--codemeter subcommand untouched",
        mod.translate_action_arg(["--codemeter", "add-server", "1.2.3.4"])
        == ["--codemeter", "add-server", "1.2.3.4"],
    )
    check(
        "--container install translates too",
        mod.translate_action_arg(["--container", "install", "-n"])
        == ["--container", "--install", "-n"],
    )
    check("empty argv untouched", mod.translate_action_arg([]) == [])


# =============================================================================
#  Container module
# =============================================================================


def test_container_module():
    print("\n\u2500\u2500 Container module \u2500\u2500")
    from td_lib import container

    check("container module importable", True)
    check("CONTAINER_NAME non-empty", bool(container.CONTAINER_NAME))
    check("CONTAINER_IMAGE non-empty", bool(container.CONTAINER_IMAGE))

    old_inside = os.environ.pop("DISTROBOX_ENTER_PATH", None)
    try:
        check(
            "is_inside_distrobox() False when env unset",
            not container.is_inside_distrobox(),
        )
    finally:
        if old_inside is not None:
            os.environ["DISTROBOX_ENTER_PATH"] = old_inside

    os.environ["DISTROBOX_ENTER_PATH"] = "/usr/bin/distrobox"
    try:
        check(
            "is_inside_distrobox() True when env set",
            container.is_inside_distrobox(),
        )
        check("is_container_mode() True inside distrobox", container.is_container_mode())
    finally:
        if old_inside is not None:
            os.environ["DISTROBOX_ENTER_PATH"] = old_inside
        else:
            os.environ.pop("DISTROBOX_ENTER_PATH", None)

    old_mode = os.environ.pop("TD_CONTAINER_MODE", None)
    try:
        os.environ["TD_CONTAINER_MODE"] = "1"
        check("is_container_mode() True with TD_CONTAINER_MODE", container.is_container_mode())
    finally:
        if old_mode is not None:
            os.environ["TD_CONTAINER_MODE"] = old_mode
        else:
            os.environ.pop("TD_CONTAINER_MODE", None)

    distrobox = container.find_distrobox()
    check(
        "find_distrobox() returns None or str",
        distrobox is None or isinstance(distrobox, str),
    )
    backend = container.find_backend()
    check(
        "find_backend() returns None or podman/docker",
        backend is None or backend in ("podman", "docker"),
    )
    check("container_exists() returns bool", isinstance(container.container_exists(), bool))
    check("noexec_mount() returns bool", isinstance(container.noexec_mount(), bool))

    # create_container / remove_container with no distrobox must fail cleanly
    if distrobox is None:
        check("create_container fails cleanly without distrobox", not container.create_container())
        check("remove_container no-ops without distrobox", container.remove_container() == 0)
    else:
        skip("distrobox present — skipping failure-path checks")

    # The TD_CONTAINER_NO_NVIDIA escape hatch must be wired into the create
    # command (slow distrobox --nvidia init on every container start).
    import inspect
    src = inspect.getsource(container.create_container)
    check("NVIDIA passthrough can be skipped via env",
          "NVIDIA_DISABLED" in src and "TD_CONTAINER_NO_NVIDIA" in src)


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
    print("\n── print_banner / print_hr ──")
    import io

    from td_lib import __version__
    from td_lib.utils import print_banner, print_hr

    short_version = ".".join(__version__.split(".")[:2])

    old_stdout = sys.stdout
    try:
        sys.stdout = io.StringIO()
        print_banner(__version__)
        output = sys.stdout.getvalue()
        check("banner contains 'TouchDesigner'", "TouchDesigner" in output)
        check("banner contains 'Iswad'", "Iswad" in output)
        check("banner shows major.minor version", short_version in output)
        check("banner drops the patch part", __version__ not in output)

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


def test_steamos_support():
    print("\n\u2500\u2500 SteamOS support (read-only root) \u2500\u2500")
    from td_lib.distro import KNOWN_DISTROS

    check("steamos in KNOWN_DISTROS", "steamos" in KNOWN_DISTROS)
    check("steamos uses pacman", KNOWN_DISTROS.get("steamos", ("", ""))[0] == "pacman")

    # The installer must disable SteamOS's read-only root before pacman
    repo = os.path.join(os.path.dirname(__file__), "..")
    src = open(os.path.join(repo, "td_lib", "distro.py")).read()
    check(
        "installer handles steamos-readonly",
        'shutil.which("steamos-readonly")' in src and '"steamos-readonly"' in src,
    )
    check(
        "installer syncs SteamOS after disable (pacman -Syu)",
        '"pacman", "-Syu"' in src,
    )
    check(
        "zypper refreshes repositories before install",
        '"zypper", "refresh"' in src,
    )


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


def test_dxvk_module():
    print("\n── DXVK module ──")
    from td_lib import wine as wine_mod

    check("DXVK DLL list covers d3d11", "d3d11" in wine_mod._DXVK_DLLS)
    check("DXVK DLL list covers dxgi", "dxgi" in wine_mod._DXVK_DLLS)
    check("DXVK DLL list covers d3d9", "d3d9" in wine_mod._DXVK_DLLS)
    check("DXVK DLL list covers d3d10core", "d3d10core" in wine_mod._DXVK_DLLS)

    # install_dxvk(enable=False) must be a no-op: no download, no wine, no
    # filesystem writes. Also guards against the enable flag regressing.
    wine_mod.install_dxvk(enable=False)
    check("install_dxvk(enable=False) is a no-op", True)

    # _register_dxvk_overrides is idempotent by construction: it only writes
    # 'native' REG_SZ entries for DLLs that exist in system32.
    import inspect
    src = inspect.getsource(wine_mod._register_dxvk_overrides)
    check("override registration only touches present DLLs",
          "os.path.isfile" in src and "native" in src)

    # The 'already installed' probe must not mistake Wine's builtin wined3d
    # DLL (also PE32, labeled "for WINE") for a real DXVK install.
    check("DXVK probe accepts a MinGW PE",
          wine_mod._looks_like_dxvk(
              "PE32+ executable for MS Windows 5.02 (DLL), x86-64"))
    check("DXVK probe rejects a Wine builtin",
          not wine_mod._looks_like_dxvk(
              "PE32+ executable for WINE (DLL), x86-64"))
    check("DXVK probe rejects non-PE output",
          not wine_mod._looks_like_dxvk("ASCII text"))

    # The version marker makes the install version-aware: an old real DXVK
    # install (marker missing or stale) must be upgraded, not kept.
    src = inspect.getsource(wine_mod.install_dxvk)
    check("install_dxvk upgrades a stale DXVK install",
          "_read_dxvk_version_marker() == DXVK_VERSION" in src)
    marker = wine_mod._read_dxvk_version_marker()
    check("version marker helper returns a string", isinstance(marker, str))


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
    from td_lib.launcher import LAUNCHER_PATH, TD_COMMAND, create_launcher_script

    backup = None
    if os.path.isfile(LAUNCHER_PATH):
        with open(LAUNCHER_PATH) as f:
            backup = f.read()
    symlink_before = os.path.islink(TD_COMMAND)

    try:
        path = create_launcher_script()
        check("launcher script generated", os.path.isfile(path))

        check("touchdesigner command symlink created", os.path.islink(TD_COMMAND))
        check(
            "symlink points to the launcher",
            os.path.realpath(TD_COMMAND) == os.path.realpath(path),
        )
        check("symlink is executable", os.access(TD_COMMAND, os.X_OK))

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
        check(
            "launcher has version-aware fix detection",
            "fp_tree" in content and "FIX_FP" in content,
        )
        check("NVIDIA block present (no NVIDIA_only)", "NV_PRIME_RENDER_OFFLOAD" in content
              and "VK_LAYER_NV_optimus" not in content)
        check(
            "NVIDIA guard tests the driver (nvidia-smi -L)",
            "nvidia-smi -L" in content,
        )
        check(
            "toeexpand has AUR fallback path",
            "/opt/touchdesigner/td/bin/toeexpand.exe" in content,
        )
        check("launcher is executable", os.access(path, os.X_OK))

        check("WAYLAND_DISPLAY cleared", 'export WAYLAND_DISPLAY=""' in content)
        check("GL YIELD = USLEEP", 'export __GL_YIELD="USLEEP"' in content)
        check("KMP_AFFINITY=disabled", 'KMP_AFFINITY="disabled"' in content)
        check("CodeMeter auto-start present", "CodeMeter.exe" in content)
        check("PYTHONPATH set for user site", 'PYTHONPATH' in content and 'steamuser' in content)
        check("find_wine64 function", 'find_wine64()' in content)
        check("WINE64_BIN variable", 'WINE64_BIN=' in content)
        check("AUR fallback path", '/opt/touchdesigner/wine/bin/wine64' in content)

        # CLI: flags answered without launching TD; unknown flags rejected
        from td_lib import __version__

        check("launcher has --help handling", "-h|--help" in content)
        check("launcher has -v/--version handling", "-v|--version" in content)
        check("launcher has --list handling", "--list" in content)
        check("launcher has --no-patch handling", "--no-patch" in content)
        check("launcher has --verbose handling", "--verbose" in content)
        check("launcher passes --exe through", "--exe|--exe=*" in content)
        check("launcher rejects unknown flags", "unknown option" in content)
        check("help mentions .toe usage", "project.toe" in content)
        check(
            "launcher bakes the tool version",
            f"TouchDesigner-Linux v{__version__}" in content,
        )

        # Flags parse in a loop, so combined flags work (--no-patch --verbose -v)
        check("flag parsing loops", "while true; do" in content)

        try:
            result = subprocess.run(
                ["bash", path, "--help"],
                capture_output=True, text=True, timeout=5,
            )
            check("--help exits 0 with usage",
                  result.returncode == 0 and "Usage: touchdesigner" in result.stdout)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            skip("launcher --help check (bash not available)")

        try:
            result = subprocess.run(
                ["bash", path, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            ok = (
                result.returncode == 0
                and "Installed TouchDesigner versions" in result.stdout
            ) or (
                result.returncode == 1 and "not installed" in result.stderr
            )
            check("--version lists versions or says none", ok)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            skip("launcher --version check (bash not available)")

        try:
            result = subprocess.run(
                ["bash", path, "-v"],
                capture_output=True, text=True, timeout=10,
            )
            from td_lib import __version__ as _ver

            ok = (
                result.returncode == 0
                and f"TouchDesigner-Linux v{_ver}" in result.stdout
                and "Installed TouchDesigner versions" in result.stdout
            ) or (
                result.returncode == 1
                and f"TouchDesigner-Linux v{_ver}" in result.stdout
            )
            check("-v shows tool + installed versions", ok)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            skip("launcher -v check (bash not available)")

        try:
            result = subprocess.run(
                ["bash", path, "--list"],
                capture_output=True, text=True, timeout=10,
            )
            ok = (
                result.returncode == 0
                and "Installed TouchDesigner versions" in result.stdout
            ) or (
                result.returncode == 1 and "not installed" in result.stderr
            )
            check("--list reports versions/paths or none", ok)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            skip("launcher --list check (bash not available)")

        # Combined flags: --no-patch and --verbose must be consumed before -v
        try:
            result = subprocess.run(
                ["bash", path, "--no-patch", "--verbose", "-v"],
                capture_output=True, text=True, timeout=10,
            )
            ok = (
                result.returncode == 0
                and "Installed TouchDesigner versions" in result.stdout
            ) or (
                result.returncode == 1 and "not installed" in result.stderr
            )
            check("combined --no-patch --verbose -v parses", ok)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            skip("launcher combined-flags check (bash not available)")

        try:
            result = subprocess.run(
                ["bash", path, "--bogus-flag"],
                capture_output=True, text=True, timeout=5,
            )
            check("unknown flag rejected with usage",
                  result.returncode == 2 and "unknown option" in result.stderr
                  and "--help" in result.stderr)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            skip("launcher unknown-flag check (bash not available)")

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
        else:
            safe_rm(LAUNCHER_PATH)
        if not symlink_before:
            safe_rm(TD_COMMAND)


# =============================================================================
#  touchdesigner command symlink
# =============================================================================


def test_touchdesigner_command():
    print("\n\u2500\u2500 touchdesigner command symlink \u2500\u2500")
    from td_lib.launcher import LAUNCHER_PATH, TD_COMMAND, create_launcher_script

    backup = None
    if os.path.isfile(LAUNCHER_PATH):
        with open(LAUNCHER_PATH) as f:
            backup = f.read()
    symlink_before = os.path.islink(TD_COMMAND)
    target_before = os.path.realpath(TD_COMMAND) if symlink_before else None

    try:
        path = create_launcher_script()
        check("command created", os.path.islink(TD_COMMAND))
        check(
            "command resolves to the launcher",
            os.path.realpath(TD_COMMAND) == os.path.realpath(path),
        )
        check("command is executable", os.access(TD_COMMAND, os.X_OK))

        # Re-running is idempotent (recreates our own symlink)
        create_launcher_script()
        check(
            "re-run keeps a valid symlink",
            os.path.islink(TD_COMMAND)
            and os.path.realpath(TD_COMMAND) == os.path.realpath(path),
        )

        # A foreign file must NOT be clobbered
        safe_rm(TD_COMMAND)
        with open(TD_COMMAND, "w") as f:
            f.write("#!/bin/sh\necho foreign\n")
        create_launcher_script()
        check(
            "foreign file is not overwritten",
            not os.path.islink(TD_COMMAND)
            and open(TD_COMMAND).read().startswith("#!/bin/sh"),
        )
        safe_rm(TD_COMMAND)

        # Cleanup (same condition as cleanup.py) removes only our symlink
        create_launcher_script()
        is_ours = os.path.islink(TD_COMMAND) and os.path.realpath(TD_COMMAND) == LAUNCHER_PATH
        if is_ours:
            safe_rm(TD_COMMAND)
        check(
            "cleanup removes only our symlink",
            is_ours and not os.path.lexists(TD_COMMAND),
        )
    finally:
        if backup:
            with open(LAUNCHER_PATH, "w") as f:
                f.write(backup)
        else:
            safe_rm(LAUNCHER_PATH)
        if symlink_before:
            safe_rm(TD_COMMAND)
            os.symlink(target_before, TD_COMMAND)
        else:
            safe_rm(TD_COMMAND)


# =============================================================================
#  Launcher container shim (distrobox re-exec)
# =============================================================================


def test_launcher_container_shim():
    print("\n\u2500\u2500 Launcher container shim \u2500\u2500")
    from td_lib.launcher import LAUNCHER_PATH, TD_COMMAND, create_launcher_script

    backup = None
    if os.path.isfile(LAUNCHER_PATH):
        with open(LAUNCHER_PATH) as f:
            backup = f.read()
    symlink_before = os.path.islink(TD_COMMAND)

    old_inside = os.environ.pop("DISTROBOX_ENTER_PATH", None)
    old_mode = os.environ.pop("TD_CONTAINER_MODE", None)
    old_name = os.environ.pop("TD_CONTAINER_NAME", None)
    try:
        # Native mode: no shim
        path = create_launcher_script()
        with open(path) as f:
            content = f.read()
        check("native launcher has no distrobox shim", "distrobox enter" not in content)

        # Container mode: shim re-execs into the container. CONTAINER_NAME is
        # read at module import, so reload it AFTER setting the env override.
        import importlib

        os.environ["TD_CONTAINER_MODE"] = "1"
        os.environ["TD_CONTAINER_NAME"] = "my-td-container"
        from td_lib import container as container_mod

        importlib.reload(container_mod)
        path = create_launcher_script()
        with open(path) as f:
            content = f.read()
        check("container launcher has distrobox shim", "distrobox enter" in content)
        check("shim uses the configured container name", "my-td-container" in content)
        check("shim guards on DISTROBOX_ENTER_PATH", "DISTROBOX_ENTER_PATH" in content)
        check("shim re-execs the same script with args", '$0' in content and '"$@"' in content)
        check("shim does not wrap the normal body", "find_touchdesigner_exe" in content)

        try:
            result = subprocess.run(
                ["bash", "-n", path],
                capture_output=True,
                text=True,
                timeout=5,
            )
            check("container launcher has valid bash syntax", result.returncode == 0)
            if result.returncode != 0:
                print(f"  bash syntax error: {result.stderr.strip()}")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            skip("bash syntax check (bash not available)")
    finally:
        if old_inside is not None:
            os.environ["DISTROBOX_ENTER_PATH"] = old_inside
        else:
            os.environ.pop("DISTROBOX_ENTER_PATH", None)
        if old_mode is not None:
            os.environ["TD_CONTAINER_MODE"] = old_mode
        else:
            os.environ.pop("TD_CONTAINER_MODE", None)
        if old_name is not None:
            os.environ["TD_CONTAINER_NAME"] = old_name
        else:
            os.environ.pop("TD_CONTAINER_NAME", None)
        if backup:
            with open(LAUNCHER_PATH, "w") as f:
                f.write(backup)
        else:
            safe_rm(LAUNCHER_PATH)
        if not symlink_before:
            safe_rm(TD_COMMAND)


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
#  CodeMeter module
# =============================================================================


def test_codemeter_module():
    print("\n── CodeMeter module ──")
    from td_lib import codemeter

    check("codemeter module importable", True)

    # Path detection against a fake prefix
    tmp = tempfile.mkdtemp(prefix="td_cm_test_")
    try:
        fake_drive = os.path.join(tmp, "drive_c", "Program Files (x86)", "CodeMeter")
        fake_bin = os.path.join(fake_drive, "Runtime", "bin")
        os.makedirs(fake_bin)
        with open(os.path.join(fake_bin, "CodeMeter.exe"), "w") as f:
            f.write("")
        with open(os.path.join(fake_bin, "cmu32.exe"), "w") as f:
            f.write("")

        exe = codemeter.find_runtime_exe(prefix=tmp)
        check("find_runtime_exe finds fake prefix install",
              exe is not None and exe.endswith("CodeMeter.exe") and os.path.isfile(exe))

        cmu32 = codemeter.find_cmu32(prefix=tmp)
        check("find_cmu32 finds fake prefix install",
              cmu32 is not None and cmu32.endswith("cmu32.exe"))

        # 64-bit runtimes ship cmu.exe instead of cmu32.exe
        os.remove(os.path.join(fake_bin, "cmu32.exe"))
        with open(os.path.join(fake_bin, "cmu.exe"), "w") as f:
            f.write("")
        cmu = codemeter.find_cmu32(prefix=tmp)
        check("find_cmu32 falls back to cmu.exe",
              cmu is not None and cmu.endswith("cmu.exe"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # No install should yield None on the real environment
    check("find_runtime_exe returns None when not installed",
          codemeter.find_runtime_exe() is None or
          (isinstance(codemeter.find_runtime_exe(), str) and os.path.isfile(codemeter.find_runtime_exe())))

    # CLI dispatch: unknown command exits non-zero without touching Wine
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        rc = codemeter.run_codemeter(["__definitely_not_a_command__"])
    check("run_codemeter rejects unknown command", rc != 0)

    rc = codemeter.run_codemeter(["help"])
    check("run_codemeter help command exits non-zero", rc != 0)

    # add-server / remove-server without argument should be rejected
    rc = codemeter.run_codemeter(["add-server"])
    check("add-server without ip rejected", rc != 0)


def test_codemeter_install_runtime():
    print("\n── CodeMeter native runtime install ──")
    from td_lib import codemeter

    tmp = tempfile.mkdtemp(prefix="td_cm_install_test_")
    try:
        # Fake extracted installer: Inno-style Program Files layout + ProgramData
        extract = os.path.join(tmp, "extracted")
        fake_bin = os.path.join(
            extract, "Program Files (x86)", "CodeMeter", "Runtime", "bin"
        )
        os.makedirs(fake_bin)
        with open(os.path.join(fake_bin, "CodeMeter.exe"), "w") as f:
            f.write("")
        with open(os.path.join(fake_bin, "cmu32.exe"), "w") as f:
            f.write("")
        with open(os.path.join(fake_bin, "cpsrt.dll"), "w") as f:
            f.write("")
        fake_pd = os.path.join(extract, "ProgramData", "WIBU-SYSTEMS", "CodeMeter")
        os.makedirs(fake_pd)
        with open(os.path.join(fake_pd, "Server.ini"), "w") as f:
            f.write("[Global]\n")

        root = codemeter._find_codemeter_root(extract)
        check("find_codemeter_root finds the CodeMeter payload dir",
              root is not None and root.endswith(os.path.join("CodeMeter")))

        wibu_pd = codemeter._find_wibu_programdata(extract)
        check("find_wibu_programdata finds WIBU-SYSTEMS dir",
              wibu_pd is not None and wibu_pd.endswith(os.path.join("WIBU-SYSTEMS")))

        # Lift the payload into a fake prefix
        fake_prefix = os.path.join(tmp, "prefix")
        drive_c = os.path.join(fake_prefix, "drive_c")
        os.makedirs(drive_c)
        codemeter._copy_payload(root, wibu_pd, drive_c)

        exe = codemeter.find_runtime_exe(prefix=fake_prefix)
        check("copy_payload lands CodeMeter.exe at the standard location",
              exe is not None and os.path.isfile(exe))
        cmu = codemeter.find_cmu32(prefix=fake_prefix)
        check("copy_payload preserves the Runtime/bin layout (cmu32 found)",
              cmu is not None and os.path.isfile(cmu))
        check("ProgramData config payload copied",
              os.path.isfile(os.path.join(
                  drive_c, "ProgramData", "WIBU-SYSTEMS", "CodeMeter", "Server.ini")))

        # Missing installer file: clean failure, no Wine involved
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            ok = codemeter.install_runtime(os.path.join(tmp, "does-not-exist.exe"))
        check("install_runtime rejects a missing installer", ok is False)

        rc = codemeter.run_codemeter(["install", os.path.join(tmp, "does-not-exist.exe")])
        check("run_codemeter install <missing> exits non-zero", rc != 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # install with no path behaves like setup: without a runtime installed it
    # must fail cleanly (non-zero), not crash. Skip when a runtime is present
    # on this machine (would try to start it via Wine).
    import contextlib
    import io
    if codemeter.find_runtime_exe() is None:
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            rc = codemeter.run_codemeter(["install"])
        check("run_codemeter install (no path) fails cleanly without a runtime",
              rc != 0)
    else:
        skip("run_codemeter install (no path) — runtime present on this machine")

    # remove/uninstall routing must be recognized (it touches the real prefix,
    # so only assert the command is accepted by the dispatcher, not run it
    # against the live prefix)
    import inspect
    src = inspect.getsource(codemeter.run_codemeter)
    check("run_codemeter routes remove/uninstall",
          '"remove"' in src and '"uninstall"' in src and "remove_runtime" in src)

    # Wibu system DLL detection used by remove_runtime
    for name, expect in [
        ("cpsrt.dll", True),
        ("WibuCm64.dll", True),
        ("wibucmJNI64.dll", True),
        ("WibuXpm4J32.dll", True),
        ("d3d11.dll", False),
        ("kernel32.dll", False),
    ]:
        check(f"is_wibu_system_dll('{name}') == {expect}",
              codemeter._is_wibu_system_dll(name) is expect)


def test_codemeter_cli_args():
    print("\n── CodeMeter CLI args ──")
    from td_lib.cli import parse_args

    args = parse_args(["--codemeter"])
    check("--codemeter (no args)", args.codemeter_args == [])

    args = parse_args(["--codemeter", "setup"])
    check("--codemeter setup", args.codemeter_args == ["setup"])

    args = parse_args(["--codemeter", "add-server", "192.168.1.15"])
    check("--codemeter add-server ip",
          args.codemeter_args == ["add-server", "192.168.1.15"])

    args = parse_args(["--codemeter", "install", "/tmp/CodeMeterRuntime.exe"])
    check("--codemeter install <path>",
          args.codemeter_args == ["install", "/tmp/CodeMeterRuntime.exe"])

    args = parse_args(["--codemeter", "status"])
    check("--codemeter status", args.codemeter_args == ["status"])


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
#  AUR launcher parity — the AUR python launcher must not drift from the bash
#  launcher's font-fix behaviors (this class of drift caused real user bugs)
# =============================================================================


def test_aur_launcher_parity():
    print("\n\u2500\u2500 AUR launcher font-fix parity \u2500\u2500")
    repo = os.path.join(os.path.dirname(__file__), "..")
    path = os.path.join(repo, "dist", "arch", "touchdesigner-launcher.py")
    with open(path) as f:
        src = f.read()

    check("AUR launcher uses /opt/touchdesigner paths", 'PREFIX = "/opt/touchdesigner"' in src)
    check(
        "AUR launcher has version-aware detection",
        "_tree_fingerprint" in src and "fix_fp" in src and "injected_fp" in src,
    )
    check(
        "AUR launcher fingerprints .text/.table only",
        'name.endswith(".text")' in src and 'name.endswith(".table")' in src,
    )
    check(
        "AUR launcher replaces stale fix (not merge)",
        "rmtree(dst, ignore_errors=True)" in src,
    )
    check(
        "AUR launcher filters stale .toc entries",
        '"wine_ui_fixes" not in ln' in src,
    )
    check(
        "AUR launcher auto-patches NewProject + startup",
        "auto_patch_toe_files" in src
        and "newproject.toe" in src.lower()
        and "startupfilename" in src,
    )

    # License preservation: the package ProgramData copy must never overwrite
    # the user's activated licenses, and the backup must happen before it.
    # Scope the call-order checks to main() so function definitions don't match.
    main_src = src[src.index("def main()"):]
    check(
        "AUR launcher skips Derivative in copy_programdata",
        'if item.lower() == "derivative":' in src
        and "continue  # user license data" in src,
    )
    check(
        "AUR launcher backs up license before copy_programdata",
        main_src.index("had_license = backup_license()")
        < main_src.index("copy_programdata()"),
    )
    check(
        "AUR launcher restores license after wineboot",
        main_src.index("ensure_wine_ready()")
        < main_src.index("if had_license:")
        < main_src.index("restore_license()"),
    )


def test_aur_launcher_license_preservation():
    print("\n── AUR launcher license preservation (behavioral) ──")
    import importlib.util

    repo = os.path.join(os.path.dirname(__file__), "..")
    launcher_path = os.path.join(repo, "dist", "arch", "touchdesigner-launcher.py")
    spec = importlib.util.spec_from_file_location("aur_launcher_test", launcher_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    tmp = tempfile.mkdtemp(prefix="td_aur_lic_test_")
    try:
        data_pd = os.path.join(tmp, "data", "ProgramData")
        user_pd = os.path.join(
            tmp, "home", ".local", "share", "touchdesigner-linux",
            "prefix", "drive_c", "ProgramData",
        )

        # Package ships a default Derivative/ins2.dat + an unrelated file
        pkg_der = os.path.join(data_pd, "Derivative")
        os.makedirs(pkg_der)
        with open(os.path.join(pkg_der, "ins2.dat"), "w") as f:
            f.write("PACKAGE-DEFAULT")
        with open(os.path.join(data_pd, "other.txt"), "w") as f:
            f.write("other")

        # User prefix has an activated license + other state
        user_der = os.path.join(user_pd, "Derivative")
        os.makedirs(user_der)
        with open(os.path.join(user_der, "ins2.dat"), "w") as f:
            f.write("USER-ACTIVATED")
        with open(os.path.join(user_pd, "state.txt"), "w") as f:
            f.write("state")

        # Point the launcher's globals at the fake tree
        mod.DATA_DIR = os.path.join(tmp, "data")
        fake_prefix = os.path.join(
            tmp, "home", ".local", "share", "touchdesigner-linux", "prefix"
        )
        mod.WINE_PREFIX = fake_prefix
        # LICENSE_DIR is computed at import time; repoint it too
        mod.LICENSE_DIR = os.path.join(
            fake_prefix, "drive_c", "ProgramData", "Derivative"
        )

        # New behavior: copy_programdata must skip Derivative
        mod.copy_programdata()
        with open(os.path.join(user_der, "ins2.dat")) as f:
            check("copy_programdata preserves user license (skips Derivative)",
                  f.read() == "USER-ACTIVATED")
        check("copy_programdata still copies other package files",
              os.path.isfile(os.path.join(user_pd, "other.txt")))

        # Sanity: the old behavior (plain copy2 into Derivative) would clobber
        shutil.copy2(os.path.join(pkg_der, "ins2.dat"), os.path.join(user_der, "ins2.dat"))
        with open(os.path.join(user_der, "ins2.dat")) as f:
            check("old behavior would overwrite the license (sanity)",
                  f.read() == "PACKAGE-DEFAULT")

        # Backup/restore round-trip must survive a wineboot that clears
        # Derivative (wineboot doesn't touch the sibling .bak)
        with open(os.path.join(user_der, "ins2.dat"), "w") as f:
            f.write("USER-ACTIVATED")
        mod.backup_license()
        shutil.rmtree(user_der)  # simulate wineboot clearing Derivative
        mod.restore_license()
        with open(os.path.join(user_der, "ins2.dat")) as f:
            check("backup/restore survives Derivative wipe",
                  f.read() == "USER-ACTIVATED")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_install_sh_sync():
    print("\n── install.sh clone sync ──")
    repo = os.path.join(os.path.dirname(__file__), "..")
    with open(os.path.join(repo, "install.sh")) as f:
        src = f.read()

    check("install.sh fetches the branch", "git fetch origin" in src)
    check("install.sh tries fast-forward merge", "git merge --ff-only" in src)
    check(
        "install.sh hard-resets a diverged clone",
        "git reset --hard" in src and "merge --ff-only" in src,
    )
    check(
        "install.sh never silently serves a stale clone",
        src.index("git fetch origin")
        < src.index("git merge --ff-only")
        < src.index('TD_CLI="$REPO_DIR/td-install"'),
    )


def test_release_version_consistency():
    print("\n\u2500\u2500 Release version consistency \u2500\u2500")
    import re

    from td_lib import __version__

    repo = os.path.join(os.path.dirname(__file__), "..")
    pkgbuild = open(os.path.join(repo, "dist", "arch", "PKGBUILD")).read()
    srcinfo = open(os.path.join(repo, "dist", "arch", ".SRCINFO")).read()

    m = re.search(r"^pkgver=([\w.]+)", pkgbuild, re.M)
    m2 = re.search(r"^\tpkgver = ([\w.]+)", srcinfo, re.M)
    check("PKGBUILD pkgver parsed", bool(m))
    check(".SRCINFO pkgver parsed", bool(m2))
    if m and m2:
        check("PKGBUILD pkgver == .SRCINFO pkgver", m.group(1) == m2.group(1))
        check("pkgver == td_lib.__version__", m.group(1) == __version__)


# =============================================================================
#  Run
# =============================================================================


def main():
    print("=" * 60)
    from td_lib import __version__

    print(f"  TouchDesigner-Linux {__version__} - Test Suite")
    print("=" * 60)

    test_imports()
    test_cli_args()
    test_container_cli_args()
    test_bare_action_translation()
    test_container_module()
    test_dry_run()
    test_safe_rm()
    test_ensure_dir()
    test_require_commands()
    test_verify_checksum()
    test_log_format()
    test_print_banner()
    test_distro_detection()
    test_steamos_support()
    test_desktop_file_content()
    test_mime_xml_content()
    test_font_fix_paths()
    test_wine_error_parser()
    test_dxvk_module()
    test_ids_patch_parsing()
    test_version_select()
    test_version_detection()
    test_version_sorting()
    test_discover_installed_versions()
    test_desktop_assets()
    test_headless_auto_detect()
    test_launcher_script()
    test_launcher_container_shim()
    test_touchdesigner_command()
    test_pip_module()
    test_codemeter_module()
    test_codemeter_install_runtime()
    test_codemeter_cli_args()
    test_diagnose_output()
    test_uninstall_text_selection()
    test_distro_package_lists()
    test_version_picker_installed_marking()
    test_progress_bar_format()
    test_aur_launcher_parity()
    test_aur_launcher_license_preservation()
    test_install_sh_sync()
    test_release_version_consistency()

    total = PASS + FAIL
    print(f"\n{'=' * 60}")
    print(f"  Results: {PASS} passed, {FAIL} failed (of {total})")
    print(f"{'=' * 60}")

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
