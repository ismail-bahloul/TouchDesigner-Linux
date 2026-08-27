"""Distrobox container mode.

Runs the whole TouchDesigner-Wine environment inside an isolated distrobox
container (podman or docker backend) so the host system is never modified:

- the 32-bit (i386/multilib) dependency problem disappears — those packages
  are installed inside the container's distro instead of the host's
- immutable / read-only hosts (SteamOS, Fedora Silverblue, ...) need no
  system changes, and ``sudo`` is never needed on the host
- ``noexec`` mounts on ``/home`` are the one remaining host-level issue —
  see :func:`noexec_mount` (a different ``TD_BASE_DIR`` fixes it)

The container shares the host ``$HOME``, so the launcher, desktop
shortcuts, Wine prefix and license files stay on the host filesystem while
every executable actually runs inside the container.

Flow::

    td-install --container install        # host side
      └─ distrobox enter touchdesigner-linux -- ~/.../td-install install
           └─ normal install flow, but distro detection sees the
              container's OS and packages are installed there
"""

import os
import shutil
import subprocess
import sys

from .utils import ensure_dir, error, info, success, warning

REPO_URL = "https://github.com/ismail-bahloul/TouchDesigner-Linux.git"

# Overridable via env so power users can pick their own container/image.
CONTAINER_NAME = os.environ.get("TD_CONTAINER_NAME", "touchdesigner-linux")
CONTAINER_IMAGE = os.environ.get("TD_CONTAINER_IMAGE", "ubuntu:24.04")

# distrobox sets this inside the container — the canonical "we are inside"
# signal (also used by distrobox's own init scripts).
_INSIDE_VAR = "DISTROBOX_ENTER_PATH"


def is_inside_distrobox() -> bool:
    """True when the current process runs inside a distrobox container."""
    return bool(os.environ.get(_INSIDE_VAR))


def is_container_mode() -> bool:
    """True when this install is managed by a container (launcher shim etc.)."""
    return is_inside_distrobox() or bool(os.environ.get("TD_CONTAINER_MODE"))


def find_distrobox() -> str | None:
    """Return the distrobox binary path, or None."""
    return shutil.which("distrobox")


def find_backend() -> str | None:
    """Return the container engine distrobox will use (podman/docker)."""
    for cmd in ("podman", "docker"):
        if shutil.which(cmd):
            return cmd
    return None


def container_exists(name: str = CONTAINER_NAME) -> bool:
    """Check whether a distrobox container named ``name`` exists."""
    distrobox = find_distrobox()
    if not distrobox:
        return False
    try:
        result = subprocess.run(
            [distrobox, "list"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    if result.returncode != 0:
        return False
    for line in result.stdout.splitlines():
        for token in line.split():
            if token == name:
                return True
    return False


def _nvidia_available() -> bool:
    """True when an NVIDIA GPU is usable on the host (drives --nvidia)."""
    if not shutil.which("nvidia-smi"):
        return False
    try:
        result = subprocess.run(["nvidia-smi", "-L"], capture_output=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def _selinux_enforcing() -> bool:
    """True when SELinux is enforcing (needs label=disable for X sockets)."""
    if not shutil.which("getenforce"):
        return False
    try:
        result = subprocess.run(
            ["getenforce"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0 and result.stdout.strip() == "Enforcing"
    except (subprocess.TimeoutExpired, OSError):
        return False


def create_container(name: str = CONTAINER_NAME, image: str = CONTAINER_IMAGE) -> bool:
    """Create the distrobox container. Returns True on success."""
    distrobox = find_distrobox()
    if not distrobox:
        error("Container mode needs distrobox, which is not installed.")
        info("Install it: curl -sSL https://distrobox.it/install | sh")
        info("Or via your package manager (package name: distrobox).")
        return False
    if not find_backend():
        error("Container mode needs podman or docker (the distrobox backend).")
        info("  Debian/Ubuntu: sudo apt install podman")
        info("  Fedora:        sudo dnf install podman")
        info("  Arch:          sudo pacman -S podman")
        info("  openSUSE:      sudo zypper install podman")
        return False

    cmd = [distrobox, "create", "--name", name, "--image", image]
    # Non-interactive: accept the image pull prompt so a first run works
    # when the image is not cached locally (also covers --non-interactive).
    cmd.append("--yes")
    if _nvidia_available():
        info("NVIDIA GPU detected: enabling host driver passthrough (--nvidia)")
        cmd.append("--nvidia")
    if _selinux_enforcing():
        info("SELinux enforcing: adding label=disable security flag")
        cmd += ["--additional-flags", "--security-opt label=disable"]

    info(f"Creating container {name} ({image})...")
    info("First run downloads the base image (~100-200 MB).")
    try:
        result = subprocess.run(cmd)
    except KeyboardInterrupt:
        print()
        info("Container creation cancelled")
        return False
    if result.returncode != 0:
        error(f"Failed to create container {name}")
        return False
    success(f"Container {name} created")
    return True


def remove_container(name: str = CONTAINER_NAME) -> int:
    """Remove a distrobox container. Returns the exit code."""
    distrobox = find_distrobox()
    if not distrobox:
        warning("distrobox not installed — nothing to remove")
        return 0
    if not container_exists(name):
        info(f"Container {name} does not exist")
        return 0
    info(f"Removing container {name}...")
    try:
        return subprocess.call([distrobox, "rm", "-f", name])
    except KeyboardInterrupt:
        print()
        return 1


def confirm_remove_container(non_interactive: bool = False) -> int:
    """Remove the container after a confirmation (unless non-interactive)."""
    if not container_exists():
        info(f"Container {CONTAINER_NAME} does not exist")
        return 0
    warning(
        f"This removes the container {CONTAINER_NAME} and the system packages"
        + " installed inside it."
    )
    info(
        "With the default TD_BASE_DIR (shared $HOME), your Wine prefix and"
        + " license activation stay on the host and are untouched."
    )
    if not non_interactive:
        try:
            confirm = (
                input(f"Remove container {CONTAINER_NAME}? [y/N]: ").strip().lower()
            )
        except (EOFError, KeyboardInterrupt):
            print()
            confirm = "n"
        if confirm not in ("y", "yes"):
            info("Container removal cancelled")
            return 0
    return remove_container()


def noexec_mount(path: str | None = None) -> bool:
    """True when ``path`` sits on a noexec mount (Wine cannot run there).

    This is the one host-level issue container mode cannot paper over with
    the default layout: Wine's binaries must be able to exec, and a noexec
    ``$HOME`` stays noexec inside the container (the home is bind-mounted).
    """
    path = path or os.path.expanduser("~/.local/share/touchdesigner-linux")
    findmnt = shutil.which("findmnt")
    if not findmnt:
        return False
    try:
        result = subprocess.run(
            [findmnt, "-T", path, "-o", "OPTIONS", "-n"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return result.returncode == 0 and "noexec" in (result.stdout or "")


def ensure_source_in_home() -> str:
    """Return a ``td-install`` script path that exists inside the container.

    The container shares the host ``$HOME``, so any script under ``$HOME``
    works directly. Otherwise (system install, clone outside home) the repo
    is cloned into the shared install directory so the container can reach
    it.
    """
    home = os.path.expanduser("~")
    candidates = [os.path.abspath(sys.argv[0])]
    if os.path.basename(sys.argv[0]) == "td-install":
        found = shutil.which("td-install")
        if found:
            candidates.append(os.path.realpath(found))
    for script in candidates:
        if script.startswith(home + os.sep) and os.path.isfile(script):
            return script

    install_dir = os.path.join(home, ".local", "share", "touchdesigner-linux")
    repo_dir = os.path.join(install_dir, "source")
    script = os.path.join(repo_dir, "td-install")
    if os.path.isfile(script):
        return script

    if not shutil.which("git"):
        error("git is required when td-install is not installed under $HOME")
        raise SystemExit(1)
    info(f"Cloning the installer into {repo_dir} (shared with the container)...")
    ensure_dir(repo_dir)
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", REPO_URL, repo_dir],
            check=True,
        )
    except subprocess.CalledProcessError:
        error("Failed to clone the installer")
        raise SystemExit(1)
    return script


def bootstrap_container(recreate: bool = False) -> int:
    """Host-side entrypoint for ``td-install --container``.

    Creates the container if needed, then re-executes the requested command
    inside it. Returns the exit code of the inner invocation, or 0 when
    already inside the container (the caller then continues normally).
    """
    if is_inside_distrobox():
        return 0

    distrobox = find_distrobox()
    if not distrobox:
        error("Container mode needs distrobox, which is not installed.")
        info("Install it: curl -sSL https://distrobox.it/install | sh")
        info("Or via your package manager (package name: distrobox).")
        return 1
    if not find_backend():
        error("Container mode needs podman or docker (the distrobox backend).")
        info("  Debian/Ubuntu: sudo apt install podman")
        info("  Fedora:        sudo dnf install podman")
        info("  Arch:          sudo pacman -S podman")
        info("  openSUSE:      sudo zypper install podman")
        return 1

    name = CONTAINER_NAME
    if recreate and container_exists(name):
        info(f"Recreating container {name}...")
        if remove_container(name) != 0:
            return 1
    if not container_exists(name):
        info("── Container mode ────────────────────────────────")
        info(f"  Container: {name}  ({CONTAINER_IMAGE})")
        info(f"  Backend:   {find_backend()}")
        info("  The host system is NOT modified: all packages, Wine and")
        info("  TouchDesigner live inside the container.")
        if not create_container(name):
            return 1
    else:
        info(f"Using existing container {name}")

    script = ensure_source_in_home()
    inner_args = [
        a for a in sys.argv[1:] if a not in ("--container", "--container-create")
    ]
    env = os.environ.copy()
    env["TD_CONTAINER_NAME"] = name

    info(f"Entering container {name}...")
    cmd = [distrobox, "enter", name, "--", script] + inner_args
    try:
        return subprocess.call(cmd, env=env)
    except KeyboardInterrupt:
        print()
        return 1
