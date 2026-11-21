<!-- SPDX-License-Identifier: Apache-2.0 -->

<!-- Target: riscv/riscv-unified-db. Not filed. Add the compiler error text before filing (see the note at the end). -->

# `cpp_hart_gen` ISS fails for configurations without Smrnmi, `marchid` or `mimpid`

## Summary

`cpp_hart_gen` emits code that depends on options that the configuration does not implement:

1. Without Smrnmi, the generated hart still contains the `mnret` instruction class and writes to `mnstatus`.
   The C++ build of the ISS fails.
2. With `MARCHID_IMPLEMENTED: false` or `MIMPID_IMPLEMENTED: false`, the reset code still reads `ARCH_ID_VALUE` or `IMP_ID_VALUE`.
   Those parameters have no value, and the ISS aborts at reset:

   ```text
   terminate called after throwing an instance of 'std::bad_optional_access'
     what():  bad optional access
   ```

Checked at Openchip-Software/riscv-unified-db `ime/fp-mx` @ `f0045fec`, which merges riscv/riscv-unified-db `main` @ `176fc360`.
The files involved are not changed on the fork.

## Reproduce

1. Use an RV64 configuration with M, S, H and V that does not list Smrnmi and sets `MARCHID_IMPLEMENTED: false`.
2. Run `rake gen:cpp_hart CONFIG=<config>` and build the ISS.

## Expected behavior

The generated hart contains only the instructions and CSRs of implemented extensions.
Reset code reads a parameter only when the configuration defines it.

## Workaround

Enable Smrnmi and set `MARCHID_IMPLEMENTED: true`, `ARCH_ID_VALUE`, `MIMPID_IMPLEMENTED: true` and `IMP_ID_VALUE`.

## Note before filing

The compiler error for item 1 was not kept.
Rebuild without Smrnmi on a compute node, about 25 minutes, and paste the first error here.
