<!-- SPDX-License-Identifier: Apache-2.0 -->

<!-- Target: Openchip-Software/riscv-ime-qemu. Not filed. -->

# IME: widening FP MACC rounds each product into C instead of forming the sub-dot-product sum first

## Summary

For W > 1, QEMU adds each product into the C element with its own `float*_muladd`, rounded with `frm`.
The specification forms the sum S of the W products of a sub-dot-product first, then updates C with `round_frm(C + S)`.
The results differ whenever one of the per-product additions is inexact.
No disclosed (G, psm, rnd) profile describes the QEMU result.

Affected: `vfwmmacc.vv`, `vfqmmacc.vv` and `vf8wmmacc.vv` for every input format, including OFP8 and OFP4.
`vfmmacc.vv` (W = 1) is not affected.

QEMU: Openchip-Software/riscv-ime-qemu `vrull/ime-wip` @ `d856b96` (OpenChip SDK of 2026-10-14).
Specification: riscv/integrated-matrix-extension @ `58810918`, section "Accumulation and rounding model" and `fp_group_sum`.

## Reproduce

Run the riscv-arch-test `Zvvfmm` suites on the `qemu-ime-rv64` configuration.
Every W > 1 file with an FP16, FP32 or FP64 C fails at its first `cp_fp_subdot` testcase.
The files with a BF16 C stop earlier, at the `altfmt` defect reported separately.
The testcase uses A = B = 1.0 and C0 = W·2^(p−1), where p is the precision of the C format, and rounds to nearest-even.
Each product alone is at most half an ULP of C0, so adding it to C0 on its own leaves C0 unchanged.
The W products sum to one ULP of C0, so the specification result is C0 + W.

## Expected behavior

C ← round_frm(C + S), with S the exact sum of the W products when psm = 0.
The Sail reference model `cleanup/ime-0.9.0` @ `0ebfc810` (`ime_fp_group_sum`) computes this, and the testcases pass on it.

## Possible second defect

QEMU may still use the A and B register layout of spec `6effbcae`, λ K elements per register.
Spec `3c1b4457` changed it to λ·W.
This defect would show for W > 1 at LMUL > 1, but the sum defect above stops each test first.
Check it again after the fix.
