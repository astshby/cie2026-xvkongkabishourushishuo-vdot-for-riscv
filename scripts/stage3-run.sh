#!/usr/bin/env bash
# 先用build_emu.sh构建本作品RTL；本脚本只在隔离目录构建和运行第三阶段材料。
set -euo pipefail
source "$(dirname "$0")/env.sh"
stage3_dir="$KKS_ROOT/stages/03-verification"
mkdir -p "$stage3_dir"/{logs,waves,images}
python3 "$KKS_ROOT/scripts/record_emu_build.py" --check
bash "$KKS_ROOT/scripts/build_nemu.sh" > "$stage3_dir/logs/NEMU构建.log" 2>&1
python3 "$KKS_ROOT/scripts/test_nemu.py" > "$stage3_dir/logs/NEMU指令测试.log" 2>&1

: > "$stage3_dir/logs/程序构建.log"
for app in vdot illegal bench smoke vadd; do
  bash "$KKS_ROOT/scripts/build_app.sh" "$app" >> "$stage3_dir/logs/程序构建.log" 2>&1
done
stage3_run() {
  local app=$1 name=$2 rc
  shift 2
  if KKS_TIMEOUT=3600 bash "$KKS_ROOT/scripts/run_emu.sh" "$app" custom diff "$@"; then
    rc=0
  else
    rc=$?
  fi
  cp "$KKS_ROOT/build/logs/$app-custom-diff.log" "$stage3_dir/logs/$name.log"
  return "$rc"
}
stage3_run vdot 点积协同仿真
stage3_run illegal 非法配置协同仿真
stage3_run vadd 标准向量回归
stage3_run bench 性能测试
stage3_run smoke 波形仿真 --dump-wave --wave-path "$KKS_ROOT/build/stage3-full.vcd" -b 3000 -e 9000
python3 "$KKS_ROOT/scripts/analyze_stage3.py" wave "$KKS_ROOT/build/stage3-full.vcd" > "$stage3_dir/logs/分析过程.log" 2>&1
python3 "$KKS_ROOT/scripts/analyze_stage3.py" perf "$stage3_dir/logs/性能测试.log" >> "$stage3_dir/logs/分析过程.log" 2>&1
python3 "$KKS_ROOT/scripts/analyze_stage3.py" figures >> "$stage3_dir/logs/分析过程.log" 2>&1
# 精简波形保存了实际选取的信号与全部变化；清理可重新生成的整核大文件。
rm -- "$KKS_ROOT/build/stage3-full.vcd"
echo 'STAGE3 PASS: DiffTest、RVV基线、性能数据和波形图片已生成'
