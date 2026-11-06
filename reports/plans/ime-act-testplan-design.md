# Proposal: the ime-test-gen plan as ACT testplans (option C)

Design only. This file is the testplan design behind Report 2, Section 16b. Sources and commits:

- ACT: `riscv-arch-test` branch `cgomez/import-ime-tests-to-act4` at `394462f26`. Paths are relative to that repository unless they start with `ime-test-gen/` (riscv-ime-arch-tests `46f3781`), `sail/` (Sail fork `c69e3e22`), `qemu/` (`Openchip-Software/riscv-ime-qemu` branch `vrull/ime-wip` at `d856b96`, which is also the SDK QEMU pin) or `spec:` (integrated-matrix.adoc at `6effbcae`, still the head of `main` on 2026-10-27).
- Sail fork citations for the source-of-truth decisions are `sail/model/extensions/IME/…`, `sail/model/extensions/V/…` and `sail/model/core/extensions.sail` at `c69e3e22`, read on 2026-10-27.
- Tags: **[Spec]** = specification requirement. **[ACT]** = existing ACT convention or code. **[Proposal]** = this design. **[Uncertain]** = not verified. **[Decision]** = project decision of 2026-10-27. **[Inferred]** = derived from code or the specification, not run.
- Two experiments ran in the scratchpad, with no repository change: `testgen` and `covergroupgen` on a copy of `Zvbc.csv` with an `ExtraExtensions` column (§1.3).
- An FP probe (now `reports/issues/sail-ime-wmmacc-partial-sum/fprnd.c`) ran `vfmmacc.vv` and `vfwmmacc.vv` on the SDK QEMU and on Sail `c69e3e22` (§6.1).
- The values in §4.4 for configurations other than the reproducer's three steps were computed from the specification's `tile_reg_idx` and the flat index of Sail `c69e3e22`. The same model reproduces `sail.out` and `qemu.out` of the reproducer (`riscv-arch-test-docs/reports/issues/sail-ime-tile-ls-index/`).

Revision of 2026-10-27. The project decided:

1. λ is gated per testcase (§1.4). Selection in the header is not pursued.
2. Round-trip tests are kept, as extra bins (§4.3). Additional tests detect a tile load or store that uses the wrong register-element mapping (§4.4).
3. The target implementation uses G=1; its `psm` and `rnd` are not disclosed (§5). The SDK QEMU and Sail use different, partly non-conforming profiles (§6.1).
4. **Source of truth** (§0.1). The IME specification decides conflicts. The Sail fork decides where the specification is silent or ambiguous. QEMU, the SDK GCC and the Rust golden model never decide.

Consequences of decision 4 in this revision:

- W>1 FP accumulation: Sail contradicts the specification. New `cp_fp_subdot` bins follow the specification and fail until the Sail fix (§4.5).
- An FP output with `altfmt=1` needs Zvfbfa: spec silent; Sail behaviour (§7).
- The MACC `vd`/`vs1`/`vs2` overlap needs a user decision. The specification is silent, Sail allows overlap, and the project earlier said `vd` cannot overlap. The non-overlap constraint stays until the user decides (§3.2, §10).
- λ legality, `EMUL_C`=16 and LD = 0 in a register: Sail contradicts the specification; the bins follow the specification (§7).

## 0. Summary

- Four unprivileged CSVs, one per family extension: `Zvvmm.csv`, `Zvvfmm.csv`, `Zvvmtls.csv` and `Zvvmttls.csv`. Illegal-instruction and `vstart` cases go in a later privileged suite, `testplans/priv/ExceptionsZvvm.csv`, following `ExceptionsVx`.
- One row per (mnemonic, type extension). The type extension goes in `ExtraExtensions`, and the `EFFEW<n>` columns give the accumulator SEW. Testgen already handles `ExtraExtensions` in a vector suite. Covergroupgen needs a fix of about 5 lines.
- λ is gated per testcase with `#if defined(UDB_SUPPORTED_LAMBDA_SEW<n>_<λ>)`. UDB already emits these macros from the overlay parameters. The header names no λ, and no file is split by λ.
- MACC tests load A, B and C with `vle<SEW>.v`. They check the C register window with `RVTEST_SIGUPD_V_LEN`. They do not use `vmtl.v` or `vmts.v`. As a result, the MACC suites are VLEN-agnostic and are not affected by the Sail tile-index bug. `vd` never overlaps `vs1` or `vs2`. That constraint stays until the user decides the open question of §10.
- Tile load and store tests check the destination register group for loads, and a memory window read back with `vle` for stores. Each instruction is first tested alone.
- Four `cp_custom_tile_*` coverpoints add composed sequences (§4.3, §4.4):
  - `cp_custom_tile_layout`: a tile load checked through the register group, and a tile store fed by `vid.v`, with data that names each element.
  - `cp_custom_tile_roundtrip`: the ime-test-gen round trips TC-LS-01/02, plus a pair whose load and store use different λ.
  - `cp_custom_tile_crossmode`: the transposing pairs TC-LS-03/04.
  - `cp_custom_tile_macc`: `vmmacc.vv` with A and B loaded by `vmtl.v` and C stored by `vmts.v`, as ime-test-gen does.
- A same-geometry round trip, and a cross-mode pair, cancel the Sail tile-index error. The layout, mixed-λ and MACC bins detect it at LMUL>1. At the reproducer configuration (VLEN=256, SEW=32, LMUL=2, λ=1), 14 of 16 checked elements differ from a conforming DUT.
- Expected values come from Sail. Until the Sail fix lands, these bins fail on a conforming DUT such as QEMU. That failure is the intended signal, and the bins stay in place (§0.1).
- FP data is integer-valued and exactly representable, after the `unordered_sum_rng` precedent. Rounding-sensitive edge cases put the only rounding into the final accumulation step. The results then depend neither on `psm` nor on `rnd`, which the specification leaves to the implementation. G=1 is confirmed and matches Sail. The SDK QEMU is rnd=xct for W=1, and Sail is rnd=frm; both are permitted.
- For W>1, Sail and QEMU add each product into C on its own, which no (G, psm, rnd) tuple describes. That is a Sail bug. A new `cp_fp_subdot` column has W products that add up to one ULP of C₀. Its bins follow the specification and fail on a conforming DUT until Sail is fixed (§4.5). Tests that depend on the disclosed tuple wait for `psm` and `rnd` parameters.
- No new check macro is needed. Test selection and the build in `act` need no change. Every framework change has a precedent in an earlier extension (§9).
- Smallest end-to-end slice: `vmmacc.vv` with `Zvvi32mm` at SEW=32, with coverpoints `cp_asm_count` and `cr_lambda_lmul`, run on `qemu-ime-rv64`. It can pass on QEMU before the Sail tile-index fix lands.

### 0.1 Source of truth (decided 2026-10-27)

When implementations or documents conflict, the IME specification decides. Where the specification is silent or ambiguous, the IME Sail fork decides. QEMU, the SDK GCC and the Rust golden model never decide a conflict.

- **Sail contradicts the specification:** Sail is wrong. The bins follow the specification and stay in place, with no `ignore_bins` and no exclusion. Their expected values come from Sail, so they embed Sail's wrong values and fail on a conforming DUT until Sail is fixed. Each case has a Sail issue or work item. The tile-index bug (§4.4) and the W>1 partial sum (§4.5) are handled this way.
- **The specification permits several behaviours**, for example rnd ∈ {frm, rto, xct}: tests do not depend on the choice (§5).
- **The specification is silent:** tests follow the Sail code, and the design records "spec silent; Sail behaviour" with a code citation.

| Conflict                                                                             | Basis                                                       | Resolution                                                                                                              |
| ------------------------------------------------------------------------------------ | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| C-tile layout (tile-index bug)                                                       | Sail contradicts the specification                          | Bins follow the specification and fail until the Sail fix (§4.4).                                                       |
| W>1 FP accumulation                                                                  | Sail and QEMU contradict the specification (spec:1352-1412) | `cp_fp_subdot` bins follow the specification and fail on a conforming DUT until the Sail fix (§4.5). QEMU: DUT finding. |
| W=1 FP rounding: Sail rnd=frm, QEMU rnd=xct                                          | The specification permits both                              | Not a conflict. W=1 data keeps products exact (§5).                                                                     |
| MACC `vd` overlap with `vs1`/`vs2`                                                   | Spec silent; Sail allows overlap and computes in place      | Open: user decision (§3.2, §10).                                                                                        |
| `altfmt=1` for an FP output without Zvfbfa                                           | Spec silent; in Sail, `vtype` bit 8 is reserved             | Rows with BF16 or E5M2 output require Zvfbfa (§7).                                                                      |
| λ legality; `EMUL_C`=16                                                              | Sail contradicts the specification (spec:811-815)           | UDB λ lists follow the specification. `EMUL_C`=16 bins fail until the Sail fix (§7).                                    |
| LD = 0 in a register other than `x0`                                                 | Sail contradicts the specification (spec:2278-2291)         | The `cp_ld` bin follows the specification and fails until the Sail fix (§3.4).                                          |
| W=4 mnemonics                                                                        | GCC and QEMU names differ from the specification            | Specification names in the CSVs; GCC names only as macro aliases (§2.2).                                                |
| Family and type extension direction                                                  | ime-test-gen differs from the specification                 | The overlay direction holds (§1.3).                                                                                     |
| `zvmma`, `zvvxofp8mm`, `zvvxnofp8mm`                                                 | GCC-only names                                              | Not used in ACT.                                                                                                        |
| QEMU microscaling and mixed-format paths; the golden model's `--fma` internal format | Not sources of truth                                        | Findings only (§6.1).                                                                                                   |

## 1. Suite split and extension requirements

### 1.1 How ACT derives requirements

- [ACT] The testplan file name (without `.csv`) is the suite name. A name starting with `V` or `Zv` is a vector suite (`generators/testgen/src/testgen/cli.py:128`).
- [ACT] Vector suites listed in `expand_vector_extension` become one suite per SEW, for example `Vx8`…`Vx64` (`generators/testgen/src/testgen/io/testplans.py:28-39`). Other `Zv*` suites stay unexpanded, and `_detect_sew` then returns 8 (`generate/unpriv.py:120-140`). Rows whose `EFFEW<sew>` cell is empty are skipped (`generate/unpriv.py:102`).
- [ACT] `REQUIRED_EXTENSIONS` is built from three parts (`io/templates.py:117-120`, `136-149`, `163-181`):
  - the suite name, split at capitals;
  - the row's `ExtraExtensions`;
  - a minimal `Zve*` base. The default base is `Zve{max(sew,32)}x` (`io/templates.py:181`).
- [ACT] An experimental extension adds `#define RVTEST_EXPERIMENTAL` (`io/templates.py:73-74`). `act` skips such tests unless `--enable-experimental-extensions` is set (`select_tests` in `framework/src/act/select_tests.py`).

### 1.2 Proposed suites

| CSV                                         | Suite → `REQUIRED_EXTENSIONS`                      | Rows                                | Per-SEW expansion        |
| ------------------------------------------- | -------------------------------------------------- | ----------------------------------- | ------------------------ |
| `testplans/Zvvmm.csv`                       | `Zvvmm` + type ext + `Zve32x`/`Zve64x`             | 13 (one per integer type extension) | `Zvvmm8`…`Zvvmm64`       |
| `testplans/Zvvfmm.csv`                      | `Zvvfmm` + type ext + `Zve32f`/`Zve64d` (+`F`,`D`) | 21 unscaled + 30 microscaling       | `Zvvfmm8`…`Zvvfmm64`     |
| `testplans/Zvvmtls.csv`                     | `Zvvmtls` + `Zve32x`/`Zve64x`                      | 2 (`vmtl.v`, `vmts.v`)              | `Zvvmtls8`…`Zvvmtls64`   |
| `testplans/Zvvmttls.csv`                    | `Zvvmttls` + `Zve32x`/`Zve64x`                     | 2 (`vmttl.v`, `vmtts.v`)            | `Zvvmttls8`…`Zvvmttls64` |
| `testplans/priv/ExceptionsZvvm.csv` (later) | set by `@add_priv_test_generator`                  | one per mnemonic                    | `EFFEW` per row          |

Why four suites:

- [Spec] The specification defines exactly four family extensions (spec:41-46). "Implementing a family-level extension requires support for all instructions in that family" (spec:590).
- [ACT] Splitting the suite name at capitals turns `Zvvmm`, `Zvvfmm`, `Zvvmtls` and `Zvvmttls` into exactly one family name each. No mapping code is needed.
- [ACT] ACT moves toward fewer suites that use `ExtraExtensions`. Commit `574c6b55c` merged `<Suite><Ext>` testplans into their base suites. Per-type CSVs would create 65 suites.
- [Overlay] Microscaling extensions require `Zvvfmm` (`requirements` in `framework/src/act/data/udb_overlays/ime/ext/Zvvxi8fp16mm.yaml`). Their rows therefore go in `Zvvfmm.csv`. This includes the integer-input forms `vfwimmacc.vv`, `vfqimmacc.vv` and `vf8wimmacc.vv`.

Required framework edits. Each has a precedent:

- Add the four suites to `expand_vector_extension` (`io/testplans.py:30`). Precedent: `Zvbb`, `Zvkb`, `Zvbc` and `Zvknhb`. Commit `a726e43af` ("Vector Crypto in Main Testgen") changed `io/testplans.py`.
- Add them to covergroupgen's `_sew_variants_for` (`generators/coverage/src/covergroupgen/generate.py:118`). Precedent: the same commits.
- Add these `vector_map` entries in `io/templates.py:163-179`. Precedent: `"Zvfbfwma": ["Zve32f","Zfbfmin","F"]` (`io/templates.py:177`).
  - `Zvvfmm8`, `Zvvfmm16` and `Zvvfmm32` → `["Zve32f","F"]`.
  - `Zvvfmm64` → `["Zve64d","F","D"]`.
- Integer and tile suites need no entry. The default `Zve{max(sew,32)}x` matches the dependency column of the specification (spec:639-681).

### 1.3 Type extensions through `ExtraExtensions`

- [ACT] `docs/DeveloperGuide.md:283` documents `ExtraExtensions` as "Extensions a row needs beyond the testplan's own". `Zfa.csv`, `Zfh.csv`, `Zacas.csv` and `Zkt.csv` already have rows with the same mnemonic and different `ExtraExtensions`.
- [ACT] Each `ExtraExtensions` value gets its own `TestConfig`, file prefix and covergroup prefix (`generate/unpriv.py:80-94`, `data/config.py:52-54`).
- Experiment with testgen. A copy of `Zvbc.csv` got a second `vclmul.vv` row with `ExtraExtensions=Zvkb`. Testgen produced `rv64i/Zvbc64/Zvbc64Zvkb-vclmul.vv-00.S` with `REQUIRED_EXTENSIONS: ['I', 'Zvbc', 'Zvkb', 'Zve64x']`. **Testgen needs no change.**
- Experiment with covergroupgen. The same CSV produced only `Zvbc64_vclmul_vv_cg`. The `ZvbcZvkb` group was lost:
  - `read_testplans` stores `extra_testplans` under the unexpanded name `Zvbc` (`generate.py:343`).
  - The per-SEW jobs look it up under `Zvbc64` (`generate.py:893`).
  - **Fix:** copy `extra_testplans[arch]` to each SEW variant at `generate.py:350-353`. It is a bug fix of about 5 lines.
- Resulting names, for example: test `tests/rv64i/Zvvmm32/Zvvmm32Zvvi8i32mm-vqmmacc.vv-00.S`, and covergroup `Zvvmm32Zvvi8i32mm_vqmmacc_vv_cg` inside `` `ifdef ZVVI8I32MM_SUPPORTED ``.
- [ACT] `.gitignore` excludes `tests/rv*/Zv*` (`.gitignore:31-34`). IME tests are regenerated rather than checked in, like all vector suites. Covergroups are checked in.

An alternative was considered: one row per mnemonic, with a mapping from (mnemonic, SEW) to the type extension inside `get_vector_base_extension`.

- For integer rows it works. Each (mnemonic, SEW) has exactly one integer extension (spec:6807-6902).
- For FP rows it does not work. At (`vfwmmacc.vv`, SEW=32), FP16 inputs and BF16 inputs are separate extensions (FP encoding map in the specification).
- Explicit CSV rows are also easier to audit against the encoding maps.

Recommendation: use `ExtraExtensions` for both integer and FP rows.

Extension direction (§0.1):

- [Spec] A row is legal only when the extension in its encoding-map cell is implemented (spec:6646-6649). A family extension therefore implies no type extension. ime-test-gen's opposite direction is a generator finding (report finding 13).
- [Spec silent; Sail] The specification does not say whether a type extension requires its family extension. The overlay requires it, as GCC does. Sail decodes IME instructions only when the family extension is enabled (`sail/model/extensions/IME/ime_mem_insts.sail:310`).
- The GCC-only names `zvmma`, `zvvxofp8mm` and `zvvxnofp8mm` are not in the specification and are not used.

### 1.4 λ gating per testcase (decided)

- [ACT] A header `params` key holds one value. A list-valued UDB parameter matches when it contains that value (`framework/src/act/select_tests.py:32-45`). One file can therefore require only one λ per SEW.
- [ACT] UDB turns each list parameter into one macro per value in `rvtest_config.h`.
  - `config/ime/qemu-ime-rv64/qemu-ime-rv64.yaml:637-640` sets the λ lists.
  - A run with the overlay emitted `UDB_SUPPORTED_LAMBDA_SEW32_1`, `UDB_SUPPORTED_LAMBDA_SEW32_2`, `UDB_SUPPORTED_LAMBDA_SEW8_2`, and so on. This was observed in a scratchpad copy of `work/qemu-ime-rv64/env/rvtest_config.h`, lines 806-814.
  - The `work/` copy in the repository predates the overlay and lacks these macros.
- [ACT] Testcases are already wrapped in preprocessor guards on DUT parameters:
  - `handle_parameter_exclusions` guards on `ZVL{n}B_SUPPORTED` and `UDB_ELEN` (`asm/vector_helpers.py:682-719`).
  - `cp_cntr.py:51` uses `#if defined(UDB_HPM_COUNTER_EN_{hpm})`.
  - `InterruptsS.py:90` uses `#ifdef UDB_STVEC_MODES_{mode}`.
- [Proposal] Wrap every IME testcase that uses λ in `#if defined(UDB_SUPPORTED_LAMBDA_SEW<sew>_<λ>)`. To do this, give `handle_parameter_exclusions` an optional `(sew, λ)` argument.
  - The header names no λ.
  - A file runs on every DUT that has the family and type extension.
  - Testcases for an unsupported λ compile out, and their bins stay uncovered.
- [Proposal] Some coverpoints do not choose λ, for example a reused `cp_vs1`. Their testcases get a default λ through an `#if/#elif` chain over λ = 1, 2, 4, 8. The chain picks the smallest λ that the DUT supports.
- Why this is safe:
  - [ACT] The signature ELF and the self-checking ELF are built from the same source with the same `rvtest_config.h`.
  - [ACT] `SIGUPD_COUNT` is an upper bound, and the signature run records the final signature offset.
  - [Spec] UDB rejects a λ for which VLEN/(SEW·λ²) ∉ {1,2,4,8,16} (overlay constraint, report §16a). A supported λ therefore implies a legal `EMUL_C` at the DUT's VLEN (spec:798-819).
- Testcases that use two λ values, such as the mixed-λ round trip (§4.3), require both macros.

Note: selection in the header was considered and not chosen. It would group chunks by λ (`group_test_chunks`, `data/test_chunk.py:153-187`) and change `generate/unpriv.py:176-204`.

## 2. Rows and type representation

### 2.1 SEW means something different than in V widening

- [Spec] In IME, `SEW` is the width of the accumulator C. A and B hold elements of width `SEW/W`, packed into `SEW`-wide storage elements (spec:352-380, 1010-1036).
- [ACT] In V widening instructions, `SEW` is the narrow width and `vd` is widened. `WVV_ACC` sets `widened_regs={"vd"}` (`formatters/types/vvv_type.py:50-53`). `Vx.csv` therefore leaves `EFFEW64` empty for `vwmacc.vv` (`testplans/Vx.csv:128`).
- [Proposal] IME rows set `EFFEW<n>` to the accumulator SEW. No register is marked as widened. Narrow inputs use the existing fractional edge suffixes `emulf2`, `emulf4` and `emulf8`, as `vzext.vf2` does (`testplans/Vx.csv:25`).

### 2.2 Row inventory

[Spec] Rows follow the encoding maps (spec:6640-6974). A reserved (instruction, SEW) cell gets an empty `EFFEW` cell.

| Mnemonic                                               | Type         | `ExtraExtensions` → EFFEW                                                                                                                                                       |
| ------------------------------------------------------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `vmmacc.vv`                                            | `MMACC`      | `Zvvi8mm`→8, `Zvvi16mm`→16, `Zvvi32mm`→32, `Zvvi64mm`→64                                                                                                                        |
| `vwmmacc.vv`                                           | `MMACC`      | `Zvvi4i8mm`→8, `Zvvi8i16mm`→16, `Zvvi16i32mm`→32, `Zvvi32i64mm`→64                                                                                                              |
| `vqmmacc.vv`                                           | `MMACC`      | `Zvvi4i16mm`→16, `Zvvi8i32mm`→32, `Zvvi16i64mm`→64                                                                                                                              |
| `v8wmmacc.vv`                                          | `MMACC`      | `Zvvi4i32mm`→32, `Zvvi8i64mm`→64                                                                                                                                                |
| `vfmmacc.vv`                                           | `FMMACC`     | `Zvvofp8mm`→8, `Zvvfp16mm`→16, `Zvvbf16mm`→16, `Zvvfp16mm:Zvvbf16mm`→16, `Zvvfp32mm`→32, `Zvvfp64mm`→64                                                                         |
| `vfwmmacc.vv`                                          | `FMMACC`     | `Zvvofp4ofp8mm`→8, `Zvvofp8fp16mm`→16, `Zvvofp8bf16mm`→16, `Zvvfp16fp32mm`→32, `Zvvbf16fp32mm`→32, `Zvvfp16fp32mm:Zvvbf16fp32mm`→32, `Zvvfp32fp64mm`→64                         |
| `vfqmmacc.vv`                                          | `FMMACC`     | `Zvvofp4fp16mm`→16, `Zvvofp4bf16mm`→16, `Zvvofp8fp32mm`→32, `Zvvfp16fp64mm`→64, `Zvvbf16fp64mm`→64, `Zvvfp16fp64mm:Zvvbf16fp64mm`→64                                            |
| `vf8wmmacc.vv`                                         | `FMMACC`     | `Zvvofp4fp32mm`→32, `Zvvofp8fp64mm`→64                                                                                                                                          |
| `vfwmmacc.vv`, `vfqmmacc.vv`, `vf8wmmacc.vv` with vm=0 | `FMMACC_MX`  | 16 rows: `Zvvx[n]ofp4ofp8mm`, `Zvvx[n]ofp8fp16mm`, `Zvvx[n]ofp8bf16mm`, `Zvvx[n]ofp4fp16mm`, `Zvvx[n]ofp4bf16mm`, `Zvvx[n]ofp8fp32mm`, `Zvvx[n]ofp4fp32mm`, `Zvvx[n]ofp8fp64mm` |
| `vfwimmacc.vv`, `vfqimmacc.vv`, `vf8wimmacc.vv`        | `MMACC_MX`   | 14 rows: `Zvvx[n]i8fp16mm`, `Zvvx[n]i8bf16mm`, `Zvvx[n]i4fp16mm`, `Zvvx[n]i4bf16mm`, `Zvvx[n]i8fp32mm`, `Zvvx[n]i4fp32mm`, `Zvvx[n]i8fp64mm`                                    |
| `vmtl.v`, `vmts.v`                                     | `VLT`, `VST` | none; EFFEW 8 to 64                                                                                                                                                             |
| `vmttl.v`, `vmtts.v`                                   | `VLT`, `VST` | none; EFFEW 8 to 64                                                                                                                                                             |

Notes:

- [Spec] A mixed FP16/BF16 row requires both named extensions (preamble of the FP encoding map in the specification). A colon list in `ExtraExtensions` expresses that, as `Zfh:D` does in `Zfa.csv`.
- [Proposal] Integer signedness and FP input or output format are not separate rows. They become bins of `cp_altfmt` (§4). The reasons:
  - One integer extension covers all four signedness combinations (integer encoding map).
  - One OFP8 extension covers all E4M3/E5M2 input combinations (FP encoding map).
- [Spec vs toolchain] The CSV uses the specification names `vqmmacc.vv`, `vfqmmacc.vv` and `vfqimmacc.vv`. They are canonical (§0.1). `tests/env/rvtest_experimental.h:158-213` defines both these names and the GCC and QEMU names (`vqwmmacc.vv`, …). The GCC names exist only as macro aliases.

## 3. Instruction formatter types

All new types live in new files under `generators/testgen/src/testgen/formatters/types/`. They register with `@add_instruction_formatter` (`formatters/registry.py:111`). Precedent: `bi_type.py` for Zibi (commit `55ef31b3f`).

### 3.1 Shared IME pieces

- New `InstructionParams` fields in `data/params.py`: `lambda_`, `imm_lambda`, `altfmt_a`, `altfmt_b`, `altfmt`, `bs` and `ld_mode`. Precedent: `egs`, `vxrm` and `index_register` were added for vector crypto and fixed point.
- New `VectorTypeConfig` field `fixed_emul: dict[str, int]`, used as `{"vd": 16}` (`formatters/registry.py:41-69`). Precedent: `egs` and `index_register` in the same dataclass. Two related edits:
  - `get_register_emul` returns the fixed value (`instructions/vector_params.py:27-41`).
  - The data label size at `instructions/vector_params.py:527` must use that EMUL.
- New helper `load_ime_vtype(params, test_data)` in `asm/vector_helpers.py`. It emits `LI(xT, <vtype>)` and `vsetvl xV, xA, xT`.
  - [Spec] The IME fields are outside the `vsetvli` immediate. Only `vsetvl` writes them (spec:712-797).
  - [Spec] Field positions (spec:686-690): `lambda[2:0]` at `vtype[XLEN-2:XLEN-4]`, `bs` at `XLEN-5`, `altfmt_A` at `XLEN-6` and `altfmt_B` at `XLEN-7`. The helper computes the vtype value per XLEN, so RV32 and RV64 both work.
  - [ACT] `LI()` has a fixed length (report 1 §10). The signature ELF and the self-checking ELF therefore keep the same addresses.
- VL semantics [Proposal]: the IME formatters read `params.vl` in units of λ·LMUL elements. For MACC the unit is one column of C. For tile loads and stores it is one line.
  - `"vlmax"` uses `vsetvl` with AVL `x0`.
  - An integer n uses `LI(n·λ·LMUL)`.
  - `"half"` computes VLMAX/2 at run time. It is a multiple of λ·LMUL when M is even.
  - `"random"` computes `(rand & (VLMAX-1) | L) & ~(L-1)` with L = λ·LMUL, after the pattern of `generate_random_vl` (`asm/vector_helpers.py:537-574`).
  - All four forms are VLEN-agnostic. [Spec] VL must be a multiple of λ·LMUL (spec:5776, spec:2353).
  - Generic coverpoints pass `vl=1` in the base suite. The IME formatters read that as one column, or one line.

### 3.2 `MMACC` (integer) and `FMMACC` (FP, vm=1)

```python
mmacc_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(
        overlap_constraints={("vd", "vs1"), ("vd", "vs2")},
        fixed_emul={"vd": 16},
        maskable=False,  # [Spec] spec:1087
        require_zero_vstart=True,  # [Spec] spec:1104
    ),
)
fmmacc_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    instruction_class=["vector_fp"],
    vector_data=VectorTypeConfig(
        overlap_constraints={("vd", "vs1"), ("vd", "vs2")},
        fixed_emul={"vd": 16},
        maskable=False,
        require_zero_vstart=True,
        random_element_generator=exact_dot_rng,  # §5
    ),
)
```

- **Register plan.**
  - C uses a 16-register window aligned to 16: base `v0` or `v16`.
  - A and B sit at LMUL alignment in the other half of the register file.
  - A may equal B. [Spec] The specification gives C ← C + A·Aᵀ as an example.
  - Why 16 registers: [Spec] `EMUL_C` = VLEN/(SEW·λ²) can be 16 (spec:381-391). `EMUL_C` depends on VLEN, so only a base aligned to 16 fits every VLEN.
  - [Open: user decision] Must the `vd` group (C, `EMUL_C` registers) avoid the `vs1` and `vs2` groups?
    - [Spec] The specification is silent. The `vmmacc.vv` exception list (spec:5782-5792) and the lists of the other MACC instructions name only alignment, `vstart`, VL, `EMUL_C`, reserved rows and, for vm=0, overlap with `v0`. `check_gemm_reg_groups` checks only alignment (spec:4193-4202).
    - [Sail] No overlap check: `execute_ime_int_mmacc` and `execute_ime_fp_mmacc` check only alignment (`sail/model/extensions/IME/ime_mem_insts.sail:286-293`, `:618-626`). The GEMM loops compute in place. They read A and B element by element while they write each finished C element (`:248-265`, `:501-597`). With an overlap, later C elements see the A or B values that earlier C writes changed.
    - Under §0.1, overlap is therefore allowed, with Sail's in-place result. That conflicts with the earlier project statement that `vd` cannot overlap `vs1` or `vs2`. The design does not override that statement. It keeps the constraint until the user decides (§10).
  - Enforcement while the question is open: `overlap_constraints={("vd","vs1"),("vd","vs2")}` in the formatter config, and an allocation that reserves all 16 registers of the C window before it places A and B. No testplan has a `cmp_vd_vs1` or `cmp_vd_vs2` column for MACC, and `ExceptionsZvvm` does not test an overlap, because neither the specification nor Sail traps on it.
- **Setup.**
  - Load C into 16 registers: `vsetvli x0, x0, e<SEW>, m8` and two `vle<SEW>.v` loads. The second address is advanced by `8·vlenb`.
  - Load A and B with `vsetvli … m<LMUL>` and `vle<SEW>.v` at VLMAX. No tile load is used.
  - [Spec] With W>1, each `SEW` storage element holds W packed inputs in standard element order (spec:1027-1036). `vle<SEW>` gives exactly that layout from a byte image.
  - FP rows: `fsrmi` and `fsflagsi 0` through `handle_vector_fp` (`asm/vector_helpers.py:750-763`).
  - Set vtype with `load_ime_vtype`. It sets λ; `altfmt_A/B` (signedness, or input formats); `altfmt` (FP output format); `vta` and `vma`; SEW; LMUL; and VL.
- **Test.** `vmmacc.vv vD, vS1, vS2`. The `.insn` macros assemble it (`tests/env/rvtest_experimental.h:158`).
- **Check.**
  - `vsetvli x0, x0, e<SEW>, m8, tu, mu` sets VL to VLMAX.
  - `write_sigupd_v_len(..., lmul=8, segments=2)` checks the two m8 halves of the C window (`asm/vector_helpers.py:106-197`).
  - Every element is then a body element, so the check is exact. It also checks that the registers beyond `EMUL_C`, and the C tail columns, are unchanged.
  - FP rows also get `RVTEST_SIGUPD_FFLAGS` through `handle_vector_fp`.
  - [ACT] No new macro is needed. The proof of concept's per-element scalar check is VLEN-specific and is not used.
- **Gate.** `#if defined(UDB_SUPPORTED_LAMBDA_SEW<SEW>_<λ>)` (§1.4). The existing `UDB_ELEN` gate in `handle_parameter_exclusions` also applies.

### 3.3 `FMMACC_MX` and `MMACC_MX` (vm=0)

- These types work like `FMMACC`, with these additions:
  - v0 holds the scales (`v0.scale`).
  - [Spec] `vd`, `vs1` and `vs2` must not overlap v0 (spec:5013, 5461).
  - `bs` selects block size 32 or 16. The row's `x` or `xn` prefix chooses it.
- Config: `overlap_constraints |= {("vd","v0"),("vs1","v0"),("vs2","v0")}`. The C window is therefore always based at `v16`, and the `cp_vd` bin `v0` does not exist for these rows.
- A new `cp_scale` edge coverpoint loads E8M0 scale patterns into v0.
- [Blocked] The Sail fork rejects vm=0. `sail/model/extensions/IME/ime_mem_insts.sail:440-449` says "Microscaled vm=0 … remain out of scope". The rows can be written now, but no DUT configuration can select them until Sail implements them.

### 3.4 `VLT` (`vmtl.v`, `vmttl.v`) and `VST` (`vmts.v`, `vmtts.v`)

```python
vlt_config = InstructionTypeConfig(
    required_params={"vd", "rs1", "rs2"},
    instruction_class=["load", "strided"],
    vector_data=VectorTypeConfig(masked_constraints={("vd", "v0")}),  # spec:2359
)
vst_config = InstructionTypeConfig(
    required_params={"vs3", "rs1", "rs2"},
    instruction_class=["store", "strided"],
    vector_data=VectorTypeConfig(),
)
```

- **Setup (load).**
  - Fill `vd` with fixed values at VLMAX, as `VectorLoad(only_setup_tail=True)` does (`asm/vector_helpers.py:487-680`).
  - Load the mask if the testcase is masked.
  - `LA(rs1, data)`.
  - `LI(rs2, LD)`, with LD chosen by `cp_ld`. LD = 0 (or `rs2 = x0`) selects the natural LD ([Spec] spec:2278-2291).
  - [Sail bug] Sail selects the natural LD only when `rs2` is `x0`, and uses LD = 0 for a register that holds 0 (`sail/model/extensions/IME/ime_mem_insts.sail:53-55`, `:145-147`). The `cp_ld` bin with 0 in a register follows the specification and fails until the Sail fix (§0.1). The `rs2 = x0` bin passes.
  - Set vtype with `load_ime_vtype`.
- **Test.** `vmtl.v vD, (xA), xL[, L<λ>][, v0.t]`.
- **Check (load).**
  - Re-issue `vsetvl` with the same VL and `vta=vma=0`.
  - Call `RVTEST_SIGUPD_V_LEN` on `vd` at the tile LMUL.
  - [Spec] A tile load always leaves inactive and tail elements undisturbed, whatever `vta` and `vma` say (spec:2321).
  - [ACT] The macro relaxes the tail check when the saved `vtype.vta` is 1 (`_FORCE_TA_MA_FLAG` path in `tests/env/signature.h:686-800`). Forcing `tu,mu` before the check keeps it strict.
- **Check (store).**
  - Read back a memory window with `vle<SEW>.v`. [ACT] This follows the store formatters, which read back with the equivalent load and check the register (`read_back` in `formatters/types/strided_store_vector_type.py`).
  - Limit a padded LD to at most 2·linesize. The window then fits in 2·LMUL registers at any VLEN; at LMUL=8 that is two m8 groups.
  - The gaps between lines must keep their preloaded values. That covers the address formula that TC-VSE-03/04 test.
- **Immediate λ.**
  - After the instruction, emit `csrr xT, vtype` and `RVTEST_SIGUPD`. This checks that the immediate did not change `vtype.lambda` ([Spec] spec:2346-2349). It uses the integer SIGUPD path (`asm/helpers.py:135-158`).
  - It replaces the ime-test-gen check, whose mask `0x3800…` reads the wrong bits (`ime-test-gen/src/expand_ir.rs:1363`; report finding 1).
- **Transposition.** The formatter derives it from the mnemonic. `vmttl.v` and `vmtts.v` use the transposed address formula, with natural LD = VLEN/(SEW·λ) (spec:2286).
- [Blocked] The Sail tile-index bug affects these tests. `sail/model/extensions/IME/ime_mem_insts.sail` lines 73-90 and 160 use the flat index.
  - Register-level checks expose the bug at LMUL>1. Every VLT and VST testcase at LMUL>1 therefore fails on a conforming DUT until the Sail fix lands. The bins stay in place (AGENTS.md).
  - LMUL=1 tests are not affected, because `tile_reg_idx(i,1,λ,epr) = i`.
  - §4.4 adds tests whose data names every element, so that a failure shows the wrong mapping directly.

### 3.5 Covergroup sample templates

- [ACT] Each type needs a template `generators/coverage/src/covergroupgen/templates/sample_<TYPE>.sv`, modelled on `sample_VVV_ACC.sv`.
- The IME vtype fields need new cases in `get_csr_val(…,"vtype",<field>)` (`framework/src/act/fcov/coverage/RISCV_coverage_csr.svh:1131-1144`). The new fields are `lambda`, `bs`, `altfmt_a`, `altfmt_b` and `altfmt`.
- Decoding needs entries in `framework/src/act/fcov/disassemble.svh`. Precedent: commit `55ef31b3f` (Zibi) added 4 lines there.
- [ACT] `RISCV_imported_decode_pkg.svh` is generated from riscv-opcodes and must not be edited by hand. riscv-opcodes has no IME encodings. The encodings must therefore stay in `disassemble.svh` until riscv-opcodes adds them. [Uncertain] No earlier extension did this.

## 4. Coverpoint columns, and the mapping of every ime-test-gen family

### 4.1 Coverpoints

Reused generators are found by prefix match (`coverpoints/registry.py:49-80`). New generators go in new files under `coverpoints/vector/`.

| Column (cell)                                                                         | Generator                                                  | Template                            | Bins and meaning                                                                  |
| ------------------------------------------------------------------------------------- | ---------------------------------------------------------- | ----------------------------------- | --------------------------------------------------------------------------------- |
| `cp_asm_count` (x)                                                                    | reuse                                                      | reuse                               | one testcase                                                                      |
| `cp_vd` (`emul16`)                                                                    | reuse `cp_vd` (`emul` suffix in `cp_vector_regs.py`)       | new `cp_vd_emul16.sv`               | `vd` ∈ {v0, v16}, VLEN-agnostic                                                   |
| `cp_vs1`, `cp_vs2` (x)                                                                | reuse                                                      | reuse                               | all 32 registers at LMUL=1                                                        |
| `cp_vd` (x), `cp_vs3` (x) for `VLT`/`VST`                                             | reuse                                                      | reuse                               | all 32 registers at LMUL=1                                                        |
| `cp_rs1` (`nx0`), `cp_rs2` (x)                                                        | reuse (`cp_regs.py`, vector-aware at `cp_regs.py:142-179`) | reuse                               | base and LD registers; `rs2=x0` gives the natural LD                              |
| `cp_vd_edges` (`x`, `f` or `f_<fmt>`)                                                 | reuse (`cp_vs_edges.py`)                                   | reuse                               | C initial value: an edge in element 0 (zero, ones, min, max, NaN, ∞, …)           |
| `cp_vs1_edges`, `cp_vs2_edges` (`x`, `emulf2/4/8`, `f_<fmt>`)                         | reuse                                                      | needs Int4, FP8 and FP4 edge tables | an edge in narrow input element 0, packed                                         |
| `cr_vs1_vs2_edges` (`f_<fmt>`)                                                        | reuse `cr_vs_reg_edges.py`                                 | reuse                               | cross of product operands, for example 0×∞                                        |
| `cp_altfmt` (x)                                                                       | new                                                        | new                                 | integer: SS, SU, US, UU; FP: the legal encoding-map rows for the row's extensions |
| `cr_lambda_lmul` (x)                                                                  | new                                                        | new                                 | λ ∈ {1,2,4,8,16,32,64} × LMUL ∈ {1,2,4,8}, at VL = VLMAX                          |
| `cp_tile_vl` (x)                                                                      | new                                                        | new                                 | VL ∈ {1 column or line, half, VLMAX, random multiple}                             |
| `cp_ld` (x)                                                                           | new                                                        | new                                 | LD ∈ {0 (natural), tight = linesize, padded = linesize+δ, 2·linesize}             |
| `cp_imm_lambda` (x)                                                                   | new                                                        | new                                 | none, or L1…L64 when supported; background λ ≠ immediate λ                        |
| `cp_masking_edges` (x)                                                                | reuse                                                      | reuse                               | the 5 standard mask edges, on tile loads and stores                               |
| `cr_tile_vtype_agnostic` (x)                                                          | new                                                        | new                                 | vta × vma on tile loads; the check stays strict                                   |
| `cp_csr_frm` (`v`)                                                                    | reuse `cp_csr_frm.py` (`_v`)                               | reuse                               | the 5 dynamic rounding modes                                                      |
| `cp_csr_fflags` (`voun` etc.)                                                         | reuse `cp_csr_fflags.py`                                   | reuse                               | preset flag bits                                                                  |
| `cp_scale` (x), MX only                                                               | new                                                        | new                                 | E8M0 edges in v0                                                                  |
| `cp_custom_tile_layout` (x), VLT and VST                                              | new                                                        | new                                 | LMUL × λ × LD ∈ {natural, padded}; data names each element (§4.4)                 |
| `cp_custom_tile_roundtrip` (x), VST                                                   | new                                                        | new                                 | same-geometry round trip; load λ ≠ store λ (§4.3)                                 |
| `cp_custom_tile_crossmode` (x), rows with `ExtraExtensions=Zvvmtls` in `Zvvmttls.csv` | new                                                        | new                                 | order-preserving load with transposing store, and the reverse (§4.3)              |
| `cp_custom_tile_macc` (x), `vmmacc.vv` rows with `ExtraExtensions=Zvvi<n>mm:Zvvmtls`  | new                                                        | new                                 | LMUL × λ, A and B by `vmtl.v`, C by `vmts.v` (§4.4)                               |
| `cp_fp_subdot` (x), FP rows with W>1                                                  | new                                                        | new                                 | W equal products that add up to one ULP of C₀; one bin per `frm` value (§4.5)     |

`cr_vl_lmul` and `cr_vtype_agnostic` cannot be reused as they are:

- They sweep fractional LMUL (`cr_vl_lmul.py:64`) and a random VL with no alignment (`cr_vl_lmul.py:67`, `asm/vector_helpers.py:568`).
- [Spec] Fractional LMUL is reserved for IME (spec:425). VL must be a multiple of λ·LMUL. Both sweeps would therefore trap.
- New generators with longer names, for example `cr_lambda_lmul`, leave the existing ones untouched.

### 4.2 Family mapping

Counts come from `ci/work/gen-asm-v512/tests.txt` (5372 IR tests at VLEN=512).

| ime-test-gen family (count @512)                                                 | Sweep, values, check                                                                                              | ACT location                                                 | Kept as                                                                                                                                                                                                       | Dropped or deferred                                                                                                    |
| -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| TC-LS-01 `vmtl→vmts` (part of 1952)                                              | SEW × λ × LMUL × VL{min,half} × stride{tight,padded} (`ime-test-gen/src/spec/sweep.rs:31-63`); round-trip compare | `Zvvmtls`: `vmtl.v`, `vmts.v`                                | Each instruction alone: SEW = EFFEW suite; `cr_lambda_lmul`; `cp_tile_vl` (line, half, plus VLMAX and random); `cp_ld` (tight, padded, plus natural). The round trip: `cp_custom_tile_roundtrip` on `vmts.v`. | — The round trip cancels the Sail bug (§4.3), so the layout bins of §4.4 carry the detection.                          |
| TC-LS-02 `vmttl→vmtts`                                                           | same                                                                                                              | `Zvvmttls`                                                   | same, with `cp_custom_tile_roundtrip` on `vmtts.v`                                                                                                                                                            | as above                                                                                                               |
| TC-LS-03/04: order load with transposing store, and the reverse                  | same                                                                                                              | rows with `ExtraExtensions=Zvvmtls` in `Zvvmttls.csv`        | `cp_custom_tile_crossmode` (§4.3)                                                                                                                                                                             | — The pair also cancels the Sail bug.                                                                                  |
| TC-LS-06 masked load (alternating)                                               | mask pattern                                                                                                      | `cp_masking_edges` on all four tile instructions             | ACT's 5 mask edges                                                                                                                                                                                            | ACT's edges replace the exact "alternating" pattern                                                                    |
| TC-LS-07: vstart skips row 1                                                     | vstart = linesize                                                                                                 | `cp_vstart` in `ExceptionsZvvm`                              | resume check                                                                                                                                                                                                  | deferred to the privileged suite, as `ExceptionsVls` does (`testplans/priv/ExceptionsVls.csv`)                         |
| TC-LS-08a: register v8                                                           | fixed register                                                                                                    | `cp_vd`/`cp_vs3`                                             | all 32 registers                                                                                                                                                                                              | —                                                                                                                      |
| TC-VSE-03/04 address formula (576)                                               | LD, sentinel memory                                                                                               | `VST` window check and `cp_ld`                               | kept                                                                                                                                                                                                          | —                                                                                                                      |
| TC-TAIL-01/02 tail undisturbed (part of 576)                                     | sentinel registers                                                                                                | every `VLT` check; `cr_tile_vtype_agnostic`                  | kept, with a strict check                                                                                                                                                                                     | —                                                                                                                      |
| TC-TAIL-04/05 masked undisturbed                                                 | alternating, odd                                                                                                  | `cp_masking_edges` with the strict check                     | kept                                                                                                                                                                                                          | ACT's edges replace the exact patterns                                                                                 |
| TC-ILL-01/02 (480): immediate λ L2/L4 over background L1; vtype preserved        | `lambda_preserve!` (`ime-test-gen/src/dsl_plans.rs:50-55`)                                                        | `cp_imm_lambda` and a vtype SIGUPD                           | kept                                                                                                                                                                                                          | **These are not illegal-instruction tests.** "ILL" means "immediate lambda".                                           |
| TC-MACC-01..06: `vmmacc`, e32, SS/US/SU/UU, C zero or ramp, positive or negative | λ × LMUL × sign; positional values                                                                                | `vmmacc.vv` rows in `Zvvmm`, at all 4 SEWs                   | `cr_lambda_lmul`, `cp_altfmt`, `cp_vd_edges` (C init), `cp_vs*_edges` (positive and negative map to max, min, ones, …). The tile-load and tile-store sequence: `cp_custom_tile_macc` (§4.4).                  | the e32-only restriction is lifted                                                                                     |
| TC-MACC-09/10: `vwmmacc`/`vqmmacc`, all signs                                    | same                                                                                                              | `vwmmacc` and `vqmmacc` rows                                 | same, plus `emulf2/4` edges                                                                                                                                                                                   | —                                                                                                                      |
| (none)                                                                           | —                                                                                                                 | `v8wmmacc.vv`; Int4 rows                                     | new                                                                                                                                                                                                           | ime-test-gen skips EEW<8 (`sweep.rs:76`)                                                                               |
| TC-FMACC-F32/F64/F16/BF16                                                        | ones and ramp; C zero or ramp                                                                                     | `vfmmacc.vv` rows in `Zvvfmm`                                | exact data (§5), FP edges, fflags                                                                                                                                                                             | —                                                                                                                      |
| TC-MX16-01..04 (f16×bf16)                                                        | mixed formats                                                                                                     | row `Zvvfp16mm:Zvvbf16mm`                                    | `cp_altfmt` bins                                                                                                                                                                                              | [Uncertain] Sail may not implement W=1 BF16 rows. `ime_mem_insts.sail:443-447` lists only FP16, FP32 and FP64 for W=1. |
| TC-FMACC-E4M3/E5M2, TC-FP8-MX-01..04                                             | OFP8, W=1                                                                                                         | row `Zvvofp8mm`                                              | `cp_altfmt` E4M3/E5M2 combinations                                                                                                                                                                            | blocked: Sail has no OFP8                                                                                              |
| TC-FW-F16/BF16/MX-05/06, TC-FW-F32                                               | W=2                                                                                                               | `vfwmmacc.vv` rows                                           | kept                                                                                                                                                                                                          | —                                                                                                                      |
| TC-FW-E4M3/E5M2, TC-FW-MX-01..04                                                 | OFP8 → f16/bf16                                                                                                   | OFP8 rows of `vfwmmacc.vv`                                   | in the CSV                                                                                                                                                                                                    | blocked: Sail                                                                                                          |
| TC-FQ-F16/BF16                                                                   | W=4 → f64                                                                                                         | `vfqmmacc.vv` rows                                           | kept                                                                                                                                                                                                          | —                                                                                                                      |
| TC-FQ-E4M3/E5M2/MX                                                               | OFP8 → f32                                                                                                        | rows                                                         | in the CSV                                                                                                                                                                                                    | blocked: Sail                                                                                                          |
| TC-RM-* (5 frm modes)                                                            | `frm: all`                                                                                                        | `cp_csr_frm_v`                                               | with single-term inexact data (§5)                                                                                                                                                                            | multi-term frm stress deferred                                                                                         |
| TC-RND-*-TIE/OVF/UNF/CAN                                                         | adversarial sums                                                                                                  | `cp_vd_edges_f`, `cp_vs*_edges_f`, `cr_vs1_vs2_edges_f`      | single-term forms                                                                                                                                                                                             | multi-term forms gated on profile parameters (§7)                                                                      |
| TC-SUB-*                                                                         | subnormal inputs and products                                                                                     | FP edges `min_subnorm`, `largestsubnorm`                     | kept                                                                                                                                                                                                          | —                                                                                                                      |
| TC-SPL-*-NAN-A/B                                                                 | NaN in A or B                                                                                                     | FP edges `canonicalQNaN`, `sNaN_payload1`                    | kept. [Spec] The result is the canonical NaN (spec:1680-1687).                                                                                                                                                | —                                                                                                                      |
| TC-FLAG-*                                                                        | expected fflags                                                                                                   | `RVTEST_SIGUPD_FFLAGS` in every FP testcase; `cp_csr_fflags` | kept in every FP testcase                                                                                                                                                                                     | —                                                                                                                      |
| TC-AS-LS, TC-MACC-AS, TC-FW-AS (`--as-loads`)                                    | load at a different storage width                                                                                 | —                                                            | —                                                                                                                                                                                                             | dropped. Tile instructions move only SEW-wide storage elements (spec:2236-2240).                                       |
| (none)                                                                           | —                                                                                                                 | microscaling rows                                            | new                                                                                                                                                                                                           | blocked: Sail                                                                                                          |

How the sweep dimensions carry over:

- VLEN is no longer a dimension. Tests are VLEN-agnostic, and Sail runs at the DUT's VLEN.
- SEW becomes the per-SEW suite.
- λ×LMUL becomes `cr_lambda_lmul`.
- Sign or format becomes `cp_altfmt`.
- VL mode becomes `cp_tile_vl`.
- Stride becomes `cp_ld`.
- Mask becomes `cp_masking_edges`.
- Rounding mode becomes `cp_csr_frm_v`.
- Value generators become edge coverpoints (§5).
- [Proposal] ime-test-gen crosses λ×LMUL×sign. ACT gets two single coverpoints and one cross (λ×LMUL). A `cr_altfmt_lambda` cross can be added if reviewers want the full product.

### 4.3 Round-trip and cross-mode tests (kept as extra bins)

Vehicle: a `cp_custom_<name>` column on the tile rows.

- [ACT] `cp_custom_*` is how ACT tests a sequence that the plain formatter does not emit. `Vls.csv` has nine such columns. `cp_custom_ffLS` builds its test chunk itself, replaces the check with `csrr vl` and `RVTEST_SIGUPD`, and wraps the testcase in an `#ifdef` (`generators/testgen/src/testgen/coverpoints/vector/cp_custom_vls.py:62-132`). The covergroup template of such a column may sample only `vtype` fields of the labelled instruction, as `cp_custom_maskLS.sv` does.
- [ACT] A row that needs a second family extension uses an `ExtraExtensions` colon list, as `Zfh:D` does in `Zfa.csv`.
- A dedicated row type was rejected. A new `Type` would duplicate the `VLT` and `VST` setup and check code, and a second row with the same mnemonic and no `ExtraExtensions` has no precedent.

| Column                     | Row (labelled instruction)                                                                                                                                 | Sequence                                                                                                                                                   | Check                                                                                                                                      | Bins                                                                                                                  |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| `cp_custom_tile_roundtrip` | `vmts.v` in `Zvvmtls.csv`; `vmtts.v` in `Zvvmttls.csv`                                                                                                     | Load `vs3` with the tile load of the same family (`vmtl.v` or `vmttl.v`) from a source window, then store with the row's instruction to a separate window. | VST check: read the destination window back with `vle<SEW>.v`, then `RVTEST_SIGUPD_V_LEN`. Gaps between lines keep their preloaded values. | `same_lmul<L>_lambda<λ>_ld<nat\|pad>` for L ∈ {1,2,4,8}; `mixed_lmul<L>_lambda<λ>_imm<λ'>` for L ∈ {2,4,8} and λ' ≠ λ |
| `cp_custom_tile_crossmode` | `vmtts.v` with `ExtraExtensions=Zvvmtls` (TC-LS-03: `vmtl.v` then `vmtts.v`); `vmttl.v` with `ExtraExtensions=Zvvmtls` (TC-LS-04: `vmttl.v` then `vmts.v`) | Load with one mode and store with the other, at the same `vtype`. The destination window holds the transpose of the source tile.                           | Same as above.                                                                                                                             | `lmul<L>_lambda<λ>_ld<nat\|pad>`                                                                                      |

- The `same` bins reproduce TC-LS-01/02 and keep the ime-test-gen check that memory comes back unchanged. The VST check makes it exact: the destination window equals the source window, line for line.
- [Inferred] The `same` and cross-mode bins cannot detect a wrong register-element mapping. The load writes tile element i to register element f(i), and the store reads tile element i from f(i), for any f. Memory then receives `dst[off_store(i)] = src[off_load(i)]` for the correct mapping and for the flat index alike. At the reproducer configuration, Sail and the specification agree on all 16 elements of both cross-mode pairs (computed).
- The `mixed` bins break the cancellation. The store uses an immediate λ' (`,L<λ'>`) that differs from the `vtype` λ of the load. `tile_reg_idx` then differs between load and store whenever LMUL>1.
  - [Spec] The immediate λ overrides `vtype.lambda` for that instruction only (spec:2314). VL = VLMAX is a multiple of λ'·LMUL for any supported λ' ≤ VLMAX/LMUL.
  - The testcase needs both λ values: `#if defined(UDB_SUPPORTED_LAMBDA_SEW<n>_<λ>) && defined(UDB_SUPPORTED_LAMBDA_SEW<n>_<λ'>)`.
  - On `qemu-ime-rv64` at SEW=32, the bin `mixed_lmul2_lambda1_imm2` runs.
  - Example at VLEN=256, SEW=32, LMUL=2: `vmtl.v` with λ=1 and LD=2 from a source holding 0..15, then `vmts.v ..., L2` with LD=4. The specification gives `0 2 1 3 4 6 5 7 | 8 10 9 11 12 14 13 15`. Sail `c69e3e22` gives `0 1 … 15`. 8 of 16 elements differ (computed).
  - The Sail fix uses the effective λ: `lambda_enc` takes the immediate when it is nonzero (`sail/model/extensions/IME/ime_mem_insts.sail:32`, which the patch does not change). The `mixed` bins therefore pass on Sail after the fix.

### 4.4 Tests for a wrong register-element mapping (the Sail bug class)

Goal: detect a tile load or store that places tile element i at a register element other than `tile_reg_idx(i, LMUL, λ, VLEN/SEW)`, and make the wrong placement readable from the signature.

Common rules:

- Data names each element. Memory sources hold a ramp: element k holds k mod 2^SEW. Register sources come from `vid.v`, so register element k holds k. A mismatching signature word then shows which element arrived. At SEW=8, values repeat after 256 elements; a wrong mapping is still detected, because most moved elements land at another index below 256.
- The ramp is a fixed data label, registered with `TestData.register_vector_data(…, elements=[…])` (`data/state.py:239-266`), as `cp_custom_ffLS` registers its mask.
- Bins cover LMUL ∈ {1, 2, 4, 8}, every λ gated as in §1.4, and both LD settings: natural (`rs2 = x0`) and padded (linesize + 1, bounded by 2·linesize as in §3.4). The LMUL=1 bins are controls: `tile_reg_idx(i, 1, λ, epr) = i`, so Sail is correct there.
- VL = VLMAX. The `vtype` is set with `load_ime_vtype` and `tu, mu`.
- Check macros: `RVTEST_SIGUPD_V_LEN` through `write_sigupd_v_len` (`asm/vector_helpers.py:106-197`) for register groups and for memory windows read back with `vle<SEW>.v`. No new macro.

| Test                                          | Column and row                                                                                           | Sequence                                                                                                                                                                                                                                  | Check                                                                                                                                                                      | Bins                              |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| L1. Tile load seen through the register group | `cp_custom_tile_layout` on `vmtl.v` and `vmttl.v`                                                        | Fill `vd` with a sentinel at VLMAX; `vmtl.v vd, (ramp), LD`                                                                                                                                                                               | `vsetvli` at the tile LMUL with `tu, mu`, then `RVTEST_SIGUPD_V_LEN` on `vd`. This is the register dump of the reproducer, with `vse32.v` replaced by the signature macro. | `lmul<L>_lambda<λ>_ld<nat\|pad>`  |
| S1. Tile store fed from `vid.v`               | `cp_custom_tile_layout` on `vmts.v` and `vmtts.v`                                                        | `vsetvli` at the tile LMUL; `vid.v vs3`; set the IME `vtype`; `vmts.v vs3, (dst), LD`                                                                                                                                                     | Read the destination window back with `vle<SEW>.v` and `RVTEST_SIGUPD_V_LEN`. Gaps keep their sentinel.                                                                    | same                              |
| R1. Mixed-λ round trip                        | `cp_custom_tile_roundtrip`, `mixed` bins (§4.3)                                                          | `vmtl.v` at λ, then the store with `L<λ'>`                                                                                                                                                                                                | as S1                                                                                                                                                                      | `mixed_lmul<L>_lambda<λ>_imm<λ'>` |
| M1. MACC through tile loads and stores        | `cp_custom_tile_macc` on `vmmacc.vv` rows with `ExtraExtensions=Zvvi<n>mm:Zvvmtls` (4 rows, one per SEW) | Zero the C window (`vmv.v.i`, two m8 groups); `vmtl.v` A (M×K_eff) and B_tile (N×K_eff) at the tile LMUL with natural LD; `vmmacc.vv`; `vmts.v` C at LMUL = `EMUL_C` with LD = M. `EMUL_C` = 16 uses two m8 stores, as ime-test-gen does. | Read the C window back with `vle<SEW>.v` (two m8 groups) and `RVTEST_SIGUPD_V_LEN`.                                                                                        | `lmul<L>_lambda<λ>`               |

M1 details:

- Data: A[i][0] = i, A[i][1] = 1, B_tile[j][0] = 256, B_tile[j][1] = j, and all other k are 0. Then C[i][j] = 256·i + j, so each C word names its row and column. This needs K_eff = λ·LMUL ≥ 2 and SEW ≥ 16. For K_eff = 1, A = 1 and B_tile[j][0] = j give C[i][j] = j.
- The data is VLEN-agnostic, because tile loads place it from a fixed memory layout. That is why ime-test-gen uses tile loads.
- `EMUL_C` = VLEN/(SEW·λ²) depends on VLEN. The `vtype` immediate for the C store is chosen by an `#if UDB_VLEN == …` chain over 128, 256, 512 and 1024. [ACT] `tests/env/utils.h:184-187` already derives `VLEN_BYTES` from `UDB_VLEN`.
- M1 also catches a store-only error at LMUL=1: the C store runs at `EMUL_C` > 1.
- M1 is the ACT form of the first-party test that work item 1 asks the Sail fork to add.

Expected mismatch at the reproducer configuration (VLEN=256, SEW=32, LMUL=2, λ=1, epr=8, linesize=2). "QEMU" is a conforming DUT. "Sail" is the reference that writes the signature.

| Bin                                           | QEMU (specification)                                   | Sail `c69e3e22`                                          | Differing words                        | Source                        |
| --------------------------------------------- | ------------------------------------------------------ | -------------------------------------------------------- | -------------------------------------- | ----------------------------- |
| L1 `vmtl.v`, `lmul2_lambda1_ldnat` (LD=2)     | `v8`: `0 2 4 6 8 10 12 14`, `v9`: `1 3 5 7 9 11 13 15` | `v8`: `0 1 … 7`, `v9`: `8 … 15`                          | 14 of 16                               | `qemu.out`, `sail.out` step 1 |
| L1 `vmtl.v`, `lmul2_lambda1_ldpad` (LD=3)     | `0 3 6 9 12 15 18 21 \| 1 4 7 10 13 16 19 22`          | `0 1 3 4 6 7 9 10 \| 12 13 15 16 18 19 21 22`            | 14 of 16                               | computed                      |
| L1 `vmttl.v`, `lmul2_lambda1_ldnat` (LD=8)    | `0 1 … 15`                                             | `0 8 1 9 2 10 … 7 15`                                    | 14 of 16                               | computed                      |
| S1 `vmts.v`, `lmul2_lambda1_ldnat` (LD=2)     | `0 8 1 9 2 10 3 11 \| 4 12 5 13 6 14 7 15`             | `0 1 … 15`                                               | 14 of 16                               | `qemu.out`, `sail.out` step 2 |
| S1 `vmts.v`, `lmul2_lambda1_ldpad` (LD=3)     | `0 8 – 1 9 – 2 10 – …`                                 | `0 1 – 2 3 – 4 5 – …`                                    | 14 of 16 written words; gaps (–) agree | computed                      |
| R1 `mixed_lmul2_lambda1_imm2`                 | `0 2 1 3 4 6 5 7 \| 8 10 9 11 12 14 13 15`             | `0 1 … 15`                                               | 8 of 16                                | computed                      |
| `same_lmul2_lambda1_ldnat` (control)          | `0 1 … 15`                                             | `0 1 … 15`                                               | 0                                      | `qemu.out`, `sail.out` step 3 |
| M1 `lmul2_lambda1` (M=8, K_eff=2, `EMUL_C`=8) | row 0: `0x0 0x1 … 0x7`; row 1: `0x100 … 0x107`         | row 0: `0x400 0x200 0x600 0x200 0x800 0x200 0xa00 0x200` | 63 of 64                               | computed                      |
| M1 `lmul1_lambda1` (K_eff=1)                  | C[i][j] = j                                            | the transpose, C[i][j] = i                               | 56 of 64 (the diagonal agrees)         | computed                      |

- At other configurations of `qemu-ime-rv64`, L1 differs in 12 of 16 words at λ=2, LMUL=2, and in 30 of 32 words at λ=1, LMUL=4 (computed).
- These bins fail on QEMU until the Sail fix lands, because the signature holds Sail's values. That is the intended signal. The bins are not moved to `ignore_bins`, and `config/ime/ci.yaml` does not exclude them: AGENTS.md reserves `ignore_bins` for architecturally unreachable bins. After the fix, the same bins pass on QEMU and on Sail.

### 4.5 Tests for the W>1 partial sum (a Sail bug)

[Spec] For W>1, the W products of a sub-dot-product are reduced into a partial sum S, and C is updated once per group with round_frm(C + S) (spec:1352-1412; `fp_group_sum` and `fp_gemm` at spec:4446-4490 and 4677-4716).
[Sail] `execute_ime_fp_gemm` adds each product into C on its own (`sail/model/extensions/IME/ime_mem_insts.sail:547-597`). No (G, psm, rnd) tuple describes the result. Under §0.1 this is a Sail bug. The draft issue is `riscv-arch-test-docs/reports/issues/sail-ime-wmmacc-partial-sum/` (work item 10). The SDK QEMU has the same deviation (`qemu/…:610-669`); that is a DUT finding.

- Column `cp_fp_subdot` on the `vfwmmacc.vv`, `vfqmmacc.vv` and `vf8wmmacc.vv` rows with vm=1.
- Data: in one sub-dot-product of C[0][0], W equal products that are exact in the C format. Each product is at most half an ULP of C₀, and together they add up to one ULP of C₀. All other products of the element are zero. The A background is 0 for the other rows.
- Bins: `ulp_<rne|rtz|rdn|rup|rmm>`, one per `frm` value.
- [Inferred] The result does not depend on any permitted choice:
  - S is exact under psm=0 and representable in the C format, so every `rnd` leaves it unchanged.
  - The other sub-dot-products are zero, so G does not matter.
  - C₀ + S is exact, so every `frm` gives C₀ + 1 ULP and raises no flag.
  - [Uncertain] A psm=1 reduction is expected to be exact on W equal powers of two. This must be checked against a disclosed algorithm.
- Expected outcome. Sail writes the per-product result into the signature, so a conforming DUT fails these bins until the Sail fix. The SDK QEMU passes them until then, because it has the same deviation. After the fix, QEMU fails them until QEMU is fixed. The bins stay in place.

| Bin `ulp_rne`, VLEN=256, λ=1 | A[0][k], B[k][0], C₀                             | Specification            | Sail `c69e3e22` and QEMU  | Source   |
| ---------------------------- | ------------------------------------------------ | ------------------------ | ------------------------- | -------- |
| `vfwmmacc.vv` FP16→FP32      | A = B = (2^-12, 2^-12), C₀ = 1.0                 | `0x3f800001` / 0         | `0x3f800000` / NX         | run      |
| `vfwmmacc.vv` BF16→FP32      | same values in BF16 (`0x3980`)                   | `0x3f800001` / 0         | `0x3f800000` / NX         | inferred |
| `vfwmmacc.vv` FP32→FP64      | A = (2^-26, 2^-26), B = (2^-27, 2^-27), C₀ = 1.0 | `0x3ff0000000000001` / 0 | `0x3ff0000000000000` / NX | run      |
| `vfqmmacc.vv` FP16→FP64      | A = B = (0.5, 0.5, 0.5, 0.5), C₀ = 2^52          | `0x4330000000000001` / 0 | `0x4330000000000000` / NX | run      |

The run rows are the reproducer of the draft issue (`fprnd.c`, `sail.out`, `qemu.out`).

## 5. Value patterns

- [ACT] Operands come from seeded random data. The seed is a hash of the instruction and the coverpoint (`coverpoints/registry.py:91-92`).
- [ACT] Edge coverpoints put one edge value in element 0 and fill the rest with fixed values (`load_vec_regs`, `asm/vector_helpers.py:594-680`).
- ime-test-gen uses positional values `val = r·cols + k + 1 + offset` (`ime-test-gen/src/gold/integer.rs:93-118`). FP rows use named value sets (`ime-test-gen/src/gold/fp_matmul.rs:283-310`).

Integer rows:

- Default data is ACT random data. Integer accumulation wraps modulo 2^SEW, so every result is exact ([Spec] spec:1112).
- Positional values give every element a unique value, which helps locate layout bugs. They are kept as one extra edge bin, `ramp`. The bin registers a fixed label through `TestData.register_vector_data(…, elements=[…])` (`data/state.py:239-266`).
- Narrow inputs reuse the `emulf2/4/8` edge path (`data/edges.py:742-782`).
- `edge_value` is pure bit arithmetic (`data/edges.py:603-640`), so it works for EEW=4. [Uncertain] The data-section writer may not emit 4-bit elements. If so, `asm/sections.py` needs a step that packs two elements per byte.

FP rows:

- [Spec] The FP result depends on the (G, psm, rnd) profile. The profile is implementation-defined per (SEW, W, λ), and the implementation must publish it (spec:1376-1460).
  - Each output element is a sum of λ sub-dot-products of W products each. Groups of G sub-dot-products are reduced to a partial sum S (`psm`), S is treated by `rnd`, and then C ← round_frm(C + S).
  - `rnd=frm` rounds S to the C format with `frm`, `rnd=rto` rounds it to odd, and `rnd=xct` keeps it exact (spec:1399-1412).
- [Decision] The target implementation uses G=1: every group is one sub-dot-product of W products. Sail also uses G=1 (§6), so both group the same products.
- [Decision] The target's `psm` and `rnd` are not disclosed. The specification permits `psm` ∈ {0, 1} and `rnd` ∈ {frm, rto, xct}, so by §0.1 the FP data gives the same result for every permitted choice.
- [Run] The random and edge data also keep every running C value exact. They therefore do not see the per-product accumulation of QEMU and Sail for W>1 (§6.1). `cp_fp_subdot` targets that deviation on purpose (§4.5).
- [ACT] Unordered reductions have the same problem. `unordered_sum_rng` exists to "avoid ever setting a rounding bit because implementations are allowed to differ" (`formatters/types/fvvsr_type.py:62-74`). It is plugged in through `VectorTypeConfig.random_element_generator` (`instructions/vector_params.py:528-530`).
- [Proposal] Random data: `exact_dot_rng` generates sparse small integers.
  - Each dot product has length K_eff = λ·W·LMUL ≤ 512. The generator keeps every product, every partial sum and every running C value, in any order, within 2^p, where p is the significand precision of the C format.
  - p is 11 for fp16, 8 for bf16, 24 for fp32, 53 for fp64, 4 for E4M3 and 3 for E5M2.
  - The C initial value is bounded the same way.
  - Every intermediate value is then exact in the C format. S is exact under `psm=0`, and `frm`, `rto` and `xct` all return an exact S unchanged. The result is therefore the same for every `psm=0` profile.
  - [Uncertain] Under `psm=1`, the reduction algorithm is implementation-specific and must be disclosed (spec:1397). Small integer data is expected to stay exact, but this must be checked against the disclosed algorithm.
  - This maps the ime-test-gen sets `ones`, `ramp` and `small`.
- [Proposal] Edge data: FP edges sit in element 0. The A background is 0 and the B background is +1.0. Each affected C element then gets one nonzero product p, so with G=1 the group sum is S = p. Two classes follow:
  - Special values: NaN, ∞, ±0 and 0×∞. The result is fixed by the special-value rules, whatever `psm` and `rnd` are. [Spec] A NaN result is the canonical NaN (spec:1680-1687). This maps TC-SPL.
  - Rounding-sensitive cases: frm sweeps, ties, overflow, underflow and the inexact flag. The edge pair is chosen so that p is exact in the C format, and C₀ is chosen so that C₀ + p rounds, overflows or underflows. The only rounding is then the final round_frm(C₀ + S), which every profile performs. This maps TC-RM, the single-term forms of TC-RND, TC-SUB and TC-FLAG.
  - For W ≥ 2, the product of two narrower inputs is exact in the C format, except at the exponent-range limits. For W=1, the edge table must pick products that are exact. This matters: an inexact W=1 product gives different results on QEMU (rnd=xct) and Sail (rnd=frm) (§6.1).
  - The other W·λ·LMUL − 1 products of the element are zero, for every W. Every implementation then computes round_frm(C₀ + p), including the per-product accumulation of QEMU and Sail.
  - `cp_csr_frm_v` testcases use the rounding-sensitive data. With `exact_dot_rng` data alone, no rounding occurs and `frm` would not be exercised.
  - New edge tables go in `data/edges.py`: FP16 inside SEW=32 (`f_emulf2`), OFP8 and OFP4. Precedent: `f_bf16` (`data/edges.py:766-767`).
- Multi-term tests that need only the specification's S are not deferred. `cp_fp_subdot` covers them now and fails until the Sail fix (§4.5).
- Waiting for a disclosure (§7): data whose result depends on the (G, psm, rnd) choice. Examples are products that are inexact or overflow in the C format, cancellation across k, and accumulation order. Without a disclosure, such tests would depend on a permitted choice (§0.1).
- [Inferred] The exact-sum design follows from §0.1. Sail is rnd=frm and the SDK QEMU is rnd=xct, and both are permitted. A W=1 testcase with an inexact product would depend on that choice.

## 6. Expected values come from Sail

- [ACT] The signature ELF stores Sail's results. The self-checking ELF compares against them (report 1 §10).
- Nothing in the proposal reads `C_ref`, `*.golden.json` or any array from `gold/`. The ime-test-gen checks map as follows:
  - `Compare` becomes `RVTEST_SIGUPD_V_LEN`.
  - `CheckFflags` becomes `RVTEST_SIGUPD_FFLAGS`.
  - `CheckVtypeField` becomes `csrr vtype` plus `RVTEST_SIGUPD`.
- The Rust golden model stays outside ACT, as an optional differential check (`crosscheck.py` in the proof of concept).

Where Sail and the Rust golden model differ for FP:

- Sail discloses G=1, psm=0, rnd=frm. It rounds each product to the C format, then accumulates with `frm` (`sail/model/extensions/IME/ime_mem_insts.sail:450-453`, `:525-526`). Its G=1 matches the target implementation (§5).
- The Rust golden model runs with `--fma` in CI. It does one fused multiply-add per product at an internal format, then rounds to the C format (`ime-test-gen/src/expand_ir.rs:792-806`):
  - the accumulator format for W=1;
  - f32 for inputs of at most 16 bits with W>1;
  - f64 otherwise.
- For W=1 that is rnd=xct, which is legal. The code comment that says it "does NOT match the spec" (`ime-test-gen/src/gold/fp_matmul.rs:164`) is wrong for W=1. QEMU matches the Rust model (report §7).
- The two profiles disagree whenever a product or a partial sum is inexact. That affects the multi-term TC-RND tests, TC-RM with ramp data, and the NX bit in TC-FLAG. With the data of §5, they agree.
- The Rust model is not a source of truth (§0.1). Its differences from Sail or QEMU are findings only.

### 6.1 FP rounding profiles of QEMU, Sail and the Rust model

- [Spec] Legal values: G a power of two with 1 ≤ G ≤ λ, counted in sub-dot-products of W products (spec:1352-1384). psm ∈ {0, 1}: S is the exact sum of the group's products, or a disclosed reduction (spec:1386-1397). rnd ∈ {frm, rto, xct} (spec:1399-1412). Then C ← round_frm(C + S). One tuple per (SEW, W, λ), shared by every format combination and by scaled and unscaled forms (spec:1449-1466). A psm=1 entry also needs a SAIL fragment (spec:1473-1502).
- [Code] QEMU sets the rounding mode from `frm` for every FP mmacc path (`qemu/target/riscv/insn_trans/trans_rvzvvmm.c.inc:2224-2225`). For each C element it does one `*_muladd` per product, k ascending (`:610-669`).

| Rows               | SDK QEMU `d856b96`                                                                                                  | Sail `c69e3e22`                                                                                                   | `ime-test-gen --fma`                                                                                     |
| ------------------ | ------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| W=1, same format   | fused: G=1, psm=0, rnd=xct. Legal. (`qemu/…:1139-1158`)                                                             | `fp_mul` + `fp_add`: G=1, psm=0, rnd=frm. Legal.                                                                  | same as QEMU                                                                                             |
| W=1, mixed formats | `float32_muladd`, then conversion: two roundings. Fits no rnd: DUT finding. (`qemu/…:1040-1136`)                    | not implemented                                                                                                   | one rounding; differs from QEMU                                                                          |
| W>1                | one fused add into C per product. Fits no tuple: QEMU violates the specification (DUT finding).                     | per product; products are exact, so the values equal QEMU's. Fits no tuple, despite the comment: Sail bug (§4.5). | same as QEMU, except f16/bf16/OFP8 into f64, which round the accumulator to f32 each step. Finding only. |
| Microscaled        | f32 scale, per-product rounding over a whole block, fused scale-add. Fits no tuple: DUT finding. (`qemu/…:180-280`) | not implemented                                                                                                   | not generated                                                                                            |

- [Run] Probe results, VLEN=256, λ=1, vl=1 (λ=2, vl=2 for the f16 row):

| Case                                                              | QEMU C / fflags           | Sail C / fflags           | Specification, G=1, psm=0           |
| ----------------------------------------------------------------- | ------------------------- | ------------------------- | ----------------------------------- |
| W=1 f32, RNE, a = b = 1+2^-12, C = −(1+2^-11)                     | `0x33800000` / 0          | `0x00000000` / NX         | xct `0x33800000`, frm `0x00000000`  |
| same, RUP                                                         | `0x33800000` / 0          | `0x34000000` / NX         | xct `0x33800000`, frm `0x34000000`  |
| W=2 f16→f32, RNE, A = B = (2^-12, 2^-12), C = 1.0                 | `0x3f800000` / NX         | `0x3f800000` / NX         | every rnd: `0x3f800001` / 0         |
| W=2 f32→f64, RNE, A = (2^-26, 2^-26), B = (2^-27, 2^-27), C = 1.0 | `0x3ff0000000000000` / NX | `0x3ff0000000000000` / NX | every rnd: `0x3ff0000000000001` / 0 |
| W=4 f16→f64, RNE, A = B = (0.5, 0.5, 0.5, 0.5), C = 2^52          | `0x4330000000000000` / NX | `0x4330000000000000` / NX | every rnd: `0x4330000000000001` / 0 |
| W=1 f16×bf16→f16, RNE, a = `0x3d89`, b = `0x39b9`, C = 1.0        | `0x3c00` / NX             | not implemented           | xct `0x3c01`                        |

- QEMU and Sail differ on every W=1 row when a product is inexact in the C format. The specification permits both profiles, so this is not a conflict (§0.1). On the W>1 rows Sail implements, the values agree, and both are wrong. [Inferred] Flags can still differ when a bf16 product underflows f32 and C ≠ 0: Sail's `fp_mul` raises UF, and QEMU does not.
- Consequence: ACT signatures come from Sail. A W=1 testcase with an inexact product would depend on a permitted choice, so the data of §5 avoids it. A W>1 testcase whose per-product additions round detects the Sail bug; `cp_fp_subdot` does that on purpose (§4.5).
- The probe is now the reproducer in `riscv-arch-test-docs/reports/issues/sail-ime-wmmacc-partial-sum/`, with the W=2 f32→f64 and W=4 f16→f64 rows added.

- Integer results are exact and do not depend on order in either model ([Spec] spec:1112).

## 7. What does not fit, and the least invasive handling

| Item                                                                             | Problem                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Least invasive handling                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| VLEN > 1024                                                                      | [ACT] `RVTEST_VLEN_MAX` is 1024 (`constants.py:166`), and `check_defines.h:232-233` stops vector builds above it. ime-test-gen CI runs up to VLEN 32768.                                                                                                                                                                                                                                                                                                                       | Keep the cap. λ ≥ 16 needs VLEN ≥ 2048 at SEW=8 (spec:798-819), so those `cr_lambda_lmul` bins stay uncovered. They are not ignored (AGENTS.md: leave such bins missing). Raising the cap is a separate change for all of ACT.                                                                                                                                                                                                                          |
| `LambdaProbe` (skip at run time)                                                 | ACT has no run-time skip.                                                                                                                                                                                                                                                                                                                                                                                                                                                      | UDB λ lists plus `#if defined(UDB_SUPPORTED_LAMBDA_SEW<n>_<λ>)` (§1.4).                                                                                                                                                                                                                                                                                                                                                                                 |
| `known-issues.txt`                                                               | ACT has no verdict list.                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Per-DUT `exclude_extensions` in `config/<dut>/ci.yaml`, as in `config/qemu/ci.yaml:8-29`. Uncovered bins report the rest.                                                                                                                                                                                                                                                                                                                               |
| Illegal-instruction cases (ime-test-gen has none)                                | [ACT] Unprivileged tests that may trap belong in the privileged style (`docs/DeveloperGuide.md:270`).                                                                                                                                                                                                                                                                                                                                                                          | `testplans/priv/ExceptionsZvvm.csv` with `@add_priv_test_generator("ExceptionsZvvm", …)`, after `ExceptionsVx` (`priv/extensions/ExceptionsV.py:274-320`, `testplans/priv/ExceptionsVx.csv`). Cases: MACC with vstart ≠ 0; VL not a multiple of λ·LMUL; fractional LMUL; λ = 000; misaligned `vd`, `vs1` or `vs2`; reserved encoding-map rows; vm=0 on `vmmacc.vv`; unsupported immediate λ.                                                            |
| vstart on tile loads and stores (TC-LS-07)                                       | [Spec] A nonzero vstart is legal, and execution resumes (spec:2361-2366).                                                                                                                                                                                                                                                                                                                                                                                                      | `cp_vstart` in `ExceptionsZvvm`, as `ExceptionsVls` does for `vle*.v`.                                                                                                                                                                                                                                                                                                                                                                                  |
| C tile tail with `vta=1`                                                         | [Spec] The tail may hold any value, including its old one (spec:2600-2624). The ACT macro accepts only "unchanged" or "all ones" for an agnostic tail, and its tail is one-dimensional.                                                                                                                                                                                                                                                                                        | MACC tests use `vta=0`, or VL = VLMAX so that there is no tail. The `vta=1` bin with a partial VL stays uncovered until a two-dimensional tail check exists.                                                                                                                                                                                                                                                                                            |
| m16 accumulators                                                                 | ime-test-gen pairs two m8 halves (`AccPair`; `ime-test-gen/src/expand_ir.rs:579-600`).                                                                                                                                                                                                                                                                                                                                                                                         | Not needed in assembly. The 16-register window is loaded and checked as two m8 groups.                                                                                                                                                                                                                                                                                                                                                                  |
| FP profile (G, psm, rnd)                                                         | The profile is implementation-defined, and the specification permits several values. G=1 is confirmed for the target; its `psm` and `rnd` are not disclosed. Sail is rnd=frm for W=1 and the SDK QEMU is rnd=xct; both are permitted. For W>1 both accumulate per product, which fits no tuple (§6.1).                                                                                                                                                                         | Use data that does not depend on the permitted choice (§5, §0.1). Cover the W>1 deviation with `cp_fp_subdot` (§4.5). For tests that depend on the tuple, add overlay parameters `IME_FP_PSM` and `IME_FP_RND`, and gate on macros such as `UDB_IME_FP_RND_frm`. A G parameter is needed only for a DUT with G ≠ 1. Precedent: `UDB_VFREDUSUM_NODE_ROUNDING_BEHAVIOR_*` for unordered reductions. Sail must then read the same values from `sail.json`. |
| OFP8, OFP4, BF16 output, microscaling                                            | The Sail fork does not implement them (`ime_mem_insts.sail:440-449`).                                                                                                                                                                                                                                                                                                                                                                                                          | Write the rows anyway. No DUT configuration lists these extensions, so `act` never selects their tests. The bins stay uncovered. Rows with BF16 or E5M2 output also require Zvfbfa.                                                                                                                                                                                                                                                                     |
| `Zvvmttls` on QEMU                                                               | This QEMU decodes only mop=00 (report §16a).                                                                                                                                                                                                                                                                                                                                                                                                                                   | Generate the suite. `qemu-ime-rv64` does not list `Zvvmttls`.                                                                                                                                                                                                                                                                                                                                                                                           |
| Sail tile-index bug                                                              | Expected values are wrong for tile loads and stores at LMUL>1, and for C stores at `EMUL_C` > 1.                                                                                                                                                                                                                                                                                                                                                                               | The MACC suites are unaffected because they use no tile instructions. Tile bins at LMUL>1, and the `cp_custom_tile_*` bins of §4.4, fail on a conforming DUT until the Sail fix (work item 1). They stay in place as the signal for that fix.                                                                                                                                                                                                           |
| Sail W>1 FP accumulation                                                         | Sail adds each product into C on its own instead of forming S (§4.5).                                                                                                                                                                                                                                                                                                                                                                                                          | `cp_fp_subdot` bins follow the specification and fail on a conforming DUT until the Sail fix (work item 10). They pass on QEMU until then.                                                                                                                                                                                                                                                                                                              |
| Sail tile loads and stores: LD and legality                                      | Sail uses LD = 0 for a register holding 0 (§3.4). Its tile loads do not raise an illegal-instruction exception when VL is not a multiple of λ·LMUL, or for a masked load whose `vd` is `v0` (spec:5874-5881).                                                                                                                                                                                                                                                                  | The `cp_ld` bin with 0 in a register fails until the Sail fix. The negative cases in `ExceptionsZvvm` follow the specification (work item 12).                                                                                                                                                                                                                                                                                                          |
| Sail accepts λ values the specification does not permit, and rejects `EMUL_C`=16 | [Sail bug] Sail accepts any λ ≤ VLEN/SEW (`sail/model/extensions/IME/ime_utils.sail:34-54`), including λ with `EMUL_C` < 1, which the specification does not permit (spec:811-815). Its MACC raises an illegal-instruction exception for `EMUL_C`=16 (`ime_utils.sail:91-92`, used at `ime_mem_insts.sail:244` and `:497`), which the specification permits (spec:381).                                                                                                        | The UDB λ lists follow the specification. Positive tests are safe because of the gating. `cr_lambda_lmul` bins with `EMUL_C`=16, such as SEW=16 with λ=1 at VLEN=256, stay and fail until the Sail fix (work item 11). The unsupported-λ cases in `ExceptionsZvvm` follow the specification and need a configurable λ set in Sail.                                                                                                                      |
| Coverage                                                                         | IME instructions are not decoded, and fcov has no IME vtype fields.                                                                                                                                                                                                                                                                                                                                                                                                            | §3.5. Coverage measurement is the last step.                                                                                                                                                                                                                                                                                                                                                                                                            |
| `altfmt` for FP output                                                           | [Spec silent] IME uses the Zvfbfa `altfmt` bit "as defined by Zvfbfa" (spec:692-697, 1202). The specification does not say whether an implementation without Zvfbfa has the field. [Sail] Sail has no Zvfbfa (`sail/model/core/extensions.sail` defines no `Ext_Zvfbfa`). Bit 8 of `vtype` lies in its reserved range (`sail/model/extensions/V/vext_regs.sail:249`), and `vsetvl` takes the illegal-`vtype` path when a reserved bit is set (`vext_vset_insts.sail:198-199`). | Spec silent; Sail behaviour: `altfmt=1` needs Zvfbfa. Rows with BF16 or E5M2 output list `Zvfbfa` in `ExtraExtensions` beside the type extension. UDB 0.1.18 defines Zvfbfa.                                                                                                                                                                                                                                                                            |
| RV32                                                                             | ime-test-gen and the SDK QEMU support only RV64.                                                                                                                                                                                                                                                                                                                                                                                                                               | Set `RV32=x` in the CSVs, because the vtype fields are defined relative to XLEN ([Spec] spec:686-690). The first slices run only RV64. [Uncertain] RV32 support in the Sail fork.                                                                                                                                                                                                                                                                       |

## 8. Draft CSVs

### 8.1 `testplans/Zvvmm.csv` (complete)

```csv
Instruction,Type,RV32,RV64,ExtraExtensions,EFFEW8,EFFEW16,EFFEW32,EFFEW64,cp_asm_count,cp_vd,cp_vs1,cp_vs2,cp_vd_edges,cp_vs1_edges,cp_vs2_edges,cp_altfmt,cr_lambda_lmul,cp_tile_vl,cp_custom_tile_macc
vmmacc.vv,MMACC,x,x,Zvvi8mm,x,,,,x,emul16,x,x,x,x,x,x,x,x,
vmmacc.vv,MMACC,x,x,Zvvi16mm,,x,,,x,emul16,x,x,x,x,x,x,x,x,
vmmacc.vv,MMACC,x,x,Zvvi32mm,,,x,,x,emul16,x,x,x,x,x,x,x,x,
vmmacc.vv,MMACC,x,x,Zvvi64mm,,,,x,x,emul16,x,x,x,x,x,x,x,x,
vwmmacc.vv,MMACC,x,x,Zvvi4i8mm,x,,,,x,emul16,x,x,x,emulf2,emulf2,x,x,x,
vwmmacc.vv,MMACC,x,x,Zvvi8i16mm,,x,,,x,emul16,x,x,x,emulf2,emulf2,x,x,x,
vwmmacc.vv,MMACC,x,x,Zvvi16i32mm,,,x,,x,emul16,x,x,x,emulf2,emulf2,x,x,x,
vwmmacc.vv,MMACC,x,x,Zvvi32i64mm,,,,x,x,emul16,x,x,x,emulf2,emulf2,x,x,x,
vqmmacc.vv,MMACC,x,x,Zvvi4i16mm,,x,,,x,emul16,x,x,x,emulf4,emulf4,x,x,x,
vqmmacc.vv,MMACC,x,x,Zvvi8i32mm,,,x,,x,emul16,x,x,x,emulf4,emulf4,x,x,x,
vqmmacc.vv,MMACC,x,x,Zvvi16i64mm,,,,x,x,emul16,x,x,x,emulf4,emulf4,x,x,x,
v8wmmacc.vv,MMACC,x,x,Zvvi4i32mm,,,x,,x,emul16,x,x,x,emulf8,emulf8,x,x,x,
v8wmmacc.vv,MMACC,x,x,Zvvi8i64mm,,,,x,x,emul16,x,x,x,emulf8,emulf8,x,x,x,
vmmacc.vv,MMACC,x,x,Zvvi8mm:Zvvmtls,x,,,,,,,,,,,,,,x
vmmacc.vv,MMACC,x,x,Zvvi16mm:Zvvmtls,,x,,,,,,,,,,,,,x
vmmacc.vv,MMACC,x,x,Zvvi32mm:Zvvmtls,,,x,,,,,,,,,,,,x
vmmacc.vv,MMACC,x,x,Zvvi64mm:Zvvmtls,,,,x,,,,,,,,,,,x
```

The last four rows carry only `cp_custom_tile_macc` (§4.4). Their tests require `Zvvmtls` in addition, so they get their own file prefix, for example `Zvvmm32Zvvi32mmZvvmtls-vmmacc.vv-00.S`.

### 8.2 `testplans/Zvvfmm.csv` (representative rows)

```csv
Instruction,Type,RV32,RV64,ExtraExtensions,EFFEW8,EFFEW16,EFFEW32,EFFEW64,cp_asm_count,cp_vd,cp_vs1,cp_vs2,cp_vd_edges,cp_vs1_edges,cp_vs2_edges,cr_vs1_vs2_edges,cp_altfmt,cr_lambda_lmul,cp_tile_vl,cp_csr_frm,cp_csr_fflags,cp_fp_subdot,cp_scale
vfmmacc.vv,FMMACC,x,x,Zvvfp32mm,,,x,,x,emul16,x,x,f,f,f,f,x,x,x,v,voun,,
vfmmacc.vv,FMMACC,x,x,Zvvfp64mm,,,,x,x,emul16,x,x,f,f,f,f,x,x,x,v,voun,,
vfmmacc.vv,FMMACC,x,x,Zvvfp16mm,,x,,,x,emul16,x,x,f,f,f,f,x,x,x,v,voun,,
vfmmacc.vv,FMMACC,x,x,Zvvbf16mm,,x,,,x,emul16,x,x,f_bf16,f_bf16,f_bf16,f_bf16,x,x,x,v,voun,,
vfmmacc.vv,FMMACC,x,x,Zvvfp16mm:Zvvbf16mm,,x,,,x,emul16,x,x,f,f,f_bf16,,x,x,x,v,voun,,
vfmmacc.vv,FMMACC,x,x,Zvvofp8mm,x,,,,x,emul16,x,x,f_ofp8,f_ofp8,f_ofp8,f_ofp8,x,x,x,v,voun,,
vfwmmacc.vv,FMMACC,x,x,Zvvfp16fp32mm,,,x,,x,emul16,x,x,f,f_emulf2,f_emulf2,f_emulf2,x,x,x,v,voun,x,
vfwmmacc.vv,FMMACC,x,x,Zvvbf16fp32mm,,,x,,x,emul16,x,x,f,f_bf16,f_bf16,f_bf16,x,x,x,v,voun,x,
vfwmmacc.vv,FMMACC,x,x,Zvvfp16fp32mm:Zvvbf16fp32mm,,,x,,x,emul16,x,x,f,f_emulf2,f_bf16,,x,x,x,v,voun,x,
vfwmmacc.vv,FMMACC,x,x,Zvvfp32fp64mm,,,,x,x,emul16,x,x,f,f_emulf2,f_emulf2,f_emulf2,x,x,x,v,voun,x,
vfwmmacc.vv,FMMACC,x,x,Zvvofp8fp16mm,,x,,,x,emul16,x,x,f,f_ofp8,f_ofp8,f_ofp8,x,x,x,v,voun,x,
vfqmmacc.vv,FMMACC,x,x,Zvvfp16fp64mm,,,,x,x,emul16,x,x,f,f_emulf4,f_emulf4,f_emulf4,x,x,x,v,voun,x,
vf8wmmacc.vv,FMMACC,x,x,Zvvofp8fp64mm,,,,x,x,emul16,x,x,f,f_ofp8,f_ofp8,f_ofp8,x,x,x,v,voun,x,
vfwmmacc.vv,FMMACC_MX,x,x,Zvvxofp8fp16mm,,x,,,x,emul16,x,x,f,f_ofp8,f_ofp8,,x,x,x,v,voun,,x
vfwmmacc.vv,FMMACC_MX,x,x,Zvvxnofp8fp16mm,,x,,,x,emul16,x,x,f,f_ofp8,f_ofp8,,x,x,x,v,voun,,x
vfwimmacc.vv,MMACC_MX,x,x,Zvvxi8fp16mm,,x,,,x,emul16,x,x,f,emulf2,emulf2,,x,x,x,v,voun,,x
```

Notes:

- `f_ofp8` covers E4M3 edges with `altfmt=0` and E5M2 edges with `altfmt=1`. The `cp_altfmt` bins drive the mixed combinations.
- In a mixed FP16/BF16 row, the edge suffix follows the operand: FP16 for `vs1` and BF16 for `vs2`. `cp_altfmt` adds the swapped order.
- `cp_fp_subdot` (§4.5) is set on the unscaled rows with W>1.

### 8.3 `testplans/Zvvmtls.csv` and `testplans/Zvvmttls.csv` (complete)

```csv
Instruction,Type,RV32,RV64,ExtraExtensions,EFFEW8,EFFEW16,EFFEW32,EFFEW64,cp_asm_count,cp_vd,cp_vs3,cp_rs1,cp_rs2,cp_ld,cp_imm_lambda,cp_masking_edges,cr_lambda_lmul,cp_tile_vl,cr_tile_vtype_agnostic,cp_custom_tile_layout,cp_custom_tile_roundtrip
vmtl.v,VLT,x,x,,x,x,x,x,x,x,,nx0,x,x,x,x,x,x,x,x,
vmts.v,VST,x,x,,x,x,x,x,x,,x,nx0,x,x,x,x,x,x,,x,x
```

```csv
Instruction,Type,RV32,RV64,ExtraExtensions,EFFEW8,EFFEW16,EFFEW32,EFFEW64,cp_asm_count,cp_vd,cp_vs3,cp_rs1,cp_rs2,cp_ld,cp_imm_lambda,cp_masking_edges,cr_lambda_lmul,cp_tile_vl,cr_tile_vtype_agnostic,cp_custom_tile_layout,cp_custom_tile_roundtrip,cp_custom_tile_crossmode
vmttl.v,VLT,x,x,,x,x,x,x,x,x,,nx0,x,x,x,x,x,x,x,x,,
vmtts.v,VST,x,x,,x,x,x,x,x,,x,nx0,x,x,x,x,x,x,,x,x,
vmttl.v,VLT,x,x,Zvvmtls,x,x,x,x,,,,,,,,,,,,,,x
vmtts.v,VST,x,x,Zvvmtls,x,x,x,x,,,,,,,,,,,,,,x
```

- The `Zvvmtls` rows of `Zvvmttls.csv` hold the cross-mode pairs: `vmttl.v` then `vmts.v` (TC-LS-04), and `vmtl.v` then `vmtts.v` (TC-LS-03). The labelled instruction is the transposing one.
- `qemu-ime-rv64` does not list `Zvvmttls`, so it selects none of the `Zvvmttls.csv` tests.

### 8.4 One generated testcase

- File: `tests/rv64i/Zvvmm32/Zvvmm32Zvvi32mm-vmmacc.vv-00.S`.
- Bin: `cr_lambda_lmul` with λ=2, LMUL=2 and VL = VLMAX.
- The header is what testgen already emits for this suite name and row. The experiment output in §1.3 has the same form.

```asm
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I', 'Zvvmm', 'Zvvi32mm', 'Zve32x']
# params:
#   MXLEN: 64
# MARCH: rv64i_zicsr_zifencei_zve32x_zvvi32mm_zvvmm
##### END_TEST_CONFIG #####

#define SIGUPD_COUNT …
#define RVTEST_VECTOR
#define RVTEST_SEW 32
#define VDSEW 32
#define RVTEST_VLEN_MAX 1024
#define RVTEST_EXPERIMENTAL
#include "riscv_arch_test.h"
…
# Testcase cr_lambda_lmul (Test lambda = 2, lmul = 2, vl = vlmax)
#if defined(UDB_SUPPORTED_LAMBDA_SEW32_2)
# C window v16-v31: two m8 loads of random e32 data
  vsetvli x17, x0, e32, m8, tu, mu
  LA (x17, vd_ime_c_random_e32)
  vle32.v v16, (x17)
  csrr x20, vlenb
  slli x20, x20, 3
  add x17, x17, x20
  vle32.v v24, (x17)
# A (vs1 = v4) and B (vs2 = v10) at LMUL=2, VL=VLMAX
  vsetvli x17, x0, e32, m2, tu, mu
  LA (x17, vs1_random_length_012)
  vle32.v v4, (x17)
  LA (x17, vs2_random_length_012)
  vle32.v v10, (x17)
# vtype: lambda[2:0]=010 at bits 62:60, altfmt_A=0, altfmt_B=0, vma=0, vta=0, vsew=e32, vlmul=m2
  LI (x20, 0x2000000000000011)
  vsetvl x17, x0, x20
Zvvmm32Zvvi32mm_vmmacc_vv_cg_cr_lambda_lmul_lambda_2_lmul_2_vl_vlmax:
  vmmacc.vv v16, v4, v10
# Check the C window at e32, m8, VL=VLMAX: every element is a body element
  vsetvli x17, x0, e32, m8, tu, mu
  RVTEST_SIGUPD_V_LEN(x2, x5, x4, x7, x29, v0, v8, v9, v11, v16, v4, v0, 0, 0, 0, 32, 8, 0, 0, Zvvmm32Zvvi32mm_vmmacc_vv_cg_cr_lambda_lmul_lambda_2_lmul_2_vl_vlmax, Zvvmm32Zvvi32mm_vmmacc_vv_cg_cr_lambda_lmul_lambda_2_lmul_2_vl_vlmax_str)
  RVTEST_SIGUPD_V_LEN(x2, x5, x4, x7, x29, v0, v8, v9, v11, v24, v4, v0, 0, 0, 0, 32, 8, 0, 0, Zvvmm32Zvvi32mm_vmmacc_vv_cg_cr_lambda_lmul_lambda_2_lmul_2_vl_vlmax, Zvvmm32Zvvi32mm_vmmacc_vv_cg_cr_lambda_lmul_lambda_2_lmul_2_vl_vlmax_str)
#endif
```

Notes:

- On `qemu-ime-rv64` (VLEN=256), SEW=32 with λ=2 gives M=4 and `EMUL_C`=2. C occupies v16-v17. The check also verifies that v18-v31 kept their initial values.
- The temporaries v0-v7, v8, v9 and v11 reuse the A and B registers after their last use. `vvv_type.py:270-272` frees `vs1` and `vs2` before the check in the same way.
- `vsetvli` at `e32` keeps λ=2. [Spec] A change of LMUL alone does not change λ (spec:741).
- [Uncertain] On its slow mask path, `RVTEST_SIGUPD_V_LEN` switches to `e8` (label 4 in `signature.h`). That re-evaluates λ for SEW=8. It is harmless here, because the next testcase sets vtype again. It should still be confirmed in Sail.

## 9. Effort and order of work

Each typical change has a precedent:

- New CSVs: every extension.
- Suite expansion entries: commit `a726e43af`.
- `vector_map` entries: Zvfbfwma.
- New formatter files: Zibi `bi_type.py`.
- New `VectorTypeConfig` and `InstructionParams` fields: `egs`, `index_register`.
- New coverpoint generators and templates: Zibi, vector crypto.
- `edges.py` tables: `f_bf16`, crypto.
- `disassemble.svh` entries: Zibi.
- A privileged `Exceptions*` suite: `ExceptionsVx`.

Two changes are not typical but are small: the `ExtraExtensions` fix in covergroupgen, which is a bug fix, and emitting 4-bit data.

No change is needed in `act`, `select_tests`, the build DAG or the signature macros.

| #   | Step                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Depends on                                                         | Effort              |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ | ------------------- |
| 1   | **Slice 1.** `Zvvmm.csv` with one row (`vmmacc.vv`, `Zvvi32mm`, EFFEW32) and the columns `cp_asm_count` and `cr_lambda_lmul`. Code: suite expansion in testgen and covergroupgen; the `ExtraExtensions` fix; the `MMACC` formatter with the `vd`/`vs1`/`vs2` overlap constraint; `load_ime_vtype`; the λ gate; `fixed_emul`; the `cr_lambda_lmul` generator; `sample_MMACC.sv` and a `cr_lambda_lmul` template. Run `EXTENSIONS=Zvvmm32 ENABLE_EXPERIMENTAL_EXTENSIONS=True make qemu-ime-rv64`. Expected: pass for λ ∈ {1,2} on QEMU and on Sail. | none (no tile instructions)                                        | 3-4 days            |
| 2   | All 13 integer rows. Add `cp_altfmt`, `cp_vd_emul16`, `cp_vs1`, `cp_vs2`, `cp_vd_edges`, `cp_vs*_edges_emulf*` (with Int4 data emission), `cp_tile_vl` and the `ramp` bin. `cr_lambda_lmul` bins with `EMUL_C`=16 fail until the Sail λ fix (work item 11).                                                                                                                                                                                                                                                                                        | 1                                                                  | 4-5 days            |
| 3   | `Zvvmtls.csv`: `VLT` and `VST`, `cp_ld`, `cp_imm_lambda` with the vtype check, `cp_masking_edges`, `cr_tile_vtype_agnostic`, and the register and `rs1`/`rs2` coverpoints. LMUL=1 bins pass at once. LMUL>1 bins pass on QEMU only after the Sail tile-index fix.                                                                                                                                                                                                                                                                                  | 1; Sail fix for LMUL>1                                             | 4-5 days            |
| 3a  | `cp_custom_tile_layout` on `vmtl.v` and `vmts.v`, and `cp_custom_tile_roundtrip` (`same` and `mixed` bins) on `vmts.v`: ramp data label, `vid.v` setup, the double λ gate. Expected on `qemu-ime-rv64` before the Sail fix: LMUL=1 and `same` bins pass; LMUL>1 layout bins and `mixed` bins fail with the values of §4.4. After the fix: all pass. This step is the ACT regression test for work item 1.                                                                                                                                          | 3                                                                  | 2-3 days            |
| 3b  | `cp_custom_tile_macc` and the four `Zvvi<n>mm:Zvvmtls` rows of `Zvvmm.csv`: A/B data, the `UDB_VLEN` chain for the C store, two m8 halves at `EMUL_C`=16. Same expectation as 3a.                                                                                                                                                                                                                                                                                                                                                                  | 2, 3a                                                              | 2 days              |
| 4   | The `Zvvfmm.csv` rows that Sail implements: W=1 FP16, FP32 and FP64; FP16 and BF16 to FP32 and FP64; FP32 to FP64. Add `exact_dot_rng`, the two classes of FP edge data, `cp_csr_frm_v`, `cp_csr_fflags`, `cp_fp_subdot` and the `vector_map` entries. The `cp_fp_subdot` bins fail on a conforming DUT until the Sail fix (work item 10), and pass on QEMU until then.                                                                                                                                                                            | 2                                                                  | 5-7 days            |
| 5   | `Zvvmttls.csv`, reusing steps 3 and 3a, with `cp_custom_tile_crossmode` on the `Zvvmtls` rows. It runs only on Sail until QEMU decodes mop≠00.                                                                                                                                                                                                                                                                                                                                                                                                     | 3, 3a                                                              | 2-3 days            |
| 6   | Coverage: IME entries in `disassemble.svh`, vtype fields in `RISCV_coverage_csr.svh`, and all templates, including the four `cp_custom_tile_*` templates. Then run `make coverage EXTENSIONS=Zvvmm32` with Sail.                                                                                                                                                                                                                                                                                                                                   | 2-5                                                                | 4-6 days            |
| 7   | The `ExceptionsZvvm` privileged suite: illegal cases and vstart.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | 3, 4                                                               | 4-5 days            |
| 8   | FP profile parameters (`psm`, `rnd`) in the overlay, and the tests whose result depends on the disclosed tuple. Sail must read the profile.                                                                                                                                                                                                                                                                                                                                                                                                        | 4; Sail change; disclosure of `psm` and `rnd`                      | 3-4 days (ACT side) |
| 9   | Rows for OFP8, OFP4, BF16 output and microscaling: edge tables, `cp_scale`, `FMMACC_MX` and `MMACC_MX`.                                                                                                                                                                                                                                                                                                                                                                                                                                            | Sail implementation; answer to question 1 for BF16 and E5M2 output | 5-7 days            |

Steps 1-7 take about 6-8 engineer-weeks. Steps 8 and 9 depend on work outside ACT.

## 10. Open questions

1. **User decision.** May the MACC `vd` group overlap `vs1` or `vs2`? The specification is silent, and Sail computes overlapping groups in place without a trap (§3.2). Under §0.1 that allows overlap, with Sail's result. The earlier project statement forbids it. The design keeps the non-overlap constraint until this is decided. If overlap is allowed, `cmp_vd_vs1` and `cmp_vd_vs2` bins can be added, with expected values from Sail.
2. Which `psm` and `rnd` does the target implementation use for each (SEW, W, λ)? If any entry uses `psm=1`, which reduction algorithm does it disclose? The answer decides how much of TC-RND and TC-RM can run (§5, §7). The SDK QEMU shows rnd=xct for same-format W=1 rows only; it is not a disclosure (§6.1).
3. Does the Sail fork support RV32, Int4 and W=1 BF16 rows? Does QEMU support Int4?

Answered on 2026-10-27:

- λ selection: per testcase (§1.4).
- Source of truth: the specification, then the Sail fork where the specification is silent (§0.1).
- Zvfbfa for an FP output with `altfmt=1`: required (spec silent; Sail behaviour, §7).
- W>1 partial sum: Sail must form S before C is updated (§4.5, work item 10).
- MACC register overlap: reopened as question 1. The earlier answer (`vd` must not overlap `vs1` or `vs2`) conflicts with Sail's behaviour, and the specification is silent (§3.2).
- Rounding grouping: G=1 (§5).
- Profiles of the SDK QEMU and of Sail (§6.1).
