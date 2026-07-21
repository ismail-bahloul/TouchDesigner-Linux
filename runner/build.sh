#!/bin/bash
# Build script for Tact Wine runner (wine-tkg)
#
# Usage:
#   ./build.sh all         # Clone + configure + build (local)
#   ./build.sh setup       # Clone wine-tkg et applique la config
#   ./build.sh build       # Lance le build
#   ./build.sh package     # Package le runner en .tar.xz
#
# CI usage:
#   ./build.sh ci          # Build complet pour CI (sortie standardisée)

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WINE_TKG_DIR="/tmp/wine-tkg-git"
OUTPUT_DIR="${OUTPUT_DIR:-/tmp/tact-runner-output}"
RUNNER_VERSION="${RUNNER_VERSION:-$(date +%Y%m%d)-dev}"

case "${1:-help}" in
    all)
        "$0" setup
        "$0" build
        "$0" package
        ;;
    
    setup)
        echo "=== Clonage wine-tkg ==="
        if [ ! -d "$WINE_TKG_DIR" ]; then
            git clone --depth 1 https://github.com/Frogging-Family/wine-tkg-git.git "$WINE_TKG_DIR"
        fi
        
        echo "=== Configuration Tact ==="
        cp "$PROJECT_DIR/runner/config/customization.cfg" "$WINE_TKG_DIR/wine-tkg-git/"
        
        echo "=== Copie des patches personnalisés ==="
        if [ -d "$PROJECT_DIR/runner/patches" ] && [ "$(ls -A "$PROJECT_DIR/runner/patches" 2>/dev/null)" ]; then
            cp -r "$PROJECT_DIR/runner/patches/"* "$WINE_TKG_DIR/wine-tkg-git/patches/" 2>/dev/null || true
            echo "  → $(ls "$PROJECT_DIR/runner/patches" | wc -l) patch(es) copié(s)"
        else
            echo "  → Aucun patch custom (dossier vide)"
        fi
        
        echo "=== Copie des DLLs personnalisées ==="
        if [ -d "$PROJECT_DIR/runner/dlls" ] && [ "$(ls -A "$PROJECT_DIR/runner/dlls" 2>/dev/null)" ]; then
            for dll_dir in "$PROJECT_DIR/runner/dlls/"*/; do
                dll_name="$(basename "$dll_dir")"
                target="$WINE_TKG_DIR/wine-tkg-git/wine-src/dlls/$dll_name"
                if [ -d "$dll_dir" ]; then
                    mkdir -p "$target"
                    cp -r "$dll_dir"/* "$target/" 2>/dev/null || true
                    echo "  → DLL $dll_name copiée"
                fi
            done
        else
            echo "  → Aucune DLL custom (dossier vide)"
        fi
        
        echo "✅ Setup terminé. Lance: ./build.sh build"
        ;;
    
    build)
        echo "=== Build wine-tkg (Wine ${_wine_version:-11.0}) ==="
        cd "$WINE_TKG_DIR/wine-tkg-git"
        
        if [ -f "./wine-tkg" ]; then
            # Mode non-makepkg (portable, pas besoin d'Arch Linux)
            ./wine-tkg --patch --build
        else
            # Mode makepkg (Arch Linux)
            makepkg -s --noconfirm
        fi
        
        echo "✅ Build terminé"
        ;;
    
    package)
        echo "=== Packaging Tact runner ==="
        mkdir -p "$OUTPUT_DIR"
        
        # Chercher le binaire wine buildé
        WINE_BUILD=""
        if [ -d "$WINE_TKG_DIR/wine-tkg-git/wine-build" ]; then
            WINE_BUILD="$WINE_TKG_DIR/wine-tkg-git/wine-build"
        elif [ -d "/opt/wine-tkg" ]; then
            WINE_BUILD=$(ls -d /opt/wine-tkg-* 2>/dev/null | head -n1)
        fi
        
        if [ -z "$WINE_BUILD" ] || [ ! -d "$WINE_BUILD/bin" ]; then
            echo "❌ Build Wine introuvable. Lance d'abord: ./build.sh build"
            exit 1
        fi
        
        PACKAGE_NAME="tact-runner-${RUNNER_VERSION}-x86_64.tar.xz"
        echo "  → Création de $PACKAGE_NAME..."
        
        # Copier dans un dossier propre pour éviter les fichiers superflus
        TMP_PKG="$(mktemp -d)"
        cp -r "$WINE_BUILD"/* "$TMP_PKG/"
        
        # Créer le tarball
        cd "$TMP_PKG"
        tar -cJf "$OUTPUT_DIR/$PACKAGE_NAME" .
        cd /
        rm -rf "$TMP_PKG"
        
        # SHA256
        sha256sum "$OUTPUT_DIR/$PACKAGE_NAME" > "$OUTPUT_DIR/$PACKAGE_NAME.sha256"
        
        echo "✅ Package créé : $OUTPUT_DIR/$PACKAGE_NAME"
        echo "   SHA256 : $(cat "$OUTPUT_DIR/$PACKAGE_NAME.sha256")"
        ;;
    
    ci)
        # Mode CI : build + package, sortie standardisée
        "$0" setup
        "$0" build
        "$0" package
        echo "TACT_RUNNER_ARTIFACT=$OUTPUT_DIR/tact-runner-${RUNNER_VERSION}-x86_64.tar.xz"
        echo "TACT_RUNNER_VERSION=${RUNNER_VERSION}"
        ;;
    
    *)
        echo "Usage: $0 {setup|build|package|all|ci}"
        echo ""
        echo "  setup    Clone wine-tkg et applique la config Tact"
        echo "  build    Lance le build Wine"
        echo "  package  Package le runner en .tar.xz"
        echo "  all      setup + build + package"
        echo "  ci       Mode CI (setup + build + package, output structuré)"
        exit 1
        ;;
esac
