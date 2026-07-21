/* nvcuda_pe.c — PE side of nvcuda.dll
 *
 * Windows-facing DLL that exports CUDA Driver API functions.
 * Each function forwards to the Unix side (nvcuda.so) via WINE_UNIX_CALL().
 *
 * Compiled with: x86_64-w64-mingw32-gcc -I/path/to/wine/include
 */

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

typedef long NTSTATUS;

/* We copy the relevant parts of wine/unixlib.h to avoid include conflicts */

typedef uint64_t unixlib_handle_t;

/* These are imported from ntdll.dll (via libntdll.a) */
extern NTSTATUS WINAPI __wine_unix_call( unixlib_handle_t handle, unsigned int code, void *args );
extern unixlib_handle_t __wine_unixlib_handle;
extern NTSTATUS WINAPI __wine_init_unix_call(void);

#define WINE_UNIX_CALL(code,args) __wine_unix_call( __wine_unixlib_handle, (code), (args) )

/* ── Function call codes (must match Unix side) ────────────────────────── */
enum {
    NVCUDA_INIT = 0,
    NVCUDA_CU_INIT,
    NVCUDA_CU_DEVICE_GET_COUNT,
    NVCUDA_CU_DEVICE_GET,
    NVCUDA_CU_DEVICE_GET_NAME,
    NVCUDA_CU_DEVICE_GET_UUID,
    NVCUDA_CU_DEVICE_GET_ATTRIBUTE,
    NVCUDA_CU_DEVICE_PRIMARY_CTX_RETAIN,
    NVCUDA_CU_DEVICE_PRIMARY_CTX_RELEASE,
    NVCUDA_CU_CTX_CREATE,
    NVCUDA_CU_CTX_DESTROY,
    NVCUDA_CU_CTX_GET_CURRENT,
    NVCUDA_CU_CTX_SET_CURRENT,
    NVCUDA_CU_MEM_ALLOC,
    NVCUDA_CU_MEM_FREE,
    NVCUDA_CU_MEMCPY_H_TO_D,
    NVCUDA_CU_MEMCPY_D_TO_H,
    NVCUDA_CU_ARRAY_CREATE,
    NVCUDA_CU_ARRAY_DESTROY,
    NVCUDA_CU_MODULE_LOAD_DATA,
    NVCUDA_CU_MODULE_GET_FUNCTION,
    NVCUDA_CU_LAUNCH_KERNEL,
    NVCUDA_CU_STREAM_CREATE,
    NVCUDA_CU_STREAM_DESTROY,
    NVCUDA_CU_EVENT_CREATE,
    NVCUDA_CU_EVENT_DESTROY,
    NVCUDA_CU_EVENT_RECORD,
    NVCUDA_CU_GET_ERROR_STRING,
    NVCUDA_CU_COUNT
};

/* ── Parameter structures (must match Unix side) ───────────────────────── */

#pragma pack(push, 1)

struct cuInit_params {
    unsigned int Flags;
    int result;
};

struct cuDeviceGetCount_params {
    int count;
    int result;
};

struct cuDeviceGet_params {
    int device;
    int ordinal;
    int result;
};

struct cuDeviceGetName_params {
    char name[256];
    int len;
    int dev;
    int result;
};

struct cuCtxCreate_params {
    uint64_t ctx;
    unsigned int flags;
    int dev;
    int result;
};

struct cuMemAlloc_params {
    uint64_t dptr;
    size_t bytesize;
    int result;
};

#pragma pack(pop)

/* ── CUDA Driver API exports ───────────────────────────────────────────── */

int WINAPI cuInit(unsigned int Flags) {
    struct cuInit_params p;
    p.Flags = Flags;
    p.result = 1;
    WINE_UNIX_CALL(NVCUDA_CU_INIT, &p);
    return p.result;
}

int WINAPI cuDeviceGetCount(int *count) {
    struct cuDeviceGetCount_params p;
    p.count = 0;
    p.result = 1;
    WINE_UNIX_CALL(NVCUDA_CU_DEVICE_GET_COUNT, &p);
    if (count) *count = p.count;
    return p.result;
}

int WINAPI cuDeviceGet(int *device, int ordinal) {
    struct cuDeviceGet_params p;
    p.device = -1;
    p.ordinal = ordinal;
    p.result = 1;
    WINE_UNIX_CALL(NVCUDA_CU_DEVICE_GET, &p);
    if (device) *device = p.device;
    return p.result;
}

int WINAPI cuDeviceGetName(char *name, int len, int dev) {
    struct cuDeviceGetName_params p;
    memset(p.name, 0, sizeof(p.name));
    p.len = len;
    p.dev = dev;
    p.result = 1;
    WINE_UNIX_CALL(NVCUDA_CU_DEVICE_GET_NAME, &p);
    if (name && len > 0) {
        strncpy(name, p.name, len - 1);
        name[len - 1] = '\0';
    }
    return p.result;
}

int WINAPI cuDeviceGetUuid(void *uuid, int dev) {
    return 0;
}

int WINAPI cuDeviceGetAttribute(int *pi, int attrib, int dev) {
    if (pi) *pi = 0;
    return 0;
}

int WINAPI cuDevicePrimaryCtxRetain(void **pctx, int dev) {
    struct cuCtxCreate_params p;
    p.ctx = 0;
    p.flags = 0;
    p.dev = dev;
    p.result = 1;
    WINE_UNIX_CALL(NVCUDA_CU_DEVICE_PRIMARY_CTX_RETAIN, &p);
    if (pctx) *pctx = (void*)(uintptr_t)p.ctx;
    return p.result;
}

int WINAPI cuDevicePrimaryCtxRelease(int dev) {
    return 0;
}

int WINAPI cuCtxCreate(void **pctx, unsigned int flags, int dev) {
    struct cuCtxCreate_params p;
    p.ctx = 0;
    p.flags = flags;
    p.dev = dev;
    p.result = 1;
    WINE_UNIX_CALL(NVCUDA_CU_CTX_CREATE, &p);
    if (pctx) *pctx = (void*)(uintptr_t)p.ctx;
    return p.result;
}

int WINAPI cuCtxDestroy(void *ctx) {
    return 0;
}

int WINAPI cuCtxGetCurrent(void **pctx) {
    if (pctx) *pctx = NULL;
    return 0;
}

int WINAPI cuCtxSetCurrent(void *ctx) {
    return 0;
}

int WINAPI cuCtxSynchronize(void) {
    return 0;
}

int WINAPI cuMemAlloc(uint64_t *dptr, size_t bytesize) {
    struct cuMemAlloc_params p;
    p.dptr = 0;
    p.bytesize = bytesize;
    p.result = 1;
    WINE_UNIX_CALL(NVCUDA_CU_MEM_ALLOC, &p);
    if (dptr) *dptr = p.dptr;
    return p.result;
}

int WINAPI cuMemFree(uint64_t dptr) {
    return 0;
}

int WINAPI cuMemcpyHtoD(uint64_t dstDevice, const void *srcHost, size_t ByteCount) {
    return 0;
}

int WINAPI cuMemcpyDtoH(void *dstHost, uint64_t srcDevice, size_t ByteCount) {
    return 0;
}

int WINAPI cuArrayCreate(void **pHandle, const void *pAllocateArray) {
    return 0;
}

int WINAPI cuArrayDestroy(void *hArray) {
    return 0;
}

int WINAPI cuModuleLoadData(void **module, const void *image) {
    return 0;
}

int WINAPI cuModuleGetFunction(void **hfunc, void *hmod, const char *name) {
    return 0;
}

int WINAPI cuLaunchKernel(void *f,
                           unsigned int gX, unsigned int gY, unsigned int gZ,
                           unsigned int bX, unsigned int bY, unsigned int bZ,
                           unsigned int smem, void *stream,
                           void **params, void **extra) {
    return 0;
}

int WINAPI cuStreamCreate(void **phStream, unsigned int Flags) {
    return 0;
}

int WINAPI cuStreamDestroy(void *hStream) {
    return 0;
}

int WINAPI cuEventCreate(void **phEvent, unsigned int Flags) {
    return 0;
}

int WINAPI cuEventDestroy(void *hEvent) {
    return 0;
}

int WINAPI cuEventRecord(void *hEvent, void *hStream) {
    return 0;
}

int WINAPI cuEventSynchronize(void *hEvent) {
    return 0;
}

/* Stubs for remaining functions */
int WINAPI cuDriverGetVersion(int *version) { if (version) *version = 12090; return 0; }
int WINAPI cuGetErrorString(int error, const char **pStr) { static const char *s = "CUDA error (Wine proxy)"; if (pStr) *pStr = s; return 0; }
int WINAPI cuGetErrorName(int error, const char **pStr) { static const char *s = "CUDA_ERROR_PROXY"; if (pStr) *pStr = s; return 0; }
int WINAPI cuDeviceGetP2PAttribute(int *v, int a, int s, int d) { if (v) *v = 0; return 0; }
int WINAPI cuDeviceCanAccessPeer(int *v, int d, int p) { if (v) *v = 0; return 0; }
int WINAPI cuCtxPushCurrent(void *ctx) { return 0; }
int WINAPI cuCtxPopCurrent(void **pctx) { if (pctx) *pctx = NULL; return 0; }
int WINAPI cuCtxGetDevice(int *device) { if (device) *device = 0; return 0; }
int WINAPI cuMemAllocHost(void **pp, size_t s) { *pp = malloc(s); return *pp ? 0 : 1; }
int WINAPI cuMemFreeHost(void *p) { free(p); return 0; }
int WINAPI cuMemcpyHtoDAsync(uint64_t d, const void *s, size_t n, void *st) { return 0; }
int WINAPI cuMemcpyDtoHAsync(void *d, uint64_t s, size_t n, void *st) { return 0; }
int WINAPI cuMemsetD8(uint64_t d, unsigned char v, size_t n) { return 0; }
int WINAPI cuMemsetD32(uint64_t d, unsigned int v, size_t n) { return 0; }
int WINAPI cuArrayGetDescriptor(void *d, void *a) { return 0; }
int WINAPI cuModuleLoadDataEx(void **m, const void *i, unsigned int n, void **o, void **v) { return 0; }
int WINAPI cuModuleGetGlobal(uint64_t *d, size_t *s, void *m, const char *n) { if (d) *d = 0; if (s) *s = 0; return 0; }
int WINAPI cuModuleUnload(void *m) { return 0; }
int WINAPI cuLaunchCooperativeKernel(void *f, unsigned int gX, unsigned int gY, unsigned int gZ, unsigned int bX, unsigned int bY, unsigned int bZ, unsigned int sm, void *st, void **p) { return 0; }
int WINAPI cuStreamSynchronize(void *s) { return 0; }
int WINAPI cuStreamWaitEvent(void *s, void *e, unsigned int f) { return 0; }
int WINAPI cuEventElapsedTime(float *t, void *s, void *e) { if (t) *t = 0; return 0; }
int WINAPI cuFuncSetAttribute(void *f, int a, int v) { return 0; }
int WINAPI cuFuncSetCacheConfig(void *f, int c) { return 0; }
int WINAPI cuFuncSetSharedMemConfig(void *f, int c) { return 0; }
int WINAPI cuOccupancyMaxPotentialBlockSize(int *g, int *b, void *f, const size_t *s, size_t d, int l) { if (g) *g = 1; if (b) *b = 256; return 0; }
int WINAPI cuOccupancyMaxActiveBlocksPerMultiprocessor(int *n, void *f, int b, size_t d) { if (n) *n = 1; return 0; }
int WINAPI cuPointerGetAttribute(void *d, int a, uint64_t p) { return 0; }
int WINAPI cuPointerSetAttribute(const void *v, int a, uint64_t p) { return 0; }
int WINAPI cuPointerGetAttributes(unsigned int n, int *a, void **d, uint64_t p) { return 0; }
int WINAPI cuCtxGetApiVersion(void *ctx, unsigned int *v) { if (v) *v = 12090; return 0; }
int WINAPI cuCtxGetCacheConfig(int *c) { if (c) *c = 0; return 0; }
int WINAPI cuCtxSetCacheConfig(int c) { return 0; }
int WINAPI cuCtxGetSharedMemConfig(int *c) { if (c) *c = 0; return 0; }
int WINAPI cuCtxSetSharedMemConfig(int c) { return 0; }
int WINAPI cuCtxEnablePeerAccess(void *c, unsigned int f) { return 0; }
int WINAPI cuCtxDisablePeerAccess(void *c) { return 0; }
int WINAPI cuCtxCanAccessPeer(int *v, void *d, void *p) { if (v) *v = 0; return 0; }
int WINAPI cuGetProcAddress(const char *s, void **p, int v, uint64_t f) { return 0; }
int WINAPI cuProfilerStart(void) { return 0; }
int WINAPI cuProfilerStop(void) { return 0; }
int WINAPI cuProfilerInitialize(const char *c, const char *o, int m) { return 0; }
int WINAPI cuDevicePrimaryCtxReset(int d) { return 0; }
int WINAPI cuDeviceGetUuid_v2(void *uuid, int dev) { return cuDeviceGetUuid(uuid, dev); }

/* ── DLL entry point ───────────────────────────────────────────────────── */

BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved) {
    if (fdwReason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hinstDLL);
        __wine_init_unix_call();
    }
    return TRUE;
}
