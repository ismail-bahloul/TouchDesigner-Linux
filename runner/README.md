# Tact — Wine runner optimisé pour TouchDesigner

## Concept

Un fork Wine custom (basé sur wine-tkg) avec tous les patches nécessaires
pour faire tourner TouchDesigner parfaitement sur Linux.

**Objectif :** Remplacer Soda Wine 9.0-1 par un runner maintenu, personnalisable,
basé sur Wine 11.x.

## Statut actuel

| Composant | Statut |
|-----------|--------|
| **Base** | wine-tkg (Wine 11.x staging-free) |
| **Patch KWin/Mutter** | 🔧 À écrire |
| **nvcuda.dll** (CUDA Driver API) | 🔧 À écrire |
| **cuda.dll** (CUDA Runtime API) | 🔧 À écrire |
| **IDS Peak SDK patch** | ✅ Via Python (tact_lib/patcher.py) |
| **wine_ui_fixes.tox** | ✅ Existant |
| **DXVK** | ✅ Intégré par wine-tkg |
| **Winetricks** | ✅ Automatisé |

## Build

### Localement (Arch Linux)
```bash
./build.sh all
```

### CI (GitHub Actions)
Le workflow `.github/workflows/build-runner.yml` construit automatiquement
le runner sur `git tag runner-v*` ou manuellement via `workflow_dispatch`.

L'artefact est publié sur GitHub Releases.

## Configuration wine-tkg

Voir `config/customization.cfg`.

```bash
_LOCAL_PRESET="valve-exp-bleeding"
_use_staging="false"        # PAS de Staging (sinon crash DWrite/mimalloc)
_use_GE_patches="true"      # Patches GloriousEggroll
_proton_fs_hack="true"      # Plein écran
_proton_rawinput="true"     # Input
_use_fsync="true"           # Perfs
_use_plasma_systray_fix="true"  # KDE
```

## Structure

```
runner/
├── config/
│   └── customization.cfg    # Configuration wine-tkg
├── dlls/                    # Sources de DLLs custom (nvcuda, cuda...)
│   ├── nvcuda/              → Module CUDA Driver API (à faire)
│   └── cuda/                → Module CUDA Runtime API (à faire)
├── patches/                 # Patches Wine custom
│   ├── 0001-...             (à faire)
│   └── ...
├── build.sh                 # Script de build CI/local
└── README.md
```

## Plan de développement

1. ✅ **Phase 1** — Configurer wine-tkg avec Wine 11
2. ✅ **Phase 2** — CI/CD pour build automatique
3. 🔄 **Phase 3** — Patch KWin/Mutter (Wine 11 → KDE Wayland)
4. ⏳ **Phase 4** — Migrer les patches Python (IDS, etc.) en C
5. ⏳ **Phase 5** — nvcuda.dll (CUDA bridge)
6. ⏳ **Phase 6** — cuda.dll (CUDA Runtime bridge)
