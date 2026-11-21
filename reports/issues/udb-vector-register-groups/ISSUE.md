<!-- SPDX-License-Identifier: Apache-2.0 -->

<!-- Target: riscv/riscv-unified-db. Not filed. -->

# Vector instruction operations index `V[vd]` only, so LMUL > 1 updates one register of the group

## Summary

The V instructions that have an `operation()` treat the destination as a single register.
At LMUL > 1, elements past the first register of the group are not read or written.
The 16-, 32- and 64-bit unit-stride loads and stores have no operation at all.

Checked at riscv/riscv-unified-db `main` @ `5d1ded1f` (2026-11-19).

## Code

`spec/std/isa/inst/V/vle8.v.yaml`:

```idl
for (U32 i = CSR[vstart].VALUE; i < CSR[vl].VALUE; i++) {
  U32 start_bit_pos = i * 8;
  U32 end_bit_pos = start_bit_pos + 7;
  V[vd][end_bit_pos:start_bit_pos] = read_memory(8, virtual_address + i, $encoding)[7:0];
}
```

With LMUL = 8 and VL = VLMAX, `end_bit_pos` reaches 8·VLEN − 1, but `V[vd]` is VLEN bits wide.
The same pattern is in:

- `vse8.v`: `V[vs3][end_bit_pos:start_bit_pos]`
- `vmv.v.i`: `V[vd][end_bit_pos:start_bit_pos] = sext_imm[state.sew-1:0]`
- `vadd.vv`: `V[vd]`, `V[vs2]` and `V[vs1]`

`vle16.v`, `vle32.v`, `vle64.v`, `vse16.v`, `vse32.v` and `vse64.v` have an empty `operation()`.

## Observed behavior

A bare-metal probe runs `vsetvli t0, zero, e8, m8, ta, ma` and `vle8.v v8, (a1)`, then reads v9 at LMUL = 1.
In a C++ ISS built by `cpp_hart_gen` (VLEN 1024), v9 does not receive the loaded bytes.
Sail loads them into v9.

## Expected behavior

Element i of a register group with base register `vd` is in register `vd + i / (VLEN/SEW)`, at bit offset `(i % (VLEN/SEW))·SEW`.
The V specification requires this for every LMUL > 1.

## Suggested fix

Add IDL helpers that read and write element i of a register group, and use them in these operations.
A local diagnostic build used such helpers to implement all eight unit-stride loads and stores.
With them, the ISS and Sail agree on every vector load and store in the riscv-arch-test IME suites.
