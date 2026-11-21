<!-- SPDX-License-Identifier: Apache-2.0 -->

<!-- Target: riscv/riscv-unified-db. Not filed. -->

# `cpp_hart_gen` ISS: `DenseMemory` has no bounds check, so an access outside RAM crashes the ISS

## Summary

`DenseMemory::read` and `DenseMemory::write` in `backends/cpp_hart_gen/cpp/include/udb/iss_soc_model.hpp` index `m_data[addr - m_offset]` without a bounds check.
A store to a device address outside RAM writes outside the buffer.
The ISS then crashes with a segmentation fault.

Checked at riscv/riscv-unified-db `main` @ `5d1ded1f` (2026-11-19).

## Observed behavior

The riscv-arch-test boot code writes a CLINT register. The CLINT base address is `0x02000000`.
RAM starts at `0x80000000`.
The ISS crashes with `Segmentation fault (core dumped)` at that store.

## Expected behavior

The ISS should not crash on an address outside RAM.
Either of these is acceptable:

- Raise an access-fault exception, as for an address with no PMA.
- Model a minimal device region, or read zero and ignore writes.

## Suggested fix

Check `addr` and `addr + bytes` against `m_offset` and `m_offset + m_data.size()` in both functions.
A local diagnostic build makes reads outside RAM return zero and ignores writes there.
The riscv-arch-test ELFs then run to the end.
