/* cuda_helper_pe.c — Windows PE version of cuda_helper
 * 
 * This is a PE executable that loads nvcuda.dll (our proxy)
 * and calls CUDA functions. Used for testing.
 * 
 * Compilation: x86_64-w64-mingw32-gcc -o cuda_helper_pe.exe cuda_helper_pe.c
 */

#include <windows.h>
#include <stdio.h>
#include <string.h>

typedef int (__stdcall *cuInit_t)(unsigned int);
typedef int (__stdcall *cuDeviceGetCount_t)(int *);
typedef int (__stdcall *cuDeviceGet_t)(int *, int);
typedef int (__stdcall *cuDeviceGetName_t)(char *, int, int);

int main(int argc, char **argv) {
    HMODULE nv = LoadLibraryA("nvcuda.dll");
    if (!nv) {
        printf("ERROR: LoadLibrary(nvcuda.dll) failed\n");
        return 1;
    }
    printf("nvcuda.dll loaded: %p\n", nv);

    cuInit_t cuInit = (cuInit_t)GetProcAddress(nv, "cuInit");
    if (!cuInit) { printf("ERROR: cuInit not found\n"); return 1; }

    int r = cuInit(0);
    printf("cuInit(0) = %d\n", r);

    if (r == 0) {
        cuDeviceGetCount_t cuDeviceGetCount = (cuDeviceGetCount_t)GetProcAddress(nv, "cuDeviceGetCount");
        int count;
        r = cuDeviceGetCount(&count);
        printf("Device count = %d\n", count);

        if (count > 0) {
            cuDeviceGet_t cuDeviceGet = (cuDeviceGet_t)GetProcAddress(nv, "cuDeviceGet");
            cuDeviceGetName_t cuDeviceGetName = (cuDeviceGetName_t)GetProcAddress(nv, "cuDeviceGetName");
            int dev;
            cuDeviceGet(&dev, 0);
            char name[256];
            cuDeviceGetName(name, 256, dev);
            printf("GPU 0: %s\n", name);
        }
    }

    FreeLibrary(nv);
    return 0;
}
