"""CLI argument parsing for td-install."""

import argparse
import os
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="td-install",
        description="Install TouchDesigner on Linux.",
        epilog="Report issues: https://github.com/ismail-bahloul/TouchDesigner-Linux/issues",
    )

    # Actions (mutually exclusive)
    action = parser.add_argument_group("actions")
    action.add_argument(
        "--install",
        dest="action",
        action="store_const",
        const="install",
        help="Install TouchDesigner (default if no action specified)",
    )
    action.add_argument(
        "--update",
        dest="action",
        action="store_const",
        const="update",
        help="Update launcher, winetricks, DXVK, and UI fixes",
    )
    action.add_argument(
        "--uninstall",
        dest="action",
        action="store_const",
        const="uninstall",
        help="Remove TouchDesigner versions or everything",
    )
    action.add_argument(
        "--diagnose",
        dest="diagnose",
        action="store_true",
        help="Run system health check and print report",
    )

    # Mode flags
    mode = parser.add_argument_group("mode")
    mode.add_argument(
        "-n",
        "--non-interactive",
        dest="non_interactive",
        action="store_true",
        help="Run without prompts (auto-confirm defaults)",
    )
    mode.add_argument(
        "-H",
        "--headless",
        dest="headless",
        action="store_true",
        help="Headless mode (SSH, no display) — skips GUI-requiring steps",
    )
    mode.add_argument(
        "-f",
        "--fast",
        dest="fast",
        action="store_true",
        help="Fast mode — skip pauses between steps",
    )

    # Version selection
    version = parser.add_argument_group("version")
    version.add_argument(
        "-v",
        "--td-version",
        dest="td_version",
        default="latest",
        help="TouchDesigner version to install (e.g. 2025.32460)",
    )
    version.add_argument(
        "-i",
        "--installer",
        dest="installer_path",
        help="Path to a local TouchDesigner .exe installer",
    )

    # Options
    opts = parser.add_argument_group("options")

    opts.add_argument(
        "--no-dxvk",
        dest="dxvk",
        action="store_false",
        default=True,
        help="Skip DXVK installation",
    )
    opts.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_true",
        help="Enable debug output",
    )
    opts.add_argument(
        "-V",
        "--version",
        dest="version",
        action="store_true",
        help="Show version and exit",
    )
    opts.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Simulate installation (no changes made)",
    )
    opts.add_argument(
        "--patch-toe",
        dest="patch_toe",
        metavar="FILE",
        help="Apply wine_ui_fixes.tox to a .toe file",
    )
    opts.add_argument(
        "--pip",
        dest="pip_args",
        nargs=argparse.REMAINDER,
        metavar="...",
        help="Run pip inside TouchDesigner's embedded Python (e.g. --pip install numpy)",
    )
    opts.add_argument(
        "--codemeter",
        dest="codemeter_args",
        nargs=argparse.REMAINDER,
        metavar="...",
        help=(
            "Manage the CodeMeter licensing runtime (dongles / network "
            "licenses). e.g. --codemeter setup, "
            "--codemeter add-server 192.168.1.15, "
            "--codemeter install /path/to/CodeMeterRuntime.exe"
        ),
    )

    # Container mode (Distrobox)
    container = parser.add_argument_group("container")
    container.add_argument(
        "--container",
        dest="container",
        action="store_true",
        help=(
            "Run inside an isolated Distrobox container — the host system "
            "is never modified. Wraps any other action (install, update, "
            "uninstall, --pip, --codemeter, --diagnose...)."
        ),
    )
    container.add_argument(
        "--container-create",
        dest="container_create",
        action="store_true",
        help="Recreate the container first, then run in container mode",
    )
    container.add_argument(
        "--container-remove",
        dest="container_remove",
        action="store_true",
        help="Remove the container (and the system packages inside it)",
    )

    args = parser.parse_args(argv)
    return args
