# TouchDesigner-Linux

[![Tests](https://img.shields.io/github/actions/workflow/status/iswad-lab/TouchDesigner-Linux/tests.yml?label=Tests)](https://github.com/iswad-lab/TouchDesigner-Linux/actions)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![AUR](https://img.shields.io/aur/version/touchdesigner-linux?label=AUR)](https://aur.archlinux.org/packages/touchdesigner-linux)

Run TouchDesigner on Linux via Wine — fully automated installation.

![Screenshot](Screenshots/TD_Preview.png)

👉 [Roadmap & planned features](ROADMAP.md)

---

## Quick Install

### Any distro (recommended)

```bash
curl -sSL https://raw.githubusercontent.com/iswad-lab/TouchDesigner-Linux/main/install.sh | bash
```

**That's it.** One command for any environment:

- **All distros** → auto-install (Arch, Ubuntu, Fedora, etc.)
- **Graphical session** → full install with shortcuts
- **SSH / headless** → auto-detected, prepares everything except GUI-only steps

**Prerequisite:** NVIDIA users should install their GPU driver first, then reboot.

### Debug mode

```bash
DEBUG=true curl -sSL https://raw.githubusercontent.com/iswad-lab/TouchDesigner-Linux/main/install.sh | bash
```

The script detects your distro, installs required packages, sets up a Wine environment, downloads and installs TouchDesigner. It supports **multiple versions side-by-side**, auto-patches `.toe` files for font fixes, and creates desktop shortcuts.

### Arch Linux (AUR)

```bash
paru -S touchdesigner-linux
```

Installs everything pre-configured from the Arch User Repository. Update with `paru -Syu`.

> **Note:** the `curl` method above also works on Arch — the AUR package is an alternative for users who prefer native package management.

![Screenshot](Screenshots/Script_Preview.png)

> **Expected time:** 5–10 min. Most of it is downloading the ~300 MB Wine runner.  
> **Disk space:** ~3–5 GB final footprint. Temporary files are cleaned up automatically.

### Supported distros

Arch, CachyOS, Manjaro, Ubuntu, Mint, Pop!_OS, Fedora, RHEL, openSUSE — and derivatives.

---

## Update

### Any distro
Run the installer and choose **2 – Update**. Regenerates launcher, updates winetricks, DXVK, and UI fixes. No need to reinstall TouchDesigner or recreate the Wine prefix.

### Arch Linux (AUR)
```bash
paru -Syu
```

## Uninstall

### Any distro
Run the installer and choose **3 – Uninstall**. Remove specific versions or everything (runtime, prefix, launcher, desktop entries, backups).

### Arch Linux (AUR)
```bash
sudo pacman -Rns touchdesigner-linux
```

---

## Documentation

- [Compatibility status](docs/compatibility.md) — what works and what doesn't
- [Troubleshooting](docs/troubleshooting.md) — common issues and fixes
- [Advanced tools (toeexpand / toecollapse)](docs/advanced-tools.md)

## First launch

On the very first launch, TouchDesigner will show a license activation screen.
**The font fix is not applied yet at this stage** — you may notice missing or broken text at the bottom of the window.

This is normal and temporary:

1. First launch → license screen appears → text may look broken
2. Enter your license
3. Close TouchDesigner
4. Launch again → font fix is applied

The font patch (`wine_ui_fixes.tox`) only gets injected into project files at launch, but the license screen is part of the native exe and runs before any `.toe` is loaded.

## Useful paths

| Path | Description |
| --- | --- |
| `~/.local/bin/launch-touchdesigner.sh` | Launcher script |
| `~/.local/share/touchdesigner-linux/` | Base directory (runner, prefix, assets) |
| `~/.local/share/touchdesigner-linux/prefix/` | Wine prefix (Windows environment) |
| `~/.local/share/touchdesigner-linux/backups/` | Auto-backups of patched `.toe` files |

File icons installed by the project:

![Screenshot](Screenshots/SVG_Preview.png)

---

## Support the project

If this helps you, support maintenance via [GitHub Sponsors](https://github.com/sponsors/iswad-lab).

---

<div align="center">Built with care — <b>Iswad</b></div>
