#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
app=${1:?Usage: scripts/run_emu.sh APP [baseline|custom] [diff|nodiff] [extra emu flags...]}
variant=${2:-baseline}
mode=${3:-diff}
shift "$(( $# >= 3 ? 3 : $# ))"
case "$variant" in
  baseline) emu="$NOOP_HOME/build/emu"; ref="$NOOP_HOME/ready-to-run/riscv64-nemu-interpreter-so" ;;
  custom) emu="$KKS_XS/build/emu"; ref="$KKS_NEMU/build/riscv64-nemu-interpreter-so" ;;
  *) echo 'unknown variant' >&2; exit 2 ;;
esac
case "$mode" in
  diff) diff_args=(--diff "$ref") ;;
  nodiff) diff_args=(--no-diff) ;;
  *) echo 'unknown diff mode' >&2; exit 2 ;;
esac
[[ -x "$emu" && -f "$KKS_ROOT/build/apps/$app.bin" ]] || { echo '先构建程序和仿真器' >&2; exit 2; }
mkdir -p "$KKS_ROOT/build/logs"
log="$KKS_ROOT/build/logs/$app-$variant-$mode.log"
echo "Running $app ($variant/$mode), full log: $log"
# timeout 的退出码被保留。即使打印 PASS，只要进程失败也不报告成功。
set +e
(
  printf 'KKS_RUN mode=%s variant=%s\n' "$mode" "$variant"
  if [[ "$variant" == custom ]]; then
    python3 "$KKS_ROOT/scripts/record_emu_build.py" --check || exit 2
    if [[ "$mode" == diff ]]; then
      python3 "$KKS_ROOT/scripts/record_emu_build.py" --nemu --check || exit 2
    fi
  fi
  sha256sum "$emu" "$KKS_ROOT/build/apps/$app.bin"
  if [[ "$mode" == diff ]]; then sha256sum "$ref"; fi
  export NOOP_HOME="$(dirname "$(dirname "$emu")")"
  cd "$(dirname "$(dirname "$emu")")" || exit 2
  timeout "${KKS_TIMEOUT:-1200}" "$emu" \
    -i "$KKS_ROOT/build/apps/$app.bin" --ram-size 128MB --no-snapshot "${diff_args[@]}" "$@"
) > "$log" 2>&1
rc=$?
set -e
printf 'KKS_RUN_EXIT code=%d\n' "$rc" >> "$log"
rg 'reference model|hello xiangshan|PASS|FAIL|HIT .*TRAP|instrCnt|Host time spent|KKS_' "$log" | tail -35 || true
[[ "$rc" == 0 ]] || { echo "emu failed: exit=$rc" >&2; exit "$rc"; }
rg -q 'HIT GOOD TRAP' "$log" || { echo '未找到 GOOD TRAP，不能视为通过' >&2; exit 1; }
