<!-- SPDX-License-Identifier: Apache-2.0 -->

<!-- Target: Openchip-Software/sail-riscv. Not filed. -->

# IME: a family flag enables every type extension, including types whose base vector extension is absent

## Summary

In `model/extensions/IME/ime_types.sail`, each FP type extension is enabled when its own flag and base vector extension are enabled, or when the family flag `Zvvfmm` is enabled.
The second term does not check the base vector extension of the type.

Checked at Openchip-Software/sail-riscv `cleanup/ime-0.9.0` @ `0ebfc810`.

## Code

```sail
function clause currentlyEnabled(Ext_Zvvfmm) =
  (hartSupports(Ext_Zvvfmm) & currentlyEnabled(Ext_Zve32f))

function clause currentlyEnabled(Ext_Zvvfp16fp64mm) =
  (hartSupports(Ext_Zvvfp16fp64mm) & currentlyEnabled(Ext_Zve64d)) |
  currentlyEnabled(Ext_Zvvfmm)
```

The same pattern is used for `Zvvbf16fp64mm`, `Zvvfp32fp64mm` and the other FP64 types.

## Effect

1. A hart with `Zvvfmm` and Zve32f but without Zve64d executes the FP64-accumulator instructions.
   The specification lists Zve64d as a dependency of those types.
2. The family flag enables every type, OFP8 included.
   In riscv-unified-db each type requires its family, and the family alone enables no type.
   A configuration generated from UDB therefore has to set every family flag to false in `sail.json` and enable each type on its own.
   riscv-arch-test does this in `config/ime/sail-ime-rv64/sail.json`.

## Expected behavior

- A type extension is never enabled without its base vector extension.
- The family flag has the meaning that UDB and the specification give it.
  If the family is only a grouping name, it should not enable any type.

## Suggested fix

Add the base vector extension check to the family term, for example
`(currentlyEnabled(Ext_Zvvfmm) & currentlyEnabled(Ext_Zve64d))`.
Decide separately whether the family flag should enable types at all, and document the decision in the configuration schema.
