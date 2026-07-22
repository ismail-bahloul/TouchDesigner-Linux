# How TouchDesigner-Linux works

This page explains the patches and workarounds applied by the installer and launcher. Written for users who want to understand what happens under the hood.

---

## IDS Peak SDK DLLs

**Problem:** TouchDesigner ships four IDS camera SDK DLLs (`ids_peak_ipl.dll`, `ids_peak_afl.dll`, `ids_peak_ifl.dll`, `ids_peak_comfort_c.dll`). These DLLs have a `DllMain` entry point that crashes under Wine, causing TouchDesigner to abort at startup with `status c0000005`.

**Fix:** Zero the `AddressOfEntryPoint` in each DLL's PE header. This tells the Windows loader to skip `DllMain` entirely — the DLL is loaded but not initialized. Since these DLLs are only needed when an IDS camera is actually connected (rare in TD workflows), this has no practical downside.

**Technical detail:** The PE header offset is found at `e_lfanew` (offset `0x3C` in the file). The `AddressOfEntryPoint` is at `e_lfanew + 40`. Zeroing those 4 bytes is the entire patch.

**File:** `tact_lib/patcher.py`

---

## Wine runner choice: Soda → GE-Proton → Tact

**Problem:** Soda 9.0-1 (the historical runner) is unmaintained. GE-Proton works but cannot be patched. Tact is our custom runner.

**Why Soda 9.0 worked (v1.x):**
- Built without Staging → no mimalloc/DWrite crash
- Basic D2D but sufficient for TD versions at the time
- No longer maintained since April 2024

**Why GE-Proton works:**
- Complete D2D implementation (1.3 MB d2d1.dll vs 552 KB for wine-tkg)
- Valve/Proton patches for graphics rendering
- `MIMALLOC_DISABLE_REDIRECT=1` required to prevent mimalloc hang

**Why Tact (our runner):**
- Custom-built Wine 11 binaries (wine-tkg, minimal config)
- PE DLLs (d2d1, dwrite, etc.) sourced from GE-Proton for complete D2D
- KWin patch for KDE compatibility
- Freedom to add TD-specific patches in the future

### Direct2D — the key discovery

In July 2026, a comparative analysis revealed that the difference between vanilla Wine and GE-Proton lies in the **Direct2D** implementation:

| Runner | d2d1.dll size | D2D functions |
|--------|---------------|---------------|
| Soda 9.0 | 449 KB | ~700 |
| Tact (wine-tkg) | 552 KB | ~837 |
| **GE-Proton11** | **1.3 MB** | **~4715** |

GE-Proton has **2.4× more D2D code** than wine-tkg. This is what allows TD to get past the splash screen. The exact patches haven't been isolated yet, but the practical approach is to use GE-Proton's PE DLLs with our custom Unix binaries.

### mimalloc + DWrite hang

On Wine 10+, DWrite uses mimalloc for its allocations, which can cause a hang. The fix is `MIMALLOC_DISABLE_REDIRECT=1`.

### KWin / Mutter workaround

Wine 11 added a Mutter (GNOME) workaround that can block window creation on KDE. A patch conditions this workaround to GNOME environments only. See `runner/patches/0001-winex11.drv-Skip-Mutter-workaround-on-KWin.patch`.

---

## Font fix (wine_ui_fixes.tox)

**Problem:** TouchDesigner's UI font rendering relies on DirectWrite font vectorization that behaves differently under Wine. This causes missing or garbled text in the UI.

**Fix:** A `.tox` component (`wine_ui_fixes.tox`) is injected into `.toe` files at launch time using TD's own `toeexpand` and `toecollapse` utilities. The fix overrides font rendering for the affected UI elements.

**Caveat:** The license activation screen appears before any `.toe` file is loaded, so the fix is not applied on the very first launch. After entering your license and restarting TD, the fix works normally.

**Backups:** Original `.toe` files are backed up before patching, auto-cleaned after 30 days.

---

## LogPixels DPI

**Problem:** Wine defaults to 96 DPI, which makes TD's UI fonts very small on high-resolution displays (common on modern laptops).

**Fix:** The launcher runs `regedit` inside the Wine prefix to set `LogPixels=0x78` (120 DPI) in `HKEY_CURRENT_CONFIG\Software\Fonts`. Applied after wineboot so it persists across launches.

**File:** `apply_font_dpi()` in the launcher script.

---

## Wineboot behavior

**Problem:** Running `wineboot -u` (prefix update) on every launch resets custom registry settings, including LogPixels DPI, font overrides, and potentially other user tweaks.

**Fix:** `wineboot -u` only runs on the very first launch. A flag file (`.td_initialized`) is created in the prefix directory to track this. On subsequent launches, the flag file is detected and wineboot is skipped.

**File:** `ensure_wine_ready()` in the launcher script.

---

## Prefix setup and drive symlinks

**Problem:** The pre-built Wine prefix contains `dosdevices` with many symlinks (`z:` -> `/`, `c:` -> `../drive_c`, `com1` through `com32` -> `/dev/ttyS*`). Copying these with `shutil.copytree` fails because some symlinks already exist at the destination or point to invalid paths.

**Fix:** `dosdevices` is skipped during prefix copy. After copying, only the two essential symlinks are created:

- `dosdevices/c:` -> `../drive_c` (required for Wine to find `C:\windows`, `kernel32.dll`)
- `dosdevices/z:` -> `/` (required for Wine to access the Linux filesystem)

Wine recreates the remaining symlinks (`d:`, `com*`, etc.) on first `wineboot`.

**File:** `ensure_drives()` in the launcher script.

---

## License backup

**Problem:** TouchDesigner stores its license activation in `drive_c/ProgramData/Derivative/ins*.dat`. If wineboot or a prefix update clears `ProgramData`, the user loses their license and must re-activate.

**Fix:** Before wineboot runs, the launcher backups the `Derivative/` folder to `Derivative.bak/`. After wineboot, the backup is restored if the folder was cleared or overwritten.

**File:** `backup_license()` / `restore_license()` in the launcher script.

---

## Diagnostics

`tact diagnose` checks system health in one command:
- OS and kernel version
- GPU(s) and Vulkan support
- Disk space
- Wine prefix status
- Installed TouchDesigner versions (both curl and AUR install paths)
- IDS patch status

This is the first thing to ask when someone reports an issue.

---

## Related

- [Compatibility status](compatibility.md) — what works and what doesn't
- [Troubleshooting](troubleshooting.md) — common issues and fixes
- [Advanced tools](advanced-tools.md) — toeexpand / toecollapse
