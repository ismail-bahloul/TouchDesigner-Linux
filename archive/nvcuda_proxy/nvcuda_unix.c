/* nvcuda_unix.c — Unix side of Wine's nvcuda unixlib
 *
 * Implements CUDA Driver API by proxying to native libcuda.so.
 * Compiled as nvcuda.so, placed in x86_64-unix/
 *
 * Dispatch table: __wine_unix_call_funcs[]
 * Each function receives a void* args, casts to its params struct.
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <stdint.h>

/* From Wine unixlib.h (for the dispatch table type) */
typedef int (*unixlib_entry_t)( void *args );

/* ── CUDA types ────────────────────────────────────────────────────────── */
typedef int CUresult;
typedef void *CUcontext;
typedef int CUdevice;
typedef void *CUfunction;
typedef void *CUmodule;
typedef uint64_t CUdeviceptr;
typedef void *CUstream;
typedef void *CUevent;
typedef void *CUarray;

/* ── Debug ──────────────────────────────────────────────────────────────── */
static int debug = 0;
#define DBG(...) do { if (debug) { fprintf(stderr, "nvcuda: " __VA_ARGS__); fprintf(stderr, "\n"); } } while(0)

/* ── libcuda.so loader ──────────────────────────────────────────────────── */
static void *libcuda = NULL;

static void *get_libcuda(void) {
    if (!libcuda) {
        libcuda = dlopen("libcuda.so", RTLD_NOW | RTLD_GLOBAL);
        if (!libcuda)
            fprintf(stderr, "nvcuda: FATAL: dlopen(libcuda.so) failed: %s\n", dlerror());
        else
            DBG("libcuda.so loaded");
    }
    return libcuda;
}

static void *get_func(const char *name) {
    if (!get_libcuda()) return NULL;
    void *fn = dlsym(libcuda, name);
    if (!fn) DBG("function %s not found", name);
    return fn;
}

/* ── Function call codes ───────────────────────────────────────────────── */
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
    NVCUDA_CU_COUNT  /* must be last */
};

/* ── Parameter structures ──────────────────────────────────────────────── */
/* Each struct matches between PE and Unix sides via shared enum */

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
    uint64_t ctx;  /* CUcontext */
    unsigned int flags;
    int dev;
    int result;
};

struct cuMemAlloc_params {
    uint64_t dptr;
    size_t bytesize;
    int result;
};

struct cuMemFree_params {
    uint64_t dptr;
    int result;
};

/* ── Implementation functions ─────────────────────────────────────────── */

static int nvcuda_unix_init(void *args) {
    debug = !!getenv("NVCUDA_DEBUG");
    DBG("nvcuda Unix side initialized");
    return get_libcuda() ? 0 : -1;
}

static int cuInit_wrapper(void *args) {
    struct cuInit_params *p = (struct cuInit_params *)args;
    typedef int (*fn_t)(unsigned int);
    fn_t fn = (fn_t)get_func("cuInit");
    p->result = fn ? fn(p->Flags) : 1;
    DBG("cuInit(%u) = %d", p->Flags, p->result);
    return 0;
}

static int cuDeviceGetCount_wrapper(void *args) {
    struct cuDeviceGetCount_params *p = (struct cuDeviceGetCount_params *)args;
    typedef int (*fn_t)(int *);
    fn_t fn = (fn_t)get_func("cuDeviceGetCount");
    int count;
    p->result = fn ? fn(&count) : 1;
    p->count = (p->result == 0) ? count : 0;
    return 0;
}

static int cuDeviceGet_wrapper(void *args) {
    struct cuDeviceGet_params *p = (struct cuDeviceGet_params *)args;
    typedef int (*fn_t)(int *, int);
    fn_t fn = (fn_t)get_func("cuDeviceGet");
    int dev;
    p->result = fn ? fn(&dev, p->ordinal) : 1;
    p->device = (p->result == 0) ? dev : -1;
    return 0;
}

static int cuDeviceGetName_wrapper(void *args) {
    struct cuDeviceGetName_params *p = (struct cuDeviceGetName_params *)args;
    typedef int (*fn_t)(char *, int, int);
    fn_t fn = (fn_t)get_func("cuDeviceGetName");
    p->result = fn ? fn(p->name, p->len, p->dev) : 1;
    return 0;
}

static int cuCtxCreate_wrapper(void *args) {
    struct cuCtxCreate_params *p = (struct cuCtxCreate_params *)args;
    typedef int (*fn_t)(CUcontext *, unsigned int, CUdevice);
    fn_t fn = (fn_t)get_func("cuCtxCreate");
    CUcontext ctx;
    p->result = fn ? fn(&ctx, p->flags, p->dev) : 1;
    p->ctx = (p->result == 0) ? (uint64_t)(uintptr_t)ctx : 0;
    return 0;
}

static int cuMemAlloc_wrapper(void *args) {
    struct cuMemAlloc_params *p = (struct cuMemAlloc_params *)args;
    typedef int (*fn_t)(CUdeviceptr *, size_t);
    fn_t fn = (fn_t)get_func("cuMemAlloc");
    CUdeviceptr dptr;
    p->result = fn ? fn(&dptr, p->bytesize) : 1;
    p->dptr = (p->result == 0) ? (uint64_t)dptr : 0;
    return 0;
}

static int cuMemFree_wrapper(void *args) {
    struct cuMemFree_params *p = (struct cuMemFree_params *)args;
    typedef int (*fn_t)(CUdeviceptr);
    fn_t fn = (fn_t)get_func("cuMemFree");
    p->result = fn ? fn((CUdeviceptr)p->dptr) : 1;
    return 0;
}

/* ── Stubs for unimplemented functions ─────────────────────────────────── */
static int return_success(void *args) { return 0; }

/* ── Wine unixlib dispatch table ───────────────────────────────────────── */
/* Must match the enum NVCUDA_* codes above exactly */
const unixlib_entry_t __wine_unix_call_funcs[] = {
    nvcuda_unix_init,           /* 0: NVCUDA_INIT */
    cuInit_wrapper,             /* 1: NVCUDA_CU_INIT */
    cuDeviceGetCount_wrapper,   /* 2: NVCUDA_CU_DEVICE_GET_COUNT */
    cuDeviceGet_wrapper,        /* 3: NVCUDA_CU_DEVICE_GET */
    cuDeviceGetName_wrapper,    /* 4: NVCUDA_CU_DEVICE_GET_NAME */
    return_success,             /* 5: cuDeviceGetUuid */
    return_success,             /* 6: cuDeviceGetAttribute */
    cuCtxCreate_wrapper,        /* 7: cuDevicePrimaryCtxRetain */
    return_success,             /* 8: cuDevicePrimaryCtxRelease */
    cuCtxCreate_wrapper,        /* 9: NVCUDA_CU_CTX_CREATE */
    return_success,             /* 10: NVCUDA_CU_CTX_DESTROY */
    return_success,             /* 11: NVCUDA_CU_CTX_GET_CURRENT */
    return_success,             /* 12: NVCUDA_CU_CTX_SET_CURRENT */
    cuMemAlloc_wrapper,         /* 13: NVCUDA_CU_MEM_ALLOC */
    cuMemFree_wrapper,          /* 14: NVCUDA_CU_MEM_FREE */
    return_success,             /* 15: NVCUDA_CU_MEMCPY_H_TO_D */
    return_success,             /* 16: NVCUDA_CU_MEMCPY_D_TO_H */
    return_success,             /* 17: NVCUDA_CU_ARRAY_CREATE */
    return_success,             /* 18: NVCUDA_CU_ARRAY_DESTROY */
    return_success,             /* 19: NVCUDA_CU_MODULE_LOAD_DATA */
    return_success,             /* 20: NVCUDA_CU_MODULE_GET_FUNCTION */
    return_success,             /* 21: NVCUDA_CU_LAUNCH_KERNEL */
    return_success,             /* 22: NVCUDA_CU_STREAM_CREATE */
    return_success,             /* 23: NVCUDA_CU_STREAM_DESTROY */
    return_success,             /* 24: NVCUDA_CU_EVENT_CREATE */
    return_success,             /* 25: NVCUDA_CU_EVENT_DESTROY */
    return_success,             /* 26: NVCUDA_CU_EVENT_RECORD */
    return_success,             /* 27: NVCUDA_CU_GET_ERROR_STRING */
};

/* Need to explicitly mark as used by Wine */
extern const size_t __wine_unix_call_funcs_size;
const size_t __wine_unix_call_funcs_size = sizeof(__wine_unix_call_funcs) / sizeof(__wine_unix_call_funcs[0]);
