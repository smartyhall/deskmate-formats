#!/usr/bin/env bash
# Run ONLY in the MSYS2 UCRT64 shell, after completing `pacman -Syu` and any
# requested terminal restarts (repeat until no updates remain).
# Does not download proprietary ROMs or modify existing DeskMate DOSLAB fixtures.
set -euo pipefail
if [[ "${MSYSTEM:-}" != "UCRT64" ]]; then
  echo 'ERROR: Run this from MSYS2 UCRT64 (not MSYS, MINGW64, or Git Bash).' >&2
  exit 2
fi
prefix=mingw-w64-ucrt-x86_64
pacman -S --needed \
  git \
  "$prefix-gcc" "$prefix-cmake" "$prefix-ninja" "$prefix-pkgconf" \
  "$prefix-openal" "$prefix-freetype" "$prefix-sdl3" \
  "$prefix-zlib" "$prefix-zstd" "$prefix-libpng" \
  "$prefix-rtmidi" "$prefix-fluidsynth" "$prefix-libslirp" \
  "$prefix-libsndfile" "$prefix-qt5-static" \
  "$prefix-qt5-translations" "$prefix-vulkan-headers"

root=/c/DeskMateLab
mkdir -p "$root/sources" "$root/builds" "$root/setup-logs"
repo="$root/sources/86Box"
if [[ -e "$repo" && ! -d "$repo/.git" ]]; then
  echo "ERROR: $repo already exists and is not a Git checkout. Refusing overwrite." >&2
  exit 3
fi
if [[ ! -d "$repo/.git" ]]; then
  git clone --recursive https://github.com/86Box/86Box.git "$repo"
fi
cd "$repo"
git rev-parse HEAD | tee "$root/setup-logs/86box-source-commit.txt"
cmake -S . -B "$root/builds/86box-automation" -G Ninja \
  -D AUTOMATION=ON -D CMAKE_BUILD_TYPE=Release
cmake --build "$root/builds/86box-automation" --parallel 4
printf '\n86Box built with AUTOMATION=ON. Find executable in build directory.\n'
printf 'Next: in PowerShell as DeskMateLab, optionally clone official ROMs with:\n'
printf '  powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\\DeskMateLab\\Setup-86Box-ROMs.ps1\n'
printf 'ROMs, VM profile, and automation socket/MCP tests are separate from compiling.\n'
