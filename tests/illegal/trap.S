.text
.align 2
.global kks_trap
kks_trap:
  addi sp, sp, -32
  sd t0, 0(sp)
  sd t1, 8(sp)
  csrr t0, mcause
  la t1, kks_cause
  sd t0, 0(t1)
  csrr t0, mepc
  la t1, kks_epc
  sd t0, 0(t1)
  addi t0, t0, 4 /* 所有被测非法编码均为32位 */
  csrw mepc, t0
  /* VS=Off负例进入此处后，先恢复向量CSR访问，再清除vstart。 */
  li t0, 0x600
  csrs mstatus, t0
  csrwi vstart, 0
  ld t0, 0(sp)
  ld t1, 8(sp)
  addi sp, sp, 32
  mret
