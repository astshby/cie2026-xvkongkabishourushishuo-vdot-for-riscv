#!/usr/bin/env python3
"""在忽略的 work/ 建隔离工作树，复用只读子模块，保留用户原有修改。"""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
XS_ENV = Path(os.environ.get('XS_ENV', ROOT.parent / 'xs-env')).resolve()
lock = json.loads((ROOT / 'env/versions.json').read_text())


def run(*args, **kw):
    return subprocess.run(args, check=True, text=True, **kw)


# 共享的是已初始化的依赖源码，不仅检查目录存在，也核对其实际版本。
# 不自动 checkout 共享目录，以免覆盖用户环境；不匹配时给出明确错误。
am = XS_ENV / 'nexus-am'
am_sha = subprocess.check_output(['git', '-C', str(am), 'rev-parse', 'HEAD'], text=True).strip()
if am_sha != lock['repos']['nexus-am']['commit']:
    raise SystemExit(f'{am}: nexus-am 版本与锁定记录不一致')
for entry in lock['repos']['XiangShan']['submodules'].splitlines():
    expected, rel = entry.strip().split()[:2]
    src = XS_ENV / 'XiangShan' / rel
    actual = subprocess.check_output(['git', '-C', str(src), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != expected:
        raise SystemExit(f'{src}: 子模块版本不匹配，预期 {expected}，实际 {actual}')

for name in ('XiangShan', 'NEMU'):
    source = XS_ENV / name
    target = ROOT / 'work' / name
    if not (target / '.git').exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        run('git', '-C', str(source), 'worktree', 'add', '--detach', str(target), lock['repos'][name]['commit'])
    head = subprocess.check_output(['git', '-C', str(target), 'rev-parse', 'HEAD'], text=True).strip()
    if head != lock['repos'][name]['commit']:
        raise SystemExit(f'{target}: 基础版本不匹配，拒绝覆盖')
    modules = target / '.gitmodules'
    if modules.exists():
        p = subprocess.run(['git', 'config', '-f', str(modules), '--get-regexp', r'^submodule\..*\.path$'], text=True, capture_output=True)
        for line in p.stdout.splitlines():
            rel = line.split(' ', 1)[1]
            dst, src = target / rel, source / rel
            if not src.is_dir():
                raise SystemExit(f'未初始化的依赖: {src}')
            if dst.is_symlink():
                continue
            if dst.is_dir():
                dst.rmdir()  # 只允许删除空的子模块占位目录。
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.symlink_to(src, target_is_directory=True)
    print('Prepared:', target)
