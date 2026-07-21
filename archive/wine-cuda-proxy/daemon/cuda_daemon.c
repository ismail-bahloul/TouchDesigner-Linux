/*
 * cuda_daemon.c - Native Linux CUDA proxy daemon for TouchDesigner under Wine
 *
 * Opens libcuda.so via dlopen(), listens on a named FIFO for JSON commands,
 * dispatches to the real CUDA Driver API, and returns JSON responses on a
 * separate response FIFO.
 *
 * Build: gcc -o cuda_daemon cuda_daemon.c -ldl
 * Usage: ./cuda_daemon [--foreground]
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/select.h>
#include <signal.h>
#include <errno.h>

/* ------------------------------------------------------------------ */
/* Constants                                                          */
/* ------------------------------------------------------------------ */
#define PIPE_CMD   "/tmp/cuda_daemon.pipe"
#define PIPE_RSP   "/tmp/cuda_daemon.rsp"
#define MAX_LINE   (1024 * 128)
#define MAX_RESP   (1024 * 128)
#define MAX_ARGS   16

/* ------------------------------------------------------------------ */
/* CUDA type shims (we do NOT include cuda.h)                         */
/* ------------------------------------------------------------------ */
typedef unsigned long long CUdeviceptr;
typedef int               CUresult;
typedef int               CUdevice;
typedef void             *CUcontext;
typedef void             *CUarray;
typedef void             *CUfunction;
typedef void             *CUstream;

typedef struct {
    unsigned int Width;
    unsigned int Height;
    unsigned int Format;
    unsigned int NumChannels;
} CUDA_ARRAY_DESCRIPTOR;

/* ------------------------------------------------------------------ */
/* Global state                                                       */
/* ------------------------------------------------------------------ */
static void    *g_libcuda   = NULL;
static int      g_cmd_fd    = -1;
static int      g_rsp_fd    = -1;
static volatile int g_running = 1;

/* ------------------------------------------------------------------ */
/* Typedefs for the CUDA functions we proxy                           */
/* ------------------------------------------------------------------ */
typedef CUresult (*cuInit_t)(unsigned int Flags);
typedef CUresult (*cuDeviceGetCount_t)(int *pCount);
typedef CUresult (*cuDeviceGet_t)(CUdevice *pDevice, int ordinal);
typedef CUresult (*cuDeviceGetName_t)(char *pName, int len, CUdevice dev);
typedef CUresult (*cuCtxCreate_t)(CUcontext *pCtx, unsigned int flags, CUdevice dev);
typedef CUresult (*cuMemAlloc_t)(CUdeviceptr *dptr, size_t bytesize);
typedef CUresult (*cuMemFree_t)(CUdeviceptr dptr);
typedef CUresult (*cuGetErrorString_t)(CUresult error, const char **ppStr);
typedef CUresult (*cuArrayCreate_t)(CUarray *pHandle, const CUDA_ARRAY_DESCRIPTOR *pAllocateArray);
typedef CUresult (*cuArrayDestroy_t)(CUarray hArray);
typedef CUresult (*cuLaunchKernel_t)(CUfunction f,
                     unsigned int gridDimX, unsigned int gridDimY, unsigned int gridDimZ,
                     unsigned int blockDimX, unsigned int blockDimY, unsigned int blockDimZ,
                     unsigned int sharedMemBytes, CUstream hStream,
                     void **kernelParams, void **extra);
typedef CUresult (*cuStreamCreate_t)(CUstream *phStream, unsigned int Flags);
typedef CUresult (*cuStreamDestroy_t)(CUstream hStream);

/* ------------------------------------------------------------------ */
/* Resolved function pointers                                         */
/* ------------------------------------------------------------------ */
static cuInit_t             d_cuInit            = NULL;
static cuDeviceGetCount_t   d_cuDeviceGetCount  = NULL;
static cuDeviceGet_t        d_cuDeviceGet       = NULL;
static cuDeviceGetName_t    d_cuDeviceGetName   = NULL;
static cuCtxCreate_t        d_cuCtxCreate       = NULL;
static cuMemAlloc_t         d_cuMemAlloc        = NULL;
static cuMemFree_t          d_cuMemFree         = NULL;
static cuGetErrorString_t   d_cuGetErrorString  = NULL;
static cuArrayCreate_t      d_cuArrayCreate     = NULL;
static cuArrayDestroy_t     d_cuArrayDestroy    = NULL;
static cuLaunchKernel_t     d_cuLaunchKernel    = NULL;
static cuStreamCreate_t     d_cuStreamCreate    = NULL;
static cuStreamDestroy_t    d_cuStreamDestroy   = NULL;

/* ------------------------------------------------------------------ */
/* Signal handler                                                     */
/* ------------------------------------------------------------------ */
static void handle_signal(int sig)
{
    (void)sig;
    g_running = 0;
}

/* ------------------------------------------------------------------ */
/* JSON helpers                                                       */
/* ------------------------------------------------------------------ */

static const char *json_seek_key(const char *json, const char *key)
{
    char pattern[512];
    snprintf(pattern, sizeof(pattern), "\"%s\"", key);
    const char *p = strstr(json, pattern);
    if (!p) return NULL;
    p += strlen(pattern);
    while (*p && (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r')) p++;
    if (*p != ':') return NULL;
    p++;
    while (*p && (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r')) p++;
    return p;
}

static int json_get_string(const char *json, const char *key,
                           char *out, int out_size)
{
    const char *p = json_seek_key(json, key);
    if (!p || *p != '"') return -1;
    p++;
    int i = 0;
    while (*p && *p != '"' && i < out_size - 1) {
        if (*p == '\\' && *(p+1)) p++;
        out[i++] = *p++;
    }
    out[i] = '\0';
    return (*p == '"') ? 0 : -1;
}

static int json_get_int_array(const char *json, const char *key,
                              long long *out, int max_count)
{
    const char *p = json_seek_key(json, key);
    if (!p || *p != '[') return -1;
    p++;
    int count = 0;
    while (*p && *p != ']' && count < max_count) {
        while (*p && (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r' || *p == ',')) p++;
        if (*p == ']') break;
        out[count++] = strtoll(p, (char **)&p, 10);
        while (*p && *p != ',' && *p != ']' && *p != ' ' && *p != '\t' && *p != '\n' && *p != '\r') p++;
    }
    return count;
}

/* Write a JSON response line to the response pipe. */
static void send_response(CUresult result, const char *data_json_fragment)
{
    char resp[MAX_RESP];
    int n;
    if (data_json_fragment && data_json_fragment[0])
        n = snprintf(resp, sizeof(resp),
                     "{\"result\":%d,%s}\n",
                     (int)result, data_json_fragment);
    else
        n = snprintf(resp, sizeof(resp), "{\"result\":%d}\n",
                     (int)result);
    if (n < 0 || (size_t)n >= sizeof(resp)) return;

    const char *ptr = resp;
    int remaining = n;
    while (remaining > 0) {
        int written = (int)write(g_rsp_fd, ptr, (size_t)remaining);
        if (written <= 0) {
            if (errno == EINTR) continue;
            break;
        }
        ptr       += written;
        remaining -= written;
    }
}

/* ------------------------------------------------------------------ */
/* Command handlers                                                   */
/* ------------------------------------------------------------------ */

static CUresult cmd_cuInit(const long long *args, int nargs,
                           char *data_frag, int data_frag_size)
{
    (void)data_frag; (void)data_frag_size;
    if (nargs < 1 || !d_cuInit) return 999;
    return d_cuInit((unsigned int)args[0]);
}

static CUresult cmd_cuDeviceGetCount(const long long *args, int nargs,
                                     char *data_frag, int data_frag_size)
{
    (void)args; (void)nargs;
    if (!d_cuDeviceGetCount) return 999;
    int count = 0;
    CUresult res = d_cuDeviceGetCount(&count);
    if (res == 0)
        snprintf(data_frag, (size_t)data_frag_size,
                 "\"data\":{\"count\":%d}", count);
    return res;
}

static CUresult cmd_cuDeviceGet(const long long *args, int nargs,
                                char *data_frag, int data_frag_size)
{
    if (nargs < 1 || !d_cuDeviceGet) return 999;
    CUdevice dev = 0;
    CUresult res = d_cuDeviceGet(&dev, (int)args[0]);
    if (res == 0)
        snprintf(data_frag, (size_t)data_frag_size,
                 "\"data\":{\"device\":%d}", (int)dev);
    return res;
}

static CUresult cmd_cuDeviceGetName(const long long *args, int nargs,
                                    char *data_frag, int data_frag_size)
{
    if (nargs < 2 || !d_cuDeviceGetName) return 999;
    char name[1024];
    CUresult res = d_cuDeviceGetName(name, (int)sizeof(name),
                                     (CUdevice)args[0]);
    if (res == 0) {
        char escaped[2048]; int j = 0;
        for (int i = 0; name[i] && j < (int)sizeof(escaped)-4; i++) {
            if (name[i] == '\\' || name[i] == '"') escaped[j++] = '\\';
            escaped[j++] = name[i];
        }
        escaped[j] = '\0';
        snprintf(data_frag, (size_t)data_frag_size,
                 "\"data\":{\"name\":\"%s\"}", escaped);
    }
    return res;
}

static CUresult cmd_cuCtxCreate(const long long *args, int nargs,
                                char *data_frag, int data_frag_size)
{
    if (nargs < 2 || !d_cuCtxCreate) return 999;
    CUcontext ctx = NULL;
    CUresult res = d_cuCtxCreate(&ctx, (unsigned int)args[0],
                                 (CUdevice)args[1]);
    if (res == 0)
        snprintf(data_frag, (size_t)data_frag_size,
                 "\"data\":{\"context\":%llu}", (unsigned long long)ctx);
    return res;
}

static CUresult cmd_cuMemAlloc(const long long *args, int nargs,
                               char *data_frag, int data_frag_size)
{
    if (nargs < 1 || !d_cuMemAlloc) return 999;
    CUdeviceptr ptr = 0;
    CUresult res = d_cuMemAlloc(&ptr, (size_t)args[0]);
    if (res == 0)
        snprintf(data_frag, (size_t)data_frag_size,
                 "\"data\":{\"ptr\":%llu}", (unsigned long long)ptr);
    return res;
}

static CUresult cmd_cuMemFree(const long long *args, int nargs,
                              char *data_frag, int data_frag_size)
{
    (void)data_frag; (void)data_frag_size;
    if (nargs < 1 || !d_cuMemFree) return 999;
    return d_cuMemFree((CUdeviceptr)((unsigned long long)args[0]));
}

static CUresult cmd_cuGetErrorString(const long long *args, int nargs,
                                     char *data_frag, int data_frag_size)
{
    if (nargs < 1) return 999;
    if (d_cuGetErrorString) {
        const char *str = NULL;
        CUresult res = d_cuGetErrorString((CUresult)args[0], &str);
        if (res == 0 && str) {
            char escaped[1024]; int j = 0;
            for (int i = 0; str[i] && j < (int)sizeof(escaped)-4; i++) {
                if (str[i] == '\\' || str[i] == '"') escaped[j++] = '\\';
                escaped[j++] = str[i];
            }
            escaped[j] = '\0';
            snprintf(data_frag, (size_t)data_frag_size,
                     "\"data\":{\"str\":\"%s\"}", escaped);
            return 0;
        }
        return res;
    }
    const char *str = "Unknown CUDA error";
    switch ((int)args[0]) {
        case 0:   str = "CUDA_SUCCESS"; break;
        case 1:   str = "CUDA_ERROR_NOT_INITIALIZED"; break;
        case 2:   str = "CUDA_ERROR_DEINITIALIZED"; break;
        case 100: str = "CUDA_ERROR_NO_DEVICE"; break;
        case 101: str = "CUDA_ERROR_INVALID_DEVICE"; break;
        case 801: str = "CUDA_ERROR_NOT_SUPPORTED"; break;
    }
    snprintf(data_frag, (size_t)data_frag_size,
             "\"data\":{\"str\":\"%s\"}", str);
    return 0;
}

static CUresult cmd_cuArrayCreate(const long long *args, int nargs,
                                  char *data_frag, int data_frag_size)
{
    if (nargs < 4 || !d_cuArrayCreate) return 999;
    CUDA_ARRAY_DESCRIPTOR desc;
    desc.Width       = (unsigned int)args[0];
    desc.Height      = (unsigned int)args[1];
    desc.Format      = (unsigned int)args[2];
    desc.NumChannels = (unsigned int)args[3];
    CUarray arr = NULL;
    CUresult res = d_cuArrayCreate(&arr, &desc);
    if (res == 0)
        snprintf(data_frag, (size_t)data_frag_size,
                 "\"data\":{\"array\":%llu}", (unsigned long long)arr);
    return res;
}

static CUresult cmd_cuArrayDestroy(const long long *args, int nargs,
                                   char *data_frag, int data_frag_size)
{
    (void)data_frag; (void)data_frag_size;
    if (nargs < 1 || !d_cuArrayDestroy) return 999;
    return d_cuArrayDestroy((CUarray)((unsigned long long)args[0]));
}

static CUresult cmd_cuLaunchKernel(const long long *args, int nargs,
                                   char *data_frag, int data_frag_size)
{
    (void)data_frag; (void)data_frag_size; (void)args; (void)nargs;
    return 999;
}

static CUresult cmd_cuStreamCreate(const long long *args, int nargs,
                                   char *data_frag, int data_frag_size)
{
    if (nargs < 1 || !d_cuStreamCreate) return 999;
    CUstream stream = NULL;
    CUresult res = d_cuStreamCreate(&stream, (unsigned int)args[0]);
    if (res == 0)
        snprintf(data_frag, (size_t)data_frag_size,
                 "\"data\":{\"stream\":%llu}", (unsigned long long)stream);
    return res;
}

static CUresult cmd_cuStreamDestroy(const long long *args, int nargs,
                                    char *data_frag, int data_frag_size)
{
    (void)data_frag; (void)data_frag_size;
    if (nargs < 1 || !d_cuStreamDestroy) return 999;
    return d_cuStreamDestroy((CUstream)((unsigned long long)args[0]));
}

/* ------------------------------------------------------------------ */
/* Dispatch table                                                     */
/* ------------------------------------------------------------------ */
typedef struct {
    const char *name;
    CUresult (*handler)(const long long *args, int nargs,
                        char *data_frag, int data_frag_size);
} CommandEntry;

static const CommandEntry g_commands[] = {
    {"cuInit",            cmd_cuInit},
    {"cuDeviceGetCount",  cmd_cuDeviceGetCount},
    {"cuDeviceGet",       cmd_cuDeviceGet},
    {"cuDeviceGetName",   cmd_cuDeviceGetName},
    {"cuCtxCreate",       cmd_cuCtxCreate},
    {"cuMemAlloc",        cmd_cuMemAlloc},
    {"cuMemFree",         cmd_cuMemFree},
    {"cuGetErrorString",  cmd_cuGetErrorString},
    {"cuArrayCreate",     cmd_cuArrayCreate},
    {"cuArrayDestroy",    cmd_cuArrayDestroy},
    {"cuLaunchKernel",    cmd_cuLaunchKernel},
    {"cuStreamCreate",    cmd_cuStreamCreate},
    {"cuStreamDestroy",   cmd_cuStreamDestroy},
    {NULL, NULL}
};

/* ------------------------------------------------------------------ */
/* Resolve all CUDA symbols from the loaded libcuda.so                */
/* ------------------------------------------------------------------ */
static int resolve_symbols(void)
{
    d_cuInit           = (cuInit_t)dlsym(g_libcuda, "cuInit");
    d_cuDeviceGetCount = (cuDeviceGetCount_t)dlsym(g_libcuda, "cuDeviceGetCount");
    d_cuDeviceGet      = (cuDeviceGet_t)dlsym(g_libcuda, "cuDeviceGet");
    d_cuDeviceGetName  = (cuDeviceGetName_t)dlsym(g_libcuda, "cuDeviceGetName");
    d_cuCtxCreate      = (cuCtxCreate_t)dlsym(g_libcuda, "cuCtxCreate");
    d_cuMemAlloc       = (cuMemAlloc_t)dlsym(g_libcuda, "cuMemAlloc");
    d_cuMemFree        = (cuMemFree_t)dlsym(g_libcuda, "cuMemFree");
    d_cuGetErrorString = (cuGetErrorString_t)dlsym(g_libcuda, "cuGetErrorString");
    d_cuArrayCreate    = (cuArrayCreate_t)dlsym(g_libcuda, "cuArrayCreate");
    d_cuArrayDestroy   = (cuArrayDestroy_t)dlsym(g_libcuda, "cuArrayDestroy");
    d_cuLaunchKernel   = (cuLaunchKernel_t)dlsym(g_libcuda, "cuLaunchKernel");
    d_cuStreamCreate   = (cuStreamCreate_t)dlsym(g_libcuda, "cuStreamCreate");
    d_cuStreamDestroy  = (cuStreamDestroy_t)dlsym(g_libcuda, "cuStreamDestroy");

    dlerror(); /* clear error state */
    return 0;
}

/* ------------------------------------------------------------------ */
/* Process a single JSON request line.                                */
/* ------------------------------------------------------------------ */
static int process_request(const char *line)
{
    char cmd[256];
    long long args[MAX_ARGS];

    if (json_get_string(line, "cmd", cmd, (int)sizeof(cmd)) != 0) {
        send_response(999, NULL);
        return 0;
    }

    int nargs = json_get_int_array(line, "args", args, MAX_ARGS);
    if (nargs < 0) nargs = 0;

    for (const CommandEntry *e = g_commands; e->name; e++) {
        if (strcmp(cmd, e->name) == 0) {
            char data_frag[MAX_RESP];
            data_frag[0] = '\0';
            CUresult res = e->handler(args, nargs, data_frag,
                                      (int)sizeof(data_frag));
            send_response(res, data_frag);
            return 0;
        }
    }

    send_response(999, NULL);
    return 0;
}

/* ------------------------------------------------------------------ */
/* Main loop: read from cmd pipe, write response to rsp pipe          */
/* ------------------------------------------------------------------ */
static void main_loop(void)
{
    char buf[MAX_LINE * 2];
    size_t buf_pos = 0;
    char line[MAX_LINE];

    while (g_running) {
        fd_set rfds;
        FD_ZERO(&rfds);
        FD_SET(g_cmd_fd, &rfds);

        struct timeval tv;
        tv.tv_sec  = 1;
        tv.tv_usec = 0;

        int ret = select(g_cmd_fd + 1, &rfds, NULL, NULL, &tv);
        if (ret < 0) {
            if (errno == EINTR) continue;
            break;
        }
        if (ret == 0) continue;

        ssize_t n = read(g_cmd_fd, buf + buf_pos,
                         sizeof(buf) - buf_pos - 1);
        if (n <= 0) {
            if (n == 0) {
                fprintf(stderr, "Command pipe closed, exiting.\n");
                break;
            }
            if (errno == EINTR) continue;
            break;
        }

        buf_pos += (size_t)n;
        buf[buf_pos] = '\0';

        char *cr;
        while ((cr = strchr(buf, '\n')) != NULL) {
            *cr = '\0';
            size_t len = (size_t)(cr - buf);
            if (len > 0 && len < MAX_LINE) {
                memcpy(line, buf, len);
                line[len] = '\0';
                process_request(line);
            }
            buf_pos -= (len + 1);
            if (buf_pos > 0)
                memmove(buf, cr + 1, buf_pos);
            else
                buf[0] = '\0';
        }

        if (buf_pos >= sizeof(buf) - 1) {
            buf_pos = 0;
            buf[0] = '\0';
        }
    }
}

/* ------------------------------------------------------------------ */
/* main                                                                */
/* ------------------------------------------------------------------ */
int main(int argc, char **argv)
{
    int foreground = 0;

    if (argc > 1 && strcmp(argv[1], "--foreground") == 0)
        foreground = 1;

    /* ---- Load libcuda.so ---- */
    fprintf(stderr, "Loading libcuda.so...\n");
    g_libcuda = dlopen("libcuda.so", RTLD_LAZY | RTLD_LOCAL);
    if (!g_libcuda) {
        fprintf(stderr, "ERROR: Failed to load libcuda.so: %s\n", dlerror());
        return 1;
    }
    resolve_symbols();

    /* ---- Create FIFOs ---- */
    unlink(PIPE_CMD);
    unlink(PIPE_RSP);

    if (mkfifo(PIPE_CMD, 0666) != 0) {
        fprintf(stderr, "ERROR: mkfifo(%s) failed: %s\n",
                PIPE_CMD, strerror(errno));
        return 1;
    }
    if (mkfifo(PIPE_RSP, 0666) != 0) {
        fprintf(stderr, "ERROR: mkfifo(%s) failed: %s\n",
                PIPE_RSP, strerror(errno));
        unlink(PIPE_CMD);
        return 1;
    }

    /* ---- Daemonize (unless --foreground) ---- */
    if (!foreground) {
        pid_t pid = fork();
        if (pid < 0) {
            fprintf(stderr, "ERROR: fork() failed: %s\n", strerror(errno));
            return 1;
        }
        if (pid > 0) {
            sleep(1);
            fprintf(stderr, "Daemon started (PID %d)\n", (int)pid);
            return 0;
        }
        if (setsid() < 0) {
            fprintf(stderr, "ERROR: setsid() failed: %s\n", strerror(errno));
            return 1;
        }
        chdir("/");
        int null_fd = open("/dev/null", O_RDWR);
        if (null_fd >= 0) {
            dup2(null_fd, STDIN_FILENO);
            dup2(null_fd, STDOUT_FILENO);
            dup2(null_fd, STDERR_FILENO);
            if (null_fd > 2) close(null_fd);
        }
    }

    /* ---- Signal handlers ---- */
    signal(SIGTERM, handle_signal);
    signal(SIGINT,  handle_signal);

    /* ---- Open FIFOs (O_RDWR avoids blocking open) ---- */
    g_cmd_fd = open(PIPE_CMD, O_RDWR);
    if (g_cmd_fd < 0) {
        fprintf(stderr, "ERROR: open(%s) failed: %s\n",
                PIPE_CMD, strerror(errno));
        return 1;
    }
    g_rsp_fd = open(PIPE_RSP, O_RDWR);
    if (g_rsp_fd < 0) {
        fprintf(stderr, "ERROR: open(%s) failed: %s\n",
                PIPE_RSP, strerror(errno));
        return 1;
    }

    fprintf(stderr, "CUDA daemon ready (cmd=%s, rsp=%s)\n",
            PIPE_CMD, PIPE_RSP);

    /* ---- Main loop ---- */
    main_loop();

    /* ---- Cleanup ---- */
    close(g_cmd_fd);
    close(g_rsp_fd);
    unlink(PIPE_CMD);
    unlink(PIPE_RSP);
    if (g_libcuda) dlclose(g_libcuda);

    fprintf(stderr, "CUDA daemon exiting.\n");
    return 0;
}
