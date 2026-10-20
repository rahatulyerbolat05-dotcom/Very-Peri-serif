#!/usr/bin/env bash
# Клонирует оригинал Instrument Serif (SIL OFL) в reference/instrument-serif.
# Там лежат исходники (.glyphs), готовые шрифты и OFL.txt, с которых снимаются все измерения.
# Версию с fonts.gstatic.com для измерений не использовать: она урезана
# (342 глифа, только ccmp/liga/locl), в оригинале 377 глифов и ещё aalt/case/dlig/ordn/ss01.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p reference
if [ -d reference/instrument-serif/.git ]; then
  git -C reference/instrument-serif fetch -q origin
else
  GIT_LFS_SKIP_SMUDGE=1 git clone -q https://github.com/Instrument/instrument-serif reference/instrument-serif
fi
git -C reference/instrument-serif checkout -q --detach 65c0ef225f386a3c7e87570a4aa9cc0262c2fd81
commit="$(git -C reference/instrument-serif rev-parse --short=7 HEAD)"
echo "commit: $commit"
# все измерения сняты с коммита 65c0ef2 (CLAUDE.md, раздел 1); на другом коммите сборка может отличаться
[ "$commit" = "65c0ef2" ] || echo "ВНИМАНИЕ: ожидался коммит 65c0ef2" >&2
ls reference/instrument-serif/sources reference/instrument-serif/fonts/ttf
