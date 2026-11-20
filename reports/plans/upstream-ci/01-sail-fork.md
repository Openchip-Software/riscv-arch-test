<!-- SPDX-License-Identifier: Apache-2.0 -->

# 01: Sail fork: fix the remaining deviation and publish a release

Repository: `Openchip-Software/sail-riscv`, default branch `integrated-matrix-extension`. Local clone:
`~/repo/ime/sail-riscv`.

State as of 2026-11-20. ACT uses branch `cleanup/ime-0.9.0` at `0ebfc810`, which follows spec `58810918` and
implements all 65 IME extensions except the OFP8-accumulator rows. Those are on the pending branch
`cgomez/ime-ofp8-acc` (`2cb7eefb`).

## Why

The ACT IME tests take their expected results from this Sail fork. Upstream ACT CI downloads Sail as a release
tarball. Until IME is in upstream Sail (work package 02), the IME CI job needs a public, immutable release of this
fork. The release must not embed results that contradict the IME specification.

## Status of the known deviations

| Deviation                              | Status                                                                                                         |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| W>1 FP multiply-accumulate partial sum | Fixed in `7707a9a1`. `ime_fp_group_sum` (`ime_mx.sail:169-181`) sums the W products exactly, then rounds once. |
| `EMUL_C`=16, floating-point            | Fixed in `359d9800`. `ime_mx.sail:100` accepts `IME_EMUL_C_MAX` (16).                                          |
| `EMUL_C`=16, integer (issue #10)       | Fixed in `cleanup/ime-0.9.0`: the ACT SEW=16 integer files pass with `0ebfc810`.                               |
| OFP8 accumulator rows                  | Raise an illegal-instruction exception in `0ebfc810`. Implemented on `cgomez/ime-ofp8-acc`.                    |

## Tasks

1. Merge `cgomez/ime-ofp8-acc`. Close issue #10 if it is still open.
2. Resolve the VL=0 inconsistency. The integer path traps when N=0 (`ime_mem_insts.sail:244`). The new FP path
   (`ime_gemm_geometry`, `ime_mx.sail:97-99`) executes VL=0 as a no-op. Check what the specification says. If it is
   silent, pick one behaviour for both paths and record it in the implementation notes.
3. Signed zero: the spec does not define the sign of `fp_internal_zero()` (draft
   `reports/issues/ime-fp-internal-zero-sign/ISSUE.md` in the ACT docs worktree). Sail starts S at +0. Keep it until
   the spec decides.
4. Add a first-party test for each fix, in the style of the existing IME tests.
5. Publish a release for ACT:
   - Run `.github/workflows/release.yml` through `workflow_dispatch`. Scheduled runs do not run on a fork.
   - Use a tag that cannot be confused with an upstream tag, for example `ime-2026.11.1`.
   - Keep upstream's asset names: `sail-riscv-Linux-x86_64.tar.gz`, `sail-riscv-Linux-aarch64.tar.gz`,
     `sail-riscv-Mac-arm64.tar.gz` and `sail_riscv_config_schema.json`. ACT downloads
     `https://github.com/<repo>/releases/download/<tag>/sail-riscv-$(uname)-$(arch).tar.gz`, unpacks it with
     `--strip-components=1`, and runs `bin/sail_riscv_sim`.
   - Do not delete or replace a published release. Publish a new tag for each change.
6. Report the tag and the commit to the ACT work (package 06).

## Acceptance

- The OFP8-accumulator rows execute.
- A release exists with the asset names above, and `sail_riscv_sim --enable-experimental-extensions` runs from the
  unpacked tarball.

## Notes for ACT (do not change ACT from this repository)

- ACT's `config/ime/*/sail.json` already use the new config schema (ACT commit `b186cce44`).
- `vset{i}vl{i}` write `vtype.altfmt` (`vtype[8]`) when IME is enabled. ACT relies on this for the BF16 accumulator.
