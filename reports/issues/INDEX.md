<!-- SPDX-License-Identifier: Apache-2.0 -->

# Bugs and issues found during the IME port to ACT4

State as of 2026-11-21. Nothing here has been filed. Each draft names its target repository on its first line.
Before filing, check that no matching issue exists, and resolve every "Note before filing" in the draft.

## Drafts ready for review

| #   | Target repository                    | Draft                            | Kind     | Summary                                                                                            |
| --- | ------------------------------------ | -------------------------------- | -------- | -------------------------------------------------------------------------------------------------- |
| 1   | riscv/riscv-unified-db               | `udb-translation-mode-with-h/`   | bug      | `current_translation_mode` returns `Reserved` for HS and U mode when `misa.H` = 1                  |
| 2   | riscv/riscv-unified-db               | `udb-vector-register-groups/`    | bug      | V operations index `V[vd]` only; LMUL > 1 updates one register; `vle16/32/64`, `vse16/32/64` empty |
| 3   | riscv/riscv-unified-db               | `udb-pmpaddr-all-ones/`          | bug      | `pmpaddr` write of all ones legalizes to `UNDEFINED_LEGAL_DETERMINISTIC`                           |
| 4   | riscv/riscv-unified-db               | `udb-iss-undefined-values/`      | bug      | ISS aborts on `UNDEFINED_LEGAL` resets, registers without reset, undefined legalized writes        |
| 5   | riscv/riscv-unified-db               | `udb-iss-memory-bounds/`         | bug      | `DenseMemory` has no bounds check; a CLINT store crashes the ISS                                   |
| 6   | riscv/riscv-unified-db               | `udb-iss-unimplemented-options/` | bug      | ISS build or reset fails without Smrnmi, `marchid` or `mimpid`; needs the compiler error           |
| 7   | riscv/riscv-unified-db               | `udb-iss-config-format/`         | bug      | ISS rejects the configuration format that the generator accepts; needs the error text              |
| 8   | riscv/riscv-unified-db               | `udb-v-operations/`              | feature  | 619 of 627 V instructions have no `operation()`                                                    |
| 9   | Openchip-Software/sail-riscv         | `sail-ime-family-flags/`         | bug      | `Zvvfmm` enables FP64 types without Zve64d; family flag semantics differ from UDB                  |
| 10  | Openchip-Software/riscv-ime-qemu     | `qemu-ime-macc-illegal-checks/`  | bug      | MACC and tile load/store run where the spec requires an illegal-instruction exception              |
| 11  | Openchip-Software/riscv-ime-qemu     | `qemu-ime-fp-subdot/`            | bug      | W > 1 FP MACC rounds each product into C; also a possible old A/B register layout                  |
| 12  | Openchip-Software/riscv-ime-qemu     | `qemu-ime-altfmt/`               | bug      | `vtype.altfmt` reserved without Zvfbfa; BF16-accumulator MACC traps                                |
| 13  | Openchip-Software/riscv-ime-qemu     | `qemu-ime-mx-rounding/`          | bug      | Microscaled MACC rounds the inner product and the scale; found by code reading, not run            |
| 14  | riscv/integrated-matrix-extension    | `ime-fp-internal-zero-sign/`     | spec gap | Sign of `fp_internal_zero()` and of an exact zero group sum is undefined (earlier draft)           |
| 15  | riscv/integrated-matrix-extension    | `spec-ime-e5m2-snan/`            | question | Can an E5M2 NaN input be signaling?                                                                |
| 16  | riscv/integrated-matrix-extension    | `spec-ime-altfmt-dependency/`    | question | BF16-accumulator types use the Zvfbfa `altfmt` field but depend only on Zve32f                     |
| 17  | riscv-non-isa/riscv-arch-test (act4) | `act-make-tests-stamps/`         | bug      | `make tests` stamps ignore `EXTENSIONS`                                                            |

Items 1 to 5 and 8 were checked against riscv-unified-db `main` @ `5d1ded1f` (2026-11-19).
Items 6 and 7 were seen on the fork `ime/fp-mx` @ `f0045fec`, which merges `main` @ `176fc360`.
Item 12 depends on the answer to item 16.

## Found, fixed or not reported

| Finding                                                                                          | Where             | Status                                                                                               |
| ------------------------------------------------------------------------------------------------ | ----------------- | ---------------------------------------------------------------------------------------------------- |
| Sail W > 1 FP MACC added each product into C                                                     | Sail `a545cc41`   | Fixed in `cleanup/ime-0.9.0` (`ime_fp_group_sum`). Draft `sail-ime-wmmacc-partial-sum/` is obsolete. |
| Sail rejects the OFP8-accumulator rows                                                           | Sail `0ebfc810`   | Implemented on `cgomez/ime-ofp8-acc` `2cb7eefb`, pending PR. Tests set aside.                        |
| `cp_ime_vm0` was never sampled: vm=0 `vmmacc.vv` and `vfmmacc.vv` decoded as illegal in coverage | ACT coverage      | Fixed on the branch (`a833181b0`).                                                                   |
| FP16 and BF16 covergroups sampled each other's instructions                                      | ACT covergroupgen | Fixed on the branch (`87073e242`).                                                                   |
| covergroupgen gave no covergroups to `ExtraExtensions` rows in per-SEW testplans                 | ACT covergroupgen | Fixed on the branch (`0bb9717a4`). Goes upstream with the PR.                                        |
| QEMU does not decode `vmttl.v` and `vmtts.v`                                                     | SDK QEMU          | Unverified. QEMU `d856b96` has decode entries and translators. Re-check by running.                  |
| ACT caps VLEN at 1024, so bins for λ ≥ 16 stay uncovered                                         | ACT               | Known limit. Not reported.                                                                           |
| `sfence.vma` reads `mstatus.TVM` before it checks the privilege mode                             | UDB               | Only a symptom of item 4. Not reported on its own.                                                   |
| GCC names the W=4 instructions `vqwmmacc.vv`, `vfqwmmacc.vv`, `vfqwimmacc.vv`                    | SDK GCC           | Naming differs from the spec. The `.insn` macros accept both. Not reported.                          |
