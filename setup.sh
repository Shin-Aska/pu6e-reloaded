#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'USAGE'
Usage: bash setup.sh [--skip-system-packages] [--help]

Set up Python 3.14, the locked development and packaging dependencies, and
the Linux desktop libraries needed by pu6e Reloaded. No existing Python or
uv installation is required. A downloaded uv stays in build/tools and
does not change your shell profile or global PATH.

Linux: automatic system package installation supports Debian, Ubuntu,
and Linux Mint; sudo is used only when required packages are missing.
macOS: macOS 13 or later on Intel or Apple Silicon; no Homebrew required.
Windows: use setup.ps1 instead.

Options:
  --skip-system-packages  Use system libraries already provisioned by you.
                         Also allows other Linux distributions.
  --help                 Show this help without changing anything.
USAGE
}

skip_system_packages=false
show_help=false
for argument in "$@"; do
    case "$argument" in
        --skip-system-packages) skip_system_packages=true ;;
        --help|-h) show_help=true ;;
        *) printf 'Unknown option: %s\n' "$argument" >&2; usage >&2; exit 2 ;;
    esac
done
if "$show_help"; then
    usage
    exit 0
fi

platform="$(uname -s)"
architecture="$(uname -m)"
case "$platform" in
    Linux)
        case "$architecture" in
            x86_64|aarch64) ;;
            *) printf 'Unsupported Linux architecture: %s. Use x86_64 or aarch64.\n' "$architecture" >&2; exit 1 ;;
        esac
        ;;
    Darwin)
        case "$architecture" in
            x86_64|arm64) ;;
            *) printf 'Unsupported macOS architecture: %s. Use Intel or Apple Silicon.\n' "$architecture" >&2; exit 1 ;;
        esac
        macos_version="$(sw_vers -productVersion)"
        if [[ "${macos_version%%.*}" -lt 13 ]]; then
            printf 'macOS 13 or later is required by Qt; found %s.\n' "$macos_version" >&2
            exit 1
        fi
        ;;
    MINGW*|MSYS*|CYGWIN*)
        printf 'On Windows, run setup.ps1 from PowerShell instead of setup.sh.\n' >&2
        exit 1
        ;;
    *) printf 'Unsupported operating system: %s.\n' "$platform" >&2; exit 1 ;;
esac

install_linux_packages() {
    local ID='' ID_LIKE=''
    if [[ -r /etc/os-release ]]; then
        . /etc/os-release
    fi
    case " $ID $ID_LIKE " in
        *' debian '*|*' ubuntu '*|*' linuxmint '*) ;;
        *)
            printf '%s\n' \
                'Automatic system package installation supports Debian, Ubuntu, and Linux Mint.' \
                'On this distribution, install curl, CA certificates, OpenGL/GLU, D-Bus, Qt X11/XCB' \
                'runtime libraries, desktop-file-utils, binutils, file, x11-utils, xauth, Xvfb, and zip' \
                'with your package manager, then run: bash setup.sh --skip-system-packages' >&2
            exit 1
            ;;
    esac
    if ! command -v apt-get >/dev/null 2>&1 || ! command -v dpkg-query >/dev/null 2>&1; then
        printf 'Debian-family setup requires apt-get and dpkg-query. Use --skip-system-packages only if dependencies are already installed.\n' >&2
        exit 1
    fi

    local package status missing_count=0
    local packages=(
        git curl ca-certificates binutils file desktop-file-utils
        libdbus-1-3 libegl1 libgl1 libgl1-mesa-dri libglu1-mesa
        libxkbcommon-x11-0 libxcb-cursor0 libxcb-glx0
        libxcb-icccm4 libxcb-image0 libxcb-keysyms1
        libxcb-randr0 libxcb-render-util0 libxcb-shape0
        libxcb-xinerama0 libxcb-xkb1 x11-utils xauth xvfb zip
    )
    local missing_packages=()
    for package in "${packages[@]}"; do
        status="$(dpkg-query -W -f='${Status}' "$package" 2>/dev/null || true)"
        if [[ "$status" != 'install ok installed' ]]; then
            missing_packages+=("$package")
            missing_count=$((missing_count + 1))
        fi
    done
    if [[ "$missing_count" -eq 0 ]]; then
        printf 'Linux system dependencies are already installed.\n'
        return
    fi

    printf 'Installing missing system packages: %s\n' "${missing_packages[*]}"
    if [[ "$EUID" -eq 0 ]]; then
        apt-get update
        apt-get install -y --no-install-recommends "${missing_packages[@]}"
    elif command -v sudo >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y --no-install-recommends "${missing_packages[@]}"
    else
        printf 'System dependencies are missing and sudo is unavailable. Ask an administrator to install the packages listed above, then rerun setup.\n' >&2
        exit 1
    fi
}

if [[ "$platform" == Linux ]] && ! "$skip_system_packages"; then
    install_linux_packages
fi

project_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_directory"
tools_directory="$project_directory/build/tools"
installer_file=''
trap 'if [[ -n "$installer_file" ]]; then rm -f -- "$installer_file"; fi' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [[ -x "$tools_directory/uv" ]]; then
    uv_command="$tools_directory/uv"
elif command -v uv >/dev/null 2>&1; then
    uv_command="$(command -v uv)"
else
    if ! command -v curl >/dev/null 2>&1; then
        printf 'curl is required to download uv. Install curl and CA certificates, then rerun setup.\n' >&2
        exit 1
    fi
    mkdir -p "$tools_directory"
    installer_file="$(mktemp "${TMPDIR:-/tmp}/pu6e-uv-install.XXXXXX")"
    curl --fail --location --show-error --proto '=https' --tlsv1.2 \
        --output "$installer_file" https://astral.sh/uv/0.12.9/install.sh
    UV_UNMANAGED_INSTALL="$tools_directory" sh "$installer_file"
    uv_command="$tools_directory/uv"
fi

"$uv_command" --version
"$uv_command" sync --locked --python 3.14 --group packaging
"$uv_command" pip check --python "$project_directory/.venv/bin/python"
"$uv_command" run --no-sync python -c \
    'import numpy; import PySide6.QtCore; import PySide6.QtWidgets; import OpenGL.GL; print("Python, NumPy, Qt Widgets, and PyOpenGL imports verified.")'

printf '\nSetup complete. Run the editor with:\n  "%s/.venv/bin/pu6e"\n' "$project_directory"
