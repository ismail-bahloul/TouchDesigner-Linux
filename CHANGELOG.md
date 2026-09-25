# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Added

- **`td-install --dpi`** — set TouchDesigner's UI scaling (LogPixels) without
  hunting for the undocumented `TD_DPI` variable: `td-install --dpi 120`
  (96/120/144/192, or `auto`). The choice is stored in `prefix/.td_dpi` and
  reapplied by the launcher, so it survives launches and updates. With no value,
  it prints the scaling currently in effect.

### Fixes

- **UI scaling is no longer a discoverability trap.** TouchDesigner ignores the
  DPI reported by Wine (`winecfg`/`winetricks` have no effect on it), and when
  the first-launch auto-detection settled on 96 DPI the launcher said nothing —
  leaving a tiny UI with no hint. The launcher now always reports the scaling it
  applies on first launch together with the command to change it, and honours
  `TD_DPI`/`.td_dpi` even on that first launch (previously `TD_DPI` was ignored
  until the second launch).

### Docs

- Documented `TD_DPI` and `td-install --dpi` (README, how-it-works,
  troubleshooting, runners, advanced-tools).
- Corrected the stale NVIDIA note in troubleshooting: NVIDIA is auto-detected by
  the launcher, and edits to the launcher are **not** preserved across updates
  (it is regenerated).

### Changed

- Removed the unreferenced `touchdesigner-launcher.py` at the repo root, which
  had drifted from the shipped AUR launcher (`dist/arch/touchdesigner-launcher.py`).

## [1.8.3] - 2026-09-12

### Fixes

- **Versioned shortcuts are no longer labelled "unknown".** When the version
  could not be read out of `TouchDesigner.exe` (missing or timed-out `strings`,
  a partially written file), detection fell back to the literal `"unknown"`, so
  an entry named "TouchDesigner unknown" could appear in the application menu.
  The version is now also read from the install path
  (`.../TouchDesigner <version>/`), which always carries it.
- **No more silent shortcut collisions.** Two installs that resolved to the
  same label produced the same `.desktop` filename, so one shortcut silently
  overwrote the other (which is why a single "unknown" entry could remain for
  two installs). Versioned shortcut file names and labels are now made unique.

## [1.8.2] - 2026-09-12

### Fixes

- **Download integrity.** `download_file()` now writes to `<dest>.part` and
  renames onto the final path only when complete, and a truncated urllib
  transfer (fewer bytes than `Content-Length`) is reported as a failure. An
  interrupted or truncated download can no longer leave a partial file where
  callers treat it as "already downloaded" (which poisoned the cache for the
  ~2 GB TouchDesigner installer).
- **Real checksum verification.** The Soda, DXVK and winetricks SHA-256
  constants were read from the environment with an empty default, and
  `verify_checksum()` returns `True` for an empty hash, so nothing was ever
  verified. They are now pinned to the actual release-asset hashes, winetricks
  is pinned to a tag (immutable URL) and its checksum is now checked too.
- **Container mode no longer drops `--no-patch`.** The launcher parsed and
  `shift`ed its flags before the distrobox re-exec, so the re-entered container
  never saw them. The original arguments are now preserved for the re-exec.
- Removed the `--fast` option, which was accepted and documented but never
  read anywhere.

### Changed

- TouchDesigner pinned to **2025.33230** (AUR `_td_ver`, regenerated
  `.SRCINFO`, and added to `FALLBACK_VERSIONS`).

## [1.8.1] - 2026-09-12

### Fixes

- **Lucida Console mono font in the Wine prefix** — TouchDesigner uses
  "Lucida Console" as its default mono font (parameter value fields, OP name
  fields, DAT tables, Textport). It ships with Windows but is not part of
  `corefonts`, so prefixes built by this tool couldn't resolve it — TD logged
  `Error Loading Default Mono Font ... Substituted with Verdana` and rendered
  mono text blank. Install and `--update` now install a mono `lucon.ttf` whose
  family is "Lucida Console" (generated from DejaVu Sans Mono, in `Assets/`)
  into `drive_c/windows/Fonts` and register it, which fixes the error and the
  blank mono text. Independent of the `wine_ui_fixes.tox` pass.

## [1.8.0] - 2026-08-27

### New

- **`touchdesigner` terminal command** — `~/.local/bin/touchdesigner` is now
  symlinked to the launcher, so `touchdesigner [project.toe]` works from any
  terminal (parity with the AUR package's `/usr/bin/touchdesigner`). It
  works from the host and inside the container, and is removed on
  uninstall. The command answers `-h`/`--help` (usage) and `-v`/`--version`
  (tool version + installed TouchDesigner versions) without launching TD,
  `--list` adds full paths, and unknown `-*` flags are rejected with a usage
  hint instead of being treated as a `.toe` path. Flags parse in a loop, so
  they combine (`touchdesigner --no-patch --verbose foo.toe`): `--no-patch`
  skips the automatic `.toe` font-fix pass, `--verbose` enables Wine debug
  output. The tool version is baked into the launcher at generation time,
  so `-v` stays in sync with the installed version after each update.
- Fix: `--exe <path>` on the launcher never worked — a stray `]` in the
  template (`[ -n "$2" ]]`) broke argument parsing at runtime (invisible to
  `bash -n`). Both `--exe <path>` and `--exe=<path>` now parse correctly.

- **Container mode (Distrobox / Podman)** — `td-install --container <action>`
  runs the whole install inside an isolated container, leaving the host
  untouched: no sudo, no 32-bit repository setup, works on immutable distros
  and SteamOS. First run creates a `touchdesigner-linux` container
  (Ubuntu 24.04, NVIDIA auto-detected via `--nvidia`, `label=disable` on
  SELinux hosts) and re-executes the requested action inside it.
  - The launcher, desktop shortcuts and `.toe` associations work from the
    host through a self re-entering shim (guarded by
    `DISTROBOX_ENTER_PATH`), and the Wine prefix stays in the shared
    `$HOME`.
  - `--container-create` recreates the container; `--container-remove`
    deletes it.
  - `TD_CONTAINER_NAME` / `TD_CONTAINER_IMAGE` env vars override the
    defaults.
  - New [docs/container.md](docs/container.md) with GPU notes and known
    limitations.
- `--diagnose` now reports container-mode status (distrobox installed,
  backend, container state, inside/outside).
- **CodeMeter runtime installation without msiexec** —
  `td-install --codemeter install <path>` extracts a CodeMeter Runtime
  installer natively on the host and lays the files into the Wine prefix,
  bypassing the Wibu MSI that hangs under Wine's `msiexec`. Handles both
  Inno setups (innoextract) and WiX/MSI bundles (7z) — the official 7.60d
  download is a WiX bundle. Also copies the Wibu system DLLs
  (`WibuCm64.dll`/`cpsrt.dll`) into the prefix's system directories.
  First real test (runtime 7.60d): `cpsrt.dll` loads fine under Wine 9.0
  (the `c000007b` failure only affects 8.41a/9.10), but `CodeMeter.exe`
  still stalls during startup — see [docs/codemeter.md](docs/codemeter.md)
  for the updated status and next steps.

### Fixes

- The one-liner (`curl | bash`) now works in minimal environments without
  `git` (e.g. a fresh distrobox container ships curl/wget but not git):
  `install.sh` falls back to downloading the installer tarball. Its
  `/dev/tty` reconnect also tests the open instead of the node's existence,
  so containers without a controlling terminal no longer error.
- `xdg-utils` and `file` added to all distro package lists — the editor
  bridge (`winebrowser.exe → xdg-open`) and DXVK/winetricks both shell out
  to those commands, and minimal containers ship neither. Found by the
  first real container-mode install.
- `td-install --container install` (bare action word) now works: argparse
  has no positional actions, so a leading `install`/`update`/`uninstall`
  (optionally after `--container`/`--container-create`) is translated to
  the flag form. `--version` is also handled before the container bootstrap
  now, so it answers without entering the container.
- `tests/test_distrobox.sh` rewritten for the current flow (the old one
  referenced the long-gone `python-rewrite` branch).
- **DXVK installs were silently skipped** on prefixes where Wine had already
  copied its builtin wined3d DLLs into `system32`: the "already installed"
  probe matched any PE32 DLL, so DXVK never activated and TouchDesigner ran
  on wined3d. The probe now rejects Wine-built DLLs (`file` → "for WINE"),
  and the DLL overrides are always (re)registered so Wine loads the DXVK
  copies from `system32`. DXVK bumped to **2.7.1**.
- **Syphon/Spout Out TOP works** with a real DXVK install (shared-texture
  path); with wined3d it errors with "Unable to share DirectX Texture".
  DXVK 3.x is not used: it crashes on the Spout node under Wine 9.0.

## [1.7.0] - 2026-08-20

### New

- **CodeMeter dongle / network-shared license tooling** (`td-install --codemeter`).
  Detects the runtime in the Wine prefix, manages the client's Server Search
  List (`add-server` / `remove-server` / `servers`) via Wibu's official
  `cmu32 --add-server` / `cmu.exe` tools with a registry fallback, and the
  launcher auto-starts `CodeMeter.exe` when installed. The **server side**
  (native Linux daemon or the official `docker-codemeter` image, UDP/TCP
  22350) is validated; the **client side under Wine is currently blocked**
  (the CodeMeter service won't start; see
  [docs/codemeter.md](docs/codemeter.md) for details and test results).
- GitHub issue templates (bug report + feature request).

### Fixes

- Launcher failures are logged to `logs/launcher.log` and surfaced with a
  desktop notification instead of failing silently on icon clicks.
- SteamOS is auto-detected and its read-only root filesystem is disabled
  before pacman steps (no more manual `steamos-readonly disable`).
- openSUSE: zypper repos are refreshed before package installation.
- Headless mode attempts `wineboot` in SSH/CI environments (fixes
  winetricks/vcrun when there is no display).
- Interactive menu banner showed a hardcoded stale version (`v1.4`); it now
  shows the real package version.
- **AUR: licenses preserved across updates.** The AUR launcher's ProgramData
  refresh no longer touches `ProgramData/Derivative/` (the user's activated
  `ins*.dat`), and the license is backed up before wineboot/package ProgramData
  copies and restored after. This addresses a report that a `paru -Syu`
  (v1.6 → v1.6.2) update changed the System Code and consumed a second
  activation; the package ProgramData copy was the only code path that
  touched the license files, so it is now excluded entirely.

### Docs

- New [docs/codemeter.md](docs/codemeter.md): dongle & network license guide
  (server setup on Windows/Linux/Docker, firewall, same-machine caveats).
- [docs/compatibility.md](docs/compatibility.md): added CodeMeter licensing
  status row.
- [docs/how-it-works.md](docs/how-it-works.md): CodeMeter runtime section.
- Runner test findings recorded (Wine 11 / Soda 11 hang, GE-Proton 11).
- CI notes for maintainers.

### CI

- Weekly smoke test runs under `xvfb` so MS installers (vcrun2022) can create
  windows; verifies `TouchDesigner.exe` is actually installed; headless
  wineboot fallback; AUR-launcher/version drift guards in the test suite.

## [1.6.2] - 2026-08-12

> Tagged and shipped to the AUR, but never announced as a GitHub release;
> these changes are included in 1.7.0 for anyone upgrading from v1.6.

### Fixes

- **Version-aware font-fix re-patch.** `wine_ui_fixes.tox` injections are now
  fingerprinted; when a new fix ships, already-patched projects are re-patched
  automatically instead of keeping a stale fix. Stale `.toc` entries are also
  deduped so re-patching can't corrupt a collapsed `.toe`.
- **NVIDIA driver guard.** The launcher no longer forces `NVIDIA_only`; it
  auto-detects the dGPU via `nvidia-smi -L` and only sets Prime offload vars
  when the driver actually works (fixes black screens on broken/missing
  NVIDIA drivers).
- **AUR launcher** now auto-patches `.toe` files with the font fix, matching
  the curl-install launcher.
- Full uninstall warns before deleting your TouchDesigner license activation
  (issue #26).
- `safe_rm` hardened with a blocklist protecting `/usr`, `/etc`, `/home` and
  other system paths from accidental deletion.

### Maintenance

- `tdascode/` (experimental .toe editing) removed from the repo; it lives on
  as its own project, [TDAsCode](https://github.com/ismail-bahloul/TDAsCode).
