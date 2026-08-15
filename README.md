# TouchDesigner-Linux

[![Tests](https://img.shields.io/github/actions/workflow/status/iswad-lab/TouchDesigner-Linux/tests.yml?label=Tests)](https://github.com/iswad-lab/TouchDesigner-Linux/actions)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![AUR](https://img.shields.io/aur/version/touchdesigner-linux?label=AUR)](https://aur.archlinux.org/packages/touchdesigner-linux)

Run TouchDesigner on Linux via Wine, fully automated.
One command, works on any distro.

![Screenshot](Screenshots/TD_Preview.png)

👉 [Roadmap & planned features](ROADMAP.md)

---

## Quick Install

**Any distro (recommended):**
```bash
curl -sSL https://raw.githubusercontent.com/iswad-lab/TouchDesigner-Linux/main/install.sh | bash
```

**Arch Linux (AUR):**
```bash
paru -S touchdesigner-linux
```

> 5-10 min, ~3-5 GB disk, auto-cleanup

The installer auto-detects your distro and environment:
- **Graphical session** -> full install with desktop shortcuts
- **SSH / headless** -> auto-detected, skips GUI-only steps
- **NVIDIA users** -> install GPU driver first, then reboot
- **SteamOS** -> the read-only root filesystem is disabled automatically (`steamos-readonly disable`, needs your sudo password)

**Debug mode:**
```bash
DEBUG=true curl -sSL https://raw.githubusercontent.com/iswad-lab/TouchDesigner-Linux/main/install.sh | bash
```

**Install Python packages into TD:**
```bash
td-install --pip install numpy
td-install --pip install torch --index-url https://download.pytorch.org/whl/cpu
td-install --pip list
```

![Screenshot](Screenshots/Script_Preview.png)

---

## Update & Uninstall

### Any distro
- **Update** -> Run the installer and choose **2. Update**
- **Uninstall** -> Run the installer and choose **3. Uninstall**

Regenerates launcher, winetricks, DXVK, and UI fixes. No need to reinstall TD or recreate the Wine prefix.

**Note:** a full uninstall removes everything, including your TouchDesigner license activation (`ins*.dat`) — you will need to re-enter your license key after reinstalling. The uninstaller warns you before deleting it.

### Arch Linux (AUR)

**Update**
```bash
paru -Syu
```

**Uninstall**
```bash
paru -R touchdesigner-linux
```

---

## First Launch

The font fix (`wine_ui_fixes.tox`) is injected into `.toe` files on launch.
The **license activation screen** loads before any `.toe`, so text may look broken.

1. Launch TD → license screen (missing text is **normal**)
2. Enter your license, close TD
3. Launch again → fonts are fixed

---

## Documentation

- [How it works](docs/how-it-works.md) — explains each fix and why it's applied
- [Compatibility status](docs/compatibility.md) — what works and what doesn't
- [Wine runners comparison](docs/runners.md) — tested runners, source analysis, compatibility
- [Troubleshooting](docs/troubleshooting.md) — common issues and fixes
- [Advanced tools](docs/advanced-tools.md) — toeexpand / toecollapse

### Useful paths

| Path | Description |
| --- | --- |
| `~/.local/bin/launch-touchdesigner.sh` | Launcher script |
| `~/.local/share/touchdesigner-linux/` | Base directory (runner, prefix, assets) |
| `~/.local/share/touchdesigner-linux/prefix/` | Wine prefix |
| `~/.local/share/touchdesigner-linux/backups/` | Auto-backups of patched `.toe` files |

File icons installed by the project:

![Screenshot](Screenshots/SVG_Preview.png)

---

## Support

If this project helps you:
- ⭐ **Star** the repo
- Support via [GitHub Sponsors](https://github.com/sponsors/iswad-lab)

---

<div align="center">Built with care - <b>Iswad</b></div>
