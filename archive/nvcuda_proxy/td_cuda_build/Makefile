# Makefile for cuda.dll — CUDA Runtime API proxy
#
# Self-contained Windows PE DLL implementing CUDA Runtime API.
# Does NOT depend on nvcuda.dll at runtime (uses host memory stubs).
#
# Build:
#   make          # build cuda.dll
#   make install  # copy to install locations
#   make clean    # remove build artifacts

MINGW_CC = x86_64-w64-mingw32-gcc
CFLAGS   = -Wall -O2
LDFLAGS  = -shared -lkernel32

TARGET   = cuda.dll
SRC      = cuda_runtime_pe.c
DEF      = cuda.def

# Installation paths
TD_BIN   = /opt/touchdesigner/td/bin
SYS32    = $(HOME)/.local/share/touchdesigner-linux/prefix/drive_c/windows/system32

all: $(TARGET)

$(TARGET): $(SRC) $(DEF)
	$(MINGW_CC) $(CFLAGS) $(LDFLAGS) -o $(TARGET) $(SRC) $(DEF)
	@echo "✅ $(TARGET) built successfully"
	@ls -la $(TARGET)

install: $(TARGET)
	@echo "Installing $(TARGET)..."
	sudo mkdir -p "$(TD_BIN)"
	sudo cp $(TARGET) "$(TD_BIN)/$(TARGET)"
	@echo "  → $(TD_BIN)/$(TARGET)"
	mkdir -p "$(SYS32)"
	cp $(TARGET) "$(SYS32)/$(TARGET)"
	@echo "  → $(SYS32)/$(TARGET)"
	@echo "✅ cuda.dll installed"

clean:
	rm -f $(TARGET) *.o

.PHONY: all install clean
