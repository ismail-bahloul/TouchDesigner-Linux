# Tests

Test suite for TouchDesigner-Linux v1.4.

## Static validation (no sudo, no install)

```bash
python3 tests/test_static.py
```

Validates imports, CLI args, dry-run, version fetching, and assets.
Safe to run anywhere — no system modifications.

## Docker

```bash
# Build and run all tests in an isolated Ubuntu container
docker build -t td-test -f tests/Dockerfile .
docker run --rm -it td-test
```

Validates the full pipeline inside a container: imports, detection,
dry-run, diagnose. Good for CI or quick smoke tests.

## Distrobox

```bash
# Test inside an Ubuntu container with desktop integration
bash tests/test_distrobox.sh
```

Creates a Distrobox container, installs dependencies, clones the repo,
and runs static validation + dry-run. Add `--additional-flags "--security-opt label=disable"`
for SELinux systems.

## Manual test matrix

| Environment | Goal | Command |
|---|---|---|
| Bare metal | Full install + launch | `./td-install` |
| VM (no GPU) | Headless extraction | `./td-install -H` |
| VM + GPU passthrough | GPU acceleration | `./td-install` |
| Distrobox | Container + desktop | `bash tests/test_distrobox.sh` |
| Docker | Smoke test | `docker build -t td-test -f tests/Dockerfile .` |
