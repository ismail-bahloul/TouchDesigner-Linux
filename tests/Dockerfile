# TouchDesigner-Linux v1.4 — Test container
# Build:  docker build -t td-test -f tests/Dockerfile .
# Run:    docker run --rm -it td-test

FROM ubuntu:24.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV NON_INTERACTIVE=true
ENV ALLOW_HEADLESS_INSTALL=true

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget ca-certificates \
    p7zip-full innoextract \
    python3 \
    xz-utils cabextract unzip \
    file coreutils xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /opt/touchdesigner-linux
WORKDIR /opt/touchdesigner-linux

# Test 1: Static validation
RUN python3 tests/test_static.py

# Test 2: Distro detection
RUN python3 -c "from td_lib.distro import detect_distro; d = detect_distro(); print(f'Detected: {d.distro_name} ({d.package_manager})')"

# Test 3: Dry-run install (no sudo, no packages)
RUN ./td-install --install --dry-run --headless

# Test 4: Diagnose
RUN ./td-install --diagnose

# Test 5: Help
RUN ./td-install --help

CMD ["/bin/bash"]
