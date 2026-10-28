<!-- SPDX-License-Identifier: Apache-2.0 -->

# Handoff: migrate ime-test-gen tests to ACT4

This file is self-contained. It tells an agent or engineer what exists, how to set up, which rules apply, and
what to do next. The full testplan design is in [ime-act-testplan-design.md](ime-act-testplan-design.md) in this
folder. Read this file first, then the design sections it names.

State as of 2026-10-28, after step 2.

## 1. Goal

Bring the tests of the Rust generator `ime-test-gen` (repository `riscv-ime-arch-tests`) into ACT4
(`riscv-arch-test`). The target is the native ACT form, "option C": testplan CSVs, instruction formatters,
coverpoint generators and covergroup templates in `testgen` and `covergroupgen`. Expected values come from the
Sail reference model, not from the Rust golden model.

## 2. Repositories, branches and paths

All paths are under `/srv/nfs/shared/home/constantino.gomez/` (written `~/` below).

| What                       | Path                                                                              | Branch / commit                                                       |
| -------------------------- | --------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| ACT4 (code work)           | `~/repo/ime/riscv-arch-test`                                                      | `cgomez/import-ime-tests-to-act4`, 9 commits on `act4` `d41bdd86a`    |
| ACT4 reports (docs work)   | `~/repo/ime/riscv-arch-test-docs` (worktree)                                      | `docs/act-ime-reports`, rebased on `origin/act4`                      |
| Rust generator             | `~/repo/ime/riscv-ime-arch-tests`                                                 | `46f3781`, generator in `ime-test-gen/`, plans in `src/dsl_plans.rs`  |
| Sail fork (reference)      | `~/repo/ime/sail-riscv`                                                           | `cgomez/0.16-plus-ime` @ `c69e3e22` (Sail 0.16 + 8 IME commits)       |
| Sail binary                | `~/repo/ime/sail-riscv/build-016/c_emulator/sail_riscv_sim`                       | built from `c69e3e22`; do not rebuild into this dir                   |
| SDK image (GCC 16.1, QEMU) | `~/repo/ime/sdk-2026.10.14.sif`                                                   | QEMU = `Openchip-Software/riscv-ime-qemu` `vrull/ime-wip` @ `d856b96` |
| IME specification          | https://github.com/riscv/integrated-matrix-extension `src/integrated-matrix.adoc` | `6effbcae` (head of `main` on 2026-10-27)                             |

Reports (HTML, open in a browser) in `~/repo/ime/riscv-arch-test-docs/reports/`:

- `act-architecture.html`: Report 1, how ACT4 works. Read §7 Generate, §10 Check, Example C and §16 Extension
  points.
- `ime-testgen-to-act.html`: Report 2, the IME generator and its integration. §16a is the bring-up, §16b the
  testplan design, §17 the work plan, §18 the findings.
- `issues/sail-ime-tile-ls-index/` and `issues/sail-ime-wmmacc-partial-sum/`: reproducers and draft GitHub
  issues for two Sail bugs. Neither is filed.

## 3. Environment

```bash
cd ~/repo/ime/riscv-arch-test
source ~/tools/act4/env.sh   # mise, uv, prek; sets XDG_DATA_HOME on local disk (UDB flock fails on NFS)
export PATH=$PWD/config/ime/bin:$PATH
export SDK_SIF=~/repo/ime/sdk-2026.10.14.sif
export SAIL_IME_SIM=~/repo/ime/sail-riscv/build-016/c_emulator/sail_riscv_sim
```

- `config/ime/bin` wraps the SDK GCC, as, objdump, nm and QEMU (through `apptainer exec $SDK_SIF`) and the Sail
  binary (always with `--enable-experimental-extensions`). See `config/ime/README.md`.
- Simulator runs are fast and run on the login host. For CPU-heavy work (Sail rebuilds, long sweeps) use the
  `moon-job` skill, which runs on a compute node inside the SDK image.
- IME tests need `ENABLE_EXPERIMENTAL_EXTENSIONS=True` (Make) or `--enable-experimental-extensions` (`act`).
  Without it ACT skips them.

## 4. Rules

1. **AGENTS.md** in `riscv-arch-test` applies. Main points: use `uv run` or Make, never bare `python`/`pip`;
   Python 3.10; Ruff and Pyright pass; SPDX header on new files; use `LI()`/`LA()`, never `li`/`la`; use
   `.p2align`/`.balign`, never `.align`; registry modules are discovered automatically; do not hand-edit
   generated files under `tests/` or `coverpoints/`; use `ignore_bins` only for architecturally unreachable
   bins.
2. **Source of truth** (project decision, 2026-10-27). The IME specification decides every conflict. Where the
   specification is silent or ambiguous, the Sail fork decides. QEMU, the SDK GCC and the Rust golden model never
   decide.
   - Sail contradicts the specification: test bins follow the specification, stay in place, and fail until Sail
     is fixed. Do not add `ignore_bins` or CI exclusions for them.
   - The specification permits several behaviours: tests must not depend on the choice.
   - The specification is silent: follow the Sail code and record "spec silent; Sail behaviour" with a citation.
3. **Where work goes.** Code goes on `cgomez/import-ime-tests-to-act4`. Reports go on `docs/act-ime-reports` in
   the docs worktree. After each meaningful code step, add a documentation step to the reports, rebuild them
   (`reports/README.md`), and commit there. Keep `docs/act-ime-reports` rebased on `origin/act4`.
4. **Commits.** Run `mise run prek` (or `prek run --files <files>`) first and fix failures. Sign off with
   `git commit -s`. No AI or agent authorship trailers. Subject: imperative, at most 72 characters, no period.
   Body: what was wrong and what it is now, in plain technical English. Do not push without approval.

## 5. Current status

Done on `cgomez/import-ime-tests-to-act4`:

| Commit      | What                                                                                                           |
| ----------- | -------------------------------------------------------------------------------------------------------------- |
| `d8e2f05ca` | UDB overlay `framework/src/act/data/udb_overlays/ime`: 65 Zvv\* extensions, `SUPPORTED_LAMBDA_SEW{8,16,32,64}` |
| `24c90741c` | Zvv\* marked experimental; `.insn` macros for every IME instruction in `tests/env/rvtest_experimental.h`       |
| `732f78d72` | DUT configuration `config/ime/qemu-ime-rv64`: SDK QEMU as DUT, Sail IME as reference; CI disabled              |
| `b8a6aaee7` | covergroupgen: `ExtraExtensions` rows in per-SEW testplans get covergroups, filtered by `EFFEW`                |
| `bf7ed4c5e` | Slice 1: `testplans/Zvvmm.csv`, `MMACC` formatter, `cr_lambda_lmul`, `fixed_emul`, `load_ime_vtype`, λ gate    |
| `52218040e` | Step 2: the 13 integer rows of `Zvvmm.csv`                                                                     |
| `2cd759066` | Step 2: `cp_vd_emul16`, `cp_vs1`, `cp_vs2`, `cp_altfmt`; λ chain for coverpoints that do not choose λ          |
| `b1964e4bf` | Step 2: `cp_vd_edges`, `cp_vs1_edges`, `cp_vs2_edges` (`emulf2/4/8` for W>1, 4-bit edges for Int4)             |
| `089da6013` | Step 2: `cp_tile_vl` (one column, VLMAX/2, VLMAX, random multiple of λ·LMUL)                                   |

Verified on `qemu-ime-rv64` (QEMU as DUT, signatures from Sail):

- The I suite passes 51 of 51.
- `Zvvmm`: the 10 files for SEW 8, 32 and 64 pass, Int4 rows included. QEMU and Sail both execute Int4.
- The 3 files for SEW 16 fail in the Sail signature run. At VLEN 256, SEW 16 and λ=1, EMUL_C is 16, which the
  specification permits and Sail rejects (`ime_group_size_legal`, work item 11). λ=1 is the smallest λ at SEW 16,
  so every base-suite testcase uses it. With λ=1 removed from a scratch copy of the DUT configuration, the 3 files
  pass. Fixing work item 11 in Sail unblocks them.
- Full `make tests` changes no other suite.

How to build and run Zvvmm. Make has no keep-going option, so call `act -k` to build past the SEW=16 failures:

```bash
uv run covergroupgen testplans --extensions Zvvmm8,Zvvmm16,Zvvmm32,Zvvmm64
uv run testgen testplans -o tests --extensions Zvvmm8,Zvvmm16,Zvvmm32,Zvvmm64
uv run act config/ime/qemu-ime-rv64/test_config.yaml --workdir work --test-dir tests \
  --extensions Zvvmm8,Zvvmm16,Zvvmm32,Zvvmm64 --enable-experimental-extensions -k
for d in work/qemu-ime-rv64/elfs/rv64i/Zvvmm*; do ./run_tests.py "$(cat config/ime/qemu-ime-rv64/run_cmd.txt)" $d; done
```

IME code in testgen, for reuse in later steps:

- `formatters/types/mmacc_type.py`: the `MMACC` type. C is a 16-register window (`fixed_emul={"vd": 16}`). Base-suite
  callers (the generic `cp_vd`, `cp_vs*`, `cp_*_edges` generators) run at VL=VLMAX. `extend_label` extends their
  data labels to fill A, B and C, and packs narrow edge values into input element 0.
- `asm/vector_helpers.py`: `ime_lambdas`, `ime_vtype_value`, `load_ime_vtype` and the `ime_lambda` argument of
  `handle_parameter_exclusions`. `params.lambda_ = None` emits an `#if/#elif` chain that selects the smallest λ the
  DUT supports. `load_ime_vtype` supports VL = n columns, `"half"`, `"vlmax"` and `"random"`.
- `InstructionParams`: `lambda_`, `altfmt_a`, `altfmt_b`. `VectorLength` includes `"half"`. No `bs` or `ld_mode` yet.
- Generators: `cr_lambda_lmul`, `cp_altfmt` (integer signedness), `cp_tile_vl`.
- Coverage: `get_csr_val` decodes `vtype.lambda`, `altfmt_a` and `altfmt_b`. `vs_edges_check` handles EEW 4.
  `ime_column_vl` gives λ·LMUL. Templates `sample_MMACC`, `cr_lambda_lmul`, `cp_altfmt`, `cp_tile_vl`,
  `cp_vd_emul16`, `cp_vd_edges`, `cp_vs1_edges_emulf2/4/8`. Coverage has not been run (needs step 6).

Known ACT issues (Report 2, §18, findings 23-28): `make tests` stamps ignore `EXTENSIONS`; the Make run
targets have no keep-going option; `run_tests.py` also runs stale ELFs left in `work/<config>/elfs`. Use the
commands above and remove stale ELFs before a run.

Not done: the `ramp` bin of step 2; other `testplans/Zvv*.csv`; tile formatters; IME decoding in `disassemble.svh`.

## 6. Next steps

The full table, with effort and dependencies, is §9 of the design. Summary:

| #   | Step                                                                                                     | Effort   |
| --- | -------------------------------------------------------------------------------------------------------- | -------- |
| 1   | **Done** (`bf7ed4c5e`). Slice 1: `Zvvmm.csv` with one row, `vmmacc.vv` / `Zvvi32mm` / EFFEW32            | 3-4 days |
| 2   | **Done** except the `ramp` bin (`52218040e`…`089da6013`). The other 12 integer MACC rows and coverpoints | 4-5 days |
| 3   | `Zvvmtls.csv`: `VLT`/`VST` formatters, `cp_ld`, `cp_imm_lambda`, masking                                 | 4-5 days |
| 3a  | `cp_custom_tile_layout` and `cp_custom_tile_roundtrip`: the regression tests for the Sail tile-index bug | 2-3 days |
| 3b  | `cp_custom_tile_macc`: MACC with tile-loaded A/B and tile-stored C                                       | 2 days   |
| 4   | `Zvvfmm.csv` rows that Sail implements, exact-sum FP data, `cp_fp_subdot`                                | 5-7 days |
| 5   | `Zvvmttls.csv` and the cross-mode pairs                                                                  | 2-3 days |
| 6   | Coverage: `disassemble.svh`, vtype fields, all templates; `make coverage EXTENSIONS=Zvvmm32`             | 4-6 days |
| 7   | Privileged suite `ExceptionsZvvm`: illegal cases and vstart                                              | 4-5 days |

Steps 1-7 take about 6-8 engineer-weeks. Steps 8 (FP profile parameters) and 9 (OFP8, OFP4, BF16 output,
microscaling) depend on Sail work outside ACT.

### Slice 1 in detail (done)

Design sections to read: §0, §0.1, §1, §2, §3.1, §3.2, §4.1, §5, §8.1, §8.4, §9.

Changes:

- `testplans/Zvvmm.csv` with the header of §8.1 and one row: `vmmacc.vv,MMACC,x,x,Zvvi32mm,,,x,,x,...` with only
  `cp_asm_count` and `cr_lambda_lmul` enabled.
- testgen and covergroupgen: suite expansion for `Zvvmm` per SEW (as for `Vx`/`Zvbb`).
- covergroupgen: fix the `ExtraExtensions` lookup for per-SEW suites (`generate.py` around lines 343-353 and
  893; about 5 lines). Rows with `ExtraExtensions` are stored under the base suite name and looked up under the
  per-SEW name, so they are dropped.
- `formatters/types/`: an `MMACC` formatter. Setup: two m8 `vle<SEW>.v` loads of C into v16-v31, `vle` loads of A
  and B, vtype with λ set through `LI()` + `vsetvl` (λ is in `vtype` bits 62:60; `vsetvli` cannot set it).
  Test: `vmmacc.vv vd, vs1, vs2` (operand order `vd, vs1, vs2`; `vs1` is A). Check: two m8
  `RVTEST_SIGUPD_V_LEN` on the C window. `vd` must not overlap `vs1` or `vs2` (see open question 1). Do not use
  `vmtl.v`/`vmts.v` here: that keeps the slice clear of the Sail tile-index bug.
- `VectorTypeConfig`: a `fixed_emul` field. `InstructionParams`: IME fields.
- A `cr_lambda_lmul` coverpoint generator. Wrap each testcase in
  `#if defined(UDB_SUPPORTED_LAMBDA_SEW32_<λ>)` ... `#endif`. UDB already emits these macros from the overlay.
- Covergroup templates `sample_MMACC.sv` and `cr_lambda_lmul`.

Acceptance:

```bash
make tests EXTENSIONS=Zvvmm32                    # per-SEW names; EXTENSIONS=Zvvmm selects nothing
EXTENSIONS=Zvvmm32 ENABLE_EXPERIMENTAL_EXTENSIONS=True make qemu-ime-rv64
```

Every testcase passes for λ ∈ {1, 2} on QEMU, and the signature run on Sail succeeds. `mise run prek` passes.
`make tests` produces no change in other suites.

## 7. Known bugs and expected failures

The Sail fork contradicts the specification in these cases. Tests follow the specification, so they fail on a
conforming DUT until Sail is fixed. This is intended. Do not hide these failures.

| Sail bug                                                                                | Affects                                       | Status                      |
| --------------------------------------------------------------------------------------- | --------------------------------------------- | --------------------------- |
| `vmtl.v`/`vmts.v`/`vmttl.v`/`vmtts.v` use the flat index, not `tile_reg_idx`, at LMUL>1 | tile tests at LMUL>1, MACC with tile operands | Patch tested; issue drafted |
| W>1 FP multiply-accumulate adds each product to C; the spec forms S first               | `cp_fp_subdot` bins                           | Issue drafted               |
| `EMUL_C`=16 raises illegal-instruction                                                  | `cr_lambda_lmul` bins with `EMUL_C`=16        | Work item 11                |
| Accepts λ the spec does not permit                                                      | none in ACT (UDB λ lists follow the spec)     | Work item 11                |
| LD = 0 in a register other than `x0` gives stride 0, not the natural stride             | `cp_ld` zero bin                              | Work item 12                |
| No illegal-instruction for VL not a multiple of λ·LMUL, or a masked load into `v0`      | `ExceptionsZvvm`                              | Work item 12                |

Other facts:

- The SDK QEMU does not decode `vmttl.v`/`vmtts.v`. Zvvmttls is not declared in `qemu-ime-rv64`.
- FP rounding: Sail is rnd=frm and QEMU rnd=xct for W=1. Both are legal, so FP test data must keep every product
  and partial sum exact (design §5, §6.1).
- GCC names the W=4 instructions `vqwmmacc.vv`, `vfqwmmacc.vv`, `vfqwimmacc.vv`. The specification names are
  `vqmmacc.vv`, `vfqmmacc.vv`, `vfqimmacc.vv`. Use the specification names; the macros accept both.
- ACT caps VLEN at 1024 (`RVTEST_VLEN_MAX`), so λ ≥ 16 bins stay uncovered.
- `tests/rv64i/Zv*` is in `.gitignore`, so generated IME tests are not checked in.

## 8. Open questions

1. **User decision pending.** May the MACC `vd` group overlap `vs1` or `vs2`? The specification is silent. Sail
   allows it and computes in place. The user said earlier that it may not. Keep the non-overlap constraint until
   the user decides.
2. Which `psm` and `rnd` does the target implementation disclose for each (SEW, W, λ)? G=1 is confirmed.
3. Does the Sail fork support RV32, Int4 and W=1 BF16? Does QEMU support Int4?
