// SPDX-License-Identifier: Apache-2.0
// FP accumulation probe for vfmmacc.vv (W=1), vfwmmacc.vv (W=2) and vfqmmacc.vv (W=4).
// VLEN=256, lambda=1, LMUL=1, vl=1: C[i,0] is element i of vd, A[i,k] is element i of vs1,
// B[k,0] is element 0 of vs2. Only C[0,0] carries a test value; the other rows multiply by zero.
// For W>1, element 0 of vs1 and vs2 holds the W packed inputs of one sub-dot-product.
#include <stdint.h>

extern volatile uint64_t tohost, fromhost;

static void putch(char c) {
  tohost = (1ull << 56) | (1ull << 48) | (uint8_t)c;
  while (tohost != 0) {
    if (fromhost != 0) { fromhost = 0; break; }
  }
}
static void puts_(const char *s) { while (*s) putch(*s++); }
static void puthex(uint64_t v, int digits) {
  puts_("0x");
  for (int i = digits - 1; i >= 0; i--) putch("0123456789abcdef"[(v >> (4 * i)) & 0xf]);
}

#define VTYPE_E32_M1_L1 0x1000000000000010ull  // lambda field = 001, vsew = e32, vlmul = m1
#define VTYPE_E64_M1_L1 0x1000000000000018ull  // lambda field = 001, vsew = e64, vlmul = m1

static uint32_t a[8], b[8], c[8];
static uint64_t a64[4], b64[4], c64[4];

static void report(const char *name, uint64_t value, int digits) {
  uint64_t flags;
  __asm__ volatile("csrr %0, fflags" : "=r"(flags));
  puts_(name); puts_(" C[0,0]="); puthex(value, digits); puts_(" fflags="); puthex(flags, 8); putch('\n');
}

static void run(const char *name, int widen, unsigned frm) {
  uint64_t vt = VTYPE_E32_M1_L1, avl = 1, vl;
  __asm__ volatile("csrw frm, %0\n csrw fflags, zero" : : "r"(frm));
  if (widen)
    __asm__ volatile(
        "vsetivli zero, 8, e32, m1, ta, ma\n vle32.v v1, (%1)\n vle32.v v2, (%2)\n vle32.v v8, (%3)\n"
        "vsetvl %0, %4, %5\n vfwmmacc.vv v8, v1, v2\n"
        "vsetivli zero, 8, e32, m1, ta, ma\n vse32.v v8, (%3)\n"
        : "=&r"(vl) : "r"(a), "r"(b), "r"(c), "r"(avl), "r"(vt) : "memory");
  else
    __asm__ volatile(
        "vsetivli zero, 8, e32, m1, ta, ma\n vle32.v v1, (%1)\n vle32.v v2, (%2)\n vle32.v v8, (%3)\n"
        "vsetvl %0, %4, %5\n vfmmacc.vv v8, v1, v2\n"
        "vsetivli zero, 8, e32, m1, ta, ma\n vse32.v v8, (%3)\n"
        : "=&r"(vl) : "r"(a), "r"(b), "r"(c), "r"(avl), "r"(vt) : "memory");
  report(name, c[0], 8);
}

// SEW=64 accumulator, lambda=1: EMUL_C = 4, so C is v8-v11. Element i of v8 is C[i,0].
static void run64(const char *name, int quad) {
  uint64_t vt = VTYPE_E64_M1_L1, avl = 1, vl;
  __asm__ volatile("csrw frm, zero\n csrw fflags, zero");
  if (quad)
    // vfqwmmacc.vv is the SDK GCC name of vfqmmacc.vv (W=4).
    __asm__ volatile(
        "vsetivli zero, 4, e64, m1, ta, ma\n vle64.v v1, (%1)\n vle64.v v2, (%2)\n vle64.v v8, (%3)\n"
        "vsetvl %0, %4, %5\n vfqwmmacc.vv v8, v1, v2\n"
        "vsetivli zero, 4, e64, m1, ta, ma\n vse64.v v8, (%3)\n"
        : "=&r"(vl) : "r"(a64), "r"(b64), "r"(c64), "r"(avl), "r"(vt) : "memory");
  else
    __asm__ volatile(
        "vsetivli zero, 4, e64, m1, ta, ma\n vle64.v v1, (%1)\n vle64.v v2, (%2)\n vle64.v v8, (%3)\n"
        "vsetvl %0, %4, %5\n vfwmmacc.vv v8, v1, v2\n"
        "vsetivli zero, 4, e64, m1, ta, ma\n vse64.v v8, (%3)\n"
        : "=&r"(vl) : "r"(a64), "r"(b64), "r"(c64), "r"(avl), "r"(vt) : "memory");
  report(name, c64[0], 16);
}

#ifdef MIXED
// W=1 mixed f16 x bf16 -> f16 (altfmt_B=1), lambda=2, SEW=16, vl=2: A[0,0..1] = elements 0..1 of v1,
// B[0..1,0] = elements 0..1 of v2, C[0,0] = element 0 of v8.
// a = 1417 * 2^-10 (f16 0x3d89), b = 185 * 2^-19 (bf16 0x39b9): a*b = 2^-11 + 2^-29. c = 1.0 (f16 0x3c00).
// One rounding to f16 (RNE): 0x3c01. Rounding to f32 first, then to f16: 1 + 2^-11 ties to 0x3c00.
#define VTYPE_E16_M1_L2_ALTB 0x2200000000000008ull
static uint16_t a16[16], b16[16], c16[64];
static void run_mixed(void) {
  uint64_t vt = VTYPE_E16_M1_L2_ALTB, avl = 2, vl;
  a16[0] = 0x3d89; b16[0] = 0x39b9; c16[0] = 0x3c00;
  __asm__ volatile("csrw frm, zero\n csrw fflags, zero");
  __asm__ volatile(
      "vsetvli zero, %4, e16, m4, ta, ma\n vle16.v v8, (%3)\n"
      "vsetivli zero, 16, e16, m1, ta, ma\n vle16.v v1, (%1)\n vle16.v v2, (%2)\n"
      "vsetvl %0, %5, %6\n vfmmacc.vv v8, v1, v2\n"
      "vsetvli zero, %4, e16, m4, ta, ma\n vse16.v v8, (%3)\n"
      : "=&r"(vl) : "r"(a16), "r"(b16), "r"(c16), "r"(64ul), "r"(avl), "r"(vt) : "memory");
  report("W1 f16xbf16>f16 rne", c16[0], 4);
}
#endif

int main(void) {
  // W=1 f32: a = b = 1 + 2^-12, c = -(1 + 2^-11). Exact a*b + c = 2^-24.
  // Fused (one rounding): 0x33800000, no NX. Product rounded to f32 first (RNE): +0, NX.
  for (int i = 0; i < 8; i++) a[i] = b[i] = c[i] = 0;
  a[0] = 0x3f800800; b[0] = 0x3f800800; c[0] = 0xbf801000;
  run("W1 f32 rne", 0, 0);
  a[0] = 0x3f800800; b[0] = 0x3f800800; c[0] = 0xbf801000;
  run("W1 f32 rup", 0, 3);
  // W=2 f16->f32: A[0,0..1] = (2^-12, 2^-12), B[0..1,0] = (2^-12, 2^-12), c = 1.0.
  // Spec with psm=0, any G, any rnd: S = 2^-23 exact, round(1 + 2^-23) = 0x3f800001, no NX.
  // Per-product accumulation into C with RNE: 1 + 2^-24 ties to 1.0 twice: 0x3f800000, NX.
  for (int i = 0; i < 8; i++) a[i] = b[i] = c[i] = 0;
  a[0] = 0x0c000c00; b[0] = 0x0c000c00; c[0] = 0x3f800000;
  run("W2 f16>f32 rne", 1, 0);
  // W=2 f32->f64: A[0,0..1] = (2^-26, 2^-26), B[0..1,0] = (2^-27, 2^-27), c = 1.0.
  // Spec: S = 2^-52 exact, 1 + 2^-52 = 0x3ff0000000000001, no NX.
  // Per-product accumulation with RNE: 1 + 2^-53 ties to 1.0 twice: 0x3ff0000000000000, NX.
  for (int i = 0; i < 4; i++) a64[i] = b64[i] = c64[i] = 0;
  a64[0] = 0x3280000032800000ull; b64[0] = 0x3200000032000000ull; c64[0] = 0x3ff0000000000000ull;
  run64("W2 f32>f64 rne", 0);
  // W=4 f16->f64: A[0,0..3] = B[0..3,0] = (0.5, 0.5, 0.5, 0.5), c = 2^52.
  // Spec: S = 1.0 exact, 2^52 + 1 = 0x4330000000000001, no NX.
  // Per-product accumulation with RNE: 2^52 + 0.25 rounds to 2^52 four times: 0x4330000000000000, NX.
  for (int i = 0; i < 4; i++) a64[i] = b64[i] = c64[i] = 0;
  a64[0] = 0x3800380038003800ull; b64[0] = 0x3800380038003800ull; c64[0] = 0x4330000000000000ull;
  run64("W4 f16>f64 rne", 1);
#ifdef MIXED
  run_mixed();
#endif
  return 0;
}
