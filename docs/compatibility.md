# Compatibility Status

| Area | Status | Notes |
| --- | --- | --- |
| Launch and runtime | ✅ | App launches normally and runs reliably |
| UI rendering | ✅ | Correct with `wine_ui_fixes.tox` (auto-patched on launch) |
| Real-time visuals | ✅ | Live updates and interaction are smooth |
| Inputs / outputs | ✅ | External outputs and inputs are functional in tested scenarios |
| NDI | ✅ | Confirmed working |
| TDAbleton | ✅ | Confirmed working |
| TDBitwig | ✅ | Confirmed working |
| Video Device In | ⚠️ | On the default Soda runner, USB webcams work on first init, but Wine "locks" the device: replug or restart TD to reset. On `--runner proton11` a patched `qcap` releases the camera when the TOP is deactivated or its format changes |
| Virtual webcam (SpoutCam) | ❌ | Windows virtual cameras like SpoutCam are not exposed to the embedded Chromium that browser-based plugins (e.g. MediaPipe) use to grab video, so they never show up in the camera list. Wine has no equivalent for a DirectShow virtual-camera filter. Workaround: a Linux virtual camera (NDI out of TD into a native receiver writing to `v4l2loopback`) |
| NVIDIA TOPs (Background, Denoise, Upscaler, RTX Video) | ⚠️ | ❌ on the default Soda runner: CUDA/TensorRT fail to initialise. ✅ with the experimental `--runner proton11` (patched nvcuda + NVIDIA Video Effects SDK), see [docs/runners.md](runners.md#experimental-td-install---runner-proton11) |
| NVIDIA Flow / Flex TOPs | ❌ | Flow: Wine lacks the keyed mutex for Vulkan-exported memory. Flex: needs a private NVAPI function that dxvk-nvapi does not implement. Same on both runners |
| Engine COMP | ❌ | The background process may start (PID assigned), but the IPC bridge fails to initialize. Workaround: move your logic into a Base or Container COMP to run within the main process |
| Video Stream Out TOP | ⚠️ | ❌ on Soda: needs NVENC (`nvEncodeAPI64.dll`), which is not available there. Use Spout2PW + OBS, NDI, or FFmpeg instead. ✅ on `--runner proton11` (NVENC through the nvidia-libs bridge, with a one-line fix the runner installs) |
| Video Stream In TOP | ⚠️ | ❌ on Soda: needs NVIDIA's hardware decoder. ✅ on `--runner proton11` |
| WebRender TOP | ❌ | Web pages do not render (no errors thrown). Known upstream limitation with Chromium-based components in Wine environments. On `--runner proton11` TouchDesigner never even starts its Chromium helper |
| External installs / integrations | ❓ | Third-party installs, Kinect, extra plugins, and advanced external production pipelines still need broader testing |
| Python packages (pip) | ⚠️ | Works for pure-Python packages (numpy, opencv, requests). Native extensions (.pyd) may fail under Wine — see troubleshooting |
| PyTorch (torch, CPU-only) | ⚠️ | Works with `KMP_AFFINITY=disabled` (auto-set in launcher). Tested 2.13.0+cpu on Wine TkG — see [issue #20](https://github.com/ismail-bahloul/TouchDesigner-Linux/issues/20) |
| Syphon / Spout Out TOP | ⚠️ | Works with a real DXVK install (DXVK 2.7.1, default since 1.8). On wined3d the node errors "Unable to share DirectX Texture" — re-run `td-install` if you see that. DXVK 3.x crashes on this node under Wine 9.0 |
| License dongles (CodeMeter) | ❌ | Client blocked: the CodeMeter service (`CodeMeter.exe`) won't start under Wine 9.0 (protected `cpsrt.dll` fails to load). Server side works (native Linux/Docker). Tooling in `--codemeter`; see [docs/codemeter.md](codemeter.md) |

## Notes

- NVIDIA GPUs are highly recommended.
- Wayland is strongly recommended (X11 may cause launch issues or black screen)
- The launcher disables native Wayland for Wine (avoids GLXMakeCurrent timing bugs on KDE Plasma 6). TouchDesigner runs through XWayland, which is transparent on modern Wayland desktops. This is a temporary workaround until Wine has reliable native Wayland support.
- Performance may vary depending on hardware and driver setup.
