#ifndef KKS_DOT16_HARDWARE_H
#define KKS_DOT16_HARDWARE_H
#include <stdint.h>

/* 字段顺序：vdot.vv vd,vs2,vs1；自定义OPIVV funct6=3、funct3=0。
 * 使用表达式生成机器字，寄存器变体不再手工维护多个十六进制常量。
 * 常量不用C的u后缀，以便同一表达式交给汇编器的.word指示符。
 */
#define KKS_DOT_WORD(vd,vs2,vs1,vm) \
  ((0x03 << 26) | ((vm) << 25) | ((vs2) << 20) | ((vs1) << 15) | ((vd) << 7) | 0x57)
#define KKS_STRING_INNER(x) #x
#define KKS_STRING(x) KKS_STRING_INNER(x)
#define KKS_DOT_INST(vd,vs2,vs1) \
  ".word " KKS_STRING(KKS_DOT_WORD(vd,vs2,vs1,1)) "\n\t"
_Static_assert(KKS_DOT_WORD(10,8,9,1) == 0x0e848557, "dot16 encoding mismatch");
_Static_assert(KKS_DOT_WORD(10,8,9,0) == 0x0c848557, "masked encoding mismatch");

/* 每次存满128位，检查高96位是否被清零。目的寄存器与源重叠时，
 * 输入必须在执行前全部读取；编译器clobber明确列出所有会改变的向量寄存器。
 */
#define KKS_DOT_ASM(vd,vs2,vs1,destination) \
  __asm__ volatile( \
    "vsetivli zero,16,e8,m1,tu,mu\n\t" \
    "vle8.v v8,(%0)\n\tvle8.v v9,(%1)\n\tvmv.v.i v10,-1\n\t" \
    KKS_DOT_INST(vd,vs2,vs1) \
    "vse8.v " destination ",(%2)" \
    : : "r"(a), "r"(b), "r"(out) : "v0", "v8", "v9", "v10", "memory")

static inline void dot16_hw(const int8_t a[16], const int8_t b[16], uint32_t out[4], unsigned variant) {
  switch (variant) {
    case 1: KKS_DOT_ASM(8,8,9,"v8"); break;   /* vd=vs2 */
    case 2: KKS_DOT_ASM(9,8,9,"v9"); break;   /* vd=vs1 */
    case 3: KKS_DOT_ASM(10,8,8,"v10"); break; /* 两个源相同 */
    case 4: KKS_DOT_ASM(0,8,9,"v0"); break;   /* vd=v0，vm=1 */
    default: KKS_DOT_ASM(10,8,9,"v10"); break;
  }
}
#undef KKS_DOT_ASM
#endif
