"""CLI argument parsing for td-install."""

import argparse
import os
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="td-install",
        description="Install TouchDesigner on Linux.",
        epilog="Report issues: https://github.com/iswad-lab/TouchDesigner-Linux/issues",
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

    # TD-as-Code (tdascode)
    code = parser.add_argument_group("td-as-code")
    code.add_argument(
        "--expand",
        dest="expand_file",
        metavar="FILE",
        help="Expand a .toe/.tox into a readable .dir folder",
    )
    code.add_argument(
        "--collapse",
        dest="collapse_file",
        metavar="FILE",
        help="Collapse a .dir folder back into its .toe/.tox",
    )
    code.add_argument(
        "--info",
        dest="info_file",
        metavar="FILE",
        help="Show the node structure of a .toe/.tox project",
    )
    code.add_argument(
        "--diff",
        dest="diff_files",
        nargs=2,
        metavar=("FILE_A", "FILE_B"),
        help="Show a semantic diff between two .toe/.tox projects",
    )
    code.add_argument(
        "--list-types",
        dest="list_types",
        nargs="?",
        const="",
        default=None,
        metavar="FAMILY",
        help="List available TouchDesigner node types (optionally filtered by family)",
    )
    code.add_argument(
        "--type-info",
        dest="type_info",
        metavar="TYPE",
        help="Show details about a node type (e.g. 'POP:null')",
    )

    args = parser.parse_args(argv)
    return args
