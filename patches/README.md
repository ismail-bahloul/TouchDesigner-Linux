# Patches

- [`nvcuda-wine11-d3dkmt.patch`](#nvcuda-wine11-d3dkmtpatch): the NVIDIA CUDA TOPs on Proton 11.
- [`qcap-release-on-stop.patch`](#qcap-release-on-stoppatch): Video Device In keeps working after the TOP is deactivated.
- [`nvenc-getinputformats.patch`](#nvenc-getinputformatspatch): the Video Stream Out TOP can encode.

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

## `qcap-release-on-stop.patch`

Patch for Wine's `qcap` (the DirectShow video capture filter that TouchDesigner's Video
Device In TOP goes through). Against Valve's Wine at commit
`00e639898e01f8dd6fbee3851bd4c1e412c5b875` (the `wine` submodule of DAW-GE-Proton11-6c)
**with the two `qcap-dshow-fixes` patches that build applies on top**
([`patches/wine-hotfixes/qcap-dshow-fixes/`](https://github.com/KitsuneDev/daw-proton-ge/tree/DAW-GE-Proton11-6c/patches/wine-hotfixes/qcap-dshow-fixes)
in KitsuneDev's fork). Background: issue #35.

What was wrong: Wine opens `/dev/video0` when the capture filter is created and only closes it
when the filter is destroyed. Stopping the graph leaves the descriptor open, and on a UVC
camera the descriptor that called `VIDIOC_S_FMT` keeps the stream "privilege" until it is
closed. TouchDesigner builds a new graph on each deactivation / format change, and the new
graph's `VIDIOC_S_FMT` then fails with `EBUSY` ("Failed to set pixel format: Device or
resource busy"): no image, and no other program can use the camera either.

What it does: the capture filter closes the camera when the graph goes to *Stopped*, after
the streaming thread has ended, and the camera is reopened on demand (the saved format is
applied again at the next start). Every access to the descriptor goes through a lock, since
the property calls (brightness...) can come from another thread than the one stopping the
graph.

Measured on the clean `--runner proton11` install (CachyOS, USB HP webcam):

| | stock qcap | patched qcap |
|---|---|---|
| Deactivate / reactivate the TOP, 6 times | image 1 time out of 6 | image 6 out of 6 (0.8 s each) |
| Camera free for another program after deactivation | never (4 probes out of 4 busy) | always (0 probes out of 4 busy) |
| Change the signal format 8 times | 45 `EBUSY` errors, test never finishes | image 8 out of 8, right resolution, 0 errors |

### Build

Needs `flex`, `bison`, `autoconf`, `make`, `gcc` and `mingw-w64-gcc`; about 15 minutes.

```bash
mkdir wine && cd wine
curl -L https://github.com/ValveSoftware/wine/archive/00e639898e01f8dd6fbee3851bd4c1e412c5b875.tar.gz \
    | tar xz --strip-components=1
base=https://raw.githubusercontent.com/KitsuneDev/daw-proton-ge/DAW-GE-Proton11-6c/patches/wine-hotfixes/qcap-dshow-fixes
for f in 0001-qcap-fix-Smart-Tee-preview-allocator-and-RGB32-negot.patch \
         0002-qcap-fix-wow64-media-type-marshaling-in-v4l-backend.patch; do
    curl -fL $base/$f | patch -p1
done
patch -p1 < /path/to/qcap-release-on-stop.patch
sh autogen.sh        # the tarball lacks configure and some generated headers
mkdir ../obj && cd ../obj
../wine/configure --enable-archs=x86_64 --disable-tests --without-x --without-wayland \
    --without-vulkan --without-opengl
make -j"$(nproc)" dlls/qcap/x86_64-windows/qcap.dll dlls/qcap/qcap.so
x86_64-w64-mingw32-strip dlls/qcap/x86_64-windows/qcap.dll && strip dlls/qcap/qcap.so
```

The two files replace `<runner>/files/lib/wine/x86_64-windows/qcap.dll` and
`<runner>/files/lib/wine/x86_64-unix/qcap.so`; they must be replaced together. The PE
imports/exports and the unix library's dependencies are identical to the stock ones.

`td-install` downloads them as the `qcap-DAW-GE-Proton11-6c.tar.gz` release asset (checksums
pinned in `td_lib/runner.py`), keeps the stock files as `*.orig`, and only does so for the
runner build it is pinned to. The change is small and generic, so it is a candidate for
upstream Wine.

Wine is licensed under the LGPL 2.1 or later; the patch above, the Wine commit and the recipe
are the corresponding source of the binaries.

## `nvenc-getinputformats.patch`

Patch for [SveSop/nvenc](https://github.com/SveSop/nvenc) (the NVENC / NVDEC bridge GE-Proton bundles
as `nvidia-libs/nvenc`), against commit `09ec9e1c8b25a351e415a6d0361bfacad0fd710c`, the one
DAW-GE-Proton11-6c ships. It is one line, and the bug is still in the latest upstream version.

What was wrong: `NvEncGetInputFormats` in `dlls/nvencodeapi/nvencodeapi.c` called
`nvEncGetInputFormatCount` instead of `nvEncGetInputFormats`. The count came back right but the
array of formats was never filled, so an application asking "which pixel formats can I give
you?" got an empty list. TouchDesigner's Video Stream Out TOP then stopped before initializing
the encoder, with `Encoding this pixel format is not supported on this GPU`. Any application that
checks the input formats first (ffmpeg's `nvenc` does) is affected the same way.

Measured on the clean `--runner proton11` install: with the stock bridge TouchDesigner opens an
NVENC session, asks for the formats, and closes it again. With the fix the encoder initializes,
registers its resources and encodes pictures. A Video Stream Out TOP feeding a Video Stream In TOP
over a local RTSP server returns a 640x360 image with real content after 2 s, and the NVDEC calls
(`cuvidCreateVideoParser`, `cuvidParseVideoData`) show the decoder in use.

### Build

Needs `wine` (the `winegcc` tool chain), `meson` and `ninja`.

```bash
git clone https://github.com/SveSop/nvenc && cd nvenc
git checkout 09ec9e1c8b25a351e415a6d0361bfacad0fd710c
git apply /path/to/nvenc-getinputformats.patch
meson setup build64 --cross-file build-wine64.txt --buildtype release
ninja -C build64
strip build64/dlls/nvencodeapi/nvencodeapi64.dll.so
```

The result replaces
`<runner>/files/lib/wine/nvidia-libs/nvenc/x86_64-windows/nvencodeapi64.dll.so`. Unlike nvcuda it
does not depend on the wineserver request numbers, but `td-install` still only installs it on the
runner build it is pinned to. It downloads it as the `nvencodeapi64-DAW-GE-Proton11-6c.dll.so`
release asset (checksum pinned in `td_lib/runner.py`) and keeps the stock file as `*.orig`.

nvenc is derived from Wine Staging code and is licensed under the LGPL 2.1 or later; the patch,
the upstream commit and the recipe above are the corresponding source of the binary.
