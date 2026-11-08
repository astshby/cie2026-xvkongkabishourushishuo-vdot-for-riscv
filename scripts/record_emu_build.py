#!/usr/bin/env python3
"""成功构建后记录实际产物，供后续运行与源码一致性检查使用。"""
import hashlib
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = ['rtl/VDot16.scala', 'rtl/KksVDot.scala', 'patches/xiangshan.patch',
         'work/XiangShan/build/rtl/VDot16.sv', 'work/XiangShan/build/emu']
out = root / 'build/emu-build-manifest.json'
check = sys.argv[1:] == ['--check']
if sys.argv[1:] not in ([], ['--check']):
    raise SystemExit('Usage: record_emu_build.py [--check]')
if check and not out.is_file():
    raise SystemExit('缺少构建清单，请先运行 scripts/build_emu.sh')
record = {'config': 'KunminghuV2Config', 'EMU_TRACE': 1, 'WITH_CHISELDB': 1, 'sha256': {}}
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
    print('EMU_BUILD_CHECK PASS')
else:
    out.write_text(json.dumps(record, indent=2) + '\n')
    print('Build manifest:', out)
    print(json.dumps(record, indent=2))
