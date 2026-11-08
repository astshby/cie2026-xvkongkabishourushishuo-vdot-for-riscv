#include "kks.h"
#include "dot16_ref.h"
#include "dot16_hw.h"

static int8_t a[16] __attribute__((aligned(16)));
static int8_t b[16] __attribute__((aligned(16)));
static uint32_t result[4] __attribute__((aligned(16)));
static uint32_t mixed[3][4] __attribute__((aligned(16)));
static unsigned vectors[4], checks[4], csr_seen;
static uint32_t rng = 0x56444f54;
static volatile uint32_t branch_zero;

static uint32_t next_random(void) {
  rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5;
  return rng;
}
static void fill(int x,int y) {
  for (unsigned i=0;i<16;++i) { a[i]=(int8_t)x; b[i]=(int8_t)y; }
}
static int equal128(const uint32_t x[4],uint32_t expected) {
  return x[0]==expected && x[1]==0 && x[2]==0 && x[3]==0;
}

/* C标量参考不使用向量归约或RTL加法树。五个寄存器变体都检查完整结果。
 * 每次预设vcsr并检查保持，覆盖vxrm的4种值和vxsat的两个初值。
 */
static int run_case(unsigned group) {
  const unsigned id=vectors[group]++;
  for (unsigned variant=0;variant<5;++variant) {
    const uint32_t expected=(uint32_t)dot16_ref(a,variant==3?a:b);
    const uintptr_t csr_expected=(id+variant)&7;
    uintptr_t csr_actual,start_actual;
    for (unsigned i=0;i<4;++i) result[i]=0xa5a5a5a5;
    __asm__ volatile("csrw vcsr,%0" : : "r"(csr_expected) : "memory");
    dot16_hw(a,b,result,variant);
    __asm__ volatile("csrr %0,vcsr\n\tcsrr %1,vstart" : "=r"(csr_actual),"=r"(start_actual) : : "memory");
    if (!equal128(result,expected) || csr_actual!=csr_expected || start_actual!=0) {
      printf("VDOT FAIL group=%u case=%u alias=%u expected=%08x got=%08x %08x %08x %08x vcsr=%lu/%lu vstart=%lu\n",
             group,id,variant,expected,result[0],result[1],result[2],result[3],csr_actual,csr_expected,start_actual);
      return 0;
    }
    csr_seen |= 1u<<csr_actual;
    ++checks[group];
  }
  return 1;
}

static int dependency_and_interleave(void) {
  for (unsigned i=0;i<16;++i) { a[i]=(int8_t)((int)i-8); b[i]=(int8_t)((int)(i%5)-2); }
  uint32_t expected=(uint32_t)dot16_ref(a,b);
  for (unsigned n=0;n<32;++n) {
    int8_t bytes[16]={0};
    for (unsigned i=0;i<4;++i) bytes[i]=(int8_t)(expected>>(i*8));
    expected=(uint32_t)dot16_ref(bytes,b);
  }
  // 33条紧邻dot，后32条的源和目的均为v10，覆盖连续RAW与重命名。
  __asm__ volatile(
    "vsetivli zero,16,e8,m1,tu,mu\n\tvle8.v v8,(%0)\n\tvle8.v v9,(%1)\n\t"
    KKS_DOT_INST(10,8,9)
    ".rept 32\n\t" KKS_DOT_INST(10,10,9) ".endr\n\tvse8.v v10,(%2)"
    : : "r"(a),"r"(b),"r"(result) : "v8","v9","v10","memory");
  if (!equal128(result,expected)) { printf("DEPENDENCY FAIL\n"); return 0; }

  // dot / 标准vredsum / dot交错，检查既有VIPU运算和结果选择。
  __asm__ volatile(
    "vsetivli zero,16,e8,m1,tu,mu\n\tvle8.v v8,(%0)\n\tvle8.v v9,(%1)\n\t"
    "vmv.v.i v12,0\n\tvmv.v.i v13,0\n\t"
    KKS_DOT_INST(10,8,9)
    "vredsum.vs v12,v8,v13\n\t"
    KKS_DOT_INST(11,8,9)
    "vse8.v v10,(%2)\n\tvse8.v v12,(%3)\n\tvse8.v v11,(%4)"
    : : "r"(a),"r"(b),"r"(mixed[0]),"r"(mixed[1]),"r"(mixed[2])
    : "v8","v9","v10","v11","v12","v13","memory");
  int sum=0; for(unsigned i=0;i<16;++i) sum+=a[i];
  expected=(uint32_t)dot16_ref(a,b);
  if (!equal128(mixed[0],expected) || !equal128(mixed[1],(uint8_t)sum) || !equal128(mixed[2],expected)) {
    printf("INTERLEAVE FAIL\n"); return 0;
  }

  // load决定的分支跳过masked非法编码，随后一条正常dot仍应完成。
  __asm__ volatile(
    "vsetivli zero,16,e8,m1,tu,mu\n\tvle8.v v8,(%2)\n\tvle8.v v9,(%3)\n\t"
    "lw t0,0(%1)\n\tbeqz t0,1f\n\t"
    ".word " KKS_STRING(KKS_DOT_WORD(10,8,9,0)) "\n\t"
    "1:\n\t" KKS_DOT_INST(10,8,9) "vse8.v v10,(%0)"
    : : "r"(result),"r"(&branch_zero),"r"(a),"r"(b) : "t0","v8","v9","v10","memory");
  if (!equal128(result,expected)) { printf("BRANCH FAIL\n"); return 0; }
  printf("PIPELINE PASS dependent_dots=33 interleave=PASS branch_skip=PASS\n");
  return 1;
}

int main(void) {
  kks_enable_vector();
  for (unsigned n=0;n<8;++n) {
    for (unsigned i=0;i<16;++i) { a[i]=(int8_t)(1+(i*7+n*11)%127); b[i]=(int8_t)(1+(i*13+n*3)%127); }
    if(!run_case(0)) return 1;
  }
  printf("POSITIVE PASS vectors=%u full128_checks=%u\n",vectors[0],checks[0]);
  for (unsigned n=0;n<8;++n) {
    for (unsigned i=0;i<16;++i) {
      a[i]=(int8_t)(-1-(i*9+n*7)%127);
      b[i]=(int8_t)((n&1)?-1-(int)(i*5+n)%127:1+(int)(i*5+n)%127);
    }
    if(!run_case(1)) return 1;
  }
  printf("NEGATIVE PASS vectors=%u full128_checks=%u\n",vectors[1],checks[1]);
  const int extremes[5][2]={{0,0},{127,127},{-128,-128},{-128,127},{127,-128}};
  for(unsigned n=0;n<5;++n) { fill(extremes[n][0],extremes[n][1]); if(!run_case(2))return 1; }
  for(unsigned lane=0;lane<16;++lane) for(unsigned n=1;n<5;++n) {
    fill(0,0);a[lane]=(int8_t)extremes[n][0];b[lane]=(int8_t)extremes[n][1];
    if(!run_case(2))return 1;
  }
  for(unsigned part=0;part<2;++part) {
    fill(0,0);
    for(unsigned i=part*8;i<part*8+8;++i) { a[i]=-128;b[i]=127; }
    if(!run_case(2))return 1;
  }
  for(unsigned i=0;i<16;++i) { a[i]=(i&1)?127:-127;b[i]=127; }
  if(!run_case(2))return 1;
  printf("BOUNDARY PASS vectors=%u full128_checks=%u max=262144 min=-260096\n",vectors[2],checks[2]);
  for(unsigned n=0;n<128;++n) {
    for(unsigned i=0;i<16;++i) { a[i]=(int8_t)next_random();b[i]=(int8_t)next_random(); }
    if(!run_case(3))return 1;
  }
  printf("RANDOM PASS vectors=%u full128_checks=%u\n",vectors[3],checks[3]);
  if(csr_seen!=255 || !dependency_and_interleave())return 1;
  unsigned total=0;for(unsigned i=0;i<4;++i)total+=checks[i];
  printf("VDOT PASS vectors=216 aliases=5 full128_checks=%u vcsr_states=8\n",total);
  return 0;
}
