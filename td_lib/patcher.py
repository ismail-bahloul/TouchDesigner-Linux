"""IDS Peak SDK DLL patching for Wine compatibility."""

import os
import shutil
import struct

from .utils import info, success, warning
from .wine import WINE_PREFIX

IDS_DLLS = [
    "ids_peak_ipl.dll",
    "ids_peak_afl.dll",
    "ids_peak_ifl.dll",
    "ids_peak_comfort_c.dll",
]


def patch_ids_dlls() -> None:
    """Zero AddressOfEntryPoint in IDS Peak DLLs to prevent DllMain crash on Wine."""
    # Search all TouchDesigner directories (versioned and non-versioned)
    program_files = os.path.join(WINE_PREFIX, "drive_c", "Program Files")

    found_any = False
    patched = 0
    skipped = 0

    for entry in os.listdir(program_files):
        if not entry.startswith("TouchDesigner"):
            continue
        td_bin = os.path.join(program_files, entry, "bin")
        if not os.path.isdir(td_bin):
            continue
        found_any = True

        for dll_name in IDS_DLLS:
            dll_path = os.path.join(td_bin, dll_name)
            if not os.path.isfile(dll_path):
                continue

            try:
                with open(dll_path, "rb") as f:
                    data = bytearray(f.read())

                e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
                ep_offset = e_lfanew + 4 + 20 + 16
                ep = struct.unpack_from("<I", data, ep_offset)[0]

                if ep == 0:
                    skipped += 1
                    continue

                backup_path = dll_path + ".bak"
                if not os.path.exists(backup_path):
                    shutil.copy2(dll_path, backup_path)

                struct.pack_into("<I", data, ep_offset, 0)
                with open(dll_path, "wb") as f:
                    f.write(data)

                patched += 1

            except (IOError, struct.error, IndexError) as e:
                warning(f"Could not patch {dll_name}: {e}")
                continue

    if not found_any:
        info("No TouchDesigner installation found, skipping IDS patch")
        return

    if patched > 0:
        success(f"Patched {patched} IDS Peak SDK DLL(s) for Wine compatibility")
    if skipped > 0:
        info(f"{skipped} IDS DLL(s) already patched")


def check_ids_patch_status() -> dict[str, bool]:
    """Return a dict mapping DLL names to their patch status."""
    program_files = os.path.join(WINE_PREFIX, "drive_c", "Program Files")
    status: dict[str, bool] = {}

    for entry in os.listdir(program_files):
        if not entry.startswith("TouchDesigner"):
            continue
        td_bin = os.path.join(program_files, entry, "bin")
        if not os.path.isdir(td_bin):
            continue

        for dll_name in IDS_DLLS:
            if dll_name in status:
                continue  # Already checked in another version
            dll_path = os.path.join(td_bin, dll_name)
            if not os.path.isfile(dll_path):
                continue

            try:
                with open(dll_path, "rb") as f:
                    data = bytearray(f.read())
                e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
                ep_offset = e_lfanew + 4 + 20 + 16
                ep = struct.unpack_from("<I", data, ep_offset)[0]
                status[dll_name] = ep == 0
            except (IOError, struct.error, IndexError):
                status[dll_name] = False

    return status
