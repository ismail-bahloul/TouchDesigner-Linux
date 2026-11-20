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
| **DPI** | LogPixels auto-detect (`td-install --dpi`) | Readability on HiDPI displays |
| **KMP_AFFINITY** | `disabled` | Fixes torch import (Intel OpenMP + Wine) |
| **PYTHONPATH** | Set automatically | Makes pip packages visible to TD |

This is exactly what `td-install` sets up, and what `launch-touchdesigner.sh` configures at runtime.

## Why Wine 9 works and Wine 10+ doesn't (short version)

| Version | Works? | Why |
|---------|--------|-----|
| **Wine 9.x** (Soda, TkG, vanilla) | ✅ | No Mutter workaround, stable DWrite |
| **Wine 10.x** (GE-Proton10, Proton) | ⚠️ | Window OK but fonts deformed → `wine_ui_fixes.tox` helps |
| **Wine 11.x** (vanilla, GE-P11, Proton) | ❌ | Mutter workaround added in Valve fork → window invisible on KWin |
| **Wine 11.x + DWrite fix** (DAW-GE-Proton11-6c via UMU) | ✅ | See the 2026-09 update below |

The key: Soda 9.0 is built with `_use_staging="false"` (no Wine Staging patches). Staging introduced the DWrite rewrite in Wine 10, and Valve added the Mutter workaround in Wine 11. Both were incompatible with TouchDesigner on KDE/Wayland; the Wine 11 part is now fixable (see the update below).

## Update (2026-09): Wine 11 works with the DWrite fix

**DAW-GE-Proton11-6c works.** Tested on CachyOS (Arch-like), NVIDIA 615.71.09, KDE/KWin Wayland.

The Wine 11 DWrite font-enumeration loop is a real Wine bug, but it is fixable.
[KitsuneDev's `daw-proton-ge` fork](https://github.com/KitsuneDev/daw-proton-ge) carries a
`dwrite: Fix glyph bitmap cache reuse (TouchDesigner)` patch (plus a WebRender / hardware-acceleration
fix) and runs TD on Wine 11. The DWrite patch is being upstreamed to GE-Proton.

### Recipe

- [umu-launcher](https://github.com/Open-Wine-Components/umu-launcher) (tested 1.4.3) with the
  `steamrt4` runtime (downloaded on first run)
- `DAW-GE-Proton11-6c` extracted from its release tarball
- A fresh prefix:

```bash
export WINEPREFIX="$HOME/td-proton/prefix"
export PROTONPATH="$HOME/td-proton/DAW-GE-Proton11-6c"
export GAMEID=0

# 1. install TouchDesigner (official installer)
umu-run TouchDesigner.2025.33230.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART

# 2. fonts (needed for text to render at all; wine_ui_fixes.tox is still needed, see Caveats)
umu-run winetricks allfonts

# 3. launch
umu-run "$WINEPREFIX/pfx/drive_c/Program Files/Derivative/TouchDesigner/bin/TouchDesigner.exe"
```

### Results

| Check | Result |
|-------|--------|
| Splash screen | Passed |
| Main window | Opens, license accepted |
| GPU | Used, `nvidia-smi` shows TouchDesigner.exe with ~755 MiB VRAM, ~35% GPU-Util |
| Fonts | Render, but descenders (p, g, j, y) are clipped in Bitmap-mode UI text, e.g. "Tem_o" in the timeline bar. `wine_ui_fixes.tox` fixes it |
| CPU | ~60-75% steady (render thread, not software rendering) |

### Caveats

- This needs the **fork**: vanilla Wine 11 and GE-Proton11-6 still loop at the splash, so this is
  not "Wine 11 works" in general yet. It becomes broadly usable once the DWrite fix lands upstream
  in GE-Proton.
- The test used the full UMU + pressure-vessel path, not `files/bin/wine` directly, so it says
  nothing about the Mutter / window-mapping path used by the direct-binary recipes below.
- The fork targets DAWs and carries unrelated patches (FL Studio, Native Instruments). Prefer
  upstream GE-Proton once the TouchDesigner patches are merged.
- `wine_ui_fixes.tox` is still needed. Text TOPs in TD's own UI that use the Bitmap display
  method lose the bottom of their glyphs; switching them to Scalable (what the `.tox` does)
  fixes it. Checked with before/after screenshots on TD 2025.33230 (2026-11).
- NVIDIA TOPs: Background, Denoise, Upscaler, RTX Video and Video Stream In/Out work with a
  patched nvcuda and NVENC bridge and the NVIDIA Video Effects SDK runtime (see issue #31). Flow, Flex and
  Web Render still don't.


## Experimental: `td-install --runner proton11`

The DAW-GE-Proton11-6c recipe above, packaged in the installer. Soda 9 stays the default;
this is opt-in, for the NVIDIA CUDA TOPs and the CodeMeter service.

```bash
td-install                                  # interactive: asks which runner (Enter = Soda)
td-install --runner proton11               # asks before downloading NVIDIA's Video Effects SDK
td-install --runner proton11 --nvidia-vfx  # downloads it without asking (~770 MB)
```

Or through the one-liner: `curl -sSL .../install.sh | bash -s -- --runner proton11`.

**Needs** [umu-launcher](https://github.com/Open-Wine-Components/umu-launcher) (`umu-run` in
`PATH`: `sudo pacman -S umu-launcher` on Arch, `sudo dnf install umu-launcher` on Fedora). The
first run also downloads the Steam Linux Runtime (a few hundred MB). Expect about **13 GB** on
disk (Soda: 3-5 GB). The AUR package is unchanged: it installs Soda and has no `--runner`
option, so this is for the curl installer.

### What it sets up

- DAW-GE-Proton11-6c from [KitsuneDev's fork](https://github.com/KitsuneDev/daw-proton-ge),
  checksum pinned, run through umu-launcher.
- A fresh prefix, fonts (`winetricks allfonts`) and the Lucida Console mono font. No DXVK or
  vcrun: Proton manages its own DXVK and re-copies it on every launch.
- On an NVIDIA GPU: a **patched nvcuda** (the CUDA bridge) and a **patched NVENC bridge**, see
  [`patches/`](../patches/README.md),
  and the NVAPI / nvenc / nvml bridges bundled with the runner. For a hybrid laptop, DXVK and
  vkd3d are limited to the NVIDIA GPU, otherwise Direct3D 12 code can land on the iGPU.
- Optionally NVIDIA's **Video Effects SDK** runtime (0.7.6), downloaded from NVIDIA for your GPU
  generation (RTX 20 / 30 / 40 / 50 series, checksum pinned). The NVIDIA Background, Denoise and
  Upscaler TOPs need it; it is not a Wine thing, Windows needs it too.
- A **patched `qcap`** (Wine's webcam capture), so a Video Device In TOP releases the camera when
  it is deactivated or its format changes, see [`patches/`](../patches/README.md) and issue #35.
- Small relay scripts at `runner/bin/{wine64,wine,wineboot,wineserver}` that forward to
  `umu-run`, so `--pip`, `--dpi`, `--codemeter` and the `.toe` font patching keep working
  unchanged.
- `.runner` (which runner this install uses), `proton11.env` (managed, rewritten by
  `td-install --update`) and `proton11.user.env` (yours, never overwritten: put `PROTON_LOG=1`
  and the like there). The launcher reads them.

### What was verified

Clean install made by the installer, then the generated launcher, 2026-11-19: CachyOS, KDE
Wayland, RTX 3070 Laptop + AMD iGPU, driver 620.70, TouchDesigner 2025.33230.

| Works | Notes |
|-------|-------|
| NVIDIA Background, Denoise, Upscaler TOPs | with the patched nvcuda and the Video Effects SDK |
| NVIDIA RTX Video TOP | super resolution mode, no error, image out |
| Video Stream Out TOP to Video Stream In TOP over a local RTSP server | a 640x360 stream comes back in 2 s with real content. NVENC encodes and NVDEC decodes on the GPU. Needs the patched NVENC bridge: the stock one reports `Encoding this pixel format is not supported on this GPU` |
| NDI Out to NDI In, Spout Out, Python (numpy, cv2, requests, HTTPS) | |
| Video Device In: deactivating the TOP, reactivating it, changing the format | the camera is released each time: 6 of 6 reactivations and 8 of 8 format changes gave an image. Stock Wine gave 1 of 6 reactivations, and its format-change test never finished (`Device or resource busy`, issue #35) |
| Font fix (`wine_ui_fixes.tox`) | still needed, the launcher injects it as usual |
| Projects stored outside `$HOME` | tried with `/var/tmp`. If TouchDesigner cannot see files on another mount, add `export PRESSURE_VESSEL_FILESYSTEMS_RW=/your/path` to `proton11.user.env` (not tried) |

Existing installs get the NVENC fix with `td-install --update`.

| Does not work | Why |
|---------------|-----|
| NVIDIA Flow TOP | Wine does not create the keyed mutex for memory *exported* by Vulkan, so TouchDesigner's GPU submit fails ("NVIDIA Driver Error"). Needs a patch in Wine's `win32u` |
| NVIDIA Flex TOP / Flex Solver COMP | Flex calls a private NVAPI function (id `0x07B86467`) that dxvk-nvapi does not have, and crashes on the null result |
| Web Render TOP | TouchDesigner never starts its Chromium helper |

### Trade-offs

- **The EDIT button asks which program to use, once per file type.** The runner's programs run in
  a container that looks like a Flatpak sandbox, so `xdg-open` goes through the desktop portal.
  On KDE Plasma the first EDIT on a `.txt` or `.frag` file shows a "Choose an application" window
  even when a default exists. Pick your editor and tick "Set as default app to open Plain text
  document files": it does not ask again, and the choice covers `.txt`, `.frag` and the other
  plain text types. (Seen on Plasma 6; not tried on other desktops.)
- **Slower launch.** Every Wine call goes through umu's container, about 3.3 s each. Opening an
  already patched project takes about 23 s from the launcher to a loaded TouchDesigner, against
  15 s for the bare launch (`touchdesigner --no-patch`). Most of the difference is the font-fix
  check. A first launch, or a project that is not patched yet, costs more.
- **A runner cannot be switched on an existing install.** `td-install` refuses, because a Wine 9
  prefix upgraded in place by Proton 11 (or the reverse) breaks in ways that are hard to debug.
  Run `td-install --uninstall` first (this also removes the TouchDesigner license activation),
  or install into another directory: `TD_BASE_DIR=~/td-proton td-install --runner proton11`.
- **The license is tied to the prefix.** A new prefix has a new Wine machine id, so TouchDesigner
  asks for a key again, the same as after any reinstall (issue #26).
- **Pinned to one Proton build.** The patched nvcuda, NVENC bridge and qcap are only valid for DAW-GE-Proton11-6c; see
  [`patches/README.md`](../patches/README.md) for why and how to rebuild it. The fork has not
  had a release since 2026-09-13; once the DWrite fix reaches upstream GE-Proton, that is the
  better target.
- `td-install --codemeter` has not been tried on this runner yet. The CodeMeter service itself
  starts on it (issue #31).

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

Note: GE-Proton10's default font rendering is actually **better** than Soda without the `.tox` fix - fonts are visible, just not perfectly shaped.

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
- **NVENC** - not available (missing `nvEncodeAPI64.dll`)
- **CUDA TOPs** - not available (NVIDIA CUDA under Wine limitation)

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
**Superseded (2026-09):** works with `DAW-GE-Proton11-6c` + `allfonts`. See the
"Update (2026-09)" section at the top. The findings below still apply to unpatched
UMU-Proton builds.

### Issues
1. **pressure-vessel sandbox** - blocks environment variables like `MIMALLOC_DISABLE_REDIRECT`
2. **UMU-Proton builds** - automated builds lack GE patches needed for TD compatibility
3. **Steam Runtime dependency** - heavy (~800 MB), complex setup
4. **prefix version conflicts** - UMU-Proton may fail when upgrading prefixes from other runners

### Workaround attempt (partial success)
- Using `UMU_USE_STEAM=0` bypasses sandbox but breaks DXVK deployment
- Using `files/bin/wine` directly with UMU-Proton gives same libvkd3d errors as GE-Proton11

**Recommendation:** Use GE-Proton directly instead of UMU-Proton wrappers.

## Proton-CachyOS

### Status
Tested briefly - TD process launched successfully (process alive). Window visibility not confirmed. Likely same behavior as GE-Proton10 (window appears with deformed fonts).

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

**Note:** Tested with system wine (not standalone). Results should be the same as any vanilla Wine 9.x build. Not independently verified with a standalone Wine 9.21 build.

### Key finding
Wine 9.x (both Soda and vanilla Staging) is fully compatible with TD. The mimalloc/DWrite issue only appeared in Wine 10+.

### Launch
Use the system `wine64` binary with the same prefix and env vars as other runners.

## Wine-GE (Lutris) 8-26

### Status
Does not work. Wine 8.x is too old - TD 2025+ requires DLL features only available in Wine 9+.

## Vanilla Wine 11.0 Staging (Kron4ek)

### Status
TD process starts, DXVK/Vulkan/D3D11 initialize successfully, swapchain created, Present called - but the X11 window never appears. The difference with Soda 9 is in the X11 window creation layer, not in D3D11/DXGI.

### Key finding
Both Soda 9 and Wine 11 create D3D11 swapchains and call Present identically. The divergence is in the X11 window mapping - Wine 9 creates a visible X11 window, Wine 10+ doesn't.

### Likely cause
Changes in Wine 10's `dlls/win32u/` or `dlls/winex11.drv/` - the X11 driver that handles native window creation and mapping.

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
This workaround adds an extra state transition (Iconic → Withdrawn → Normal) instead of (Iconic → Normal). On **KWin (KDE Wayland)**, this likely leaves the window stuck in WithdrawnState - invisible on screen.

**Conclusion (2026-08):** GE-Proton10-34 + `wine_ui_fixes.tox` was the best path for a working Proton runner. Wine 11's issue is a Wine bug to report upstream. **Superseded 2026-09:** a patched Wine 11 (DAW-GE-Proton11-6c) works, see the update at the top.

### Soda 11 (Bottles, Wine 11)
**Tested 2026-08 (soda-11.0-5), full investigation:**

- **Symptom:** TD freezes at the end of the splash screen (during project load) - a busy loop, not a crash (CPU stays at 60-120%).
- **Root cause:** a DWrite font-enumeration infinite loop. A `+dwrite` trace shows ~1.9M `localizedstrings_` and ~1.1M `dwritefontfile_` calls in 25 seconds. It is an upstream Wine 11 bug, not a TD or mimalloc issue.
- **What was ruled out:** the `wine_ui_fixes.tox` COMP (happens on pristine projects too), `MIMALLOC_DISABLE_REDIRECT=1` (does not help), the prefix's font files (loop happens with 0 fonts in `windows/Fonts`), and host fontconfig (loop also happens with `FONTCONFIG_FILE=/dev/null`).
- **Partial workaround:** `MIMALLOC_DISABLE_REDIRECT=1` + `FONTCONFIG_FILE=/dev/null FONTCONFIG_PATH=/nonexistent` + empty `windows/Fonts` lets TD launch and load projects - but with **no fonts available**, so UI text is broken. Not usable as a daily setup.

**Verdict (2026-08):** Wine 11 remains unusable for TD until the DWrite font-enumeration loop is fixed upstream. Stick with Soda 9.0-1. **Superseded 2026-09:** the loop is fixed by the DWrite patch in DAW-GE-Proton11-6c (see the update at the top); upstreaming to GE-Proton is in progress.

**GE-Proton11-5 (Wine 11 Staging) was also tested (2026-08):** identical busy loop at the splash screen. Unpatched Wine 11 builds loop. The DWrite patch in DAW-GE-Proton11-6c fixes it (see the 2026-09 update at the top). The only other newer-than-9 runner that works is GE-Proton10-34 (Wine 10).

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
Not available on Soda or on stock GE-Proton: the NVENC bridge that ships with GE-Proton has a
bug in `NvEncGetInputFormats` (it never lists the input formats), so TouchDesigner reports an
unsupported pixel format. With the fixed bridge that `td-install --runner proton11` installs, the
Video Stream Out TOP encodes on the GPU, see [patches/README.md](../patches/README.md).

**Workarounds on Soda:**
- **Spout2PW** - TD → Spout → PipeWire → OBS (NVENC on Linux side)
- **NDI** - confirmed working
- **FFmpeg** - pipe frames to native Linux FFmpeg with `-hwaccel nvenc`

### Wayland
Wine's native Wayland support can cause window creation issues. Always set `WAYLAND_DISPLAY=""` to force XWayland.

## Summary

| Feature | Soda 9.0 | GE-P10 | GE-P11 | DAW-GE-P11-6c (UMU) |
|---------|----------|--------|--------|---------------------|
| TD launches | ✅ | ✅* | ✅* | ✅ |
| Font rendering | ✅ (via .tox) | ⚠️ Present but deformed | ⚠️ Present but deformed | ⚠️ descenders clipped in Bitmap UI text, `.tox` fixes it |
| D3D11/Vulkan | ✅ | ✅ | ✅ | ✅ |
| NDI output | ✅ | ❓ | ❓ | ✅ |
| Video Stream Out (NVENC) | ❌ | ❌ | ❌ | ✅ (patched NVENC bridge) |
| CUDA TOPs | ❌ | ❌ | ❌ | ✅ (patched nvcuda, `--runner proton11`) |
| Setup complexity | Low | Medium | Medium | Medium (needs UMU) |

* *Requires IDS patch, corefonts, vcrun2019, mimalloc fix*
