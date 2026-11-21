<!-- SPDX-License-Identifier: Apache-2.0 -->

<!-- Target: Openchip-Software/riscv-ime-qemu. Not filed. -->

# IME: MACC and tile load/store instructions run in cases where the specification requires an illegal-instruction exception

## Summary

The SDK QEMU executes these instructions instead of raising an illegal-instruction exception:

| Instructions                                     | Case                                         |
| ------------------------------------------------ | -------------------------------------------- |
| `vmmacc.vv`, `vfmmacc.vv` and the widening forms | `vstart` ≠ 0                                 |
| same                                             | VL is not a multiple of λ·LMUL               |
| `vmtl.v`, `vmts.v`                               | `vtype.vill` = 1                             |
| `vmtl.v`, `vmts.v`                               | immediate λ L64 when λ = 64 is not supported |
| `vmtl.v`, `vmts.v`                               | VL is not a multiple of λ·LMUL               |
| `vmtl.v`                                         | masked load (vm = 0) with `vd` = v0          |

With the immediate λ L64, the test later crashes QEMU with an M-mode double trap.

QEMU: Openchip-Software/riscv-ime-qemu `vrull/ime-wip` @ `d856b96`, as shipped in the OpenChip SDK of 2026-10-14.
Command line: `-cpu max,vlen=256,x-zvvm=true,...`.
Specification: riscv/integrated-matrix-extension @ `58810918`.

## Reproduce

Build the riscv-arch-test `ExceptionsZvvm` suite for the `qemu-ime-rv64` configuration and run it with `-d int`.
Each listed case has its own testcase. The ELF expects an illegal-instruction trap at the instruction.
QEMU executes the instruction and continues, so the testcase fails.
The first failure is at `cp_ime_vstart`.

## Expected behavior

The specification requires an illegal-instruction exception in each listed case.
The Sail reference model raises the exception in each case.

## Note

The comment above `GEN_LDST_TILE_TRANS` in `target/riscv/insn_trans/trans_rvzvmtls.c.inc` says that these checks belong in `ldst_tile_trans`.
They are not implemented there yet.
