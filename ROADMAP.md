# Roadmap

Planned improvements and future directions for TouchDesigner-Linux.
This is a living document — priorities may shift based on feedback and contributions.

---

## High Priority

### 1. Multiple Wine runners (Wine-GE / Proton)

Currently locked to **Soda Wine 9.0-1**. Wine-GE (GloriousEggroll) and Proton-GE often deliver better GPU performance and fewer bugs with graphics-heavy Windows apps. Allow users to pick their runner — or different runners per installed TouchDesigner version.

### 2. Diagnostic / Health check (`--diagnose`)

✅ **Done!** Run `td-install --diagnose` to check OS, GPU, Vulkan, disk space, Wine, installed TD versions, and IDS patch status in one go.

### 3. Containerized mode (Distrobox / Docker)

Some users struggle with 32-bit dependencies or `noexec` mounts on `/home`. An optional Distrobox (Podman/Docker) mode would sidestep these issues entirely and work on any distro without touching the host system.

---

## Under Consideration

### 4. Richer version management

Partially done — **multi-version side-by-side**, version picker on install, versioned shortcuts, and `--exe` flag work. Still missing:

- Set a default version for double-clicking `.toe` files
- Menu to switch between installed versions without reinstalling
- Update TD to a newer version without re-downloading everything

### 5. Auto-detect NVIDIA + Optimus switching

Currently requires `USE_NVIDIA_DGPU=Y` manually. Could detect NVIDIA + Intel/AMD hybrid setups automatically and offer config on first launch.

### 6. Distribution packages (Flatpak)

**AUR package** — ✅ **Done!** `paru -S touchdesigner-linux` with automatic updates.

**Flatpak** — Distro-agnostic, sandboxed, one-command install. Requires more work around GPU driver access and sandboxing.

### 7. Toggle for each patch (IDS, Engine COMP, WebRender)

Currently the IDS Peak SDK DLLs are patched automatically. If someone ever needs to use IDS cameras under Wine (or if support improves), each patch should be togglable individually. Same applies to Engine COMP and WebRender fixes.

### 8. Auto-cleanup of old versions

Installing multiple versions of TouchDesigner adds up quickly. A menu entry to remove specific versions with estimated freed space would be a nice quality-of-life improvement.

---

## Long-term

- ~~Python rewrite~~ ✅ **Done!** The installer now uses modular Python (`td-install`, `td_lib/`).

---

*Have a suggestion? [Open an issue](https://github.com/iswad-lab/TouchDesigner-Linux/issues/new) or upvote existing ones — feedback shapes the roadmap.*
