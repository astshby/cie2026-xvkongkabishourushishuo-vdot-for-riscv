#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
python3 "$KKS_ROOT/scripts/prepare_sources.py"
python3 "$KKS_ROOT/scripts/apply_patches.py" NEMU
if [[ -f "$KKS_ROOT/patches/nemu-compat.patch" ]]; then
  python3 "$KKS_ROOT/scripts/apply_patches.py" NEMU-compat
fi
export NEMU_HOME="$KKS_NEMU"
cp "$KKS_ROOT/env/nemu-ref.config" "$KKS_NEMU/configs/kks-v2-ref_defconfig"
python3 "$KKS_ROOT/scripts/pin_nemu_deps.py"
make -C "$KKS_NEMU" kks-v2-ref_defconfig
make -C "$KKS_NEMU" -j"$KKS_JOBS"
mkdir -p "$KKS_ROOT/build"
"${CROSS_COMPILE}gcc" -nostdlib -nostartfiles -static -march=rv64gcv -mabi=lp64d \
  -Wl,-Ttext=0x80000000 -Wl,--build-id=none "$KKS_ROOT/tests/nemu/loop.S" -o "$KKS_ROOT/build/nemu-loop.elf"
"${CROSS_COMPILE}objcopy" -O binary "$KKS_ROOT/build/nemu-loop.elf" "$KKS_ROOT/build/nemu-loop.bin"
python3 "$KKS_ROOT/scripts/record_emu_build.py" --nemu
