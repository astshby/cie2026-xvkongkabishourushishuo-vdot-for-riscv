#!/usr/bin/env python3
"""逐行读取大 VCD，只保留指令链路信号；CSV 完全来自实测波形。"""
import argparse
import csv
from pathlib import Path
import re

p = argparse.ArgumentParser()
p.add_argument('vcd', type=Path)
p.add_argument('--pc', type=lambda s: int(s, 0), default=0x8000015e)
p.add_argument('--output', type=Path, default=Path('build/stage1-wave'))
p.add_argument('--unit', default='VialuFix', help='VDot uses Vipu')
p.add_argument('--name', default='vadd')
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
scope, signals, codes, values, rows = [], {}, set(), {}, []


def selected(path, name):
    if path in ('TOP.clock', 'TOP.SimTop.difftest_timer'):
        return True
    if path.rsplit('.', 1)[0].endswith('.inner_ctrlBlock.decode'):
        return bool(re.fullmatch(r'io_in_\d+_(ready|valid|bits_(pc|instr))', name))
    if path.rsplit('.', 1)[0].endswith('.inner_ctrlBlock.rob'):
        return bool(re.fullmatch(r'io_enq_req_\d+_(valid|bits_(pc|instr))|io_commits_(isCommit|commitValid_\d+|info_\d+_debug_(pc|instr))', name))
    if re.search(r'\.exus(?:_\d+)?\.' + re.escape(a.unit) + '$', path.rsplit('.', 1)[0]):
        return name in ('io_in_valid', 'io_in_ready', 'io_out_valid', 'io_out_ready',
                        'io_in_bits_data_src_0', 'io_in_bits_data_src_1', 'io_out_bits_res_data')
    return False


def get(suffix):
    candidates = [code for path, (_, code, _) in signals.items() if path.endswith(suffix)]
    if len(candidates) != 1:
        return None
    raw = values.get(candidates[0], 'x')
    return int(raw, 2) if set(raw) <= {'0', '1'} else None


def sample(t):
    if get('TOP.clock') != 1:
        return
    timer = get('SimTop.difftest_timer')
    for i in range(8):
        pc = get(f'.decode.io_in_{i}_bits_pc')
        if pc == a.pc and get(f'.decode.io_in_{i}_valid') == 1 and get(f'.decode.io_in_{i}_ready') == 1:
            rows.append(('decode', t, timer, i, hex(pc), hex(get(f'.decode.io_in_{i}_bits_instr') or 0), '', '', ''))
        pc = get(f'.rob.io_enq_req_{i}_bits_pc')
        if pc == a.pc and get(f'.rob.io_enq_req_{i}_valid') == 1:
            rows.append(('rob_enqueue', t, timer, i, hex(pc), hex(get(f'.rob.io_enq_req_{i}_bits_instr') or 0), '', '', ''))
        pc = get(f'.rob.io_commits_info_{i}_debug_pc')
        if pc == a.pc and get('.rob.io_commits_isCommit') == 1 and get(f'.rob.io_commits_commitValid_{i}') == 1:
            rows.append(('commit', t, timer, i, hex(pc), hex(get(f'.rob.io_commits_info_{i}_debug_instr') or 0), '', '', ''))
    for base in alu_bases:
        if get(base + '.io_in_valid') == 1 and get(base + '.io_in_ready') == 1:
            rows.append(('alu_input', t, timer, base.split('.')[-2], '', '', hex(get(base + '.io_in_bits_data_src_0') or 0), hex(get(base + '.io_in_bits_data_src_1') or 0), ''))
        if get(base + '.io_out_valid') == 1 and get(base + '.io_out_ready') == 1:
            rows.append(('alu_output', t, timer, base.split('.')[-2], '', '', '', '', hex(get(base + '.io_out_bits_res_data') or 0)))


with a.vcd.open() as f, (a.output / f'{a.name}-selected.vcd').open('w') as out:
    out.write('$timescale 1ps $end\n$scope module selected $end\n')
    for line in f:
        x = line.split()
        if not x:
            continue
        if x[0] == '$scope':
            scope.append(x[2])
        elif x[0] == '$upscope':
            scope.pop()
        elif x[0] == '$var':
            path = '.'.join(scope + [x[4]])
            if selected(path, x[4]):
                signals[path] = (int(x[2]), x[3], x[4])
                codes.add(x[3])
                out.write(f'$var wire {x[2]} {x[3]} {path.replace(".", "__")} $end\n')
        elif x[0] == '$enddefinitions':
            break
    out.write('$upscope $end\n$enddefinitions $end\n')
    alu_bases = sorted({path.rsplit('.', 1)[0] for path in signals if f'.{a.unit}.' in path})
    t = None
    for line in f:
        if line.startswith('#'):
            if t is not None:
                sample(t)
            t = int(line[1:])
            out.write(line)
        elif line.startswith(('b', 'B', 'r')):
            x = line.split()
            if len(x) == 2 and x[1] in codes:
                values[x[1]] = x[0][1:]
                out.write(line)
        elif line and line[0] in '01xzXZ' and line[1:].strip() in codes:
            values[line[1:].strip()] = line[0]
            out.write(line)
    if t is not None:
        sample(t)

with (a.output / f'{a.name}-events.csv').open('w') as f:
    w = csv.writer(f, lineterminator='\n')
    w.writerow(('event', 'vcd_time', 'sim_timer', 'slot', 'pc', 'instruction', 'vs1', 'vs2', 'result'))
    w.writerows(rows)
with (a.output / 'signals.txt').open('w') as f:
    for path in signals:
        f.write(path + '\n')
print('events', len(rows), 'signals', len(signals))
for row in rows:
    print(row)
assert any(r[0] == 'commit' for r in rows), '没有找到目标指令提交，不能生成通过证据'
