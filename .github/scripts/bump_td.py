#!/usr/bin/env python3
"""Detect a new TouchDesigner release and bump the pinned version.

Used by .github/workflows/bump-td.yml. The tool itself already resolves the
latest version online at install time; this keeps the *packaging* in sync:

- ``dist/arch/PKGBUILD``   -> ``_td_ver`` (and ``pkgrel++``)
- ``dist/arch/.SRCINFO``   -> regenerated lines for the new source
- ``td_lib/touchdesigner.py`` -> newest entry in ``FALLBACK_VERSIONS``

Exit code is always 0 (a scheduled job must not fail just because there is
nothing to do). The outcome is reported through ``$GITHUB_OUTPUT``:
``changed=true|false`` and ``version=<new>``.

Testing overrides (never set in CI):
- ``BUMP_TD_VERSION``            force the target version
- ``BUMP_TD_SKIP_INSTALLER_CHECK=1``  skip the installer HEAD probe
"""

import os
import re
import sys
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PKGBUILD = os.path.join(REPO, "dist", "arch", "PKGBUILD")
SRCINFO = os.path.join(REPO, "dist", "arch", ".SRCINFO")
TD_PY = os.path.join(REPO, "td_lib", "touchdesigner.py")

VERSION_RE = re.compile(r"20\d{2}\.\d{4,6}")


def gh_output(**kv: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        for key, value in kv.items():
            print(f"{key}={value}")
        return
    with open(path, "a") as f:
        for key, value in kv.items():
            f.write(f"{key}={value}\n")


def finish(changed: bool, version: str = "") -> int:
    gh_output(changed="true" if changed else "false", version=version)
    return 0


def latest_version() -> str | None:
    forced = os.environ.get("BUMP_TD_VERSION", "").strip()
    if forced:
        return forced
    sys.path.insert(0, REPO)
    from td_lib.touchdesigner import fetch_available_versions

    versions = fetch_available_versions()
    return versions[0] if versions else None


def installer_exists(version: str) -> bool:
    if os.environ.get("BUMP_TD_SKIP_INSTALLER_CHECK") == "1":
        return True
    url = f"https://download.derivative.ca/TouchDesigner.{version}.exe"
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status == 200
    except Exception as e:  # noqa: BLE001 - any failure means "don't bump"
        print(f"Installer HEAD probe failed for {version}: {e}")
        return False


def main() -> int:
    latest = latest_version()
    if not latest:
        print("No TouchDesigner versions found; skipping.")
        return finish(False)
    if not VERSION_RE.fullmatch(latest):
        print(f"Unexpected version format {latest!r}; skipping.")
        return finish(False)

    pkgbuild = open(PKGBUILD).read()
    m = re.search(r"^_td_ver=([\w.]+)", pkgbuild, re.M)
    if not m:
        print("Could not parse _td_ver from PKGBUILD; skipping.")
        return finish(False)
    current = m.group(1)

    if latest == current:
        print(f"Already up to date ({current}).")
        return finish(False)
    if latest < current:
        print(f"{latest} is not newer than {current}; skipping.")
        return finish(False)
    if not installer_exists(latest):
        print(f"Installer for {latest} is not reachable; skipping.")
        return finish(False)

    # --- PKGBUILD: bump _td_ver and pkgrel ---
    pkgbuild = re.sub(r"^_td_ver=[\w.]+", f"_td_ver={latest}", pkgbuild, count=1, flags=re.M)

    def _bump_pkgrel(mm: "re.Match") -> str:
        return f"pkgrel={int(mm.group(1)) + 1}"

    pkgbuild, n = re.subn(r"^pkgrel=(\d+)", _bump_pkgrel, pkgbuild, count=1, flags=re.M)
    if not n:
        print("Could not parse pkgrel from PKGBUILD; skipping.")
        return finish(False)
    open(PKGBUILD, "w").write(pkgbuild)

    # --- .SRCINFO: same two fields + the source filename/URL ---
    srcinfo = open(SRCINFO).read()
    srcinfo = re.sub(r"^\tpkgrel = \d+", f"\tpkgrel = {int(re.search(r'^pkgrel=(\d+)', pkgbuild, re.M).group(1))}", srcinfo, count=1, flags=re.M)
    if current not in srcinfo:
        print(f".SRCINFO does not mention {current}; refusing to edit it.")
        return finish(False)
    srcinfo = srcinfo.replace(current, latest)
    open(SRCINFO, "w").write(srcinfo)

    # --- FALLBACK_VERSIONS: prepend the new version ---
    tdpy = open(TD_PY).read()
    if f'"{latest}"' not in tdpy:
        tdpy = re.sub(
            r"(FALLBACK_VERSIONS = \[\n)",
            lambda mm: mm.group(1) + f'    "{latest}",\n',
            tdpy,
            count=1,
        )
        open(TD_PY, "w").write(tdpy)

    print(f"Bumped TouchDesigner {current} -> {latest}")
    return finish(True, latest)


if __name__ == "__main__":
    sys.exit(main())
