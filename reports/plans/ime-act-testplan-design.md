<!-- SPDX-License-Identifier: Apache-2.0 -->

# Design: the ime-test-gen plan as ACT testplans (option C)

This file describes how the IME tests of ime-test-gen are expressed as native ACT testplans ("option C"). It covers
the implemented design, the open issues and the remaining work. It is the testplan design behind Report 2,
Section 16b. Current status, pins and results are in [HANDOFF.md](HANDOFF.md); this file does not repeat them.

Pins and conventions:

- ACT: `riscv-arch-test` branch `cgomez/ime-udb-0.9.0` (HANDOFF §5).
- Paths are relative to that repository unless they start with one of these prefixes:
  - `ime-test-gen/`: riscv-ime-arch-tests `46f3781`.
  - `sail/`: the Sail fork `Openchip-Software/sail-riscv`. The reference model is `cleanup/ime-0.9.0` `0ebfc810`.
    Line citations were taken on the older branch `cgomez/0.16-plus-ime` and may not match.
  - `qemu/`: `Openchip-Software/riscv-ime-qemu` branch `vrull/ime-wip` at `d856b96`, which is also the SDK QEMU pin.
  - `spec:`: the tests follow spec `58810918`. Line citations `spec:<n>` were taken at `6effbcae`
    (`src/integrated-matrix.adoc`) and may be off. [udb-0.9.0.md](udb-0.9.0.md) lists the normative changes.
- ARC review draft of the specification: branch `jmoreira/arc-review-updates-01` at `d051f35b` (commit `ad6de478da`).
  It is not merged. It makes every 0 ≤ VL ≤ VLMAX legal for tile loads and stores, and makes a MACC VL that is not a
  multiple of λ·LMUL reserved. It renames λ to KLEN and M to MLEN. `EMUL_C` ∈ {1,2,4,8,16} is unchanged. This design
  follows spec `main`. §7 lists what must be reviewed when the draft merges.
- Tags: **[Spec]** = specification requirement. **[ACT]** = existing ACT convention or code. **[Impl]** = what the
  IME code on the branch does. **[Planned]** = not implemented yet. **[Decision]** = project decision of 2026-10-27.
  **[Inferred]** = derived from code or the specification, not run.

Project decisions of 2026-10-27, still valid:

1. λ is gated per testcase (§1.4). Selection in the test header is not used.
2. Composed tile tests are extra bins (`cp_custom_tile_*`, §4.3).
3. The FP profile (G, psm, rnd) is disclosed per (SEW, W, λ) through UDB parameters (§5). The target
   implementation's values are not known yet.
4. **Source of truth** (§0.1). The IME specification decides conflicts. The Sail fork decides where the specification
   is silent or ambiguous. QEMU, the SDK GCC and the Rust golden model never decide.

## 0. Summary

- Four unprivileged CSVs, one per family extension: `Zvvmm.csv`, `Zvvfmm.csv`, `Zvvmtls.csv` and `Zvvmttls.csv`.
  Illegal-instruction and `vstart` cases are in the privileged suite `testplans/priv/ExceptionsZvvm.csv`.
- One row per (mnemonic, type extension). The type extension goes in `ExtraExtensions`. The `EFFEW<n>` columns give
  the accumulator SEW.
- λ is gated per testcase with `#if defined(UDB_SUPPORTED_LAMBDA_SEW<n>_<λ>)`. UDB emits these macros from the
  `SUPPORTED_LAMBDA_SEW<n>` parameters. The header names no λ, and no file is split by λ.
- MACC tests load A, B and C with `vle<SEW>.v`. They check the 16-register C window with `RVTEST_SIGUPD_V_LEN`. They
  do not use tile instructions, so they are VLEN-agnostic. `vd` never overlaps `vs1` or `vs2` (spec `5bcd3946`).
- Tile load tests check the destination register group. Tile store tests read back a memory window with `vle`.
- Two composed coverpoints are implemented: `cp_custom_tile_macc` (`vmmacc.vv` with tile-loaded A and B and a
  tile-stored C) and `cp_custom_tile_crossmode` (TC-LS-03/04). `cp_custom_tile_layout` and `cp_custom_tile_roundtrip`
  are optional (step 3a, §4.4).
- FP data is exact: small integers in A and B, half-integers in C. The result then does not depend on `psm` or `rnd`.
  `cp_fp_rnd` adds profile-dependent data, gated on the disclosed profile (§5).
- `cp_fp_subdot` tests the W>1 partial sum (§4.5). Sail follows the specification; QEMU fails these bins.
- No new check macro was needed. `act` test selection and the build needed no change.

### 0.1 Source of truth (decided 2026-10-27)

When implementations or documents conflict, the IME specification decides. Where the specification is silent or
ambiguous, the IME Sail fork decides. QEMU, the SDK GCC and the Rust golden model never decide a conflict.

- **Sail contradicts the specification:** Sail is wrong. The bins follow the specification and stay in place, with no
  `ignore_bins` and no exclusion. Expected values come from Sail, so these bins fail on a conforming DUT until Sail is
  fixed. Each case has a Sail issue.
- **The specification permits several behaviours**, for example rnd ∈ {frm, rto, xct}: tests do not depend on the
  choice (§5).
- **The specification is silent:** tests follow the Sail code. The design records "spec silent; Sail behaviour".

| Conflict                                                     | Basis                                                              | Resolution                                                                                             |
| ------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| W>1 FP accumulation                                          | QEMU contradicts the specification (spec:1352-1412)                | Fixed in Sail. `cp_fp_subdot` bins follow the specification and fail on QEMU (§4.5).                   |
| MACC `EMUL_C`=16                                             | Old Sail rejected it; the specification permits it (spec:381)      | Fixed in Sail `0ebfc810` ([sail-riscv#10](https://github.com/Openchip-Software/sail-riscv/issues/10)). |
| λ with `EMUL_C` < 1                                          | Sail accepts it; the specification forbids it (spec:811-815)       | UDB λ lists follow the specification. Positive tests are gated, so they never use such a λ (§7).       |
| W=1 FP rounding: Sail rnd=frm, QEMU rnd=xct                  | The specification permits both                                     | Not a conflict. W=1 data keeps products exact (§5).                                                    |
| MACC `vd` overlap with `vs1`/`vs2`                           | Spec `5bcd3946` forbids it                                         | `cp_ime_vd_overlap` expects a trap (§7).                                                               |
| `altfmt=1` for an FP output without Zvfbfa                   | Spec lists only Zve32f; Sail `0ebfc810` writes `vtype[8]` with IME | Rows do not require Zvfbfa. QEMU needs `x-zvfbfa=true` (§7).                                           |
| W=4 mnemonics                                                | GCC and QEMU names differ from the specification                   | Specification names in the CSVs. GCC names exist only as macro aliases (§2.2).                         |
| Family and type extension direction                          | ime-test-gen differs from the specification                        | The UDB direction holds (§1.3).                                                                        |
| `zvmma`, `zvvxofp8mm`, `zvvxnofp8mm`                         | GCC-only names                                                     | Not used in ACT.                                                                                       |
| QEMU microscaling and mixed-format paths; Rust model `--fma` | Not sources of truth                                               | Findings only (§6.1).                                                                                  |

Fixed in the Sail fork, with no workaround left in ACT:

- Tile loads and stores used the flat register index instead of `tile_reg_idx`. Fixed by `a545cc41`.
- LD = 0 in a register other than `x0` did not select the natural LD. Fixed by `c1d96b3e`.
- A masked tile load with `vd` = `v0` did not trap. Fixed by `fd88fd86`.
- VL = 0 trapped for transposing tile loads and stores. Fixed by `c9361710`.

## 1. Suite split and extension requirements

### 1.1 How ACT derives requirements

- [ACT] The testplan file name (without `.csv`) is the suite name. A name starting with `V` or `Zv` is a vector suite
  (`generators/testgen/src/testgen/cli.py`).
- [ACT] Vector suites listed in `expand_vector_extension` become one suite per SEW
  (`generators/testgen/src/testgen/io/testplans.py`). Rows whose `EFFEW<sew>` cell is empty are skipped.
- [ACT] `REQUIRED_EXTENSIONS` is built from the suite name split at capitals, the row's `ExtraExtensions`, and a minimal
  `Zve*` base from `get_vector_base_extension` (`io/templates.py`). The default base is `Zve{max(sew,32)}x`.
- [ACT] An experimental extension adds `#define RVTEST_EXPERIMENTAL`. `act` skips such tests unless
  `--enable-experimental-extensions` is set.

### 1.2 Suites

| CSV                                 | Suite → `REQUIRED_EXTENSIONS`                      | Rows                                                      | Per-SEW expansion        |
| ----------------------------------- | -------------------------------------------------- | --------------------------------------------------------- | ------------------------ |
| `testplans/Zvvmm.csv`               | `Zvvmm` + type ext + `Zve32x`/`Zve64x`             | 13 integer type extensions + 4 `cp_custom_tile_macc` rows | `Zvvmm8`…`Zvvmm64`       |
| `testplans/Zvvfmm.csv`              | `Zvvfmm` + type ext + `Zve32f`/`Zve64d` (+`F`,`D`) | 8 rows that Sail implements                               | `Zvvfmm8`…`Zvvfmm64`     |
| `testplans/Zvvmtls.csv`             | `Zvvmtls` + `Zve32x`/`Zve64x`                      | 2 (`vmtl.v`, `vmts.v`)                                    | `Zvvmtls8`…`Zvvmtls64`   |
| `testplans/Zvvmttls.csv`            | `Zvvmttls` + `Zve32x`/`Zve64x`                     | 2 + 2 cross-mode rows (`ExtraExtensions=Zvvmtls`)         | `Zvvmttls8`…`Zvvmttls64` |
| `testplans/priv/ExceptionsZvvm.csv` | set by `@add_priv_test_generator`                  | one per mnemonic (11)                                     | `EFFEW` per row          |

Why four suites:

- [Spec] The specification defines exactly four family extensions (spec:41-46). "Implementing a family-level extension
  requires support for all instructions in that family" (spec:590).
- [ACT] Splitting the suite name at capitals turns each suite name into exactly one family name. No mapping code is
  needed.
- [ACT] ACT moves toward fewer suites that use `ExtraExtensions`. Commit `574c6b55c` merged `<Suite><Ext>` testplans
  into their base suites. Per-type CSVs would create 65 suites.
- [UDB] Microscaling extensions require `Zvvfmm` (UDB `spec/std/isa/ext/Zvvxi8fp16mm.yaml`).
  Their rows therefore belong in `Zvvfmm.csv`, including the integer-input forms `vfwimmacc.vv`, `vfqimmacc.vv` and
  `vf8wimmacc.vv`.

[Impl] Framework edits:

- The four suites are in `expand_vector_extension` (`io/testplans.py`) and in covergroupgen's `_sew_variants_for`
  (`generators/coverage/src/covergroupgen/generate.py`).
- `vector_map` in `io/templates.py` maps `Zvvfmm8`, `Zvvfmm16` and `Zvvfmm32` to `["Zve32f","F"]`, and `Zvvfmm64` to
  `["Zve64d","F","D"]`.
- IME suites skip the V widening adjustments of `get_vector_base_extension` (`IME_SUITE_PREFIXES`). In IME, no operand
  is wider than SEW, so the V rule that raises the base to `Zve64*` does not apply (commit `98595c2a5`).

### 1.3 Type extensions through `ExtraExtensions`

- [ACT] `docs/DeveloperGuide.md` documents `ExtraExtensions` as "Extensions a row needs beyond the testplan's own".
  `Zfa.csv`, `Zfh.csv`, `Zacas.csv` and `Zkt.csv` already have rows with the same mnemonic and different
  `ExtraExtensions`.
- [ACT] Each `ExtraExtensions` value gets its own `TestConfig`, file prefix and covergroup prefix. Testgen needed no
  change.
- [Impl] Covergroupgen lost `ExtraExtensions` groups of per-SEW suites. `read_testplans` now copies each group into the
  SEW variants whose `EFFEW` column selects it (commit `0bb9717a4`).
- Resulting names: test `tests/rv64i/Zvvmm32/Zvvmm32Zvvi8i32mm-vqmmacc.vv-00.S`, and covergroup
  `Zvvmm32Zvvi8i32mm_vqmmacc_vv_cg` inside `` `ifdef ZVVI8I32MM_SUPPORTED ``.
- [ACT] `.gitignore` excludes `tests/rv*/Zv*` and `tests/priv/**/*.S`. IME tests are regenerated, not checked in.
  Covergroups are checked in.

A mapping from (mnemonic, SEW) to the type extension was rejected. It works for integer rows, but at
(`vfwmmacc.vv`, SEW=32) FP16 and BF16 inputs are separate extensions. Explicit rows are also easier to audit against the
encoding maps.

Extension direction (§0.1):

- [Spec] A row is legal only when the extension in its encoding-map cell is implemented (spec:6646-6649). A family
  extension therefore implies no type extension. ime-test-gen's opposite direction is generator finding 13.
- [Spec silent; Sail] The specification does not say whether a type extension requires its family extension. The
  UDB requires it, as GCC does. In Sail a family flag enables every type of the family, so the `sail.json` files
  enable only the declared types.

### 1.4 λ gating per testcase (decided)

- [ACT] A header `params` key holds one value, so one file could require only one λ per SEW. Header selection was
  therefore not used.
- [ACT] UDB turns each list parameter into one macro per value in `rvtest_config.h`. The UDB parameters
  `SUPPORTED_LAMBDA_SEW8` … `SUPPORTED_LAMBDA_SEW64` produce `UDB_SUPPORTED_LAMBDA_SEW<n>_<λ>`.
- [Impl] `asm/vector_helpers.py` provides the gate:
  - `ime_lambdas(sew)` returns the λ values with SEW·λ² ≤ `VLEN_MAX` (1024). Larger λ need `EMUL_C` < 1 at every
    supported VLEN.
  - `ime_lambda_condition(sew, lambdas)` builds the `#if defined(...) || ...` condition.
  - `handle_parameter_exclusions(..., ime_condition=...)` wraps setup and check in that condition.
- [Impl] A testcase that names no λ (for example `cp_vs1`) uses a preprocessor chain in `load_ime_vtype`. The chain
  picks the smallest λ that the DUT supports. `LI()` has a fixed length, so every branch has the same size.
- Testcases with an immediate λ require both the immediate λ and a different background λ (§3.4).
- Why this is safe:
  - [ACT] The signature ELF and the self-checking ELF are built from the same source and the same `rvtest_config.h`.
  - [ACT] `SIGUPD_COUNT` is an upper bound. The signature run records the final signature offset.
  - [Spec] UDB rejects a λ for which VLEN/(SEW·λ²) ∉ {1,2,4,8,16}. A supported λ therefore implies a legal `EMUL_C`
    (spec:798-819).

## 2. Rows and type representation

### 2.1 SEW is the accumulator width

- [Spec] In IME, `SEW` is the width of the accumulator C. A and B hold elements of width `SEW/W`, packed into
  `SEW`-wide storage elements (spec:352-380, 1010-1036).
- [ACT] In V widening instructions, `SEW` is the narrow width, and `vd` is widened. `Vx.csv` therefore leaves
  `EFFEW64` empty for `vwmacc.vv`.
- [Impl] IME rows set `EFFEW<n>` to the accumulator SEW. No register is marked as widened. Narrow integer inputs use
  the edge suffixes `emulf2`, `emulf4` and `emulf8`. Narrow FP inputs use `f_emulf2`, `f_emulf4` and `f_bf16`.

### 2.2 Row inventory

[Spec] Rows follow the encoding maps (spec:6640-6974). A reserved (instruction, SEW) cell gets an empty `EFFEW` cell.

| Mnemonic                                               | Type         | `ExtraExtensions` → EFFEW                                                                                                                                              | Status  |
| ------------------------------------------------------ | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `vmmacc.vv`                                            | `MMACC`      | `Zvvi8mm`→8, `Zvvi16mm`→16, `Zvvi32mm`→32, `Zvvi64mm`→64                                                                                                               | done    |
| `vwmmacc.vv`                                           | `MMACC`      | `Zvvi4i8mm`→8, `Zvvi8i16mm`→16, `Zvvi16i32mm`→32, `Zvvi32i64mm`→64                                                                                                     | done    |
| `vqmmacc.vv`                                           | `MMACC`      | `Zvvi4i16mm`→16, `Zvvi8i32mm`→32, `Zvvi16i64mm`→64                                                                                                                     | done    |
| `v8wmmacc.vv`                                          | `MMACC`      | `Zvvi4i32mm`→32, `Zvvi8i64mm`→64                                                                                                                                       | done    |
| `vfmmacc.vv`                                           | `FMMACC`     | done: `Zvvfp16mm`→16, `Zvvbf16mm`→16, `Zvvfp32mm`→32, `Zvvfp64mm`→64. Planned: `Zvvfp16mm:Zvvbf16mm`→16, `Zvvofp8mm`→8                                                 | partial |
| `vfwmmacc.vv`                                          | `FMMACC`     | done: `Zvvfp16fp32mm`→32, `Zvvbf16fp32mm`→32, `Zvvfp32fp64mm`→64. Planned: `Zvvfp16fp32mm:Zvvbf16fp32mm`→32, `Zvvofp4ofp8mm`→8, `Zvvofp8fp16mm`→16, `Zvvofp8bf16mm`→16 | partial |
| `vfqmmacc.vv`                                          | `FMMACC`     | done: `Zvvfp16fp64mm`→64, `Zvvbf16fp64mm`→64. Planned: `Zvvfp16fp64mm:Zvvbf16fp64mm`→64, `Zvvofp4fp16mm`→16, `Zvvofp4bf16mm`→16, `Zvvofp8fp32mm`→32                    | partial |
| `vf8wmmacc.vv`                                         | `FMMACC`     | `Zvvofp4fp32mm`→32, `Zvvofp8fp64mm`→64                                                                                                                                 | planned |
| `vfwmmacc.vv`, `vfqmmacc.vv`, `vf8wmmacc.vv` with vm=0 | `FMMACC_MX`  | 16 rows `Zvvx[n]ofp*` (microscaled OFP8/OFP4 inputs)                                                                                                                   | planned |
| `vfwimmacc.vv`, `vfqimmacc.vv`, `vf8wimmacc.vv`        | `MMACC_MX`   | 14 rows `Zvvx[n]i8*`, `Zvvx[n]i4*`                                                                                                                                     | planned |
| `vmtl.v`, `vmts.v`                                     | `VLT`, `VST` | none; EFFEW 8 to 64                                                                                                                                                    | done    |
| `vmttl.v`, `vmtts.v`                                   | `VLT`, `VST` | none; EFFEW 8 to 64                                                                                                                                                    | done    |

Notes:

- [Spec] A mixed FP16/BF16 row requires both named extensions. A colon list in `ExtraExtensions` expresses that, as
  `Zfh:D` does in `Zfa.csv`.
- Integer signedness is not a separate row. It is a bin of `cp_altfmt`: one integer extension covers all four
  signedness combinations. [Planned] FP input-format combinations (mixed FP16/BF16, E4M3/E5M2) become `cp_altfmt`
  bins on the FP rows in the same way.
- [Spec vs toolchain] The CSV uses the specification names `vqmmacc.vv`, `vfqmmacc.vv` and `vfqimmacc.vv`.
  `tests/env/rvtest_experimental.h` defines `.insn` macros for both these names and the GCC and QEMU names
  (`vqwmmacc.vv`, …).

## 3. Instruction formatter types

The formatters are in `generators/testgen/src/testgen/formatters/types/mmacc_type.py` (`MMACC`, `FMMACC`) and
`tile_type.py` (`VLT`, `VST`).

### 3.1 Shared IME pieces

- [Impl] New `InstructionParams` fields (`data/params.py`): `lambda_`, `altfmt_a`, `altfmt_b`, `imm_lambda` and `ld`.
  `vl` also accepts `"half"`.
- [Impl] New `VectorTypeConfig` field `fixed_emul: dict[str, int]`, used as `{"vd": 16}`. `get_register_emul`,
  `get_occupied_v_registers` and the data label size use it.
- [Impl] `load_ime_vtype(params, test_data, ...)` in `asm/vector_helpers.py` emits `LI(xT, <vtype>)` and
  `vsetvl xV, xA, xT`.
  - [Spec] The IME fields are outside the `vsetvli` immediate. Only `vsetvl` writes them (spec:712-797).
  - [Spec] Field positions (spec:686-690): `lambda[2:0]` at `vtype[XLEN-2:XLEN-4]`, `bs` at `XLEN-5`, `altfmt_A` at
    `XLEN-6` and `altfmt_B` at `XLEN-7`. `ime_vtype_value` computes the value per XLEN. `bs` stays 0.
- [Impl] VL semantics. The IME formatters count `params.vl` in units of λ·LMUL elements: one column of C for MACC, one
  line for tile loads and stores.
  - `"vlmax"`: `vsetvl` with AVL `x0`.
  - An integer n: n units.
  - `"half"`: VLMAX/2. VLMAX/(λ·LMUL) = VLEN/(SEW·λ) is a power of two of at least 2.
  - `"random"`: a random multiple of λ·LMUL in [λ·LMUL, VLMAX − λ·LMUL], computed at run time.
  - [Spec] VL must be a multiple of λ·LMUL (spec:5776, spec:2353). See §7 for the ARC draft.
- [Impl] Base-suite coverpoints (for example `cp_vs1`) pass VL=1 and short data labels. The IME formatters run them at
  VL = VLMAX and extend the labels with `ime_extend_label`.

### 3.2 `MMACC` (integer) and `FMMACC` (FP, vm=1)

[Impl] `mmacc_type.py`:

```python
mmacc_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(
        overlap_constraints={("vd", "vs1"), ("vd", "vs2")},
        fixed_emul={"vd": 16},
        maskable=False,
        require_zero_vstart=True,
    ),
)
fmmacc_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    instruction_class=["vector_fp"],
    vector_data=VectorTypeConfig(
        overlap_constraints={("vd", "vs1"), ("vd", "vs2"), ("vs1", "vs2")},
        fixed_emul={"vd": 16},
        maskable=False,
        require_zero_vstart=True,
    ),
)
```

- **Register plan.**
  - C uses a 16-register window aligned to 16: base `v0` or `v16`. `format_mmacc` reserves all 16 registers before it
    places A and B.
  - [Spec] `EMUL_C` = VLEN/(SEW·λ²) can be 16 (spec:381-391). Only a base aligned to 16 fits every VLEN.
  - Integer rows allow A = B. FP rows keep A and B apart, so that an edge value in A meets the background of B.
  - [Spec] `vd` must not overlap `vs1` or `vs2`, regardless of VL (spec `5bcd3946`). An overlap raises an
    illegal-instruction exception. `cp_ime_vd_overlap` in `ExceptionsZvvm` tests it.
- **Setup.**
  - Load C as two m8 groups: `vsetvli x0, x0, e<SEW>, m8` and two `vle<SEW>.v` loads, the second at `+8·vlenb`.
  - Load A and B with `vle<SEW>.v` at LMUL and VL = VLMAX.
  - [Spec] With W>1, each `SEW` storage element holds W packed inputs in standard element order (spec:1027-1036).
  - Set `vtype` and VL with `load_ime_vtype`.
  - FP rows: `FMMACC` builds exact data (§5), then `handle_vector_fp` adds `fsrmi` and `fsflagsi 0`.
- **Test.** `vmmacc.vv vD, vS1, vS2`, assembled by the `.insn` macros in `tests/env/rvtest_experimental.h`.
- **Check.**
  - `vsetvli x0, x0, e<SEW>, m8, tu, mu`, then `write_sigupd_v_len(..., lmul=8, segments=2)` on the whole window.
  - Every element is a body element, so the check is exact. It also checks that the registers beyond `EMUL_C`, and the
    C tail columns, are unchanged.
  - FP rows also record `fflags` through `handle_vector_fp`.
- **Gate.** The λ condition of §1.4, plus the existing `UDB_ELEN` gate.

### 3.3 `FMMACC_MX` and `MMACC_MX` (vm=0) [Planned]

- They work like `FMMACC`, with these additions:
  - v0 holds the scales (`v0.scale`).
  - [Spec] `vd`, `vs1` and `vs2` must not overlap v0 (spec:5013, 5461). The C window is therefore based at `v16`.
  - `bs` selects block size 32 or 16. The row's `x` or `xn` prefix chooses it.
- A new `cp_scale` coverpoint loads E8M0 scale patterns into v0.
- Sail `0ebfc810` implements vm=0. It applies block scales exactly, as spec `324c62b7` requires.

### 3.4 `VLT` (`vmtl.v`, `vmttl.v`) and `VST` (`vmts.v`, `vmtts.v`)

[Impl] `tile_type.py`:

```python
vlt_config = InstructionTypeConfig(
    required_params={"vd", "rs1", "rs2"},
    instruction_class=["load"],
    vector_data=VectorTypeConfig(masked_constraints={("vd", "v0")}),
)
vst_config = InstructionTypeConfig(
    required_params={"vs3", "rs1", "rs2"},
    instruction_class=["store"],
    vector_data=VectorTypeConfig(),
)
```

- **Data.** All tile tests of one SEW share one random label, `ime_tile_data_e<SEW>`, of 16 registers at `VLEN_MAX`.
  Every LD is at most 2·linesize, so any tile fits in it.
- **Setup.**
  - Load the mask if the testcase is masked.
  - Fill the register group (`vd` or `vs3`) at VL = VLMAX.
  - `LA(rs1, data)`.
  - Load LD into `rs2` (see `cp_ld`, §4.1). [Spec] LD = 0, or `rs2 = x0`, selects the natural LD (spec:2278-2291).
    linesize = λ·LMUL is the natural LD of `vmtl.v` and `vmts.v`.
  - The natural LD of `vmttl.v` and `vmtts.v` is M = VLEN/(SEW·λ) (spec:2286). It depends on VLEN, so the setup
    computes it at run time as `vlenb >> log2(SEW·λ/8)`. Each λ branch loads its own shift.
  - Set `vtype` and VL with `load_ime_vtype`.
- **Test.** `vmtl.v vD, (xA), xL[, L<λ>][, v0.t]`.
- **Check (load).**
  - Re-issue `vsetvl` with the same VL and `vta=vma=0` (`keep_vl=True`).
  - `RVTEST_SIGUPD_V_LEN` on `vd` at the tile LMUL.
  - [Spec] A tile load leaves inactive and tail elements undisturbed, whatever `vta` and `vma` say (spec:2321).
  - [ACT] The macro relaxes the tail check when the saved `vtype.vta` is 1. Forcing `tu,mu` before the check keeps it
    strict.
- **Check (store).** Read back 2·LMUL registers of memory from `rs1` with `vle<SEW>.v` (two m8 groups at LMUL=8), then
  `RVTEST_SIGUPD_V_LEN`. The lines and the gaps between them are both checked.
- **Immediate λ.**
  - `vtype.lambda` holds a supported λ different from the immediate. The testcase is gated on both.
  - After the instruction, `csrr xT, vtype` and `RVTEST_SIGUPD` check that the immediate did not change `vtype.lambda`
    ([Spec] spec:2346-2349).
  - This replaces the ime-test-gen check, whose mask `0x3800…` reads the wrong bits (`ime-test-gen/src/expand_ir.rs`;
    report finding 1).
- **Transposition.** The formatter derives it from the mnemonic (`TRANSPOSING`).

### 3.5 Coverage

[Impl] Step 6 (commit `98595c2a5`) and earlier steps added:

- Sample templates `sample_MMACC.sv`, `sample_FMMACC.sv`, `sample_VLT.sv` and `sample_VST.sv`, and coverpoint templates
  under `generators/coverage/src/covergroupgen/templates/vector/` (privileged ones under `vector/priv/`).
- `vtype` fields `lambda`, `altfmt_a` and `altfmt_b` in `get_csr_val` (`framework/src/act/fcov/coverage/RISCV_coverage_csr.svh`).
- IME encodings in `framework/src/act/fcov/coverage/RISCV_decode_pkg.svh` and `framework/src/act/fcov/disassemble.svh`.
  riscv-opcodes has no IME encodings, so `RISCV_imported_decode_pkg.svh` cannot provide them.
- The coverage testbench compiles in pyslang (`reports/ime-poc/slang_check.py`). The coverage simulation has not run:
  no Questa or VCS is available, and Verilator is deferred.

## 4. Coverpoints, and the mapping of every ime-test-gen family

### 4.1 Coverpoints

Reused generators are found by prefix match. New generators are in `generators/testgen/src/testgen/coverpoints/vector/`.

| Column (cell)                                                                   | Generator                                       | Bins                                                                            |
| ------------------------------------------------------------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------- |
| `cp_asm_count` (x)                                                              | reuse                                           | one testcase                                                                    |
| `cp_vd` (`emul16`), MACC                                                        | reuse; template `cp_vd_emul16.sv`               | `vd` ∈ {v0, v16}                                                                |
| `cp_vs1`, `cp_vs2` (x), MACC; `cp_vd`, `cp_vs3` (x), tile                       | reuse                                           | register numbers                                                                |
| `cp_rs1` (`nx0`), `cp_rs2` (x), tile                                            | reuse                                           | base and LD registers; `rs2=x0` gives the natural LD                            |
| `cp_vd_edges` (`x` or `f`)                                                      | reuse                                           | C initial value: an edge in element 0                                           |
| `cp_vs1_edges`, `cp_vs2_edges` (`x`, `emulf2/4/8`, `f`, `f_emulf2/4`, `f_bf16`) | reuse; new `f_emulf*` tables in `data/edges.py` | an edge in narrow input element 0, packed                                       |
| `cp_altfmt` (x), integer MACC                                                   | `cp_altfmt.py`                                  | `ss`, `su`, `us`, `uu`                                                          |
| `cr_lambda_lmul` (x)                                                            | `cr_lambda_lmul.py`                             | `lambda_<λ>_lmul_<L>_vl_vlmax` for λ in `ime_lambdas(SEW)`, L ∈ {1,2,4,8}       |
| `cp_tile_vl` (x)                                                                | `cp_tile_vl.py`                                 | at LMUL=2: `vl_one_column`, `vl_half`, `vl_vlmax`, `vl_random`                  |
| `cp_ld` (x), tile                                                               | `cp_tile.py`                                    | `ld_x0`, `ld_zero` (0 in a register), `ld_tight`, `ld_padded` (+1), `ld_double` |
| `cp_imm_lambda` (x), tile                                                       | `cp_tile.py`                                    | `L<λ>` for λ in `ime_lambdas(SEW)`; background λ ≠ immediate λ                  |
| `cp_masking_edges` (x), tile                                                    | reuse                                           | the 5 standard mask edges                                                       |
| `cr_tile_vtype_agnostic` (x), tile loads                                        | `cp_tile.py`                                    | masked load at VL = VLMAX/2, vta × vma; the check stays strict                  |
| `cp_csr_frm` (`v`), FP                                                          | reuse                                           | the 5 dynamic rounding modes                                                    |
| `cp_csr_fflags` (`voun`), FP                                                    | reuse                                           | preset flag bits                                                                |
| `cp_fp_subdot` (x), FP rows with W>1                                            | `cp_fp_subdot.py`                               | `ulp_<rne\|rtz\|rdn\|rup\|rmm>` (§4.5)                                          |
| `cp_custom_tile_macc` (x), `vmmacc.vv` rows `Zvvi<n>mm:Zvvmtls`                 | `cp_custom_tile_macc.py`                        | `lmul<L>_lambda<λ>` (§4.3)                                                      |
| `cp_custom_tile_crossmode` (x), `Zvvmtls` rows of `Zvvmttls.csv`                | `cp_custom_tile_crossmode.py`                   | `lmul<L>_lambda<λ>_ld<nat\|pad>` (§4.3)                                         |
| `cp_custom_tile_layout`, `cp_custom_tile_roundtrip`                             | [Planned] step 3a                               | §4.4                                                                            |
| `cp_scale` (x), MX rows                                                         | [Planned]                                       | E8M0 edges in v0                                                                |

`cr_vl_lmul` and `cr_vtype_agnostic` are not reused. They sweep fractional LMUL and an unaligned random VL. [Spec]
Fractional LMUL is reserved for IME (spec:425), and VL must be a multiple of λ·LMUL, so both sweeps would trap.

### 4.2 Family mapping

Counts come from `ci/work/gen-asm-v512/tests.txt` of ime-test-gen (5372 IR tests at VLEN=512).

| ime-test-gen family                                                        | ACT location                                         | Status and notes                                                                                                |
| -------------------------------------------------------------------------- | ---------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| TC-LS-01 `vmtl→vmts`, TC-LS-02 `vmttl→vmtts` (part of 1952)                | `Zvvmtls`, `Zvvmttls`: each instruction alone        | Done: `cr_lambda_lmul`, `cp_tile_vl`, `cp_ld`. The round trip itself is the planned `cp_custom_tile_roundtrip`. |
| TC-LS-03/04: order-preserving load with transposing store, and the reverse | `cp_custom_tile_crossmode` in `Zvvmttls.csv`         | Done                                                                                                            |
| TC-LS-06 masked load (alternating)                                         | `cp_masking_edges` on all four tile instructions     | Done. ACT's 5 mask edges replace the alternating pattern.                                                       |
| TC-LS-07: vstart skips row 1                                               | `cp_ime_vstart` in `ExceptionsZvvm`                  | Done (`vstart_one`, `vstart_half`)                                                                              |
| TC-LS-08a: register v8                                                     | `cp_vd`/`cp_vs3`                                     | Done                                                                                                            |
| TC-VSE-03/04 address formula (576)                                         | `VST` window check and `cp_ld`                       | Done                                                                                                            |
| TC-TAIL-01/02 tail undisturbed (part of 576)                               | every `VLT` check; `cr_tile_vtype_agnostic`          | Done, with a strict check                                                                                       |
| TC-TAIL-04/05 masked undisturbed                                           | `cp_masking_edges` with the strict check             | Done                                                                                                            |
| TC-ILL-01/02 (480): immediate λ over background λ; vtype kept              | `cp_imm_lambda` and a vtype SIGUPD                   | Done. "ILL" means "immediate lambda", not illegal instruction.                                                  |
| TC-MACC-01..06: `vmmacc`, e32, SS/US/SU/UU, C zero or ramp                 | `vmmacc.vv` rows in `Zvvmm` at all 4 SEWs            | Done: `cr_lambda_lmul`, `cp_altfmt`, edges. The tile sequence is `cp_custom_tile_macc`. Planned: `ramp` bin.    |
| TC-MACC-09/10: `vwmmacc`/`vqmmacc`, all signs                              | `vwmmacc` and `vqmmacc` rows                         | Done, plus `emulf2/4` edges                                                                                     |
| (none)                                                                     | `v8wmmacc.vv`; Int4 rows                             | Done. ime-test-gen skips EEW<8.                                                                                 |
| TC-FMACC-F32/F64/F16/BF16                                                  | `vfmmacc.vv` rows in `Zvvfmm`                        | F16, F32, F64 done. W=1 BF16 planned.                                                                           |
| TC-MX16-01..04 (f16×bf16)                                                  | rows `Zvvfp16mm:Zvvbf16mm` etc.                      | Planned (mixed rows)                                                                                            |
| TC-FW-F16/BF16/F32, TC-FQ-F16/BF16                                         | `vfwmmacc.vv`, `vfqmmacc.vv` rows                    | Done                                                                                                            |
| TC-FMACC-E4M3/E5M2, TC-FP8-MX, TC-FW-E4M3/E5M2, TC-FQ-E4M3/E5M2            | OFP8 rows                                            | Planned; Sail has no OFP8                                                                                       |
| TC-RM-* (5 frm modes)                                                      | `cp_csr_frm_v`                                       | Column done. With exact data no rounding occurs; rounding-sensitive data is planned (§5).                       |
| TC-RND-*-TIE/OVF/UNF/CAN                                                   | FP edges                                             | Single-term forms through edges. Multi-term forms wait for profile parameters (§7).                             |
| TC-SUB-_, TC-SPL-_-NAN-A/B                                                 | FP edges                                             | Done. [Spec] A NaN result is the canonical NaN (spec:1680-1687).                                                |
| TC-FLAG-*                                                                  | `fflags` check in every FP testcase; `cp_csr_fflags` | Done                                                                                                            |
| TC-AS-LS, TC-MACC-AS, TC-FW-AS (`--as-loads`)                              | —                                                    | Dropped. Tile instructions move only SEW-wide storage elements (spec:2236-2240).                                |
| (none)                                                                     | microscaling rows                                    | Planned; needs Sail                                                                                             |

How the sweep dimensions carry over: VLEN is no longer a dimension, because tests are VLEN-agnostic and Sail runs at
the DUT's VLEN. SEW becomes the per-SEW suite. λ×LMUL becomes `cr_lambda_lmul`. Sign becomes `cp_altfmt`. VL mode
becomes `cp_tile_vl`. Stride becomes `cp_ld`. Mask becomes `cp_masking_edges`. Rounding mode becomes `cp_csr_frm_v`.
ime-test-gen crosses λ×LMUL×sign; ACT has one cross (λ×LMUL) and a single `cp_altfmt`.

### 4.3 Composed tile tests (implemented)

[ACT] `cp_custom_*` is how ACT tests a sequence that the plain formatter does not emit, for example `cp_custom_ffLS` in
`coverpoints/vector/cp_custom_vls.py`. A row that needs a second family extension uses an `ExtraExtensions` colon list
or a single extra extension.

`cp_custom_tile_crossmode` (commit `98595c2a5`):

- Rows: `vmttl.v` and `vmtts.v` with `ExtraExtensions=Zvvmtls` in `Zvvmttls.csv`. The labelled instruction is the
  transposing one.
- Sequence: `vmtl.v` then `vmtts.v` (TC-LS-03), or `vmttl.v` then `vmts.v` (TC-LS-04), at the same `vtype` and
  VL = VLMAX. The destination window then holds the transpose of the source tile.
- LD: natural (`x0`) or padded. Padded is linesize + 1 for the order-preserving instruction and M + 1 for the
  transposing one, with M computed from `vlenb`.
- Check: read back 2·LMUL registers of the destination with `vle<SEW>.v`. The gaps keep their values.
- Bins: `lmul<L>_lambda<λ>_ld<nat|pad>`.

`cp_custom_tile_macc` (commit `98595c2a5`):

- Rows: the four `vmmacc.vv` rows with `ExtraExtensions=Zvvi<n>mm:Zvvmtls` in `Zvvmm.csv`.
- Sequence: zero the C window `v16-v31`; `vmtl.v` A into `v0` and B into `v8` with the natural LD; `vmmacc.vv`; store C
  with `vmts.v` at LMUL = `EMUL_C` and LD = M. `EMUL_C` depends on VLEN, so an `#if UDB_VLEN == …` chain over 128,
  256, 512 and 1024 selects the store. `EMUL_C` = 16 uses two LMUL=8 stores.
- Data: with K = λ·LMUL ≥ 2, A[i] = (i, 1, 0, …) and B_tile[j] = (f, j, 0, …), so C[i][j] = f·i + j names its row and
  column. f is 256, or 16 at SEW=8. With K = 1, A[i] = 1 and B_tile[j] = j, so C[i][j] = j.
- Check: read back 16 registers of the C destination and `RVTEST_SIGUPD_V_LEN`.
- Bins: `lmul<L>_lambda<λ>`.

### 4.4 Step 3a: layout and round-trip conformance tests (optional)

These tests check that a tile load or store places tile element i at register element
`tile_reg_idx(i, LMUL, λ, VLEN/SEW)`. They name each element, so a wrong placement is readable from the signature. The
Sail tile-index bug that motivated them is fixed by `a545cc41`, so they are now ordinary conformance tests.

- `cp_custom_tile_layout` on all four tile instructions. Load: fill `vd` with a sentinel, load a ramp (element k holds
  k mod 2^SEW), check `vd`. Store: `vid.v vs3`, store, read the window back. Bins `lmul<L>_lambda<λ>_ld<nat|pad>`.
- `cp_custom_tile_roundtrip` on `vmts.v` and `vmtts.v`. `same_*` bins reproduce TC-LS-01/02. `mixed_*` bins store with
  an immediate λ' ≠ the load λ. A same-geometry round trip cannot detect a wrong mapping, because the load and the store
  apply the same mapping. The `mixed` bins can, at LMUL>1.
- Implementation: register the ramp with `TestData.register_vector_data(…, elements=[…])`; gate `mixed` bins on both λ
  macros.

### 4.5 W>1 partial sum (QEMU deviation)

- [Spec] For W>1, the W products of a sub-dot-product form a partial sum S. C is updated once per group with
  round_frm(C + S) (spec:1352-1412; `fp_group_sum` and `fp_gemm` at spec:4446-4490 and 4677-4716).
- [Sail] Fixed. The old fork added each product into C on its own (finding 30). `ime_fp_group_sum` now sums the W
  products exactly and rounds once.
- [QEMU] The SDK QEMU still adds each product into C on its own. No (G, psm, rnd) tuple describes the result.
- [Impl] `cp_fp_subdot` on the unscaled W>1 rows. In one sub-dot-product of C[0][0], W equal exact products add up to
  one ULP of C₀. All other products are zero. One bin per `frm` value.

| (SEW, W)             | A, B per lane | C₀   | Specification and Sail | QEMU                     |
| -------------------- | ------------- | ---- | ---------------------- | ------------------------ |
| (32, 2) FP16 or BF16 | 2^-12, 2^-12  | 1.0  | `0x3f800001`, no flags | `0x3f800000`, NX         |
| (64, 2) FP32         | 2^-26, 2^-27  | 1.0  | `0x3ff0000000000001`   | `0x3ff0000000000000`, NX |
| (64, 4) FP16 or BF16 | 0.5, 0.5      | 2^52 | `0x4330000000000001`   | `0x4330000000000000`, NX |

- [Inferred] The specification result does not depend on any permitted choice. S is exact and representable, G does
  not matter because other sub-dot-products are zero, and C₀ + S is exact in every `frm`. [Uncertain] A psm=1
  reduction is expected to be exact on W equal powers of two.
- Outcome: Sail writes the specification result into the signature. QEMU fails these bins until it is fixed. The
  bins stay in place.

## 5. Value patterns

- [ACT] Operands come from seeded random data. The seed is a hash of the instruction and the coverpoint.
- [ACT] Edge coverpoints put one edge value in element 0 and fill the rest.

Integer rows:

- [Impl] ACT random data. Integer accumulation wraps modulo 2^SEW, so every result is exact ([Spec] spec:1112).
- [Impl] Narrow inputs use the `emulf2/4/8` edge path. `ime_extend_label` packs narrow elements, including 4-bit ones,
  into SEW storage elements.
- [Planned] A `ramp` edge bin with positional values `r·cols + k + 1`, after ime-test-gen.

FP rows:

- [Spec] The FP result depends on the (G, psm, rnd) profile. The profile is implementation-defined per (SEW, W, λ), and
  the implementation must publish it (spec:1376-1460). C ← round_frm(C + S) for each group sum S.
- [UDB] The profile is disclosed per (SEW, W, λ) in `ZVVM_FP_{GROUPING,PSM,RND}_SEW<s>_W<w>`. UDB emits macros such
  as `UDB_ZVVM_FP_RND_SEW32_W2_IDX0_FRM` and `UDB_ZVVM_FP_PSM_SEW32_W2_MASK`.
- [Decision] Default data gives the same result for every permitted profile and needs no gate. Profile-dependent
  data is generated for Sail's profile (G=1, psm=0, rnd=frm) and gated on it.
- [Impl] `fp_exact_data` in `mmacc_type.py`:
  - A and B inputs are sparse integers in [−2, 2], packed W per storage element.
  - C holds half-integers k + 0.5 with |k| ≤ 128, so no C value is zero.
  - A dot product has at most λ·W·LMUL ≤ 64 terms at fp16, so every running sum stays below 512 in magnitude. Every
    value is then exact in fp16, bf16 (inputs), fp32 and fp64, in any order.
  - A BF16 C has 8 significant bits. Its rows use inputs in [−1, 1] and |k| ≤ 31, so every sum stays below 96.
- [Impl] `cp_fp_rnd`: the products of C[0][0] give a group sum S that is not exact in the C format, while C₀ + S is.
  The rnd=frm and rnd=xct results then differ in every `frm`. Gated on rnd=frm and psm=0.
- [Impl] FP edges (`fp_edge_data`): the edge sits in element 0 of its operand. An A edge meets B = +1.0 and an A
  background of 0. A B edge is symmetric. A C edge meets A = B = 0. Each affected C element then has one nonzero
  product, which equals the edge. Every implementation computes round_frm(C₀ + edge).
- [Impl] BF16 inputs set `altfmt_A = altfmt_B = 1`. A BF16 C sets `altfmt = 1` (`vtype[8]`).
- Consequence: the random and edge data never round inside the sum. They do not see the W>1 per-product deviation;
  `cp_fp_subdot` targets it (§4.5). They also do not exercise `frm`.
- [Planned] Rounding-sensitive data for `cp_csr_frm_v`: an exact product p and a C₀ chosen so that C₀ + p rounds,
  ties, overflows or underflows. The only rounding is then the final round_frm(C₀ + S). For W=1 the product must be
  exact, because an inexact W=1 product gives different results on QEMU (rnd=xct) and Sail (rnd=frm).
- [Planned] More profile-dependent data, gated like `cp_fp_rnd`: inexact products, cancellation across k, and
  accumulation order.

## 6. Expected values come from Sail

- [ACT] The signature ELF stores Sail's results. The self-checking ELF compares against them.
- Nothing reads `C_ref`, `*.golden.json` or any array from ime-test-gen `gold/`. The ime-test-gen checks map as
  follows: `Compare` → `RVTEST_SIGUPD_V_LEN`; `CheckFflags` → `fflags` SIGUPD; `CheckVtypeField` → `csrr vtype` plus
  `RVTEST_SIGUPD`.
- The Rust golden model stays outside ACT. Its differences from Sail or QEMU are findings only.

### 6.1 FP rounding profiles of QEMU, Sail and the Rust model

- [Spec] Legal values: G a power of two with 1 ≤ G ≤ λ (spec:1352-1384). psm ∈ {0, 1} (spec:1386-1397). rnd ∈ {frm,
  rto, xct} (spec:1399-1412). One tuple per (SEW, W, λ) (spec:1449-1466).

| Rows               | SDK QEMU `d856b96`                                                          | Sail                                               | `ime-test-gen --fma`                                     |
| ------------------ | --------------------------------------------------------------------------- | -------------------------------------------------- | -------------------------------------------------------- |
| W=1, same format   | fused: G=1, psm=0, rnd=xct. Legal.                                          | `fp_mul` + `fp_add`: G=1, psm=0, rnd=frm. Legal.   | same as QEMU                                             |
| W=1, mixed formats | `float32_muladd`, then conversion: two roundings. DUT finding.              | implemented; not tested by ACT yet                 | one rounding                                             |
| W>1                | one fused add into C per product. Fits no tuple: DUT finding.               | exact group sum, one rounding: G=1, psm=0, rnd=frm | same as QEMU, except narrow inputs into f64 round to f32 |
| Microscaled        | f32 scale, per-product rounding over a block, fused scale-add. DUT finding. | exact block scales; not tested by ACT yet          | not generated                                            |

- On W=1 rows, QEMU and Sail differ when a product is inexact in the C format. Both are permitted, so the data of §5
  avoids such products.
- [Inferred] Flags can differ when a bf16 product underflows f32 and C ≠ 0: Sail's `fp_mul` raises UF, and QEMU does
  not.

## 7. What does not fit, and its handling

| Item                                      | Problem                                                                                                                                                      | Handling                                                                                                                                                                                                |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| VLEN > 1024                               | [ACT] `RVTEST_VLEN_MAX` is 1024. ime-test-gen CI runs up to VLEN 32768.                                                                                      | Keep the cap. `ime_lambdas` drops λ that need VLEN > 1024. Raising the cap is a separate change for all of ACT.                                                                                         |
| `LambdaProbe`, `known-issues.txt`         | ACT has no run-time skip and no verdict list.                                                                                                                | λ gating (§1.4). Per-DUT `exclude_extensions` in `config/<dut>/ci.yaml`.                                                                                                                                |
| C tile tail with `vta=1`                  | [Spec] The tail may hold any value (spec:2600-2624). The ACT macro accepts only "unchanged" or "all ones", and its tail is one-dimensional.                  | MACC tests use `vta=0`. A `vta=1` bin with a partial VL needs a two-dimensional tail check.                                                                                                             |
| FP profile (G, psm, rnd)                  | Implementation-defined per (SEW, W, λ). UDB discloses it in `ZVVM_FP_*` parameters.                                                                          | Data that does not depend on the choice (§5). Profile-dependent testcases (`cp_fp_rnd`) are generated for Sail's profile and gated on the `UDB_ZVVM_FP_*` macros.                                       |
| OFP8, OFP4, microscaling                  | Sail `0ebfc810` implements them, except the OFP8-accumulator rows (pending branch `cgomez/ime-ofp8-acc`).                                                    | Rows are planned (HANDOFF §8). Tests for OFP8-accumulator rows are set aside (udb-0.9.0.md).                                                                                                            |
| `Zvvmttls` on QEMU                        | The SDK QEMU does not decode `vmttl.v` and `vmtts.v`.                                                                                                        | `qemu-ime-rv64` does not list `Zvvmttls`. The suite runs with Sail as DUT.                                                                                                                              |
| QEMU W>1 FP accumulation                  | QEMU adds each product into C on its own (§4.5).                                                                                                             | `cp_fp_subdot` bins follow the specification and fail on QEMU.                                                                                                                                          |
| Sail accepts λ with `EMUL_C` < 1          | The old Sail accepted any λ ≤ VLEN/SEW. Not rechecked in `0ebfc810`. The specification forbids `EMUL_C` < 1 (spec:811-815).                                  | UDB λ lists follow the specification, so positive tests never use such a λ. `cp_ime_imm_lambda_unsupported` uses L64, which no VLEN ≤ 1024 supports.                                                    |
| Tile and MACC VL not a multiple of λ·LMUL | Spec `main` makes it illegal for both. The ARC review draft makes every 0 ≤ VL ≤ VLMAX legal for tile loads and stores, and makes it reserved for MACC.      | `cp_ime_vl_not_multiple` in `ExceptionsZvvm` follows spec `main` and expects a trap. Review these bins when the draft merges: tile bins become legal partial-line transfers; MACC bins become reserved. |
| `altfmt` for FP output                    | IME uses the Zvfbfa `altfmt` bit, `vtype[8]`. The spec lists only Zve32f as a dependency of `Zvvbf16mm`. Sail `0ebfc810` writes the bit when IME is enabled. | Rows do not require Zvfbfa. The SDK QEMU reserves the bit without `x-zvfbfa=true`, so its `Zvvbf16mm` tests fail (QEMU deviation).                                                                      |
| RV32                                      | ime-test-gen and the SDK QEMU support only RV64.                                                                                                             | CSVs set `RV32=x`, and `ime_vtype_value` computes the fields per XLEN. No RV32 configuration exists, so RV32 has not run.                                                                               |

`ExceptionsZvvm` (step 7, commit `98595c2a5`, `priv/extensions/ExceptionsZvvm.py`):

| Coverpoint                      | Rows                        | Case                                                                   |
| ------------------------------- | --------------------------- | ---------------------------------------------------------------------- |
| `cp_vill`                       | all                         | `vtype.vill = 1`                                                       |
| `cp_ime_vstart`                 | all                         | MACC: `vstart = 1` traps. Tile: `vstart_one`, `vstart_half` resume.    |
| `cp_ime_vl_not_multiple`        | all                         | VL = 1 at LMUL = 2 (ARC draft review needed, see above)                |
| `cp_ime_lmul_fractional`        | all                         | LMUL = 1/2                                                             |
| `cp_ime_vd_misaligned`          | all                         | MACC: `vd = v17` per λ with `EMUL_C` ≥ 2. Tile: odd group at LMUL = 2. |
| `cp_ime_vs1_misaligned`, `_vs2` | MACC                        | odd group at LMUL = 2                                                  |
| `cp_ime_vd_overlap`             | MACC                        | `vs1`/`vs2` at the base of C, `vs2` at the last register of C, VL = 0  |
| `cp_ime_vm0`                    | `vmmacc.vv`, `vfmmacc.vv`   | vm = 0 on an instruction with no microscaled form                      |
| `cp_ime_reserved_sew`           | `vqmmacc.vv`, `v8wmmacc.vv` | a reserved encoding-map SEW                                            |
| `cp_ime_masked_vd_v0`           | `vmtl.v`, `vmttl.v`         | masked tile load into `v0`                                             |
| `cp_ime_imm_lambda_unsupported` | tile                        | immediate L64, guarded by `!defined(UDB_SUPPORTED_LAMBDA_SEW<n>_64)`   |

Each trap case is guarded by its row's type extension, by ELEN and by the supported λ values.

## 8. Testplans as implemented

The CSVs are the source. Headers and representative rows at `59666b161`:

`testplans/Zvvmm.csv` (13 integer rows, then 4 `cp_custom_tile_macc` rows):

```csv
Instruction,Type,RV32,RV64,ExtraExtensions,EFFEW8,EFFEW16,EFFEW32,EFFEW64,cp_asm_count,cp_vd,cp_vs1,cp_vs2,cp_vd_edges,cp_vs1_edges,cp_vs2_edges,cp_altfmt,cr_lambda_lmul,cp_tile_vl,cp_custom_tile_macc
vmmacc.vv,MMACC,x,x,Zvvi8mm,x,,,,x,emul16,x,x,x,x,x,x,x,x,
vwmmacc.vv,MMACC,x,x,Zvvi4i8mm,x,,,,x,emul16,x,x,x,emulf2,emulf2,x,x,x,
vqmmacc.vv,MMACC,x,x,Zvvi8i32mm,,,x,,x,emul16,x,x,x,emulf4,emulf4,x,x,x,
v8wmmacc.vv,MMACC,x,x,Zvvi4i32mm,,,x,,x,emul16,x,x,x,emulf8,emulf8,x,x,x,
vmmacc.vv,MMACC,x,x,Zvvi32mm:Zvvmtls,,,x,,,,,,,,,,,,x
```

`testplans/Zvvfmm.csv` (complete):

```csv
Instruction,Type,RV32,RV64,ExtraExtensions,EFFEW8,EFFEW16,EFFEW32,EFFEW64,cp_asm_count,cp_vd,cp_vs1,cp_vs2,cr_lambda_lmul,cp_tile_vl,cp_vd_edges,cp_vs1_edges,cp_vs2_edges,cp_csr_frm,cp_csr_fflags,cp_fp_subdot,cp_fp_rnd
vfmmacc.vv,FMMACC,x,x,Zvvfp16mm,,x,,,x,emul16,x,x,x,x,f,f,f,v,voun,,x
vfmmacc.vv,FMMACC,x,x,Zvvbf16mm,,x,,,x,emul16,x,x,x,x,f_bf16,f_bf16,f_bf16,v,voun,,x
vfmmacc.vv,FMMACC,x,x,Zvvfp32mm,,,x,,x,emul16,x,x,x,x,f,f,f,v,voun,,x
vfmmacc.vv,FMMACC,x,x,Zvvfp64mm,,,,x,x,emul16,x,x,x,x,f,f,f,v,voun,,x
vfwmmacc.vv,FMMACC,x,x,Zvvfp16fp32mm,,,x,,x,emul16,x,x,x,x,f,f_emulf2,f_emulf2,v,voun,x,x
vfwmmacc.vv,FMMACC,x,x,Zvvbf16fp32mm,,,x,,x,emul16,x,x,x,x,f,f_bf16,f_bf16,v,voun,x,x
vfwmmacc.vv,FMMACC,x,x,Zvvfp32fp64mm,,,,x,x,emul16,x,x,x,x,f,f_emulf2,f_emulf2,v,voun,x,x
vfqmmacc.vv,FMMACC,x,x,Zvvfp16fp64mm,,,,x,x,emul16,x,x,x,x,f,f_emulf4,f_emulf4,v,voun,x,x
vfqmmacc.vv,FMMACC,x,x,Zvvbf16fp64mm,,,,x,x,emul16,x,x,x,x,f,f_bf16,f_bf16,v,voun,x,x
```

`testplans/Zvvmtls.csv` (complete; no `ExtraExtensions` column):

```csv
Instruction,Type,RV32,RV64,EFFEW8,EFFEW16,EFFEW32,EFFEW64,cp_asm_count,cp_vd,cp_vs3,cp_rs1,cp_rs2,cp_ld,cp_imm_lambda,cp_masking_edges,cr_lambda_lmul,cp_tile_vl,cr_tile_vtype_agnostic
vmtl.v,VLT,x,x,x,x,x,x,x,x,,nx0,x,x,x,x,x,x,x
vmts.v,VST,x,x,x,x,x,x,x,,x,nx0,x,x,x,x,x,x,
```

`testplans/Zvvmttls.csv` (complete):

```csv
Instruction,Type,RV32,RV64,ExtraExtensions,EFFEW8,EFFEW16,EFFEW32,EFFEW64,cp_asm_count,cp_vd,cp_vs3,cp_rs1,cp_rs2,cp_ld,cp_imm_lambda,cp_masking_edges,cr_lambda_lmul,cp_tile_vl,cr_tile_vtype_agnostic,cp_custom_tile_crossmode
vmttl.v,VLT,x,x,,x,x,x,x,x,x,,nx0,x,x,x,x,x,x,x,
vmtts.v,VST,x,x,,x,x,x,x,x,,x,nx0,x,x,x,x,x,x,,
vmttl.v,VLT,x,x,Zvvmtls,x,x,x,x,,,,,,,,,,,,x
vmtts.v,VST,x,x,Zvvmtls,x,x,x,x,,,,,,,,,,,,x
```

`testplans/priv/ExceptionsZvvm.csv` has one row per mnemonic and the coverpoints of the table in §7.

Step 3a adds `cp_custom_tile_layout` to both tile CSVs and `cp_custom_tile_roundtrip` to the store rows.

### 8.1 One generated testcase

From `tests/rv64i/Zvvmm32/Zvvmm32Zvvi32mm-vmmacc.vv-00.S`, bin `cr_lambda_lmul` with λ=2, LMUL=2, VL = VLMAX. The two
`RVTEST_SIGUPD_V_LEN` lines are shortened.

```asm
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I', 'Zvvmm', 'Zvvi32mm', 'Zve32x']
# params:
#   MXLEN: 64
# MARCH: rv64i_zicsr_zifencei_zve32x_zvvi32mm_zvvmm
##### END_TEST_CONFIG #####
…
# Testcase cr_lambda_lmul (Test lambda = 2, lmul = 2, vl = vlmax)
#if defined(UDB_SUPPORTED_LAMBDA_SEW32_2)
# C window v0-v15: two m8 loads
  vsetvli x13, x0, e32, m8, tu, mu
  LA (x13, vd_random_length_111)
  vle32.v v0, (x13)
  csrr x18, vlenb
  slli x18, x18, 3
  add x13, x13, x18
  vle32.v v8, (x13)
# A (vs1 = v30) and B (vs2 = v28) at LMUL=2, VL=VLMAX
  vsetvli x13, x0, e32, m2, tu, mu
  LA (x13, vs1_random_length_111)
  vle32.v v30, (x13)
  LA (x13, vs2_random_length_111)
  vle32.v v28, (x13)
# vtype: lambda=2, altfmt_A=0, altfmt_B=0, vma=0, vta=0, vsew=e32, vlmul=m2, VL=vlmax
  LI(x29, 0x2000000000000011)
  vsetvl x13, x0, x29
Zvvmm32Zvvi32mm_vmmacc_vv_cg_cr_lambda_lmul_lambda_2_lmul_2_vl_vlmax:
  vmmacc.vv v0, v30, v28
# Check the C window at e32, m8, VL=VLMAX. vta=0, so elements beyond VL are unchanged
  vsetvli x13, x0, e32, m8, tu, mu
  RVTEST_SIGUPD_V_LEN(x2, x5, x4, x6, x20, v16, v28, v29, v31, v0, v30, v0, 0, 0, 0, 32, 8, 0, 0, …)
  RVTEST_SIGUPD_V_LEN(x2, x5, x4, x6, x20, v16, v28, v29, v31, v8, v30, v0, 0, 0, 0, 32, 8, 0, 0, …)
#endif
```

- On `qemu-ime-rv64` (VLEN=256), SEW=32 with λ=2 gives M=4 and `EMUL_C`=2. C occupies v0-v1. The check also verifies
  that v2-v15 kept their initial values.
- `vsetvli` at `e32` keeps λ=2. [Spec] A change of LMUL alone does not change λ (spec:741).
- [Uncertain] On its slow mask path, `RVTEST_SIGUPD_V_LEN` switches to `e8`, which re-evaluates λ for SEW=8. The next
  testcase sets `vtype` again, so this is harmless.

## 9. Status

| #   | Step                                                                                                                 | Status                                                                  |
| --- | -------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| 0   | IME definitions (65 `Zvv*` extensions, `SUPPORTED_LAMBDA_SEW*`); `.insn` macros; `config/ime/qemu-ime-rv64`          | done: `98595c2a5`, `8ada25d12`; UDB instead of the overlay: `49b999ce9` |
| 1   | Slice 1: `Zvvmm.csv` first row, `MMACC`, `cr_lambda_lmul`, `fixed_emul`, `load_ime_vtype`, λ gate; covergroupgen fix | done: `0bb9717a4`, `98595c2a5`                                          |
| 2   | All 13 integer rows; `cp_vd_emul16`, `cp_vs1/2`, `cp_altfmt`, edges, `cp_tile_vl`                                    | done: `98595c2a5`. Open: `ramp` bin.                                    |
| 3   | `Zvvmtls.csv`: `VLT`, `VST`, `cp_ld`, `cp_imm_lambda`, `cr_tile_vtype_agnostic`                                      | done: `98595c2a5`                                                       |
| 3a  | `cp_custom_tile_layout`, `cp_custom_tile_roundtrip` (§4.4)                                                           | open, optional                                                          |
| 3b  | `cp_custom_tile_macc` and the four `Zvvi<n>mm:Zvvmtls` rows                                                          | done: `98595c2a5`                                                       |
| 4   | `Zvvfmm.csv`, `FMMACC`, exact FP data, FP edges, `cp_csr_frm_v`, `cp_csr_fflags`, `cp_fp_subdot`                     | done: `98595c2a5`                                                       |
| 4b  | W=1 BF16 (`Zvvbf16mm`)                                                                                               | done: `59666b161`                                                       |
| 4c  | Mixed FP16/BF16 rows, FP `cp_altfmt` bins; `vf8wmmacc.vv` rows; rounding-sensitive data for `cp_csr_frm_v`           | open                                                                    |
| 5   | `Zvvmttls.csv`, run-time natural LD, `cp_custom_tile_crossmode`                                                      | done: `98595c2a5`                                                       |
| 6   | Coverage: IME decode, `vtype` fields, templates                                                                      | done: `98595c2a5`. Open: `altfmt` filtering; simulation run.            |
| 7   | `ExceptionsZvvm` privileged suite; `cp_ime_vd_overlap`                                                               | done: `98595c2a5`, `413966b5a`                                          |
| 8   | FP profile disclosure and `cp_fp_rnd`                                                                                | done: `49b999ce9`, `aaa0c329c`                                          |
| 9   | OFP8, OFP4, microscaling rows; `cp_scale`; `FMMACC_MX`, `MMACC_MX`                                                   | open: HANDOFF §8, steps 4.2 and 4.3                                     |
| —   | PR to `act4`                                                                                                         | open; needs approval to push                                            |

Results and DUT deviations are in HANDOFF §7.

## 10. Open questions

1. Which FP profile does the target implementation disclose for each (SEW, W, λ)? If an entry uses `psm=1`, which
   reduction algorithm does it disclose?
2. Does the Sail fork support RV32? No RV32 configuration has been run.
3. When the ARC review draft merges, the `ExceptionsZvvm` VL bins and the λ/KLEN naming must be updated (§7).

Answered: λ selection per testcase (§1.4, 2026-10-27); source of truth (§0.1, 2026-10-27); G=1 for the target
(2026-10-27); W>1 partial sum formed before C is updated (§4.5); `vd` must not overlap `vs1`/`vs2` (spec `5bcd3946`);
FP profile disclosure through UDB (§5); `altfmt` without Zvfbfa (§7, 2026-11-19).
