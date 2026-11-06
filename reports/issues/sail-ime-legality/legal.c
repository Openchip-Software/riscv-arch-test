// SPDX-License-Identifier: Apache-2.0
// Legality probe for vmmacc.vv with EMUL_C = 16 and for tile loads and stores with VL not a multiple of
// lambda*LMUL. VLEN = 256. Each case prints the mcause of the trap it raised, or "none".
// The specification requires: no trap for EMUL_C = 16, and an illegal-instruction trap (mcause 2) for
// every tile load or store with VL not a multiple of lambda*LMUL.
#include <stdint.h>

extern volatile uint64_t tohost, fromhost;
volatile uint64_t trap_cause;

static void putch(char c) {
  tohost = (1ull << 56) | (1ull << 48) | (uint8_t)c;
  while (tohost != 0) {
    if (fromhost != 0) { fromhost = 0; break; }
  }
}
static void puts_(const char *s) { while (*s) putch(*s++); }

// vtype for RV64: lambda field in bits 62:60 (log2(lambda) + 1), vsew in bits 5:3, vlmul in bits 2:0.
#define VTYPE(lambda_field, vsew, vlmul) (((uint64_t)(lambda_field) << 60) | ((vsew) << 3) | (vlmul))
#define E16 1
#define E32 2
#define M1 0
#define M2 1

static uint32_t mem[1024];

static void report(const char *name, const char *expected) {
  puts_(name);
  puts_(": expected ");
  puts_(expected);
  puts_(", got ");
  uint64_t cause = trap_cause;
  if (cause == ~0ull)
    puts_("none");
  else
    putch('0' + (char)cause);
  putch('\n');
}

#define RUN(name, expected, avl, vt, insn)                                                   \
  do {                                                                                        \
    uint64_t vl;                                                                              \
    trap_cause = ~0ull;                                                                       \
    __asm__ volatile("vsetvl %0, %1, %2\n" insn : "=&r"(vl) : "r"(avl), "r"(vt), "r"(mem)    \
                     : "memory");                                                             \
    report(name, expected);                                                                   \
  } while (0)

int main(void) {
  // EMUL_C = VLEN/(SEW*lambda^2). VL = 1 is a multiple of lambda*LMUL = 1.
  RUN("vmmacc.vv SEW=32 lambda=1 EMUL_C=8 ", "none", 1, VTYPE(1, E32, M1), "vmmacc.vv v16, v0, v8");
  RUN("vmmacc.vv SEW=16 lambda=1 EMUL_C=16", "none", 1, VTYPE(1, E16, M1), "vmmacc.vv v16, v0, v8");

  // SEW = 32, lambda = 2, LMUL = 2: lambda*LMUL = 4. VL = 4 is a multiple, VL = 1 is not.
  RUN("vmtl.v  VL=4", "none", 4, VTYPE(2, E32, M2), "vmtl.v v8, (%3), zero");
  RUN("vmtl.v  VL=1", "2", 1, VTYPE(2, E32, M2), "vmtl.v v8, (%3), zero");
  RUN("vmts.v  VL=1", "2", 1, VTYPE(2, E32, M2), "vmts.v v8, (%3), zero");
  RUN("vmttl.v VL=1", "2", 1, VTYPE(2, E32, M2), "vmttl.v v8, (%3), zero");
  RUN("vmtts.v VL=1", "2", 1, VTYPE(2, E32, M2), "vmtts.v v8, (%3), zero");
  return 0;
}
