"""Cleanup and uninstall workflow."""

from .utils import info, print_banner


def run_uninstall_menu(args):
    """Show uninstall menu and remove TouchDesigner versions."""
    print_banner("2.0-dev")
    info("Uninstall workflow coming in V2.0 — use install.sh for now.")
