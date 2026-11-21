<!-- SPDX-License-Identifier: Apache-2.0 -->

<!-- Target: riscv/integrated-matrix-extension. Not filed. Clarification. -->

# IME: BF16-accumulator types use the Zvfbfa `altfmt` field but do not depend on Zvfbfa

## Summary

The BF16-accumulator type extensions select the BF16 C format with `vtype.altfmt`, a field that Zvfbfa defines.
Their only listed dependency is Zve32f.
The specification does not say whether `altfmt` is writable when Zvfbfa is not implemented.
Implementations disagree.

## Specification text

riscv/integrated-matrix-extension @ `58810918`, `src/unpriv/integrated-matrix.adoc`:

- Line 838, the type-extension table: `Zvvbf16mm` depends on `Zve32f`.
- Line 1090: "The Zvvm Integrated Matrix floating-point extensions use the _altfmt_ field (as defined by Zvfbfa) to select the floating-point format of the elements in the output accumulator matrix C, in conjunction with `vsew`."
- Lines 855–861: `altfmt` "resides in the low part of `vtype` at the bit position assigned by Zvfbfa".

## Current behavior of the models

- The Sail reference model (Openchip-Software/sail-riscv `cleanup/ime-0.9.0` @ `0ebfc810`) writes `vtype[8]` whenever IME is enabled.
- The SDK QEMU (Openchip-Software/riscv-ime-qemu `vrull/ime-wip` @ `d856b96`) treats `vtype[8]` as reserved unless Zvfbfa is enabled.
  `vsetvl` then sets `vill`.
- riscv-unified-db lists Zve32f as the only dependency, like the specification.

## Request

State one of:

1. An implementation of a BF16-accumulator type makes `vtype.altfmt` writable, with or without Zvfbfa.
   The specification then also defines the field for those implementations.
2. The BF16-accumulator types depend on Zvfbfa.
