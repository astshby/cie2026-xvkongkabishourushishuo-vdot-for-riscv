#!/usr/bin/env bash
# 从Hello开始保留本次构建、差分运行和向量波形；已有工具链不重复安装。
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$KKS_ROOT"
export KKS_RUN_ID=${KKS_RUN_ID:-$(TZ=Asia/Shanghai date +%Y%m%d-%H%M%S)}
[[ "$KKS_RUN_ID" =~ ^[A-Za-z0-9_-]+$ ]] || { echo '运行编号只能包含字母、数字、下划线和短横线' >&2; exit 2; }
logs="stages/01-environment/logs/$KKS_RUN_ID"
evidence="stages/01-environment/evidence/$KKS_RUN_ID"
mkdir -p "$logs" "$evidence" build
: "${KKS_IP_ADDRESS:?请先设置实际虚拟机网卡的 KKS_IP_ADDRESS}"
printf 'STAGE1_RUN=%s\nHello XiangShan: build and execute\n' "$KKS_RUN_ID"
TZ=Asia/Shanghai date -Iseconds
cat tests/hello/main.c
bash scripts/build_app.sh hello 2>&1 | tee "$logs/hello-build.log"
bash scripts/run_emu.sh hello baseline diff
cp build/logs/hello-baseline-diff.log "$logs/hello-full.log"

printf '\nVector addition: build, disassemble and simulate with waveform\n'
cat tests/vadd/main.c
bash scripts/build_app.sh vadd 2>&1 | tee "$logs/vadd-build.log"
"${CROSS_COMPILE}nm" -n build/apps/vadd.elf > "$evidence/vadd-symbols.txt"
pc=$(awk '$3 == "kks_vadd_begin" { print "0x" $1 }' "$evidence/vadd-symbols.txt")
[[ -n "$pc" ]] || { echo '未找到vadd标签' >&2; exit 1; }
rg -n -A 3 -B 3 'kks_vadd_begin' build/apps/vadd.disasm | tee "$evidence/vadd-disassembly.txt"
wave="$KKS_ROOT/build/stage1-$KKS_RUN_ID.vcd"
bash scripts/run_emu.sh vadd baseline diff --dump-wave --wave-path "$wave"
cp build/logs/vadd-baseline-diff.log "$logs/vadd-full.log"
python3 scripts/extract_vadd_wave.py "$wave" --pc "$pc" --output "$evidence"
gzip -n -c "$evidence/vadd-selected.vcd" > "$evidence/vadd-selected.vcd.gz"
gzip -t "$evidence/vadd-selected.vcd.gz"
# 精简波形压缩成功后清除全量临时VCD和重复的解压副本。
rm -- "$wave" "$evidence/vadd-selected.vcd"
python3 scripts/collect_summary.py "$logs/hello-full.log" "$evidence/hello-summary.txt"
python3 scripts/collect_summary.py "$logs/vadd-full.log" "$evidence/vadd-summary.txt"

# 版本和资源信息作报告附录，不占录制时的基础性检查环节。
python3 scripts/capture_env.py > "$logs/environment.json"
python3 - "$logs/host.json" <<'PY'
import json, os, platform, subprocess, sys
from pathlib import Path
os_release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
cpu = next((line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')), '')
host = {'os': os_release.get('PRETTY_NAME', '').strip('"'), 'kernel': platform.release(),
        'architecture': platform.machine(), 'cpu': cpu, 'logical_cpus': os.cpu_count(),
        'ip_used': os.environ['KKS_IP_ADDRESS'],
        'interfaces': json.loads(subprocess.check_output(['ip', '-j', '-4', 'address', 'show', 'scope', 'global'], text=True))}
Path(sys.argv[1]).write_text(json.dumps(host, ensure_ascii=False, indent=2) + '\n')
PY
TZ=Asia/Shanghai date -Iseconds
printf 'STAGE1_COMMANDS_PASS run=%s pc=%s\n' "$KKS_RUN_ID" "$pc"
