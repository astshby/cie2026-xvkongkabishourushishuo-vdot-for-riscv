#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
variant=${1:-custom}
if [[ "$variant" == baseline ]]; then
  make -C "$NOOP_HOME" emu CONFIG=KunminghuV2Config EMU_TRACE=1 WITH_CHISELDB=1 \
    JVM_XMX="${KKS_JVM_XMX:-12G}" -j"$KKS_JOBS"
  exit 0
fi
[[ "$variant" == custom ]] || { echo 'Usage: scripts/build_emu.sh [baseline|custom]' >&2; exit 2; }
python3 "$KKS_ROOT/scripts/prepare_sources.py"
cp "$KKS_ROOT/rtl/VDot16.scala" "$KKS_XS/src/main/scala/xiangshan/backend/fu/vector/VDot16.scala"
cp "$KKS_ROOT/rtl/KksVDot.scala" "$KKS_XS/src/main/scala/xiangshan/backend/decode/KksVDot.scala"
python3 "$KKS_ROOT/scripts/apply_patches.py" XiangShan
# 新模块从 rtl/ 复制到对应 package；补丁负责接入既有译码和 VIPU。
cmp "$KKS_ROOT/rtl/VDot16.scala" "$KKS_XS/src/main/scala/xiangshan/backend/fu/vector/VDot16.scala"
cmp "$KKS_ROOT/rtl/KksVDot.scala" "$KKS_XS/src/main/scala/xiangshan/backend/decode/KksVDot.scala"
export NOOP_HOME="$KKS_XS"
make -C "$KKS_XS" emu CONFIG=KunminghuV2Config EMU_TRACE=1 WITH_CHISELDB=1 \
  JVM_XMX="${KKS_JVM_XMX:-12G}" -j"$KKS_JOBS"
python3 "$KKS_ROOT/scripts/record_emu_build.py"
