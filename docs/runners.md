# Wine Runners Comparison

A technical reference for the Wine runners tested with TouchDesigner under Linux.

## Recommended setup

| Component | Choice | Reason |
|-----------|--------|--------|
| **Runner** | **Tact** (Wine 11 + GE-Proton DLLs) | Custom Wine 11 with KWin patch + complete D2D from GE-Proton |
| **DXVK** | 2.4+ | Vulkan translation for D3D10/11 |
| **Winetricks** | corefonts, vcrun2022 | Missing fonts and MSVC runtimes |
| **IDS patch** | Required | Zero AddressOfEntryPoint in 4 IDS DLLs |
| **Font fix** | `wine_ui_fixes.tox` | Corrects font rendering (auto-injected by launcher) |
| **DPI** | LogPixels auto-detect | Readability on HiDPI displays |
| **KMP_AFFINITY** | `disabled` | Fixes torch import (Intel OpenMP + Wine) |
| **MIMALLOC_DISABLE_REDIRECT** | `=1` | Prevents mimalloc/DWrite hang on Wine 10+ |
| **PYTHONPATH** | Set automatically | Makes pip packages visible to TD |

## Runner comparison

| Runner | Wine version | D2D impl. | TD launches ? | Fonts | Maintenu ? |
|--------|-------------|-----------|---------------|-------|-----------|
| **Soda 9.0-1** | Wine 9.0 TkG | Basique (449 KB d2d1) | ✅ | ❌ Absentes | ❌ Abandonné |
| **GE-Proton10** | Wine 10 Proton | Complète (~1.3 MB d2d1) | ✅ | ⚠️ Déformées | ✅ Actif |
| **GE-Proton11** | Wine 11 Proton | Complète (~1.3 MB d2d1) | ✅ | ⚠️ Déformées | ✅ Actif |
| **Tact (Wine 11 + DLLs GE)** | Wine 11 TkG | Complète (DLLs de GE) | ✅ | ⚠️ Déformées | ✅ Toi |
| **Vanilla Wine 11** | Wine 11 Staging | Basique (552 KB d2d1) | ❌ Splash | — | ✅ |

## D2D : la vraie raison pour laquelle Wine 11 bloque

**Découverte importante (juillet 2026) :** Le problème de Wine 11 avec TouchDesigner n'est pas (seulement) le workaround Mutter — c'est l'implémentation **Direct2D** incomplète.

### Analyse comparative de d2d1.dll

| Runner | Taille d2d1.dll | Fonctions d2d_* |
|--------|----------------|-----------------|
| Soda 9.0-1 | 449 KB | ~700 |
| Tact (wine-tkg) | 552 KB | ~837 |
| **GE-Proton11** | **1.3 MB** | **~4715** |
| Windows 10 natif | ~1.5 MB | — |

GE-Proton a une `d2d1.dll` **2.4× plus grosse** et **5.6× plus de fonctions** que wine-tkg. C'est cette différence qui permet à TD de passer le splash screen et d'afficher la fenêtre principale.

### D'où vient cette différence ?

GE-Proton est buildé à partir du **source Valve/Proton** avec des patches D2D supplémentaires qui ne sont pas dans :
- WineHQ upstream
- wine-tkg (même avec `valve-exp-bleeding` + Staging)
- Soda 9.0-1

Les patches exacts n'ont pas encore été isolés, mais le résultat est clair : les DLLs PE de GE-Proton (`d2d1.dll`, `dwrite.dll`, etc.) ont des implémentations bien plus complètes que celles de wine-tkg.

### Solution pratique

Le **binaire Unix (.so)** de wine-tkg est bon. Il suffit de remplacer les **DLLs PE (.dll)** par celles de GE-Proton. C'est l'approche du runner **Tact**.

## Le patch KWin/Mutter (Wine 11)

### Contexte

Wine 11.0 a ajouté un workaround pour Mutter (GNOME) dans `dlls/winex11.drv/window.c` :

```c
/* When transitioning a window from IconicState to NormalState and the window is managed,
 * go through WithdrawnState. This is needed because Mutter doesn't unmap windows when
 * making windows iconic/minimized as Mutter needs to support live preview. */
if (data->managed && MAKELONG(old_state, new_state) == MAKELONG(IconicState, NormalState))
{
    WARN("window %p/%lx is iconic, remapping to workaround Mutter issues.\n");
    window_set_wm_state(data, WithdrawnState, FALSE);
    window_set_wm_state(data, NormalState, activate);
    return;
}
```

### Problème

Ce workaround est appliqué pour **tous les window managers**, pas seulement Mutter. Sur **KDE/KWin**, la transition `Iconic → Withdrawn → Normal` peut laisser la fenêtre bloquée en `WithdrawnState` — invisible à l'écran.

### Patch

```c
static BOOL is_mutter_desktop(void)
{
    const char *desktop = getenv("XDG_CURRENT_DESKTOP");
    if (!desktop) return FALSE;
    if (strstr(desktop, "GNOME") || strstr(desktop, "gnome"))
        return TRUE;
    return FALSE;
}
```

Le workaround n'est appliqué que sur GNOME/Mutter. Sur KDE et autres WM, la transition directe `Iconic → Normal` est utilisée.

### Note importante

Ce patch a été écrit mais **n'a pas pu être testé isolément** car le problème D2D (voir section ci-dessus) bloquait TD avant même que la création de fenêtre n'ait lieu. Il est probablement correct, mais son effet réel n'a pas été confirmé. Il reste dans la base de code pour référence et pour les utilisateurs qui voudraient utiliser Wine 11 vanilla avec des DLLs natives Windows.

## Soda 9.0-1

### Statut
Runner par défaut de `tact` v1.x. Stable mais abandonné par Bottles.

### Avantages
- Fonctionne avec TD (sauf fonts timeline)
- Bien testé
- Pas de dépendance Steam

### Limitations
- **Wine 9.0** — trop vieux, plus de mises à jour de sécurité
- **D2D basique** (449 KB d2d1.dll)
- **Fonts absentes** sans `wine_ui_fixes.tox`
- Projet Bottles ne publie plus de mises à jour Soda

## GE-Proton10-34

### Statut
Fonctionne avec fixes. Fenêtre visible, fonts présentes mais déformées.

### Configuration requise
```bash
export WINEPREFIX="/path/to/prefix"
export MIMALLOC_DISABLE_REDIRECT=1  # ← OBLIGATOIRE sur Wine 10+
export WAYLAND_DISPLAY=""
export KMP_AFFINITY="disabled"
```

### vkd3d setup (GE-Proton11 uniquement)
```bash
VKD3D_SRC="/path/to/GE-Proton11-1/files/lib/vkd3d/x86_64-windows"
SYS32="/path/to/prefix/drive_c/windows/system32"
cp "$VKD3D_SRC/libvkd3d-1.dll" "$SYS32/"
cp "$VKD3D_SRC/libvkd3d-shader-1.dll" "$SYS32/"
cp "$VKD3D_SRC/libvkd3d-utils-1.dll" "$SYS32/"
```

## Tact (Wine 11 + DLLs GE-Proton)

### Concept
Runner custom qui combine :
- **Binaires Unix (.so)** de Wine 11 buildé avec wine-tkg (config minimaliste, sans bloat)
- **DLLs PE (.dll)** de GE-Proton (D2D/DWrite complet)
- **Patch KWin** pour compatibilité KDE

### Pourquoi cette approche ?

Le binaire Wine (.so) de wine-tkg est fonctionnel et permet d'appliquer des patches customs (KWin, etc.). Ce qui manque c'est l'implémentation D2D côté PE (.dll). En copiant les DLLs de GE-Proton, on obtient le meilleur des deux mondes.

### Build
```bash
# 1. Builder wine-tkg avec la config Tact
cd runner && bash build.sh all

# 2. Télécharger GE-Proton
curl -L https://github.com/GloriousEggroll/proton-ge-custom/releases/download/GE-Proton11-1/GE-Proton11-1.tar.gz

# 3. Extraire les DLLs
cp GE-Proton11-1/files/lib/wine/x86_64-windows/*.dll <tact-runner>/lib/wine/x86_64-windows/
cp GE-Proton11-1/files/lib/wine/i386-windows/*.dll <tact-runner>/lib/wine/i386-windows/
```

## Common issues across all runners

### IDs Peak SDK DLLs
All TD 2025+ builds ship `ids_peak_ipl.dll`, `ids_peak_afl.dll`, `ids_peak_ifl.dll`, `ids_peak_comfort_c.dll` which crash under Wine. Fix: zero the `AddressOfEntryPoint` in each DLL's PE header.

See `tact_lib/patcher.py` for implementation.

### mimalloc + DWrite hang (Wine 10+)
TD ships `mimalloc.dll` and `mimalloc-redirect.dll`. On Wine 10+, DWrite's font enumeration triggers a crash in mimalloc's redirected allocations, causing TD to hang on the splash screen.

**Fix:** `MIMALLOC_DISABLE_REDIRECT=1`

Not needed on Wine 9.x (Soda, Wine 9 vanilla) because DWrite's allocation patterns are compatible.

### NVENC (Video Stream Out TOP)
Not available under any Wine runner. Requires `nvEncodeAPI64.dll` from the Windows NVIDIA driver, not redistributable and not provided by Wine.

**Workarounds:**
- **Spout2PW** — TD → Spout → PipeWire → OBS (NVENC on Linux side)
- **NDI** — confirmed working
- **FFmpeg** — pipe frames to native Linux FFmpeg with `-hwaccel nvenc`

### Wayland
Wine's native Wayland support can cause window creation issues. Always set `WAYLAND_DISPLAY=""` to force XWayland.

## Summary

| Feature | Soda 9.0 | GE-P10/11 | Tact |
|---------|----------|-----------|------|
| TD launches | ✅ | ✅ | ✅ |
| D2D implementation | ❌ Basique (449 KB) | ✅ Complète (1.3 MB) | ✅ Complète (DLLs GE) |
| Font rendering | ❌ Absentes sans fix | ⚠️ Déformées | ⚠️ Déformées |
| Maintenu ? | ❌ Abandonné | ✅ GloriousEggroll | ✅ Toi |
| Patches customs | ❌ Impossible | ❌ Impossible | ✅ KWin, etc. |
| D3D11/Vulkan | ✅ | ✅ | ✅ |
| NDI | ✅ | ❓ | ❓ |
| NVENC | ❌ | ❌ | ❌ |
| CUDA TOPs | ❌ | ❌ | ❌ |
| Setup complexity | Low | Medium | Low (automatisé) |

## Recherches en cours

Les domaines suivants sont en investigation active :

### 1. Patches D2D exacts de GE-Proton
Identifier précisément quels patches dans GE-Proton permettent d'obtenir une `d2d1.dll` complète (1.3 MB vs 552 KB). Objectif : intégrer ces patches dans le build wine-tkg pour ne plus dépendre des DLLs de GE.

### 2. Engine COMP (IPC bridge)
Le sous-processus Engine COMP ne parvient pas à initialiser le pont IPC. Cause probable : création de pipe/named pipe sous Wine.

### 3. CUDA TOPs
Bridge CUDA Driver API (`nvcuda.dll`) vers `libcuda.so` Linux. Projet de long terme, complexité très élevée. Voir `archive/nvcuda_proxy/` pour les expériences en cours.
