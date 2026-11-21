<!-- SPDX-License-Identifier: Apache-2.0 -->

<!-- Target: riscv/riscv-unified-db. Not filed. -->

# `current_translation_mode` returns `Reserved` for HS and U mode when `misa.H` is 1

## Summary

`current_translation_mode` in `spec/std/isa/isa/globals.isa` never reads `satp` when the H extension is present.
In HS mode and U mode it returns `SatpMode::Reserved`, so every translated access from those modes faults.

Checked at riscv/riscv-unified-db `main` @ `5d1ded1f` (2026-11-19).

## Code

`spec/std/isa/isa/globals.isa`, function `current_translation_mode`, from line 1420:

```idl
if (CSR[misa].H == 1'b1) {
  if (effective_mode == PrivilegeMode::VS || effective_mode == PrivilegeMode::VU) {
    Bits<4> mode_val = CSR[vsatp].MODE;
    ...
  } else {
    return SatpMode::Reserved;
  }
} else if (CSR[misa].S == 1'b1) {
  # if we reach here, then the effective mode is S or U
  ...
  Bits<4> mode_val = CSR[satp].MODE;
```

When `misa.H` is 1, the outer `if` is taken for S and U mode too.
The inner `else` then returns `Reserved`.
The `satp` branch is reachable only when `misa.H` is 0.

## Observed behavior

A C++ ISS built by `cpp_hart_gen` from a configuration with H and S runs the riscv-arch-test boot code.
After the `mret` to S mode, the first instruction fetch raises a page fault, and the hart loops on page faults.
`satp.MODE` is Bare at that point.

## Expected behavior

In HS mode and U mode (V=0), the first-stage translation mode comes from `satp`, whether or not H is implemented.

## Suggested fix

Take the `vsatp` branch only for VS and VU mode:

```idl
if ((CSR[misa].H == 1'b1) &&
    (effective_mode == PrivilegeMode::VS || effective_mode == PrivilegeMode::VU)) {
```

With this change, the ISS runs the riscv-arch-test boot code to the test body.
The inner `else return SatpMode::Reserved;` becomes unreachable and can be removed.
