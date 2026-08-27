# Changelog

All notable changes to this project are documented here.

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
