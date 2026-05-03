#!/bin/sh
# los-bootstrap one-line installer for Linux and macOS.
#
# What this does:
#   1. Detects your OS and package manager (apt, dnf, pacman, zypper, brew).
#   2. Installs `pipx` and `adb` via that package manager (with sudo on Linux).
#   3. Runs `pipx install "los-bootstrap[wizard]"`.
#
# What this does NOT do:
#   - Bundle adb. We use whatever your distro ships.
#   - Install fastboot or heimdall (only needed for `flash run` / Samsung).
#   - Modify any system config beyond installing those two packages.
#
# Usage:
#   sh install.sh                # interactive (asks for sudo when needed)
#   sh install.sh --dry-run      # print what would happen, run nothing
#   sh install.sh --yes          # skip confirmations
#   sh install.sh --allow-root   # permit running as root (otherwise refused)
#
# Read the source before piping a curl into sh. This script is short on
# purpose so you can audit it in one sitting.

set -eu

DRY_RUN=0
ASSUME_YES=0
ALLOW_ROOT=0

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --yes|-y) ASSUME_YES=1 ;;
        --allow-root) ALLOW_ROOT=1 ;;
        --help|-h)
            sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            printf 'unknown argument: %s\n' "$arg" >&2
            exit 2
            ;;
    esac
done

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }

confirm() {
    [ "$ASSUME_YES" -eq 1 ] && return 0
    [ "$DRY_RUN" -eq 1 ] && return 0
    printf '%s [y/N] ' "$1"
    read -r answer
    case "$answer" in
        y|Y|yes|YES) return 0 ;;
        *) return 1 ;;
    esac
}

run() {
    cmd="$*"
    printf '    $ %s\n' "$cmd"
    [ "$DRY_RUN" -eq 1 ] && return 0
    # shellcheck disable=SC2086
    sh -c "$cmd"
}

if [ "$(id -u)" = "0" ] && [ "$ALLOW_ROOT" -ne 1 ]; then
    die "refusing to run as root. pipx installs into your user home; rerun without sudo, or pass --allow-root if you really mean it."
fi

OS="$(uname -s)"
case "$OS" in
    Linux)
        if [ -r /etc/os-release ]; then
            # shellcheck disable=SC1091
            . /etc/os-release
            DISTRO="${ID:-unknown}"
        else
            DISTRO="unknown"
        fi
        ;;
    Darwin) DISTRO="macos" ;;
    *)
        die "unsupported OS: $OS. Linux and macOS only. For Windows, use scripts/install.ps1."
        ;;
esac

PIPX_PKG=""
ADB_PKG=""
PM=""
SUDO=""
if [ "$OS" = "Linux" ] && [ "$(id -u)" != "0" ]; then
    SUDO="sudo"
fi

case "$DISTRO" in
    ubuntu|debian|raspbian|pop|linuxmint|elementary)
        PM="apt"; PIPX_PKG="pipx"; ADB_PKG="android-tools-adb"
        ;;
    fedora|rhel|centos|rocky|almalinux)
        PM="dnf"; PIPX_PKG="pipx"; ADB_PKG="android-tools"
        ;;
    arch|manjaro|endeavouros|cachyos)
        PM="pacman"; PIPX_PKG="python-pipx"; ADB_PKG="android-tools"
        ;;
    opensuse*|suse|sles)
        PM="zypper"; PIPX_PKG="python3-pipx"; ADB_PKG="android-tools"
        ;;
    macos)
        PM="brew"; PIPX_PKG="pipx"; ADB_PKG="android-platform-tools"
        SUDO=""
        ;;
    *)
        warn "unrecognised distro: $DISTRO"
        warn "install pipx and adb manually, then run: pipx install \"los-bootstrap[wizard]\""
        exit 1
        ;;
esac

log "detected: $OS / $DISTRO (package manager: $PM)"

if [ "$PM" = "brew" ] && ! command -v brew >/dev/null 2>&1; then
    die "Homebrew not found. Install it from https://brew.sh and re-run."
fi

log "los-bootstrap installer plan"
echo "    1. install pipx via $PM"
echo "    2. install $ADB_PKG via $PM (provides the adb binary)"
echo "    3. pipx install \"los-bootstrap[wizard]\""
echo
echo "    fastboot and heimdall are NOT installed by default. The flash"
echo "    subcommand will tell you when you need them."
echo

if [ "$DRY_RUN" -eq 1 ]; then
    log "dry-run mode — printing commands without executing"
fi

if ! confirm "proceed?"; then
    warn "aborted by user"
    exit 1
fi

case "$PM" in
    apt)
        run "$SUDO apt update"
        run "$SUDO apt install -y $PIPX_PKG $ADB_PKG"
        ;;
    dnf)
        run "$SUDO dnf install -y $PIPX_PKG $ADB_PKG"
        ;;
    pacman)
        run "$SUDO pacman -Sy --needed --noconfirm $PIPX_PKG $ADB_PKG"
        ;;
    zypper)
        run "$SUDO zypper install -y $PIPX_PKG $ADB_PKG"
        ;;
    brew)
        run "brew install $PIPX_PKG $ADB_PKG"
        ;;
esac

run "pipx ensurepath"
run "pipx install --force \"los-bootstrap[wizard]\""

log "done."
echo
echo "    If 'los-bootstrap' isn't found yet, restart your shell so the"
echo "    pipx PATH change takes effect (or: source ~/.bashrc / ~/.zshrc)."
echo
echo "    Next steps:"
echo "      los-bootstrap version"
echo "      los-bootstrap                    # interactive wizard"
echo "      los-bootstrap audit              # privacy/degoogle audit"
