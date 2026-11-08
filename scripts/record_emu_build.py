#!/usr/bin/env python3
"""成功构建后记录实际产物，供后续运行与源码一致性检查使用。"""
import hashlib
import json
import argparse
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check', action='store_true')
parser.add_argument('--nemu', action='store_true', help='记录或校验NEMU参考库')
args = parser.parse_args()
files = ['rtl/VDot16.scala', 'rtl/KksVDot.scala', 'patches/xiangshan.patch',
         'work/XiangShan/build/rtl/VDot16.sv', 'work/XiangShan/build/emu']
out = root / 'build/emu-build-manifest.json'
check = args.check
record = {'config': 'KunminghuV2Config', 'EMU_TRACE': 1, 'WITH_CHISELDB': 1, 'sha256': {}}
label = 'EMU'
if args.nemu:
    files = ['patches/nemu.patch', 'patches/nemu-compat.patch',
             'env/nemu-ref.config', 'env/nemu-dependencies.json',
             'work/NEMU/.config',
             'work/NEMU/src/isa/riscv64/include/isa-all-instr.h',
             'work/NEMU/src/isa/riscv64/instr/rvv/decode.h',
             'work/NEMU/src/isa/riscv64/instr/rvv/vcompute.h',
             'work/NEMU/src/cpu/difftest/ref.c', 'work/NEMU/src/isa/riscv64/system/intr.c',
             'work/NEMU/build/riscv64-nemu-interpreter-so']
    out = root / 'build/nemu-build-manifest.json'
    record = {'reference': 'NEMU', 'sha256': {}}
    label = 'NEMU'
if check and not out.is_file():
    script = 'build_nemu.sh' if args.nemu else 'build_emu.sh'
    raise SystemExit(f'缺少构建清单，请先运行 scripts/{script}')
for rel in files:
    digest = hashlib.sha256()
    with (root / rel).open('rb') as f:
        # Ubuntu 22.04默认Python 3.10，没有3.11新增的file_digest接口。
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    record['sha256'][rel] = digest.hexdigest()
if check:
    if json.loads(out.read_text()) != record:
        raise SystemExit('源码或模拟器与成功构建记录不一致，请重新构建后运行')
    print(f'{label}_BUILD_CHECK PASS')
else:
    out.write_text(json.dumps(record, indent=2) + '\n')
    print('Build manifest:', out)
    print(json.dumps(record, indent=2))
