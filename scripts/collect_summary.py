#!/usr/bin/env python3
"""从原始日志摘录证据，并同时记录日志的 SHA256，保持来源可查。"""
import argparse
import hashlib
from pathlib import Path
import re

p = argparse.ArgumentParser()
p.add_argument('log', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
raw = a.log.read_bytes()
s = re.sub(r'\x1b\[[0-9;]*m', '', raw.decode(errors='replace'))
needles = ['KKS_RUN', 'hello xiangshan', 'PASS', 'FAIL', 'HIT GOOD TRAP',
           'HIT BAD TRAP', 'instrCnt', 'reference model', 'different at pc', 'KKS_PERF', 'KKS_ILLEGAL']
lines = [x for x in s.splitlines() if any(n in x for n in needles) or re.match(r'^[0-9a-f]{64}\s', x)]
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text('raw_log_sha256: ' + hashlib.sha256(raw).hexdigest() + '\n' + '\n'.join(lines) + '\n')
print(a.output)
