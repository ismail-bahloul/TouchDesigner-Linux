# TouchDesigner-Linux

Run TouchDesigner on Linux via Wine — fully automated installation.

👉 [Roadmap & planned features](ROADMAP.md)

---

## Quick Install

```bash
curl -sSL https://raw.githubusercontent.com/iswad-lab/TouchDesigner-Linux/main/install.sh | bash
```

**Prerequisite:** NVIDIA users should install their GPU driver first, then reboot.

### Options

| Command | Description |
| --- | --- |
| `curl ... \| bash` | Normal install (graphical session required) |
| `curl ... \| bash -s -- -H` | Headless install (SSH, no display) |
| `DEBUG=true curl ... \| bash` | Verbose logs for issue reports |

The script detects your distro, installs required packages, sets up a Wine environment, downloads and installs TouchDesigner. It supports **multiple versions side-by-side**, auto-patches `.toe` files for font fixes, and creates desktop shortcuts.

> **Expected time:** 5–10 min. Most of it is downloading the ~300 MB Wine runner.  
> **Disk space:** ~3–5 GB final footprint. Temporary files are cleaned up automatically.

### Supported distros

Arch, CachyOS, Manjaro, Ubuntu, Mint, Pop!_OS, Fedora, RHEL, openSUSE — and derivatives.

---

## Update

Run the installer and choose **2 – Update**. Regenerates launcher, updates winetricks, DXVK, and UI fixes. No need to reinstall TouchDesigner or recreate the Wine prefix.

## Uninstall

Run the installer and choose **3 – Uninstall**. Remove specific versions or everything (runtime, prefix, launcher, desktop entries, backups).

---

## Documentation

- [Compatibility status](docs/compatibility.md) — what works and what doesn't
- [Troubleshooting](docs/troubleshooting.md) — common issues and fixes
- [Advanced tools (toeexpand / toecollapse)](docs/advanced-tools.md)

## Useful paths

| Path | Description |
| --- | --- |
| `~/.local/bin/launch-touchdesigner.sh` | Launcher script |
| `~/.local/share/touchdesigner-linux/` | Base directory (runner, prefix, assets) |
| `~/.local/share/touchdesigner-linux/prefix/` | Wine prefix (Windows environment) |
| `~/.local/share/touchdesigner-linux/backups/` | Auto-backups of patched `.toe` files |

---

## Support the project

If this helps you, support maintenance via [GitHub Sponsors](https://github.com/sponsors/iswad-lab).

---

<div align="center">Built with care — <b>Iswad</b></div>
