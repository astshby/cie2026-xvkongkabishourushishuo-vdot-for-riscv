#!/usr/bin/env python3
"""记录复现所需版本；不读取账号令牌或用户环境秘密。"""
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
XS_ENV = Path(os.environ.get('XS_ENV', ROOT.parent / 'xs-env')).resolve()


def run(*args, cwd=None):
    p = subprocess.run(args, text=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.stdout.strip()


repos = {}
for name in ('XiangShan', 'NEMU', 'nexus-am'):
    path = XS_ENV / name
    repos[name] = {'commit': run('git', '-C', str(path), 'rev-parse', 'HEAD'),
                   'dirty': run('git', '-C', str(path), 'status', '--short')}
repos['XiangShan']['submodules'] = run('git', '-C', str(XS_ENV / 'XiangShan'), 'submodule', 'status')
tools = {}
for name in ('mill', 'java', 'verilator', os.environ.get('CROSS_COMPILE', 'riscv64-unknown-linux-gnu-')+'gcc', 'gcc', 'make'):
    path = shutil.which(name)
    if name == 'mill':
        # launcher 在沙箱里可能无法启动 server；工程固定版本以版本文件为准。
        pin = (XS_ENV / 'XiangShan/.mill-version').read_text().strip()
        tools[name] = {'path': path, 'version': [pin], 'source': 'XiangShan/.mill-version'}
    else:
        tools[name] = {'path': path, 'version': run(path, '-version' if name == 'java' else '--version').splitlines()[:3] if path else []}
output = {'repos': repos, 'tools': tools, 'memory': run('free', '-h'),
          'cpu_count': os.cpu_count(), 'base_config': 'KunminghuV2Config',
          'semantics': {'elements': 16, 'sew': 8, 'vlen': 128, 'result_bits': 32}}
print(json.dumps(output, indent=2, ensure_ascii=False))
