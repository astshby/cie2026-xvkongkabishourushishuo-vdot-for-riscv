#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
python3 "$KKS_ROOT/scripts/prepare_sources.py"
cp "$KKS_ROOT/rtl/VDot16.scala" "$KKS_XS/src/main/scala/xiangshan/backend/fu/vector/VDot16.scala"
cp "$KKS_ROOT/rtl/KksVDot.scala" "$KKS_XS/src/main/scala/xiangshan/backend/decode/KksVDot.scala"
cp "$KKS_ROOT/rtl/VDot16Spec.scala" "$KKS_XS/src/test/scala/xiangshan/VDot16Spec.scala"
cp "$KKS_ROOT/rtl/EmitVDot16.scala" "$KKS_XS/src/test/scala/xiangshan/EmitVDot16.scala"
cd "$KKS_XS"
mill -i -Djvm-xmx=12G xiangshan.test.testOnly xiangshan.VDot16Spec
