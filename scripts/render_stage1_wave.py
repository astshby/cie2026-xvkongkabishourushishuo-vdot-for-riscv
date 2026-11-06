#!/usr/bin/env python3
"""从本次精简VCD读取握手信号，绘图并生成GTKWave的Tcl视图。"""
import argparse
import csv
import gzip
from pathlib import Path
import os
import subprocess
os.environ.setdefault('MPLCONFIGDIR', str(Path(__file__).resolve().parents[1] / 'build/matplotlib-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib import font_manager

p = argparse.ArgumentParser()
p.add_argument('evidence', type=Path)
a = p.parse_args()
rows = list(csv.DictReader((a.evidence / 'vadd-events.csv').open()))
start, end = int(rows[0]['vcd_time'])-4, int(rows[-1]['vcd_time'])+4
offsets = {int(r['sim_timer'])-int(r['vcd_time']) for r in rows}
assert len(offsets) == 1
offset = offsets.pop()
pc = int(rows[0]['pc'], 16)
decode = 'decode__io_in_' + rows[0]['slot']
rob = 'rob__io_enq_req_' + rows[1]['slot']
unit = rows[2]['slot'] + '__VialuFix'
commit = rows[4]['slot']
names, values, times, samples = {}, {}, [], []

wave = a.evidence / 'vadd-selected.vcd'
stream = wave.open() if wave.exists() else gzip.open(str(wave)+'.gz', 'rt')
with stream as f:
    for line in f:
        parts = line.split()
        if parts and parts[0] == '$var':
            names[parts[4]] = (parts[3], int(parts[2]))
        if '$enddefinitions' in line:
            break
    def value(suffix):
        matches = [code for name, (code, _) in names.items() if name.endswith(suffix)]
        assert len(matches) == 1, suffix
        raw = values.get(matches[0], 'x')
        return int(raw, 2) if raw and set(raw) <= {'0','1'} else None
    def sample(t):
        if t is None or not start <= t <= end:
            return
        times.append(t+offset)
        samples.append([
            value(decode+'_valid') == 1 and value(decode+'_ready') == 1 and value(decode+'_bits_pc') == pc,
            value(rob+'_valid') == 1 and value(rob+'_bits_pc') == pc,
            value(unit+'__io_in_valid') == 1 and value(unit+'__io_in_ready') == 1,
            value(unit+'__io_out_valid') == 1 and value(unit+'__io_out_ready') == 1,
            value('rob__io_commits_isCommit') == 1 and value('rob__io_commits_commitValid_'+commit) == 1
                and value('rob__io_commits_info_'+commit+'_debug_pc') == pc])
    t = None
    for line in f:
        if line.startswith('#'):
            sample(t)
            t = int(line[1:])
            if t > end+1:
                break
        elif line.startswith(('b','B')):
            parts = line.split()
            if len(parts) == 2:
                values[parts[1]] = parts[0][1:]
        elif line and line[0] in '01xXzZ':
            values[line[1:].strip()] = line[0]
    sample(t)

assert times and len(times) == len(samples)
font_file = subprocess.check_output(['fc-match', '-f', '%{file}', 'Noto Sans CJK SC'], text=True).strip()
font_manager.fontManager.addfont(font_file)
font_name = font_manager.FontProperties(fname=font_file).get_name()
plt.rcParams.update({'font.family':font_name, 'axes.unicode_minus':False})
labels = ['译码接收', 'ROB分配', 'ALU输入握手', 'ALU输出握手', 'ROB提交']
fig, axes = plt.subplots(5, 1, figsize=(11.8, 5.2), sharex=True)
for i, ax in enumerate(axes):
    ys = [int(s[i]) for s in samples]
    ax.step(times, ys, where='post', color='#000000', linewidth=1.7)
    ax.set_ylim(-.15, 1.45)
    ax.set_yticks([0,1])
    ax.set_ylabel(labels[i], rotation=0, ha='right', va='center', labelpad=18, fontsize=10)
    ax.grid(axis='x', alpha=.22)
    event_time = int(rows[i]['sim_timer'])
    assert any(x == event_time and y == 1 for x,y in zip(times,ys)), rows[i]
    ax.annotate(str(event_time), (event_time,1), xytext=(3,5), textcoords='offset points', color='#000000', fontsize=10)
    ax.spines[['top','right']].set_visible(False)
axes[-1].set_xlim(start+offset,end+offset)
axes[-1].xaxis.set_major_locator(MaxNLocator(integer=True, nbins=12))
axes[-1].ticklabel_format(useOffset=False,style='plain',axis='x')
axes[-1].set_xlabel('仿真周期 sim_timer')
fig.suptitle(f'vadd.vv 实测握手波形  PC={pc:#x}', fontsize=14)
fig.text(.17,.015,'译码、ROB与提交信号按目标PC筛选；执行单元为 '+rows[2]['slot']+'.VialuFix。',fontsize=9,color='#000000')
fig.subplots_adjust(left=.17,right=.98,top=.9,bottom=.13,hspace=.18)
for suffix in ['png']:
    fig.savefig(a.evidence/f'vadd-handshakes.{suffix}',dpi=180)
plt.close(fig)

suffixes = ['TOP__clock','TOP__SimTop__difftest_timer',decode+'_valid',decode+'_ready',
            decode+'_bits_pc',decode+'_bits_instr',rob+'_valid',rob+'_bits_pc',
            unit+'__io_in_valid',unit+'__io_in_ready',unit+'__io_in_bits_data_src_0',
            unit+'__io_in_bits_data_src_1',unit+'__io_out_valid',unit+'__io_out_ready',
            unit+'__io_out_bits_res_data','rob__io_commits_isCommit',
            'rob__io_commits_commitValid_'+commit,'rob__io_commits_info_'+commit+'_debug_pc']
selected = []
for suffix in suffixes:
    matches = [name for name in names if name.endswith(suffix)]
    assert len(matches) == 1
    selected.append('selected.'+matches[0])
tcl = ['# Run: gtkwave vadd-selected.vcd --script=view-vadd.tcl',
       'set requested [list '+' '.join('{'+name+'}' for name in selected)+']',
       'set found [list]', 'set n [gtkwave::getNumFacs]',
       'foreach requested_name $requested {',
       '  for {set i 0} {$i < $n} {incr i} {',
       '    set name [gtkwave::getFacName $i]',
       '    set base [regsub {\\[[^]]+\\]$} $name ""]',
       '    if {$base eq $requested_name} {lappend found $name; break}',
       '  }', '}', 'puts "stage1 signals selected: [llength $found]"',
       'gtkwave::addSignalsFromList $found',
       f'gtkwave::setZoomRangeTimes {start} {end}',
       f'gtkwave::setMarker {rows[2]["vcd_time"]}']
for marker,row,label in zip('ABCDE',rows,['decode','ROB','ALU-in','ALU-out','commit']):
    tcl.append(f'gtkwave::setNamedMarker {marker} {row["vcd_time"]} "{label}"')
tcl += ['puts "stage1 waveform view ready"',
        'if {[info exists ::env(KKS_WAVE_SMOKE_TEST)]} {',
        '  exit 0', '}']
(a.evidence/'view-vadd.tcl').write_text('\n'.join(tcl)+'\n')
print('WAVE FIGURE PASS: five handshake traces read from actual VCD; GTKWave Tcl view written')
