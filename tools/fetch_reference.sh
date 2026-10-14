#!/usr/bin/env bash
# Скачивает эталонный Instrument Serif (SIL OFL) в reference/ для измерений.
# Бинарники в git не кладём: reference/*.ttf в .gitignore.
set -euo pipefail
cd "$(dirname "$0")/../reference"
curl -fsS -o IS-Regular.ttf "https://fonts.gstatic.com/s/instrumentserif/v5/jizBRFtNs2ka5fXjeivQ4LroWlx-2zI.ttf"
curl -fsS -o IS-Italic.ttf  "https://fonts.gstatic.com/s/instrumentserif/v5/jizHRFtNs2ka5fXjeivQ4LroWlx-6zATiw.ttf"
ls -la IS-*.ttf
