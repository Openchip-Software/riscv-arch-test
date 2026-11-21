<!-- SPDX-License-Identifier: Apache-2.0 -->

<!-- Target: Openchip-Software/riscv-ime-qemu. Not filed. Found by code reading; not run. -->

# IME: microscaled MACC rounds the inner product and the scale before it updates C

## Summary

The microscaled helpers in `target/riscv/insn_trans/trans_rvzvvmm.c.inc` round in several places where the specification rounds once.

`GEN_ZVVMM_VFMMACC_VV_MX` (FP inputs), from its comment:

```text
ip = 0; for k: ip = OP(a[k], b[k], ip, fs)   (inner product in type TD)
scale_td = SCALE_TO_TD(scale_A_f32 × scale_B_f32)
*c_ptr = FMA_TD(scale_td, ip, *c_ptr, 0, fs)
```

`GEN_ZVVMM_VFIMMACC_VV` (integer inputs):

```text
ip = 0; for k: ip += a[k] * b[k]   (integer)
ip_f32 = INT_TO_F32(ip, fs)
ip_td  = SCALE_TO_TD(ip_f32, fs)
scale_td = SCALE_TO_TD(e8m0_A × e8m0_B, fs)
*c = FMA_TD(scale_td, ip_td, *c, 0, fs)
```

QEMU: Openchip-Software/riscv-ime-qemu `vrull/ime-wip` @ `d856b96`.
Specification: riscv/integrated-matrix-extension @ `58810918` (block scales, including `324c62b7`).

## Differences from the specification

1. FP inputs: each product is added to `ip` in the C format with its own rounding.
   The specification sums each block exactly.
2. Integer inputs: the exact integer sum is converted to FP32 and then to the C format.
   A sum wider than 24 bits loses bits before the scale is applied.
3. The combined scale is formed as an FP32 product and converted to the C format.
   The specification applies the combined E8M0 exponent exactly.
   For combined exponents outside the FP32 or C-format range, the scale over- or underflows before it is applied.

## Reproduce

Not run: the riscv-arch-test `qemu-ime-rv64` configuration does not enable `x-zvvfmmmx`.
The `Zvvx*` files in riscv-arch-test, with `cp_scale` and `cp_fp_subdot`, are expected to show these differences.
They pass on the Sail reference model.

## Expected behavior

The scaled partial sum is formed exactly and rounded once with `frm` into C.
