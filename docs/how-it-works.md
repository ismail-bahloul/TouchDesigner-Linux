# How TouchDesigner-Linux works

This page explains the patches and workarounds applied by the installer and launcher. Written for users who want to understand what happens under the hood.

---

## IDS Peak SDK DLLs

**Problem:** TouchDesigner ships four IDS camera SDK DLLs (`ids_peak_ipl.dll`, `ids_peak_afl.dll`, `ids_peak_ifl.dll`, `ids_peak_comfort_c.dll`). These DLLs have a `DllMain` entry point that crashes under Wine, causing TouchDesigner to abort at startup with `status c0000005`.

**Fix:** Zero the `AddressOfEntryPoint` in each DLL's PE header. This tells the Windows loader to skip `DllMain` entirely — the DLL is loaded but not initialized. Since these DLLs are only needed when an IDS camera is actually connected (rare in TD workflows), this has no practical downside.

**Technical detail:** The PE header offset is found at `e_lfanew` (offset `0x3C` in the file). The `AddressOfEntryPoint` is at `e_lfanew + 40`. Zeroing those 4 bytes is the entire patch.

**File:** `td_lib/patcher.py`

---

## Wine runner choice: Soda over Proton

**Problem:** Most users trying TD on Linux reach for Proton (via Bottles or Steam) because it's the most well-known Wine distribution. Proton works for many Windows apps, but TD has specific needs that Proton doesn't handle well.

**Why Soda Wine:** Soda is a Wine distribution maintained by the Bottles project, focused on running Windows **applications** (not games). It's more conservative, more stable, and doesn't have the gaming-oriented patches that can cause regressions with TD.

**Why not Proton 10:** Proton 10 ships a new `DWrite.dll` (DirectWrite) that's incompatible with TD's bundled `mimalloc.dll`. This causes a hang during font enumeration at project load. The workaround (`MIMALLOC_DISABLE_REDIRECT=1`) exists but Soda avoids the issue entirely.

**Why not Wine-GE:** Wine-GE is not yet supported as an optional runner, but it's on the roadmap. It may offer better GPU performance once properly integrated.

---

## Font fix (wine_ui_fixes.tox)

**Problem:** TouchDesigner's UI font rendering relies on DirectWrite font vectorization that behaves differently under Wine. This causes missing or garbled text in the UI.

**Fix:** A `.tox` component (`wine_ui_fixes.tox`) is injected into `.toe` files at launch time using TD's own `toeexpand` and `toecollapse` utilities. The fix overrides font rendering for the affected UI elements.

**Version-aware re-patching:** The launcher compares a content fingerprint of the fix injected in a `.toe` with the currently shipped `wine_ui_fixes.tox`. If they differ (e.g. after a new fix release), the old fix is replaced — so upgrading the fix actually reaches projects that were already patched with an older version.

**Caveat:** The license activation screen appears before any `.toe` file is loaded, so the fix is not applied on the very first launch. After entering your license and restarting TD, the fix works normally.

**Backups:** Original `.toe` files are backed up before patching, auto-cleaned after 30 days.

---

## Lucida Console (default mono font)

**Problem:** TouchDesigner uses **Lucida Console** as its default mono font (parameter value fields, OP name fields, DAT tables, Textport). Lucida Console ships with Windows but is **not** part of the winetricks `corefonts` set, so a prefix that only installs `corefonts` cannot resolve it. TD then reports at startup:

```
Error Loading Default Mono Font. Failed to load font file. Failed to load . Substituted with Verdana.
```

and the mono text simply doesn't render. This is independent of the `wine_ui_fixes.tox` pass above (which only changes how Text TOPs are rasterized — bitmap/polygon vs. scalable — it does not load the default mono font), so the error can persist even after the `.tox` fix is applied.

**Fix:** Install a mono font whose family name is `Lucida Console` as `lucon.ttf` into the prefix and register it:

```
cp lucon.ttf "$WINEPREFIX/drive_c/windows/Fonts/"
wine64 reg add "HKLM\Software\Microsoft\Windows NT\CurrentVersion\Fonts" \
  /v "Lucida Console (TrueType)" /d "lucon.ttf" /f
```

The bundled `Assets/lucon.ttf` is generated from DejaVu Sans Mono with its `name` table rewritten (family `Lucida Console`), so it can be distributed freely — no proprietary Microsoft font is shipped. The install and `--update` flows both run this (`install_lucida_console()` in `td_lib/wine.py`). A running `wineserver` is killed first and the result is verified with `reg query`, because `reg add` can silently lose the entry if a stale wineserver flushes its state afterwards.

---

## LogPixels DPI

**Problem:** Wine defaults to 96 DPI, which makes TD's UI fonts very small on high-resolution displays (common on modern laptops). Changing the DPI through `winecfg` or `winetricks` has **no effect** — TouchDesigner ignores the DPI Wine reports and only reads the `LogPixels` registry value at startup, so the override has to be written into the prefix directly.

**Fix:** On first launch the launcher detects the display's logical DPI (`Xft.dpi` via `xrdb`, falling back to `xdpyinfo`) and writes the matching value (`96`, `120`, `144` or `192`) to `LogPixels` in `HKEY_CURRENT_CONFIG\Software\Fonts`. It runs after `wineboot`, which would otherwise reset the value, and is skipped on later launches so the prefix keeps it.

**Override:** `td-install --dpi 120` records a persistent value (survives launches and updates), or `TD_DPI=120 touchdesigner` for a one-off launch. The persistent choice is stored in `prefix/.td_dpi`, which the launcher reads before falling back to auto-detection.

**File:** `apply_font_dpi()` (AUR launcher) and the `UI scaling (LogPixels)` block in the generated shell launcher (`td_lib/launcher.py`).

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

A full uninstall (`td-install --uninstall` → *Uninstall EVERYTHING*) removes the whole prefix — including `ins*.dat` — so the license activation is lost by design. The uninstaller prints a warning before deleting it (`_warn_license_loss()` in `td_lib/cleanup.py`), and removing a single version does **not** touch the license.

---

## Diagnostics

`td-install --diagnose` checks system health in one command:
- OS and kernel version
- GPU(s) and Vulkan support
- Disk space
- Wine prefix status
- Installed TouchDesigner versions (both curl and AUR install paths)
- IDS patch status

This is the first thing to ask when someone reports an issue.

---

## CodeMeter runtime (dongles & network licenses)

**Problem:** TouchDesigner's licensing runs on Wibu-Systems CodeMeter. The TD installer installs the CodeMeter Runtime into the prefix ("Install Runtime for Dongle Licensing"), but Wine does not auto-start Windows services, so `CodeMeter.exe` never runs, leaving dongle and network-shared licenses unreachable.

**Fix:** A `td-install --codemeter` command detects the runtime, starts it, and manages the client's Server Search List (`cmu32 --add-server`/`cmu.exe`, with a registry fallback). The launcher auto-starts `CodeMeter.exe` if installed.

**Current limitation (tested 2026-08):** the CodeMeter service itself does not start under the project's Wine runner: Wibu's AxProtector-protected `cpsrt.dll` fails to map (`c000007b`), so the network client path under Wine is blocked for now. The server side (native Linux / Docker / other hosts, UDP/TCP 22350) works and is validated; the tooling remains useful for detection and configuration. See [`docs/codemeter.md`](codemeter.md) for the full picture.

**File:** `td_lib/codemeter.py`

---

## Related

- [Compatibility status](compatibility.md) — what works and what doesn't
- [Troubleshooting](troubleshooting.md) — common issues and fixes
- [Advanced tools](advanced-tools.md) — toeexpand / toecollapse
