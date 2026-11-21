<!-- SPDX-License-Identifier: Apache-2.0 -->

<!-- Target: riscv/riscv-unified-db. Not filed. -->

# `cpp_hart_gen` ISS aborts when a program reads an undefined reset value

## Summary

The C++ ISS built by `cpp_hart_gen` tracks unknown bits.
The ISS aborts with `udb::UndefinedValueError` as soon as an instruction compares or converts a value that has unknown bits.
Three sources of unknown bits stop common boot code:

1. CSR fields whose reset value is `UNDEFINED_LEGAL`. The reset code in `csrs_impl.hxx.erb` leaves them fully undefined (`m_value = ValueType()`).
2. Registers with no reset value, such as the general-purpose registers. `hart.hxx.erb` skips them at reset.
3. CSR writes whose `sw_write` legalizes to an undefined value. One example is the `pmpaddr` write of all ones (separate issue).

Checked at riscv/riscv-unified-db `main` @ `5d1ded1f` (2026-11-19).

## Observed behavior

With a configuration that implements M, S, H and V, the riscv-arch-test boot code stops at its first `mtvec` read:

```text
PC 800bc81c csrrw x7, x7, 770
PC 800bc820 sd x6, x7(696)
PC 800bc824 csrrs x8, x0, 773
terminate called after throwing an instance of 'udb::UndefinedValueError'
  what():  Cannot convert value with unknowns to a native C++ type
```

An earlier run stopped at `sfence.vma` with `Cannot compare unknown value`.
Its conditions read CSR fields that reset to `UNDEFINED_LEGAL`.
A store of a general-purpose register that the program had not yet written also aborts.

## Expected behavior

The architecture allows software to read these values.
An ISS used as a reference model needs one defined value for each of them.
Real hardware and Sail reset them to a fixed value, usually zero.

## Suggested fix

One of these options:

- Add an ISS option that resets `UNDEFINED_LEGAL` fields and registers without a reset value to zero.
  The option should also keep the old value when a write legalizes to an undefined value.
- Let the configuration give the reset value of each such field.

A local diagnostic build applies the first option in `csrs_impl.hxx.erb` and `hart.hxx.erb`.
The riscv-arch-test boot code then runs.
