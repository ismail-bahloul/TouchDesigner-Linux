# Patches

## `nvcuda-wine11-d3dkmt.patch`

Patch for [SveSop/nvcuda](https://github.com/SveSop/nvcuda) (the CUDA bridge for
Wine), against commit `b00c75a`. It is what makes the NVIDIA CUDA TOPs
(Background, Denoise, Upscaler, RTX Video, Video Stream In/Out) work on the
`--runner proton11` runner. Background and findings: issue #31.

What it changes:

- **Shared handles go through D3DKMT.** TouchDesigner exports its Vulkan textures
  and semaphores as Win32 handles. nvcuda turned them into host fds with the
  `sharedgpures.sys` ioctl of older Proton, which no longer exists in Proton 11
  (Wine 11 keeps them as D3DKMT objects in the wineserver), so
  `cuImportExternalMemory` failed with 999 ("Unable to map the CUDA memory of
  the input texture"). nvcuda now sends a `d3dkmt_object_open` request and calls
  `wine_server_handle_to_fd()` on the result, and keeps the old ioctl as a fallback.
- **The 4-semaphore ring is opt-in.** nvcuda kept only the last 4 imported
  semaphores and destroyed older ones (a leak workaround for one game). With more
  than 4 in use, TouchDesigner hung forever on a destroyed semaphore. Set
  `NVCUDA_SEMAPHORE_RING=1` to get the old behavior back.

### The wineserver request number is build specific

`d3dkmt_object_open` is a request number in the wineserver protocol, and
wine-staging adds requests, so the number differs between Wine builds. It is a
compile-time define, `NVCUDA_D3DKMT_OPEN_REQ` (overridable at runtime with an
environment variable of the same name). For `DAW-GE-Proton11-6c` it is `309`.
For another build, read it from the `wineserver` binary:

```bash
python3 patches/req_numbers.py <runner>/files/bin/wineserver d3dkmt_object_open
```

**The binary `td-install` downloads is therefore only valid for the exact
Proton build it is pinned to** (`DAW-GE-Proton11-6c`).

### Build

Needs `wine` (the `winegcc` tool chain), `meson`, `ninja` and `mingw-w64-gcc`.

```bash
git clone https://github.com/SveSop/nvcuda && cd nvcuda
git checkout b00c75a
git apply /path/to/nvcuda-wine11-d3dkmt.patch

# cross file: the one shipped upstream, with the request number added
sed "s/'-D__WINESRC__'\]/'-D__WINESRC__', '-DNVCUDA_D3DKMT_OPEN_REQ=309']/" \
    build-wine64.txt > cross-6c.txt
meson setup build64 --cross-file cross-6c.txt --buildtype release
ninja -C build64
strip build64/dlls/nvcuda/nvcuda.dll.so
```

The result replaces
`<runner>/files/lib/wine/nvidia-libs/nvcuda/x86_64-windows/nvcuda.dll.so`.

### License

nvcuda is derived from Wine Staging code and is licensed under the
[LGPL 2.1 or later](https://github.com/SveSop/nvcuda/blob/master/LICENSE.md).
The patch above, the upstream commit and the recipe are the corresponding source
of the binary distributed as a release asset.
