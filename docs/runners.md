# Wine Runners Comparison

A technical reference for the Wine runners tested with TouchDesigner under Linux.

## Recommended setup

| Component | Choice | Reason |
|-----------|--------|--------|
| **Runner** | **Tact** (Wine 11 + GE-Proton DLLs) | Custom Wine 11 with KWin patch + complete D2D from GE-Proton |
| **DXVK** | 2.4+ | Vulkan translation for D3D10/11 |
| **Winetricks** | corefonts, vcrun2022 | Missing fonts and MSVC runtimes |
| **IDS patch** | Required | Zero AddressOfEntryPoint in 4 IDS DLLs |
| **Font fix** | `wine_ui_fixes.tox` | Corrects font rendering (auto-injected by launcher) |
| **DPI** | LogPixels auto-detect | Readability on HiDPI displays |
| **KMP_AFFINITY** | `disabled` | Fixes torch import (Intel OpenMP + Wine) |
| **MIMALLOC_DISABLE_REDIRECT** | `=1` | Prevents mimalloc/DWrite hang on Wine 10+ |
| **PYTHONPATH** | Set automatically | Makes pip packages visible to TD |

## Runner comparison

| Runner | Wine version | D2D impl. | TD launches ? | Fonts | Maintained ? |
|--------|-------------|-----------|---------------|-------|-------------|
| **Soda 9.0-1** | Wine 9.0 TkG | Basic (449 KB d2d1) | ✅ | ❌ Missing | ❌ Abandoned |
| **GE-Proton10** | Wine 10 Proton | Full (~1.3 MB d2d1) | ✅ | ⚠️ Deformed | ✅ Active |
| **GE-Proton11** | Wine 11 Proton | Full (~1.3 MB d2d1) | ✅ | ⚠️ Deformed | ✅ Active |
| **Tact (Wine 11 + GE DLLs)** | Wine 11 TkG | Full (GE DLLs) | ✅ | ⚠️ Deformed | ✅ You |
| **Vanilla Wine 11** | Wine 11 Staging | Basic (552 KB d2d1) | ❌ Splash hang | — | ✅ |

## D2D: the real reason Wine 11 blocks

**Key finding (July 2026):** Wine 11's problem with TouchDesigner is not (just) the Mutter workaround — it's the incomplete **Direct2D** implementation.

### d2d1.dll comparison

| Runner | d2d1.dll size | d2d_* functions |
|--------|---------------|-----------------|
| Soda 9.0-1 | 449 KB | ~700 |
| Tact (wine-tkg) | 552 KB | ~837 |
| **GE-Proton11** | **1.3 MB** | **~4715** |
| Windows 10 native | ~1.5 MB | — |

GE-Proton's `d2d1.dll` is **2.4× larger** and has **5.6× more functions** than wine-tkg. This is the difference that allows TD to get past the splash screen and show the main window.

### Where does this difference come from?

GE-Proton is built from the **Valve/Proton source tree** with additional D2D patches not found in:
- Upstream WineHQ
- wine-tkg (even with `valve-exp-bleeding` + Staging)
- Soda 9.0-1

The exact patches haven't been isolated yet, but the result is clear: GE-Proton's PE DLLs (`d2d1.dll`, `dwrite.dll`, etc.) have much more complete implementations than wine-tkg's.

### Practical solution

The **Unix binary (.so)** from wine-tkg is functional. The **PE DLLs (.dll)** just need to be replaced with GE-Proton's. This is the **Tact** runner approach.

## KWin/Mutter patch (Wine 11)

### Context

Wine 11.0 added a Mutter (GNOME) workaround in `dlls/winex11.drv/window.c`:

```c
/* When transitioning a window from IconicState to NormalState and the window is managed,
 * go through WithdrawnState. This is needed because Mutter doesn't unmap windows when
 * making windows iconic/minimized as Mutter needs to support live preview. */
if (data->managed && MAKELONG(old_state, new_state) == MAKELONG(IconicState, NormalState))
{
    WARN("window %p/%lx is iconic, remapping to workaround Mutter issues.\n");
    window_set_wm_state(data, WithdrawnState, FALSE);
    window_set_wm_state(data, NormalState, activate);
    return;
}
```

### Problem

This workaround is applied to **all window managers**, not just Mutter. On **KDE/KWin**, the `Iconic → Withdrawn → Normal` transition can leave the window stuck in `WithdrawnState` — invisible on screen.

### Patch

```c
static BOOL is_mutter_desktop(void)
{
    const char *desktop = getenv("XDG_CURRENT_DESKTOP");
    if (!desktop) return FALSE;
    if (strstr(desktop, "GNOME") || strstr(desktop, "gnome"))
        return TRUE;
    return FALSE;
}
```

The workaround is only applied on GNOME/Mutter. On KDE and other WMs, the direct `Iconic → Normal` transition is used.

### Important note

This patch was written but **could not be tested in isolation** because the D2D issue (see above) blocked TD before window creation even occurred. It is likely correct, but its actual effect has not been confirmed. It remains in the codebase for reference and for users who want to use vanilla Wine 11 with native Windows DLLs.

## Soda 9.0-1

### Status
Default runner for `tact` v1.x. Stable but abandoned by Bottles.

### Advantages
- Works with TD (except timeline fonts)
- Well-tested
- No Steam dependency

### Limitations
- **Wine 9.0** — too old, no more security updates
- **Basic D2D** (449 KB d2d1.dll)
- **Missing fonts** without `wine_ui_fixes.tox`
- Bottles project no longer publishes Soda updates

## GE-Proton10-34

### Status
Works with fixes. Window visible, fonts present but deformed.

### Required configuration
```bash
export WINEPREFIX="/path/to/prefix"
export MIMALLOC_DISABLE_REDIRECT=1  # ← REQUIRED on Wine 10+
export WAYLAND_DISPLAY=""
export KMP_AFFINITY="disabled"
```

### vkd3d setup (GE-Proton11 only)
```bash
VKD3D_SRC="/path/to/GE-Proton11-1/files/lib/vkd3d/x86_64-windows"
SYS32="/path/to/prefix/drive_c/windows/system32"
cp "$VKD3D_SRC/libvkd3d-1.dll" "$SYS32/"
cp "$VKD3D_SRC/libvkd3d-shader-1.dll" "$SYS32/"
cp "$VKD3D_SRC/libvkd3d-utils-1.dll" "$SYS32/"
```

## Tact (Wine 11 + GE-Proton DLLs)

### Concept
Custom runner combining:
- **Unix binaries (.so)** from wine-tkg Wine 11 build (minimal config, no bloat)
- **PE DLLs (.dll)** from GE-Proton (complete D2D/DWrite)
- **KWin patch** for KDE compatibility

### Why this approach?

The Wine `.so` binary from wine-tkg is functional and allows custom patches (KWin, etc.). What's missing is the D2D implementation on the PE (`.dll`) side. By copying GE-Proton's DLLs, we get the best of both worlds.

### Build
```bash
# 1. Build wine-tkg with Tact config
cd runner && bash build.sh all

# 2. Download GE-Proton
curl -L https://github.com/GloriousEggroll/proton-ge-custom/releases/download/GE-Proton11-1/GE-Proton11-1.tar.gz

# 3. Extract DLLs
cp GE-Proton11-1/files/lib/wine/x86_64-windows/*.dll <tact-runner>/lib/wine/x86_64-windows/
cp GE-Proton11-1/files/lib/wine/i386-windows/*.dll <tact-runner>/lib/wine/i386-windows/
```

## Common issues across all runners

### IDs Peak SDK DLLs
All TD 2025+ builds ship `ids_peak_ipl.dll`, `ids_peak_afl.dll`, `ids_peak_ifl.dll`, `ids_peak_comfort_c.dll` which crash under Wine. Fix: zero the `AddressOfEntryPoint` in each DLL's PE header.

See `tact_lib/patcher.py` for implementation.

### mimalloc + DWrite hang (Wine 10+)
TD ships `mimalloc.dll` and `mimalloc-redirect.dll`. On Wine 10+, DWrite's font enumeration triggers a crash in mimalloc's redirected allocations, causing TD to hang on the splash screen.

**Fix:** `MIMALLOC_DISABLE_REDIRECT=1`

Not needed on Wine 9.x (Soda, Wine 9 vanilla) because DWrite's allocation patterns are compatible.

### NVENC (Video Stream Out TOP)
Not available under any Wine runner. Requires `nvEncodeAPI64.dll` from the Windows NVIDIA driver, not redistributable and not provided by Wine.

**Workarounds:**
- **Spout2PW** — TD → Spout → PipeWire → OBS (NVENC on Linux side)
- **NDI** — confirmed working
- **FFmpeg** — pipe frames to native Linux FFmpeg with `-hwaccel nvenc`

### Wayland
Wine's native Wayland support can cause window creation issues. Always set `WAYLAND_DISPLAY=""` to force XWayland.

## Summary

| Feature | Soda 9.0 | GE-P10/11 | Tact |
|---------|----------|-----------|------|
| TD launches | ✅ | ✅ | ✅ |
| D2D implementation | ❌ Basic (449 KB) | ✅ Full (1.3 MB) | ✅ Full (GE DLLs) |
| Font rendering | ❌ Missing without fix | ⚠️ Deformed | ⚠️ Deformed |
| Maintained ? | ❌ Abandoned | ✅ GloriousEggroll | ✅ You |
| Custom patches | ❌ Impossible | ❌ Impossible | ✅ KWin, etc. |
| D3D11/Vulkan | ✅ | ✅ | ✅ |
| NDI | ✅ | ❓ | ❓ |
| NVENC | ❌ | ❌ | ❌ |
| CUDA TOPs | ❌ | ❌ | ❌ |
| Setup complexity | Low | Medium | Low (automated) |

## Ongoing research

The following areas are under active investigation:

### 1. GE-Proton's exact D2D patches
Identify precisely which patches in GE-Proton produce a complete `d2d1.dll` (1.3 MB vs 552 KB). Goal: integrate these patches into the wine-tkg build to remove the GE DLL dependency.

### 2. Engine COMP (IPC bridge)
The Engine COMP sub-process fails to initialize the IPC bridge. Likely cause: named pipe creation under Wine.

### 3. CUDA TOPs
Bridge CUDA Driver API (`nvcuda.dll`) to Linux `libcuda.so`. Long-term project, very high complexity. See `archive/nvcuda_proxy/` for ongoing experiments.
