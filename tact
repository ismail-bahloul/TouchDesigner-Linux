#!/usr/bin/env python3
"""
Tact — TouchDesigner on Linux.

Usage:
    tact                            Install (auto-detect graphical / headless)
    tact --diagnose                 System health check
    tact --help                     Full options
    tact run [project.toe]          Launch TouchDesigner
    tact pip install numpy          Install Python packages
"""

import os
import sys

# Ensure the tact_lib package is importable
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# Also check system-installed location (AUR, system package)
SHARE_DIR = "/usr/share/tact"
if os.path.isdir(SHARE_DIR) and SHARE_DIR not in sys.path:
    sys.path.append(SHARE_DIR)

# Fallback: look for tact_lib relative to this script when run in-tree
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
if PARENT_DIR not in sys.path and os.path.isdir(os.path.join(PARENT_DIR, "tact_lib")):
    sys.path.insert(0, PARENT_DIR)
# Another fallback: /opt/tact (AUR package tact_lib might live there)
for p in ["/opt/tact", "/opt/tact/app"]:
    if os.path.isdir(os.path.join(p, "tact_lib")) and p not in sys.path:
        sys.path.append(p)

# Legacy fallback: /opt/touchdesigner
for p in ["/opt/touchdesigner", "/opt/touchdesigner/app"]:
    if os.path.isdir(os.path.join(p, "tact_lib")) and p not in sys.path:
        sys.path.append(p)

from tact_lib.cleanup import run_uninstall
from tact_lib.cli import parse_args
from tact_lib.diagnose import run_diagnose
from tact_lib.install import run_install
from tact_lib.pip import run_pip
from tact_lib.update import run_update
from tact_lib.utils import error, print_banner, setup_logging


def main():
    args = parse_args()

    # Auto-detect headless mode if no graphical session
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if not has_display and not args.headless:
        args.headless = True
        args.non_interactive = True

    # Auto-enable debug from environment
    if os.environ.get("DEBUG") in ("true", "1", "yes"):
        args.debug = True

    setup_logging(args.debug)

    if args.diagnose:
        run_diagnose()
        return

    if args.version:
        from tact_lib import __version__

        print(f"tact {__version__}")
        return

    # Handle --patch-toe standalone mode
    if args.patch_toe:
        run_patch_toe(args.patch_toe)
        return

    # Handle --pip standalone mode
    if args.pip_args is not None:
        sys.exit(run_pip(args.pip_args))

    # Main menu loop
    while True:
        # Show interactive menu if no action specified
        if args.action is None:
            if args.non_interactive:
                args.action = "install"
            else:
                _show_menu(args)

        match args.action:
            case "install":
                run_install(args)
                args.action = None
            case "update":
                run_update(args)
                args.action = None
            case "uninstall":
                did_uninstall = run_uninstall(args)
                args.action = None
                if not did_uninstall:
                    continue  # Back pressed, skip pause
            case _:
                break

        # Pause before returning to menu so user can read output
        if args.action is None and not args.non_interactive:
            try:
                input("\nPress Enter to return to menu... ")
            except (EOFError, KeyboardInterrupt):
                print()
                break


def _show_menu(args):
    """Show interactive main menu."""
    import sys
    import termios
    import tty

    from tact_lib.distro import detect_distro
    from tact_lib.utils import Colors, print_banner, print_hr

    if sys.stdout.isatty():
        print("\033[2J\033[H", end="")  # clear screen
    print_banner("2.0-dev")

    OS_NAME = "Unknown"
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    OS_NAME = line.split("=", 1)[1].strip().strip('"')
                    break
    except OSError:
        pass

    ARCH_NAME = os.uname().machine
    PKG_MANAGER = detect_distro().package_manager

    compat_ok = ARCH_NAME == "x86_64" and PKG_MANAGER != "unknown"

    print(f"\n{Colors.bold}{Colors.dim}Environment check{Colors.nc}\n")

    print(f" {Colors.dim}╔═══════════════════════════════════╗{Colors.nc}")
    sysname = f"System: {OS_NAME} / {ARCH_NAME}"
    print(f" {Colors.dim}║{Colors.nc} {sysname:<33} {Colors.dim}║{Colors.nc}")
    print(f" {Colors.dim}╚═══════════════════════════════════╝{Colors.nc}")

    if compat_ok:
        print(f"  {Colors.white}▸ Your Linux is supported{Colors.nc}\n")
    else:
        print(f"  {Colors.gray}▸ Your Linux is not supported{Colors.nc}\n")

    print(f"{Colors.bold}{Colors.white}WHAT YOU GET:{Colors.nc}\n")

    def _item(label, text):
        print(
            f"  {Colors.dim}[{Colors.nc}{Colors.white}{Colors.bold}{label:<7}{Colors.nc}{Colors.dim}]{Colors.nc}  {text}"
        )

    runner_label = "Tact Wine 11 (custom)" if getattr(args, 'runner', 'tact') == 'tact' else "Soda Wine 9.0-1 (standalone)"
    _item("Runner", runner_label)
    _item("GPU", "Vulkan acceleration (3D graphics)")
    _item("Font", "Microsoft core fonts (corefonts)")
    _item("App", "Latest TouchDesigner version installation")

    print(f"\n{Colors.white}OPTIONS :{Colors.nc}\n")

    options = [
        (
            "Install",
            "Install and run TouchDesigner on Linux — idempotent, safe to re-run",
        ),
        ("Update", "Update launcher, Wine components, UI fixes and icons"),
        (
            "Uninstall",
            "Remove selected versions or everything (prefix, runner, launcher)",
        ),
        ("Exit", "Quit without making changes"),
    ]
    actions = ["install", "update", "uninstall", None]

    # Fall back to simple input when stdin is not a TTY
    if not sys.stdin.isatty():
        print(f"  1. Install")
        print(
            f"{Colors.accent}     Install and run TouchDesigner on Linux — idempotent, safe to re-run{Colors.nc}"
        )
        print()
        print(f"  2. Update")
        print(
            f"{Colors.accent}     Update launcher, Wine components, UI fixes and icons{Colors.nc}"
        )
        print()
        print(f"  3. Uninstall")
        print(f"{Colors.accent}     Remove selected versions or everything{Colors.nc}")
        print()
        print(f"  0. Exit")
        print(
            f"{Colors.accent}     Quit without making changes.{Colors.nc}\n"
        )
        try:
            choice = input("  Select option [1]: ").strip() or "1"
        except (EOFError, KeyboardInterrupt):
            print()
            choice = "0"
        match choice:
            case "1":
                args.action = "install"
            case "2":
                args.action = "update"
            case "3":
                args.action = "uninstall"
            case "0":
                print("Exiting...")
                sys.exit(0)
            case _:
                args.action = "install"
        return

    cursor = 0

    def _draw_menu():
        lines = []
        for i, (title, desc) in enumerate(options):
            num = str(i + 1) if i < 3 else "0"
            marker = "▶" if i == cursor else " "
            lines.append(f"  {marker}  {num}. {title}")
            if i == cursor:
                lines.append(f"{Colors.accent}     {desc}{Colors.nc}")
            else:
                lines.append(f"{Colors.accent}     {desc}{Colors.nc}")
            if i < len(options) - 1:
                lines.append("")
        return lines

    lines = _draw_menu()
    sys.stdout.write("\033[?25l")  # Hide cursor
    sys.stdout.flush()
    for line in lines:
        print(line)
    print_count = len(lines)

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        new = termios.tcgetattr(fd)
        new[tty.LFLAG] &= ~(termios.ICANON | termios.ECHO)
        new[tty.CC][termios.VMIN] = 1
        new[tty.CC][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSADRAIN, new)

        while True:
            try:
                key = sys.stdin.read(1)
            except (EOFError, KeyboardInterrupt):
                key = "\x03"

            if key == "\x03":  # Ctrl+C
                print()
                print("Exiting...")
                sys.exit(0)

            if key == "\x1b":
                seq = ""
                try:
                    seq = sys.stdin.read(2)
                except (EOFError, OSError):
                    pass
                if seq == "[A":  # Up
                    cursor = (cursor - 1) % len(options)
                elif seq == "[B":  # Down
                    cursor = (cursor + 1) % len(options)
            elif key in ("\r", "\n"):  # Enter
                if cursor == 3:  # Exit
                    print()
                    print("Exiting...")
                    sys.exit(0)
                args.action = actions[cursor]
                break

            # Redraw
            lines = _draw_menu()
            for _ in range(print_count):
                sys.stdout.write("\033[A")
            for line in lines:
                sys.stdout.write(f"\033[K{line}\n")
            sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.write("\033[?25h")  # Show cursor
        sys.stdout.flush()
    print()


def run_patch_toe(file_path: str) -> None:
    """Apply wine_ui_fixes.tox to a single .toe file (--patch-toe)."""
    from tact_lib.utils import TACT_BASE_DIR, ensure_dir, error, info
    from tact_lib.wine import RUNNER_DIR, WINE_PREFIX

    file_path = os.path.expanduser(file_path)
    if not os.path.isfile(file_path):
        error(f"File not found: {file_path}")
        sys.exit(1)

    runner_bin = os.path.join(RUNNER_DIR, "bin")
    if not os.path.isdir(runner_bin):
        error("TouchDesigner Wine environment not found. Run 'tact install' first.")
        sys.exit(1)

    # Find toeexpand and toecollapse
    drive_c = os.path.join(WINE_PREFIX, "drive_c")
    toeexpand = None
    toecollapse = None
    for root, dirs, files in os.walk(drive_c):
        for f in files:
            if f.lower() == "toeexpand.exe":
                toeexpand = os.path.join(root, f)
            elif f.lower() == "toecollapse.exe":
                toecollapse = os.path.join(root, f)

    if not toeexpand or not toecollapse:
        error("toeexpand/toecollapse not found in Wine prefix.")
        sys.exit(1)

    # Find fix file
    fix_file = os.path.join(TACT_BASE_DIR, "wine_ui_fixes.tox")
    if not os.path.isfile(fix_file):
        from tact_lib.desktop import install_font_fix

        fix_file = install_font_fix()
        if not fix_file:
            error("wine_ui_fixes.tox not found. Cannot patch.")
            sys.exit(1)

    # Run patch using Wine's toeexpand/toecollapse
    import shutil
    import subprocess
    import tempfile

    fix_tmpdir = tempfile.mkdtemp(prefix="tact_fix_")
    try:
        fix_copy = os.path.join(fix_tmpdir, "fix.tox")
        shutil.copy2(fix_file, fix_copy)

        env = os.environ.copy()
        env["WINEPREFIX"] = WINE_PREFIX
        env["PATH"] = f"{runner_bin}:{env.get('PATH', '')}"

        # Expand the fix file to get entries
        subprocess.run(
            [toeexpand, f"z:{fix_copy}"],
            env=env,
            capture_output=True,
            timeout=30,
        )

        fix_entries = []
        toc_file = f"{fix_copy}.toc"
        if os.path.isfile(toc_file):
            with open(toc_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and line != ".build":
                        fix_entries.append(line)

        # Backup original .toe
        backup_dir = os.path.join(TACT_BASE_DIR, "backups")
        ensure_dir(backup_dir)
        unique_name = file_path.replace("/", "_") + ".bak"
        shutil.copy2(file_path, os.path.join(backup_dir, unique_name))

        # Expand target .toe
        wine_path = f"z:{file_path}"
        subprocess.run(
            [toeexpand, wine_path],
            env=env,
            capture_output=True,
            timeout=30,
        )

        toe_dir = f"{file_path}.dir"
        if os.path.isdir(toe_dir):
            # Merge fix
            subprocess.run(
                [toeexpand, f"z:{fix_copy}"],
                env=env,
                capture_output=True,
                timeout=30,
            )
            fix_dir = f"{fix_copy}.dir"
            if os.path.isdir(fix_dir):
                for item in os.listdir(fix_dir):
                    shutil.copytree(
                        os.path.join(fix_dir, item),
                        os.path.join(toe_dir, item),
                        dirs_exist_ok=True,
                    )

            # Add fix entries to .toc
            toe_toc = f"{file_path}.toc"
            with open(toe_toc, "a") as f:
                for entry in fix_entries:
                    f.write(f"{entry}\n")

            # Collapse back
            subprocess.run(
                [toecollapse, wine_path],
                env=env,
                capture_output=True,
                timeout=30,
            )

            # Cleanup expanded files
            if os.path.isdir(toe_dir):
                shutil.rmtree(toe_dir)
            if os.path.isfile(toe_toc):
                os.remove(toe_toc)

            info(f"Patched: {file_path}")
        else:
            error(f"Failed to expand {file_path}")
            sys.exit(1)
    finally:
        if os.path.isdir(fix_tmpdir):
            shutil.rmtree(fix_tmpdir)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        error("Installation cancelled")
        sys.exit(1)
