"""Update workflow: launcher, winetricks, DXVK, font fix, icons."""

import sys

from .utils import info, print_banner, success


def run_update(args) -> None:
    """Update launcher, winetricks, DXVK, UI fixes, and icons."""
    if sys.stdout.isatty():
        print("\033[2J\033[H", end="")
    print_banner("1.4")
    info("Starting TouchDesigner update...\n")

    # 1. Regenerate launcher
    from .launcher import create_launcher_script

    info("Regenerating launcher script...")
    create_launcher_script(nvidia_offload=args.nvidia_offload)
    success("Launcher updated")

    # 2. Icons
    from .desktop import install_icons

    info("Updating icons...")
    icon_path = install_icons()
    if icon_path != "touchdesigner":
        info(f"Icon installed: {icon_path}")

    # 3. Winetricks
    from .wine import download_winetricks

    info("Updating winetricks...")
    download_winetricks()
    success("Winetricks updated")

    # 4. DXVK
    from .wine import install_dxvk

    info("Updating DXVK...")
    install_dxvk(enable=args.dxvk)
    success("DXVK updated")

    # 5. Font fix
    from .desktop import distribute_font_fix, install_font_fix

    info("Updating wine_ui_fixes.tox...")
    fix_path = install_font_fix()
    if fix_path:
        distribute_font_fix()
        success("UI fixes updated")

    # 6. Desktop shortcuts (regenerate)
    from .desktop import create_shortcuts, create_versioned_shortcuts

    info("Regenerating shortcuts...")
    create_shortcuts(icon_path)
    create_versioned_shortcuts(icon_path)

    # 7. Patch .toe files in all installed TouchDesigner versions
    from .patches import patch_toe_projects_in_drive

    info("Patching .toe files...")
    patch_toe_projects_in_drive()

    print()
    success("Update Complete")
    info("TouchDesigner components are up to date!")
