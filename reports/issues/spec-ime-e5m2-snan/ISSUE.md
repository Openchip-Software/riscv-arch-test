<!-- SPDX-License-Identifier: Apache-2.0 -->

<!-- Target: riscv/integrated-matrix-extension. Not filed. Question. -->

# IME: can an OFP8 E5M2 NaN input be signaling?

## Question

The specification does not say whether an E5M2 NaN input can be a signaling NaN.
This decides whether the input raises the invalid-operation flag (NV).

## Specification text

riscv/integrated-matrix-extension @ `58810918`, `src/unpriv/integrated-matrix.adoc`, lines 1840–1847, on `fp_mul_exact`:

> Special values are handled according to the rules of the operand formats.
> For example, signaling NaN operands and invalid operations such as zero multiplied by infinity raise the invalid-operation flag and produce an internal NaN value.

The OCP 8-bit floating point specification defines the E5M2 NaN encodings but not a quiet/signaling distinction.
Under the IEEE 754 convention, an E5M2 NaN with the most significant fraction bit clear (for example 0x7D) would be signaling.

## Current behavior of the models

- The Sail reference model (Openchip-Software/sail-riscv `cleanup/ime-0.9.0` @ `0ebfc810`) treats every E5M2 NaN as quiet.
- E4M3 has a single NaN encoding per sign, so the question does not arise for E4M3.

## Request

State whether E5M2 NaN inputs follow the IEEE 754 quiet/signaling convention or are all quiet.

## Effect on tests

The riscv-arch-test E5M2 edge testcase for 0x7D sets `fflags.NV` before the instruction.
It therefore passes under either reading.
Until the specification decides, tests cannot check NV for E5M2 NaN inputs.
