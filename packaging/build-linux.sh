#!/usr/bin/env bash
set -euo pipefail

project_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_directory"

architecture="$(uname -m)"
if [[ "$architecture" != x86_64 ]]; then
    printf 'Linux release builds currently require x86_64; found %s.\n' "$architecture" >&2
    exit 1
fi

release_version="${RELEASE_VERSION:-$(uv run --no-sync python -c "from importlib.metadata import version; print(version('pu6e-reloaded'))")}"
release_version="${release_version#v}"
release_directory="$project_directory/dist/release"
portable_parent="$project_directory/dist/linux"
portable_directory="$portable_parent/pu6e-reloaded"
build_directory="$project_directory/build/pyinstaller/linux"

mkdir -p "$release_directory" "$build_directory"

uv run --no-sync pyinstaller \
    --noconfirm \
    --clean \
    --windowed \
    --onedir \
    --name pu6e-reloaded \
    --collect-submodules OpenGL.platform \
    --copy-metadata PyOpenGL \
    --add-data "$project_directory/LICENSE:." \
    --add-data "$project_directory/NOTICE.md:." \
    --add-data "$project_directory/THIRD_PARTY_NOTICES.md:." \
    --specpath "$build_directory" \
    --workpath "$build_directory/work" \
    --distpath "$portable_parent" \
    pu6e.py

install -m644 LICENSE NOTICE.md THIRD_PARTY_NOTICES.md "$portable_directory/"

(
    cd "$portable_parent"
    zip --filesync --symlinks --recurse-paths \
        "$release_directory/pu6e-reloaded-${release_version}-linux-x86_64.zip" \
        pu6e-reloaded
)

app_directory="$(mktemp -d "$project_directory/build/pu6e.AppDir.XXXXXX")"
mkdir -p \
    "$app_directory/usr/lib/pu6e-reloaded" \
    "$app_directory/usr/share/applications" \
    "$app_directory/usr/share/icons/hicolor/scalable/apps" \
    "$app_directory/usr/share/doc/pu6e-reloaded"

cp -a "$portable_directory/." "$app_directory/usr/lib/pu6e-reloaded/"
install -m755 packaging/AppRun "$app_directory/AppRun"
install -m644 packaging/pu6e-reloaded.desktop "$app_directory/pu6e-reloaded.desktop"
install -m644 packaging/pu6e-reloaded.desktop \
    "$app_directory/usr/share/applications/pu6e-reloaded.desktop"
install -m644 packaging/pu6e-reloaded.svg "$app_directory/pu6e-reloaded.svg"
install -m644 packaging/pu6e-reloaded.svg \
    "$app_directory/usr/share/icons/hicolor/scalable/apps/pu6e-reloaded.svg"
install -m644 LICENSE NOTICE.md THIRD_PARTY_NOTICES.md \
    "$app_directory/usr/share/doc/pu6e-reloaded/"
ln -s pu6e-reloaded.svg "$app_directory/.DirIcon"

desktop-file-validate "$app_directory/pu6e-reloaded.desktop"

appimage_tool="${APPIMAGETOOL:-$project_directory/build/tools/appimagetool-x86_64.AppImage}"
if [[ ! -x "$appimage_tool" ]]; then
    mkdir -p "$(dirname -- "$appimage_tool")"
    curl --fail --location --show-error \
        --output "$appimage_tool" \
        https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x "$appimage_tool"
fi

ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$appimage_tool" \
    --no-appstream \
    "$app_directory" \
    "$release_directory/pu6e-reloaded-${release_version}-linux-x86_64.AppImage"

printf 'Linux release artifacts are available in %s\n' "$release_directory"
