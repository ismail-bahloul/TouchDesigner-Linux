"""Installation workflow."""

from .utils import error, info, print_banner, success


def run_install(args):
    """Run full TouchDesigner installation."""
    print_banner("2.0-dev")
    info("Starting TouchDesigner installation...\n")

    # Check prerequisites
    _check_prerequisites()

    # Step 1: System packages
    from .distro import detect_distro, install_packages

    if not args.dry_run:
        distro = detect_distro()
        success(f"Detected: {distro.distro_name} ({distro.package_manager})")
        install_packages(distro)

    # Step 2: Wine runner
    from .wine import download_soda_runner

    info("Step 2/6: Setting up compatibility runtime...")
    if not args.dry_run:
        download_soda_runner()

    # Step 3: Wine prefix
    from .wine import setup_wine_prefix

    info("Step 3/6: Setting up compatibility environment...")
    if not args.dry_run:
        setup_wine_prefix(headless=args.headless)

    # Step 4: Windows dependencies (winetricks, DXVK)
    from .utils import ensure_dir
    from .wine import (
        WINETRICKS_TMP,
        download_winetricks,
        install_dxvk,
        install_windows_deps,
    )

    if not args.dry_run:
        info("Step 4/6: Installing compatibility libraries...")
        ensure_dir(WINETRICKS_TMP)
        download_winetricks()
        install_windows_deps()
        install_dxvk(enable=args.dxvk)

    # Step 5: IDS DLL patch
    from .patcher import patch_ids_dlls

    if not args.dry_run:
        info("Patching IDS Peak SDK DLLs...")
        patch_ids_dlls()

    # Step 6: Launcher script
    from .launcher import LAUNCHER_PATH, create_launcher_script

    if not args.dry_run:
        info("Creating launcher script...")
        create_launcher_script(nvidia_offload=args.nvidia_offload)

    # Step 7: Desktop shortcuts (TODO)
    # Step 8: Cleanup
    from .utils import safe_rm

    if not args.dry_run:
        # Clean up downloaded installer
        if (
            hasattr(args, "installer_path")
            and args.installer_path
            and os.path.isfile(args.installer_path)
        ):
            safe_rm(args.installer_path)
            info("Downloaded installer removed")

    info("Installation complete — use launch-touchdesigner.sh to start.")


def _check_prerequisites():
    """Verify required system commands are available."""
    from .utils import require_any_command, require_command

    require_command("grep")
    require_command("sed")
    require_command("tar")
    require_command("mktemp")
    require_command("find")

    if not require_any_command("curl", "wget"):
        error("Need curl or wget to download files.")
        raise SystemExit(1)
