# vmmacc.vv with EMUL_C = VLEN/(SEW*lambda^2) = 16 (VLEN=256, e16, m1, L1, VL=1).
# The spec permits EMUL_C in {1, 2, 4, 8, 16}, so neither vmmacc.vv may trap.
# vd = v16 is aligned to 16 registers. The trap handler records mcause in s1
# and skips the instruction.
# Exit code is a bit mask of failing cases; 0 means pass:
#    1: e32 L1, EMUL_C = 8:  vsetvl set vill
#    2: e32 L1, EMUL_C = 8:  vmmacc.vv trapped (control)
#    4: e16 L1, EMUL_C = 16: vsetvl set vill
#    8: e16 L1, EMUL_C = 16: vmmacc.vv trapped
    .section .text.init
    .globl _start
_start:
    la t0, trap; csrw mtvec, t0
    li t0, 0x200; csrs mstatus, t0     # mstatus.VS = Initial
    li s2, 0

    li t1, 0x1000000000000010          # vtype: lambda field 001 (L1), e32, m1
    vsetvl t0, x0, t1                  # VL = VLMAX = 8
    li t2, 1
    vsetvl t0, t2, t1                  # VL = 1
    csrr t3, vtype
    bgez t3, 1f; ori s2, s2, 1
1:  li s1, 0
    .word 0xe2800857                   # vmmacc.vv v16, v0, v8
    beqz s1, 1f; ori s2, s2, 2

1:  li t1, 0x1000000000000008          # vtype: lambda field 001 (L1), e16, m1
    vsetvl t0, t2, t1                  # VL = 1
    csrr t3, vtype
    bgez t3, 1f; ori s2, s2, 4
1:  li s1, 0
    .word 0xe2800857                   # vmmacc.vv v16, v0, v8
    beqz s1, 1f; ori s2, s2, 8
1:  j done

    .p2align 2
trap:
    csrr s1, mcause
    csrr t6, mepc; addi t6, t6, 4; csrw mepc, t6
    mret

done:
    slli t1, s2, 1; ori t1, t1, 1
    la t0, tohost
1:  sd t1, 0(t0)
    j 1b

    .section .tohost, "aw", @progbits
    .p2align 6
    .globl tohost
tohost: .dword 0
    .p2align 6
    .globl fromhost
fromhost: .dword 0
