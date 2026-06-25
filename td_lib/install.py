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

    # Step 5: Download TouchDesigner
    from .touchdesigner import (
        download_touchdesigner,
        fetch_available_versions,
        install_touchdesigner,
        select_version_interactive,
    )

    td_exe_path = None

    if args.dry_run:
        td_exe_path = "/dry-run/placeholder.exe"
    elif args.installer_path:
        info("Step 5/6: Using local installer...")
        td_exe_path = download_touchdesigner("", installer_path=args.installer_path)
    else:
        info("Step 5/6: Downloading TouchDesigner...")
        versions = fetch_available_versions()

        if args.non_interactive or args.headless:
            selected_version = (
                args.td_version if args.td_version != "latest" else versions[0]
            )
            info(f"Non-interactive mode: selected version {selected_version}")
            td_exe_path = download_touchdesigner(selected_version)
        else:
            try:
                selected = select_version_interactive(versions)
            except KeyboardInterrupt:
                info("\nInstallation cancelled by user")
                import sys

                sys.exit(1)
            if selected is None:
                info("Skipping TouchDesigner install")
            elif selected == "__custom__":
                path = input("Path to TouchDesigner installer (.exe): ").strip()
                td_exe_path = download_touchdesigner("", installer_path=path)
            else:
                td_exe_path = download_touchdesigner(selected)

    # Step 6: Install TouchDesigner
    if td_exe_path and not args.dry_run:
        info("Step 6/6: Installing TouchDesigner...")
        if not install_touchdesigner(td_exe_path):
            error("TouchDesigner installation failed")
            raise SystemExit(1)

    # Step 7: IDS DLL patch
    from .patcher import patch_ids_dlls

    if td_exe_path and not args.dry_run:
        info("Patching IDS Peak SDK DLLs...")
        patch_ids_dlls()

    # Step 8: Launcher script + desktop integration
    from .launcher import LAUNCHER_PATH, create_launcher_script

    if not args.dry_run:
        info("Creating launcher script...")
        create_launcher_script(nvidia_offload=args.nvidia_offload)
        from .desktop import run_desktop_integration

        run_desktop_integration(
            create_shortcuts_flag=not args.headless,
            associate_flag=not args.headless,
        )

    # Step 9: Cleanup
    from .touchdesigner import DOWNLOAD_DIR
    from .utils import safe_rm

    if td_exe_path and not args.dry_run:
        if os.path.isfile(td_exe_path) and DOWNLOAD_DIR in os.path.dirname(td_exe_path):
            safe_rm(td_exe_path)
            info("Downloaded installer removed (freed ~2 GB)")

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
