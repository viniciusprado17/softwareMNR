#!/usr/bin/env bash
# Compila o nucleo do firmware (firmware/lib/coldchain_core) para o PC e roda os vetores
# dourados. As assinaturas geradas pelo C++ sao verificadas pelo Python.
# Uso: bash firmware/test_host/run.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
BUILD="$ROOT/firmware/.host_build"
UECC_COMMIT="541b3a78026420a3e369c4c9281c396b5e531113"  # mesmo commit do platformio.ini
UECC_DIR="$BUILD/micro-ecc"

mkdir -p "$BUILD"
if [ ! -f "$UECC_DIR/uECC.c" ]; then
  git clone -q https://github.com/kmackay/micro-ecc.git "$UECC_DIR"
  git -C "$UECC_DIR" checkout -q "$UECC_COMMIT"
fi

CORE="$ROOT/firmware/lib/coldchain_core/src"
gcc -O2 -c "$UECC_DIR/uECC.c" -I"$UECC_DIR" -o "$BUILD/uECC.o"
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -I"$CORE" -I"$UECC_DIR" \
  "$HERE/test_core.cpp" "$CORE"/cc_packet.cpp "$CORE"/cc_sha256.cpp "$CORE"/cc_signer.cpp \
  "$CORE"/cc_selftest.cpp "$BUILD/uECC.o" -o "$BUILD/test_core"

"$BUILD/test_core" | tee "$BUILD/output.txt"
python3 "$ROOT/tools/check_fw_output.py" --vectors "$BUILD/output.txt"
