#include "kks.h"
#include "dot16_hw.h"

volatile uint64_t kks_cause,kks_epc;
extern void kks_trap(void);
static uint32_t result[4] __attribute__((aligned(16)));

// 与RVC混排时，32位指令可以从半字边界开始；逐字节读取避免未对齐C指针。
static uint32_t instruction_at(uintptr_t pc) {
  const volatile uint8_t *p=(const volatile uint8_t *)pc;
  return (uint32_t)p[0] | ((uint32_t)p[1]<<8) | ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24);
}

int main(void) {
  kks_enable_vector();
  __asm__ volatile("csrw mtvec,%0" : : "r"(kks_trap) : "memory");
  // 锁定版本实现双重陷阱检查：清除mstatus.MDT，并保持mnstatus.NMIE=1，
  // 使主动制造的非法指令进入mtvec。0x744为mnstatus，bit3为NMIE。
  const uintptr_t mdt=1ull<<42;
  __asm__ volatile("csrc mstatus,%0\n\tcsrsi 0x744,8" : : "r"(mdt) : "memory");
  for(unsigned mode=0;mode<8;++mode) {
    kks_cause=kks_epc=0;
    __asm__ volatile("vsetivli zero,16,e8,m1,tu,mu\n\tvmv.v.i v8,1\n\tvmv.v.i v9,2\n\tvmv.v.i v10,-1"
                     : : : "v8","v9","v10","memory");
    switch(mode) {
      case 0: __asm__ volatile("vsetivli zero,15,e8,m1,tu,mu" : : : "memory");break;
      case 1: __asm__ volatile("vsetivli zero,8,e16,m1,tu,mu" : : : "memory");break;
      case 2: __asm__ volatile("vsetivli zero,16,e8,m2,tu,mu" : : : "memory");break;
      case 3: __asm__ volatile("csrwi vstart,1" : : : "memory");break;
      case 5: __asm__ volatile("vsetivli zero,0,e8,m1,tu,mu" : : : "memory");break;
      case 6: // 不支持的e128设置vill，避免手工改写只读的vtype CSR。
        __asm__ volatile("li t0,0x20\n\tli t1,16\n\tvsetvl zero,t1,t0" : : : "t0","t1","memory");break;
      case 7: {
        const uintptr_t vs=3u<<9;
        __asm__ volatile("csrc mstatus,%0" : : "r"(vs) : "memory");break;
      }
    }
    if(mode==2) __asm__ volatile(KKS_DOT_INST(10,8,12) : : : "v10","memory");
    else if(mode==4) __asm__ volatile(".word " KKS_STRING(KKS_DOT_WORD(10,8,9,0)) : : : "v10","memory");
    else __asm__ volatile(KKS_DOT_INST(10,8,9) : : : "v10","memory");
    // 重新设置可访问的向量配置，whole-register store检查全部128位旧值。
    __asm__ volatile("vsetivli zero,16,e8,m1,tu,mu\n\tvs1r.v v10,(%0)" : : "r"(result) : "memory");
    if(kks_cause!=2 || !kks_epc ||
       (instruction_at((uintptr_t)kks_epc)&0xfc00707f)!=0x0c000057 ||
       result[0]!=0xffffffff || result[1]!=0xffffffff || result[2]!=0xffffffff || result[3]!=0xffffffff) {
      printf("ILLEGAL FAIL mode=%u cause=%lu epc=%lx vd=%08x %08x %08x %08x\n",
              mode,kks_cause,kks_epc,result[0],result[1],result[2],result[3]);return 1;
    }
    printf("ILLEGAL CASE PASS mode=%u cause=2 preserved128=PASS\n",mode);
  }
  printf("ILLEGAL PASS modes=8\n");return 0;
}
