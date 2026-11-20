<!-- SPDX-License-Identifier: Apache-2.0 -->

# Log: IME tests on riscv-unified-db and spec 58810918

Started 2026-11-19 on branch `cgomez/ime-udb-0.9.0`. Pins, environment and current status are in
[HANDOFF.md](HANDOFF.md). This file records what each step changed and why.

Before this work, the tests followed spec `6effbcae` (the v0.9 freeze of 2026-08-04), took the IME definitions from
an ACT-local UDB overlay, and used Sail `cgomez/0.16-plus-ime` `a545cc41`.

## Step 1: UDB replaces the overlay (`49b999ce9`)

- Removed the overlay `framework/src/act/data/udb_overlays/ime` and the `arch_overlay` code in
  `parse_udb_config.py`, which is the `act4` version again. `toolchain.py` lists the 65 IME extensions.
- `qemu-ime-rv64.yaml`: Zvvm versions 1.0.0 → 0.9.0. The newer UDB rejects five Sdext/SCONTEXT parameters. It
  requires the stateen `C`/`SE0` types and `HEDELEG_IAM_WRITABLE`; the values come from the write masks in the SDK
  QEMU (`target/riscv/csr.c`).
- QEMU FP disclosure: G=1, psm=0, rnd=xct. QEMU adds each product to C with one `float*_muladd` rounded with `frm`.
  For W>1 it also adds product by product, which no disclosure describes. The config repeats the W=1 profile.
- Check: `extensions.txt` unchanged. `rvtest_config.h` differs only in the version macros, the parameters above and
  115 new `UDB_ZVVM_FP_*` lines. QEMU results unchanged.

## Step 2: Sail `cleanup/ime-0.9.0` and `sail-ime-rv64` (`b186cce44`)

- Sail built on a compute node (job 65550).
- This Sail needs three new `sail.json` keys: `base.misa_implemented`, `H.hedeleg_zero_writable` and the Sdtrig
  `mcontrol6` access-size tables. The values are the Sail defaults and are not checked against QEMU.
- `config/ime/sail-ime-rv64` is `config/sail/sail-rv64-max` (VLEN 1024) plus the IME extensions, Zvvmttls, the λ
  lists for VLEN 1024 and Sail's FP profile. Sail is the DUT. It runs the gated tests and Zvvmttls.

## Step 3: tests for spec 58810918 (`413966b5a`, `aaa0c329c`)

- `cp_ime_vd_overlap` (ExceptionsZvvm): `vs1` or `vs2` at the base of C, `vs2` at the last register of C for each λ,
  and VL = 0.
- `cp_fp_rnd` (Zvvfmm): a group sum S that is not exact in the C format while C₀ + S is. The rnd=frm and rnd=xct
  results then differ in every rounding mode. Gated on rnd=frm and psm=0.
- Results: `sail-ime-rv64` 41/41 files pass. On `qemu-ime-rv64` the integer and tile suites pass. The 5 W>1 Zvvfmm
  files fail at `cp_fp_subdot`, and ExceptionsZvvm fails 7/7 at `cp_ime_vstart`.

## Step 4.1: BF16 accumulator `Zvvbf16mm` (`59666b161`)

- New `Zvvfmm.csv` row: `vfmmacc.vv` at SEW=16 with `altfmt_A = altfmt_B = altfmt = 1`. `altfmt` is `vtype[8]`, the
  Zvfbfa position, and selects the C format. `InstructionParams.altfmt` sets it.
- The FMMACC formatter and `cp_fp_rnd` take the C format from the row: BF16 when the type extension ends in `bf16mm`.
  A BF16 value has 8 significant bits. Its data uses inputs in [-1, 1] and C = k + 0.5 with |k| ≤ 31, so every sum
  stays below 96 and is exact.
- New coverage template `cp_vd_edges_f_bf16_sew16`. Both configs declare `Zvvbf16mm`.
- The other IME tests regenerate byte for byte.
- Results: Zvvfmm16 passes 2/2 on `sail-ime-rv64`. On `qemu-ime-rv64`, `Zvvbf16mm` fails at its first testcase
  (HANDOFF, QEMU deviation 5).

## Step 4.2: OFP8 inputs (`5494a1432`)

- Rows from the spec encoding map: `vfwmmacc.vv` SEW=16 (`Zvvofp8fp16mm`, `Zvvofp8bf16mm`), `vfqmmacc.vv` SEW=32
  (`Zvvofp8fp32mm`), `vf8wmmacc.vv` SEW=64 (`Zvvofp8fp64mm`). Sail `0ebfc810` (`ime_fp_base_row_ok`) and the SDK QEMU
  (`trans_vfwmmacc_vv`, `trans_vfqwmmacc_vv`, `trans_vf8wmmacc_vv`; all enabled by `x-zvvm=true`) decode all four, so
  both configs declare them. The `.insn` macros and `RISCV_decode_pkg.svh` already had `vf8wmmacc.vv`.
- `altfmt_A` and `altfmt_B` select E4M3 or E5M2 per operand. New `cp_altfmt_ofp8` runs the four combinations. New
  edge variant `f_ofp8`: E4M3 and E5M2 edges, each testcase with `altfmt_A = altfmt_B` set to the edge's format. The
  templates `cp_vs{1,2}_edges_f_ofp8_sew{16,32,64}` have one coverpoint per format, filtered on its `altfmt` bit.
- Exact data: K = λ·W·LMUL reaches 256 at SEW=16, W=4, so a widening row with an FP16 or BF16 C holds at most one
  nonzero input per storage element (at most 64 nonzero terms per dot product).
- `cp_fp_subdot`: A = B = 1.0 and C0 = W·2^(p−1). `cp_fp_rnd`: data for (16,2) and (32,4) in E4M3, and (64,8) in
  E5M2. OFP4 products span too few bits to make the group sum inexact, so OFP4 rows will have no `cp_fp_rnd`.
- Disclosures added: `ZVVM_FP_{GROUPING,PSM,RND}_SEW16_W2`, `_SEW32_W4`, `_SEW64_W8`, with each simulator's profile.
- Existing tests regenerate byte for byte. Covergroup changes are additions only. pyslang compiles Zvvfmm16/32/64.
- Results: Zvvfmm 13/13 on `sail-ime-rv64`. On `qemu-ime-rv64` all four OFP8 files fail: three at `cp_fp_subdot`
  (QEMU deviation 4), `Zvvofp8bf16mm` at its first testcase (deviation 5).

## Decisions

- **Family flags.** In UDB each type extension requires its family, and a family alone enables no type. In Sail a
  family flag enables every type of the family (`currentlyEnabled` in `ime_types.sail`), OFP8 included. The
  `sail.json` files set the families to false and each declared type to true.
- **Gated FP tests.** Sail computes rnd=frm only. A test that depends on rnd is generated for rnd=frm and gated on
  `UDB_ZVVM_FP_RND_SEW<s>_W<w>_IDX<i>_FRM` and on psm=0. QEMU discloses rnd=xct and skips them. Their bins stay open
  there.
- **`altfmt` without Zvfbfa.** The spec lists Zve32f as the only dependency of `Zvvbf16mm`, and UDB agrees. Sail
  `0ebfc810` writes `vtype[8]` whenever IME is enabled. The rows therefore do not require Zvfbfa. This replaces the
  decision of 2026-10-27, taken with the old Sail, that BF16 and E5M2 outputs require Zvfbfa.
- **E5M2 signaling NaN.** The spec says OFP8 special values follow "the rules of the operand formats" and does not
  say whether an E5M2 NaN can be signaling. Sail treats all E5M2 NaNs as quiet. The testcase for 0x7D (signaling
  under the IEEE convention) sets `fflags.NV` before the instruction, so C is the canonical NaN and NV is set either
  way.
- **QEMU command line.** It stays as the SDK ships it. `x-zvfbfa=true` would hide QEMU deviation 5.

## Spec delta 6effbcae → 58810918

| Spec commit                                                            | Change                                                                     | ACT impact                                                               |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `5bcd3946`                                                             | `vd` must not overlap `vs1` or `vs2`, regardless of VL                     | New `cp_ime_vd_overlap`. The MMACC formatter already kept them apart.    |
| `3c1b4457`                                                             | Each A/B register holds λ·W consecutive K elements per row (was λ)         | No generator change: Sail computes the values. QEMU uses the old layout. |
| `cc42d98d`                                                             | N = VL/(λ·LMUL); a VL that is not a multiple stays illegal                 | None. `cp_ime_vl_not_multiple` stays.                                    |
| `e4bf2c19`                                                             | `vta=1`: each tail element unchanged or all ones; VL = 0 updates nothing   | None: MACC tests use `vta=0`.                                            |
| `26b0fd87`, `d74d8d85`, `fcca60a8`                                     | The W=1 term is the exact product; products may leave the C exponent range | None: FP data is exact under every profile.                              |
| `fcc718d4`, `2a1fc11f`, `9eea6c86`, `dbc788ec`                         | Intrinsics text (immediate λ, mask type, `__riscv_vsetlambda`)             | None. The immediate-λ rule matches `cp_ime_imm_lambda_unsupported`.      |
| `37840bb8`                                                             | psm=1 rules                                                                | Gated tests require psm=0.                                               |
| `ad2d5f22`, `7ac568a5`, `0a13020a`, `e06eca02`, `40446383`, `324c62b7` | Block scales: E8M0, exact application, LMUL limits, count                  | Step 4.3 (microscaling).                                                 |

## OFP8 tests set aside

Sail `0ebfc810` decodes the OFP8-accumulator rows and raises an illegal-instruction exception for them. The pending
Sail branch `cgomez/ime-ofp8-acc` (`2cb7eefb`) implements them. Their tests are listed here and handled with that
pull request.

| Extension                           | Rows                        | Status                                                  |
| ----------------------------------- | --------------------------- | ------------------------------------------------------- |
| `Zvvofp8mm`                         | `vfmmacc.vv` SEW=8          | no testplan row; not declared in the configs (step 4.2) |
| `Zvvofp4ofp8mm`                     | `vfwmmacc.vv` SEW=8         | no testplan row yet                                     |
| `Zvvxofp4ofp8mm`, `Zvvxnofp4ofp8mm` | `vfwmmacc.vv` SEW=8, `vm=0` | no testplan row yet                                     |
