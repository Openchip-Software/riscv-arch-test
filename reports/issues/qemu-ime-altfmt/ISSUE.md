<!-- SPDX-License-Identifier: Apache-2.0 -->

<!-- Target: Openchip-Software/riscv-ime-qemu. Not filed. Depends on the answer to spec-ime-altfmt-dependency. -->

# IME: `vtype.altfmt` is reserved unless Zvfbfa is enabled, so BF16-accumulator MACC cannot run with `x-zvvm=true`

## Summary

`vtype_reserved` in `target/riscv/vector_helper.c` treats `vtype[8]` (`altfmt`) as reserved unless `ext_zvfbfa` or `ext_zvfofp8min` is set.
`x-zvvm=true` sets neither.
A `vsetvl` with `altfmt` = 1 then sets `vill`, and the following `vfmmacc.vv` with a BF16 C raises an illegal-instruction exception.

QEMU: Openchip-Software/riscv-ime-qemu `vrull/ime-wip` @ `d856b96` (OpenChip SDK of 2026-10-14).

## Code

```c
if (riscv_cpu_cfg(env)->ext_zvfbfa ||
    riscv_cpu_cfg(env)->ext_zvfofp8min) {
    reserved = vtype & MAKE_64BIT_MASK(R_VTYPE_RESERVED_SHIFT, ...);
} else {
    reserved = vtype & MAKE_64BIT_MASK(R_VTYPE_ALTFMT_SHIFT, ...);
}
```

The Zvvm block that follows clears λ, `bs`, `altfmt_A` and `altfmt_B` from `reserved`, but not `altfmt`.

## Reproduce

Run the riscv-arch-test `Zvvbf16mm` and `Zvvofp*bf16mm` files on `qemu-ime-rv64`.
Each one fails at its first testcase.
With `x-zvfbfa=true` added to `-cpu`, the `Zvvbf16mm` file passes.

## Expected behavior

The specification (riscv/integrated-matrix-extension @ `58810918`) lists Zve32f as the only dependency of `Zvvbf16mm`.
It uses the Zvfbfa `altfmt` field to select a BF16 C.
When a BF16-accumulator type extension is enabled, `vtype[8]` must be writable.
The Sail reference model writes the bit whenever IME is enabled.

## Suggested fix

Clear `altfmt` from `reserved` when any IME type extension with a BF16 C is enabled.
