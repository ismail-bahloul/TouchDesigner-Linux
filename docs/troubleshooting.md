# Troubleshooting

## Version list fetch fails

Script falls back to a curated list automatically. No action needed.

## Textport warning: `Error Loading Default Mono Font ... Substituted with Verdana`

Non-blocking fallback. UI and projects still work. The launcher auto-patches `.toe` files with `wine_ui_fixes.tox` on launch.

## License invalidated after an update (new System Code, re-activation needed)

Reported with AUR updates (`paru -Syu` / `yay -Syu`): after updating the package, TouchDesigner showed a new System Code and asked for re-activation (consuming another activation).

**v1.7.0 hardens the launcher against this:** the package ProgramData refresh no longer touches `ProgramData/Derivative/` (your activated `ins*.dat`), and the license is backed up before wineboot/updates and restored after. If you were affected, update to v1.7.0+ and the license files survive updates; if you still see a System Code change, please open an issue with `td-install --diagnose` output.

If you already lost an activation this way, contact `licensing@derivative.ca` with your license ID; they can recover stuck activations.

## Fonts still missing after patching

If text is missing, tiny, or broken, apply `wine_ui_fixes.tox` manually once per project:

1. Open your `.toe` in TouchDesigner
2. Open Palette > **My Components**
3. Right-click and select **Refresh Folder**
4. Drag and drop `wine_ui_fixes.tox` into your network
5. Click **Enable**, then save

The launcher also auto-patches on launch.

## Ubuntu/Debian `:i386` dependency errors (Breaks, version mismatch)

Usually caused by third-party repo skew between amd64 and i386 packages. The installer does not force downgrades. Align package versions in apt sources, then rerun the script.

## TD installer fails on specific `.dll` files (e.g. ZED, Spinnaker, TensorRT/CUDA)

In the TouchDesigner installer, choose **Custom** / **Minimal** install and uncheck optional hardware SDK components you do not need.

## Duplicate menu entry

Remove stale `.desktop` files in `~/.local/share/applications` and run `update-desktop-database`.

## Backup files piling up

Backups are automatically cleaned up after 30 days. You can also delete `~/.local/share/touchdesigner-linux/backups/` manually.

## NVIDIA hybrid laptop uses wrong GPU

Set `USE_NVIDIA_DGPU=Y` before launching, or edit `~/.local/bin/launch-touchdesigner.sh` and change `USE_NVIDIA_DGPU="N"` to `"Y"`. The setting is preserved across updates.

## Python packages fail to install or import (pip)

TouchDesigner ships with its own embedded Python and pip. Use the `--pip` command to install packages:

```bash
td-install --pip install numpy
td-install --pip list
```

If `--pip` is not available, run pip manually:
```bash
WINEPREFIX=~/.local/share/touchdesigner-linux/prefix \
  ~/.local/share/touchdesigner-linux/runner/bin/wine64 \
  "c:\Program Files\TouchDesigner <version>\bin\python.exe" -m pip install <package>
```

### PyTorch / torch fails with OpenMP error (OMP: Error #179, GetNumaNodeProcessorMaskEx)

**Error:**
```
OMP: Error #179: Function GetNumaNodeProcessorMaskEx() failed:
OMP: System error #120: Call not implemented.
```

or with the older error:
```
OSError: [WinError 998] No access to memory location.
Error loading "...torch\\lib\\c10.dll" or one of its dependencies.
```

**Root cause:** Intel OpenMP (bundled with PyTorch) calls `GetNumaNodeProcessorMaskEx()`, a Windows API that Wine TkG doesn't fully implement. When this fails, OpenMP's thread affinity code crashes before torch can even load its core DLLs.

**Fix:** Set `KMP_AFFINITY=disabled` to disable Intel OpenMP thread affinity:
```bash
export KMP_AFFINITY=disabled
td-install --pip install torch --index-url https://download.pytorch.org/whl/cpu
```

This environment variable is already set automatically:
- In the **launcher** (`launch-touchdesigner.sh`) — torch works in TOP Scripts out of the box
- In **`td-install --pip`** — pip installs and `--pip run` commands work automatically

**Works with:** PyTorch CPU-only (tested 2.13.0+cpu under Wine TkG)
**CUDA support:** Not yet tested

**Still stuck?** Process torch logic in a native Linux Python process and bridge results to TD via OSC/UDP.
