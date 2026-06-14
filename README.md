# TouchDesigner-Linux

This is an automated installer to run TouchDesigner on Linux.

![Screenshot](Screenshots/TD_Preview.png)

File icons installed by the project:

![Screenshot](Screenshots/SVG_Preview.png)

### Installation

<details open>
<summary id="automated-installation-recommended"><b>Using the script</b></summary>

![Screenshot](Screenshots/Script_Preview.png)

### Prerequisites

> **NVIDIA users:** Please install your GPU driver before running the script. Reboot after.

### Install

```bash
curl -sSL https://raw.githubusercontent.com/iswad-lab/TouchDesigner-Linux/main/install.sh | bash
```

---


To run headless (SSH, no display):
```bash
curl -sSL https://raw.githubusercontent.com/iswad-lab/TouchDesigner-Linux/main/install.sh | bash -s -- -H
```

To run in debug mode (verbose logs):
```bash
curl -sSL https://raw.githubusercontent.com/iswad-lab/TouchDesigner-Linux/main/install.sh | DEBUG=true bash
```
</sub>

The script is idempotent, it is safe to run multiple times. It skips already-installed components.

**What it does:** detects your distro, installs system packages, sets up a compatibility runtime and environment, lets you pick a TD version, supports side-by-side multi-version installs, creates launcher shortcuts with optional desktop integration, and automatically patches `.toe` files to correct font issues. Installation is **fully silent and headless** — no GUI required, works over SSH. Also features an **Update** option for maintenance and centralised backups with auto-cleanup after 30 days.

---

**Supported distros:**

| Family | Examples |
| --- | --- |
| Arch-based | Arch, CachyOS, Manjaro… |
| Debian/Ubuntu-based | Ubuntu, Mint, Pop!_OS… |
| Fedora-based | Fedora, RHEL… |
| openSUSE-based | Leap, Tumbleweed… |

**Required dependencies (installed automatically):**
| Package | Role |
| --- | --- |
| `innoextract` | Extracts the TouchDesigner installer natively (no Wine needed) |
| `7z` (p7zip) | Decompresses the embedded installer archive |

**Expected duration:** 5–10 min on first run.

> ⏳ Most of the time is spent downloading the ~300MB Wine runner and installing Windows compatibility libraries. The TouchDesigner `.exe` extraction itself takes ~2 min.
>
> First launch can take 1–2 min. This is all normal.

---

### Update

Run the installer again and choose **2 – Update**. This will:

- Regenerate the launcher script with the latest improvements
- Update winetricks
- Reinstall DXVK
- Refresh `wine_ui_fixes.tox` and icons

No need to reinstall TouchDesigner or recreate the Wine prefix.

---

### Uninstall

Run the installer again and choose **3 – Uninstall**. You can remove one selected TouchDesigner version, multiple versions, or everything (runtime, environment, launcher, desktop entries, and backups).

---

### Automatic `.toe` patching

When you launch TouchDesigner or open a `.toe` file (via double click or CLI), the launcher automatically:

1. Checks if the `.toe` file already has the `wine_ui_fixes` patch using toeexpand
2. If not, creates a backup in the centralised backup directory
3. Injects the `wine_ui_fixes.tox` into the `.toe` file using toecollapse
4. Launches TouchDesigner

This process is **idempotent** — if a file is already patched, nothing happens.

---

### Backups

Patched `.toe` files are backed up to a centralised directory:

| Path | Description |
| --- | --- |
| `~/.local/share/touchdesigner-linux/backups/` | Centralised backup directory |

Backups are automatically cleaned up after 30 days.

---

### Useful Paths

| Path | Description |
| --- | --- |
| `~/.local/bin/launch-touchdesigner.sh` | Launcher script |
| `~/.local/share/touchdesigner-linux/` | Base directory (Wine prefix, assets, backups) |
| `~/.local/share/touchdesigner-linux/runner/` | Soda Wine runner |
| `~/.local/share/touchdesigner-linux/prefix/` | Wine prefix (Windows environment) |
| `~/.local/share/touchdesigner-linux/wine_ui_fixes.tox` | Font/UI fix component |
| `~/.local/share/touchdesigner-linux/backups/` | Automatic backups of patched `.toe` files |
| `~/.local/share/touchdesigner-linux/logs/` | Debug logs |
| `~/.local/share/applications/touchdesigner.desktop` | Application menu entry |

---

### Troubleshooting

| Symptom | Fix |
| --- | --- |
| Version list fetch fails | Script falls back to a curated list automatically |
| Textport warning: `Error Loading Default Mono Font ... Substituted with Verdana` | Non-blocking fallback. UI and projects still work. The launcher auto-patches `.toe` files with `wine_ui_fixes.tox` on launch. |
| Fonts still missing after patching | If text is missing, tiny, or broken, apply `wine_ui_fixes.tox` manually once per project: open your `.toe` in TouchDesigner, open Palette > **My Components**, right-click and select **Refresh Folder**, drag and drop `wine_ui_fixes.tox` into your network, click **Enable**, then save. The launcher also auto-patches on launch. |
| Ubuntu/Debian `:i386` dependency errors (`Breaks`, version mismatch) | Usually caused by third-party repo skew between amd64 and i386 packages. The installer does not force downgrades. Align package versions in apt sources, then rerun the script. |
| TD installer fails on specific `.dll` files (for example ZED, Spinnaker, TensorRT/CUDA) | In the TouchDesigner installer, choose `Custom`/`Minimal` install and uncheck optional hardware SDK components you do not need. |
| Duplicate menu entry | Remove stale `.desktop` files in `~/.local/share/applications` and run `update-desktop-database` |
| Backup files piling up | Backups are automatically cleaned up after 30 days. You can also delete `~/.local/share/touchdesigner-linux/backups/` manually. |
| NVIDIA hybrid laptop uses wrong GPU | Set `USE_NVIDIA_DGPU=Y` before launching, or edit `~/.local/bin/launch-touchdesigner.sh` and change `USE_NVIDIA_DGPU="N"` to `"Y"`. The setting is preserved across updates. |

---

### Advanced tools: toeexpand / toecollapse

TouchDesigner includes two utility programs in its `bin/` directory:

- **`toeexpand`** — expands a `.toe` or `.tox` file into a collection of ASCII-readable files (`.n`, `.parm`, `.panel`, `.table`...). To reverse the expansion process, `toecollapse` will convert the files back into a `.toe` or `.tox` format readable by TouchDesigner.
- **`toecollapse`** — collapses an expanded `.toe` file into a form readable by TouchDesigner. This can only be used on a `.toe` file that has been expanded into a collection of ASCII files using `toeexpand`.

All commands use the launcher's Wine environment:

```bash
TD_BASE_DIR="$HOME/.local/share/touchdesigner-linux"
WINE_PREFIX="$TD_BASE_DIR/prefix"
WINEPREFIX="$WINE_PREFIX" "$TD_BASE_DIR/runner/bin/wine64" \
  "$(find "$WINE_PREFIX/drive_c" -name toeexpand.exe -print -quit)" \
  "z:/path/to/file.toe"
```

**Useful workflows:**

- **Inspect a `.toe` contents** — expand it to inspect or version-control its internal components as plain text files
- **Check if `wine_ui_fixes` is applied** — expand and look for a `wine_ui_fixes/` folder inside the `.dir`
- **Manually patch a single file** — `install.sh --patch-toe /path/to/file.toe`
- **Extract, edit, and re-collapse** — expand, modify the ASCII files, then run `toecollapse` to rebuild the `.toe`

The launcher handles all of this automatically, but these tools are available if you need fine-grained control.

---

</details>

---

## Compatibility Status

| Area | Status | Notes |
| --- | --- | --- |
| Launch and runtime | ✅ | App launches normally and runs reliably |
| UI rendering | ✅ | Correct with `wine_ui_fixes.tox` (auto-patched on launch) |
| Real-time visuals | ✅ | Live updates and interaction are smooth |
| Inputs / outputs | ✅ | External outputs and inputs are functional in tested scenarios |
| NDI | ✅ | Confirmed working |
| TD - Bitwig | ✅ | Confirmed working |
| Video Device In | ⚠️ | USB Webcams work on first init, but Wine "locks" the device. Replug or TD restart required to reset |
| NVIDIA TOP | ❌ | Background, Flow and Denoise fail to init CUDA/TensorRT in this environment |
| Engine COMP | ❌ | The background process may start (PID assigned), but the IPC bridge fails to initialize — `.tox` files do not load and textures do not cook. Workaround: move your logic into a Base or Container COMP to run within the main process |
| WebRender TOP | ❌ | Web pages do not render (no errors thrown). Known upstream limitation with Chromium-based components in Wine environments |
| External installs / integrations | ❓ | Third-party installs, Kinect, extra plugins, and advanced external production pipelines still need broader testing |

---

## Notes

- NVIDIA GPUs are highly recommended.
- Wayland is strongly recommended (X11 may cause launch issues or black screen)
- The launcher disables native Wayland for Wine (avoids GLXMakeCurrent timing bugs on KDE Plasma 6). TouchDesigner runs through XWayland, which is transparent on modern Wayland desktops. This is a temporary workaround until Wine has reliable native Wayland support.
- Performance may vary depending on hardware and driver setup.

---

## Support the project

If this project helps you, you can support maintenance and improvements via GitHub Sponsors:

- https://github.com/sponsors/iswad-lab


---

<div align="center">

Built with care — **Iswad**

</div>
