<!-- SPDX-License-Identifier: Apache-2.0 -->

# 01: Sail fork: fix the remaining deviation and publish a release

Repository: `Openchip-Software/sail-riscv`, default branch `integrated-matrix-extension`. Local clone:
`~/repo/ime/sail-riscv`.

State as of 2026-11-09. Branch head `7707a9a1` (PR #11, "Ime microscaling"). The branch is based on upstream
`eb3e896f`, which is after the `0.16` tag.

## Why

The ACT IME tests take their expected results from this Sail fork. Upstream ACT CI downloads Sail as a release
tarball. Until IME is in upstream Sail (work package 02), the IME CI job needs a public, immutable release of this
fork. The release must not embed results that contradict the IME specification.

## Status of the known deviations

| Deviation                              | Status                                                                                                                                                      |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| W>1 FP multiply-accumulate partial sum | Fixed in `7707a9a1`. `ime_fp_group_sum` (`ime_mx.sail:169-181`) sums the W products exactly, then rounds once.                                              |
| `EMUL_C`=16, floating-point            | Fixed in `359d9800`. `ime_mx.sail:100` accepts `IME_EMUL_C_MAX` (16).                                                                                       |
| `EMUL_C`=16, integer (issue #10)       | **Not fixed.** `execute_ime_int_gemm` calls `ime_group_size_legal` (`ime_mem_insts.sail:249`), which accepts only 1, 2, 4 and 8 (`ime_utils.sail:134-135`). |

## Tasks

1. Fix integer `EMUL_C`=16. The specification permits `EMUL_C` = VLEN/(SEW·λ²) in {1, 2, 4, 8, 16}, with vd at v0 or
   v16 when `EMUL_C` is 16. Reuse the floating-point check in `ime_mx.sail` so both paths share one rule. Update issue
   #10 to say that only the integer path was open, and close it with the fix.
2. Resolve the VL=0 inconsistency. The integer path traps when N=0 (`ime_mem_insts.sail:244`). The new FP path
   (`ime_gemm_geometry`, `ime_mx.sail:97-99`) executes VL=0 as a no-op. Check what the specification says. If it is
   silent, pick one behaviour for both paths and record it in the implementation notes.
3. Check the signed-zero behaviour of the new FP engine. The partial sum S starts at +0 (`ime_mx.sail:172`), so
   C = −0 plus a −0 product gives +0 except with RDN rounding. Check this against the specification's
   `fp_internal_zero` rule. If the specification is silent, record it.
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

- The integer and FP multiply-accumulate instructions accept `EMUL_C`=16 at VLEN 256, SEW 16 and λ=1.
- A release exists with the asset names above, and `sail_riscv_sim --enable-experimental-extensions` runs from the
  unpacked tarball.

## Notes for ACT (do not change ACT from this repository)

- The new config schema adds `misa_implemented`, `hedeleg_zero_writable`, the trigger keys
  `supported_address_access_sizes` and `supported_data_access_sizes`, and 28 `Zvvx*`/`Zvvxn*` extension entries.
  ACT's `sail.json` files for IME must be updated (package 06).
- `vsetvli`/`vsetivli` with `zimm[8]` set now write `vtype.altfmt` when IME is enabled, instead of setting `vill`.
