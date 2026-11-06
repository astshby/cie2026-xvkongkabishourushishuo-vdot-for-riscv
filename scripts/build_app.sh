#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
app=${1:?Usage: scripts/build_app.sh hello|vadd|vdot|bench}
[[ "$app" =~ ^[a-z0-9_-]+$ ]] || exit 2
mkdir -p "$KKS_ROOT/build/include"
if [[ "$app" == hello ]]; then
  # 从内核路由表读取实际接口地址；允许复现时通过 KKS_IP_ADDRESS 指定。
  python3 - "$KKS_ROOT/build/include/identity.h" <<'PY'
import ipaddress, os, re, sys
ip = os.environ.get('KKS_IP_ADDRESS')
if not ip:
    try:
        text = open('/proc/net/fib_trie').read()
        ips = re.findall(r'\|-- ([0-9.]+)\n\s+/32 host LOCAL', text)
        ip = next(x for x in ips if not ipaddress.ip_address(x).is_loopback)
    except (OSError, StopIteration):
        raise SystemExit('无法检测 IP：请先 export KKS_IP_ADDRESS=你的虚拟机实际IP')
ipaddress.ip_address(ip)
open(sys.argv[1], 'w').write('#define KKS_IP_ADDRESS "' + ip + '"\n')
print('Hello IP:', ip)
PY
fi
make -C "$KKS_ROOT/tests/$app" ARCH=riscv64-xs MARCH=rv64gcv_zba_zbb_zbc_zbs -j"$KKS_JOBS"
mkdir -p "$KKS_ROOT/build/apps"
cp "$KKS_ROOT/tests/$app/build/kks-$app-riscv64-xs.bin" "$KKS_ROOT/build/apps/$app.bin"
cp "$KKS_ROOT/tests/$app/build/kks-$app-riscv64-xs.elf" "$KKS_ROOT/build/apps/$app.elf"
"${CROSS_COMPILE}objdump" -d "$KKS_ROOT/build/apps/$app.elf" > "$KKS_ROOT/build/apps/$app.disasm"
