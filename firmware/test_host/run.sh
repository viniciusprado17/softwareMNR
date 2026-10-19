#!/usr/bin/env bash
# Compila o nucleo do firmware (firmware/lib/coldchain_core) para o PC e roda os vetores
# dourados. As assinaturas geradas pelo C++ sao verificadas pelo Python.
# Uso: bash firmware/test_host/run.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
BUILD="$ROOT/firmware/.host_build"
mkdir -p "$BUILD"

# Mesmos fontes que o PlatformIO compila (micro-ecc local com simbolos renomeados).
CORE="$ROOT/firmware/lib/coldchain_core/src"
gcc -O2 -c "$CORE/cc_uecc.c" -I"$CORE" -o "$BUILD/uECC.o"
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -I"$CORE" \
  "$HERE/test_core.cpp" "$CORE"/cc_packet.cpp "$CORE"/cc_sha256.cpp "$CORE"/cc_signer.cpp \
  "$CORE"/cc_selftest.cpp "$BUILD/uECC.o" -o "$BUILD/test_core"

"$BUILD/test_core" | tee "$BUILD/output.txt"
python3 "$ROOT/tools/check_fw_output.py" --vectors "$BUILD/output.txt"
