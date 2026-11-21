<!-- SPDX-License-Identifier: Apache-2.0 -->

<!-- Target: riscv/riscv-unified-db. Not filed. -->

# A `pmpaddr` write of all ones legalizes to `UNDEFINED_LEGAL_DETERMINISTIC`

## Summary

`pmpaddrN.layout` returns `UNDEFINED_LEGAL_DETERMINISTIC` for any written address at or above the largest implemented value.
Boot code commonly writes all ones to `pmpaddr0` to cover all of memory with one TOR or NAPOT entry.
In a C++ ISS built by `cpp_hart_gen`, that write aborts the simulation.

Checked at riscv/riscv-unified-db `main` @ `5d1ded1f` (2026-11-19).

## Code

`spec/std/isa/csr/I/pmpaddrN.layout`, `sw_write`:

```idl
} else if (csr_value.ADDR >= ((1 `<< (PHYS_ADDR_WIDTH - 2)) - 1)) {
  return UNDEFINED_LEGAL_DETERMINISTIC;
} else {
  return csr_value.ADDR;
}
```

The comparison uses `>=`, so the value with every implemented bit set is also undefined.
That value is the largest legal address.

## Observed behavior

The riscv-arch-test boot code writes all ones to `pmpaddr0`.
The ISS then aborts with `udb::UndefinedValueError`.

## Expected behavior

The privileged specification stores bits [PHYS_ADDR_WIDTH−1:2] of the address in `pmpaddr`.
The upper bits are WARL (write any values, reads legal values).
A write of all ones then reads back as all ones in the implemented bits.
Sail returns that value.

## Suggested fix

Return `csr_value.ADDR[PHYS_ADDR_WIDTH-3:0]` for values that do not fit.
A local diagnostic build makes this change and then matches Sail on the boot code.
If the undefined value is intended, a configuration parameter should select the implemented behavior.
