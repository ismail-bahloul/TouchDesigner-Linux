# Wine Runners Comparison

A technical reference for the Wine runners tested with TouchDesigner under Linux.

## Tested runners

| Runner | Base | Status | Notes |
|--------|------|--------|-------|
| **Soda 9.0-1** | Wine 9.0 | ✅ Default | Stable, fully supported, included in installer |
| **Wine TkG** | Wine 9.0+ | ✅ AUR | CachyOS/Arch default via AUR, similar to Soda |
| **GE-Proton10-34** | Wine 10.0 (Staging) | ✅ Works | Best Proton option, vkd3d-proton bundled |
| **GE-Proton11-1** | Wine 11.0 (Staging) | ✅ Works | Needs vkd3d DLLs copied manually |
| **UMU-Proton-10.0-4** | Wine 10.0 (Staging) | ❌ | pressure-vessel sandbox conflicts with TD |
| **Proton-CachyOS** | Wine 10.0 (Staging) | ❓ | Not tested |

## GE-Proton10-34 (recommended Proton runner)

### Status
Fully working. TD launches, renders, and is stable.

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
- **NVENC** — not available (missing `nvEncodeAPI64.dll`)
- **CUDA TOPs** — not available (NVIDIA CUDA under Wine limitation)
- Same limitations as Soda Wine for hardware access

## GE-Proton11-1

### Status
Works after manually installing vkd3d DLLs. Most recent GE-Proton build.

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
- Same hardware access limitations as all Wine runners

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

| Feature | Soda 9.0 | GE-Proton10 | GE-Proton11 | UMU-Proton |
|---------|----------|-------------|-------------|------------|
| TD launches | ✅ | ✅ | ✅* | ❌ |
| Font rendering | ✅ | ✅ | ✅ | ❌ |
| D3D11/Vulkan | ✅ | ✅ | ✅ | ❌ |
| NDI output | ✅ | ✅ | ✅ | ❌ |
| Video Stream Out (NVENC) | ❌ | ❌ | ❌ | ❌ |
| CUDA TOPs | ❌ | ❌ | ❌ | ❌ |
| Spout2 | ❓ | ❓ | ❓ | ❓ |
| Setup complexity | Low | Medium | Medium | High |

*\* Requires vkd3d DLLs copied manually*
