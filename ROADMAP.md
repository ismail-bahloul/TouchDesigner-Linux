# Roadmap

Planned improvements and future directions for TouchDesigner-Linux.  
*This is a living document — priorities may shift based on feedback and contributions.*

---

## 🔥 High Priority

### 1. Multiple Wine runners (Wine-GE / Proton)

Currently locked to **Soda Wine 9.0-1**. Wine-GE (GloriousEggroll) and Proton-GE often deliver better GPU performance and fewer bugs with graphics-heavy Windows apps. Allow users to pick their runner — or different runners per installed TouchDesigner version.

### 2. Diagnostic / Health check (`--diagnose`)

A single command that checks everything at once:
- Installed TD versions
- Wine runner + version
- GPU drivers (NVIDIA / Vulkan / OpenGL)
- Missing 32-bit dependencies
- Patched vs unpatched DLLs
- Disk space
- Wine prefix health

Users could paste the full output into an issue — saving multiple rounds of back-and-forth debugging.

### 3. Containerized mode (Distrobox / Docker)

Some users struggle with 32-bit dependencies or `noexec` mounts on `/home`. An optional Distrobox (Podman/Docker) mode would sidestep these issues entirely and work on **any distro** without touching the host system.

---

## 📦 Nice to have

### 4. Richer version management

- Set a **default version** (when double-clicking a `.toe` file)
- Menu to **switch** between installed versions without reinstalling
- **Update** TD to a newer version without re-downloading everything

### 5. Auto-detect NVIDIA + Optimus switching

Currently requires `USE_NVIDIA_DGPU=Y` manually. Could detect NVIDIA + Intel/AMD hybrid setups automatically and offer config on first launch.

### 6. Distribution packages (AUR / Flatpak)

**AUR package** — Arch and its derivatives (CachyOS, EndeavourOS, Manjaro) are popular among creative coders. An AUR PKGBUILD would mean `yay -S touchdesigner-linux` with automatic updates.

**Flatpak** — Distro-agnostic, sandboxed, one command install. Requires more work around GPU driver access and sandboxing.

---

## 🧹 Polish

### 7. Toggle for each patch (IDS, Engine COMP, WebRender)

Currently the IDS Peak SDK DLLs are patched automatically. If someone ever needs to use IDS cameras under Wine (or if support improves), each patch should be togglable individually. Same applies to Engine COMP and WebRender fixes.

### 8. Auto-cleanup of old versions

Installing 5 versions of TouchDesigner adds up to ~10 GB. A menu entry to "remove versions X, Y, Z" with estimated freed space would be a nice quality-of-life improvement.

---

## 💡 Long-term: Python rewrite

The current `install.sh` is **3340 lines of bash**. As features grow, this is becoming hard to maintain. A Python rewrite would bring:

- Modular structure (small files, clear responsibilities)
- Proper CLI (argparse) for free
- Error handling that doesn't rely on `|| exit 1`
- Easier contributions from the community
- Testability (pytest)

The installer already depends on `python3` (IDS patch, URI decoding), so this adds **zero** new requirements for users.

---

*Have a suggestion? [Open an issue](https://github.com/iswad-lab/TouchDesigner-Linux/issues/new) or upvote existing ones — feedback shapes the roadmap.*
