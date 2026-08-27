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
| Video Device In | ⚠️ | USB Webcams work on first init, but Wine "locks" the device. Replug or TD restart required to reset |
| NVIDIA TOP | ❌ | Background, Flow and Denoise fail to init CUDA/TensorRT in this environment |
| Engine COMP | ❌ | The background process may start (PID assigned), but the IPC bridge fails to initialize. Workaround: move your logic into a Base or Container COMP to run within the main process |
| Video Stream Out TOP | ❌ | Requires NVENC (`nvEncodeAPI64.dll`) which is not available under Wine. Use Spout2PW + OBS, NDI, or FFmpeg instead |
| Video Stream In TOP | ❌ | Requires NVIDIA's hardware decoder, not supported under Wine |
| WebRender TOP | ❌ | Web pages do not render (no errors thrown). Known upstream limitation with Chromium-based components in Wine environments |
| External installs / integrations | ❓ | Third-party installs, Kinect, extra plugins, and advanced external production pipelines still need broader testing |
| Python packages (pip) | ⚠️ | Works for pure-Python packages (numpy, opencv, requests). Native extensions (.pyd) may fail under Wine — see troubleshooting |
| PyTorch (torch, CPU-only) | ⚠️ | Works with `KMP_AFFINITY=disabled` (auto-set in launcher). Tested 2.13.0+cpu on Wine TkG — see [issue #20](https://github.com/ismail-bahloul/TouchDesigner-Linux/issues/20) |
| License dongles (CodeMeter) | ❌ | Client blocked: the CodeMeter service (`CodeMeter.exe`) won't start under Wine 9.0 (protected `cpsrt.dll` fails to load). Server side works (native Linux/Docker). Tooling in `--codemeter`; see [docs/codemeter.md](codemeter.md) |

## Notes

- NVIDIA GPUs are highly recommended.
- Wayland is strongly recommended (X11 may cause launch issues or black screen)
- The launcher disables native Wayland for Wine (avoids GLXMakeCurrent timing bugs on KDE Plasma 6). TouchDesigner runs through XWayland, which is transparent on modern Wayland desktops. This is a temporary workaround until Wine has reliable native Wayland support.
- Performance may vary depending on hardware and driver setup.
