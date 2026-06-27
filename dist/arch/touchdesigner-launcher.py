#!/usr/bin/env python3
"""TouchDesigner launcher for AUR package - handles prefix setup + .toe patching."""
import os
import shutil
import subprocess
import sys
import tempfile

PREFIX = "/opt/touchdesigner"
WINE = f"{PREFIX}/wine/bin/wine64"
TD_DIR = f"{PREFIX}/td"
DXVK_DIR = f"{PREFIX}/dxvk"
WINETRICKS = f"{PREFIX}/winetricks"
DATA_DIR = f"{PREFIX}/data"
FIX_FILE = f"{PREFIX}/wine_ui_fixes.tox"
BACKUP_DIR = f"{PREFIX}/backups"
WINE_PREFIX = os.path.expanduser("~/.local/share/touchdesigner-linux/prefix")

os.environ["WINEDLLOVERRIDES"] = "mscoree="
os.environ["WINEDEBUG"] = "fixme-all,warn-all"
os.environ["PATH"] = f"{PREFIX}/wine/bin:{os.environ.get('PATH', '')}"
os.environ["LD_LIBRARY_PATH"] = f"{PREFIX}/wine/lib:{PREFIX}/wine/lib64:{os.environ.get('LD_LIBRARY_PATH', '')}"
os.environ["WINEPREFIX"] = WINE_PREFIX


def setup_prefix():
    """Copy pre-made prefix on first run."""
    system_reg = f"{WINE_PREFIX}/drive_c/windows/system.reg"
    default_prefix = f"{PREFIX}/default-prefix"
    if not os.path.isfile(system_reg) and os.path.isdir(default_prefix):
        print("TouchDesigner - Setting up...")
        os.makedirs(os.path.dirname(WINE_PREFIX), exist_ok=True)
        for item in os.listdir(default_prefix):
            src = os.path.join(default_prefix, item)
            dst = os.path.join(WINE_PREFIX, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)


def copy_programdata():
    """Copy ProgramData if present."""
    if os.path.isdir(f"{DATA_DIR}/ProgramData"):
        os.makedirs(f"{WINE_PREFIX}/drive_c/ProgramData", exist_ok=True)
        for item in os.listdir(f"{DATA_DIR}/ProgramData"):
            src = os.path.join(f"{DATA_DIR}/ProgramData", item)
            dst = os.path.join(f"{WINE_PREFIX}/drive_c/ProgramData", item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)


def patch_toe(toe_path):
    """Patch a .toe file with wine_ui_fixes.tox."""
    toe_expand = f"{TD_DIR}/bin/toeexpand.exe"
    toe_collapse = f"{TD_DIR}/bin/toecollapse.exe"

    if not all(os.path.exists(f) for f in [toe_expand, toe_collapse, FIX_FILE]):
        return

    toe_dir = toe_path + ".dir"
    toe_toc = toe_path + ".toc"

    shutil.rmtree(toe_dir, True)
    shutil.rmtree(toe_toc, True)

    env = os.environ.copy()
    subprocess.run([WINE, toe_expand, "z:" + toe_path], capture_output=True, timeout=30, env=env)

    needs_patch = not os.path.isdir(os.path.join(toe_dir, "wine_ui_fixes"))
    shutil.rmtree(toe_dir, True)
    shutil.rmtree(toe_toc, True)

    if not needs_patch:
        return

    subprocess.run([WINE, toe_expand, "z:" + toe_path], capture_output=True, timeout=30, env=env)

    if os.path.isdir(toe_dir):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        shutil.copy2(toe_path, os.path.join(BACKUP_DIR, os.path.basename(toe_path) + ".bak"))

        tmp = tempfile.mkdtemp(prefix="td_patch_")
        shutil.copy2(FIX_FILE, os.path.join(tmp, "fix.tox"))
        subprocess.run([WINE, toe_expand, "z:" + os.path.join(tmp, "fix.tox")], capture_output=True, timeout=30, env=env)

        fix_dir = os.path.join(tmp, "fix.tox.dir")
        if os.path.isdir(fix_dir):
            for f in os.listdir(fix_dir):
                src_path = os.path.join(fix_dir, f)
                dst_path = os.path.join(toe_dir, f)
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(src_path, dst_path)

        shutil.rmtree(tmp, True)
        subprocess.run([WINE, toe_collapse, "z:" + toe_path], capture_output=True, timeout=30, env=env)
        shutil.rmtree(toe_dir, True)
        shutil.rmtree(toe_toc, True)


def find_td_exe():
    """Find TouchDesigner.exe in the install dir."""
    for path in [f"{TD_DIR}/bin/TouchDesigner.exe", f"{TD_DIR}/TouchDesigner.exe"]:
        if os.path.isfile(path):
            return path
    for root, dirs, files in os.walk(TD_DIR):
        for f in files:
            if f.lower() == "touchdesigner.exe":
                return os.path.join(root, f)
    return None


def main():
    setup_prefix()
    copy_programdata()

    # Patch .toe argument if provided
    input_path = sys.argv[1] if len(sys.argv) > 1 else None
    if input_path and os.path.isfile(input_path) and input_path.endswith(".toe"):
        patch_toe(input_path)

    # Launch TD
    td_exe = find_td_exe()
    if not td_exe:
        print("Error: TouchDesigner not found")
        sys.exit(1)

    args = [WINE, td_exe]
    if input_path:
        args.append("z:" + input_path)

    os.execve(WINE, args, os.environ)


if __name__ == "__main__":
    main()
