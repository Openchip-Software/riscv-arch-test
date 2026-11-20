<!-- SPDX-License-Identifier: Apache-2.0 -->

# 04: IME QEMU: report the deviations and pin a commit

Repository: `Openchip-Software/riscv-ime-qemu`, default branch `master` (public). The SDK image ships the same QEMU
as `qemu-system-riscv64` 10.2.50, run with `-cpu max,vlen=256,x-zvvm=true`.

State as of 2026-11-20. The ACT reference is Sail `0ebfc810` and spec `58810918`.

## Why

Sail as DUT against Sail as reference finds no model bugs. Package 07 adds this QEMU to upstream ACT CI as an
independent IME implementation. CI must pass, so each known QEMU deviation needs an issue that ACT can cite in its
exclusion list. ACT builds QEMU from source at a pinned commit, so it also needs a commit that builds cleanly with
the upstream QEMU build steps.

## Deviations found by the ACT IME tests

The IME specification is the reference. Each item below is a case where QEMU does not do what the specification
requires.

1. `vmmacc.vv` and `vfmmacc.vv` execute with `vstart` = 1 instead of raising an illegal-instruction exception.
2. `vmmacc.vv` and `vfmmacc.vv` execute with VL not a multiple of λ·LMUL instead of trapping.
3. Tile loads and stores execute with `vtype.vill` = 1 instead of trapping.
4. Tile loads and stores execute with the immediate λ L64, which no VLEN up to VLEN_MAX supports, instead of trapping.
5. A masked tile load into v0 executes instead of trapping.
6. `vmttl.v` and `vmtts.v` (Zvvmttls) are not decoded.
7. W>1 FP multiply-accumulate (`vfwmmacc.vv`, `vfqmmacc.vv`, `vf8wmmacc.vv`) adds each product to C with its own
   rounding. The specification forms the partial sum of the W products first. The ACT `cp_fp_subdot` bins fail on
   QEMU.
8. `vtype[8]` (`altfmt`) is reserved unless `x-zvfbfa=true`. The spec makes Zve32f the only dependency of
   `Zvvbf16mm`, so the bit must be writable with IME alone. With `x-zvfbfa=true` the ACT `Zvvbf16mm` tests pass.
9. [Inferred] The A/B register layout follows spec `6effbcae` (λ K elements per register). Spec `3c1b4457` makes it
   λ·W. Expected to fail W>1 at LMUL>1; item 7 hides it today.

Item 2 also covers tile loads and stores with VL not a multiple of λ·LMUL. Spec `58810918` still requires a multiple
for them. The unmerged ARC review draft makes every 0 ≤ VL ≤ VLMAX legal (Sail issue #8); recheck when it merges.

## Tasks

1. Reproduce each deviation with a minimal program, or with the ACT test named in the issue, and confirm it against
   the specification text.
2. File one issue per deviation, with the specification clause, the reproducer, and the expected and observed
   behaviour.
3. Fix what can be fixed. Item 7 changes FP results, so add a test for it.
4. Check that `./configure --target-list=riscv32-softmmu,riscv64-softmmu && make && make install` builds on
   `ubuntu-latest`. ACT's `install-qemu.sh` uses exactly these steps.
5. Choose a commit or tag to pin, and report it with the issue links to the ACT work (package 07).

## Acceptance

- One public issue per open deviation.
- A pinned commit that builds with the steps in task 4 and runs the ACT command line
  `qemu-system-riscv64 -nographic -semihosting -icount shift=1 -machine virt -cpu max,vlen=256,x-zvvm=true -bios <elf>`.
