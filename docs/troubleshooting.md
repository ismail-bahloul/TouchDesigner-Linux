# Troubleshooting

## Version list fetch fails

Script falls back to a curated list automatically. No action needed.

## Textport warning: `Error Loading Default Mono Font ... Substituted with Verdana`

Non-blocking fallback. UI and projects still work. The launcher auto-patches `.toe` files with `wine_ui_fixes.tox` on launch.

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
