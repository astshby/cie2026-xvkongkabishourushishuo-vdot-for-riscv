#!/usr/bin/env python3
"""首次获取推荐依赖提交；保留已存在的其他提交及本地修改。"""
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
lock = json.loads((root / 'env/nemu-dependencies.json').read_text())
urls = {
    'softfloat/repo': 'https://github.com/ucb-bar/berkeley-softfloat-3.git',
    'nanopb': 'https://github.com/nanopb/nanopb.git',
    'LibCheckpoint': 'https://github.com/OpenXiangShan/LibCheckpoint.git',
    'gcpt_restore': 'https://github.com/OpenXiangShan/LibCheckpointAlpha.git',
}
for rel, sha in lock.items():
    repo = root / 'work/NEMU/resource' / rel
    if not (repo / '.git').exists():
        # 首次defconfig尚未启用FPU时不会下载softfloat；直接获取锁定提交，
        # 不依赖运行过一次make，也不先编译远端当前HEAD。
        repo.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'init', str(repo)], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['git', '-C', str(repo), 'remote', 'add', 'origin', urls[rel]], check=True)
        subprocess.run(['git', '-C', str(repo), 'fetch', '--depth=1', 'origin', sha], check=True)
        subprocess.run(['git', '-C', str(repo), 'checkout', '--detach', sha], check=True)
    cmd = ['git', '-C', str(repo)]
    head = subprocess.check_output(cmd + ['rev-parse', 'HEAD'], text=True).strip()
    print(f'NEMU dependency {rel}: {head}')
    if head != sha:
        print(f'NOTICE: 推荐 {sha}；保留现有提交，继续编译以检查兼容性')
print('NEMU dependencies ready')
