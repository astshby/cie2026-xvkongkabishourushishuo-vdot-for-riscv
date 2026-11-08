#!/usr/bin/env python3
"""第三阶段实测数据处理：解析真实VCD/日志，生成波形、周期图和GTKWave视图。"""
import argparse
import gzip
import json
import os
from pathlib import Path
import re
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT/'stages/03-verification'

def save_json(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

def extract_wave(args):
    output=args.output/'waves';output.mkdir(parents=True,exist_ok=True)
    nm_tool=os.environ.get('CROSS_COMPILE','riscv64-unknown-linux-gnu-')+'nm'
    nm=subprocess.check_output([nm_tool,'-n',str(args.elf)],text=True)
    wanted={'kks_dot_exec','kks_baseline_mul','kks_baseline_reduce','kks_baseline_move'}
    targets={parts[2]:int(parts[0],16) for line in nm.splitlines()
             if len(parts:=line.split())==3 and parts[2] in wanted}
    assert set(targets)==wanted,'ELF缺少波形定位符号'
    reverse={pc:name for name,pc in targets.items()}
    scopes=[];signals={};values={};events=[];rob_map={};clock_offsets=set()
    wrapper_re=re.compile(r'\.exus(?:_\d+)?\.(Vipu|Vimac|VialuFix)$')
    parent_re=re.compile(r'\.inner_vfExuBlock\.exus(?:_\d+)?$')
    def choose(path,name):
        scope=path.rsplit('.',1)[0]
        if path in ('TOP.clock','TOP.SimTop.difftest_timer'):return True
        if scope.endswith('.inner_ctrlBlock.decode'):
            return bool(re.fullmatch(r'io_in_\d+_(ready|valid|bits_(pc|instr))',name))
        if scope.endswith('.inner_ctrlBlock.rob'):
            return bool(re.fullmatch(r'io_enq_req_\d+_(valid|bits_(pc|instr|robIdx_(flag|value)))|io_commits_(isCommit|commitValid_\d+|info_\d+_debug_(pc|instr))',name))
        if wrapper_re.search(scope):
            return name in ('io_in_valid','io_in_ready','io_out_valid','io_out_ready',
                'io_in_bits_ctrl_fuOpType','io_in_bits_ctrl_vpu_vuopIdx',
                'io_in_bits_ctrl_vpu_vsew','io_in_bits_ctrl_vpu_vlmul',
                'io_in_bits_data_src_0','io_in_bits_data_src_1',
                'io_out_bits_res_data','io_out_bits_ctrl_robIdx_flag','io_out_bits_ctrl_robIdx_value')
        if parent_re.search(scope):
            return name in ('io_in_bits_robIdx_flag','io_in_bits_robIdx_value')
        if scope.endswith('.Vipu.dot16'):
            return name in ('io_enableS1','io_enableS2','io_result','sum') or name.startswith('pairSumsReg_')
        return False
    selected=output/'执行波形.vcd.gz'
    with args.vcd.open() as source,gzip.open(selected,'wt',compresslevel=6) as dest:
        dest.write('$timescale 1ps $end\n$scope module selected $end\n')
        for line in source:
            fields=line.split()
            if not fields:continue
            if fields[0]=='$scope':scopes.append(fields[2])
            elif fields[0]=='$upscope':scopes.pop()
            elif fields[0]=='$var':
                path='.'.join(scopes+[fields[4]])
                if choose(path,fields[4]):
                    signals[path]=(int(fields[2]),fields[3])
                    dest.write(f'$var wire {fields[2]} {fields[3]} {path.replace(".","__")} $end\n')
            elif fields[0]=='$enddefinitions':break
        dest.write('$upscope $end\n$enddefinitions $end\n')
        codes={code for width,code in signals.values()}
        def unique(suffix):
            found=[s for s in signals if s.endswith(suffix)]
            assert len(found)==1,(suffix,found)
            return found[0]
        decode=unique('.decode.io_in_0_valid').rsplit('.',1)[0]
        rob=unique('.rob.io_enq_req_0_valid').rsplit('.',1)[0]
        units=sorted({s.rsplit('.',1)[0] for s in signals if wrapper_re.search(s.rsplit('.',1)[0])})
        decode_slots=sorted({int(m[1]) for s in signals if (m:=re.search(r'\.decode.io_in_(\d+)_valid$',s))})
        rob_slots=sorted({int(m[1]) for s in signals if (m:=re.search(r'\.rob.io_enq_req_(\d+)_valid$',s))})
        commit_slots=sorted({int(m[1]) for s in signals if (m:=re.search(r'\.rob.io_commits_commitValid_(\d+)$',s))})
        def get(path):
            item=signals.get(path)
            return values.get(item[1]) if item else None
        def add(kind,t,timer,pc,**kw):
            if pc in reverse:events.append(dict(event=kind,vcd_time=t,cycle=timer,target=reverse[pc],pc=hex(pc),**kw))
        def sample(t):
            if get('TOP.clock')!=1:return
            timer=get('TOP.SimTop.difftest_timer')
            if timer is None:return
            clock_offsets.add(timer-t)
            for i in decode_slots:
                b=f'{decode}.io_in_{i}'
                if get(b+'_valid')==1 and get(b+'_ready')==1:
                    pc=get(b+'_bits_pc')
                    add('decode',t,timer,pc,slot=i,instruction=hex(get(b+'_bits_instr') or 0))
            for i in rob_slots:
                b=f'{rob}.io_enq_req_{i}'
                if get(b+'_valid')==1:
                    pc=get(b+'_bits_pc');tag=(get(b+'_bits_robIdx_flag'),get(b+'_bits_robIdx_value'))
                    if None not in tag:rob_map[tag]=pc
                    add('rob_enqueue',t,timer,pc,slot=i,rob=list(tag))
            for unit in units:
                parent=unit.rsplit('.',1)[0]
                if get(unit+'.io_in_valid')==1 and get(unit+'.io_in_ready')==1:
                    tag=(get(parent+'.io_in_bits_robIdx_flag'),get(parent+'.io_in_bits_robIdx_value'))
                    add('fu_input',t,timer,rob_map.get(tag),unit=unit,rob=list(tag),
                        fuop=get(unit+'.io_in_bits_ctrl_fuOpType'),uop=get(unit+'.io_in_bits_ctrl_vpu_vuopIdx'),
                        vs1=hex(get(unit+'.io_in_bits_data_src_0') or 0),vs2=hex(get(unit+'.io_in_bits_data_src_1') or 0))
                if get(unit+'.io_out_valid')==1 and get(unit+'.io_out_ready')==1:
                    tag=(get(unit+'.io_out_bits_ctrl_robIdx_flag'),get(unit+'.io_out_bits_ctrl_robIdx_value'))
                    add('fu_output',t,timer,rob_map.get(tag),unit=unit,rob=list(tag),
                        result=hex(get(unit+'.io_out_bits_res_data') or 0))
            for i in commit_slots:
                if get(rob+'.io_commits_isCommit')==1 and get(f'{rob}.io_commits_commitValid_{i}')==1:
                    add('commit',t,timer,get(f'{rob}.io_commits_info_{i}_debug_pc'),slot=i)
        t=None
        for line in source:
            if line.startswith('#'):
                if t is not None:sample(t)
                t=int(line[1:]);dest.write(line)
            elif line.startswith(('b','B')):
                fields=line.split()
                if len(fields)==2 and fields[1] in codes:
                    raw=fields[0][1:]
                    values[fields[1]]=int(raw,2) if set(raw)<={'0','1'} else None
                    dest.write(line)
            elif line and line[0] in '01xXzZ' and line[1:].strip() in codes:
                values[line[1:].strip()]=int(line[0]) if line[0] in '01' else None
                dest.write(line)
        if t is not None:sample(t)
    assert len(clock_offsets)==1,('仿真计数与VCD采样单位不一致',clock_offsets)
    offset=clock_offsets.pop()
    for name in wanted:
        assert any(r['event']=='commit' and r['target']==name for r in events),('没有目标提交',name)
    dot_in=[r for r in events if r['target']=='kks_dot_exec' and r['event']=='fu_input']
    dot_out=[r for r in events if r['target']=='kks_dot_exec' and r['event']=='fu_output']
    assert len(dot_in)==len(dot_out)==1,(dot_in,dot_out)
    assert int(dot_out[0]['result'],16)==((-32416)&0xffffffff),'完整128位点积结果不匹配'
    assert dot_in[0]['rob']==dot_out[0]['rob'],'输入输出ROB标识不一致'
    dot_latency=dot_out[0]['cycle']-dot_in[0]['cycle']
    assert dot_latency>0
    base=[r for r in events if r['target'] in ('kks_baseline_mul','kks_baseline_reduce')]
    b0=min(r['cycle'] for r in base if r['event']=='fu_input')
    b1=max(r['cycle'] for r in base if r['event']=='fu_output')
    data={'targets':{k:hex(v) for k,v in targets.items()},'timer_offset':offset,
          'events':events,'dot_latency':dot_latency,'baseline_math_span':b1-b0,
          'signals':{name:{'width':width,'code':code} for name,(width,code) in signals.items()}}
    save_json(output/'波形数据.json',data)
    write_gtk(output,data,dot_in[0],dot_out[0],b0-offset,b1-offset)
    print('WAVE_PARSE PASS selected_signals='+str(len(signals)))
    for row in events:print(json.dumps(row,ensure_ascii=False))
    print(f'WAVE_LATENCY dot={dot_latency} baseline_math_span={b1-b0} result128=0x{int(dot_out[0]["result"],16):032x}')

def write_gtk(folder,data,din,dout,base_start,base_end):
    names=data['signals']
    unit=din['unit'];parent=unit.rsplit('.',1)[0]
    wanted=['TOP.clock','TOP.SimTop.difftest_timer']
    for suffix in ['.io_in_valid','.io_in_ready','.io_in_bits_ctrl_fuOpType',
                   '.io_in_bits_data_src_0','.io_in_bits_data_src_1',
                   '.dot16.io_enableS1','.dot16.io_enableS2','.dot16.pairSumsReg_4',
                   '.dot16.pairSumsReg_5','.io_out_valid','.io_out_ready','.io_out_bits_res_data']:
        if unit+suffix in names:wanted.append(unit+suffix)
    for path in names:
        if '.Vimac.' in path and path.rsplit('.',1)[-1] in ('io_in_valid','io_out_valid','io_out_bits_res_data'):
            wanted.append(path)
    def gtkname(n):return 'selected.'+n.replace('.','__')
    tcl=['# 打开同目录执行波形.vcd.gz，并用本脚本选取实测信号。',
         'set requested [list '+' '.join('{'+gtkname(n)+'}' for n in wanted)+']',
         'set found [list]','set count [gtkwave::getNumFacs]',
         'foreach requested_name $requested {',
         '  for {set i 0} {$i < $count} {incr i} {',
         '    set name [gtkwave::getFacName $i]',
         '    set base [regsub {\\[[^]]+\\]$} $name ""]',
         '    if {$base eq $requested_name} {lappend found $name; break}',
         '  }','}',
         'if {[llength $found] != [llength $requested]} {error "selected waveform signal missing"}',
         'gtkwave::addSignalsFromList $found',
         'if {[info exists ::env(KKS_WAVE_VIEW)] && $::env(KKS_WAVE_VIEW) eq "baseline"} {',
         f'  gtkwave::setZoomRangeTimes {base_start-4} {base_end+4}',
         f'  gtkwave::setMarker {base_start}',
         '} else {',f'  gtkwave::setZoomRangeTimes {din["vcd_time"]-4} {dout["vcd_time"]+6}',
         f'  gtkwave::setMarker {din["vcd_time"]}','}',
         f'gtkwave::setNamedMarker A {din["vcd_time"]} "dot-in"',
         f'gtkwave::setNamedMarker B {dout["vcd_time"]} "dot-out"',
         f'gtkwave::setNamedMarker C {base_start} "baseline-in"',
         f'gtkwave::setNamedMarker D {base_end} "baseline-out"',
         'puts "GTKWave stage3 selected [llength $found] signals"',
         'if {[info exists ::env(KKS_WAVE_SMOKE_TEST)]} {exit 0}']
    # 使用ASCII文件名，兼容本环境GTKWave 3.3的Tcl初始化。
    (folder/'view.tcl').write_text('\n'.join(tcl)+'\n')

def analyze_perf(args):
    text=args.log.read_text(errors='replace')
    assert all(s in text for s in ['BASELINE_EQ PASS cases=5','BENCH PASS','HIT GOOD TRAP','KKS_RUN_EXIT code=0','Difftest enabled.'])
    assert 'BENCH FAIL' not in text
    pattern=r'KKS_PERF count=(\d+) sample=(\d+) baseline=(\d+) dot=(\d+) baseline_total=(\d+) dot_total=(\d+)'
    rows=[tuple(map(int,parts)) for parts in re.findall(pattern,text)]
    assert len(rows)==15 and {(r[0],r[1]) for r in rows}=={(n,i) for n in (1,8,32) for i in range(5)}
    assert all(all(v>0 for v in row[2:]) for row in rows)
    summary=[]
    for n in (1,8,32):
        group=[r for r in rows if r[0]==n]
        b,d,bt,dt=[statistics.median(r[i] for r in group) for i in range(2,6)]
        summary.append(dict(count=n,baseline=b,dot=d,baseline_total=bt,dot_total=dt,
                            speedup=b/d,total_speedup=bt/dt,
                            baseline_range=[min(r[2] for r in group),max(r[2] for r in group)],
                            dot_range=[min(r[3] for r in group),max(r[3] for r in group)]))
    save_json(args.output/'logs/性能数据.json',{'columns':['count','sample','baseline','dot','baseline_total','dot_total'],'samples':rows,'summary':summary})
    print('PERF_ANALYSIS PASS samples=15 equivalent_cases=5')
    for row in summary:print(json.dumps(row,ensure_ascii=False))

def figures(args):
    os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'build/matplotlib-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.ticker import MaxNLocator
    font_path=subprocess.check_output(['fc-match','-f','%{file}','Noto Sans CJK SC'],text=True).strip()
    font_manager.fontManager.addfont(font_path)
    plt.rcParams.update({'font.family':font_manager.FontProperties(fname=font_path).get_name(),
                         'axes.unicode_minus':False,'text.color':'black','axes.labelcolor':'black',
                         'axes.edgecolor':'black','xtick.color':'black','ytick.color':'black'})
    folder=args.output/'images';folder.mkdir(parents=True,exist_ok=True)
    wave=json.loads((args.output/'waves/波形数据.json').read_text())
    perf=json.loads((args.output/'logs/性能数据.json').read_text())
    events=wave['events']
    dot=[r for r in events if r['target']=='kks_dot_exec']
    enq=next(r for r in dot if r['event']=='rob_enqueue')
    # 同一PC可在flush前反复出现在译码端；选最后一次进入目标ROB前的译码观察。
    dec=max((r for r in dot if r['event']=='decode' and r['cycle']<=enq['cycle']),key=lambda r:r['cycle'])
    ordered=[dec,enq]+[next(r for r in dot if r['event']==s) for s in ['fu_input','fu_output','commit']]
    fig,axes=plt.subplots(2,1,figsize=(11.5,8.0))
    ax=axes[0];lo=dec['cycle']-2;hi=ordered[-1]['cycle']+2
    labels=['译码接收（最后一次）','ROB分配','VIPU输入握手','VIPU输出握手','ROB提交']
    for i,(r,label) in enumerate(zip(ordered,labels)):
        y=4-i;t=r['cycle']
        ax.step([lo,t,t+1,hi],[y,y+.65,y,y],where='post',color='black',linewidth=1.5)
        ax.annotate(str(t),(t,y+.65),xytext=(2,3),textcoords='offset points',fontsize=10)
    ax.set_yticks(range(5),labels[::-1]);ax.set_ylim(-.35,5.0);ax.set_xlim(lo,hi)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_title(f'vdot：ROB={tuple(enq["rob"])}，输入到输出 {wave["dot_latency"]} 拍')
    ax.set_xlabel('仿真周期 sim_timer')
    ax.grid(axis='x',color='0.85',linewidth=.6)
    ax=axes[1]
    base=[r for r in events if r['target'] in ('kks_baseline_mul','kks_baseline_reduce')]
    lanes=[('kks_baseline_mul','fu_input','vwmul 输入'),('kks_baseline_mul','fu_output','vwmul 输出'),
           ('kks_baseline_reduce','fu_input','vwredsum 输入'),('kks_baseline_reduce','fu_output','vwredsum 输出')]
    for i,(target,kind,label) in enumerate(lanes):
        rlist=[r for r in base if r['target']==target and r['event']==kind]
        y=3-i
        for r in rlist:
            t=r['cycle'];ax.plot([t,t],[y,y+.6],color='black',linewidth=1.5)
            ax.plot(t,y+.6,'ko',markersize=3)
            ax.annotate(str(t),(t,y+.6),xytext=(2,3),textcoords='offset points',fontsize=9)
    ax.set_yticks(range(4),[x[2] for x in lanes][::-1]);ax.set_ylim(-.35,4.05)
    b0=min(r['cycle'] for r in base if r['event']=='fu_input')
    b1=max(r['cycle'] for r in base if r['event']=='fu_output')
    ax.set_xlim(b0-2,b1+2);ax.xaxis.set_major_locator(MaxNLocator(integer=True,nbins=12))
    ax.set_title(f'RVV数学运算片段：首个乘法输入到最终归约输出 {b1-b0} 拍')
    ax.set_xlabel('仿真周期 sim_timer');ax.grid(axis='x',color='0.85',linewidth=.6)
    for ax in axes:
        ax.spines[['top','right']].set_visible(False)
        ax.ticklabel_format(useOffset=False,style='plain',axis='x')
    fig.suptitle('同一输入的真实执行事件：低八对为零，上八对非零',fontsize=14)
    fig.text(.5,.012,'两幅图使用不同横轴窗口；结果均为 0x000000000000000000000000ffff8160。',ha='center',fontsize=10)
    fig.subplots_adjust(left=.2,right=.98,top=.91,bottom=.09,hspace=.55)
    fig.savefig(folder/'波形与延迟.png',dpi=180);plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(11.5,4.5))
    groups=perf['summary'];xs=list(range(len(groups)));width=.34
    for ax,(left,right,title) in zip(axes,[('baseline','dot','计算窗口'),('baseline_total','dot_total','完整调用窗口')]):
        b=[r[left] for r in groups];d=[r[right] for r in groups]
        ax.bar([x-width/2 for x in xs],b,width,color='white',edgecolor='black',hatch='///',label='RVV基线')
        ax.bar([x+width/2 for x in xs],d,width,color='0.75',edgecolor='black',label='vdot')
        for x,v in zip([x-width/2 for x in xs],b):ax.text(x,v+max(b)*.02,str(v),ha='center',fontsize=10)
        for x,v in zip([x+width/2 for x in xs],d):ax.text(x,v+max(b)*.02,str(v),ha='center',fontsize=10)
        ax.set_xticks(xs,[str(r['count']) for r in groups]);ax.set_xlabel('依赖链中的点积次数')
        ax.set_ylabel('实测周期中位数');ax.set_title(title);ax.set_ylim(0,max(b)*1.17)
        ax.spines[['top','right']].set_visible(False);ax.legend(frameon=False)
    fig.suptitle('同一昆明湖V2配置：每种长度暖机后采样五次',fontsize=14)
    fig.tight_layout(rect=[0,0,1,.91]);fig.savefig(folder/'周期对比.png',dpi=180);plt.close(fig)
    print('FIGURES PASS actual_vcd_events=checked actual_perf_samples=15 black_and_white=enabled')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=DEFAULT)
    sub=p.add_subparsers(dest='command',required=True)
    w=sub.add_parser('wave');w.add_argument('vcd',type=Path);w.add_argument('--elf',type=Path,default=ROOT/'build/apps/smoke.elf')
    f=sub.add_parser('perf');f.add_argument('log',type=Path)
    sub.add_parser('figures')
    args=p.parse_args()
    {'wave':extract_wave,'perf':analyze_perf,'figures':figures}[args.command](args)

if __name__=='__main__':main()
