// SPDX-License-Identifier: Apache-2.0
// vmtl.v / vmts.v register-element mapping at LMUL=2.
// VLEN=256, SEW=32, lambda=1, LMUL=2, vl=16, LD=2. Elements per register (epr) = 8.
// Spec: tile element i lives at register-group element tile_reg_idx(i, 2, 1, 8) = (i % 2) * 8 + i / 2.
#include <stdint.h>

extern volatile uint64_t tohost, fromhost;

static void putch(char c) {
  tohost = (1ull << 56) | (1ull << 48) | (uint8_t)c;  // HTIF console: device 1, command 1
  while (tohost != 0) {
    if (fromhost != 0) { fromhost = 0; break; }
  }
}
static void puts_(const char *s) { while (*s) putch(*s++); }
static void putu(uint32_t v) {
  char b[11]; int n = 0;
  do { b[n++] = (char)('0' + v % 10); v /= 10; } while (v);
  while (n) putch(b[--n]);
}
static void dump(const char *name, const uint32_t *p) {
  puts_(name);
  for (int i = 0; i < 16; i++) { putch(' '); putu(p[i]); if (i == 7) puts_(" |"); }
  putch('\n');
}

// vtype for vsetvl: lambda field (bits 62:60) = 001 -> lambda = 1, vsew = e32, vlmul = m2.
#define VTYPE_E32_M2_L1 0x1000000000000011ull

static uint32_t A[16] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15};
static uint32_t regs_after_vmtl[16], mem_after_vmts[16], round_trip[16];

int main(void) {
  uint64_t vt = VTYPE_E32_M2_L1, avl = 16, ld = 2, vl;
  for (int i = 0; i < 16; i++) regs_after_vmtl[i] = mem_after_vmts[i] = round_trip[i] = 0xffffffffu;

  // 1. vmtl.v at LMUL=2, then dump v8,v9 in register order with vse32.v.
  __asm__ volatile(
      "vsetvl   %0, %1, %2\n"
      "vmtl.v   v8, (%3), %4\n"
      "vsetivli zero, 16, e32, m2, ta, ma\n"
      "vse32.v  v8, (%5)\n"
      : "=&r"(vl) : "r"(avl), "r"(vt), "r"(A), "r"(ld), "r"(regs_after_vmtl) : "memory");

  // 2. v16,v17 = 0..15 in register order (vid.v), then vmts.v at LMUL=2.
  __asm__ volatile(
      "vsetivli zero, 16, e32, m2, ta, ma\n"
      "vid.v    v16\n"
      "vsetvl   %0, %1, %2\n"
      "vmts.v   v16, (%3), %4\n"
      : "=&r"(vl) : "r"(avl), "r"(vt), "r"(mem_after_vmts), "r"(ld) : "memory");

  // 3. vmtl.v then vmts.v with the same geometry: the round trip hides the bug.
  __asm__ volatile(
      "vsetvl   %0, %1, %2\n"
      "vmtl.v   v24, (%3), %4\n"
      "vmts.v   v24, (%5), %4\n"
      : "=&r"(vl) : "r"(avl), "r"(vt), "r"(A), "r"(ld), "r"(round_trip) : "memory");

  puts_("config: VLEN=256 SEW=32 LMUL=2 lambda=1 vl=");
  putu((uint32_t)vl);
  puts_(" LD=2\n");
  dump("1 vmtl.v A=0..15; vse32.v v8,v9:", regs_after_vmtl);
  dump("2 vid.v v16,v17; vmts.v -> mem: ", mem_after_vmts);
  dump("3 vmtl.v + vmts.v round trip:   ", round_trip);
  return 0;
}
