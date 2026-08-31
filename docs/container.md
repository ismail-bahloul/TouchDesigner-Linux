# Container mode (Distrobox / Podman)

An **optional** way to run TouchDesigner-Linux: instead of installing packages
on your host system, everything runs inside an isolated
[Distrobox](https://distrobox.it/) container (podman or docker backend). The
host system is **never modified** — no `sudo`, no 32-bit repositories, no
system-wide packages.

![Screenshot](../Screenshots/Script_Preview.png)

```
td-install --container install
    └─ distrobox enter touchdesigner-linux -- ~/.../td-install install
         └─ normal install flow, but distro detection sees the container's
            OS and all packages are installed inside the container
```

## Why use it

- **No 32-bit dependency pain.** The installer normally has to enable i386 /
  multilib on your host (`dpkg --add-architecture i386`, editing
  `pacman.conf`, ...). In container mode those packages are installed inside
  an Ubuntu container — the host repo setup doesn't matter.
- **Works on any distro, immutable or not.** SteamOS, Fedora Silverblue,
  NixOS, or anything else — no `steamos-readonly disable`, no touching
  `/etc`.
- **No `sudo` on the host.** Only the user-level `distrobox` / `podman`
  (or `docker`) commands are used.
- **Clean removal.** `td-install --container-remove` deletes the container;
  the host is exactly as it was before.

## Requirements

- `distrobox` (package `distrobox` on most distros, or
  `curl -sSL https://distrobox.it/install | sh`)
- `podman` (recommended, rootless) or `docker`

## Usage

```bash
# Install (creates the container on first run)
td-install --container install

# Any other action works through the container too:
td-install --container update
td-install --container uninstall
td-install --container --diagnose
td-install --container --pip install numpy
td-install --container --codemeter status

# Recreate the container from scratch (e.g. new image)
td-install --container-create install

# Remove the container and the system packages inside it
td-install --container-remove
```

The container is named `touchdesigner-linux` and uses `ubuntu:24.04` by
default. Both are overridable:

```bash
export TD_CONTAINER_NAME=my-td
export TD_CONTAINER_IMAGE=fedora:40
td-install --container install
```

> Note: only Debian/Ubuntu images are currently tested in container mode.
> Other distros work through the normal distro-detection path but are less
> battle-tested here.

## The one-liner works too

The `curl | bash` one-liner plays nicely with container mode, both ways:

**From the host** (recommended) — pass `--container` through the pipe, the
installer bootstraps the container and runs everything inside it:

```bash
curl -sSL https://raw.githubusercontent.com/ismail-bahloul/TouchDesigner-Linux/main/install.sh | bash -s -- --container
```

**Inside an existing container** — the one-liner also works when run from
inside a distrobox container (e.g. after `distrobox create` +
`distrobox enter`). install.sh now falls back to a tarball download when
`git` is missing (fresh containers ship `curl`/`wget` but not git), so
nothing needs to be installed first:

```bash
distrobox create --name td --image ubuntu:24.04 --nvidia
distrobox enter td
# inside the container:
curl -sSL https://raw.githubusercontent.com/ismail-bahloul/TouchDesigner-Linux/main/install.sh | bash
```

Either way the installer ends up running inside the container: packages are
installed there, and the launcher is generated with the container shim so
it works from the host.

## How it works

1. `--container` on the **host** checks for distrobox + podman/docker,
   creates the container if missing (passing `--nvidia` automatically when
   an NVIDIA GPU is detected, and `label=disable` on SELinux hosts), then
   re-executes the same command inside the container.
2. Inside the container the **normal** install flow runs — distro detection
   sees Ubuntu, packages (including all `:i386` libraries Wine needs) are
   installed inside the container.
3. The container shares the host `$HOME`, so:
   - the Wine prefix, TouchDesigner install, licenses (`ins*.dat`) and
     backups live on the host filesystem as usual (`~/.local/share/
     touchdesigner-linux`), visible from both sides
   - the launcher (`~/.local/bin/launch-touchdesigner.sh`), desktop
     shortcuts and `.toe` file associations are written into the shared
     home and work from the host
4. The generated launcher starts with a small shim: when invoked from the
   host it re-enters the container (`distrobox enter`), and does nothing
   when already inside (guarded by `DISTROBOX_ENTER_PATH`, which distrobox
   only sets inside). Desktop icons and double-clicking `.toe` files
   therefore work without any extra setup.

## Launching

A `touchdesigner` command is installed in `~/.local/bin` (symlink to the
launcher, same as the AUR package's `/usr/bin/touchdesigner`). It works
from the host *and* from inside the container — with the shim it re-enters
the container when needed:

```bash
touchdesigner                  # launch TouchDesigner
touchdesigner my-project.toe   # open a project
touchdesigner --help           # usage (answers without launching)
touchdesigner -v               # tool version + installed TD versions
touchdesigner --list           # same, with full install paths
touchdesigner --no-patch foo.toe   # open without the .toe font-fix pass
touchdesigner --verbose        # show Wine debug output (errors/warnings)
touchdesigner --exe "/path/to/TouchDesigner.exe"   # specific install
```

Flags combine (e.g. `touchdesigner --no-patch --verbose foo.toe`); unknown
`-*` flags are rejected with a usage hint instead of being treated as a
project path.

The full launcher path (`~/.local/bin/launch-touchdesigner.sh`) still
works as before.

## GPU & hardware

- **AMD / Intel:** distrobox mounts `/dev/dri` into the container by
  default; Vulkan/DXVK works out of the box.
- **NVIDIA:** the installer detects `nvidia-smi` on the host and creates the
  container with `--nvidia`, which mounts the host driver's userspace
  libraries into the container. The host kernel module version must match
  the host driver (as always with containers).
  - **Slow startup note:** distrobox's `--nvidia` init scans the whole host
    tree for NVIDIA files on **every** container start and bind-mounts each
    one, which can take several minutes on big systems (no `--nvidia` step
    in the logs = still scanning). The container is usable once it finishes.
  - If you don't need GPU acceleration inside the container (or find the
    init too slow), skip the passthrough:
    ```bash
    TD_CONTAINER_NO_NVIDIA=1 td-install --container install
    ```
- **Audio:** distrobox forwards the PipeWire/PulseAudio sockets.
- **USB (MIDI controllers, cameras...):** distrobox shares host devices, but
  devices plugged in *after* the container is started may not appear until
  the container is restarted, and host udev rules don't apply inside.

## Known limitations

- **`noexec` on `$HOME`:** the one host problem container mode cannot paper
  over with the default layout — the home directory is bind-mounted into the
  container, so a noexec mount stays noexec. If `td-install --container`
  warns about it, install with a different base directory:
  ```bash
  TD_BASE_DIR=/var/tmp/touchdesigner-linux td-install --container install
  ```
  (this keeps the heavy files inside the container's own filesystem; the
  launcher bakes the path in automatically).
- **`.toe` files outside `$HOME`** are not visible inside the container
  (distrobox only shares the home directory). Keep your projects under
  `$HOME` in container mode, or mount extra paths when creating the
  container.
- **Shared prefix with a native install:** if you already have a native
  install, its prefix/runner in the shared home are reused by the container.
  That usually works, but mixing a host-created prefix with container
  libraries is the least tested path — `td-install --container-create` +
  fresh install is the cleanest when switching.
- **CodeMeter client** stays blocked under Wine regardless of container mode
  (see [codemeter.md](codemeter.md)). The `docker-codemeter` *server*
  remains a good companion.

## Troubleshooting

- **Shell config errors on `distrobox enter`** (`command not found: fastfetch`,
  `no such file or directory: /usr/share/...-zsh-config/...`). The container
  shares your `$HOME`, and distrobox gives the container user the same shell
  as your host — so your host `.zshrc`/`.bashrc` runs inside the container
  too, where host-only programs and config paths don't exist. This only
  affects interactive `distrobox enter`; command entries
  (`distrobox enter NAME -- cmd`, used by the launcher and the installer)
  don't source shell configs. Two fixes:
  - Guard your host shell config (recommended) — add at the **top** of
    `~/.zshrc` (or `~/.bashrc`):
    ```zsh
    # distrobox: skip host-only config inside containers
    if [[ -n "${DISTROBOX_ENTER_PATH:-}" ]]; then
      export PATH="$HOME/.local/bin:$PATH"
      return
    fi
    ```
  - Or use a plain shell inside the container (your `~/.bashrc` is then the
    only shared config): `distrobox enter touchdesigner-linux -- sudo chsh -s /usr/bin/bash $(id -un)`
- `Error: unable to find user <name>` on first `distrobox enter`: the
  container init was interrupted (Ctrl+C / timeout during creation). Fix:
  `distrobox rm -f touchdesigner-linux` and run the command again.
- `Failed to create container`: check `podman info` / `docker info` works,
  and that your user is in the `docker` group (docker backend) or rootless
  podman is configured.
- GUI won't start: make sure you're on X11/XWayland (the launcher clears
  `WAYLAND_DISPLAY` for Wine), and that SELinux systems created the
  container with `label=disable` (the installer does this automatically
  when `getenforce` reports `Enforcing`).

## Testing

```bash
bash tests/test_distrobox.sh          # full flow: bootstrap → diagnose →
                                      # dry-run → static tests → cleanup
```
