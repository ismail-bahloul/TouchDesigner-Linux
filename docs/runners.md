# Wine Runners Comparison

A technical reference for the Wine runners tested with TouchDesigner under Linux.

## Recommended setup (the "secret recipe")

Based on extensive testing and source code analysis, this is the optimal configuration:

| Component | Choice | Reason |
|-----------|--------|--------|
| **Runner** | **Soda 9.0-1** (Wine TkG, Valve 9.0 based) | No Wine Staging patches = no DWrite/mimalloc/Mutter bugs |
| **DXVK** | 2.4+ | Vulkan translation for D3D10/11 |
| **Winetricks** | corefonts, vcrun2019, vcrun2022 | Missing fonts and MSVC runtimes |
| **IDS patch** | Required | Zero AddressOfEntryPoint in 4 IDS DLLs |
| **Font fix** | `wine_ui_fixes.tox` | Corrects font rendering (auto-injected by launcher) |
| **DPI** | LogPixels auto-detect | Readability on HiDPI displays |
| **KMP_AFFINITY** | `disabled` | Fixes torch import (Intel OpenMP + Wine) |
| **PYTHONPATH** | Set automatically | Makes pip packages visible to TD |

This is exactly what `td-install` sets up, and what `launch-touchdesigner.sh` configures at runtime.

## Why Wine 9 works and Wine 10+ doesn't (short version)

| Version | Works? | Why |
|---------|--------|-----|
| **Wine 9.x** (Soda, TkG, vanilla) | ✅ | No Mutter workaround, stable DWrite |
| **Wine 10.x** (GE-Proton10, Proton) | ⚠️ | Window OK but fonts deformed → `wine_ui_fixes.tox` helps |
| **Wine 11.x** (vanilla, GE-P11, Proton) | ❌ | Mutter workaround added in Valve fork → window invisible on KWin |

The key: Soda 9.0 is built with `_use_staging="false"` (no Wine Staging patches). Staging introduced the DWrite rewrite in Wine 10, and Valve added the Mutter workaround in Wine 11. Both are incompatible with TouchDesigner on KDE/Wayland.


## Soda build recipe (the "secret sauce")

Soda 9.0-1 is built using **wine-tkg** (Frogging-Family) with this configuration:

```bash
_LOCAL_PRESET="valve-exp-bleeding"
_use_staging="false"        # ← KEY: no Staging patches
_use_GE_patches="true"
_proton_rawinput="true"
_proton_fs_hack="true"
_use_fsync="true"
_use_plasma_systray_fix="true"  # KDE fix
```

- **Source:** ValveSoftware/wine (tag `experimental_9.0`), not WineHQ
- **Staging:** Explicitly disabled (`_use_staging="false"`)
- **GE/Proton patches:** Active but compatible (`_use_GE_patches="true"`)
- **Result:** A Wine 9.0 build without the problematic Staging patches that break TD on Wine 10+

This is why Soda works perfectly while GE-Proton (which enables Staging) has issues on Wine 10/11.

## Wine 9.x: Soda / Staging / TkG
## GE-Proton10-34 (works with fixes)

### Status
Main window opens and renders. **Fonts are present** (unlike Soda without fix, where fonts are missing entirely), but slightly deformed. The `wine_ui_fixes.tox` should correct them. Needs the same fixes as Soda: IDS DLL patch, corefonts, vcrun2019.

Note: GE-Proton10's default font rendering is actually **better** than Soda without the `.tox` fix — fonts are visible, just not perfectly shaped.

Tested with GE-Proton10-34. The `MIMALLOC_DISABLE_REDIRECT=1` fix is required (Wine 10+ DWrite incompatibility).

### Requirements
- GE-Proton10-34 extracted to `~/.local/share/Steam/compatibilitytools.d/`
- A Wine prefix with:
  - **DXVK** installed (auto by winetricks or Proton setup)
  - **vkd3d-proton** bundled with GE-Proton10
  - **corefonts** + **vcrun2019** installed via winetricks
  - **IDS DLLs** patched (AddressOfEntryPoint zeroed)

### Launch command
```bash
export WINEPREFIX="/path/to/prefix"
export MIMALLOC_DISABLE_REDIRECT=1
export WAYLAND_DISPLAY=""
export __NV_PRIME_RENDER_OFFLOAD=1   # if hybrid GPU
export __GLX_VENDOR_LIBRARY_NAME=nvidia
export DRI_PRIME=1
export KMP_AFFINITY="disabled"

/path/to/GE-Proton10-34/files/bin/wine /path/to/TouchDesigner.exe
```

### Known issues
- **Splash only** — main window never appears
- **NVENC** — not available (missing `nvEncodeAPI64.dll`)
- **CUDA TOPs** — not available (NVIDIA CUDA under Wine limitation)

## GE-Proton11-1

### Status
Same as GE-Proton10-34: works with fixes. Main window opens, fonts render (slightly deformed). Requires vkd3d DLLs copied manually to the prefix.

### vkd3d setup
### Differences from GE-Proton10-34
- vkd3d DLLs not deployed to prefix automatically when using `files/bin/wine` directly
- Requires copying `libvkd3d-*.dll` from `files/lib/vkd3d/x86_64-windows/` to `drive_c/windows/system32/`
- Otherwise identical setup

### vkd3d setup
```bash
VKD3D_SRC="/path/to/GE-Proton11-1/files/lib/vkd3d/x86_64-windows"
SYS32="/path/to/prefix/drive_c/windows/system32"

cp "$VKD3D_SRC/libvkd3d-1.dll" "$SYS32/"
cp "$VKD3D_SRC/libvkd3d-shader-1.dll" "$SYS32/"
cp "$VKD3D_SRC/libvkd3d-utils-1.dll" "$SYS32/"
```

## UMU-Proton / faugus-launcher

### Status
Not working reliably. TD either hangs on splash screen or crashes during initialization.

### Issues
1. **pressure-vessel sandbox** — blocks environment variables like `MIMALLOC_DISABLE_REDIRECT`
2. **UMU-Proton builds** — automated builds lack GE patches needed for TD compatibility
3. **Steam Runtime dependency** — heavy (~800 MB), complex setup
4. **prefix version conflicts** — UMU-Proton may fail when upgrading prefixes from other runners

### Workaround attempt (partial success)
- Using `UMU_USE_STEAM=0` bypasses sandbox but breaks DXVK deployment
- Using `files/bin/wine` directly with UMU-Proton gives same libvkd3d errors as GE-Proton11

**Recommendation:** Use GE-Proton directly instead of UMU-Proton wrappers.

## Proton-CachyOS

### Status
Splash only — same as other Proton builds. Main window never opens.

### Differences from GE-Proton
- Based on Wine 11.0 Staging (same base as GE-Proton11)
- vkd3d-proton bundled and deployed automatically
- CachyOS-specific compiler optimizations
- Compatible with the same prefix as GE-Proton10/11

### Launch command
Same as GE-Proton10: use `files/lib/wine/x86_64-unix/wine64` as the wine binary.

## Wine Staging 9.21 (system package)

### Status
Works with vanilla Wine 9.x from distro packages. No GE patches needed.

### Key finding
Wine 9.x (both Soda and vanilla Staging) is fully compatible with TD. The mimalloc/DWrite issue only appeared in Wine 10+.

### Launch
Use the system `wine64` binary with the same prefix and env vars as other runners.

## Wine-GE (Lutris) 8-26

### Status
Does not work. Wine 8.x is too old — TD 2025+ requires DLL features only available in Wine 9+.

## Vanilla Wine 11.0 Staging (Kron4ek)

### Status
TD process starts, DXVK/Vulkan/D3D11 initialize successfully, swapchain created, Present called — but the X11 window never appears. The difference with Soda 9 is in the X11 window creation layer, not in D3D11/DXGI.

### Key finding
Both Soda 9 and Wine 11 create D3D11 swapchains and call Present identically. The divergence is in the X11 window mapping — Wine 9 creates a visible X11 window, Wine 10+ doesn't.

### Likely cause
Changes in Wine 10's `dlls/win32u/` or `dlls/winex11.drv/` — the X11 driver that handles native window creation and mapping.

### Root cause identified

**Wine 10 vs Wine 11 are two different issues:**

**Wine 10+ (GE-Proton10, Proton-CachyOS):** The main window appears but fonts are deformed. This is the same font rendering issue that Soda 9 solves with `wine_ui_fixes.tox`. No Mutter workaround exists in Wine 10.

**Wine 11.0 (vanilla):** The main window never appears. Wine 11.0 added a workaround for **Mutter (GNOME)** in `dlls/winex11.drv/window.c`:
```c
/* When transitioning a window from IconicState to NormalState and the window is managed, go
 * through WithdrawnState. This is needed because Mutter doesn't unmap windows when making
 * windows iconic/minimized as Mutter needs to support live preview for minimized windows. */
WARN("window %p/%lx is iconic, remapping to workaround Mutter issues.\n");
```
This workaround adds an extra state transition (Iconic → Withdrawn → Normal) instead of (Iconic → Normal). On **KWin (KDE Wayland)**, this likely leaves the window stuck in WithdrawnState — invisible on screen.

**Conclusion:** GE-Proton10-34 + `wine_ui_fixes.tox` is the best path for a working Proton runner. Wine 11's issue is a Wine bug to report upstream.

### Download
```bash
curl -L https://github.com/Kron4ek/Wine-Builds/releases/download/11.0/wine-11.0-staging-amd64.tar.xz
```

## Soda Wine 9.0-1 (default)

### Status
Stable, fully supported. This is what the `td-install` script installs and the launcher uses.

### Advantages
- Bundled with installer
- No Steam Runtime dependency
- No sandbox interference
- Well-tested with TouchDesigner
- All patches (IDS, DPI, fonts) integrated into launcher

### Limitations
- Wine 9.0 base (older than GE-Proton10/11)
- No vkd3d-proton (not needed for TD)
- Fonts require `wine_ui_fixes.tox` (auto-injected by launcher, transparent to user)
- Same hardware access limitations as all Wine runners

### Font rendering comparison

| Runner | Without fix | With `wine_ui_fixes.tox` |
|--------|-------------|--------------------------|
| **Soda 9.0** | ❌ Fonts missing on timeline | ✅ Fully working |
| **GE-Proton10/11** | ⚠️ Fonts **present** but slightly deformed | ✅ Expected to work |

Soda's font fix is auto-injected by the launcher. GE-Proton has better base font rendering (visible without fix) but needs the same `.tox` for proper appearance.

## Common issues across all runners

### IDs Peak SDK DLLs
All TD 2025+ builds ship `ids_peak_ipl.dll`, `ids_peak_afl.dll`, `ids_peak_ifl.dll`, `ids_peak_comfort_c.dll` which crash under Wine. Fix: zero the `AddressOfEntryPoint` in each DLL's PE header.

See `td_lib/patcher.py` for implementation.

### mimalloc + DWrite hang (Proton 10+)
TD ships `mimalloc.dll` and `mimalloc-redirect.dll`. On Wine 10+, DWrite's font enumeration triggers a crash in mimalloc's redirected allocations, causing TD to hang on the splash screen.

**Fix:** `MIMALLOC_DISABLE_REDIRECT=1`

This is not needed on Wine 9.x (Soda) because DWrite's allocation patterns are compatible.

### NVENC (Video Stream Out TOP)
Not available under any Wine runner. Requires `nvEncodeAPI64.dll` from the Windows NVIDIA driver, which is not redistributable and not provided by Wine.

**Workarounds:**
- **Spout2PW** — TD → Spout → PipeWire → OBS (NVENC on Linux side)
- **NDI** — confirmed working
- **FFmpeg** — pipe frames to native Linux FFmpeg with `-hwaccel nvenc`

### Wayland
Wine's native Wayland support can cause window creation issues. Always set `WAYLAND_DISPLAY=""` to force XWayland.

## Summary

| Feature | Soda 9.0 | GE-P10 | GE-P11 | P-CachyOS |
|---------|----------|--------|--------|----------|
| TD launches | ✅ | ✅* | ✅* | ✅* |
| Font rendering | ✅ | ⚠️ | ⚠️ | ⚠️ |
| D3D11/Vulkan | ✅ | ✅ | ✅ | ✅ |
| NDI output | ✅ | ❓ | ❓ | ❓ |
| Video Stream Out (NVENC) | ❌ | ❌ | ❌ | ❌ |
| CUDA TOPs | ❌ | ❌ | ❌ | ❌ |
| Setup complexity | Low | Medium | Medium | Medium |

* *Requires IDS patch, corefonts, vcrun2019, mimalloc fix*

*\* Requires vkd3d DLLs copied manually*
