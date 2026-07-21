# wine-cuda-proxy — Native CUDA support for Wine
# Integrates into Wine's PE/Unix split architecture

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WINE_SRC="${WINE_SRC:-$HOME/tmp/wine-build}"
WINE_PREFIX="${WINE_PREFIX:-$HOME/.local/share/touchdesigner-linux/prefix}"
WINE_LIBDIR="${WINE_LIBDIR:-/opt/touchdesigner/wine/lib/wine}"

# ── Build nvcuda (CUDA Driver API) ───────────────────────────────────
build_nvcuda() {
    echo "=== Building nvcuda (Driver API) ==="
    
    cd "$PROJECT_DIR/dlls/nvcuda"
    
    # 1. Generate assembly with __wine_spec_nt_header from .spec
    winebuild --dll -m64 -o nvcuda_gen.s -E nvcuda.spec
    
    # 2. Compile Unix side
    gcc -c -fPIC -I "$WINE_SRC/include" -o nvcuda_unix.o nvcuda_unix.c
    
    # 3. Assemble winebuild output
    gcc -c -o nvcuda_gen.o nvcuda_gen.s
    
    # 4. Link Unix .so
    gcc -o nvcuda.so -shared nvcuda_gen.o nvcuda_unix.o -ldl
    
    # 5. Compile PE side (needs Wine headers and libntdll)
    x86_64-w64-mingw32-gcc -c -I "$WINE_SRC/include" \
        -o nvcuda_main.o nvcuda_main.c
    
    x86_64-w64-mingw32-gcc -shared -o nvcuda.dll nvcuda_main.o \
        -L "$WINE_SRC/dlls/ntdll" -lntdll \
        -lkernel32

    echo "✅ nvcuda built"
}

# ── Build cuda (CUDA Runtime API) ─────────────────────────────────────
build_cuda() {
    echo "=== Building cuda (Runtime API) ==="
    
    cd "$PROJECT_DIR/dlls/cuda"
    
    winebuild --dll -m64 -o cuda_gen.s -E cuda.spec
    
    gcc -c -fPIC -I "$WINE_SRC/include" -o cuda_unix.o cuda_unix.c
    gcc -c -o cuda_gen.o cuda_gen.s
    gcc -o cuda.so -shared cuda_gen.o cuda_unix.o -ldl
    
    x86_64-w64-mingw32-gcc -c -I "$WINE_SRC/include" \
        -o cuda_main.o cuda_main.c
    x86_64-w64-mingw32-gcc -shared -o cuda.dll cuda_main.o \
        -L "$WINE_SRC/dlls/ntdll" -lntdll \
        -lkernel32

    echo "✅ cuda built"
}

# ── Install into Wine ────────────────────────────────────────────────
install() {
    echo "=== Installing to Wine ==="
    
    # Unix .so files go to x86_64-unix/
    sudo cp "$PROJECT_DIR/dlls/nvcuda/nvcuda.so" "$WINE_LIBDIR/x86_64-unix/"
    sudo cp "$PROJECT_DIR/dlls/cuda/cuda.so" "$WINE_LIBDIR/x86_64-unix/"
    
    # PE .dll files go to x86_64-windows/
    sudo cp "$PROJECT_DIR/dlls/nvcuda/nvcuda.dll" "$WINE_LIBDIR/x86_64-windows/"
    sudo cp "$PROJECT_DIR/dlls/cuda/cuda.dll" "$WINE_LIBDIR/x86_64-windows/"
    
    # Also copy to prefix system32 for native fallback
    cp "$PROJECT_DIR/dlls/nvcuda/nvcuda.dll" "$WINE_PREFIX/drive_c/windows/system32/"
    cp "$PROJECT_DIR/dlls/cuda/cuda.dll" "$WINE_PREFIX/drive_c/windows/system32/"
    
    echo "✅ Installed"
}

# ── Test ──────────────────────────────────────────────────────────────
test_cuda() {
    echo "=== Testing CUDA under Wine ==="
    
    WINEPREFIX="$WINE_PREFIX" \
    WINEDLLOVERRIDES="nvcuda,cuda=b" \
    wine64 python3 -c "
import ctypes
nv = ctypes.WinDLL('nvcuda.dll')
nv.cuInit(0)
c = ctypes.c_int()
nv.cuDeviceGetCount(ctypes.byref(c))
print(f'CUDA Driver: {c.value} device(s)')

cd = ctypes.WinDLL('cuda.dll')
cd.cudaGetDeviceCount(ctypes.byref(c))
print(f'CUDA Runtime: {c.value} device(s)')
"
}

# ── Main ──────────────────────────────────────────────────────────────
case "${1:-all}" in
    nvcuda)  build_nvcuda ;;
    cuda)    build_cuda ;;
    all)     build_nvcuda && build_cuda ;;
    install) install ;;
    test)    test_cuda ;;
    *)
        echo "Usage: $0 {all|nvcuda|cuda|install|test}"
        exit 1
        ;;
esac
