/* Test minimal: appeler CUDA Driver API directement via libcuda.so */
#include <stdio.h>
#include <dlfcn.h>
#include <cuda.h>   /* ou on utilise les types à la main */

typedef int (*cuInit_t)(unsigned int);
typedef int (*cuDeviceGetCount_t)(int *);
typedef int (*cuDeviceGet_t)(int *, int);
typedef int (*cuDeviceGetName_t)(char *, int, int);
typedef int (*cuCtxCreate_t)(void *, unsigned int, int);
typedef int (*cuMemAlloc_t)(void *, size_t);
typedef int (*cuMemcpyHtoD_t)(void *, void *, size_t);

int main() {
    void *handle = dlopen("libcuda.so", RTLD_NOW | RTLD_GLOBAL);
    if (!handle) {
        fprintf(stderr, "❌ dlopen(libcuda.so) failed: %s\n", dlerror());
        return 1;
    }
    printf("✅ libcuda.so loaded at %p\n", handle);

    cuInit_t cuInit = (cuInit_t)dlsym(handle, "cuInit");
    cuDeviceGetCount_t cuDeviceGetCount = (cuDeviceGetCount_t)dlsym(handle, "cuDeviceGetCount");
    cuDeviceGet_t cuDeviceGet = (cuDeviceGet_t)dlsym(handle, "cuDeviceGet");
    cuDeviceGetName_t cuDeviceGetName = (cuDeviceGetName_t)dlsym(handle, "cuDeviceGetName");
    cuCtxCreate_t cuCtxCreate = (cuCtxCreate_t)dlsym(handle, "cuCtxCreate");
    cuMemAlloc_t cuMemAlloc = (cuMemAlloc_t)dlsym(handle, "cuMemAlloc");

    if (!cuInit || !cuDeviceGetCount || !cuDeviceGet || !cuDeviceGetName) {
        fprintf(stderr, "❌ Failed to resolve CUDA functions\n");
        dlclose(handle);
        return 1;
    }
    printf("✅ CUDA Driver API functions resolved\n");

    int ret = cuInit(0);
    printf("   cuInit(0) = %d (%s)\n", ret, ret == 0 ? "CUDA_SUCCESS" : "FAILED");
    if (ret != 0) return 1;

    int count;
    ret = cuDeviceGetCount(&count);
    printf("   Device count = %d\n", count);

    if (count > 0) {
        int dev;
        cuDeviceGet(&dev, 0);
        char name[256];
        cuDeviceGetName(name, 256, dev);
        printf("   GPU 0: %s\n", name);

        if (cuCtxCreate) {
            void *ctx;
            ret = cuCtxCreate(&ctx, 0, dev);
            printf("   cuCtxCreate = %d\n", ret);
        }
    }

    dlclose(handle);
    printf("\n✅ Test passed! libcuda.so is fully functional.\n");
    return 0;
}
