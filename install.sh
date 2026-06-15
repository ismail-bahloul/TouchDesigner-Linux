#!/bin/bash

set -eo pipefail

# Colors for output
BLACK='\033[0;30m'
WHITE='\033[0;97m'
GRAY='\033[0;90m'
DIM='\033[2m'
BOLD='\033[1m'

PRIMARY='\033[0;97m'
GREEN='\033[0;32m'
SECONDARY='\033[0;90m'
ACCENT='\033[2;37m'
SUCCESS='\033[0;97m'
WARNING='\033[0;33m'
ERROR='\033[0;90m'
NC='\033[0m' # No Color

# Check for Linux
if [ "$(uname)" != "Linux" ]; then
    printf "${SECONDARY}▸${NC} Error: This installer only supports Linux systems\n"
    exit 1
fi

# --- DRY RUN WRAPPERS ---
dry_run_mkdir() { if [ "$DRY_RUN" = true ]; then echo "[DRY RUN] mkdir $*"; else mkdir "$@"; fi; }
dry_run_cp()    { if [ "$DRY_RUN" = true ]; then echo "[DRY RUN] cp $*"; else cp "$@"; fi; }
dry_run_rm()    { if [ "$DRY_RUN" = true ]; then echo "[DRY RUN] rm $*"; else rm "$@"; fi; }
dry_run_mv()    { if [ "$DRY_RUN" = true ]; then echo "[DRY RUN] mv $*"; else mv "$@"; fi; }
dry_run_chmod() { if [ "$DRY_RUN" = true ]; then echo "[DRY RUN] chmod $*"; else chmod "$@"; fi; }
dry_run_ln()    { if [ "$DRY_RUN" = true ]; then echo "[DRY RUN] ln $*"; else ln "$@"; fi; }

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        printf "${SECONDARY}▸${NC} Missing required command: %s\n" "$1"
        exit 1
    fi
}

require_any_command() {
    local cmd
    for cmd in "$@"; do
        if command -v "$cmd" >/dev/null 2>&1; then
            return 0
        fi
    done

    printf "${SECONDARY}▸${NC} Missing required command (need one of): %s\n" "$*"
    exit 1
}

check_prerequisites() {
    require_command grep
    require_command sed
    require_command tar
    require_command tr
    require_command sort
    require_command mktemp
    require_command find
    require_any_command curl wget
}

check_prerequisites

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
TD_BASE_DIR="${TD_BASE_DIR:-$HOME/.local/share/touchdesigner-linux}"
RUNNER_DIR=""
WINE_PREFIX=""
WINETRICKS_BIN=""
LOG_DIR=""
DOWNLOAD_DIR="$HOME/Downloads"
# Detect the actual Desktop directory using XDG user dirs, fallback to $HOME/Desktop
if command -v xdg-user-dir >/dev/null 2>&1; then
    DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
else
    DESKTOP_DIR="$HOME/Desktop"
fi
APPLICATIONS_DIR="$HOME/.local/share/applications"
LAUNCHER_DIR="$HOME/.local/bin"
LAUNCHER_PATH="$LAUNCHER_DIR/launch-touchdesigner.sh"

refresh_runtime_paths() {
    RUNNER_DIR="$TD_BASE_DIR/runner"
    WINE_PREFIX="$TD_BASE_DIR/prefix"
    WINETRICKS_BIN="$TD_BASE_DIR/winetricks"
    LOG_DIR="$TD_BASE_DIR/logs"
    WINETRICKS_TMP="$TD_BASE_DIR/tmp"
}

refresh_runtime_paths

SODA_URL="https://github.com/bottlesdevs/wine/releases/download/soda-9.0-1/soda-9.0-1-x86_64.tar.xz"
DXVK_VERSION="2.4"
DXVK_URL="https://github.com/doitsujin/dxvk/releases/download/v${DXVK_VERSION}/dxvk-${DXVK_VERSION}.tar.gz"
WINETRICKS_URL="https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks"
SCRIPT_VERSION="v1.3"
REPO_ASSETS_BASE_URL="${REPO_ASSETS_BASE_URL:-https://raw.githubusercontent.com/iswad-lab/TouchDesigner-Linux/main/Assets}"
SODA_SHA256="${SODA_SHA256:-}"
DXVK_SHA256="${DXVK_SHA256:-}"
WINETRICKS_SHA256="${WINETRICKS_SHA256:-}"
TD_INSTALLER_SHA256="${TD_INSTALLER_SHA256:-}"

# Get terminal width for horizontal rules
TERMINAL_WIDTH=$(tput cols 2>/dev/null)
TERMINAL_WIDTH=${TERMINAL_WIDTH:-60}

# Read prompts from stdin in normal mode, or from /dev/tty when piped (e.g. curl | bash).
if [ -t 0 ]; then
    INTERACTIVE_INPUT="/dev/stdin"
elif [ -r /dev/tty ]; then
    INTERACTIVE_INPUT="/dev/tty"
else
    INTERACTIVE_INPUT=""
fi

# Configuration variables
FAST_MODE=${FAST_MODE:-false}
NON_INTERACTIVE=${NON_INTERACTIVE:-false}
ALLOW_HEADLESS_INSTALL=${ALLOW_HEADLESS_INSTALL:-false}
INSTALL_CHOICE=${INSTALL_CHOICE:-1}
TD_VERSION=${TD_VERSION:-latest}
TD_INSTALLER_PATH=${TD_INSTALLER_PATH:-}
FORCE_UNINSTALL=${FORCE_UNINSTALL:-false}
DEBUG=${DEBUG:-false}
TRACE=${TRACE:-false}
PATCH_TOE_FILE=${PATCH_TOE_FILE:-}
ENABLE_DXVK=${ENABLE_DXVK:-Y}
CREATE_SHORTCUT=${CREATE_SHORTCUT:-N}
ASSOC_FILES=${ASSOC_FILES:-N}
WINE_DLL_OVERRIDES="mscoree="
USE_NVIDIA_DGPU=${USE_NVIDIA_DGPU:-N}
TD_ICON_PATH="touchdesigner"
DEBUG_LOG_FILE=""
OPTIONAL_FONT_FIX_LOCATIONS=""
SHORTCUT_SUMMARY=""

if [ "$NON_INTERACTIVE" = true ]; then
    [ "$CREATE_SHORTCUT" = "N" ] && CREATE_SHORTCUT="Y"
    [ "$ASSOC_FILES" = "N" ] && ASSOC_FILES="Y"
fi

# Utility functions for Iswad aesthetic

print_hr() {
    local hr=$(printf '%.0s─' $(seq 1 "$TERMINAL_WIDTH"))
    printf "${DIM}%s${NC}\n" "$hr"
}

print_banner() {
    [ -t 1 ] && clear
    print_hr
    printf "${BOLD}${PRIMARY}TouchDesigner Linux installer ${ACCENT}%s${NC}\n" "$SCRIPT_VERSION"
    printf "${SECONDARY}By Iswad${NC}\n"
    print_hr
}

print_container() {
    local title="$1"
    local content="$2"
    printf " ${DIM}╔═══════════════════════════════════╗${NC}\n"
    printf " ${DIM}║${NC} %-33s ${DIM}║${NC}\n" "$title: $content"
    printf " ${DIM}╚═══════════════════════════════════╝${NC}\n"
}

print_list_item() {
    local label="$1"
    local text="$2"
    printf "  ${DIM}[${NC}${PRIMARY}${BOLD}%-7s${NC}${DIM}]${NC}  %s\n" "$label" "$text"
}

print_footer() {
    printf "\n"
    print_hr
    printf "Press ${PRIMARY}[Enter]${NC} to start, ${SECONDARY}[Ctrl+C]${NC} to quit\n"
}

print_success() {
    printf "${PRIMARY}▸${NC} %s\n" "$1"
}

print_error() {
    printf "${SECONDARY}▸${NC} %s\n" "$1"
}

print_info() {
    printf "${DIM}→${NC} %s\n" "$1"
}

print_warning() {
    printf "${DIM}•${NC} %s\n" "$1"
}

print_font_fix_instructions() {
    printf "\n\n${DIM}────────────────────────────────────────────${NC}\n"
    printf "${BOLD}${WARNING}PLEASE READ:${NC}\n"
    printf "\n"
    printf "${BOLD}${PRIMARY}Font/UI Fix (.tox)${NC}\n"
    printf "${DIM}If text is missing, tiny, or broken in TouchDesigner, apply this once per project.${NC}\n"
    printf "\n"
    printf "${PRIMARY}1.${NC} In TouchDesigner, open your project (.toe)\n"
    printf "${PRIMARY}2.${NC} Open Palette > ${BOLD}My Components${NC}\n"
    printf "${PRIMARY}3.${NC} Right-click in My Components and click ${BOLD}Refresh Folder${NC}\n"
    printf "${PRIMARY}4.${NC} Drag and drop ${BOLD}wine_ui_fixes.tox${NC} into your network\n"
    printf "${PRIMARY}5.${NC} Click ${BOLD}Enable${NC} on the .tox component\n"
    printf "${PRIMARY}6.${NC} Save your project to keep the fix\n"
    printf "${DIM}────────────────────────────────────────────${NC}\n"
}


prompt_yes_no() {
    local prompt="$1"
    local default_choice="$2"

    while true; do
        if [ "$default_choice" = "Y" ]; then
            printf "%s [Y/n]: " "$prompt" >&2
        else
            printf "%s [y/N]: " "$prompt" >&2
        fi

        local answer
        if ! IFS= read -r answer <"$INTERACTIVE_INPUT"; then
            answer=""
        fi

        answer=$(printf "%s" "$answer" | tr -d '[:space:]')

        if [ -z "$answer" ]; then
            PROMPT_YES_NO_RESULT="$default_choice"
            return 0
        fi

        case "$answer" in
            y|Y|yes|YES)
                PROMPT_YES_NO_RESULT="Y"
                return 0
                ;;
            n|N|no|NO)
                PROMPT_YES_NO_RESULT="N"
                return 0
                ;;
            *)
                printf "${DIM}•${NC} Please answer y or n\n" >&2
                ;;
        esac
    done
}

ensure_interactive_input() {
    if [ "$NON_INTERACTIVE" = true ]; then
        return
    fi

    if [ -n "$INTERACTIVE_INPUT" ]; then
        return
    fi

    print_error "No interactive terminal detected for prompts"
    print_info "Run this installer in a terminal session so it can ask for input."
    exit 1
}

check_network_access() {
    local url="$1"

    if command -v curl >/dev/null 2>&1; then
        curl -fsSI --connect-timeout 5 --max-time 10 "$url" >/dev/null 2>&1 && return 0
    elif command -v wget >/dev/null 2>&1; then
        wget -q --spider --timeout=10 "$url" >/dev/null 2>&1 && return 0
    fi

    print_warning "Network check failed for $url (continuing anyway)"
    return 1
}

download_file() {
    local url="$1"
    local output_path="$2"
    local label="$3"
    local mode="${4:-progress}"
    local user_agent="${5:-}"
    local connect_timeout="${6:-10}"
    local max_time="${7:-0}"
    local tries="${8:-2}"

    local -a curl_opts=(
        --fail
        --location
        --connect-timeout "$connect_timeout"
        --retry "$tries"
        --retry-delay 1
    )

    if [ "$max_time" -gt 0 ] 2>/dev/null; then
        curl_opts+=(--max-time "$max_time")
    fi

    if [ -n "$user_agent" ]; then
        curl_opts+=(-A "$user_agent")
    fi

    if [ "$mode" = "quiet" ]; then
        curl_opts+=(--silent --show-error)
    else
        curl_opts+=(--progress-bar)
    fi

    if [ "$mode" = "progress" ] && command -v wget >/dev/null 2>&1; then
        local -a wget_opts=(
            "--tries=$tries"
            "--timeout=$connect_timeout"
        )

        if [ -n "$user_agent" ]; then
            wget_opts+=("--user-agent=$user_agent")
        fi

        if [ "$mode" = "quiet" ]; then
            wget_opts+=(-q)
        else
            wget_opts+=(-q --show-progress)
        fi

        wget "${wget_opts[@]}" -O "$output_path" "$url" && return 0
    fi

    if command -v curl >/dev/null 2>&1; then
        curl "${curl_opts[@]}" -o "$output_path" "$url" && return 0
    fi

    if command -v wget >/dev/null 2>&1; then
        local -a wget_opts=(
            "--tries=$tries"
            "--timeout=$connect_timeout"
        )

        if [ -n "$user_agent" ]; then
            wget_opts+=("--user-agent=$user_agent")
        fi

        if [ "$mode" = "quiet" ]; then
            wget_opts+=(-q)
        else
            wget_opts+=(-q --show-progress)
        fi

        wget "${wget_opts[@]}" -O "$output_path" "$url" && return 0
    fi

    print_error "No downloader available for $label (need curl or wget)"
    return 1
}

verify_checksum() {
    local file_path="$1"
    local expected_hash="$2"
    local label="$3"

    if [ -z "$expected_hash" ]; then
        print_warning "No checksum configured for $label (skipping verification)"
        return 0
    fi

    if ! command -v sha256sum >/dev/null 2>&1; then
        print_warning "sha256sum not found, cannot verify $label"
        return 0
    fi

    if printf "%s  %s\n" "$expected_hash" "$file_path" | sha256sum -c - >/dev/null 2>&1; then
        print_success "$label checksum verified"
        return 0
    fi

    print_error "$label checksum verification failed"
    return 1
}

safe_rm_rf() {
    local target="$1"

    if [ -z "$target" ] || [ "$target" = "/" ]; then
        print_error "Refusing to delete unsafe directory: '$target'"
        exit 1
    fi

    dry_run_rm -rf -- "$target"
}

setup_debug_mode() {
    if [ "$DEBUG" != true ] && [ "$TRACE" != true ]; then
        return
    fi

    dry_run_mkdir -p "$LOG_DIR"
    DEBUG_LOG_FILE="$LOG_DIR/install-$(date +%Y%m%d-%H%M%S).log"

    # Mirror all output to a persistent log file for issue reports.
    exec > >(tee -a "$DEBUG_LOG_FILE") 2>&1

    print_warning "Debug logging enabled"
    print_info "Debug log: $DEBUG_LOG_FILE"

    if [ "$TRACE" = true ]; then
        set -x
    fi
}

path_is_noexec() {
    local target_path="$1"
    local mount_opts=""
    local mount_point=""

    if command -v findmnt >/dev/null 2>&1; then
        mount_opts=$(findmnt -no OPTIONS -T "$target_path" 2>/dev/null || true)
    fi

    if [ -z "$mount_opts" ]; then
        mount_point=$(stat -c %m "$target_path" 2>/dev/null || true)
        if [ -n "$mount_point" ] && [ -r /proc/mounts ]; then
            mount_opts=$(awk -v mp="$mount_point" '$2 == mp {print $4; exit}' /proc/mounts 2>/dev/null || true)
        fi
    fi

    case ",${mount_opts}," in
        *,noexec,*)
            return 0
            ;;
    esac

    return 1
}

path_allows_exec() {
    local target_path="$1"
    local probe_file="$target_path/.td_exec_probe.$$"

    if ! dry_run_mkdir -p "$target_path" >/dev/null 2>&1; then
        return 1
    fi

    if ! printf '#!/bin/sh\nexit 0\n' >"$probe_file" 2>/dev/null; then
        dry_run_rm -f "$probe_file" >/dev/null 2>&1 || true
        return 1
    fi

    dry_run_chmod +x "$probe_file" >/dev/null 2>&1 || {
        dry_run_rm -f "$probe_file" >/dev/null 2>&1 || true
        return 1
    }

    if "$probe_file" >/dev/null 2>&1; then
        dry_run_rm -f "$probe_file" >/dev/null 2>&1 || true
        return 0
    fi

    dry_run_rm -f "$probe_file" >/dev/null 2>&1 || true
    return 1
}

ensure_exec_capable_base_dir() {
    mkdir -p "$TD_BASE_DIR" 2>/dev/null || true

    if ! path_is_noexec "$TD_BASE_DIR" && path_allows_exec "$TD_BASE_DIR"; then
        return
    fi

    printf "${SECONDARY}▸${NC} Installation location issue: the chosen path doesn't support running applications.\n"

    local fallback
    for fallback in "$HOME/.cache/touchdesigner-linux" "/var/tmp/$USER/touchdesigner-linux"; do
        mkdir -p "$fallback" 2>/dev/null || true
        if ! path_is_noexec "$fallback" && path_allows_exec "$fallback"; then
            TD_BASE_DIR="$fallback"
            refresh_runtime_paths
            print_info "Switched installation path to a compatible location."
            return
        fi
    done

    print_error "Installation location error: please choose a different drive or folder"
    print_info "Set TD_BASE_DIR to a path on an exec-mounted filesystem, then rerun installer"
    print_info "Example: TD_BASE_DIR=/var/tmp/$USER/touchdesigner-linux bash install.sh"
    exit 1
}

ensure_exec_capable_base_dir
setup_debug_mode

add_optional_font_fix_location() {
    local location="$1"

    [ -n "$location" ] || return
    case "\n$OPTIONAL_FONT_FIX_LOCATIONS\n" in
        *"\n$location\n"*)
            return
            ;;
    esac

    if [ -n "$OPTIONAL_FONT_FIX_LOCATIONS" ]; then
        OPTIONAL_FONT_FIX_LOCATIONS="$OPTIONAL_FONT_FIX_LOCATIONS
$location"
    else
        OPTIONAL_FONT_FIX_LOCATIONS="$location"
    fi
}

add_shortcut_summary_entry() {
    local entry="$1"

    [ -n "$entry" ] || return

    if [ -n "$SHORTCUT_SUMMARY" ]; then
        SHORTCUT_SUMMARY="$SHORTCUT_SUMMARY
$entry"
    else
        SHORTCUT_SUMMARY="$entry"
    fi
}

print_shortcut_summary() {
    [ -n "$SHORTCUT_SUMMARY" ] || return 0

    # Split summary into lines and reorder: main shortcut, Font Fixes, then versions
    main_shortcut=""
    font_fixes=""
    versions=""
    while IFS= read -r entry; do
        case "$entry" in
            *"Desktop + Application menu"*) main_shortcut="$entry" ;;
            *"Font Fixes"*) font_fixes="$entry" ;;
            *"launches this specific installed version"*)
                versions="$versions$entry\n"
                ;;
        esac
    done <<< "$SHORTCUT_SUMMARY"

    printf "\n${BOLD}${PRIMARY}SHORTCUTS CREATED:${NC}\n"
    [ -n "$main_shortcut" ] && printf "  ${DIM}•${NC} %s\n" "$main_shortcut"
    [ -n "$font_fixes" ] && printf "  ${DIM}•${NC} %s\n" "$font_fixes"
    # Print each version shortcut
    while IFS= read -r vline; do
        [ -n "$vline" ] && printf "  ${DIM}•${NC} %s\n" "$vline"
    done <<< "${versions%\n}"
    printf "\n"

    SHORTCUT_SUMMARY=""
}

require_graphical_session() {
    if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
        return
    fi

    if [ "$ALLOW_HEADLESS_INSTALL" = true ]; then
        print_warning "No graphical session detected"
        print_info "Continuing in headless preparation mode (GUI-only steps will be skipped)."
        return 1
    fi

    print_error "No graphical session detected"
    print_info "Run this installer from a terminal inside your desktop session (not plain TTY/SSH)."
    print_info "Expected DISPLAY or WAYLAND_DISPLAY to be set."
    exit 1
}

run_and_tail() {
    local lines="$1"
    shift

    local log_file
    log_file=$(mktemp)

    if "$@" >"$log_file" 2>&1; then
        tail -n "$lines" "$log_file"
        rm -f "$log_file"
        return 0
    fi

    tail -n "$lines" "$log_file"
    rm -f "$log_file"
    return 1
}

run_with_progress() {
    local interval="$1"
    shift

    local log_file
    log_file=$(mktemp)

    local start
    start=$(date +%s)

    (
        last_line=""
        while true; do
            elapsed=$(( $(date +%s) - start ))
            latest=$(grep -E 'Get:|Unpacking|Setting up|Installing|Downloading|Retrieving|Preparing|installing |upgrading |downloading |:: Retrieving' \
                "$log_file" 2>/dev/null | tail -n 1 | sed 's/^[[:space:]]*//' | tr -d '\r' || true)
            if [ -n "$latest" ] && [ "$latest" != "$last_line" ]; then
                print_info "(${elapsed}s) $latest"
                last_line="$latest"
            else
                print_info "Still working... (${elapsed}s)"
            fi
            sleep "$interval"
        done
    ) &
    local progress_pid=$!

    local cmd_status=0
    if "$@" >"$log_file" 2>&1; then
        cmd_status=0
    else
        cmd_status=$?
    fi

    kill "$progress_pid" 2>/dev/null || true
    wait "$progress_pid" 2>/dev/null || true

    if [ "$cmd_status" -ne 0 ]; then
        tail -n 10 "$log_file"
        rm -f "$log_file"
        return "$cmd_status"
    fi

    rm -f "$log_file"
    return 0
}

apt_has_install_candidate() {
    local pkg="$1"
    local candidate

    candidate=$(apt-cache policy "$pkg" 2>/dev/null | awk '/Candidate:/ {print $2; exit}')
    [ -n "$candidate" ] && [ "$candidate" != "(none)" ]
}

zypper_has_package() {
    local pkg="$1"
    local search_output

    rpm -q "$pkg" >/dev/null 2>&1 && return 0
    search_output=$(zypper -x search --match-exact --type package "$pkg" 2>/dev/null || true)
    printf "%s" "$search_output" | grep -q "name=\"$pkg\""
}

append_first_zypper_package() {
    local -n package_list_ref="$1"
    shift

    local pkg
    for pkg in "$@"; do
        if zypper_has_package "$pkg"; then
            package_list_ref+=("$pkg")
            return 0
        fi
    done

    return 1
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTERACTIVE MENU
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

show_main_menu() {
    ensure_interactive_input

    if [ "$NON_INTERACTIVE" = true ]; then
        choice=$(printf "%s" "$INSTALL_CHOICE" | tr -d '[:space:]')
        print_info "Non-interactive mode enabled (INSTALL_CHOICE=$choice)"
        return
    fi

    detect_package_manager
    print_banner

    printf "\n${BOLD}${DIM}Environment check${NC}\n\n"

    # System info container
    OS_NAME=$(source /etc/os-release 2>/dev/null && echo "$PRETTY_NAME" 2>/dev/null || echo "Unknown")
    ARCH_NAME=$(uname -m)
    print_container "System" "$OS_NAME / $ARCH_NAME"

    # Compatibility check
    local compat_ok=true
    if [ "$ARCH_NAME" != "x86_64" ]; then
        compat_ok=false
    fi
    if [ "$PKG_MANAGER" = "unknown" ]; then
        compat_ok=false
    fi

    if [ "$compat_ok" = true ]; then
        printf "  ${PRIMARY}▸ Your Linux is supported${NC}\n\n"
    else
        printf "  ${SECONDARY}▸ Your Linux is not supported${NC}\n"
        if [ "$ARCH_NAME" != "x86_64" ]; then
            printf "  ${DIM}  Architecture %s is not supported (x86_64 required)${NC}\n" "$ARCH_NAME"
        fi
        if [ "$PKG_MANAGER" = "unknown" ]; then
            printf "  ${DIM}  No supported package manager found (apt/dnf/pacman/zypper)${NC}\n"
        fi
        printf "\n"
    fi

    # What you get list
    printf "\n${BOLD}${PRIMARY}WHAT YOU GET:${NC}\n\n"
    print_list_item "Runner" "Soda Wine 9.0-1 (standalone)"
    print_list_item "GPU" "Vulkan acceleration (3D graphics)"
    print_list_item "Font" "Microsoft core fonts (corefonts)"
    print_list_item "App" "Latest TouchDesigner version installation"

    # Installation options
    printf "\n${PRIMARY}INSTALLATION OPTIONS :${NC}\n\n"
    printf "  1  Install\n"
    printf "${ACCENT}      • Run TouchDesigner on Linux.${NC}\n"
    printf "${ACCENT}      • Auto-configure compatibility components.${NC}\n"
    printf "${ACCENT}      • GPU acceleration for better graphics performance.${NC}\n"
    printf "${ACCENT}      • Install multiple TouchDesigner versions independently.${NC}\n"
    printf "\n"
    printf "${ACCENT}      -> Already installed? Re-run safely ! Completed steps will be skipped.${NC}\n"
    printf "\n"
    printf "  2  Update\n"
    printf "${ACCENT}      • Update launcher, Wine components, UI fixes and icons.${NC}\n"
    printf "\n"
    printf "  3  Uninstall\n"
    printf "${ACCENT}      • Removes the Wine prefix, runner, launcher, and all TouchDesigner data.${NC}\n"
    printf "\n"
    printf "  0  Exit\n"
    printf "${ACCENT}      • Quit this script without making changes.${NC}\n\n"

    printf "Select option [1]: "
    if ! IFS= read -r choice <"$INTERACTIVE_INPUT"; then
        choice=""
    fi
    choice=${choice:-1}
    choice=$(printf "%s" "$choice" | tr -d '[:space:]')
}

pick_local_installer_with_dialog() {
    local selected_path=""

    if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
        return 1
    fi

    if command -v zenity >/dev/null 2>&1; then
        selected_path=$(zenity --file-selection \
            --title="Select TouchDesigner installer (.exe)" \
            --filename="$DOWNLOAD_DIR/" \
            --file-filter="Windows executable | *.exe" 2>/dev/null || true)
    elif command -v kdialog >/dev/null 2>&1; then
        selected_path=$(kdialog --getopenfilename "$DOWNLOAD_DIR/" "*.exe|Windows executable" 2>/dev/null || true)
    elif command -v yad >/dev/null 2>&1; then
        selected_path=$(yad --file-selection \
            --title="Select TouchDesigner installer (.exe)" \
            --filename="$DOWNLOAD_DIR/" \
            --file-filter="Windows executable | *.exe" 2>/dev/null || true)
    else
        return 1
    fi

    [ -n "$selected_path" ] || return 1
    printf "%s\n" "$selected_path"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DETECTION & INSTALLATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

detect_package_manager() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
    fi

    local os_id="${ID,,}"
    local os_id_like="${ID_LIKE,,}"

    case "$os_id" in
        arch)
            PKG_MANAGER="pacman"; PKG_DISTRO="Arch Linux";
            ;;
        manjaro)
            PKG_MANAGER="pacman"; PKG_DISTRO="Manjaro";
            ;;
        endeavouros)
            PKG_MANAGER="pacman"; PKG_DISTRO="EndeavourOS";
            ;;
        garuda|garudalinux)
            PKG_MANAGER="pacman"; PKG_DISTRO="Garuda Linux";
            ;;
        artix)
            PKG_MANAGER="pacman"; PKG_DISTRO="Artix Linux";
            ;;
        rebornos)
            PKG_MANAGER="pacman"; PKG_DISTRO="RebornOS";
            ;;
        archcraft)
            PKG_MANAGER="pacman"; PKG_DISTRO="Archcraft";
            ;;
        cachyos)
            PKG_MANAGER="pacman"; PKG_DISTRO="CachyOS";
            ;;
        ubuntu)
            PKG_MANAGER="apt"; PKG_DISTRO="Ubuntu";
            ;;
        linuxmint)
            PKG_MANAGER="apt"; PKG_DISTRO="Linux Mint";
            ;;
        pop|pop_os)
            PKG_MANAGER="apt"; PKG_DISTRO="Pop!_OS";
            ;;
        debian)
            PKG_MANAGER="apt"; PKG_DISTRO="Debian";
            ;;
        fedora)
            PKG_MANAGER="dnf"; PKG_DISTRO="Fedora";
            ;;
        rocky|rocky-linux)
            PKG_MANAGER="dnf"; PKG_DISTRO="Rocky Linux";
            ;;
        almalinux|alma)
            PKG_MANAGER="dnf"; PKG_DISTRO="AlmaLinux";
            ;;
        centos)
            PKG_MANAGER="dnf"; PKG_DISTRO="CentOS";
            ;;
        opensuse*|suse*)
            PKG_MANAGER="zypper"; PKG_DISTRO="openSUSE/SUSE";
            ;;
        zorin)
            PKG_MANAGER="apt"; PKG_DISTRO="Zorin OS";
            ;;
        elementary)
            PKG_MANAGER="apt"; PKG_DISTRO="elementary OS";
            ;;
        neon)
            PKG_MANAGER="apt"; PKG_DISTRO="KDE Neon";
            ;;
        kali)
            PKG_MANAGER="apt"; PKG_DISTRO="Kali Linux";
            ;;
        parrot)
            PKG_MANAGER="apt"; PKG_DISTRO="Parrot OS";
            ;;
        mx)
            PKG_MANAGER="apt"; PKG_DISTRO="MX Linux";
            ;;
        lmde)
            PKG_MANAGER="apt"; PKG_DISTRO="Linux Mint Debian Edition";
            ;;
        *)
            case "$os_id_like" in
                *arch*)
                    PKG_MANAGER="pacman"; PKG_DISTRO="Arch-based Linux";
                    ;;
                *ubuntu*|*debian*)
                    PKG_MANAGER="apt"; PKG_DISTRO="Ubuntu/Debian-based Linux";
                    ;;
                *fedora*|*rhel*)
                    PKG_MANAGER="dnf"; PKG_DISTRO="Fedora/RHEL-based Linux";
                    ;;
                *suse*)
                    PKG_MANAGER="zypper"; PKG_DISTRO="SUSE-based Linux";
                    ;;
                *)
                    if command -v pacman >/dev/null 2>&1; then
                        PKG_MANAGER="pacman"; PKG_DISTRO="Pacman-based Linux";
                    elif command -v dnf >/dev/null 2>&1; then
                        PKG_MANAGER="dnf"; PKG_DISTRO="DNF-based Linux";
                    elif command -v apt-get >/dev/null 2>&1; then
                        PKG_MANAGER="apt"; PKG_DISTRO="APT-based Linux";
                    elif command -v zypper >/dev/null 2>&1; then
                        PKG_MANAGER="zypper"; PKG_DISTRO="openSUSE/SUSE";
                    else
                        PKG_MANAGER="unknown"; PKG_DISTRO="Unknown Linux";
                    fi
                    ;;
            esac
            ;;
    esac
}

install_packages() {
    case "$PKG_MANAGER" in
        pacman)
            print_info "Enabling multilib repository if needed..."
            if grep -q "^#\[multilib\]" /etc/pacman.conf; then
                sudo sed -i '/^#\[multilib\]/,+1 {
                    s/^#\[multilib\]/[multilib]/
                    s/^#Include/Include/
                }' /etc/pacman.conf 2>/dev/null || true
            fi

            print_info "Installing required packages..."
            if ! run_with_progress 6 sudo pacman -S --needed --noconfirm \
                curl wget tar xz cabextract unzip p7zip innoextract \
                mesa-utils \
                vulkan-tools vulkan-icd-loader lib32-vulkan-icd-loader \
                lib32-glib2 lib32-gcc-libs lib32-libx11 libx11 \
                lib32-libxext lib32-libxrender lib32-libxrandr \
                lib32-libxi lib32-libxcursor lib32-libxfixes \
                lib32-libxinerama lib32-libxxf86vm lib32-libxcomposite \
                lib32-libunwind lib32-gnutls \
                lib32-freetype2 lib32-fontconfig lib32-alsa-lib \
                xorg-xwayland; then
                print_error "Failed to install packages. Try: sudo pacman -Syu"
                exit 1
            fi
            ;;
        apt)
            print_info "Enabling 32-bit architecture..."
            sudo dpkg --add-architecture i386 >/dev/null 2>&1 || true

            print_info "Refreshing apt package index..."
            if ! run_and_tail 5 sudo apt-get update; then
                print_error "Failed to refresh apt package index"
                print_info "Try: sudo apt-get update"
                exit 1
            fi

            local asound_pkg=""
            local asound_pkg_i386=""
            if apt_has_install_candidate "libasound2"; then
                asound_pkg="libasound2"
            elif apt_has_install_candidate "libasound2t64"; then
                asound_pkg="libasound2t64"
            fi

            if [ -n "$asound_pkg" ] && apt_has_install_candidate "${asound_pkg}:i386"; then
                asound_pkg_i386="${asound_pkg}:i386"
            fi

            if [ -z "$asound_pkg" ]; then
                print_warning "Could not resolve libasound package name (continuing without explicit audio runtime package)"
            fi

            local -a apt_packages=(
                curl wget tar xz-utils cabextract unzip p7zip-full innoextract
                libvulkan1 libvulkan1:i386 vulkan-tools
                libglib2.0-0 libglib2.0-0:i386
                libx11-6 libx11-6:i386
                libxext6 libxext6:i386
                libxrender1 libxrender1:i386
                libxrandr2 libxrandr2:i386
                libxi6 libxi6:i386
                libxcursor1 libxcursor1:i386
                libxfixes3 libxfixes3:i386
                libxinerama1 libxinerama1:i386
                libxxf86vm1 libxxf86vm1:i386
                libgl1 libgl1:i386
                libegl1 libegl1:i386
                libc6 libc6:i386
                libunwind8 libunwind8:i386
                libfreetype6 libfreetype6:i386
                libfontconfig1 libfontconfig1:i386
                libgcc-s1 libgcc-s1:i386
                libstdc++6 libstdc++6:i386
                mesa-utils xwayland
            )

            if [ -n "$asound_pkg" ]; then
                apt_packages+=("$asound_pkg")
            fi
            if [ -n "$asound_pkg_i386" ]; then
                apt_packages+=("$asound_pkg_i386")
            fi

            if ! run_with_progress 6 sudo apt-get install -y "${apt_packages[@]}"; then
                print_error "Failed to install required packages"
                print_info "Try: sudo apt-get update && sudo apt-get upgrade"
                exit 1
            fi
            ;;
        dnf)
            print_info "Enabling RPM Fusion free repository if needed..."
            local fedora_ver
            fedora_ver=$(rpm -E %fedora 2>/dev/null)
            if [[ "$fedora_ver" =~ ^[0-9]+$ ]]; then
                sudo dnf install -y \
                    "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-${fedora_ver}.noarch.rpm" \
                    >/dev/null 2>&1 || true
            fi

            print_info "Installing required packages..."
            if ! run_with_progress 6 sudo dnf install -y \
                curl wget tar xz cabextract unzip p7zip innoextract \
                vulkan-loader vulkan-loader.i686 mesa-vulkan-drivers vulkan-tools \
                mesa-demos xorg-x11-server-Xwayland \
                libunwind libunwind.i686 \
                glibc glibc.i686 libgcc libgcc.i686 libstdc++ libstdc++.i686 \
                gnutls gnutls.i686 \
                freetype freetype.i686 fontconfig fontconfig.i686 \
                alsa-lib alsa-lib.i686 \
                libX11 libX11.i686 libXext libXext.i686 \
                libXcomposite libXcomposite.i686 \
                libXrender libXrender.i686 libXrandr libXrandr.i686 \
                libXi libXi.i686 libXcursor libXcursor.i686 \
                libXfixes libXfixes.i686 libXinerama libXinerama.i686 \
                libXxf86vm libXxf86vm.i686 \
                mesa-libGL mesa-libGL.i686 mesa-libGLU mesa-libGLU.i686 mesa-libEGL mesa-libEGL.i686 \
                glib2 glib2.i686 \
                mesa-vulkan-drivers.i686
        then
                print_error "Failed to install required packages"
                print_info "Try: sudo dnf upgrade --refresh"
                exit 1
            fi
            ;;
        zypper)
            print_info "Installing required packages..."
            local -a zypper_packages=(
                curl wget tar xz cabextract unzip p7zip
                libvulkan1 libvulkan1-32bit vulkan-tools
            )

            append_first_zypper_package zypper_packages Mesa-demo-x mesa-demo-x || true
            append_first_zypper_package zypper_packages libglib-2_0-0 glib2 || true
            append_first_zypper_package zypper_packages libglib-2_0-0-32bit glib2-32bit || true
            append_first_zypper_package zypper_packages libX11-6 || true
            append_first_zypper_package zypper_packages libX11-6-32bit || true
            append_first_zypper_package zypper_packages libXext6 || true
            append_first_zypper_package zypper_packages libXext6-32bit || true
            append_first_zypper_package zypper_packages libXrender1 || true
            append_first_zypper_package zypper_packages libXrender1-32bit || true
            append_first_zypper_package zypper_packages libXrandr2 || true
            append_first_zypper_package zypper_packages libXrandr2-32bit || true
            append_first_zypper_package zypper_packages libXi6 || true
            append_first_zypper_package zypper_packages libXi6-32bit || true
            append_first_zypper_package zypper_packages libXcursor1 || true
            append_first_zypper_package zypper_packages libXcursor1-32bit || true
            append_first_zypper_package zypper_packages libXfixes3 || true
            append_first_zypper_package zypper_packages libXfixes3-32bit || true
            append_first_zypper_package zypper_packages libXinerama1 || true
            append_first_zypper_package zypper_packages libXinerama1-32bit || true
            append_first_zypper_package zypper_packages libXxf86vm1 || true
            append_first_zypper_package zypper_packages libXxf86vm1-32bit || true
            append_first_zypper_package zypper_packages libXcomposite1 || true
            append_first_zypper_package zypper_packages libXcomposite1-32bit || true
            append_first_zypper_package zypper_packages libunwind8 libunwind || true
            append_first_zypper_package zypper_packages libunwind8-32bit libunwind-32bit || true
            append_first_zypper_package zypper_packages libgnutls30 gnutls || true
            append_first_zypper_package zypper_packages libgnutls30-32bit gnutls-32bit || true
            append_first_zypper_package zypper_packages libfreetype6 freetype2 || true
            append_first_zypper_package zypper_packages libfreetype6-32bit freetype2-32bit || true
            append_first_zypper_package zypper_packages libfontconfig1 fontconfig || true
            append_first_zypper_package zypper_packages libfontconfig1-32bit fontconfig-32bit || true
            append_first_zypper_package zypper_packages libasound2 alsa || true
            append_first_zypper_package zypper_packages libasound2-32bit alsa-32bit || true
            append_first_zypper_package zypper_packages libgcc_s1 || true
            append_first_zypper_package zypper_packages libgcc_s1-32bit || true
            append_first_zypper_package zypper_packages libstdc++6 || true
            append_first_zypper_package zypper_packages libstdc++6-32bit || true
            append_first_zypper_package zypper_packages libGL1 Mesa-libGL1 || true
            append_first_zypper_package zypper_packages libGL1-32bit Mesa-libGL1-32bit || true
            append_first_zypper_package zypper_packages libEGL1 Mesa-libEGL1 || true
            append_first_zypper_package zypper_packages libEGL1-32bit Mesa-libEGL1-32bit || true

            append_first_zypper_package zypper_packages innoextract || true

            if ! run_with_progress 6 sudo zypper install -y "${zypper_packages[@]}"; then
                print_error "Failed to install required packages"
                print_info "Try: sudo zypper refresh && sudo zypper update"
                exit 1
            fi
            ;;
        *)
            print_error "Distribution not automatically supported"
            exit 1
            ;;
    esac

    print_success "System packages installed"
}

check_arch_runtime_dependencies() {
    if [ "$PKG_MANAGER" != "pacman" ] || ! command -v pacman >/dev/null 2>&1; then
        return 0
    fi

    local -a required_packages=(
        xorg-xwayland
        vulkan-icd-loader
        lib32-vulkan-icd-loader
        lib32-glib2
        lib32-gcc-libs
        lib32-libx11
        lib32-libxext
        lib32-libxrender
        lib32-libxrandr
        lib32-libxi
        lib32-libxcursor
        lib32-libxfixes
        lib32-libxinerama
        lib32-libxxf86vm
        lib32-libxcomposite
        lib32-libunwind
        lib32-gnutls
        lib32-freetype2
        lib32-fontconfig
        lib32-alsa-lib
    )

    if command -v nvidia-smi >/dev/null 2>&1; then
        required_packages+=(lib32-libglvnd lib32-nvidia-utils)
    fi

    local -a missing_packages=()
    local pkg
    for pkg in "${required_packages[@]}"; do
        if ! pacman -Q "$pkg" >/dev/null 2>&1; then
            missing_packages+=("$pkg")
        fi
    done

    if [ "${#missing_packages[@]}" -eq 0 ]; then
        print_success "Arch runtime dependency check passed"
        return 0
    fi

    print_warning "Arch runtime pre-check found missing packages"
    print_info "Attempting to install missing packages now..."

    if run_with_progress 4 sudo pacman -S --needed --noconfirm "${missing_packages[@]}"; then
        print_success "Arch runtime dependencies repaired"
        return 0
    fi

    print_error "Unable to install required Arch runtime packages"
    print_info "Ensure [multilib] is enabled in /etc/pacman.conf and retry with:"
    print_info "sudo pacman -S --needed ${missing_packages[*]}"
    exit 1
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PATCH .TOE FILE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Check if a .toe file already has the wine_ui_fixes patch
has_fix_already() {
    local f="$1"
    local toeexpand="$2"

    local f_dir
    f_dir=$(dirname "$f")
    local f_base
    f_base=$(basename "$f")

    # Quick check: expand the .toe and look for wine_ui_fixes folder in .dir
    local wine_f="z:${f//\//\\}"
    local toe_dir="$f_dir/${f_base}.dir"
    local toe_toc="$f_dir/${f_base}.toc"

    rm -rf "$toe_dir" "$toe_toc" 2>/dev/null || true
    WINEPREFIX="$WINE_PREFIX" "$RUNNER_DIR/bin/wine64" "$toeexpand" "$wine_f" >/dev/null 2>&1 || true

    local has_fix=false
    if [ -d "$toe_dir/wine_ui_fixes" ]; then
        has_fix=true
    fi

    rm -rf "$toe_dir" "$toe_toc" 2>/dev/null || true
    $has_fix && return 0 || return 1
}

patch_single_toe_file() {
    local f="$1"
    local fixfile="$2"
    local toeexpand="$3"
    local toecollapse="$4"

    local f_base
    f_base=$(basename "$f")
    local f_noext="${f_base%.*}"

    print_info "Patching ${f_base}..."

    # Expand the .tox fix file to get its structure
    local fix_tmpdir
    fix_tmpdir=$(mktemp -d "/tmp/td_fix_${f_noext}.XXXXXX")
    local fix_copy="$fix_tmpdir/fix.tox"
    cp -f "$fixfile" "$fix_copy" 2>/dev/null || true
    local wine_fix_copy="z:${fix_copy//\//\\}"
    WINEPREFIX="$WINE_PREFIX" "$RUNNER_DIR/bin/wine64" "$toeexpand" "$wine_fix_copy" >/dev/null 2>&1 || true

    if [ ! -d "$fix_copy.dir" ]; then
        rm -rf "$fix_tmpdir"
        return 1
    fi

    # Read fix .toc entries
    local -a fix_entries=()
    while IFS= read -r entry; do
        [ -z "$entry" ] && continue
        [[ "$entry" == \#* ]] && continue
        [ "$entry" = ".build" ] && continue
        fix_entries+=("$entry")
    done < "$fix_copy.toc"

    rm -rf "$fix_tmpdir"

    # Step 3: Backup centralisé (nom unique basé sur le chemin complet)
    local backup_dir="$TD_BASE_DIR/backups"
    mkdir -p "$backup_dir" 2>/dev/null || true
    local unique_bak_name="${f//\//_}.bak"
    local backup="$backup_dir/$unique_bak_name"
    cp -f "$f" "$backup" 2>/dev/null || true

    # Step 4: Expand target .toe
    local f_dir
    f_dir=$(dirname "$f")
    local toe_dir="$f_dir/${f_base}.dir"
    local toe_toc="$f_dir/${f_base}.toc"
    local wine_f="z:${f//\//\\}"

    rm -rf "$toe_dir" "$toe_toc" 2>/dev/null || true
    WINEPREFIX="$WINE_PREFIX" "$RUNNER_DIR/bin/wine64" "$toeexpand" "$wine_f" >/dev/null 2>&1 || true

    if [ ! -d "$toe_dir" ]; then
        # Restore depuis le backup centralisé
        cp -f "$backup" "$f" 2>/dev/null || true
        return 1
    fi

    # Step 5: Merge fix into expanded toe
    local merge_tmpdir
    merge_tmpdir=$(mktemp -d "/tmp/td_merge_${f_noext}.XXXXXX")
    local merge_fix="$merge_tmpdir/fix.tox"
    cp -f "$fixfile" "$merge_fix" 2>/dev/null || true
    local wine_mfix="z:${merge_fix//\//\\}"
    WINEPREFIX="$WINE_PREFIX" "$RUNNER_DIR/bin/wine64" "$toeexpand" "$wine_mfix" >/dev/null 2>&1 || true

    if [ -d "$merge_fix.dir" ]; then
        cp -rf "$merge_fix.dir/"* "$toe_dir/" 2>/dev/null || true
    fi
    rm -rf "$merge_tmpdir"

    for entry in "${fix_entries[@]}"; do
        echo "$entry" >> "$toe_toc"
    done

    WINEPREFIX="$WINE_PREFIX" "$RUNNER_DIR/bin/wine64" "$toecollapse" "$wine_f" >/dev/null 2>&1 || true
    rm -rf "$toe_dir" "$toe_toc" 2>/dev/null || true
}

patch_toe_projects_in_drive() {
    [ -d "$WINE_PREFIX/drive_c" ] || return 0

    local toeexpand toecollapse
    toeexpand=$(find "$WINE_PREFIX/drive_c" -type f -iname 'toeexpand.exe' 2>/dev/null | head -n1 || true)
    toecollapse=$(find "$WINE_PREFIX/drive_c" -type f -iname 'toecollapse.exe' 2>/dev/null | head -n1 || true)

    if [ -z "$toeexpand" ] || [ -z "$toecollapse" ]; then
        print_warning "toeexpand/toecollapse not found — skipping .toe patching"
        return 0
    fi

    local fixfile="$TD_BASE_DIR/wine_ui_fixes.tox"
    if [ ! -f "$fixfile" ]; then
        print_warning "wine_ui_fixes.tox not found — skipping .toe patching"
        return 0
    fi

    mapfile -t toe_files < <(find "$WINE_PREFIX/drive_c" -type f -iname '*.toe' 2>/dev/null || true)
    [ "${#toe_files[@]}" -eq 0 ] && return 0

    local total=${#toe_files[@]}
    local patched=0
    local skipped=0

    for f in "${toe_files[@]}"; do
        local f_base
        f_base=$(basename "$f")
        if has_fix_already "$f" "$toeexpand"; then
            print_info "${f_base} — already patched"
            skipped=$((skipped + 1))
        else
            print_info "${f_base} — patching..."
            patch_single_toe_file "$f" "$fixfile" "$toeexpand" "$toecollapse"
            patched=$((patched + 1))
        fi
    done

    print_success "${total} .toe file(s) detected, ${patched} patched, ${skipped} already up to date"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WINE RUNNER SETUP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

download_soda_runner() {
    if [ -f "$RUNNER_DIR/bin/wine64" ]; then
        print_success "Compatibility runtime already installed"
        return
    fi

    print_info "Downloading Soda Wine runtime (~300MB)..."
    local tarball="$TD_BASE_DIR/soda-runner.tar.xz"
    mkdir -p "$TD_BASE_DIR"
    check_network_access "$SODA_URL" || true

    download_file "$SODA_URL" "$tarball" "Soda Wine runtime" "progress" || {
        print_error "Failed to download compatibility runtime"
        rm -f "$tarball"
        exit 1
    }

    verify_checksum "$tarball" "$SODA_SHA256" "Soda Wine runner" || {
        rm -f "$tarball"
        exit 1
    }

    print_info "Extracting compatibility runtime..."
    mkdir -p "$RUNNER_DIR"
    tar -xJf "$tarball" -C "$RUNNER_DIR" --strip-components=1
    rm -f "$tarball"

    if [ ! -f "$RUNNER_DIR/bin/wine64" ]; then
        print_error "Wine runner extraction failed: bin/wine64 not found"
        print_info "Contents of $RUNNER_DIR:"
        ls -la "$RUNNER_DIR" 2>/dev/null || true
        exit 1
    fi

    chmod +x "$RUNNER_DIR/bin/wine" "$RUNNER_DIR/bin/wine64" 2>/dev/null || true
    print_success "Soda Wine runner installed"
}

setup_wine_prefix() {
    if [ -d "$WINE_PREFIX/drive_c" ]; then
        if WINEPREFIX="$WINE_PREFIX" \
            WINEDLLOVERRIDES="$WINE_DLL_OVERRIDES" \
            PATH="$RUNNER_DIR/bin:$PATH" \
            "$RUNNER_DIR/bin/wine64" cmd /c exit >/dev/null 2>&1; then
            print_success "Wine prefix already initialized"
            return
        fi

        print_warning "Existing Wine prefix looks broken, recreating it..."
        WINEPREFIX="$WINE_PREFIX" PATH="$RUNNER_DIR/bin:$PATH" \
            "$RUNNER_DIR/bin/wineserver" -k >/dev/null 2>&1 || true
        safe_rm_rf "$WINE_PREFIX"
    fi

    if ! require_graphical_session; then
        print_warning "Skipping Wine prefix initialization (requires graphical session)"
        return
    fi

    print_info "Initializing Wine prefix (win64)..."
    mkdir -p "$WINE_PREFIX"

    local wineboot_log
    wineboot_log=$(mktemp)

    if ! WINEPREFIX="$WINE_PREFIX" \
        WINEARCH=win64 \
        WINEDLLOVERRIDES="$WINE_DLL_OVERRIDES" \
        PATH="$RUNNER_DIR/bin:$PATH" \
            "$RUNNER_DIR/bin/wineboot" --init >"$wineboot_log" 2>&1; then
        tail -n 20 "$wineboot_log" || true

        if grep -qiE 'noexec filesystem|failed to set 60000020 protection' "$wineboot_log"; then
            print_error "Wine prefix path is on a noexec filesystem"
            print_info "Current path: $WINE_PREFIX"
            print_info "Re-run with an exec-capable path, for example:"
            print_info "TD_BASE_DIR=/var/tmp/$USER/touchdesigner-linux bash install.sh"
        fi

        if grep -qiE 'libunwind\.so\.8|could not load ntdll\.so' "$wineboot_log"; then
            print_error "Wine runtime dependency issue detected (missing libunwind/ntdll runtime)"
            print_info "On Fedora, install missing runtime libs and retry:"
            print_info "sudo dnf install -y libunwind libunwind.i686 glibc glibc.i686 libgcc libgcc.i686 libstdc++ libstdc++.i686 gnutls gnutls.i686 vulkan-loader vulkan-loader.i686"
        fi

        if grep -qiE 'could not load kernel32\.dll|status c0000135' "$wineboot_log"; then
            print_error "Wine runtime dependency issue detected (kernel32.dll load failure)"
            if [ "$PKG_MANAGER" = "dnf" ]; then
                print_info "On Fedora, install missing runtime libs and retry:"
                print_info "sudo dnf install -y libunwind libunwind.i686 glibc glibc.i686 libgcc libgcc.i686 libstdc++ libstdc++.i686 gnutls gnutls.i686 vulkan-loader vulkan-loader.i686 xorg-x11-server-Xwayland"
            elif [ "$PKG_MANAGER" = "pacman" ]; then
                print_info "On Arch-based distros, install missing runtime libs and retry:"
                print_info "sudo pacman -S --needed xorg-xwayland vulkan-icd-loader lib32-vulkan-icd-loader lib32-glib2 lib32-gcc-libs lib32-libx11 lib32-libxext lib32-libxrender lib32-libxrandr lib32-libxi lib32-libxcursor lib32-libxfixes lib32-libxinerama lib32-libxxf86vm lib32-libxcomposite lib32-libunwind lib32-gnutls lib32-freetype2 lib32-fontconfig lib32-alsa-lib"
                if command -v nvidia-smi >/dev/null 2>&1; then
                    print_info "NVIDIA users may also need: sudo pacman -S --needed lib32-libglvnd lib32-nvidia-utils"
                fi
            else
                print_info "On Ubuntu/Debian, install missing runtime libs and retry:"
                print_info "sudo dpkg --add-architecture i386 && sudo apt-get update"
                print_info "sudo apt-get install -y libc6:i386 libgcc-s1:i386 libstdc++6:i386 libx11-6:i386 libxrandr2:i386 libgl1:i386 xwayland"
            fi
        fi

        if grep -qiE 'xrandr14_get_adapters|nodrv_CreateWindow|No GPU vendor found|Failed to create hwnd' "$wineboot_log"; then
            print_warning "Display/GPU bridge issue detected while creating the Wine prefix"
            print_info "If you are on Wayland, ensure Xwayland is installed and relogin."
        fi

        rm -f "$wineboot_log"
        print_error "Wine prefix initialization failed"
        exit 1
    fi

    rm -f "$wineboot_log"

    sleep 2
    WINEPREFIX="$WINE_PREFIX" PATH="$RUNNER_DIR/bin:$PATH" \
        "$RUNNER_DIR/bin/wineserver" -k 2>/dev/null || true

    if [ ! -d "$WINE_PREFIX/drive_c" ]; then
        print_error "Wine prefix initialization failed"
        exit 1
    fi

    print_success "Wine prefix initialized"
}

download_winetricks() {
    if [ -f "$WINETRICKS_BIN" ] && [ -x "$WINETRICKS_BIN" ]; then
        print_success "Winetricks already available"
        return
    fi

    print_info "Downloading winetricks..."
    mkdir -p "$TD_BASE_DIR"
    download_file "$WINETRICKS_URL" "$WINETRICKS_BIN" "winetricks" "quiet" || {
        print_error "Failed to download system libraries"
        exit 1
    }

    chmod +x "$WINETRICKS_BIN"
    print_success "Winetricks downloaded"
}

install_dxvk() {
    if [[ "$ENABLE_DXVK" =~ ^[Nn]$ ]]; then
        return
    fi

    local sys32="$WINE_PREFIX/drive_c/windows/system32"
    if [ -f "$sys32/d3d11.dll" ] && file "$sys32/d3d11.dll" 2>/dev/null | grep -qi "PE32"; then
        print_success "DXVK already installed"
        return
    fi

    print_info "Downloading DXVK $DXVK_VERSION..."
    local dxvk_tarball="$TD_BASE_DIR/dxvk.tar.gz"
    check_network_access "$DXVK_URL" || true
    download_file "$DXVK_URL" "$dxvk_tarball" "DXVK archive" "progress" || {
        print_warning "Failed to download GPU acceleration, skipping (optional)"
        rm -f "$dxvk_tarball"
        return
    }

    verify_checksum "$dxvk_tarball" "$DXVK_SHA256" "DXVK archive" || {
        rm -f "$dxvk_tarball"
        return
    }

    local dxvk_dir
    dxvk_dir=$(mktemp -d)
    tar -xzf "$dxvk_tarball" -C "$dxvk_dir" --strip-components=1
    rm -f "$dxvk_tarball"

    print_info "Installing DXVK..."
    PATH="$RUNNER_DIR/bin:$PATH" \
    WINEPREFIX="$WINE_PREFIX" \
    WINE="$RUNNER_DIR/bin/wine64" \
        bash "$dxvk_dir/setup_dxvk.sh" install 2>/dev/null || {
        print_warning "DXVK setup script failed, installing DLLs manually..."
        local syswow64="$WINE_PREFIX/drive_c/windows/syswow64"
        mkdir -p "$sys32" "$syswow64"
        [ -d "$dxvk_dir/x64" ] && cp "$dxvk_dir"/x64/*.dll "$sys32/" 2>/dev/null || true
        [ -d "$dxvk_dir/x32" ] && cp "$dxvk_dir"/x32/*.dll "$syswow64/" 2>/dev/null || true

        for dll in d3d9 d3d10core d3d11 dxgi; do
            WINEPREFIX="$WINE_PREFIX" PATH="$RUNNER_DIR/bin:$PATH" \
                "$RUNNER_DIR/bin/wine64" reg add \
                "HKEY_CURRENT_USER\\Software\\Wine\\DllOverrides" \
                /v "$dll" /t REG_SZ /d native /f 2>/dev/null || true
        done
    }

    rm -rf "$dxvk_dir"
    print_success "DXVK installed"
}

install_windows_deps() {
    print_info "Installing compatibility libraries..."
    print_info "This can take several minutes depending on your network and disk speed."

    local appdata_check
    appdata_check=$(WINEPREFIX="$WINE_PREFIX" PATH="$RUNNER_DIR/bin:$PATH" \
        "$RUNNER_DIR/bin/wine64" cmd.exe /c echo %AppData% 2>/dev/null | tr -d '\r' | tail -n 1)
    if [ -z "$appdata_check" ] || printf "%s" "$appdata_check" | grep -q '^%AppData%$'; then
        print_warning "Wine runtime check failed (%AppData% unavailable), repairing Wine prefix..."
        setup_wine_prefix
        appdata_check=$(WINEPREFIX="$WINE_PREFIX" PATH="$RUNNER_DIR/bin:$PATH" \
            "$RUNNER_DIR/bin/wine64" cmd.exe /c echo %AppData% 2>/dev/null | tr -d '\r' | tail -n 1)
        if [ -z "$appdata_check" ] || printf "%s" "$appdata_check" | grep -q '^%AppData%$'; then
            print_error "Wine runtime is still unhealthy after prefix repair (%AppData% empty)"
            if [ "$PKG_MANAGER" = "pacman" ]; then
                print_info "Arch fix: sudo pacman -S --needed xorg-xwayland vulkan-icd-loader lib32-vulkan-icd-loader lib32-glib2 lib32-gcc-libs lib32-libx11 lib32-libxext lib32-libxrender lib32-libxrandr lib32-libxi lib32-libxcursor lib32-libxfixes lib32-libxinerama lib32-libxxf86vm lib32-libxcomposite lib32-libunwind lib32-gnutls lib32-freetype2 lib32-fontconfig lib32-alsa-lib"
                if command -v nvidia-smi >/dev/null 2>&1; then
                    print_info "Arch NVIDIA fix: sudo pacman -S --needed lib32-libglvnd lib32-nvidia-utils"
                fi
            fi
            print_info "Try rerunning with: TD_BASE_DIR=/var/tmp/$USER/touchdesigner-linux bash install.sh"
            exit 1
        fi
    fi

    local wt_log
    wt_log=$(mktemp)

    local wt_start
    wt_start=$(date +%s)

    # Keep the installer visibly alive while winetricks runs in foreground.
    (
        last_progress=""
        current_verb=""
        while true; do
            elapsed=$(( $(date +%s) - wt_start ))

            # Track which verb winetricks is currently working on
            verb_line=$(grep -E '^Executing:' "$wt_log" 2>/dev/null | tail -n 1 || true)
            if [ -n "$verb_line" ]; then
                current_verb=$(printf "%s" "$verb_line" | sed 's/^Executing:[[:space:]]*//' | tr -d '\r' || true)
            fi

            progress_line=$(grep -E 'Executing|Downloading|Installing|Using' "$wt_log" 2>/dev/null | tail -n 1 || true)

            if [ -n "$progress_line" ] && [ "$progress_line" != "$last_progress" ]; then
                print_info "Winetricks (${elapsed}s): $progress_line"
                last_progress="$progress_line"
            elif [ -n "$current_verb" ]; then
                print_info "Winetricks (${elapsed}s): working on ${current_verb}..."
            else
                print_info "Winetricks (${elapsed}s): preparing..."
            fi

            sleep 8
        done
    ) &
    local heartbeat_pid=$!

    local wt_status=0
    set +e
    mkdir -p "$WINETRICKS_TMP"
    TMPDIR="$WINETRICKS_TMP" \
    TMP="$WINETRICKS_TMP" \
    TEMP="$WINETRICKS_TMP" \
    PATH="$RUNNER_DIR/bin:$PATH" \
    WINEPREFIX="$WINE_PREFIX" \
    WINEDLLOVERRIDES="$WINE_DLL_OVERRIDES" \
    WINE="$RUNNER_DIR/bin/wine64" \
    WINESERVER="$RUNNER_DIR/bin/wineserver" \
    WINEDEBUG=-all \
        bash "$WINETRICKS_BIN" -q corefonts d3dx11_43 vcrun2019 >"$wt_log" 2>&1
    wt_status=$?
    set -e

    kill "$heartbeat_pid" >/dev/null 2>&1 || true
    wait "$heartbeat_pid" 2>/dev/null || true

    local total_elapsed
    total_elapsed=$(( $(date +%s) - wt_start ))
    print_info "Windows dependencies step completed in ${total_elapsed}s"

    if [ "$wt_status" -ne 0 ]; then
        print_error "Winetricks failed with status ${wt_status}"
        print_info "Last winetricks log lines:"
        cat "$wt_log" 2>/dev/null || print_info "(log file empty)"
        print_info "Retry with DEBUG=true for a full persistent log."
        rm -f "$wt_log"
        exit 1
    fi

    # Check for real failures (exclude known harmless patterns)
    local real_errors
    real_errors=$(grep -E 'returned status [^01]|error:|Error:' "$wt_log" \
        | grep -v -E 'returned status 10[0-9]|wineserver:|fixme:|warn:' || true)

    if [ -n "$real_errors" ]; then
        printf "%s\n" "$real_errors"
        print_warning "Winetricks reported non-fatal warnings"
    fi

    rm -f "$wt_log"
    print_success "Windows dependencies installed"
}


download_touchdesigner() {
    local td_archive="https://derivative.ca/download/archive"
    local -a versions=()
    local -a fallback_versions=(
        "2025.32460"
        "2025.32280"
        "2025.32050"
        "2025.31760"
        "2025.31550"
        "2025.30000"
        "2024.10000"
        "2023.12120"
        "2022.33910"
    )
    local selected=""
    local selected_version=""
    local use_custom_installer=false
    local use_skip=false
    TD_SKIP_INSTALL=false
    local custom_installer_path=""
    local custom_label="Use local installer (.exe path)"
    local skip_label="Skip"
    local max_versions=10
    local td_html
    local archive_user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"
    td_html=$(mktemp)

    print_info "Fetching available TouchDesigner versions..."
    print_info "Fetching archive index (timeout 20s)..."
    download_file "$td_archive" "$td_html" "TouchDesigner archive index" "quiet" "$archive_user_agent" 8 20 1 || true

    if [ -s "$td_html" ]; then
        mapfile -t versions < <(
            grep -oE '20[0-9]{2}\.[0-9]{4,6}' "$td_html" \
                | sort -Vu \
                | sort -Vr
        )
    fi

    rm -f "$td_html"

    if [ "${#versions[@]}" -eq 0 ]; then
        print_warning "Could not fetch live version list from Derivative website"
        versions=("${fallback_versions[@]}")
        print_info "Using curated version list fallback"
    else
        print_success "Found ${#versions[@]} available versions"
    fi

    if [ "${#versions[@]}" -gt "$max_versions" ]; then
        versions=("${versions[@]:0:$max_versions}")
    fi

    if [ "$NON_INTERACTIVE" = true ]; then
        if [ -n "$TD_INSTALLER_PATH" ]; then
            custom_installer_path="$TD_INSTALLER_PATH"
            if [[ "$custom_installer_path" == ~/* ]]; then
                custom_installer_path="$HOME/${custom_installer_path#~/}"
            fi

            if [ ! -f "$custom_installer_path" ]; then
                print_error "TD_INSTALLER_PATH does not exist: $custom_installer_path"
                exit 1
            fi

            if [[ ! "$custom_installer_path" =~ \.[Ee][Xx][Ee]$ ]]; then
                print_warning "TD_INSTALLER_PATH does not end with .exe (continuing anyway)"
            fi

            TD_FILEPATH="$custom_installer_path"
            TD_FILENAME="$(basename "$TD_FILEPATH")"
            print_info "Non-interactive mode: using local installer $TD_FILEPATH"
            return
        fi

        if [ -n "$TD_VERSION" ] && [ "$TD_VERSION" != "latest" ]; then
            local found_version=false
            local v
            for v in "${versions[@]}"; do
                if [ "$v" = "$TD_VERSION" ]; then
                    selected_version="$TD_VERSION"
                    found_version=true
                    break
                fi
            done
            if [ "$found_version" = false ]; then
                print_warning "Requested TD_VERSION '$TD_VERSION' not found, using latest available"
            fi
        fi

        if [ -z "$selected_version" ]; then
            selected_version="${versions[0]}"
        fi

        print_info "Non-interactive mode: selected version $selected_version"
    else
        printf "\n${BOLD}${PRIMARY}AVAILABLE TOUCHDESIGNER VERSIONS:${NC}\n"
        printf "${DIM}Use ↑ ↓ to navigate, Enter to select${NC}\n\n"

        local cursor=0
        local count="${#versions[@]}"
        local total_count=$((count + 2))  # selectable items (versions + custom + skip)

        # Build set of already-installed version numbers
        local -A _installed_versions=()
        while IFS= read -r _iroot; do
            local _iver
            _iver="$(detect_touchdesigner_version "$_iroot" 2>/dev/null || true)"
            [ -n "$_iver" ] && _installed_versions["$_iver"]=1
        done < <(discover_touchdesigner_install_roots 2>/dev/null || true)

        # Detect year boundaries: _sep_before[i]=year means print a separator before versions[i]
        local -A _sep_before=()
        local _sep_count=0
        local _prev_year=""
        local _vi
        for _vi in "${!versions[@]}"; do
            local _vyear="${versions[$_vi]%%.*}"
            if [ "$_vyear" != "$_prev_year" ]; then
                _sep_before[$_vi]="$_vyear"
                _prev_year="$_vyear"
                _sep_count=$((_sep_count + 1))
            fi
        done
        # Total drawn lines = versions + separators + 1 (year sep before custom) + 1 (custom entry) + 1 (skip)
        local draw_lines=$((count + _sep_count + 1 + 1 + 1))

        # Draw the list
        _draw_version_list() {
            local i
            for i in "${!versions[@]}"; do
                # Year separator
                if [[ -n "${_sep_before[$i]+x}" ]]; then
                    printf "  ${DIM}── %s ──────────────────────────${NC}\n" "${_sep_before[$i]}"
                fi
                local label="${versions[$i]}"
                [ "$i" -eq 0 ] && label="${versions[$i]} (Latest stable)"
                local installed_tag=""
                [[ -n "${_installed_versions[${versions[$i]}]+x}" ]] && installed_tag=" ${GREEN}✔ installed${NC}"
                if [ "$i" -eq "$cursor" ]; then
                    printf "  ${BOLD}${PRIMARY}▶  %-30s${NC}%b\n" "$label" "$installed_tag"
                else
                    printf "  ${DIM}   %-30s${NC}%b\n" "$label" "$installed_tag"
                fi
            done

            printf "  ${DIM}──────────────────────────────────${NC}\n"
            if [ "$cursor" -eq "$count" ]; then
                printf "  ${BOLD}${PRIMARY}▶  %-30s${NC}\n" "$custom_label"
            else
                printf "  ${DIM}   %-30s${NC}\n" "$custom_label"
            fi

            local skip_idx=$((count + 1))
            if [ "$cursor" -eq "$skip_idx" ]; then
                printf "  ${BOLD}${PRIMARY}▶  %-30s${NC}\n" "$skip_label"
            else
                printf "  ${DIM}   %-30s${NC}\n" "$skip_label"
            fi
        }

        _draw_version_list

        # Hide cursor while navigating
        tput civis 2>/dev/null || true

        while true; do
            local key
            IFS= read -rsn1 key <"$INTERACTIVE_INPUT" || true
            if [[ "$key" == $'\x1b' ]]; then
                local seq
                IFS= read -rsn2 -t 0.1 seq <"$INTERACTIVE_INPUT" || true
                key="${key}${seq}"
            fi

            case "$key" in
                $'\x1b[A'|$'\x1b[D')  # Up or Left
                    if [ "$cursor" -gt 0 ]; then
                        cursor=$((cursor - 1))
                    else
                        cursor=$((total_count - 1))
                    fi
                    ;;
                $'\x1b[B'|$'\x1b[C')  # Down or Right
                    if [ "$cursor" -lt $((total_count - 1)) ]; then
                        cursor=$((cursor + 1))
                    else
                        cursor=0
                    fi
                    ;;
                '')  # Enter
                    break
                    ;;
            esac

            # Redraw: move up by total drawn lines (versions + separators + custom)
            tput cuu "$draw_lines" 2>/dev/null || printf "\033[${draw_lines}A"
            _draw_version_list
        done

        tput cnorm 2>/dev/null || true
        printf "\n"

        local skip_idx=$((count + 1))
        if [ "$cursor" -eq "$count" ]; then
            use_custom_installer=true
        elif [ "$cursor" -eq "$skip_idx" ]; then
            use_skip=true
        else
            selected_version="${versions[$cursor]}"
        fi
    fi

    if [ "$use_skip" = true ]; then
        TD_SKIP_INSTALL=true
        print_info "Skipping TouchDesigner download/install"
        return
    fi

    if [ "$use_custom_installer" = true ]; then
        custom_installer_path="$(pick_local_installer_with_dialog || true)"
        if [ -n "$custom_installer_path" ]; then
            print_info "Selected from file picker: $custom_installer_path"
        else
            print_info "No file picker selection, falling back to manual path input"
        fi

        while true; do
            if [ -z "$custom_installer_path" ]; then
                printf "Path to TouchDesigner installer (.exe): "
                if ! IFS= read -r custom_installer_path <"$INTERACTIVE_INPUT"; then
                    custom_installer_path=""
                fi
            fi

            custom_installer_path=$(printf "%s" "$custom_installer_path" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')

            if [ -z "$custom_installer_path" ]; then
                print_warning "Please provide a file path"
                continue
            fi

            if [[ "$custom_installer_path" == ~/* ]]; then
                custom_installer_path="$HOME/${custom_installer_path#~/}"
            fi

            if [ ! -f "$custom_installer_path" ]; then
                print_warning "File not found: $custom_installer_path"
                custom_installer_path=""
                continue
            fi

            if [[ ! "$custom_installer_path" =~ \.[Ee][Xx][Ee]$ ]]; then
                prompt_yes_no "File does not end with .exe, continue anyway?" "N"
                if [ "$PROMPT_YES_NO_RESULT" != "Y" ]; then
                    custom_installer_path=""
                    continue
                fi
            fi

            TD_FILEPATH="$custom_installer_path"
            TD_FILENAME="$(basename "$TD_FILEPATH")"
            print_success "Using local installer: $TD_FILEPATH"
            return
        done
    fi

    TD_URL="https://download.derivative.ca/TouchDesigner.$selected_version.exe"
    print_success "Selected version: $selected_version"

    TD_FILENAME=$(basename "$TD_URL")
    mkdir -p "$DOWNLOAD_DIR"

    if [ -f "$DOWNLOAD_DIR/$TD_FILENAME" ]; then
        print_success "File already downloaded"
        TD_FILEPATH="$DOWNLOAD_DIR/$TD_FILENAME"
    else
        print_info "Downloading $TD_FILENAME (≈2GB)..."
        if ! download_file "$TD_URL" "$DOWNLOAD_DIR/$TD_FILENAME" "$TD_FILENAME" "progress"; then
            print_error "Download failed"
            exit 1
        fi
        print_success "Download completed"
        TD_FILEPATH="$DOWNLOAD_DIR/$TD_FILENAME"
    fi

}

install_touchdesigner() {
    local exe_path="$1"
    local td_install_dir="$WINE_PREFIX/drive_c/Program Files/TouchDesigner"

    if [ -f "$td_install_dir/bin/TouchDesigner.exe" ]; then
        print_success "TouchDesigner already installed at: $td_install_dir"
        return
    fi

    if ! command -v 7z >/dev/null 2>&1; then
        print_error "7z (p7zip) is required for installation"
        print_info "Install it with your package manager, then re-run."
        exit 1
    fi

    if ! command -v innoextract >/dev/null 2>&1; then
        print_error "innoextract is required for installation"
        print_info "Install it with your package manager, then re-run."
        exit 1
    fi

    mkdir -p "$WINETRICKS_TMP"
    local extract_root
    extract_root=$(mktemp -d "$WINETRICKS_TMP/td_install.XXXXXX")

    print_info "Extracting TouchDesigner installer (7z)..."
    (
        _7z_start=$(date +%s)
        while true; do
            _7z_elapsed=$(( $(date +%s) - _7z_start ))
            print_info "7z (${_7z_elapsed}s)..."
            sleep 5
        done
    ) &
    local _7z_heartbeat=$!

    local extract_7z="$extract_root/7z_extract"
    mkdir -p "$extract_7z"
    if ! 7z x "$exe_path" -o"$extract_7z" -y >/dev/null 2>&1; then
        kill "$_7z_heartbeat" 2>/dev/null || true
        wait "$_7z_heartbeat" 2>/dev/null || true
        print_error "Failed to extract 7z archive from installer"
        rm -rf "$extract_root"
        exit 1
    fi
    kill "$_7z_heartbeat" 2>/dev/null || true
    wait "$_7z_heartbeat" 2>/dev/null || true

    local inner_exe
    inner_exe=$(find "$extract_7z" -maxdepth 1 -type f -iname '*.exe' 2>/dev/null | head -n 1)
    if [ -z "$inner_exe" ]; then
        print_error "No inner Inno Setup installer found in the archive"
        rm -rf "$extract_root"
        exit 1
    fi

    print_info "Extracting TouchDesigner (innoextract)..."
    (
        _inno_start=$(date +%s)
        while true; do
            _inno_elapsed=$(( $(date +%s) - _inno_start ))
            print_info "Innoextract (${_inno_elapsed}s)..."
            sleep 10
        done
    ) &
    local _inno_heartbeat=$!

    local extract_inno="$extract_root/inno_extract"
    mkdir -p "$extract_inno"
    if ! innoextract -d "$extract_inno" -e "$inner_exe" >/dev/null 2>&1; then
        kill "$_inno_heartbeat" 2>/dev/null || true
        wait "$_inno_heartbeat" 2>/dev/null || true
        print_error "Failed to extract Inno Setup installer"
        rm -rf "$extract_root"
        exit 1
    fi
    kill "$_inno_heartbeat" 2>/dev/null || true
    wait "$_inno_heartbeat" 2>/dev/null || true

    if [ ! -d "$extract_inno/"'$'"/app" ]; then
        print_error "Unexpected installer structure"
        rm -rf "$extract_root"
        exit 1
    fi

    print_info "Copying TouchDesigner files to Wine prefix..."

    mkdir -p "$td_install_dir"
    cp -rf "$extract_inno/"'$'"/app/." "$td_install_dir/"

    if [ -d "$extract_inno/commonappdata" ]; then
        local programdata="$WINE_PREFIX/drive_c/ProgramData"
        mkdir -p "$programdata"
        cp -rf "$extract_inno/commonappdata/." "$programdata/" 2>/dev/null || true
    fi

    rm -rf "$extract_root"

    if [ ! -f "$td_install_dir/bin/TouchDesigner.exe" ]; then
        print_error "TouchDesigner installation failed: TouchDesigner.exe not found"
        exit 1
    fi

    print_success "TouchDesigner installed to: $td_install_dir"
}

check_graphics() {
    print_info "Checking graphics support..."

    if command -v lspci >/dev/null 2>&1; then
        local gpu_lines
        gpu_lines=$(lspci 2>/dev/null | grep -E 'VGA compatible controller|3D controller|Display controller' || true)
        if [ -n "$gpu_lines" ]; then
            print_info "Detected GPUs (PCI):"
            printf "%s\n" "$gpu_lines"
        fi
    fi

    if command -v nvidia-smi >/dev/null 2>&1; then
        local nvidia_gpus
        nvidia_gpus=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || true)
        if [ -n "$nvidia_gpus" ]; then
            print_info "Detected NVIDIA GPU(s):"
            printf "%s\n" "$nvidia_gpus"
        fi
    fi

    if command -v glxinfo >/dev/null 2>&1; then
        local glx_info
        glx_info=$(glxinfo 2>/dev/null | grep -E "OpenGL vendor string|OpenGL renderer string|OpenGL version string")
        if [ -n "$glx_info" ]; then
            printf "%s\n" "$glx_info"
            if command -v nvidia-smi >/dev/null 2>&1 && ! echo "$glx_info" | grep -qi nvidia; then
                print_warning "OpenGL is currently using a non-NVIDIA GPU"
                print_info "Set USE_NVIDIA_DGPU=Y before launch to force NVIDIA offload on hybrid laptops."
            fi
            if echo "$glx_info" | grep -qi llvmpipe; then
                print_warning "LLVMPipe detected: software rendering may reduce TouchDesigner performance."
            fi
        else
            print_warning "glxinfo did not return OpenGL information."
        fi
    else
        if [ "$PKG_MANAGER" = "dnf" ] && command -v rpm >/dev/null 2>&1 \
            && rpm -q mesa-demos >/dev/null 2>&1; then
            if [ -f /run/.containerenv ] || [ -n "${container:-}" ]; then
                print_warning "glxinfo is not visible in this container environment (mesa-demos is installed)."
                print_info "If Vulkan is detected, this is usually safe to ignore."
            else
                print_warning "mesa-demos is installed but glxinfo command is missing from PATH."
            fi
            return
        fi

        case "$PKG_MANAGER" in
            apt)
                print_warning "glxinfo not installed. Install: sudo apt-get install -y mesa-utils"
                ;;
            dnf)
                print_warning "glxinfo not installed. Install: sudo dnf install -y mesa-demos"
                ;;
            pacman)
                print_warning "glxinfo not installed. Install: sudo pacman -S --needed mesa-utils"
                ;;
            zypper)
                print_warning "glxinfo not installed. Install: sudo zypper install -y Mesa-demo-x"
                ;;
            *)
                print_warning "glxinfo not installed. Install mesa-utils or equivalent to verify OpenGL support."
                ;;
        esac
    fi

    if command -v vulkaninfo >/dev/null 2>&1; then
        if vulkaninfo > /dev/null 2>&1; then
            print_success "Vulkan support detected"
        else
            print_warning "Vulkan support is unavailable or not configured."
        fi
    else
        print_warning "vulkaninfo not installed. Install vulkan-tools to verify Vulkan support."
    fi
}

find_touchdesigner_exe() {
    find "$WINE_PREFIX/drive_c" -type f -iname 'TouchDesigner.exe' 2>/dev/null | sort -V | tail -n 1
}


register_toe_mimetype() {
    local mime_dir="$HOME/.local/share/mime/packages"
    mkdir -p "$mime_dir"

    # Remove old/legacy MIME cache to force a clean rebuild
    rm -f "$HOME/.local/share/mime/globs2" \
          "$HOME/.local/share/mime/magic" \
          "$HOME/.local/share/mime/types" \
          "$HOME/.local/share/mime/subclasses" \
          "$HOME/.local/share/mime/XMLnamespaces" \
          "$HOME/.local/share/mime/aliases" \
          "$HOME/.local/share/mime/generic-icons" 2>/dev/null || true

    cat > "$mime_dir/touchdesigner.xml" << XML
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-touchdesigner-toe">
    <comment>TouchDesigner project file</comment>
    <glob pattern="*.toe" priority="100"/>
    <icon name="TouchDesigner-toe"/>
  </mime-type>
  <mime-type type="application/x-touchdesigner-tox">
    <comment>TouchDesigner component file</comment>
    <glob pattern="*.tox" priority="100"/>
    <icon name="TouchDesigner-tox"/>
  </mime-type>
</mime-info>
XML

    # Don't install icons into hicolor/mimetypes — creating index.theme breaks KDE.
    if command -v update-mime-database >/dev/null 2>&1; then
        update-mime-database "$HOME/.local/share/mime" >/dev/null 2>&1 || true
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# POST-INSTALLATION FEATURES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

create_launcher_script() {
    local nvidia_mode="$USE_NVIDIA_DGPU"

    # Préserver le réglage NVIDIA existant si l'utilisateur l'a modifié
    if [ -f "$LAUNCHER_PATH" ]; then
        local existing_nvidia
        existing_nvidia=$(grep -E '^USE_NVIDIA_DGPU=' "$LAUNCHER_PATH" | cut -d'"' -f2 2>/dev/null || echo "")
        [ -n "$existing_nvidia" ] && nvidia_mode="$existing_nvidia"
    fi

    mkdir -p "$LAUNCHER_DIR"

    cat > "$LAUNCHER_PATH" << LAUNCHER
#!/bin/bash
# Allow overriding base dir; default to conventional user install
TD_BASE_DIR="\${TD_BASE_DIR:-\$HOME/.local/share/touchdesigner-linux}"
RUNNER_DIR="\${TD_BASE_DIR%/}/runner"
WINE_PREFIX="\${TD_BASE_DIR%/}/prefix"
USE_NVIDIA_DGPU="${nvidia_mode}"

# Graphics & Display fixes for Wayland (KDE Plasma 6)
# Forces standalone window initialization through XWayland and avoids GLXMakeCurrent timing bugs.
export WAYLAND_DISPLAY=""
export __GL_YIELD="USLEEP"

find_touchdesigner_exe() {
    find "\$WINE_PREFIX/drive_c" -type f -iname 'TouchDesigner.exe' 2>/dev/null | sort -V | tail -n 1
}

# Support version-specific shortcuts via argument (--exe) or env override.
TOUCHDESIGNER_EXE_OVERRIDE_ARG=""
if [[ "\$1" == "--exe" ]] && [ -n "\$2" ]; then
    TOUCHDESIGNER_EXE_OVERRIDE_ARG="\$2"
    shift 2
elif [[ "\$1" == --exe=* ]]; then
    TOUCHDESIGNER_EXE_OVERRIDE_ARG="\${1#--exe=}"
    shift
fi

if [ -n "\$TOUCHDESIGNER_EXE_OVERRIDE_ARG" ] && [ -f "\$TOUCHDESIGNER_EXE_OVERRIDE_ARG" ]; then
    TOUCHDESIGNER_EXE="\$TOUCHDESIGNER_EXE_OVERRIDE_ARG"
elif [ -n "\$TOUCHDESIGNER_EXE_OVERRIDE" ] && [ -f "\$TOUCHDESIGNER_EXE_OVERRIDE" ]; then
    TOUCHDESIGNER_EXE="\$TOUCHDESIGNER_EXE_OVERRIDE"
else
    TOUCHDESIGNER_EXE="\$(find_touchdesigner_exe)"
fi

if [ -z "\$TOUCHDESIGNER_EXE" ]; then
    echo "Error: TouchDesigner.exe not found in Wine prefix."
    exit 1
fi

# On hybrid laptops, optionally offload rendering to NVIDIA dGPU.
if command -v nvidia-smi >/dev/null 2>&1; then
    if [ "\$USE_NVIDIA_DGPU" = "Y" ] || [ "\$USE_NVIDIA_DGPU" = "y" ]; then
        export __NV_PRIME_RENDER_OFFLOAD=1
        export __GLX_VENDOR_LIBRARY_NAME=nvidia
        export __VK_LAYER_NV_optimus=NVIDIA_only
        export DRI_PRIME=1
    fi
fi

# Handle optional .toe file argument
EXTRA_ARGS=()
if [ -n "\$1" ]; then
    INPUT_PATH="\$1"
    # Decode file:// URI if passed by desktop environment
    if [[ "\$INPUT_PATH" == file://* ]]; then
        INPUT_PATH="\${INPUT_PATH#file://}"
        INPUT_PATH="\$(python3 -c "import sys, urllib.parse; print(urllib.parse.unquote(sys.argv[1]))" "\$INPUT_PATH" 2>/dev/null || { echo "Warning: python3 not available; .toe file URI path may contain encoded characters" >&2; echo "\$INPUT_PATH"; })"
    fi
    # Map Linux path to Wine Z: drive
    WINE_PATH="z:\${INPUT_PATH//\//\\\\}"
    EXTRA_ARGS=("\$WINE_PATH")
fi

# Before launching, check if .toe files need the wine_ui_fixes patch
TOE_EXPAND="\$(find "\$WINE_PREFIX/drive_c" -type f -iname 'toeexpand.exe' 2>/dev/null | head -n1 || true)"
TOE_COLLAPSE="\$(find "\$WINE_PREFIX/drive_c" -type f -iname 'toecollapse.exe' 2>/dev/null | head -n1 || true)"
FIX_FILE="\$TD_BASE_DIR/wine_ui_fixes.tox"

# Patch a single .toe file: checks if already patched, and if not, merges wine_ui_fixes
check_and_patch_toe() {
    local TOE_PATH="\$1"
    [ -f "\$TOE_PATH" ] || return 0
    local TOE_BASE TOE_DIR DIR_PATH TOC_PATH WINE_TOE
    TOE_BASE="\$(basename "\$TOE_PATH")"
    TOE_DIR="\$(dirname "\$TOE_PATH")"
    DIR_PATH="\$TOE_DIR/\${TOE_BASE}.dir"
    TOC_PATH="\$TOE_DIR/\${TOE_BASE}.toc"
    WINE_TOE="z:\${TOE_PATH//\//\\\\}"

    # Check if already patched
    rm -rf "\$DIR_PATH" "\$TOC_PATH" 2>/dev/null || true
    WINEPREFIX="\$WINE_PREFIX" "\$RUNNER_DIR/bin/wine64" "\$TOE_EXPAND" "\$WINE_TOE" >/dev/null 2>&1 || true
    local NEEDS_PATCH=false
    if [ ! -d "\$DIR_PATH/wine_ui_fixes" ]; then
        NEEDS_PATCH=true
    fi
    rm -rf "\$DIR_PATH" "\$TOC_PATH" 2>/dev/null || true

    if [ "\$NEEDS_PATCH" = true ]; then
        # Backup centralisé (nom unique basé sur le chemin complet)
        BACKUP_DIR="\$TD_BASE_DIR/backups"
        mkdir -p "\$BACKUP_DIR" 2>/dev/null || true
        # Transforme /home/user/proj/file.toe en _home_user_proj_file.toe.bak (unique même si même nom de fichier)
        local UNIQUE_BAK_NAME="\${TOE_PATH//\//_}.bak"
        cp -f "\$TOE_PATH" "\$BACKUP_DIR/\$UNIQUE_BAK_NAME" 2>/dev/null || true
        # Expand target .toe
        WINEPREFIX="\$WINE_PREFIX" "\$RUNNER_DIR/bin/wine64" "\$TOE_EXPAND" "\$WINE_TOE" >/dev/null 2>&1 || true
        if [ -d "\$DIR_PATH" ]; then
            # Merge fix
            local MERGE_TMP="\$(mktemp -d "/tmp/td_merge_toe.XXXXXX" 2>/dev/null || true)"
            if [ -n "\$MERGE_TMP" ]; then
                local MERGE_FIX="\$MERGE_TMP/fix.tox"
                cp -f "\$FIX_FILE" "\$MERGE_FIX" 2>/dev/null || true
                local WINE_MFIX="z:\${MERGE_FIX//\//\\\\}"
                WINEPREFIX="\$WINE_PREFIX" "\$RUNNER_DIR/bin/wine64" "\$TOE_EXPAND" "\$WINE_MFIX" >/dev/null 2>&1 || true
                if [ -d "\$MERGE_FIX.dir" ]; then
                    cp -rf "\$MERGE_FIX.dir/"* "\$DIR_PATH/" 2>/dev/null || true
                fi
                rm -rf "\$MERGE_TMP" 2>/dev/null || true
            fi
            # Add fix entries to .toc
            for entry in "\${FIX_ENTRIES[@]}"; do
                echo "\$entry" >> "\$TOC_PATH"
            done
            WINEPREFIX="\$WINE_PREFIX" "\$RUNNER_DIR/bin/wine64" "\$TOE_COLLAPSE" "\$WINE_TOE" >/dev/null 2>&1 || true
        fi
        rm -rf "\$DIR_PATH" "\$TOC_PATH" 2>/dev/null || true
    fi
}

if [ -n "\$TOE_EXPAND" ] && [ -n "\$TOE_COLLAPSE" ] && [ -f "\$FIX_FILE" ]; then
    # Read fix .toc entries once (shared across all patches)
    FIX_TMPDIR="\$(mktemp -d "/tmp/td_fix_launcher.XXXXXX" 2>/dev/null || true)"
    if [ -n "\$FIX_TMPDIR" ]; then
        FIX_COPY="\$FIX_TMPDIR/fix.tox"
        cp -f "\$FIX_FILE" "\$FIX_COPY" 2>/dev/null || true
        WINE_FIX_COPY="z:\${FIX_COPY//\//\\\\}"
        WINEPREFIX="\$WINE_PREFIX" "\$RUNNER_DIR/bin/wine64" "\$TOE_EXPAND" "\$WINE_FIX_COPY" >/dev/null 2>&1 || true

        if [ -d "\$FIX_COPY.dir" ]; then
            # Read fix entries
            FIX_ENTRIES=()
            while IFS= read -r entry; do
                [ -z "\$entry" ] && continue
                [[ "\$entry" == \#* ]] && continue
                [ "\$entry" = ".build" ] && continue
                FIX_ENTRIES+=("\$entry")
            done < "\$FIX_COPY.toc"

            # Patch NewProject.toe files in drive_c (TouchDesigner default templates)
            while IFS= read -r -d '' NP_TOE; do
                check_and_patch_toe "\$NP_TOE"
            done < <(find "\$WINE_PREFIX/drive_c" -type f -iname 'NewProject.toe' -print0 2>/dev/null || true)

            # Check the startup mode defined in pref.txt and patch custom template if set
            PREF_FILE="\$WINE_PREFIX/drive_c/users/steamuser/AppData/Local/Derivative/TouchDesigner099/pref.txt"
            if [ -f "\$PREF_FILE" ]; then
                STARTUP_MODE=\$(grep -E '^general\.startupfilemode' "\$PREF_FILE" 2>/dev/null | head -n1 | cut -f2 | tr -d '\r' || true)
                if [ "\$STARTUP_MODE" = "2" ]; then
                    CUSTOM_TOE=\$(grep -E '^general\.startupfilename' "\$PREF_FILE" 2>/dev/null | head -n1 | cut -f2- | tr -d '\r' || true)
                    if [ -n "\$CUSTOM_TOE" ]; then
                        PATCH_CUSTOM_TOE="\${CUSTOM_TOE#z:}"
                        PATCH_CUSTOM_TOE="\${PATCH_CUSTOM_TOE#Z:}"
                        PATCH_CUSTOM_TOE="\${PATCH_CUSTOM_TOE//\\\\/\/}"
                        [ -f "\$PATCH_CUSTOM_TOE" ] && check_and_patch_toe "\$PATCH_CUSTOM_TOE"
                    fi
                fi
            fi

            # Patch the .toe file passed as argument (double-click or CLI), if not already patched
            if [ -n "\$INPUT_PATH" ] && [[ "\$INPUT_PATH" == *.toe ]]; then
                check_and_patch_toe "\$INPUT_PATH"
            fi
        fi
        rm -rf "\$FIX_TMPDIR" 2>/dev/null || true
    fi
fi

# Nettoyage automatique des backups de plus de 30 jours
BACKUP_DIR="\$TD_BASE_DIR/backups"
if [ -d "\$BACKUP_DIR" ]; then
    find "\$BACKUP_DIR" -name '*.bak' -type f -mtime +30 -delete 2>/dev/null || true
fi

# 1. On prépare l'environnement d'exécution
PATH="\$RUNNER_DIR/bin:\$PATH"
export WINEPREFIX="\$WINE_PREFIX"

# 2. On remplace le processus Bash par Wine (Supprime le besoin de l'arrière-plan &)
exec "\$RUNNER_DIR/bin/wine64" "\$TOUCHDESIGNER_EXE" "\${EXTRA_ARGS[@]}"
LAUNCHER
    chmod +x "$LAUNCHER_PATH"
}

install_optional_font_fix() {
    local src
    local dest="$TD_BASE_DIR/wine_ui_fixes.tox"

    mkdir -p "$TD_BASE_DIR"

    for src in "$SCRIPT_DIR/wine_ui_fixes.tox" "$SCRIPT_DIR/Assets/wine_ui_fixes.tox"; do
        if [ -f "$src" ]; then
            cp -f "$src" "$dest"
            return 0
        fi
    done

    if download_file "$REPO_ASSETS_BASE_URL/wine_ui_fixes.tox" "$dest" "wine_ui_fixes.tox" "quiet" "" 10 20 2; then
        return 0
    fi

    rm -f "$dest"
    return 1
}

distribute_optional_font_fix() {
    local src="$TD_BASE_DIR/wine_ui_fixes.tox"
    local wine_steamuser_dir="$WINE_PREFIX/drive_c/users/steamuser"
    local wine_desktop="$wine_steamuser_dir/Desktop"
    local wine_palette_dir="$wine_steamuser_dir/Documents/Derivative/Palette"

    [ -f "$src" ] || return 0
    OPTIONAL_FONT_FIX_LOCATIONS=""
    add_optional_font_fix_location "$src"

    # Wine-visible locations requested by default TouchDesigner-Linux setup.
    if [ -d "$WINE_PREFIX/drive_c" ]; then
        mkdir -p "$wine_desktop"
        local wine_desktop_fix_path="$wine_desktop/wine_ui_fixes.tox"

        if cp -f "$src" "$wine_desktop_fix_path" 2>/dev/null; then
            add_optional_font_fix_location "$wine_desktop_fix_path"
        fi

        mkdir -p "$wine_palette_dir"
        local wine_palette_fix_path="$wine_palette_dir/wine_ui_fixes.tox"

        if cp -f "$src" "$wine_palette_fix_path" 2>/dev/null; then
            add_optional_font_fix_location "$wine_palette_fix_path"
        fi
    fi
}

install_optional_icon() {
    local src

    TD_ICON_PATH="touchdesigner"

    mkdir -p "$TD_BASE_DIR"

    # Install TouchDesigner app icon into TD_BASE_DIR
    # Use absolute path in .desktop files — this is the most reliable method
    # across KDE, GNOME, and other Linux desktop environments.
    local td_svg_src="$SCRIPT_DIR/Assets/Icons/TouchDesigner.svg"
    if [ ! -f "$td_svg_src" ]; then
        download_file "$REPO_ASSETS_BASE_URL/Icons/TouchDesigner.svg" "$TD_BASE_DIR/TouchDesigner.svg" "TouchDesigner.svg" "quiet" "" 10 20 2 || true
    else
        cp -f "$td_svg_src" "$TD_BASE_DIR/TouchDesigner.svg" 2>/dev/null || true
    fi
    if [ -f "$TD_BASE_DIR/TouchDesigner.svg" ]; then
        TD_ICON_PATH="$TD_BASE_DIR/TouchDesigner.svg"
    fi

    # Install .toe and .tox file-type icons into the system icon theme
    # so the MIME type XML <icon name="..."> references are resolved correctly.
    local mime_icon_dir="$HOME/.local/share/icons/hicolor/scalable/mimetypes"
    mkdir -p "$mime_icon_dir"

    for icon_name in TouchDesigner-toe TouchDesigner-tox; do
        local short_name
        case "$icon_name" in
            TouchDesigner-toe) short_name="toe" ;;
            TouchDesigner-tox) short_name="tox" ;;
        esac
        local icon_src="$SCRIPT_DIR/Assets/Icons/${icon_name}.svg"
        local icon_dest="$mime_icon_dir/${icon_name}.svg"
        if [ ! -f "$icon_src" ]; then
            download_file "$REPO_ASSETS_BASE_URL/Icons/${icon_name}.svg" "$icon_dest" "${icon_name}.svg" "quiet" "" 10 20 2 || true
        else
            cp -f "$icon_src" "$icon_dest" 2>/dev/null || true
        fi
        # Also keep a copy in TD_BASE_DIR for reference
        cp -f "$icon_dest" "$TD_BASE_DIR/${short_name}.svg" 2>/dev/null || true
    done

    return 0
}

create_desktop_shortcut() {
    if [[ ! $CREATE_SHORTCUT =~ ^[Yy]$ ]]; then
        return
    fi

    mkdir -p "$DESKTOP_DIR"

    cat > "$DESKTOP_DIR/TouchDesigner.desktop" << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=TouchDesigner
Comment=Real-time visual development platform
Exec=$LAUNCHER_PATH
Icon=$TD_ICON_PATH
Terminal=false
StartupNotify=true
Categories=Graphics;
DESKTOP

    trust_desktop_shortcut "$DESKTOP_DIR/TouchDesigner.desktop"
}

trust_desktop_shortcut() {
    local desktop_file="$1"

    [ -f "$desktop_file" ] || return 0
    chmod +x "$desktop_file" 2>/dev/null || true

    if command -v gio >/dev/null 2>&1; then
        gio set "$desktop_file" metadata::trusted true >/dev/null 2>&1 || true
    fi
}

create_applications_shortcut() {
    if [[ ! $CREATE_SHORTCUT =~ ^[Yy]$ ]]; then
        return
    fi

    mkdir -p "$APPLICATIONS_DIR"

    cat > "$APPLICATIONS_DIR/touchdesigner.desktop" << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=TouchDesigner
Comment=Real-time visual development platform
Exec=$LAUNCHER_PATH
Icon=$TD_ICON_PATH
Terminal=false
StartupNotify=true
Categories=Graphics;
DESKTOP

    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$APPLICATIONS_DIR" >/dev/null 2>&1 || true
    fi
}


create_versioned_shortcuts() {
    [[ $CREATE_SHORTCUT =~ ^[Yy]$ ]] || return 0

    local install_root td_exe version label safe_version
    local any_created=false
    local -a all_roots=()

    while IFS= read -r install_root; do
        all_roots+=("$install_root")
    done < <(discover_touchdesigner_install_roots)

    # Only create version-specific shortcuts when 2+ versions are installed
    [ "${#all_roots[@]}" -lt 2 ] && return 0

    for install_root in "${all_roots[@]}"; do
        td_exe="$install_root/bin/TouchDesigner.exe"
        [ -f "$td_exe" ] || td_exe="$install_root/TouchDesigner.exe"
        [ -f "$td_exe" ] || continue

        version="$(detect_touchdesigner_version "$install_root")"
        if [ -z "$version" ]; then
            version="$(basename "$install_root")"
        fi

        label="TouchDesigner $version"
        safe_version="${version//[^a-zA-Z0-9._-]/-}"

        mkdir -p "$DESKTOP_DIR"
        cat > "$DESKTOP_DIR/TouchDesigner-${safe_version}.desktop" << VDESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=$label
Comment=Version $version
Exec=$LAUNCHER_PATH --exe "$td_exe"
Icon=$TD_ICON_PATH
Terminal=false
StartupNotify=true
Categories=Graphics;
VDESKTOP
        trust_desktop_shortcut "$DESKTOP_DIR/TouchDesigner-${safe_version}.desktop"

        mkdir -p "$APPLICATIONS_DIR"
        cat > "$APPLICATIONS_DIR/touchdesigner-${safe_version}.desktop" << VAPPS
[Desktop Entry]
Version=1.0
Type=Application
Name=$label
Comment=Version $version
Exec=$LAUNCHER_PATH --exe "$td_exe"
Icon=$TD_ICON_PATH
Terminal=false
StartupNotify=true
Categories=Graphics;
VAPPS
        any_created=true
        add_shortcut_summary_entry "$label: launches this specific installed version"
    done < <(discover_touchdesigner_install_roots)

    if [ "$any_created" = true ] && command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$APPLICATIONS_DIR" >/dev/null 2>&1 || true
    fi
}

associate_toe_files() {
    if [[ ! $ASSOC_FILES =~ ^[Yy]$ ]]; then
        return
    fi

    mkdir -p "$APPLICATIONS_DIR"

    cat > "$APPLICATIONS_DIR/touchdesigner-file.desktop" << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=TouchDesigner
Exec=$LAUNCHER_PATH %u
MimeType=application/x-touchdesigner-toe;application/x-touchdesigner-tox;
NoDisplay=true
Icon=TouchDesigner
StartupNotify=true
Categories=Graphics;
DESKTOP

    register_toe_mimetype

    if command -v xdg-mime >/dev/null 2>&1; then
        xdg-mime default touchdesigner-file.desktop application/x-touchdesigner-toe 2>/dev/null || true
        xdg-mime default touchdesigner-file.desktop application/x-touchdesigner-tox 2>/dev/null || true
    fi

    print_success ".toe and .tox files associated"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLEANUP & UNINSTALL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

discover_touchdesigner_install_roots() {
    local drive_c="$WINE_PREFIX/drive_c"

    [ -d "$drive_c" ] || return 0

    find "$drive_c" -type f -iname 'TouchDesigner.exe' 2>/dev/null | while IFS= read -r exe_path; do
        local install_root

        if [[ "$exe_path" == */bin/TouchDesigner.exe ]]; then
            install_root="$(dirname "$(dirname "$exe_path")")"
        else
            install_root="$(dirname "$exe_path")"
        fi

        [ -d "$install_root" ] && printf "%s\n" "$install_root"
    done | sort -u
}

detect_touchdesigner_version() {
    local install_root="$1"
    local td_exe="$install_root/bin/TouchDesigner.exe"
    local version=""

    [ -f "$td_exe" ] || return 0
    command -v strings >/dev/null 2>&1 || return 0

    version=$(strings "$td_exe" 2>/dev/null | sed -nE 's/.*TouchDesigner[[:space:]]+((20[0-9]{2}\.[0-9]+)).*/\1/p' | head -n 1)

    if [ -z "$version" ]; then
        version=$(strings "$td_exe" 2>/dev/null | sed -nE 's/.*((20[0-9]{2}\.[0-9]+)).*/\1/p' | head -n 1)
    fi

    [ -n "$version" ] && printf "%s\n" "$version"
}

uninstall_selected_touchdesigner_versions() {
    local -a selected_roots=("$@")
    local removed_count=0
    local root

    if [ "${#selected_roots[@]}" -eq 0 ]; then
        print_warning "No versions selected"
        return 0
    fi

    for root in "${selected_roots[@]}"; do
        local pretty_root="${root#$WINE_PREFIX/drive_c/}"
        [ "$pretty_root" = "$root" ] && pretty_root="$root"

        if [ -d "$root" ]; then
            # Remove version-specific shortcuts for this install
            local version
            version="$(detect_touchdesigner_version "$root" 2>/dev/null || true)"
            if [ -n "$version" ]; then
                local safe_version="${version//[^a-zA-Z0-9._-]/-}"
                rm -f "$DESKTOP_DIR/TouchDesigner-${safe_version}.desktop" \
                      "$APPLICATIONS_DIR/touchdesigner-${safe_version}.desktop" 2>/dev/null || true
            fi

            print_info "Removing: $pretty_root"
            safe_rm_rf "$root"
            removed_count=$((removed_count + 1))
        else
            print_warning "Already missing: $pretty_root"
        fi
    done

    # After removal, if ≤ 1 version remains, remove all version-specific shortcuts
    local remaining_roots=()
    mapfile -t remaining_roots < <(discover_touchdesigner_install_roots)
    if [ "${#remaining_roots[@]}" -le 1 ]; then
        for _vshortcut in "$DESKTOP_DIR"/TouchDesigner-*.desktop; do
            [ -f "$_vshortcut" ] && rm -f "$_vshortcut"
        done
        for _vapp in "$APPLICATIONS_DIR"/touchdesigner-[0-9]*.desktop; do
            [ -f "$_vapp" ] && rm -f "$_vapp"
        done
        if command -v update-desktop-database >/dev/null 2>&1; then
            update-desktop-database "$APPLICATIONS_DIR" >/dev/null 2>&1 || true
        fi
    fi

    if [ "$removed_count" -gt 0 ]; then
        print_success "Removed $removed_count TouchDesigner version(s)"
    else
        print_info "No versions were removed"
    fi
}

uninstall_touchdesigner_menu() {
    ensure_interactive_input

    if [ "$NON_INTERACTIVE" = true ]; then
        uninstall_touchdesigner
        return
    fi

    local -a install_roots=()
    mapfile -t install_roots < <(discover_touchdesigner_install_roots)

    print_banner
    printf "\n${BOLD}${PRIMARY}UNINSTALL TOUCHDESIGNER:${NC}\n\n"

    if [ "${#install_roots[@]}" -eq 0 ]; then
        print_warning "No installed TouchDesigner versions were detected in the Wine prefix"
        printf "\n  1  Uninstall everything (prefix, runner, launcher, desktop entries)\n"
        printf "  0  Cancel\n\n"
        printf "Select option [0]: "

        local empty_choice
        if ! IFS= read -r empty_choice <"$INTERACTIVE_INPUT"; then
            empty_choice="0"
        fi
        empty_choice=$(printf "%s" "$empty_choice" | tr -d '[:space:]')
        empty_choice=${empty_choice:-0}

        case "$empty_choice" in
            1)
                uninstall_touchdesigner
                ;;
            0)
                print_info "Uninstall cancelled"
                ;;
            *)
                print_error "Invalid option"
                ;;
        esac

        return
    fi

    local count="${#install_roots[@]}"
    local purge_all_option=$((count + 1))
    local i

    printf "Detected versions in Wine prefix:\n\n"
    for i in "${!install_roots[@]}"; do
        local root="${install_roots[$i]}"
        local label
        local pretty_root
        local detected_version

        pretty_root="${root#$WINE_PREFIX/drive_c/}"
        [ "$pretty_root" = "$root" ] && pretty_root="$root"

        detected_version="$(detect_touchdesigner_version "$root")"
        if [ -n "$detected_version" ]; then
            label="TouchDesigner $detected_version"
        else
            label="TouchDesigner ($(basename "$root"))"
        fi

        printf "  %d  %s\n" "$((i + 1))" "$label"
        printf "${ACCENT}      %s${NC}\n" "$pretty_root"
    done

    printf "\n  %d  Uninstall EVERYTHING (prefix, runner, launcher, desktop entries)\n" "$purge_all_option"
    printf "\n"
    printf "  0  Cancel\n\n"
    printf "Select one or multiple versions (e.g. 1,3) [0]: "

    local selection_raw
    if ! IFS= read -r selection_raw <"$INTERACTIVE_INPUT"; then
        selection_raw="0"
    fi
    selection_raw=${selection_raw:-0}

    local selection
    selection=$(printf "%s" "$selection_raw" | tr ',' ' ' | tr -s '[:space:]' ' ' | sed 's/^ //; s/ $//')

    if [ "$selection" = "0" ]; then
        print_info "Uninstall cancelled"
        return
    fi

    if [ "$selection" = "$purge_all_option" ]; then
        uninstall_touchdesigner
        return
    fi

    local token
    local -a selected_roots=()

    for token in $selection; do
        if ! [[ "$token" =~ ^[0-9]+$ ]]; then
            print_error "Invalid selection: $token"
            return
        fi

        if [ "$token" -lt 1 ] || [ "$token" -gt "$count" ]; then
            print_error "Selection out of range: $token"
            return
        fi

        local idx=$((token - 1))
        local candidate_root="${install_roots[$idx]}"
        local already_selected=false
        local existing_root

        for existing_root in "${selected_roots[@]}"; do
            if [ "$existing_root" = "$candidate_root" ]; then
                already_selected=true
                break
            fi
        done

        if [ "$already_selected" = false ]; then
            selected_roots+=("$candidate_root")
        fi
    done

    if [ "${#selected_roots[@]}" -eq 0 ]; then
        print_warning "No versions selected"
        return
    fi

    prompt_yes_no "Remove ${#selected_roots[@]} selected version(s)?" "Y"
    if [ "$PROMPT_YES_NO_RESULT" != "Y" ]; then
        print_info "Uninstall cancelled"
        return
    fi

    uninstall_selected_touchdesigner_versions "${selected_roots[@]}"
}

uninstall_touchdesigner() {
    ensure_interactive_input
    print_warning "This will completely remove TouchDesigner and all related files"

    if [ "$NON_INTERACTIVE" = true ]; then
        if [ "$FORCE_UNINSTALL" != true ]; then
            print_error "Refusing uninstall in non-interactive mode without FORCE_UNINSTALL=true"
            return
        fi
        REPLY="Y"
    else
        prompt_yes_no "Are you sure?" "Y"
        REPLY="$PROMPT_YES_NO_RESULT"
    fi

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Uninstall cancelled"
        return
    fi

    print_info "Removing centralised backups..."
    if [ -d "$TD_BASE_DIR/backups" ]; then
        rm -rf "$TD_BASE_DIR/backups"
        print_success "Centralised backups removed"
    fi

    print_info "Removing Wine prefix and runner..."
    if [ -d "$TD_BASE_DIR" ]; then
        safe_rm_rf "$TD_BASE_DIR"
        print_success "Wine prefix and runner removed"
    else
        print_info "Base directory not found (already removed?)"
    fi

    print_info "Removing launcher script..."
    if [ -f "$LAUNCHER_PATH" ]; then
        rm -f "$LAUNCHER_PATH"
        print_success "Launcher script removed"
    fi
    if [ -f "$HOME/launch-touchdesigner.sh" ]; then
        rm -f "$HOME/launch-touchdesigner.sh"
        print_success "Launcher script removed"
    fi

    print_info "Removing desktop shortcut..."
    if [ -f "$DESKTOP_DIR/TouchDesigner.desktop" ]; then
        rm -f "$DESKTOP_DIR/TouchDesigner.desktop"
        print_success "Desktop shortcut removed"
    fi
    # Remove versioned desktop shortcuts
    for _vshortcut in "$DESKTOP_DIR"/TouchDesigner-*.desktop; do
        [ -f "$_vshortcut" ] && rm -f "$_vshortcut"
    done

    print_info "Removing file association..."
    if [ -f "$APPLICATIONS_DIR/touchdesigner.desktop" ]; then
        rm -f "$APPLICATIONS_DIR/touchdesigner.desktop"
        print_success "Application menu entry removed"
    fi
    if [ -f "$APPLICATIONS_DIR/touchdesigner-file.desktop" ]; then
        rm -f "$APPLICATIONS_DIR/touchdesigner-file.desktop"
        print_success "File association removed"
    fi
    if [ -f "$APPLICATIONS_DIR/touchdesigner-font-fixes.desktop" ]; then
        rm -f "$APPLICATIONS_DIR/touchdesigner-font-fixes.desktop"
    fi
    if [ -f "$APPLICATIONS_DIR/touchdesigner-starter.desktop" ]; then
        rm -f "$APPLICATIONS_DIR/touchdesigner-starter.desktop"
    fi
    # Remove versioned application shortcuts
    for _vapp in "$APPLICATIONS_DIR"/touchdesigner-[0-9]*.desktop; do
        [ -f "$_vapp" ] && rm -f "$_vapp"
    done

    local mime_icon_dir="$HOME/.local/share/icons/hicolor/scalable/mimetypes"
    for _icon in TouchDesigner-toe.svg TouchDesigner-tox.svg; do
        if [ -f "$mime_icon_dir/$_icon" ]; then
            rm -f "$mime_icon_dir/$_icon"
        fi
    done

    local mime_dir="$HOME/.local/share/mime/packages"
    if [ -f "$mime_dir/touchdesigner.xml" ]; then
        rm -f "$mime_dir/touchdesigner.xml"
        if command -v update-mime-database >/dev/null 2>&1; then
            update-mime-database "$HOME/.local/share/mime" >/dev/null 2>&1 || true
        fi
        print_success "MIME type removed"
    fi

    printf "\n${DIM}────────────────────────────────────────────${NC}\n"
    printf "${PRIMARY}Uninstall Complete${NC}\n"
    printf "${PRIMARY}TouchDesigner has been completely removed.${NC}\n"
    printf "${SECONDARY}Iswad${NC}\n"
    printf "${DIM}────────────────────────────────────────────${NC}\n\n"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN EXECUTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

main() {
    show_main_menu

    case $choice in
        1)
            local headless_mode=false
            if [ "$ALLOW_HEADLESS_INSTALL" = true ] && [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
                headless_mode=true
            fi

            print_banner
            print_info "Starting TouchDesigner installation..."
            printf "\n"

            # Check available disk space early — extraction needs at least 10 GB
            mkdir -p "$WINETRICKS_TMP"
            local _avail_kb
            _avail_kb=$(df --output=avail "$WINETRICKS_TMP" 2>/dev/null | tail -n 1)
            if [ -n "$_avail_kb" ] && [ "$_avail_kb" -lt 8388608 ] 2>/dev/null; then
                print_error "Insufficient disk space: less than 8 GB available on $(df --output=target "$WINETRICKS_TMP" 2>/dev/null | tail -n 1)"
                print_info "TouchDesigner installation requires at least 8 GB of free space (final install is ~9 GB)."
                print_info "Free up space or set TD_BASE_DIR to a drive with more room."
                print_info "Example: TD_BASE_DIR=/mnt/bigdrive/touchdesigner-linux ./install.sh"
                exit 1
            fi

            # Clean up temp files from previous runs
            # Step 1: System packages
            print_info "Step 1/6: Installing system packages..."
            detect_package_manager
            [[ "$PKG_MANAGER" == "unknown" ]] && { print_error "Unsupported distribution"; exit 1; }
            print_success "Detected: $PKG_DISTRO ($PKG_MANAGER)"
            if ! command -v sudo >/dev/null 2>&1; then
                print_error "sudo is required to install system packages"
                exit 1
            fi
            install_packages
            check_arch_runtime_dependencies
            check_graphics
            [ "$FAST_MODE" != true ] && sleep 0.3

            # Step 2: Soda Wine runner
            if [ ! -f "$RUNNER_DIR/bin/wine64" ]; then
                print_info "Step 2/6: Setting up compatibility runtime..."
                download_soda_runner
            else
                print_success "Step 2/6: Compatibility runtime ready"
            fi
            [ "$FAST_MODE" != true ] && sleep 0.3

            # Step 3: Wine prefix
            print_info "Step 3/6: Setting up compatibility environment..."
            setup_wine_prefix
            [ "$FAST_MODE" != true ] && sleep 0.3

            # Step 4: Windows dependencies
            if [ -d "$WINE_PREFIX/drive_c" ]; then
                print_info "Step 4/6: Installing compatibility libraries..."
                download_winetricks
                install_windows_deps
                install_dxvk
            else
                print_warning "Step 4/6: Skipped (Wine prefix not initialized)"
            fi
            [ "$FAST_MODE" != true ] && sleep 0.3

            # Step 5: Download TouchDesigner
            print_info "Step 5/6: Downloading TouchDesigner..."
            download_touchdesigner
            [ "$FAST_MODE" != true ] && sleep 0.3

            # Step 6: Install TouchDesigner
            if [ "$TD_SKIP_INSTALL" = true ]; then
                print_info "Step 6/6: Skipped (user chose to skip TouchDesigner install)"
            else
                print_info "Step 6/6: Installing TouchDesigner..."
                install_touchdesigner "$TD_FILEPATH"
            fi

            if [ "$TD_SKIP_INSTALL" = true ] || find_touchdesigner_exe >/dev/null; then
                # Create launcher
                print_info "Creating launcher script..."
                create_launcher_script
                print_success "Launcher created: ~/.local/bin/launch-touchdesigner.sh"

                install_optional_icon || true
                if [ "$TD_ICON_PATH" != "touchdesigner" ]; then
                    print_info "Icon installed: $TD_ICON_PATH"
                fi
                [ "$FAST_MODE" != true ] && sleep 0.3

            print_info "Patching existing .toe files..."
            install_optional_font_fix || true
            patch_toe_projects_in_drive

            CREATE_SHORTCUT=Y
            print_info "Creating desktop & application menu shortcuts..."
                if [[ $CREATE_SHORTCUT =~ ^[Yy]$ ]]; then
                    # Remove all existing TouchDesigner shortcuts to recreate them cleanly
                    for _old in "$DESKTOP_DIR"/TouchDesigner*.desktop; do
                        [ -f "$_old" ] && rm -f "$_old"
                    done
                    for _old in "$APPLICATIONS_DIR"/touchdesigner*.desktop; do
                        [ -f "$_old" ] && rm -f "$_old"
                    done
                    if command -v update-desktop-database >/dev/null 2>&1; then
                        update-desktop-database "$APPLICATIONS_DIR" >/dev/null 2>&1 || true
                    fi
                fi
                create_desktop_shortcut
                create_applications_shortcut
                if [[ $CREATE_SHORTCUT =~ ^[Yy]$ ]]; then
                    add_shortcut_summary_entry "TouchDesigner (Desktop + Application menu): launches latest installed version"
                fi
                create_versioned_shortcuts

                print_shortcut_summary

                ASSOC_FILES=Y
                print_info "Associating .toe & .tox files..."
                associate_toe_files
            elif [ "$TD_SKIP_INSTALL" != true ]; then
                print_warning "TouchDesigner is not installed yet; skipping launcher and desktop integration"
            fi

            if install_optional_font_fix; then
                distribute_optional_font_fix
                print_font_fix_instructions
            fi


            printf "\n${DIM}────────────────────────────────────────────${NC}\n"
            if find_touchdesigner_exe >/dev/null; then
                printf "${PRIMARY}Installation Complete${NC}\n"
                printf "${SECONDARY}TouchDesigner is ready to use!${NC}\n"
                printf "\n"
                print_success "Launch TouchDesigner from the shortcut."
            elif [ "$headless_mode" = true ]; then
                printf "${PRIMARY}Headless Preparation Complete${NC}\n"
                printf "${SECONDARY}Re-run this script from a graphical session to finish installation.${NC}\n"
                printf "\n"
                print_info "When you have a graphical session, re-run the installer and choose Install."
            else
                printf "${PRIMARY}Installation Complete${NC}\n"
                printf "${SECONDARY}TouchDesigner is ready to use!${NC}\n"
                printf "\n"
                print_success "Launch TouchDesigner from the shortcut."
            fi
            if [ -n "$DEBUG_LOG_FILE" ]; then
                print_info "Debug log saved to: $DEBUG_LOG_FILE"
            fi
            printf "\n"
            printf "${SECONDARY}Iswad${NC}\n"
            printf "${DIM}────────────────────────────────────────────${NC}\n\n"
            ;;
        2)
            print_banner
            print_info "Starting TouchDesigner update..."
            printf "\n"

            print_info "Regenerating launcher script..."
            create_launcher_script
            print_success "Launcher updated"

            install_optional_icon || true
            print_info "Updating winetricks..."
            download_winetricks
            print_success "Winetricks updated"

            print_info "Updating DXVK..."
            install_dxvk
            print_success "DXVK updated"

            print_info "Updating wine_ui_fixes.tox..."
            install_optional_font_fix || true
            print_success "UI fixes updated"

            printf "\n${DIM}────────────────────────────────────────────${NC}\n"
            printf "${PRIMARY}Update Complete${NC}\n"
            printf "${SECONDARY}TouchDesigner components are up to date!${NC}\n"
            printf "${DIM}────────────────────────────────────────────${NC}\n\n"
            ;;
        3)
            uninstall_touchdesigner_menu
            ;;
        0)
            print_info "Exiting..."
            exit 0
            ;;
        *)
            print_error "Invalid option"
            exit 1
            ;;
    esac
}

show_help() {
        cat << EOF
Usage: $(basename "$0") [OPTIONS]

Quick start: just run ./install.sh and follow the on-screen instructions.

Common options:
    -h, --help           Show this help and exit
    -V, --version        Show installer version and exit
    --dry-run            Simulate install (no changes made)
    --list-versions      List available TouchDesigner versions
    --check              Check environment (dependencies, GPU, etc.)

Examples:
    ./install.sh
    ./install.sh --dry-run
    ./install.sh --list-versions
    ./install.sh --check
    ./install.sh --version

For advanced options and automation: ./install.sh --help-advanced
EOF
}

show_help_advanced() {
        cat << EOF
Usage: $(basename "$0") [OPTIONS]

ADVANCED OPTIONS:
    -n, --non-interactive       No prompts (auto Y for shortcuts and .toe association)
    -f, --fast                  Fast mode (skip pauses)
    -H, --headless              Headless mode (no graphical installer)
    -d, --debug                 Enable debug output
    -x, --trace                 Bash xtrace (bash -x)
    -u, --force-uninstall       Uninstall without confirmation
    -s, --create-shortcut       Force shortcut creation
    -a, --assoc-files           Force .toe file association
    -g, --nvidia                Force NVIDIA dGPU offload
    -v, --td-version VERSION    TouchDesigner version to install
    -i, --installer PATH        Use a local .exe installer
    -c, --choice N              Pre-select main menu choice (1=Install, 2=Uninstall...)

Environment variables (for scripting/CI):
    NON_INTERACTIVE, INSTALL_CHOICE, FAST_MODE, ALLOW_HEADLESS_INSTALL,
    TD_VERSION, TD_INSTALLER_PATH, CREATE_SHORTCUT, ASSOC_FILES, USE_NVIDIA_DGPU,
    ENABLE_DXVK, FORCE_UNINSTALL, DEBUG, TRACE
Example:
    NON_INTERACTIVE=true TD_VERSION=2025.32460 bash install.sh

EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        --help-advanced)
            show_help_advanced
            exit 0
            ;;
        -V|--version)
            echo "$SCRIPT_VERSION"
            exit 0
            ;;
        --dry-run)
            DRY_RUN=true
            ;;
        --list-versions)
            LIST_VERSIONS=true
            ;;
        --check)
            CHECK_ENV=true
            ;;
        -n|--non-interactive)
            NON_INTERACTIVE=true
            ;;
        -f|--fast)
            FAST_MODE=true
            ;;
        -H|--headless)
            ALLOW_HEADLESS_INSTALL=true
            ;;
        -d|--debug)
            DEBUG=true
            ;;
        -x|--trace)
            TRACE=true
            ;;
        -u|--force-uninstall)
            FORCE_UNINSTALL=true
            ;;
        -s|--create-shortcut)
            CREATE_SHORTCUT=Y
            ;;
        -a|--assoc-files)
            ASSOC_FILES=Y
            ;;
        -g|--nvidia)
            USE_NVIDIA_DGPU=Y
            ;;
        -v|--td-version)
            if [ -z "$2" ]; then
                print_error "Missing value for $1"
                exit 1
            fi
            TD_VERSION="$2"
            shift
            ;;
        -i|--installer)
            if [ -z "$2" ]; then
                print_error "Missing value for $1"
                exit 1
            fi
            TD_INSTALLER_PATH="$2"
            shift
            ;;
        --patch-toe)
            if [ -z "$2" ]; then
                print_error "Missing value for $1"
                exit 1
            fi
            PATCH_TOE_FILE="$2"
            shift
            ;;
        -c|--choice)
            if [ -z "$2" ]; then
                print_error "Missing value for $1"
                exit 1
            fi
            INSTALL_CHOICE="$2"
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            print_info "Use -h or --help to see available options"
            exit 1
            ;;
    esac
    shift
done

if [ "$NON_INTERACTIVE" = true ]; then
    [ "$CREATE_SHORTCUT" = "N" ] && CREATE_SHORTCUT="Y"
    [ "$ASSOC_FILES" = "N" ] && ASSOC_FILES="Y"
fi

if [ "$DRY_RUN" = true ]; then
    printf "${DIM}────────────────────────────────────────────${NC}\n"
    printf "${BOLD}${PRIMARY}TouchDesigner Linux installer ${ACCENT}%s${NC}\n" "$SCRIPT_VERSION"
    printf "${SECONDARY}By Iswad${NC}\n"
    printf "${DIM}────────────────────────────────────────────${NC}\n"
    printf "\n"
    printf "Would install TouchDesigner on your system:\n"
    printf "  • Install system packages\n"
    printf "  • Download and extract Soda Wine runner (~300MB)\n"
    printf "  • Initialize Wine prefix\n"
    printf "  • Install Windows dependencies (corefonts, vcrun2019)\n"
    printf "  • Download and install TouchDesigner\n"
    printf "  • Create desktop shortcuts and file associations\n"
    printf "  • Patch .toe files with wine_ui_fixes\n"
    printf "\n"
    echo "[DRY RUN] Simulation mode enabled. No changes were made."
    exit 0
fi

if [ "$LIST_VERSIONS" = true ]; then
    list_touchdesigner_versions() {
        local td_archive="https://derivative.ca/download/archive"
        local -a versions=()
        local -a fallback_versions=(
            "2025.32460" "2025.32280" "2025.32050" "2025.31760" "2025.31550" "2025.30000" "2024.10000" "2023.12120" "2022.33910"
        )
        local td_html
        local archive_user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"
        td_html=$(mktemp)
        echo "Fetching available TouchDesigner versions..."
        download_file "$td_archive" "$td_html" "TouchDesigner archive index" "quiet" "$archive_user_agent" 8 20 1 || true
        if [ -s "$td_html" ]; then
            mapfile -t versions < <(grep -oE '20[0-9]{2}\.[0-9]{4,6}' "$td_html" | sort -Vu | sort -Vr)
        fi
        rm -f "$td_html"
        if [ "${#versions[@]}" -eq 0 ]; then
            echo "Could not fetch live version list from Derivative website."
            versions=("${fallback_versions[@]}")
            echo "Using fallback version list:"
        fi
        for v in "${versions[@]}"; do
            echo "$v"
        done
    }
    list_touchdesigner_versions
    exit 0
fi

if [ "$CHECK_ENV" = true ]; then
    check_env_report() {
        echo "Checking environment..."
        check_prerequisites
        echo "- Required commands: OK"
        if command -v glxinfo >/dev/null 2>&1; then
            echo "- GPU: $(glxinfo | grep 'OpenGL renderer' | head -n1)"
        elif command -v vulkaninfo >/dev/null 2>&1; then
            echo "- GPU: $(vulkaninfo | grep 'deviceName' | head -n1)"
        else
            echo "- GPU: (glxinfo/vulkaninfo not found)"
        fi
        echo "- Desktop session: $XDG_SESSION_TYPE ($DESKTOP_SESSION)"
        echo "- DISPLAY: $DISPLAY"
        echo "- WAYLAND_DISPLAY: $WAYLAND_DISPLAY"
        echo "- User: $USER"
        echo "- Kernel: $(uname -r)"
        echo "- Distro: $(grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '"')"
        echo "- Bash version: $BASH_VERSION"
        echo "- Home: $HOME"
        echo "- Script version: $SCRIPT_VERSION"
        echo "Environment check complete."
    }
    check_env_report
    exit 0
fi

# If --patch-toe is provided, run standalone patch mode
if [ -n "$PATCH_TOE_FILE" ]; then
    if [ ! -f "$PATCH_TOE_FILE" ]; then
        print_error "File not found: $PATCH_TOE_FILE"
        exit 1
    fi
    if [ ! -d "$RUNNER_DIR/bin" ] || [ ! -d "$WINE_PREFIX/drive_c" ]; then
        print_error "TouchDesigner Wine environment not found. Run the installer first."
        exit 1
    fi
    # Find toe tools
    _toeexpand=$(find "$WINE_PREFIX/drive_c" -type f -iname 'toeexpand.exe' 2>/dev/null | head -n1 || true)
    _toecollapse=$(find "$WINE_PREFIX/drive_c" -type f -iname 'toecollapse.exe' 2>/dev/null | head -n1 || true)
    if [ -z "$_toeexpand" ] || [ -z "$_toecollapse" ]; then
        print_error "toeexpand/toecollapse not found in Wine prefix."
        exit 1
    fi
    _fixfile="$TD_BASE_DIR/wine_ui_fixes.tox"
    if [ ! -f "$_fixfile" ]; then
        # Try to install the font fix
        install_optional_font_fix
    fi
    if [ ! -f "$_fixfile" ]; then
        print_error "wine_ui_fixes.tox not found. Cannot patch."
        exit 1
    fi
    patch_single_toe_file "$PATCH_TOE_FILE" "$_fixfile" "$_toeexpand" "$_toecollapse"
    exit $?
fi

main "$@"
