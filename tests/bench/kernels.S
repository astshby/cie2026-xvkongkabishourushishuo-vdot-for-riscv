/* 两个内核保持相同输入/输出布局和循环依赖。
 * 计时包含实际指令序列与循环开销，不能据此宣称纯组合逻辑延迟。
 * 返回 {compute_cycles, end_to_end_cycles}，符合 RV64 两寄存器结构体 ABI。
 */
.text
.align 2
.global kks_dot_kernel
kks_dot_kernel:
  fence rw,rw
  rdcycle t4
  fence rw,rw
  vsetivli zero,16,e8,m1,tu,mu
  vle8.v v8,(a0)
  vle8.v v9,(a1)
  mv t2,a3
  fence rw,rw
  rdcycle t5
  fence rw,rw
1:
.global kks_dot_exec
kks_dot_exec:
  .word 0x0e848557 /* v10 = dot16(v8,v9) */
  vmv.v.v v8,v10 /* 下一次 dot 依赖本次完整结果，测量依赖链 */
  addi t2,t2,-1
  bnez t2,1b
  fence rw,rw
  rdcycle t6
  fence rw,rw
  vse8.v v8,(a2)
  fence rw,rw
  rdcycle t3
  sub a0,t6,t5
  sub a1,t3,t4
  ret

.align 2
.global kks_baseline_kernel
kks_baseline_kernel:
  fence rw,rw
  rdcycle t4
  fence rw,rw
  vsetivli zero,16,e8,m1,tu,mu
  vle8.v v8,(a0)
  vle8.v v9,(a1)
  vmv.v.i v20,0  /* 归约初值，最低16位为0 */
  vmv.v.i v24,0  /* tu 策略保留的目的尾部必须预先清零 */
  mv t2,a3
  fence rw,rw
  rdcycle t5
  fence rw,rw
2:
.global kks_baseline_mul
kks_baseline_mul:
  vwmul.vv v16,v8,v9 /* signed int8 -> int16，v16/v17 保存16个积 */
  vsetivli zero,16,e16,m2,tu,mu
.global kks_baseline_reduce
kks_baseline_reduce:
  vwredsum.vs v24,v16,v20 /* int16 -> int32 的扩宽求和，防止中间溢出 */
  vsetivli zero,16,e8,m1,tu,mu
.global kks_baseline_move
kks_baseline_move:
  vmv.v.v v8,v24
  addi t2,t2,-1
  bnez t2,2b
  fence rw,rw
  rdcycle t6
  fence rw,rw
  vse8.v v8,(a2)
  fence rw,rw
  rdcycle t3
  sub a0,t6,t5
  sub a1,t3,t4
  ret
