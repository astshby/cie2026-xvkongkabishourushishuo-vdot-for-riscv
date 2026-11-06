#!/usr/bin/env python3
"""在终端记录结束后核对实际日志、128位波形结果并生成本次文件清单。"""
import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('run_id')
a = p.parse_args()
if not re.fullmatch(r'[A-Za-z0-9_-]+', a.run_id):
    raise SystemExit('invalid run id')
stage = root / 'stages/01-environment'
logs, evidence = stage / 'logs' / a.run_id, stage / 'evidence' / a.run_id

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

for app, marker in [('hello', 'hello xiangshan, I am xvkongkabishourushishuo, IP address:'),
                    ('vadd', 'VADD PASS lanes=16')]:
    s = (logs / f'{app}-full.log').read_text(errors='replace')
    assert marker in s and 'HIT GOOD TRAP' in s, app
    assert 'KKS_RUN mode=diff variant=baseline' in s
    assert 'different at pc' not in s and 'HIT BAD TRAP' not in s and 'FAIL ' not in s
    for digest, path in re.findall(r'^([0-9a-f]{64})  (.+)$', s, re.M):
        assert sha(Path(path)) == digest, path

rows = list(csv.DictReader((evidence / 'vadd-events.csv').open()))
assert [r['event'] for r in rows] == ['decode', 'rob_enqueue', 'alu_input', 'alu_output', 'commit'], rows
lhs = [1, 2, 3, 4, -1, -2, -3, -4, 127, -128, 0, 42, 8, 9, 10, 11]
rhs = [10, 20, 30, 40, 1, 2, 3, 4, 1, -1, 0, -42, 1, 2, 3, 4]
expected = int.from_bytes(bytes((x+y) & 255 for x,y in zip(lhs,rhs)), 'little')
assert int(rows[3]['result'], 16) == expected
latency = int(rows[3]['sim_timer']) - int(rows[2]['sim_timer'])
assert latency > 0
assert rows[0]['pc'] == rows[1]['pc'] == rows[4]['pc']
record = logs / 'operations.typescript'
raw = record.read_text(errors='replace')
assert f'STAGE1_COMMANDS_PASS run={a.run_id}' in raw
clean = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', raw).replace('\r\n', '\n')
(logs / 'operations.log').write_text(clean)
manifest = {'run_id': a.run_id, 'checked_at': datetime.now().astimezone().isoformat(),
            'execution': 'existing baseline emulator, Hello build/run, vadd build/run and waveform',
            'hello': 'GOOD TRAP', 'vadd': 'PASS and GOOD TRAP',
            'vadd_pc': rows[0]['pc'], 'result128': f'0x{expected:032x}',
            'alu_interface_cycles': latency, 'events': rows,
            'video_status': 'awaiting participant recording', 'sha256': {}}
for folder in [logs, evidence]:
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.suffix != '.vcd' and path.name != 'manifest.json':
            manifest['sha256'][str(path.relative_to(root))] = sha(path)
for rel in ['tests/hello/main.c', 'tests/vadd/main.c', 'scripts/stage1-run.sh',
            'scripts/build_app.sh', 'scripts/run_emu.sh', 'scripts/extract_vadd_wave.py',
            'scripts/finalize_stage1.py', 'scripts/render_stage1_wave.py']:
    manifest['sha256'][rel] = sha(root / rel)
(evidence / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
(stage / 'latest-run.json').write_text(json.dumps({'run_id': a.run_id,
    'logs': str(logs.relative_to(root)), 'evidence': str(evidence.relative_to(root))}, indent=2) + '\n')
print(f'STAGE1_EVIDENCE_PASS run={a.run_id} pc={rows[0]["pc"]} result=0x{expected:032x} ALU={latency}cycle')
