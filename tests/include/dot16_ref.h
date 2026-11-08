#ifndef KKS_DOT16_REFERENCE_H
#define KKS_DOT16_REFERENCE_H
#include <stdint.h>

/* 与 RTL 结构独立的标量参考：先转换为 int32，确保所有乘法均带符号。 */
static inline int32_t dot16_ref(const int8_t a[16], const int8_t b[16]) {
  int32_t sum = 0;
  for (unsigned i = 0; i < 16; ++i) sum += (int32_t)a[i] * (int32_t)b[i];
  return sum;
}
#endif
