# TouchDesigner-Linux

[![Tests](https://img.shields.io/github/actions/workflow/status/ismail-bahloul/TouchDesigner-Linux/tests.yml?label=Tests)](https://github.com/ismail-bahloul/TouchDesigner-Linux/actions)
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
curl -sSL https://raw.githubusercontent.com/ismail-bahloul/TouchDesigner-Linux/main/install.sh | bash
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
DEBUG=true curl -sSL https://raw.githubusercontent.com/ismail-bahloul/TouchDesigner-Linux/main/install.sh | bash
```

**Install Python packages into TD:**
```bash
td-install --pip install numpy
td-install --pip install torch --index-url https://download.pytorch.org/whl/cpu
td-install --pip list
```

**Use a license dongle / network-shared license (CodeMeter):**
```bash
td-install --codemeter status          # runtime installed & running?
td-install --codemeter add-server 192.168.1.15   # add a license server to the search list
# No runtime yet? Install one without msiexec (any version, e.g. to test):
td-install --codemeter install /path/to/CodeMeterRuntime.exe
```
> ⚠️ The CodeMeter **server side** works (native Linux / Docker). The **client
> under Wine is still blocked** while Wibu's protected `cpsrt.dll` won't load
> under Wine 9.0 (tested with runtimes 8.41a and 9.10) — `--codemeter install`
> makes it easy to try other runtime versions. See
> [docs/codemeter.md](docs/codemeter.md) for status & test results.

---

## Container mode (Distrobox)

**Don't want to touch your host system?** Run the whole install inside an
isolated Distrobox container (podman/docker) — no sudo, no 32-bit
repository setup, works on any distro including immutable/SteamOS:

```bash
td-install --container install
# or straight from the one-liner:
curl -sSL https://raw.githubusercontent.com/ismail-bahloul/TouchDesigner-Linux/main/install.sh | bash -s -- --container
```

First run creates a `touchdesigner-linux` container (Ubuntu 24.04), then
installs everything inside it. The launcher, desktop shortcuts and `.toe`
associations still work from the host (they re-enter the container
automatically), and the Wine prefix stays in your `$HOME`.

```bash
td-install --container update          # same as above for other actions
TD_CONTAINER_IMAGE=fedora:40 td-install --container-create install   # custom image
```

See [docs/container.md](docs/container.md) for details, GPU notes and
limitations.

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
- [CodeMeter dongles & network licenses](docs/codemeter.md) — use a license dongle over the LAN
- [Advanced tools](docs/advanced-tools.md) — toeexpand / toecollapse
- [CI notes](docs/ci.md) — maintainer notes on the GitHub Actions setup, headless Wine gotchas

### Useful paths

| Path | Description |
| --- | --- |
| `~/.local/bin/touchdesigner` | Terminal command (launch TD, open `.toe` files) |
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
- Support via [GitHub Sponsors](https://github.com/sponsors/ismail-bahloul)

---

<div align="center">Built with care - <b>Iswad</b></div>
