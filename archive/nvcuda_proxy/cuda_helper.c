/* Helper natif Linux : exécute des commandes CUDA et retourne les résultats */
/* Accepte une séquence de commandes en un seul appel */
/* Usage: ./cuda_helper "cuInit 0;cuDeviceGetCount" */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <cuda.h>

static void *libcuda = NULL;
static int initialized = 0;

static void ensure_libcuda() {
    if (!libcuda) {
        libcuda = dlopen("libcuda.so", RTLD_NOW | RTLD_GLOBAL);
        if (!libcuda) {
            fprintf(stderr, "ERROR: dlopen(libcuda.so) failed: %s\n", dlerror());
            exit(1);
        }
    }
}

static int run_command(const char *cmd) {
    /* Parse: command arg1 arg2 ... */
    char cmd_copy[4096];
    strncpy(cmd_copy, cmd, sizeof(cmd_copy)-1);
    cmd_copy[sizeof(cmd_copy)-1] = '\0';

    char *args[32];
    int argc = 0;
    char *tok = strtok(cmd_copy, " \t");
    while (tok && argc < 32) {
        args[argc++] = tok;
        tok = strtok(NULL, " \t");
    }

    if (argc == 0) return 0;

    const char *name = args[0];

    if (strcmp(name, "cuInit") == 0) {
        unsigned int flags = (argc > 1) ? atoi(args[1]) : 0;
        if (!libcuda) ensure_libcuda();
        typedef int (*fn_t)(unsigned int);
        fn_t fn = (fn_t)dlsym(libcuda, "cuInit");
        if (!fn) { fprintf(stderr, "ERROR: cuInit not found\n"); return 1; }
        int r = fn(flags);
        printf("RESULT:%s=%d\n", name, r);
        initialized = (r == 0);
        return (r == 0) ? 0 : 1;
    }

    if (!initialized) {
        /* Auto-init for chained commands */
        if (!libcuda) ensure_libcuda();
        typedef int (*fn_t)(unsigned int);
        fn_t fn = (fn_t)dlsym(libcuda, "cuInit");
        if (fn) fn(0);
        initialized = 1;
    }

    if (strcmp(name, "cuDeviceGetCount") == 0) {
        typedef int (*fn_t)(int *);
        fn_t fn = (fn_t)dlsym(libcuda, "cuDeviceGetCount");
        int count;
        int r = fn(&count);
        printf("RESULT:%s=%d\n", name, r);
        if (r == 0) printf("DATA:count=%d\n", count);
        return 0;
    }

    if (strcmp(name, "cuDeviceGet") == 0) {
        int ordinal = (argc > 1) ? atoi(args[1]) : 0;
        typedef int (*fn_t)(int *, int);
        fn_t fn = (fn_t)dlsym(libcuda, "cuDeviceGet");
        int dev;
        int r = fn(&dev, ordinal);
        printf("RESULT:%s=%d\n", name, r);
        if (r == 0) printf("DATA:device=%d\n", dev);
        return 0;
    }

    if (strcmp(name, "cuDeviceGetName") == 0) {
        int dev = (argc > 1) ? atoi(args[1]) : 0;
        typedef int (*fn_t)(char *, int, int);
        fn_t fn = (fn_t)dlsym(libcuda, "cuDeviceGetName");
        char buf[256] = {0};
        int r = fn(buf, 256, dev);
        printf("RESULT:%s=%d\n", name, r);
        if (r == 0) printf("DATA:name=%s\n", buf);
        return 0;
    }

    if (strcmp(name, "cuCtxCreate") == 0) {
        int dev = (argc > 1) ? atoi(args[1]) : 0;
        typedef int (*fn_t)(CUcontext *, unsigned int, CUdevice);
        fn_t fn = (fn_t)dlsym(libcuda, "cuCtxCreate");
        CUcontext ctx;
        int r = fn(&ctx, 0, dev);
        printf("RESULT:%s=%d\n", name, r);
        if (r == 0) printf("DATA:ctx=%lu\n", (unsigned long)(uintptr_t)ctx);
        return 0;
    }

    if (strcmp(name, "cuMemAlloc") == 0) {
        size_t size = (argc > 1) ? atol(args[1]) : 1024;
        typedef int (*fn_t)(CUdeviceptr *, size_t);
        fn_t fn = (fn_t)dlsym(libcuda, "cuMemAlloc");
        CUdeviceptr ptr;
        int r = fn(&ptr, size);
        printf("RESULT:%s=%d\n", name, r);
        if (r == 0) printf("DATA:ptr=%llu\n", (unsigned long long)ptr);
        return 0;
    }

    fprintf(stderr, "ERROR: unknown command %s\n", name);
    return 1;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s '<cmd1> [args];<cmd2> [args];...'\n", argv[0]);
        fprintf(stderr, "Examples:\n");
        fprintf(stderr, "  %s 'cuInit 0'\n", argv[0]);
        fprintf(stderr, "  %s 'cuDeviceGetCount'\n", argv[0]);
        fprintf(stderr, "  %s 'cuDeviceGet 0;cuDeviceGetName 0'\n", argv[0]);
        return 1;
    }

    /* Process commands separated by ; */
    char cmds[65536];
    strncpy(cmds, argv[1], sizeof(cmds)-1);
    cmds[sizeof(cmds)-1] = '\0';

    char *saveptr;
    char *cmd = strtok_r(cmds, ";", &saveptr);
    while (cmd) {
        /* Skip leading whitespace */
        while (*cmd == ' ' || *cmd == '\t') cmd++;
        if (*cmd) {
            if (run_command(cmd) != 0) return 1;
        }
        cmd = strtok_r(NULL, ";", &saveptr);
    }

    return 0;
}
