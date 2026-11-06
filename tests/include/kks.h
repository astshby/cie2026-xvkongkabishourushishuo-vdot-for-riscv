#ifndef KKS_TEST_SUPPORT_H
#define KKS_TEST_SUPPORT_H
#include <stdint.h>
#include <klib.h>

/* 裸机程序显式开启向量状态。C 编译关闭自动向量化，避免开启前使用 RVV。 */
static inline void kks_enable_vector(void) {
  const uintptr_t vs_dirty = 3u << 9;
  __asm__ volatile("csrs mstatus, %0\n\tcsrwi vstart, 0" : : "r"(vs_dirty) : "memory");
}

static inline uint64_t kks_cycle(void) {
  uint64_t result;
  __asm__ volatile("rdcycle %0" : "=r"(result) : : "memory");
  return result;
}
#endif
