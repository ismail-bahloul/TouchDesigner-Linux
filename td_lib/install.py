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

    distro = detect_distro()
    success(f"Detected: {distro.distro_name} ({distro.package_manager})")

    if not args.dry_run:
        install_packages(distro)

    # Step 2: Wine runner
    # Step 3: Wine prefix
    # Step 4: Windows dependencies (winetricks, DXVK)
    # Step 5: Download TouchDesigner
    # Step 6: Install TouchDesigner
    # Step 7: IDS DLL patch
    # Step 8: Launcher, shortcuts, icons
    # Step 9: Cleanup

    info("Full installation workflow continuing in V2.0 \u2014 use install.sh for now.")


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
