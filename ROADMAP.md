# Roadmap

Planned improvements and future directions for TouchDesigner-Linux.
This is a living document — priorities may shift based on feedback and contributions.

---

## High Priority

### 1. Multiple Wine runners (Wine-GE / Proton)

Currently locked to **Soda Wine 9.0-1** — still the recommended default. See [`docs/runners.md`](docs/runners.md) for the full comparison (8 runners tested).

**Key findings:**
- **Wine 9.x** (Soda, TkG, vanilla) → fully compatible
- **Wine 10.x** (GE-Proton10) → works with `wine_ui_fixes.tox` but fonts need correction
- **Wine 11.x** → Mutter workaround in Valve fork breaks window creation on KWin
- **Reason:** Soda disables Wine Staging patches (`_use_staging="false"`). Staging introduced the DWrite/mimalloc bug in Wine 10, and Valve added a Mutter workaround in Wine 11.

**Known Proton 10 issue:** TD hangs due to mimalloc + DWrite incompatibility. Fix: set `MIMALLOC_DISABLE_REDIRECT=1`. Must be auto-applied when using Proton runners.

**Custom wine-tkg runner explored and abandoned (for now):** A custom Wine 11 TkG build with GE-Proton's `d2d1.dll`/`dwrite.dll` swapped in (to get GE-Proton's more complete D2D — ~4715 functions vs wine-tkg's own ~700-837) was built and tested. It has a reproducible hang: `d2d_device_context_draw_glyph_run_bitmap` fails with `E_OUTOFMEMORY` rendering Bitmap-mode text, looping forever. Root cause: mixing Unix-side binaries and PE-side DLLs from two different Wine builds crosses Wine's internal PE↔Unix ABI boundary, and the halves don't agree on protocol/versions — a DLL swap alone can't fix this; it would need building both halves from the same source tree. A pure GE-Proton11 build (no mixing) rendered fonts correctly with no D2D hang, but hit a separate, not-yet-root-caused crash once tested with the full GPU-hybrid launcher path (possibly the known Wine Staging `c0000005` in `d3d11_swapchain_Present`). Not pursued further; Soda remains the default until this is isolated with more time.

**Spout2PW:** Bridges Spout2 video from Windows apps under Proton to PipeWire on Linux. Useful for OBS capture. AUR package: `spout2pw-bin`. Worth documenting or integrating when Spout output is needed.

**In progress: moving TD to a newer Wine build.** The project is pinned to Soda 9.0 because it is the only runner that is fully compatible today. A newer Wine build would also unlock **DXVK 3.x**, which currently crashes on the Syphon/Spout Out TOP under Wine 9.0 (DXVK stays on 2.7.1 for v1.8). This is also the leading candidate to unblock the CodeMeter client (see #21).

### 2. Diagnostic / Health check (`--diagnose`)

✅ **Done!** Run `td-install --diagnose` to check OS, GPU, Vulkan, disk space, Wine, installed TD versions, and IDS patch status in one go.

### 3. Containerized mode (Distrobox / Docker)

✅ **Done!** (v1.8) `td-install --container <action>` runs the whole
TouchDesigner-Wine environment inside an isolated Distrobox container
(podman/docker backend): no host modifications, no sudo, no 32-bit repo
setup — works on any distro, including immutable ones and SteamOS. The
launcher, desktop shortcuts and `.toe` associations work from the host via
a self re-entering shim, and the Wine prefix stays in the shared `$HOME`.
GPU passthrough is automatic (NVIDIA via `--nvidia`).

Remaining known limits: a `noexec` `$HOME` needs a custom `TD_BASE_DIR`,
`.toe` files outside `$HOME` aren't visible inside the container. Battle-
tested with **Ubuntu 24.04 and Fedora 40** images (v1.8); first container
run auto-accepts the image pull (`--yes`), and `TD_CONTAINER_NO_NVIDIA=1`
skips the slow distrobox `--nvidia` init. See [docs/container.md](docs/container.md).

### 4. Pip wrapper / Python package manager

✅ **Done!** (v1.5) `td-install --pip install <package>` wraps `wine64 python.exe -m pip install` with proper Wine environment setup.

Usage:
```bash
td-install --pip install numpy
td-install --pip install torch --index-url https://download.pytorch.org/whl/cpu
td-install --pip list
td-install --pip uninstall <package>
```

**Known issue:** OpenMP crash (`GetNumaNodeProcessorMaskEx` not implemented) when importing torch. **Fixed** with `KMP_AFFINITY=disabled` (auto-set in launcher). CPU-only torch 2.13.0 confirmed working on Wine TkG. See [issue #20](https://github.com/ismail-bahloul/TouchDesigner-Linux/issues/20).

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

### 13. CI/CD pipeline tools

`td-install --expand`, `--collapse`, `--patch-toe` as stable CLI commands for version-controlling and manipulating `.toe` files outside TD. Enables Git-based workflows and automated testing.

### 14. Dedicated fix documentation page

✅ **Done!** See [docs/how-it-works.md](docs/how-it-works.md). Explains each patch applied by the installer: why `ids_peak_ipl.dll` needs its entrypoint zeroed, why Soda Wine is used over Proton, how the font fix works, LogPixels DPI, wineboot behavior, and more. Target audience: users who prefer manual setup but want to understand what the script does before running it.

---

### 15. Native external editor support

✅ **Done!** (v1.5) TouchDesigner now opens Text DATs (Ctrl+E) in the user's default Linux editor via `winebrowser.exe` -> `xdg-open`. Configured automatically in `pref.txt` (`dats.texteditor`). Change editor with `xdg-mime default <editor.desktop> text/plain`.

### 16. Auto-detect display DPI

✅ **Done!** (v1.5) The launcher now reads `Xft.dpi` from the display server on first launch and applies the correct LogPixels value to Wine (96/120/144/192). No more hardcoded 120 DPI forced on every launch. Override with `TD_DPI=96 touchdesigner`.

### 17. License preservation on install/reinstall

✅ **Done!** (v1.5) Bug fix — the installer's `commonappdata/` was overwriting the user's activated license files (`ins2.dat`, `ins5.dat`) on every fresh install, reinstall, or version update. Now backs up `ProgramData/Derivative/` before copying and restores it after.

### 18. Code review bug fixes

✅ **Done!** (v1.5) Systematic code review of all `td_lib/` modules found and fixed:
- Missing `import re` causing `NameError` on uninstall (`cleanup.py`)
- Winetricks log read after file deletion — "already installed" message was dead code (`wine.py`)
- Unreachable `raise SystemExit(1)` after `_handle_wineboot_error` (`wine.py`)
- Guard against empty version list before `versions[0]` access (`install.py`)

### 19. Dynamic font-fix detection (`wine_ui_fixes.tox` v2)

✅ **Done!** The old fix hardcoded ~23 specific `/ui` paths in a lookup table (`op(i)` + silent skip if the path no longer exists in a newer TD version). Rewritten to scan dynamically instead:

- Scans `/ui` (TD's own interface — not reachable via `findChildren()` from `/`, has to be scanned separately with `includeUtility=True`) and `/` (the regular project tree, catches third-party palette components like kantanMapper) for Text TOPs not already in `scalable` mode, and converts them.
- Fixed on genuine project start (`onStart()`) and via a working **Fix Now** button (a proper Parameter Execute DAT — the previous version's pulse-parameter-via-expression wiring didn't work).
- **Verified against Soda specifically** (not just GE-Proton/Tact, which is where earlier testing happened): an intermediate version left `bitmap` untouched in `/ui`, assuming it already rendered correctly there (true under GE-Proton, where ~80% of `/ui` elements are `bitmap` and fine). Under Soda, several `/ui` elements (the timeline attribute fields — FPS, Start, End, Tempo) default to `bitmap` and are *broken* there, unlike under GE-Proton. The original hardcoded table forced these unconditionally regardless of starting state, which is why it worked where the conditional rewrite didn't. Fixed by converting anything not already `scalable` (`automatic`/`polygon`/`stroke`/`bitmap`) everywhere, matching the original's unconditional behavior instead of trying to guess which starting state is "safe" per-runner.

### 20. TD-as-Code — programmatic .toe manipulation

**Moved out of this repo.** What started as an MVP here (built and used to verify the font fix above, every edit round-tripped through the real `toeexpand`/`toecollapse` binaries) grew into its own standalone project, [TDAsCode](https://github.com/ismail-bahloul/TDAsCode) — it no longer depends on `td_lib` and has its own env-detection layer. The two correctness bugs originally found here (a hardcoded 32-byte `.text` header that's actually variable-length, and incorrect `.toc` regeneration on `write()`) are fixed and verified there, along with a from-scratch node-file write-order corruption bug found on a real production project. It also grew a second, unrelated component: a live TCP bridge for controlling a *running* TD instance in real time, complementary to the offline `.toe` editing.

This repo's `td_lib` and installer are unaffected — the historical code that lived in `tdascode/` here (last on the `feature/tdascode`/`dev` branches) is superseded by that repo and won't be revived here.

### 21. CodeMeter dongle / network license support

**Partial — tooling shipped (`td-install --codemeter`), client blocked.**

**Done:** detection of the runtime in the prefix, Server Search List management (`cmu32 --add-server` / `cmu.exe` / registry), launcher auto-start, a validated **server-side** setup (native Linux daemon or the official `docker-codemeter` image, port 22350), and an **msiexec-free runtime install** (`td-install --codemeter install <path>`: native extraction via innoextract/7z, handles the WiX-bundled 7.60d download, copies the Wibu system DLLs).

**Blocked (tested 2026-08, Wine 9.0 TkG/Soda):** the Windows CodeMeter service (`CodeMeter.exe`) still does not come up. Runtimes 8.41a/9.10 crash on load (protected `cpsrt.dll`, `c000007b`); runtime **7.60d** loads fine but the service **stalls during startup** (single thread, never opens port 22350). Until `CodeMeter.exe` runs, TouchDesigner under Wine cannot borrow network-shared licenses. Direct USB dongle passthrough remains out of scope. See the open feature request and [docs/codemeter.md](docs/codemeter.md).

**Next test to try:** a newer Wine build (10/11 or GE-Proton) with runtime 7.60d — the stall looks Wine-version dependent. Also worth upstreaming both failures (7.60d stall + 9.10 `cpsrt.dll` loader error) to WineHQ.

## Long-term

- ~~Python rewrite~~ ✅ **Done!** The installer now uses modular Python (`td-install`, `td_lib/`).

---

*Have a suggestion? [Open an issue](https://github.com/ismail-bahloul/TouchDesigner-Linux/issues/new) or upvote existing ones — feedback shapes the roadmap.*
