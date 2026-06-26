"""Utility functions: logging, colors, download, checksums."""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ── Terminal colors ──────────────────────────────────────────────────────────


class Colors:
    """Minimal terminal color codes. Disables colors when not a TTY."""

    _enabled = sys.stdout.isatty()

    dim = "\033[2m" if _enabled else ""
    bold = "\033[1m" if _enabled else ""
    green = "\033[0;32m" if _enabled else ""
    yellow = "\033[0;33m" if _enabled else ""
    red = "\033[0;31m" if _enabled else ""
    cyan = "\033[0;36m" if _enabled else ""
    gray = "\033[0;90m" if _enabled else ""
    white = "\033[0;97m" if _enabled else ""
    accent = "\033[2;37m" if _enabled else ""  # dim white (bash ACCENT)
    nc = "\033[0m" if _enabled else ""


# ── Logging ──────────────────────────────────────────────────────────────────

_DEBUG = False
_LOG_FILE: str | None = None


def setup_logging(debug: bool = False):
    global _DEBUG
    _DEBUG = debug


def set_log_file(path: str):
    global _LOG_FILE
    _LOG_FILE = path


def _log(level: str, color: str, *args):
    msg = " ".join(str(a) for a in args)
    print(f"{color}{level}{Colors.nc} {msg}", file=sys.stderr)


def info(*args):
    _log("→", Colors.accent, *args)


def success(*args):
    _log("▸", Colors.green, *args)


def warning(*args):
    _log("•", Colors.yellow, *args)


def error(*args):
    _log("▸", Colors.red, *args)


def debug(*args):
    if _DEBUG:
        _log("DEBUG", Colors.gray, *args)


# ── I/O utilities ────────────────────────────────────────────────────────────


def print_banner(version: str = "1.4"):
    """Print the project banner."""
    term_width = shutil.get_terminal_size().columns
    hr = "─" * min(term_width, 80)
    print(f"{Colors.dim}{hr}{Colors.nc}")
    print(
        f"{Colors.bold}{Colors.white}TouchDesigner Linux installer {Colors.dim}{version}{Colors.nc}"
    )
    print(f"{Colors.gray}By Iswad{Colors.nc}")
    print(f"{Colors.dim}{hr}{Colors.nc}")


def print_hr():
    term_width = shutil.get_terminal_size().columns
    hr = "─" * min(term_width, 80)
    print(f"{Colors.dim}{hr}{Colors.nc}")


# ── System commands ──────────────────────────────────────────────────────────


def require_command(cmd: str) -> str | None:
    """Check if a command is available, return its path or None."""
    return shutil.which(cmd)


def require_any_command(*cmds: str) -> str | None:
    """Return the path of the first available command, or None."""
    for cmd in cmds:
        found = shutil.which(cmd)
        if found:
            return found
    return None


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command and return the result. Raises on failure."""
    debug(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, **kwargs)


def run_optional(cmd: list[str], **kwargs) -> subprocess.CompletedProcess | None:
    """Run a command, return None if it fails."""
    try:
        return run(cmd, **kwargs)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def sudo_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command with sudo."""
    return run(["sudo"] + cmd, **kwargs)


# ── Download ─────────────────────────────────────────────────────────────────


def download_file(
    url: str,
    dest: str,
    label: str = "",
    show_progress: bool = True,
    timeout: int = 30,
    retries: int = 2,
    user_agent: str = "",
) -> bool:
    """Download a file using curl or wget. Returns True on success."""
    label = label or os.path.basename(dest)
    dest_dir = os.path.dirname(dest)
    os.makedirs(dest_dir, exist_ok=True)

    # Use Python's urllib for a clean progress bar (no external deps)
    if show_progress:
        try:
            return _download_with_progress(url, dest, label, timeout, user_agent)
        except Exception:
            pass  # Fall through to curl/wget

    curl = shutil.which("curl")
    wget = shutil.which("wget")

    if curl:
        cmd = [
            curl,
            "--fail",
            "--location",
            "--connect-timeout",
            str(timeout),
            "--retry",
            str(retries),
            "--retry-delay",
            "1",
        ]
        if user_agent:
            cmd.extend(["-A", user_agent])
        cmd.extend(["--output", dest, url])
        if not show_progress:
            cmd.insert(1, "--silent")
            cmd.insert(2, "--show-error")
        try:
            if show_progress:
                subprocess.run(cmd, check=True)
            else:
                subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    if wget:
        cmd = [
            wget,
            "--tries",
            str(retries),
            "--timeout",
            str(timeout),
            "--output-document",
            dest,
            url,
        ]
        if show_progress:
            cmd.insert(1, "-q")
            cmd.insert(2, "--show-progress")
        else:
            cmd.insert(1, "-q")
        try:
            if show_progress:
                subprocess.run(cmd, check=True)
            else:
                subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    error("No download tool found (need curl or wget)")
    return False


def _download_with_progress(
    url: str, dest: str, label: str, timeout: int, user_agent: str
) -> bool:
    """Download with a clean progress bar using urllib."""
    import urllib.request

    req = urllib.request.Request(url)
    if user_agent:
        req.add_header("User-Agent", user_agent)

    with urllib.request.urlopen(req, timeout=timeout) as response:
        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 8192

        with open(dest, "wb") as f:
            start = time.time()
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                if total > 0:
                    pct = downloaded * 100 // total
                    bar_len = 30
                    filled = bar_len * downloaded // total
                    bar = (
                        "=" * (filled - 1) + ">" + "-" * (bar_len - filled)
                        if filled > 0
                        else "-" * bar_len
                    )
                    elapsed = time.time() - start
                    speed = downloaded / (1024 * 1024 * max(elapsed, 0.1))
                    print(
                        f"\r  {label}: [{bar}] {pct}% ({downloaded / 1024 / 1024:.0f}/{total / 1024 / 1024:.0f} MB) {speed:.1f} MB/s",
                        end="",
                        flush=True,
                    )
                else:
                    elapsed = time.time() - start
                    speed = downloaded / (1024 * 1024 * max(elapsed, 0.1))
                    print(
                        f"\r  {label}: {downloaded / 1024 / 1024:.1f} MB @ {speed:.1f} MB/s",
                        end="",
                        flush=True,
                    )

        print()
        return True


# ── Checksums ────────────────────────────────────────────────────────────────


def verify_checksum(file_path: str, expected_hash: str) -> bool:
    """Verify a SHA-256 checksum. Returns True if no hash provided or match."""
    if not expected_hash:
        return True

    try:
        with open(file_path, "rb") as f:
            actual = hashlib.sha256(f.read()).hexdigest()
        return actual.lower() == expected_hash.lower()
    except (IOError, OSError):
        return False


# ── Directory helpers ────────────────────────────────────────────────────────

TD_BASE_DIR = os.environ.get(
    "TD_BASE_DIR",
    os.path.expanduser("~/.local/share/touchdesigner-linux"),
)


def ensure_dir(path: str):
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


def safe_rm(path: str):
    """Remove a file or directory safely (no rm -rf /)."""
    if not path or path == "/":
        error(f"Refusing to delete: {path}")
        return
    if os.path.isfile(path) or os.path.islink(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)
