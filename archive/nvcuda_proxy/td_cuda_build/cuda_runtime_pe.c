/* cuda_runtime_pe.c — CUDA Runtime API DLL (cuda.dll)
 *
 * Self-contained Windows PE DLL that implements the CUDA Runtime API.
 * All CUDA Driver API dependencies are built in as stubs — this DLL
 * does NOT depend on nvcuda.dll being loadable at runtime.
 *
 * For real CUDA operations, the functions either:
 *   - Return sensible defaults (for device queries, version info)
 *   - Store/discard state (for memory, kernel launch)
 *   - Use host memory as a fallback when device memory is unavailable
 *
 * Compiled with:
 *   x86_64-w64-mingw32-gcc -shared -o cuda.dll cuda_runtime_pe.c -lkernel32 -lucrtbase
 *
 * For deployment, use -static when ucrtbase.dll is missing:
 *   x86_64-w64-mingw32-gcc -static -shared -o cuda.dll cuda_runtime_pe.c -lkernel32
 */

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* =========================================================================
 * CUDA Runtime types
 * ========================================================================= */

typedef enum cudaError {
    cudaSuccess                              = 0,
    cudaErrorInvalidValue                    = 1,
    cudaErrorMemoryAllocation                = 2,
    cudaErrorNotInitialized                  = 3,
    cudaErrorDeinitialized                   = 4,
    cudaErrorInvalidDevice                   = 10,
    cudaErrorNoDevice                        = 100,
    cudaErrorInvalidImage                    = 200,
    cudaErrorInvalidContext                  = 201,
    cudaErrorContextAlreadyCurrent           = 202,
    cudaErrorMapFailed                       = 205,
    cudaErrorUnmapFailed                     = 206,
    cudaErrorArrayIsMapped                   = 207,
    cudaErrorAlreadyMapped                   = 208,
    cudaErrorNoBinaryForGPU                  = 209,
    cudaErrorAlreadyAcquired                 = 210,
    cudaErrorNotMapped                       = 211,
    cudaErrorNotMappedAsArray                = 212,
    cudaErrorNotMappedAsPointer              = 213,
    cudaErrorECCUncorrectable                = 214,
    cudaErrorUnsupportedLimit                = 215,
    cudaErrorContextAlreadyInUse             = 216,
    cudaErrorPeerAccessUnsupported           = 217,
    cudaErrorInvalidPtx                      = 218,
    cudaErrorInvalidGraphicsContext          = 219,
    cudaErrorInvalidSource                   = 300,
    cudaErrorFileNotFound                    = 301,
    cudaErrorSharedObjectSymbolNotFound      = 302,
    cudaErrorSharedObjectInitFailed          = 303,
    cudaErrorOperatingSystem                 = 304,
    cudaErrorInvalidHandle                   = 400,
    cudaErrorNotFound                        = 500,
    cudaErrorNotReady                        = 600,
    cudaErrorIllegalAddress                  = 700,
    cudaErrorLaunchOutOfResources            = 701,
    cudaErrorLaunchTimeout                   = 702,
    cudaErrorLaunchIncompatibleTexturing     = 703,
    cudaErrorPeerAccessAlreadyEnabled        = 704,
    cudaErrorPeerAccessNotEnabled            = 705,
    cudaErrorContextIsDestroyed              = 707,
    cudaErrorAssert                          = 710,
    cudaErrorTooManyPeers                    = 711,
    cudaErrorHostMemoryAlreadyRegistered     = 712,
    cudaErrorHostMemoryNotRegistered         = 713,
    cudaErrorHardwareStackError              = 714,
    cudaErrorIllegalInstruction              = 715,
    cudaErrorMisalignedAddress               = 716,
    cudaErrorInvalidAddressSpace             = 717,
    cudaErrorInvalidPc                       = 718,
    cudaErrorLaunchFailed                    = 719,
    cudaErrorCooperativeLaunchTooLarge       = 720,
    cudaErrorNotPermitted                    = 800,
    cudaErrorNotSupported                    = 801,
    cudaErrorUnknown                         = 999
} cudaError_t;

typedef enum {
    cudaMemcpyHostToHost     = 0,
    cudaMemcpyHostToDevice   = 1,
    cudaMemcpyDeviceToHost   = 2,
    cudaMemcpyDeviceToDevice = 3,
    cudaMemcpyDefault        = 4
} cudaMemcpyKind;

typedef struct cudaDeviceProp {
    char name[256];
    size_t totalGlobalMem;
    size_t sharedMemPerBlock;
    int regsPerBlock;
    int warpSize;
    size_t memPitch;
    int maxThreadsPerBlock;
    int maxThreadsDim[3];
    int maxGridSize[3];
    int clockRate;
    size_t totalConstMem;
    int major; int minor;
    size_t textureAlignment;
    size_t texturePitchAlignment;
    int deviceOverlap;
    int multiProcessorCount;
    int kernelExecTimeoutEnabled;
    int integrated;
    int canMapHostMemory;
    int computeMode;
    int maxTexture1D;
    int maxTexture1DMipmap;
    int maxTexture1DLinear;
    int maxTexture2D[2];
    int maxTexture2DMipmap[2];
    int maxTexture2DLinear[3];
    int maxTexture2DGather[2];
    int maxTexture3D[3];
    int maxTexture3DAlt[3];
    int maxTextureCubemap;
    int maxTexture1DLayered[2];
    int maxTexture2DLayered[3];
    int maxTextureCubemapLayered[2];
    int maxSurface1D;
    int maxSurface2D[2];
    int maxSurface3D[3];
    int maxSurface1DLayered[2];
    int maxSurface2DLayered[3];
    int maxSurfaceCubemap;
    int maxSurfaceCubemapLayered[2];
    size_t surfaceAlignment;
    int concurrentKernels;
    int ECCEnabled;
    int pciBusID;
    int pciDeviceID;
    int pciDomainID;
    int tccDriver;
    int asyncEngineCount;
    int unifiedAddressing;
    int memoryClockRate;
    int memoryBusWidth;
    int l2CacheSize;
    int persistingL2CacheMaxSize;
    int maxThreadsPerMultiProcessor;
    int streamPrioritiesSupported;
    int globalL1CacheSupported;
    int localL1CacheSupported;
    size_t sharedMemPerMultiprocessor;
    int regsPerMultiprocessor;
    int managedMemory;
    int isMultiGpuBoard;
    int multiGpuBoardGroupID;
    int hostNativeAtomicSupported;
    int singleToDoublePrecisionPerfRatio;
    int pageableMemoryAccess;
    int concurrentManagedAccess;
    int computePreemptionSupported;
    int canUseHostPointerForRegisteredMem;
    int cooperativeLaunch;
    int cooperativeMultiDeviceLaunch;
    size_t sharedMemPerBlockOptin;
    int pageableMemoryAccessUsesHostPageTables;
    int directManagedMemAccessFromHost;
    int maxBlocksPerMultiProcessor;
    int accessPolicyMaxWindowSize;
    size_t reserved[412];
} cudaDeviceProp;

typedef enum cudaChannelFormatKind {
    cudaChannelFormatKindSigned           = 0,
    cudaChannelFormatKindUnsigned         = 1,
    cudaChannelFormatKindFloat            = 2,
    cudaChannelFormatKindNone             = 3
} cudaChannelFormatKind;

typedef struct cudaChannelFormatDesc {
    int x, y, z, w;
    cudaChannelFormatKind f;
} cudaChannelFormatDesc;

typedef struct cudaExtent {
    size_t width, height, depth;
} cudaExtent;

typedef struct cudaPitchedPtr {
    void *ptr;
    size_t pitch, xsize, ysize;
} cudaPitchedPtr;

typedef struct cudaPos { size_t x, y, z; } cudaPos;

typedef struct cudaMemcpy3DParms {
    void *srcArray;
    struct cudaPos srcPos;
    struct cudaPitchedPtr srcPtr;
    void *dstArray;
    struct cudaPos dstPos;
    struct cudaPitchedPtr dstPtr;
    struct cudaExtent extent;
    cudaMemcpyKind kind;
} cudaMemcpy3DParms;

typedef enum cudaResourceType {
    cudaResourceTypeArray          = 0,
    cudaResourceTypeMipmappedArray = 1,
    cudaResourceTypeLinear         = 2,
    cudaResourceTypePitch2D        = 3
} cudaResourceType;

typedef enum cudaTextureReadMode {
    cudaReadModeElementType     = 0,
    cudaReadModeNormalizedFloat = 1
} cudaTextureReadMode;

typedef struct cudaResourceDesc {
    cudaResourceType resType;
    union {
        struct { void *array; } array;
        struct { void *mipmap; } mipmap;
        struct { void *devPtr; struct cudaChannelFormatDesc desc; size_t sizeInBytes; } linear;
        struct { void *devPtr; struct cudaChannelFormatDesc desc; size_t width; size_t height; size_t pitchInBytes; } pitch2D;
    } res;
} cudaResourceDesc;

typedef struct cudaTextureDesc {
    int addressMode[3];
    int filterMode;
    cudaTextureReadMode readMode;
    int sRGB;
    float borderColor[4];
    int normalizedCoords;
    unsigned int maxAnisotropy;
    int mipmapFilterMode;
    float mipmapLevelBias;
    float minMipmapLevelClamp;
    float maxMipmapLevelClamp;
    int disableTrilinearOptimization;
} cudaTextureDesc;

/* Opaque handle types */
typedef struct CUstream_st *cudaStream_t;
typedef struct CUevent_st *cudaEvent_t;
typedef unsigned long long cudaTextureObject_t;
typedef unsigned long long cudaSurfaceObject_t;

/* =========================================================================
 * Internal state
 * ========================================================================= */

static cudaError_t g_last_error = cudaSuccess;
static int g_current_device = 0;

/* Kernel launch configuration */
static struct {
    int configured;
    unsigned int gridDim_x, gridDim_y, gridDim_z;
    unsigned int blockDim_x, blockDim_y, blockDim_z;
    unsigned int sharedMem;
    void *stream;
} g_kernel_config = {0};

/* Fat binary / function registration */
#define MAX_REGISTERED_FUNCTIONS 256
#define MAX_FAT_BINARIES 32

typedef struct {
    void *fatCubin;
    int handle_id;
    int registered;
    void *module;
} FatBinaryEntry;

typedef struct {
    const char *name;
    void *fatCubinHandle;
    void *deviceFunction;
    void *hostFunction;
    void *module;
} RegisteredFunction;

static FatBinaryEntry g_fat_binaries[MAX_FAT_BINARIES];
static int g_fat_binary_count = 0;
static int g_next_handle_id = 1;

static RegisteredFunction g_registered_funcs[MAX_REGISTERED_FUNCTIONS];
static int g_registered_func_count = 0;

/* =========================================================================
 * Internal helpers
 * ========================================================================= */

static cudaError_t set_last_error(cudaError_t e) {
    g_last_error = e;
    return e;
}

/* =========================================================================
 * DLL entry point
 * ========================================================================= */

BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved) {
    if (fdwReason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hinstDLL);
    }
    return TRUE;
}

/* =========================================================================
 * EXPORTS — CUDA Runtime API functions
 * ========================================================================= */

/* ── Memory management ─────────────────────────────────────────────────────── */

cudaError_t WINAPI cudaMalloc(void **devPtr, size_t size) {
    if (!devPtr) return set_last_error(cudaErrorInvalidValue);
    /* Allocate host memory as a stand-in for device memory */
    *devPtr = malloc(size ? size : 1);
    if (!*devPtr) return set_last_error(cudaErrorMemoryAllocation);
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaFree(void *devPtr) {
    if (devPtr) free(devPtr);
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaMemcpy(void *dst, const void *src, size_t count, cudaMemcpyKind kind) {
    if (!dst || !src) return set_last_error(cudaErrorInvalidValue);
    memcpy(dst, src, count);
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaMemcpyAsync(void *dst, const void *src, size_t count,
                                    cudaMemcpyKind kind, cudaStream_t stream) {
    return cudaMemcpy(dst, src, count, kind);
}

cudaError_t WINAPI cudaMemset(void *devPtr, int value, size_t count) {
    if (!devPtr) return set_last_error(cudaErrorInvalidValue);
    memset(devPtr, value, count);
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaMemsetAsync(void *devPtr, int value, size_t count, cudaStream_t stream) {
    return cudaMemset(devPtr, value, count);
}

cudaError_t WINAPI cudaMallocHost(void **ptr, size_t size) {
    if (!ptr) return set_last_error(cudaErrorInvalidValue);
    *ptr = malloc(size ? size : 1);
    if (!*ptr) return set_last_error(cudaErrorMemoryAllocation);
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaFreeHost(void *ptr) {
    if (ptr) free(ptr);
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaMemGetInfo(size_t *free_bytes, size_t *total_bytes) {
    if (free_bytes)  *free_bytes  = 8ULL * 1024 * 1024 * 1024;
    if (total_bytes) *total_bytes = 8ULL * 1024 * 1024 * 1024;
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaMallocArray(void **array, const cudaChannelFormatDesc *desc,
                                    size_t width, size_t height, unsigned int flags) {
    if (array) *array = malloc(64);
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaFreeArray(void *array) {
    if (array) free(array);
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaMallocMipmappedArray(void **mipmap,
                                             const cudaChannelFormatDesc *desc,
                                             size_t width, size_t height,
                                             unsigned int numLevels,
                                             unsigned int flags) {
    if (mipmap) *mipmap = malloc(64);
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaFreeMipmappedArray(void *mipmap) {
    if (mipmap) free(mipmap);
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaGetMipmappedArrayLevel(void **level, void *mipmap, unsigned int levelIdx) {
    if (level) *level = mipmap;
    return set_last_error(cudaSuccess);
}

/* ── Device management ─────────────────────────────────────────────────────── */

cudaError_t WINAPI cudaGetDevice(int *device) {
    if (!device) return set_last_error(cudaErrorInvalidValue);
    *device = g_current_device;
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaSetDevice(int device) {
    g_current_device = device;
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaGetDeviceCount(int *count) {
    if (!count) return set_last_error(cudaErrorInvalidValue);
    /* Report 1 device always available (the proxy GPU) */
    *count = 1;
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaChooseDevice(int *device, const cudaDeviceProp *prop) {
    if (device) *device = 0;
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaSetDeviceFlags(unsigned int flags) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaDeviceSynchronize(void) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaDeviceReset(void) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaGetDeviceProperties(cudaDeviceProp *prop, int device) {
    if (!prop) return set_last_error(cudaErrorInvalidValue);

    memset(prop, 0, sizeof(cudaDeviceProp));
    strncpy(prop->name, "CUDA Proxy GPU (Wine/TG)", 255);
    prop->name[255] = '\0';
    prop->totalGlobalMem                 = 8ULL * 1024 * 1024 * 1024;
    prop->sharedMemPerBlock              = 49152;
    prop->regsPerBlock                   = 65536;
    prop->warpSize                       = 32;
    prop->memPitch                       = 1048576;
    prop->maxThreadsPerBlock             = 1024;
    prop->maxThreadsDim[0]               = 1024;
    prop->maxThreadsDim[1]               = 1024;
    prop->maxThreadsDim[2]               = 64;
    prop->maxGridSize[0]                 = 2147483647;
    prop->maxGridSize[1]                 = 65535;
    prop->maxGridSize[2]                 = 65535;
    prop->clockRate                      = 1500000;
    prop->totalConstMem                  = 65536;
    prop->major                          = 8;
    prop->minor                          = 0;
    prop->textureAlignment               = 512;
    prop->texturePitchAlignment          = 32;
    prop->multiProcessorCount            = 1;
    prop->kernelExecTimeoutEnabled       = 0;
    prop->integrated                     = 0;
    prop->canMapHostMemory               = 1;
    prop->computeMode                    = 0;
    prop->concurrentKernels              = 1;
    prop->ECCEnabled                     = 0;
    prop->pciBusID                       = 0;
    prop->pciDeviceID                    = 0;
    prop->pciDomainID                    = 0;
    prop->tccDriver                      = 0;
    prop->asyncEngineCount               = 1;
    prop->unifiedAddressing              = 1;
    prop->memoryClockRate                = 5000000;
    prop->memoryBusWidth                 = 256;
    prop->l2CacheSize                    = 4194304;
    prop->maxThreadsPerMultiProcessor    = 1024;
    prop->streamPrioritiesSupported      = 0;
    prop->globalL1CacheSupported         = 1;
    prop->localL1CacheSupported          = 1;
    prop->sharedMemPerMultiprocessor     = 65536;
    prop->regsPerMultiprocessor          = 65536;
    prop->managedMemory                  = 1;
    prop->isMultiGpuBoard                = 0;
    prop->cooperativeLaunch              = 1;
    prop->cooperativeMultiDeviceLaunch   = 0;
    prop->sharedMemPerBlockOptin         = 49152;
    prop->pageableMemoryAccess           = 1;
    prop->concurrentManagedAccess        = 1;
    prop->computePreemptionSupported     = 1;
    prop->hostNativeAtomicSupported      = 1;
    prop->singleToDoublePrecisionPerfRatio = 1;
    prop->maxBlocksPerMultiProcessor     = 16;
    prop->accessPolicyMaxWindowSize      = 0;

    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaDeviceGetAttribute(int *value, int attr, int device) {
    if (!value) return set_last_error(cudaErrorInvalidValue);
    /* Return reasonable defaults for common attributes */
    switch (attr) {
        case 1:   *value = 1024; break;  /* MaxThreadsPerBlock */
        case 2:   *value = 1024; break;  /* MaxBlockDimX */
        case 3:   *value = 1024; break;  /* MaxBlockDimY */
        case 4:   *value = 64;   break;  /* MaxBlockDimZ */
        case 5:   *value = 2147483647; break; /* MaxGridDimX */
        case 6:   *value = 65535; break; /* MaxGridDimY */
        case 7:   *value = 65535; break; /* MaxGridDimZ */
        case 8:   *value = 49152; break; /* MaxSharedMemoryPerBlock */
        case 10:  *value = 32;   break;  /* WarpSize */
        case 13:  *value = 1500000; break; /* ClockRate */
        case 16:  *value = 1;    break;  /* MultiProcessorCount */
        case 39:  *value = 1024; break;  /* MaxThreadsPerMultiProcessor */
        case 75:  *value = 8;    break;  /* ComputeCapabilityMajor */
        case 76:  *value = 0;    break;  /* ComputeCapabilityMinor */
        default:  *value = 0;    break;
    }
    return set_last_error(cudaSuccess);
}

/* ── Stream management ─────────────────────────────────────────────────────── */

cudaError_t WINAPI cudaStreamCreate(cudaStream_t *stream) {
    if (!stream) return set_last_error(cudaErrorInvalidValue);
    *stream = (cudaStream_t)malloc(8);
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaStreamCreateWithFlags(cudaStream_t *stream, unsigned int flags) {
    return cudaStreamCreate(stream);
}

cudaError_t WINAPI cudaStreamDestroy(cudaStream_t stream) {
    if (stream) free(stream);
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaStreamSynchronize(cudaStream_t stream) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaStreamWaitEvent(cudaStream_t stream, cudaEvent_t event, unsigned int flags) {
    return set_last_error(cudaSuccess);
}

/* ── Event management ──────────────────────────────────────────────────────── */

cudaError_t WINAPI cudaEventCreate(cudaEvent_t *event) {
    if (!event) return set_last_error(cudaErrorInvalidValue);
    *event = (cudaEvent_t)malloc(8);
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaEventCreateWithFlags(cudaEvent_t *event, unsigned int flags) {
    return cudaEventCreate(event);
}

cudaError_t WINAPI cudaEventDestroy(cudaEvent_t event) {
    if (event) free(event);
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaEventRecord(cudaEvent_t event, cudaStream_t stream) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaEventSynchronize(cudaEvent_t event) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaEventElapsedTime(float *ms, cudaEvent_t start, cudaEvent_t end) {
    if (ms) *ms = 0.0f;
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaEventQuery(cudaEvent_t event) {
    return set_last_error(cudaSuccess);
}

/* ── Error handling ────────────────────────────────────────────────────────── */

cudaError_t WINAPI cudaGetLastError(void) {
    cudaError_t e = g_last_error;
    g_last_error = cudaSuccess;
    return e;
}

cudaError_t WINAPI cudaPeekAtLastError(void) {
    return g_last_error;
}

const char* WINAPI cudaGetErrorString(cudaError_t error) {
    switch (error) {
        case cudaSuccess:           return "no error";
        case cudaErrorInvalidValue: return "invalid argument";
        case cudaErrorMemoryAllocation: return "out of memory";
        case cudaErrorNotInitialized: return "CUDA not initialized";
        case cudaErrorDeinitialized:  return "CUDA deinitialized";
        case cudaErrorInvalidDevice:  return "invalid device ordinal";
        case cudaErrorNoDevice:       return "no CUDA-capable device";
        case cudaErrorInvalidImage:   return "invalid kernel image";
        case cudaErrorInvalidContext: return "invalid device context";
        case cudaErrorNotReady:       return "device not ready";
        case cudaErrorIllegalAddress: return "illegal memory access";
        case cudaErrorLaunchFailed:   return "kernel launch failed";
        case cudaErrorLaunchOutOfResources: return "too many resources requested";
        case cudaErrorUnknown:        return "unknown error";
        default:                      return "CUDA error";
    }
}

cudaError_t WINAPI cudaGetErrorName(cudaError_t error, const char **name) {
    static const char *n[] = {"cudaSuccess", "cudaErrorInvalidValue",
        "cudaErrorMemoryAllocation", "cudaErrorNotInitialized"};
    if (name) {
        if (error >= 0 && (size_t)error < sizeof(n)/sizeof(n[0]))
            *name = n[error];
        else
            *name = "cudaErrorUnknown";
    }
    return cudaSuccess;
}

/* ── Version ───────────────────────────────────────────────────────────────── */

cudaError_t WINAPI cudaRuntimeGetVersion(int *version) {
    if (version) *version = 12090;
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaDriverGetVersion(int *version) {
    if (version) *version = 12090;
    return set_last_error(cudaSuccess);
}

/* ── Kernel launch ─────────────────────────────────────────────────────────── */

cudaError_t WINAPI cudaLaunchKernel(const void *func,
                                     unsigned int gridDim_x, unsigned int gridDim_y, unsigned int gridDim_z,
                                     unsigned int blockDim_x, unsigned int blockDim_y, unsigned int blockDim_z,
                                     unsigned int sharedMemBytes, cudaStream_t stream,
                                     void **kernelParams, void **extra) {
    /* Stub: kernel launch is a no-op in proxy mode */
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaConfigureCall(unsigned int gridDim_x, unsigned int gridDim_y, unsigned int gridDim_z,
                                      unsigned int blockDim_x, unsigned int blockDim_y, unsigned int blockDim_z,
                                      unsigned int sharedMemBytes, cudaStream_t stream) {
    g_kernel_config.configured = 1;
    g_kernel_config.gridDim_x = gridDim_x;
    g_kernel_config.gridDim_y = gridDim_y;
    g_kernel_config.gridDim_z = gridDim_z;
    g_kernel_config.blockDim_x = blockDim_x;
    g_kernel_config.blockDim_y = blockDim_y;
    g_kernel_config.blockDim_z = blockDim_z;
    g_kernel_config.sharedMem = sharedMemBytes;
    g_kernel_config.stream = (void *)stream;
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaSetupArgument(const void *arg, size_t size, size_t offset) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaLaunch(const void *func) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaFuncSetAttribute(const void *func, int attr, int value) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaFuncSetCacheConfig(const void *func, int config) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaFuncSetSharedMemConfig(const void *func, int config) {
    return set_last_error(cudaSuccess);
}

/* ── Occupancy ─────────────────────────────────────────────────────────────── */

cudaError_t WINAPI cudaOccupancyMaxPotentialBlockSize(int *minGridSize, int *blockSize,
                                                       const void *func,
                                                       size_t dynamicSMemSize,
                                                       size_t blockSizeLimit) {
    if (minGridSize) *minGridSize = 1;
    if (blockSize)   *blockSize   = 256;
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaOccupancyMaxActiveBlocksPerMultiprocessor(int *numBlocks,
                                                                  const void *func,
                                                                  int blockSize,
                                                                  size_t dynamicSMemSize) {
    if (numBlocks) *numBlocks = 1;
    return set_last_error(cudaSuccess);
}

/* ── Kernel registration ───────────────────────────────────────────────────── */

void** WINAPI __cudaRegisterFatBinary(void *fatCubin) {
    if (g_fat_binary_count >= MAX_FAT_BINARIES) return NULL;

    FatBinaryEntry *entry = &g_fat_binaries[g_fat_binary_count++];
    entry->fatCubin = fatCubin;
    entry->handle_id = g_next_handle_id++;
    entry->registered = 0;
    entry->module = NULL;

    void **handle = (void **)malloc(sizeof(void *));
    if (handle) *handle = (void *)(uintptr_t)entry->handle_id;
    return handle;
}

void WINAPI __cudaRegisterFunction(void **fatCubinHandle,
                                    const char *hostFun,
                                    char *deviceFun,
                                    const char *deviceName,
                                    int threadLimit,
                                    uint64_t *tid,
                                    uint64_t *bid,
                                    int *blockDim,
                                    int *gridDim,
                                    int *warpSize,
                                    int *unused) {
    if (g_registered_func_count >= MAX_REGISTERED_FUNCTIONS) return;

    RegisteredFunction *rf = &g_registered_funcs[g_registered_func_count++];
    rf->name = deviceName;
    rf->fatCubinHandle = fatCubinHandle ? *fatCubinHandle : NULL;
    rf->hostFunction = (void *)hostFun;
    rf->deviceFunction = (void *)hostFun; /* Use host function pointer directly */
    rf->module = NULL;
}

void WINAPI __cudaUnregisterFatBinary(void **fatCubinHandle) {
    if (!fatCubinHandle) return;
    free(fatCubinHandle);
}

cudaError_t WINAPI __cudaPushCallConfiguration(unsigned int gridDim_x, unsigned int gridDim_y, unsigned int gridDim_z,
                                                unsigned int blockDim_x, unsigned int blockDim_y, unsigned int blockDim_z,
                                                unsigned int sharedMemBytes, void *stream) {
    g_kernel_config.configured = 1;
    g_kernel_config.gridDim_x = gridDim_x;
    g_kernel_config.gridDim_y = gridDim_y;
    g_kernel_config.gridDim_z = gridDim_z;
    g_kernel_config.blockDim_x = blockDim_x;
    g_kernel_config.blockDim_y = blockDim_y;
    g_kernel_config.blockDim_z = blockDim_z;
    g_kernel_config.sharedMem = sharedMemBytes;
    g_kernel_config.stream = stream;
    return cudaSuccess;
}

cudaError_t WINAPI __cudaPopCallConfiguration(unsigned int *gridDim_x, unsigned int *gridDim_y, unsigned int *gridDim_z,
                                               unsigned int *blockDim_x, unsigned int *blockDim_y, unsigned int *blockDim_z,
                                               size_t *sharedMemBytes, void **stream) {
    if (gridDim_x)     *gridDim_x = g_kernel_config.gridDim_x;
    if (gridDim_y)     *gridDim_y = g_kernel_config.gridDim_y;
    if (gridDim_z)     *gridDim_z = g_kernel_config.gridDim_z;
    if (blockDim_x)    *blockDim_x = g_kernel_config.blockDim_x;
    if (blockDim_y)    *blockDim_y = g_kernel_config.blockDim_y;
    if (blockDim_z)    *blockDim_z = g_kernel_config.blockDim_z;
    if (sharedMemBytes) *sharedMemBytes = g_kernel_config.sharedMem;
    if (stream)        *stream = g_kernel_config.stream;
    return cudaSuccess;
}

/* ── Texture / Surface objects (NGX / DLSS) ────────────────────────────────── */

cudaError_t WINAPI cudaCreateTextureObject(cudaTextureObject_t *texObj,
                                            const cudaResourceDesc *resDesc,
                                            const cudaTextureDesc *texDesc,
                                            const void *texView) {
    if (!texObj) return set_last_error(cudaErrorInvalidValue);
    *texObj = (cudaTextureObject_t)(uintptr_t)(g_next_handle_id++);
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaDestroyTextureObject(cudaTextureObject_t texObj) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaCreateSurfaceObject(cudaSurfaceObject_t *surfObj,
                                            const cudaResourceDesc *resDesc) {
    if (!surfObj) return set_last_error(cudaErrorInvalidValue);
    *surfObj = (cudaSurfaceObject_t)(uintptr_t)(g_next_handle_id++);
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaDestroySurfaceObject(cudaSurfaceObject_t surfObj) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaGetTextureObjectResourceDesc(cudaResourceDesc *resDesc,
                                                     cudaTextureObject_t texObj) {
    if (resDesc) {
        memset(resDesc, 0, sizeof(cudaResourceDesc));
        resDesc->resType = cudaResourceTypeArray;
    }
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaGetTextureObjectResourceViewDesc(void *resViewDesc,
                                                         cudaTextureObject_t texObj) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaGetTextureObjectTextureDesc(cudaTextureDesc *texDesc,
                                                    cudaTextureObject_t texObj) {
    if (texDesc) memset(texDesc, 0, sizeof(cudaTextureDesc));
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaGetSurfaceObjectResourceDesc(cudaResourceDesc *resDesc,
                                                     cudaSurfaceObject_t surfObj) {
    if (resDesc) {
        memset(resDesc, 0, sizeof(cudaResourceDesc));
        resDesc->resType = cudaResourceTypeArray;
    }
    return set_last_error(cudaSuccess);
}

/* ── Peer access ───────────────────────────────────────────────────────────── */

cudaError_t WINAPI cudaDeviceCanAccessPeer(int *canAccess, int device, int peerDevice) {
    if (canAccess) *canAccess = 1;
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaDeviceEnablePeerAccess(int peerDevice, unsigned int flags) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaDeviceDisablePeerAccess(int peerDevice) {
    return set_last_error(cudaSuccess);
}

/* ── Pointer attributes ────────────────────────────────────────────────────── */

cudaError_t WINAPI cudaPointerGetAttributes(void *attributes, const void *ptr) {
    return set_last_error(cudaSuccess);
}

/* ── IPC ───────────────────────────────────────────────────────────────────── */

cudaError_t WINAPI cudaIpcGetMemHandle(void *handle, void *devPtr) {
    memset(handle, 0, 64);
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaIpcOpenMemHandle(void **devPtr, void *handle, unsigned int flags) {
    if (devPtr) *devPtr = NULL;
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaIpcCloseMemHandle(void *devPtr) {
    return set_last_error(cudaSuccess);
}

/* ── Profiling ─────────────────────────────────────────────────────────────── */

cudaError_t WINAPI cudaProfilerStart(void) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaProfilerStop(void) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaProfilerInitialize(const char *configFile, const char *outputFile,
                                           int outputMode) {
    return set_last_error(cudaSuccess);
}

/* ── Miscellaneous ─────────────────────────────────────────────────────────── */

cudaError_t WINAPI cudaDeviceGetByPCIBusId(int *device, const char *pciBusId) {
    if (device) *device = 0;
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaDeviceGetPCIBusId(char *pciBusId, int len, int device) {
    if (pciBusId && len > 0) snprintf(pciBusId, len, "0000:00:00.0");
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaDeviceSetCacheConfig(int config) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaDeviceSetSharedMemConfig(int config) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaDeviceGetLimit(size_t *pValue, int limit) {
    if (pValue) *pValue = 0;
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaDeviceSetLimit(int limit, size_t value) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaGetSymbolAddress(void **devPtr, const void *symbol) {
    if (devPtr) *devPtr = (void *)0xDEAD0000;
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaGetSymbolSize(size_t *size, const void *symbol) {
    if (size) *size = 0;
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaMemcpyToSymbol(const void *symbol, const void *src,
                                       size_t count, size_t offset,
                                       cudaMemcpyKind kind) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaMemcpyFromSymbol(void *dst, const void *symbol,
                                         size_t count, size_t offset,
                                         cudaMemcpyKind kind) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaMemcpyToSymbolAsync(const void *symbol, const void *src,
                                            size_t count, size_t offset,
                                            cudaMemcpyKind kind, cudaStream_t stream) {
    return cudaMemcpyToSymbol(symbol, src, count, offset, kind);
}

cudaError_t WINAPI cudaMemcpyFromSymbolAsync(void *dst, const void *symbol,
                                              size_t count, size_t offset,
                                              cudaMemcpyKind kind, cudaStream_t stream) {
    return cudaMemcpyFromSymbol(dst, symbol, count, offset, kind);
}

cudaError_t WINAPI cudaMemset2D(void *devPtr, size_t pitch, int value,
                                 size_t width, size_t height) {
    if (!devPtr) return set_last_error(cudaErrorInvalidValue);
    size_t row;
    for (row = 0; row < height; row++)
        memset((unsigned char *)devPtr + row * pitch, value, width);
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaMemset3D(cudaPitchedPtr pitchedDevPtr, int value,
                                 cudaExtent extent) {
    size_t y;
    for (y = 0; y < extent.height; y++)
        memset((unsigned char *)pitchedDevPtr.ptr + y * pitchedDevPtr.pitch,
               value, extent.width);
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaMemcpy3D(const cudaMemcpy3DParms *p) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaThreadSynchronize(void) {
    return cudaDeviceSynchronize();
}

cudaError_t WINAPI cudaThreadExit(void) {
    return set_last_error(cudaSuccess);
}

cudaError_t WINAPI cudaStreamCreateWithPriority(cudaStream_t *stream,
                                                  unsigned int flags, int priority) {
    return cudaStreamCreate(stream);
}
