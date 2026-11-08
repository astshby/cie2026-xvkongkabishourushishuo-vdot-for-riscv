#!/usr/bin/env python3
"""仅在隔离副本应用本仓库补丁；重复执行可识别已应用状态。"""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
for name in sys.argv[1:] or ['XiangShan']:
    target = root / 'work' / name.split('-', 1)[0]
    patch = root / 'patches' / (name.lower() + '.patch')
    if not patch.exists():
        raise SystemExit(f'补丁不存在：{patch}，请使用对应阶段的完整源码')
    cmd = ['git', '-C', str(target), 'apply']
    check = subprocess.run(cmd + ['--check', str(patch)], capture_output=True)
    if check.returncode == 0:
        subprocess.run(cmd + [str(patch)], check=True)
        print('Applied', name)
    elif subprocess.run(cmd + ['--reverse', '--check', str(patch)], capture_output=True).returncode == 0:
        print('Already applied', name)
    else:
        raise SystemExit(f'{name}: 工作树与补丁不兼容，保留现状，请使用新的 XS_ENV/工作目录复现')
