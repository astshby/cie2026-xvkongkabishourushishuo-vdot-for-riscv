/* 无 AM、无 UART 的 NEMU 功能测试。测试驱动通过物理内存交换数据。 */
.section .text
.global _start
_start:
  li t0, 0x600
  csrs mstatus, t0
  /* 参考模型启用了 Smdbltrp：固件必须先解除复位后的 MDT 防护。 */
  li t0, 0x40000000000 /* RV64 mstatus.MDT 在 bit 42 */
  csrc mstatus, t0
  csrsi 0x744, 8 /* mnstatus.NMIE：使普通非法指令异常可进入 mtvec */
  la t0, trap_handler
  csrw mtvec, t0
  li a0, 0x80010000
  li a1, 0x80010010
  li a2, 0x80010100
  li a3, 0x80010200
loop:
  /* 先在合法配置下装满输入，避免vill、VS=Off负例在load处提前异常。
   * config={AVL,vtype,vstart,flags,vcsr}，flags bit0=masked，bit1=VSOff。
   */
  vsetivli zero,16,e8,m1,tu,mu
  vle8.v v8, (a0)
  vle8.v v12, (a1)
  vmv.v.i v10,-1
  lw t0, 0x50(a0)
  csrw vcsr,t0
  lw t0, 0x40(a0)
  lw t1, 0x44(a0)
  vsetvl zero, t0, t1
  lw t0, 0x48(a0)
  csrw vstart, t0
  lw t0, 0x4c(a0)
  andi t1,t0,2
  beqz t1,1f
  li t1,0x600
  csrc mstatus,t1
1:
  andi t0,t0,1
  bnez t0, masked
.global kks_nemu_dot
kks_nemu_dot:
  .word 0x0e860557 /* vdot.vv v10,v8,v12 */
  vse8.v v10, (a2)
  addi t1, a2, 16
  .word 0x0e860457 /* vd=vs2=v8 */
  vse8.v v8, (t1)
  vle8.v v8, (a0)
  addi t1, a2, 32
  .word 0x0e860657 /* vd=vs1=v12 */
  vse8.v v12, (t1)
  vle8.v v12, (a1)
  addi t1, a2, 48
  .word 0x0e840557 /* vdot.vv v10,v8,v8: 相同源 */
  vse8.v v10, (t1)
  addi t1, a2, 64
  .word 0x0e860057 /* vd=v0，仍是非掩码指令 */
  vse8.v v0, (t1)
  csrr t0,vcsr
  sw t0,16(a3)
  li t0, 0x1234
  sw t0, 0(a3)
  j loop
masked:
.global kks_nemu_masked
kks_nemu_masked:
  .word 0x0c860557
  j loop
.align 2
trap_handler:
  csrr t0, mcause
  sw t0, 4(a3)
  csrr t0, mepc
  sd t0, 8(a3)
  /* 恢复访问后直接保存旧目的寄存器，检查异常没有提交向量写入。 */
  li t0,0x600
  csrs mstatus,t0
  csrwi vstart,0
  vsetivli zero,16,e8,m1,tu,mu
  vs1r.v v10,(a2)
  csrr t0,vcsr
  sw t0,16(a3)
  li t0,0xdead
  sw t0,0(a3)
trap_loop:
  j trap_loop
