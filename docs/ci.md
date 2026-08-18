# CI notes

Notes for maintainers on the GitHub Actions setup (`.github/workflows/tests.yml`), especially the parts that aren't obvious from the workflow file alone.

## Jobs

- **`Tests` (push/PR)** — static tests only (`tests/test_static.py`). No Wine, no sudo, fast, always green if the code is sane.
- **`distro-detect`** — runs `td_lib.distro.detect_distro()` + static tests inside 5 distro containers (Ubuntu 22/24, Fedora, Arch, openSUSE). Catches package-name/manager drift.
- **`weekly-smoke`** — the only job that runs the *real* installer (downloads Soda Wine, winetricks, DXVK, TouchDesigner) on a bare `ubuntu-latest` runner. Runs on the Monday cron and on manual `workflow_dispatch`. This is the flaky one — see below.

## Headless Wine gotchas (found 2026-08-17)

The smoke job needed three fix commits in a row before it passed. Root causes, so the next runner change doesn't rediscover them the slow way:

1. **A skipped `wineboot --init` leaves winetricks broken.** The install path used to skip prefix initialization entirely in headless mode ("requires graphical session"). But winetricks verbs like `vcrun2022` need an initialized prefix — skipping it produced `Winetricks failed (vcrun2022)` with no further detail. Fix (`td_lib/wine.py`, `setup_wine_prefix`): attempt `wine64 wineboot --init` even when headless, with a timeout and a graceful fallback (skip + warn) if it genuinely can't run.

2. **MS redistributable installers need a real display, not just an initialized prefix.** `vcrun2022` runs an actual Windows installer UI under the hood; with no X server at all it still fails. Fix: wrap the install step in `xvfb-run -a` so Wine has a virtual display to create windows on.

3. **Under `xvfb-run`, stdin is not a TTY.** Once a display existed, the install crashed with `termios.error: (25, 'Inappropriate ioctl for device')` — any code path that calls `input()` blows up because there's no real terminal attached. Fix: pass `--non-interactive` to `td-install` in CI so it never prompts.

4. **apt's Wine packages need `libunwind8` explicitly.** `wine64`/`wine32` from Ubuntu's repos don't pull this in as a dependency, but Wine misbehaves without it. Install `libunwind8` and `libunwind8:i386` alongside `wine64 wine32`.

Net effect, in order: `wineboot --init` (headless-safe) → `xvfb-run -a` → `--non-interactive` → `libunwind8`. Skipping any one of these reproduces one of the three failures above.

## Debugging a red `weekly-smoke` run

The raw log is mostly download progress-bar spam (`... MB/s` lines). Skip straight to the actual error:

```bash
gh run view <run-id> --repo iswad-lab/TouchDesigner-Linux --log-failed \
  | grep -iE "error|fail|traceback|conflict" | grep -v "MB/s"
```
