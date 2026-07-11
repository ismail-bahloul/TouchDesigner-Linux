# Roadmap

Planned improvements and future directions for TouchDesigner-Linux.
This is a living document — priorities may shift based on feedback and contributions.

---

## High Priority

### 1. Multiple Wine runners (Wine-GE / Proton)

Currently locked to **Soda Wine 9.0-1**. Wine-GE (GloriousEggroll) and Proton-GE often deliver better GPU performance and fewer bugs with graphics-heavy Windows apps. Allow users to pick their runner — or different runners per installed TouchDesigner version.

**Known Proton 10 issue:** TD hangs due to mimalloc + DWrite incompatibility. Fix: set `MIMALLOC_DISABLE_REDIRECT=1`. Must be auto-applied when using Proton runners.

**Spout2PW:** Bridges Spout2 video from Windows apps under Proton to PipeWire on Linux. Useful for OBS capture. AUR package: `spout2pw-bin`. Worth documenting or integrating when Spout output is needed.

### 2. Diagnostic / Health check (`--diagnose`)

✅ **Done!** Run `td-install --diagnose` to check OS, GPU, Vulkan, disk space, Wine, installed TD versions, and IDS patch status in one go.

### 3. Containerized mode (Distrobox / Docker)

Some users struggle with 32-bit dependencies or `noexec` mounts on `/home`. An optional Distrobox (Podman/Docker) mode would sidestep these issues entirely and work on any distro without touching the host system.

### 4. Pip wrapper / Python package manager

Recent TouchDesigner versions now ship pip directly on Windows (`python.exe -m pip`). Since we run TD through Wine, the same pip is available to us. (Thanks to community testing for confirming this.)

Goal: wrap `wine64 python.exe -m pip install <package>` into a simple `td-install --pip` command, so users can install packages (numpy, opencv, requests, etc.) into TD's Python environment without manually juggling Wine paths.

### 5. Watchdog / systemd service

Systemd user service that launches TD with auto-restart on crash and logs to journald. Makes TD viable for 24/7 installations (exhibitions, kiosks, servers).

---

## Under Consideration

### 6. Richer version management

Partially done — **multi-version side-by-side**, version picker on install, versioned shortcuts, and `--exe` flag work. Still missing:

- Set a default version for double-clicking `.toe` files
- Menu to switch between installed versions without reinstalling
- Update TD to a newer version without re-downloading everything

### 7. Auto-detect NVIDIA + Optimus switching

Currently requires `USE_NVIDIA_DGPU=Y` manually. Could detect NVIDIA + Intel/AMD hybrid setups automatically and offer config on first launch.

### 8. Distribution packages (Flatpak)

**AUR package** — ✅ **Done!** `paru -S touchdesigner-linux` with automatic updates.

**Flatpak** — Distro-agnostic, sandboxed, one-command install. Requires more work around GPU driver access and sandboxing.

### 9. Toggle for each patch (IDS, Engine COMP, WebRender)

Currently the IDS Peak SDK DLLs are patched automatically. If someone ever needs to use IDS cameras under Wine (or if support improves), each patch should be togglable individually. Same applies to Engine COMP and WebRender fixes.

### 10. Auto-cleanup of old versions

Mostly done — the uninstall menu (`td-install --uninstall`) already lets you select and remove specific versions, and backups are auto-cleaned after 30 days.

Still missing: show estimated freed space per version before removal.

### 11. Config file

Centralise user preferences in `~/.config/touchdesigner-linux/config.toml`: default runner, patch toggles, NVIDIA mode, default TD version. Reduces need for CLI flags on every command.

### 12. Headless / kiosk mode

`td-install --headless project.toe` — launch TD without GUI. Useful for automated rendering, server deployment, and export pipelines. Combined with the watchdog and container mode, unlocks serious production use.

### 14. Dedicated fix documentation page

Create a standalone page (or section) explaining each patch applied by the installer: why `ids_peak_ipl.dll` needs its entrypoint zeroed, why Soda Wine is used over Proton, how the font fix works, LogPixels DPI, wineboot behavior, etc. Target audience: users who prefer manual setup but want to understand what the script does before running it.

`td-install --expand`, `--collapse`, `--patch-toe` as stable CLI commands for version-controlling and manipulating `.toe` files outside TD. Enables Git-based workflows and automated testing.

---

## Long-term

- ~~Python rewrite~~ ✅ **Done!** The installer now uses modular Python (`td-install`, `td_lib/`).

---

*Have a suggestion? [Open an issue](https://github.com/iswad-lab/TouchDesigner-Linux/issues/new) or upvote existing ones — feedback shapes the roadmap.*
