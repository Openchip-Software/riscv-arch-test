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
  E5M2.
- Disclosures added: `ZVVM_FP_{GROUPING,PSM,RND}_SEW16_W2`, `_SEW32_W4`, `_SEW64_W8`, with each simulator's profile.
- Existing tests regenerate byte for byte. Covergroup changes are additions only. pyslang compiles Zvvfmm16/32/64.
- Results: Zvvfmm 13/13 on `sail-ime-rv64`. On `qemu-ime-rv64` all four OFP8 files fail: three at `cp_fp_subdot`
  (QEMU deviation 4), `Zvvofp8bf16mm` at its first testcase (deviation 5).

## Step 4.2: OFP4 inputs (`483225a9a`)

- Rows: `vfqmmacc.vv` SEW=16 (`Zvvofp4fp16mm`, `Zvvofp4bf16mm`) and `vf8wmmacc.vv` SEW=32 (`Zvvofp4fp32mm`). Sail and
  the SDK QEMU decode all three. Both configs declare them and disclose `SEW16_W4` and `SEW32_W8`.
- Edge variant `f_ofp4`: all 16 E2M1 encodings. No `cp_altfmt`: `altfmt_A = 1` or `altfmt_B = 1` is reserved for
  4-bit inputs.
- `cp_fp_rnd`: E2M1 products are multiples of 2^−2 up to 36, so a group sum of W ≤ 8 products is exact in FP16 and
  FP32. Only `Zvvofp4bf16mm` has data: S = 3·36 + 2^−2 = 108.25 needs 9 significant bits, and BF16 has 8.
- Existing tests regenerate byte for byte. Covergroup changes are additions only. pyslang compiles Zvvfmm16/32.
- Results: Zvvfmm16 6/6 and Zvvfmm32 5/5 on `sail-ime-rv64`. On `qemu-ime-rv64` the FP16 and FP32 files fail at
  `cp_fp_subdot` (deviation 4), `Zvvofp4bf16mm` at its first testcase (deviation 5).

## Step 4.3: microscaled FP inputs (`42f233275`)

- Rows: `Zvvxofp8{fp16,bf16,fp32,fp64}mm`, `Zvvxofp4{fp16,bf16,fp32}mm` and their `Zvvxn*` forms, 14 in all, type
  `FMMACC_MX`. A `Zvvx*` row runs with `vtype.bs = 0` (block size 32), a `Zvvxn*` row with `bs = 1` (block size 16).
  Only `sail-ime-rv64` declares them. QEMU `d856b96` accepts vm=0 only with `x-zvvfmmmx=true`.
- Sail `0ebfc810` (`ime_mx.sail`) implements every FP microscaled row except an OFP8 C. It rejects any operand on v0
  and, for bs=1, W·LMUL > SEW.
- v0 holds the scale pairs, so the C window is v16 and A and B are in v1–v15; at LMUL=8 both are v8.
- Exact data: random scales have a combined exponent of −1, 0 or 1, so every value is a multiple of 0.5. An FP16 C
  stays below 640.5. A BF16 C zeroes the odd A and B storage elements, which keeps at most 32 nonzero terms and the
  sum below 96.
- `cp_scale` per C format: NaN scale_A or scale_B in element 0, the pairs (2^−127, 2^127) and (2^127, 2^−127), and
  combined exponents −26/−136/−152 (below FP16/BF16/FP32) and 16/128 (above FP16, BF16/FP32). For the last two, A is
  zero except A[0][0] and B is constant, so each scaled partial sum is exact in C. FP64 has no such exponents.
- The `Zvvxn` OFP4 rows use `cr_lambda_lmul_lte4` (W·LMUL ≤ SEW).
- Coverage: vm=0 decode and disassembly (`, v0.scale`), `vtype.bs` in `get_csr_val`. Sample calls are gated on
  `insn[25]` per row type, so unscaled and microscaled covergroups no longer sample each other's instructions.
- Existing tests regenerate byte for byte. pyslang compiles Zvvfmm16/32/64. Results: Zvvfmm16 14/14, Zvvfmm32 9/9,
  Zvvfmm64 7/7 on `sail-ime-rv64`.

## Step 4.3: microscaled integer inputs (`89c7fdb33`)

- Rows: `Zvvxi8{fp16,bf16,fp32,fp64}mm`, `Zvvxi4{fp16,bf16,fp32}mm` and their `Zvvxn*` forms, 14 in all, type
  `FMMACC_MX`, on `vfwimmacc.vv`, `vfqimmacc.vv` and `vf8wimmacc.vv`. Only `sail-ime-rv64` declares them.
- The spec sums each block of integer products exactly, applies the combined exponent and rounds once with frm. G,
  psm and rnd do not apply, so the results are fully specified. Sail `ime_int_scaled_gemm` does the same.
- Edges: the integer variants of the unscaled rows (`emulf2`, `emulf4`, `emulf8`). `cp_fp_subdot`: W products of 1
  sum to one ULP of C0. `cp_scale` overflow: zero partial sum, since an integer sum of at least 1 would overflow C.
  No `cp_fp_rnd` and no `cp_altfmt`: MXINT inputs are signed only.
- Earlier tests regenerate byte for byte. pyslang compiles Zvvfmm16/32/64. Results: Zvvfmm16 22/22, Zvvfmm32 13/13,
  Zvvfmm64 9/9 on `sail-ime-rv64`.

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
- **QEMU command line.** It stays as the SDK ships it. `x-zvfbfa=true` would hide QEMU deviation 5. Without
  `x-zvvfmmmx=true`, QEMU raises an illegal-instruction exception for every vm=0 MACC. The QEMU config therefore
  declares no microscaled extension.
- **Scales of edge tests.** Edge values, `cp_fp_subdot` and `cp_fp_rnd` run with unit scales (0x7F). Their results
  then equal the unscaled results, and they test that the vm=0 path decodes inputs and forms partial sums the same
  way.

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
| `Zvvofp4ofp8mm`                     | `vfwmmacc.vv` SEW=8         | no testplan row; not declared in the configs (step 4.2) |
| `Zvvxofp4ofp8mm`, `Zvvxnofp4ofp8mm` | `vfwmmacc.vv` SEW=8, `vm=0` | no testplan row; not declared in the configs (step 4.3) |
