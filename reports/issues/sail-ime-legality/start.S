// SPDX-License-Identifier: Apache-2.0
// Machine-mode entry: set sp and mtvec, enable the vector unit, call main, report the exit code over HTIF.
// The trap handler stores mcause in trap_cause and resumes at the next instruction.
  .section .text.init
  .globl _start
_start:
  la    sp, __stack_top
  la    t0, trap_handler
  csrw  mtvec, t0
  li    t0, 0x2200         // mstatus.VS = Initial, mstatus.FS = Initial
  csrs  mstatus, t0
  call  main
  slli  a0, a0, 1
  ori   a0, a0, 1
  la    t0, tohost
1:sd    a0, 0(t0)
  j     1b

  .p2align 2
trap_handler:
  csrw  mscratch, t0
  csrr  t0, mcause
  sd    t0, trap_cause, t1
  csrr  t0, mepc
  addi  t0, t0, 4          // every instruction under test is 32 bits
  csrw  mepc, t0
  csrr  t0, mscratch
  mret

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
