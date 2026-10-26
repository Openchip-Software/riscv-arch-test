// SPDX-License-Identifier: Apache-2.0
// Machine-mode entry: set sp, enable the vector unit, call main, report the exit code over HTIF.
  .section .text.init
  .globl _start
_start:
  la    sp, __stack_top
  li    t0, 0x200          // mstatus.VS = Initial
  csrs  mstatus, t0
  call  main
  slli  a0, a0, 1
  ori   a0, a0, 1
  la    t0, tohost
1:sd    a0, 0(t0)
  j     1b

  .section .tohost, "aw", @progbits
  .p2align 6
  .globl tohost
  .type tohost, @object
  .size tohost, 8
tohost:   .dword 0
  .p2align 6
  .globl fromhost
  .type fromhost, @object
  .size fromhost, 8
fromhost: .dword 0
