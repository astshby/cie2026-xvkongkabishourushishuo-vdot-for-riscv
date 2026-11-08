#include "kks.h"
#include "dot16_ref.h"

typedef struct { uint64_t compute, total; } KksTimes;
extern KksTimes kks_dot_kernel(const int8_t *, const int8_t *, uint32_t *, unsigned);
extern KksTimes kks_baseline_kernel(const int8_t *, const int8_t *, uint32_t *, unsigned);
static const int8_t lhs[16] __attribute__((aligned(16))) = {
  -128, 127, -1, 2, 3, -4, 5, -6, 7, -8, 9, -10, 11, -12, 13, -14
};
static const int8_t rhs[16] __attribute__((aligned(16))) = {
  127, -128, 2, -3, 4, -5, 6, -7, 8, -9, 10, -11, 12, -13, 14, -15
};
static uint32_t out_dot[4] __attribute__((aligned(16)));
static uint32_t out_base[4] __attribute__((aligned(16)));
static int8_t edge_a[16] __attribute__((aligned(16)));
static int8_t edge_b[16] __attribute__((aligned(16)));
typedef struct { unsigned count, sample; KksTimes b,d; } Sample;
static Sample samples[15];

static uint32_t chain_reference(unsigned count) {
  int8_t current[16];
  for (int i = 0; i < 16; ++i) current[i] = lhs[i];
  uint32_t sum = 0;
  for (unsigned n = 0; n < count; ++n) {
    sum = (uint32_t)dot16_ref(current, rhs);
    for (int lane = 0; lane < 16; ++lane)
      current[lane] = lane < 4 ? (int8_t)(sum >> (lane*8)) : 0;
  }
  return sum;
}

static int valid(const uint32_t x[4], uint32_t expected) {
  return x[0] == expected && x[1] == 0 && x[2] == 0 && x[3] == 0;
}

int main(void) {
  kks_enable_vector();
  // 先验证标准RVV基线在最大、最小与零输入上也保留全部128位语义。
  const int extremes[5][2]={{0,0},{127,127},{-128,-128},{-128,127},{127,-128}};
  for(unsigned n=0;n<5;++n) {
    for(unsigned i=0;i<16;++i) { edge_a[i]=(int8_t)extremes[n][0];edge_b[i]=(int8_t)extremes[n][1]; }
    const uint32_t expected=(uint32_t)dot16_ref(edge_a,edge_b);
    kks_baseline_kernel(edge_a,edge_b,out_base,1);
    kks_dot_kernel(edge_a,edge_b,out_dot,1);
    if(!valid(out_base,expected)||!valid(out_dot,expected)) {
      printf("BASELINE_EQ FAIL case=%u\n",n);return 1;
    }
  }
  const unsigned counts[] = {1, 8, 32};
  for (unsigned k = 0; k < 3; ++k) {
    const unsigned count = counts[k];
    const uint32_t expected = chain_reference(count);
    /* 每个长度先暖机，两种执行顺序交替，保留全部原始样本。 */
    kks_baseline_kernel(lhs, rhs, out_base, count);
    kks_dot_kernel(lhs, rhs, out_dot, count);
    if(!valid(out_dot,expected)||!valid(out_base,expected)) {
      printf("WARMUP FAIL count=%u\n",count);return 1;
    }
    for (unsigned sample = 0; sample < 5; ++sample) {
      KksTimes b, d;
      if (sample & 1) {
        d = kks_dot_kernel(lhs, rhs, out_dot, count);
        b = kks_baseline_kernel(lhs, rhs, out_base, count);
      } else {
        b = kks_baseline_kernel(lhs, rhs, out_base, count);
        d = kks_dot_kernel(lhs, rhs, out_dot, count);
      }
      if (!valid(out_dot, expected) || !valid(out_base, expected)) {
        printf("BENCH FAIL count=%u expected=%08x dot=%08x baseline=%08x\n",
               count, expected, out_dot[0], out_base[0]);
        return 1;
      }
      samples[k*5+sample]=(Sample){count,sample,b,d};
    }
  }
  // 所有计时结束后统一打印，避免每次UART输出改变下一对计时的运行背景。
  printf("BASELINE_EQ PASS cases=5 full128=checked signed_extremes=checked\n");
  for(unsigned i=0;i<15;++i) {
    const Sample *s=&samples[i];
    printf("KKS_PERF count=%u sample=%u baseline=%lu dot=%lu baseline_total=%lu dot_total=%lu\n",
           s->count,s->sample,s->b.compute,s->d.compute,s->b.total,s->d.total);
  }
  printf("BENCH PASS signed_dot16=equivalent samples=15 results128=checked\n");
  return 0;
}
