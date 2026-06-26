"""Patch existing .toe files in the Wine prefix with wine_ui_fixes."""

import os
import shutil
import subprocess
import tempfile

from .utils import TD_BASE_DIR, info, safe_rm
from .wine import RUNNER_DIR, WINE_PREFIX


def patch_toe_projects_in_drive() -> None:
    """Patch all .toe files in drive_c with wine_ui_fixes.tox during install/update."""
    drive_c = os.path.join(WINE_PREFIX, "drive_c")
    if not os.path.isdir(drive_c):
        return

    # Find toeexpand/toecollapse
    toeexpand = None
    toecollapse = None
    for root, dirs, files in os.walk(drive_c):
        for f in files:
            if f.lower() == "toeexpand.exe":
                toeexpand = os.path.join(root, f)
            elif f.lower() == "toecollapse.exe":
                toecollapse = os.path.join(root, f)

    if not toeexpand or not toecollapse:
        return

    # Find fix file
    fix_file = os.path.join(TD_BASE_DIR, "wine_ui_fixes.tox")
    if not os.path.isfile(fix_file):
        return

    # Collect .toe files
    toe_files = []
    for root, dirs, files in os.walk(drive_c):
        for f in files:
            if f.lower().endswith(".toe"):
                toe_files.append(os.path.join(root, f))

    if not toe_files:
        return

    info(f"Patching {len(toe_files)} .toe file(s) with UI fixes...")

    # Build Wine environment
    wine64 = os.path.join(RUNNER_DIR, "bin", "wine64")
    env = os.environ.copy()
    env["WINEPREFIX"] = WINE_PREFIX
    env["PATH"] = f"{os.path.join(RUNNER_DIR, 'bin')}:{env.get('PATH', '')}"

    def _wine_run(args: list[str], **kwargs):
        """Run a command via wine64."""
        return subprocess.run([wine64] + args, env=env, capture_output=True, **kwargs)

    # Read fix entries
    fix_entries = []
    fix_tmp = tempfile.mkdtemp(prefix="td_patch_")
    try:
        fix_copy = os.path.join(fix_tmp, "fix.tox")
        shutil.copy2(fix_file, fix_copy)

        _wine_run([toeexpand, f"z:{fix_copy}"], timeout=30)

        toc = f"{fix_copy}.toc"
        if os.path.isfile(toc):
            with open(toc) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and line != ".build":
                        fix_entries.append(line)

        patched = 0
        skipped = 0

        for toe_path in toe_files:
            try:
                toe_name = os.path.basename(toe_path)
                toe_dir = f"{toe_path}.dir"
                toe_toc = f"{toe_path}.toc"

                # Detect TD version from parent directory
                version_label = ""
                parent_dirs = os.path.dirname(toe_path).split(os.sep)
                for i, d in enumerate(parent_dirs):
                    if "TouchDesigner" in d:
                        version_label = f" [{d}]"
                        break

                # Show which file we're checking
                info(f"{version_label}  Checking: {toe_name}")

                # Check if already patched
                shutil.rmtree(toe_dir, ignore_errors=True)
                safe_rm(toe_toc)

                _wine_run([toeexpand, f"z:{toe_path}"], timeout=60)

                needs_patch = True
                if os.path.isdir(toe_dir):
                    if os.path.isdir(os.path.join(toe_dir, "wine_ui_fixes")):
                        needs_patch = False
                    shutil.rmtree(toe_dir, ignore_errors=True)
                safe_rm(toe_toc)

                if not needs_patch:
                    skipped += 1
                    continue

                info(f"  Patching: {toe_name}")

                # Backup
                backup_dir = os.path.join(TD_BASE_DIR, "backups")
                os.makedirs(backup_dir, exist_ok=True)
                unique_name = toe_path.replace("/", "_") + ".bak"
                shutil.copy2(toe_path, os.path.join(backup_dir, unique_name))

                # Expand target
                _wine_run([toeexpand, f"z:{toe_path}"], timeout=60)

                if os.path.isdir(toe_dir):
                    # Merge fix
                    _wine_run([toeexpand, f"z:{fix_copy}"], timeout=30)

                    fix_dir = f"{fix_copy}.dir"
                    if os.path.isdir(fix_dir):
                        for item in os.listdir(fix_dir):
                            src = os.path.join(fix_dir, item)
                            dst = os.path.join(toe_dir, item)
                            if os.path.isdir(src):
                                shutil.copytree(src, dst, dirs_exist_ok=True)
                            else:
                                shutil.copy2(src, dst)

                    # Add entries to .toc
                    with open(toe_toc, "a") as f:
                        for entry in fix_entries:
                            f.write(f"{entry}\n")

                    # Collapse back
                    _wine_run([toecollapse, f"z:{toe_path}"], timeout=60)

                    # Cleanup expanded files
                    shutil.rmtree(toe_dir, ignore_errors=True)
                    safe_rm(toe_toc)

                    patched += 1
                else:
                    skipped += 1

            except (subprocess.TimeoutExpired, OSError):
                skipped += 1

        if patched > 0:
            info(f"Patched {patched} .toe file(s)")
        if skipped > 0:
            info(f"{skipped} .toe file(s) already patched or skipped")

    finally:
        shutil.rmtree(fix_tmp, ignore_errors=True)
