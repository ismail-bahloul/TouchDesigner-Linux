/* nvcuda.dll - Windows PE DLL compiled with mingw-w64
 * Pont vers libcuda.so via le helper natif Linux
 * Chaque fonction CUDA Driver API lance cuda_helper et parse le résultat */

#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* ── Configuration ───────────────────────────────────────────────────────── */

/* Chemin vers le helper (à ajuster selon l'install) */
static char HELPER_PATH[1024] = "";

/* ── Helper: exécute une commande et retourne le code RESULT ─────────────── */

static int run_helper(const char *cmd, int *out_data_count) {
    char full_cmd[8192];
    char line[4096];
    char temp_file[MAX_PATH];
    int result = -1;
    int data_count = 0;

    /* Créer un fichier temporaire pour stdout */
    GetTempPathA(sizeof(temp_file), temp_file);
    GetTempFileNameA(temp_file, "cuda", 0, temp_file);

    /* Construire la commande */
    snprintf(full_cmd, sizeof(full_cmd), "\"%s\" \"%s\" > \"%s\" 2> nul",
             HELPER_PATH, cmd, temp_file);

    /* Lancer le helper */
    STARTUPINFOA si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    BOOL ok = CreateProcessA(NULL, full_cmd, NULL, NULL, FALSE,
                             CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
    if (!ok) {
        /* Helper pas trouvé ? On essaie de le trouver */
        DeleteFileA(temp_file);
        return -1;
    }

    /* Attendre la fin */
    WaitForSingleObject(pi.hProcess, 10000);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    /* Lire le résultat */
    FILE *f = fopen(temp_file, "r");
    if (f) {
        while (fgets(line, sizeof(line), f)) {
            /* Enlever le \n */
            size_t len = strlen(line);
            if (len > 0 && line[len-1] == '\n') line[len-1] = '\0';

            if (strncmp(line, "RESULT:", 7) == 0) {
                /* Format: RESULT:cmdname=code */
                char *eq = strrchr(line, '=');
                if (eq) result = atoi(eq + 1);
            } else if (strncmp(line, "DATA:", 5) == 0) {
                data_count++;
            }
        }
        fclose(f);
    }

    DeleteFileA(temp_file);
    if (out_data_count) *out_data_count = data_count;
    return result;
}

/* ── Initialisation de la DLL ────────────────────────────────────────────── */

BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved) {
    if (fdwReason == DLL_PROCESS_ATTACH) {
        /* Déterminer le chemin du helper */
        GetModuleFileNameA(hinstDLL, HELPER_PATH, sizeof(HELPER_PATH));
        char *last_slash = strrchr(HELPER_PATH, '\\');
        if (last_slash) {
            last_slash[1] = '\0';
            strcat(HELPER_PATH, "cuda_helper.exe");
        } else {
            strcpy(HELPER_PATH, "cuda_helper.exe");
        }
        /* Alternative : le helper est dans le PATH */
        DisableThreadLibraryCalls(hinstDLL);
    }
    return TRUE;
}

/* ── Fonctions CUDA Driver API ───────────────────────────────────────────── */

/* Helper pour appeler une fonction simple */
static int cuda_simple(const char *cmd) {
    return run_helper(cmd, NULL);
}

/* cuInit : initialize CUDA driver */
CUresult CUDAAPI cuInit(unsigned int Flags) {
    char cmd[256];
    snprintf(cmd, sizeof(cmd), "cuInit %u", Flags);
    int r = cuda_simple(cmd);
    return (r < 0) ? CUDA_ERROR_NO_DEVICE : (CUresult)r;
}

/* cuDeviceGetCount */
CUresult CUDAAPI cuDeviceGetCount(int *count) {
    char cmd[256] = "cuDeviceGetCount";
    int data_count;
    int r = run_helper(cmd, &data_count);
    if (r == 0 && count) {
        /* On doit parser le DATA:count=N */
        /* Pour l'instant on retourne juste 0 et on parse dans une fonction dédiée */
    }
    return (r < 0) ? CUDA_ERROR_NO_DEVICE : (CUresult)r;
}

/* ── Export table ─────────────────────────────────────────────────────────── */

/* Les exports sont déclarés dans le .def ou via __declspec(dllexport) */
