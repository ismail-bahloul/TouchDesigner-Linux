# wine-cuda-proxy — PoC : CUDA sous Wine pour TouchDesigner

## Structure

```
wine-cuda-proxy/
├── daemon/                        ← ✅ Ce qui MARCHE
│   ├── cuda_daemon.c              ← Daemon Linux natif (dlopen libcuda.so)
│   ├── cuda_daemon                ← Binaire compilé
│   ├── nvcuda.dll                 ← DLL Windows (mingw) qui parle au daemon
│   └── Makefile                   ← Build du daemon + DLL
│
├── dlls/
│   ├── nvcuda/
│   │   ├── nvcuda_final.c         ← DLL unifiée (Driver + Runtime API)
│   │   └── Makefile.in            ← Pour intégration future dans Wine
│   └── cuda/
│       ├── cuda_runtime_pe.c      ← Version alternative de cuda.dll
│       ├── cuda.spec              ← Exports CUDA Runtime API
│       └── cuda.dll               ← Compilée
│
├── scripts/
│   └── build.sh                   ← Build + install
└── README.md
```

## Comment ça marche

```
nvcuda.dll (PE Windows) ──FIFO pipes──► cuda_daemon (Linux natif)
                                              │
                                              └──► dlopen("libcuda.so")
                                                       │
                                                       └──► NVIDIA GPU
```

## Utilisation

```bash
# 1. Lancer le daemon
/usr/local/bin/cuda_daemon --foreground &

# 2. Lancer TD (les DLLs sont dans /opt/touchdesigner/td/bin/)
~/.local/bin/launch-touchdesigner.sh
```

## État

| Composant | Statut |
|-----------|--------|
| CUDA Driver API (cuInit, cuMemAlloc...) | ✅ Marche via daemon |
| CUDA Runtime API (cudaMalloc, cudaFree...) | ✅ Intégré dans la même DLL |
| NGX (nvngx.dll) | ✅ Installé |
| NVIDIA TOPs dans TD | ❌ Bloqué par TensorRT |
| Module Wine natif (PE/Unix split) | 🔧 En cours |
