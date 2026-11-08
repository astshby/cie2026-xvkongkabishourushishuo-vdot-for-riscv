#!/usr/bin/env python3
"""通过真正的DiffTest共享库执行指令，从内存读取完整128位结果及异常状态。"""
import argparse
import ctypes as C
import os
from pathlib import Path
import random
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    'vectors': (16, 0, 0, 0), 'vl15': (15, 0, 0, 0),
    'sew16': (8, 8, 0, 0), 'lmul2': (16, 1, 0, 0),
    'vstart1': (16, 0, 1, 0), 'masked': (16, 0, 0, 1),
    'vl0': (0, 0, 0, 0), 'vill': (16, 0x20, 0, 0),
    'vs_off': (16, 0, 0, 2),
}
p = argparse.ArgumentParser()
p.add_argument('--case', choices=CASES)
args = p.parse_args()
if args.case is None:
    for name in CASES:
        subprocess.run([sys.executable, __file__, '--case', name], check=True)
    print('NEMU SUITE PASS vector_cases=133 aliases=5 full128_checks=665 illegal_modes=8 vcsr_states=8')
    sys.exit(0)

ref = C.CDLL(str(ROOT/'work/NEMU/build/riscv64-nemu-interpreter-so'), mode=os.RTLD_LOCAL)
ref.difftest_set_ramsize.argtypes = [C.c_size_t]
ref.difftest_memcpy.argtypes = [C.c_uint64, C.c_void_p, C.c_size_t, C.c_bool]
ref.difftest_exec.argtypes = [C.c_uint64]
ref.difftest_regcpy.argtypes = [C.c_void_p, C.c_bool]
ref.difftest_set_ramsize(128*1024*1024)
ref.difftest_init()
# 锁定版本ABI前缀：32 GPR、32 FPR、18个特权/CSR字段、PC。
size = C.c_uint.in_dll(ref, 'DIFFTEST_REG_SIZE').value
assert size >= 83*8 and size % 8 == 0
state = (C.c_uint64*(size//8))()
ref.difftest_regcpy(state, False)
assert state[64] == 3 and state[82] in (0x10000000, 0x80000000), '参考库ABI不匹配'
state[82] = 0x80000000
ref.difftest_regcpy(state, True)

def put(addr, data):
    buf = C.create_string_buffer(data)
    ref.difftest_memcpy(addr, buf, len(data), True)

def get(addr, length):
    buf = C.create_string_buffer(length)
    ref.difftest_memcpy(addr, buf, length, False)
    return buf.raw

put(0x80000000, (ROOT/'build/nemu-loop.bin').read_bytes())
rng = random.Random(0x56444f54)
vectors = [([127]*16,[127]*16), ([-128]*16,[-128]*16),
           ([-128]*16,[127]*16), ([0]*8+[1]*8,[0]*8+[7]*8),
           ([0]*16,[-128]*16)]
vectors += [([rng.randrange(-128,128) for _ in range(16)],
             [rng.randrange(-128,128) for _ in range(16)]) for _ in range(128)]
if args.case != 'vectors':
    vectors = vectors[:1]
for index, (a,b) in enumerate(vectors):
    csr = index & 7
    put(0x80010000, bytes(x & 255 for x in a+b))
    put(0x80010040, struct.pack('<5I', *CASES[args.case], csr))
    put(0x80010100, bytes([0xa5])*80)
    put(0x80010200, bytes(24))
    # 每次只执行一条，收到本次完成标志立即停止，下一组从j loop重新初始化。
    for step in range(512):
        ref.difftest_exec(1)
        done = struct.unpack('<I',get(0x80010200,4))[0]
        if done:
            break
    else:
        raise AssertionError(('测试程序未完成',args.case,index))
    done,cause,epc,actual_csr = struct.unpack('<IIQI',get(0x80010200,20))
    assert actual_csr == csr,(args.case,'vcsr变化',csr,actual_csr)
    if args.case == 'vectors':
        assert done == 0x1234 and cause == 0,(done,cause,hex(epc))
        ab = sum(x*y for x,y in zip(a,b))
        totals = [ab,ab,ab,sum(x*x for x in a),ab]
        actual = get(0x80010100,80)
        for slot,total in enumerate(totals):
            expected = struct.pack('<I',total & 0xffffffff)+bytes(12)
            assert actual[slot*16:(slot+1)*16] == expected,(index,slot,total,actual.hex())
    else:
        assert done == 0xdead and cause == 2 and 0x80000000<=epc<0x80001000,(done,cause,hex(epc))
        inst = struct.unpack('<I',get(epc,4))[0]
        assert inst in (0x0e860557,0x0c860557),(args.case,hex(epc),hex(inst))
        assert get(0x80010100,16) == bytes([255])*16,'非法指令改变旧目的寄存器'
print(f'NEMU {args.case} PASS vectors={len(vectors)} result128=checked vcsr=preserved')
