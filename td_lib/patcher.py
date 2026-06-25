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
    td_bin = os.path.join(
        WINE_PREFIX, "drive_c", "Program Files", "TouchDesigner", "bin"
    )

    if not os.path.isdir(td_bin):
        info("TouchDesigner bin directory not found, skipping IDS patch")
        return

    patched = 0
    skipped = 0

    for dll_name in IDS_DLLS:
        dll_path = os.path.join(td_bin, dll_name)
        if not os.path.isfile(dll_path):
            continue

        try:
            with open(dll_path, "rb") as f:
                data = bytearray(f.read())

            # PE header: e_lfanew at offset 0x3C (4 bytes)
            e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
            # AddressOfEntryPoint = e_lfanew + 4 (PE sig) + 20 (COFF hdr) + 16 (into OptHdr)
            ep_offset = e_lfanew + 4 + 20 + 16
            ep = struct.unpack_from("<I", data, ep_offset)[0]

            if ep == 0:
                skipped += 1
                continue

            # Create backup
            backup_path = dll_path + ".bak"
            if not os.path.exists(backup_path):
                shutil.copy2(dll_path, backup_path)

            # Zero the entry point
            struct.pack_into("<I", data, ep_offset, 0)
            with open(dll_path, "wb") as f:
                f.write(data)

            patched += 1

        except (IOError, struct.error, IndexError) as e:
            warning(f"Could not patch {dll_name}: {e}")
            continue

    if patched > 0:
        success(f"Patched {patched} IDS Peak SDK DLL(s) for Wine compatibility")
    if skipped > 0:
        info(f"{skipped} IDS DLL(s) already patched")


def check_ids_patch_status() -> dict[str, bool]:
    """Return a dict mapping DLL names to their patch status."""
    td_bin = os.path.join(
        WINE_PREFIX, "drive_c", "Program Files", "TouchDesigner", "bin"
    )
    status: dict[str, bool] = {}

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
            status[dll_name] = ep == 0
        except (IOError, struct.error, IndexError):
            status[dll_name] = False

    return status
