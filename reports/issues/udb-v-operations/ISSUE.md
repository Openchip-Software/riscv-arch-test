<!-- SPDX-License-Identifier: Apache-2.0 -->

<!-- Target: riscv/riscv-unified-db. Not filed. Feature request, lower priority than the bugs. -->

# Most V instructions have no `operation()`, so the ISS cannot run vector test suites

## Summary

Only 8 of the 627 instruction files in `spec/std/isa/inst/V/` have a non-empty `operation()`:
`vadd.vv`, `vle8.v`, `vmv.v.i`, `vmv.x.s`, `vse8.v`, `vsetivli`, `vsetvl` and `vsetvli`.
In a C++ ISS built by `cpp_hart_gen`, every other V instruction completes without changing any state.

Checked at riscv/riscv-unified-db `main` @ `5d1ded1f` (2026-11-19).

## Effect

riscv-arch-test checks each vector result with `vid.v`, slides, compares, mask instructions and `vfirst.m`.
None of these does anything in the ISS, so every vector test fails at its first check, even when the instruction under test is correct.
A bare-metal probe program compared against Sail shows that `vid.v`, the slides, `vmv.v.v`, `vmv.v.x`, the compares, the mask instructions, `vcpop.m` and `vfirst.m` leave their destinations unchanged.

## Request

Add operations for the V instructions, starting with those that test frameworks use for checking:
`vid.v`, `vmv.v.v`, `vmv.v.x`, the slides, the integer compares, the mask-logical instructions, `vfirst.m` and `vcpop.m`.
They depend on the register-group fix in the separate LMUL > 1 issue.
