#!/usr/bin/env bash
# Клонирует оригинал Instrument Serif (SIL OFL) в reference/instrument-serif.
# Там лежат исходники (.glyphs), готовые шрифты и OFL.txt, с которых снимаются все измерения.
# Версию с fonts.gstatic.com для измерений не использовать: она урезана
# (342 глифа, только ccmp/liga/locl), в оригинале 377 глифов и ещё aalt/case/dlig/ordn/ss01.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p reference
if [ -d reference/instrument-serif/.git ]; then
  git -C reference/instrument-serif pull --ff-only -q
else
  GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 -q https://github.com/Instrument/instrument-serif reference/instrument-serif
fi
echo "commit: $(git -C reference/instrument-serif rev-parse --short HEAD)"
ls reference/instrument-serif/sources reference/instrument-serif/fonts/ttf
