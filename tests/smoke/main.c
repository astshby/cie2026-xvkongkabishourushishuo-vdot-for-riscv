#include "kks.h"
#include "dot16_ref.h"

static const int8_t a[16] __attribute__((aligned(16))) = {
  0,0,0,0,0,0,0,0,-128,127,-1,2,3,-4,5,-6
};
static const int8_t b[16] __attribute__((aligned(16))) = {
  0,0,0,0,0,0,0,0,127,-128,2,-3,4,-5,6,-7
};
typedef struct { uint64_t compute,total; } KksTimes;
extern KksTimes kks_dot_kernel(const int8_t *,const int8_t *,uint32_t *,unsigned);
extern KksTimes kks_baseline_kernel(const int8_t *,const int8_t *,uint32_t *,unsigned);
static uint32_t out_dot[4] __attribute__((aligned(16)));
static uint32_t out_base[4] __attribute__((aligned(16)));

int main(void) {
  kks_enable_vector();
  // 同一程序、同一输入，先执行标准RVV组合，再执行自定义dot。
  // 低8对为零，高8对非零，区分只处理8个元素的实现。
  const KksTimes base=kks_baseline_kernel(a,b,out_base,1);
  const KksTimes dot=kks_dot_kernel(a,b,out_dot,1);
  const uint32_t expected = (uint32_t)dot16_ref(a,b);
  if (out_dot[0]!=expected || out_dot[1] || out_dot[2] || out_dot[3] ||
      out_base[0]!=expected || out_base[1] || out_base[2] || out_base[3]) {
    printf("WAVE FAIL dot=%08x baseline=%08x expected=%08x\n",out_dot[0],out_base[0],expected);
    return 1;
  }
  printf("WAVE PASS upper8_only signed_result=%d high96=zero baseline=%lu dot=%lu\n",
         (int32_t)out_dot[0],base.compute,dot.compute);
  return 0;
}
