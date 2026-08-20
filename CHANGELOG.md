# Changelog

All notable changes to this project are documented here.

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
  as its own project, [TDAsCode](https://github.com/iswad-lab/TDAsCode).
