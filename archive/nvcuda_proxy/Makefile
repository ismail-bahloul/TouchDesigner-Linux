# nvcuda.dll.so — Wine unixlib proxy for CUDA Driver API
#
# Build:
#   make          # build nvcuda.dll.so
#   make install  # install into Wine prefix
#   make test     # run quick test

WINEBUILD = winebuild
CC = gcc
MINGW_CC = x86_64-w64-mingw32-gcc
CFLAGS = -fPIC -I/opt/cuda/targets/x86_64-linux/include -Wall -O2
LDFLAGS = -shared -ldl

# CUDA Driver API functions for the .spec file
CUDA_FUNCS = \
	cuInit \
	cuDriverGetVersion \
	cuDeviceGet \
	cuDeviceGetCount \
	cuDeviceGetName \
	cuDeviceGetUuid \
	cuDeviceGetAttribute \
	cuDevicePrimaryCtxRetain \
	cuDevicePrimaryCtxRelease \
	cuDevicePrimaryCtxReset \
	cuCtxCreate \
	cuCtxDestroy \
	cuCtxGetCurrent \
	cuCtxSetCurrent \
	cuCtxGetDevice \
	cuCtxSynchronize \
	cuCtxPushCurrent \
	cuCtxPopCurrent \
	cuMemAlloc \
	cuMemAllocHost \
	cuMemFree \
	cuMemFreeHost \
	cuMemcpyHtoD \
	cuMemcpyDtoH \
	cuMemcpyHtoDAsync \
	cuMemcpyDtoHAsync \
	cuMemsetD8 \
	cuMemsetD32 \
	cuArrayCreate \
	cuArrayDestroy \
	cuArrayGetDescriptor \
	cuModuleLoadData \
	cuModuleLoadDataEx \
	cuModuleGetFunction \
	cuModuleGetGlobal \
	cuModuleUnload \
	cuLaunchKernel \
	cuLaunchCooperativeKernel \
	cuStreamCreate \
	cuStreamDestroy \
	cuStreamSynchronize \
	cuStreamWaitEvent \
	cuEventCreate \
	cuEventDestroy \
	cuEventRecord \
	cuEventSynchronize \
	cuEventElapsedTime \
	cuGetErrorString \
	cuGetErrorName \
	cuFuncSetAttribute \
	cuFuncSetCacheConfig \
	cuFuncSetSharedMemConfig \
	cuOccupancyMaxPotentialBlockSize \
	cuOccupancyMaxActiveBlocksPerMultiprocessor \
	cuPointerGetAttribute \
	cuPointerSetAttribute \
	cuPointerGetAttributes \
	cuCtxGetApiVersion \
	cuCtxGetCacheConfig \
	cuCtxSetCacheConfig \
	cuCtxGetSharedMemConfig \
	cuCtxSetSharedMemConfig \
	cuCtxEnablePeerAccess \
	cuCtxDisablePeerAccess \
	cuCtxCanAccessPeer \
	cuDeviceCanAccessPeer \
	cuDeviceGetP2PAttribute \
	cuGraphicsGLRegisterBuffer \
	cuGraphicsGLRegisterImage \
	cuGraphicsD3D11RegisterBuffer \
	cuGraphicsD3D11RegisterImage \
	cuGraphicsUnregisterResource \
	cuGraphicsMapResources \
	cuGraphicsUnmapResources \
	cuGraphicsResourceGetMappedPointer \
	cuGraphicsResourceGetMappedMipLevel \
	cuGraphicsSubResourceGetMappedArray \
	cuGetProcAddress \
	cuProfilerStart \
	cuProfilerStop \
	cuProfilerInitialize \

# Build a .spec file from the function list
SPEC_FILE = nvcuda.spec
SO_FILE = nvcuda.dll.so

all: $(SO_FILE)

# Generate .spec file
$(SPEC_FILE): Makefile
	@echo "Generating $(SPEC_FILE)..."
	@rm -f $(SPEC_FILE)
	@for fn in $(CUDA_FUNCS); do \
		echo "@ stdcall $$fn(ptr)" >> $(SPEC_FILE); \
	done

# Generate assembly with __wine_spec_nt_header from .spec
nvcuda_spec.s: $(SPEC_FILE)
	$(WINEBUILD) --spec $(SPEC_FILE) --dll nvcuda --export -o $@

# Compile the unix implementation
nvcuda_unix.o: nvcuda_unix.c
	$(CC) $(CFLAGS) -c -o $@ $<

# Link everything into nvcuda.dll.so
$(SO_FILE): nvcuda_spec.s nvcuda_unix.o
	$(CC) -o $@ nvcuda_spec.s nvcuda_unix.o $(LDFLAGS)

install: $(SO_FILE)
	@echo "Installing to Wine library path..."
	sudo cp $(SO_FILE) /opt/touchdesigner/wine/lib/wine/x86_64-windows/nvcuda.dll
	@echo "✅ Installed! Override with: WINEDLLOVERRIDES=nvcuda=b"

test: $(SO_FILE)
	@echo "Testing nvcuda loading..."
	WINEPREFIX=~/.local/share/touchdesigner-linux/prefix \
	WINEDLLOVERRIDES=nvcuda=b \
	/opt/touchdesigner/wine/bin/wine64 /opt/touchdesigner/td/bin/python.exe -c "import ctypes; nv=ctypes.CDLL('nvcuda.dll'); print('Loaded:', nv); nv.cuInit(0); print('cuInit OK')"

clean:
	rm -f $(SO_FILE) $(SPEC_FILE) nvcuda_spec.s *.o

.PHONY: all install test clean
