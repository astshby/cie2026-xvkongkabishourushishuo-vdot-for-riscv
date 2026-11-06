#include "kks.h"

static const int8_t lhs[16] __attribute__((aligned(16))) = {
  1, 2, 3, 4, -1, -2, -3, -4, 127, -128, 0, 42, 8, 9, 10, 11
};
static const int8_t rhs[16] __attribute__((aligned(16))) = {
  10, 20, 30, 40, 1, 2, 3, 4, 1, -1, 0, -42, 1, 2, 3, 4
};
static uint8_t result[16] __attribute__((aligned(16)));

int main(void) {
  kks_enable_vector();
  __asm__ volatile(
    "vsetivli zero, 16, e8, m1, tu, mu\n\t"
    "vle8.v v8, (%0)\n\t"
    "vle8.v v9, (%1)\n\t"
    ".global kks_vadd_begin\nkks_vadd_begin:\n\t"
    "vadd.vv v10, v8, v9\n\t"
    ".global kks_vadd_end\nkks_vadd_end:\n\t"
    "vse8.v v10, (%2)"
    : : "r"(lhs), "r"(rhs), "r"(result)
    : "v8", "v9", "v10", "memory");
  for (int i = 0; i < 16; ++i) {
    const uint8_t expected = (uint8_t)((uint8_t)lhs[i] + (uint8_t)rhs[i]);
    if (result[i] != expected) {
      printf("VADD FAIL lane=%d got=%d expected=%d\n", i, result[i], expected);
      return 1;
    }
  }
  printf("VADD PASS lanes=16, including int8 wraparound\n");
  return 0;
}
