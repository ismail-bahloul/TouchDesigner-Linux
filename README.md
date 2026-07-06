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

**Recommended - any distro:**
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

**Debug mode:**
```bash
DEBUG=true curl -sSL https://raw.githubusercontent.com/iswad-lab/TouchDesigner-Linux/main/install.sh | bash
```

![Screenshot](Screenshots/Script_Preview.png)

---

## Update & Uninstall

### Any distro
- **Update** -> Run the installer and choose **2 - Update**
- **Uninstall** -> Run the installer and choose **3 - Uninstall**

Regenerates launcher, winetricks, DXVK, and UI fixes. No need to reinstall TD or recreate the Wine prefix.

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

- [Compatibility status](docs/compatibility.md) - what works and what doesn't
- [Troubleshooting](docs/troubleshooting.md) - common issues and fixes
- [Advanced tools](docs/advanced-tools.md) - toeexpand / toecollapse

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
