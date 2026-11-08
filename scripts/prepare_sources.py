#!/usr/bin/env python3
"""在 work/ 建隔离工作树；推荐提交只作提示，兼容性由补丁和构建检查。"""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
XS_ENV = Path(os.environ.get('XS_ENV', ROOT.parent / 'xs-env')).resolve()
lock = json.loads((ROOT / 'env/versions.json').read_text())


def run(*args, **kw):
    return subprocess.run(args, check=True, text=True, **kw)


def head(repo):
    if not (repo / '.git').exists():
        raise SystemExit(f'依赖未初始化：{repo}；请按 README 获取源码及子模块')
    return subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()


def recommend(repo, expected):
    actual = head(repo)
    if actual != expected:
        print(f'NOTICE: {repo} 使用 {actual}，推荐 {expected}；继续检查补丁和构建兼容性')


am = Path(os.environ.get('AM_HOME', XS_ENV / 'nexus-am')).resolve()
recommend(am, lock['repos']['nexus-am']['commit'])
recommended_modules = dict(entry.strip().split()[:2][::-1]
                           for entry in lock['repos']['XiangShan']['submodules'].splitlines())

for name in ('XiangShan', 'NEMU'):
    source = XS_ENV / name
    target = ROOT / 'work' / name
    if not (target / '.git').exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        # 使用调用者选择的基础源码 HEAD，避免隐式切换或覆盖其环境。
        head(source)
        run('git', '-C', str(source), 'worktree', 'add', '--detach', str(target), 'HEAD')
    recommend(target, lock['repos'][name]['commit'])
    modules = target / '.gitmodules'
    if modules.exists():
        p = subprocess.run(['git', 'config', '-f', str(modules), '--get-regexp', r'^submodule\..*\.path$'], text=True, capture_output=True)
        for line in p.stdout.splitlines():
            rel = line.split(' ', 1)[1]
            dst, src = target / rel, source / rel
            expected = recommended_modules.get(rel) if name == 'XiangShan' else None
            if dst.is_symlink():
                if not dst.is_dir():
                    raise SystemExit(f'依赖链接已失效：{dst}；请恢复 XS_ENV 或使用新的作品克隆目录')
                if expected:
                    recommend(dst, expected)
                continue
            if dst.is_dir() and any(dst.iterdir()):
                # 允许调用者在隔离目录自行初始化或选择其他子模块版本。
                if expected:
                    recommend(dst, expected)
                else:
                    head(dst)
                continue
            head(src)
            if expected:
                recommend(src, expected)
            if dst.is_dir():
                dst.rmdir()  # 只允许删除空的子模块占位目录。
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.symlink_to(src, target_is_directory=True)
    print('Prepared:', target)
