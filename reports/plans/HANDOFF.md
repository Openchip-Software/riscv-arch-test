<!-- SPDX-License-Identifier: Apache-2.0 -->

# Handoff: IME tests in ACT4

This file is self-contained. It describes what exists, how to run it, the rules, the open problems and the next
steps. The testplan design is in [ime-act-testplan-design.md](ime-act-testplan-design.md). Read this file first.

State as of 2026-11-07.

## 1. Goal

Bring the tests of the Rust generator `ime-test-gen` (repository `riscv-ime-arch-tests`) into ACT4
(`riscv-arch-test`). The tests use the native ACT form, "option C": testplan CSVs, instruction formatters,
coverpoint generators and covergroup templates in `testgen` and `covergroupgen`. Expected values come from the Sail
reference model, not from the Rust golden model.

## 2. Repositories and tools

All paths are under `/srv/nfs/shared/home/constantino.gomez/` (written `~/` below).

| What                       | Where                                                           | Version                                                                         |
| -------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| ACT4, code                 | `~/repo/ime/riscv-arch-test`                                    | branch `cgomez/import-ime-tests-to-act4`, 19 commits on `act4` `8b9ddedcd`      |
| ACT4, reports              | `~/repo/ime/riscv-arch-test-docs` (worktree)                    | branch `docs/act-ime-reports`                                                   |
| Rust generator             | `~/repo/ime/riscv-ime-arch-tests`                               | `46f3781`; generator in `ime-test-gen/`, plans in `src/dsl_plans.rs`            |
| Sail fork (reference)      | `~/repo/ime/sail-riscv`, Openchip-Software/sail-riscv           | branch `cgomez/0.16-plus-ime` @ `a545cc41` (Sail 0.16 + IME)                    |
| Sail binary                | `~/repo/ime/sail-riscv/build-016/c_emulator/sail_riscv_sim`     | built from `a545cc41` plus test-only commits; `--build-info` shows a stale hash |
| SDK image (GCC 16.1, QEMU) | `~/repo/ime/sdk-2026.10.14.sif`                                 | QEMU = Openchip-Software/riscv-ime-qemu `vrull/ime-wip` @ `d856b96`             |
| IME specification          | riscv/integrated-matrix-extension, `src/integrated-matrix.adoc` | `main` @ `6effbcae`                                                             |

The ARC review draft of the specification (branch `jmoreira/arc-review-updates-01` @ `d051f35b`,
`src/unpriv/integrated-matrix.adoc`) is not merged. It renames λ to `KLEN` and M to `MLEN`. It makes every VL legal
for tile loads and stores, and makes a multiply-accumulate VL that is not a multiple of λ·LMUL reserved. The tests
follow `main` until the draft is merged (section 8).

Reports in `~/repo/ime/riscv-arch-test-docs/reports/` (rebuild instructions in `README.md` there):

- `act-architecture.html`: Report 1, how ACT4 works. Useful: §7 Generate, §10 Check, Example C, §16 Extension
  points.
- `ime-testgen-to-act.html`: Report 2, analysis of `ime-test-gen` and the integration. §16a describes the
  implementation, §18 lists the findings.

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
- IME tests need `ENABLE_EXPERIMENTAL_EXTENSIONS=True` (Make) or `--enable-experimental-extensions` (`act`).
  Without it ACT skips them.
- Simulator runs are fast and run on the login host. For Sail rebuilds and long sweeps use the `moon-job` skill
  (compute node, SDK image). A Sail build needs `--no-container`, because the SDK image has no cmake.

## 4. Rules

1. **AGENTS.md** in `riscv-arch-test` applies: `uv run` or Make, never bare `python`/`pip`; Python 3.10; Ruff and
   Pyright pass; SPDX header on new files; `LI()`/`LA()`, never `li`/`la`; `.p2align`/`.balign`, never `.align`;
   do not hand-edit generated files; `ignore_bins` only for architecturally unreachable bins.
2. **Source of truth** (project decision, 2026-10-27). The IME specification decides every conflict. Where it is
   silent or ambiguous, the Sail fork decides. QEMU, the SDK GCC and the Rust golden model never decide.
   - Sail contradicts the specification: the bins follow the specification, stay in place, and fail until Sail is
     fixed. No `ignore_bins` or CI exclusions for them.
   - The specification permits several behaviours: tests must not depend on the choice.
   - The specification is silent: follow the Sail code and record "spec silent; Sail behaviour" with a citation.
3. **Where work goes.** Code on `cgomez/import-ime-tests-to-act4`. Reports on `docs/act-ime-reports` in the docs
   worktree. After each meaningful code step, update the reports, rebuild them and commit there. Keep both
   branches rebased on `origin/act4`.
4. **Commits.** Run `mise run prek` (or `prek run --files <files>`) first. Sign off with `git commit -s`. No AI or
   agent authorship trailers. Subject imperative, at most 72 characters, no period. Body: what was wrong and what
   it is now. Do not push without approval.

## 5. Current implementation

Commits on `cgomez/import-ime-tests-to-act4`:

| Commit      | What                                                                                                           |
| ----------- | -------------------------------------------------------------------------------------------------------------- |
| `fa3641965` | UDB overlay `framework/src/act/data/udb_overlays/ime`: 65 Zvv\* extensions, `SUPPORTED_LAMBDA_SEW{8,16,32,64}` |
| `85586531e` | Zvv\* experimental; `.insn` macros for every IME instruction in `tests/env/rvtest_experimental.h`              |
| `394462f26` | DUT configuration `config/ime/qemu-ime-rv64`: SDK QEMU as DUT, Sail IME as reference; CI disabled              |
| `34afab1e9` | covergroupgen: `ExtraExtensions` rows in per-SEW testplans get covergroups, filtered by `EFFEW`                |
| `9ef93d17a` | `Zvvmm.csv` first row, `MMACC` formatter, `cr_lambda_lmul`, `fixed_emul`, `load_ime_vtype`, λ gate             |
| `978527c1e` | The 13 integer rows of `Zvvmm.csv`                                                                             |
| `ea4f9edd7` | `cp_vd_emul16`, `cp_vs1`, `cp_vs2`, `cp_altfmt`; λ chain for coverpoints that do not choose λ                  |
| `38c196f92` | `cp_vd_edges`, `cp_vs1_edges`, `cp_vs2_edges` (`emulf2/4/8` for W>1, 4-bit edges for Int4)                     |
| `6e9f5b04b` | `cp_tile_vl`                                                                                                   |
| `feb5d61a4` | `Zvvmtls.csv`, `VLT`/`VST` formatters, `cp_ld`, `cp_imm_lambda`, `cr_tile_vtype_agnostic`                      |
| `797fc5784` | `cp_custom_tile_macc` on four `vmmacc.vv` rows with `ExtraExtensions=Zvvi<n>mm:Zvvmtls`                        |
| `52a08ff97` | IME suites keep their base extension: no Zve64\* for `vw*`/`vfw*` at SEW=32                                    |
| `a25873963` | `Zvvfmm.csv` (8 rows), `FMMACC` formatter, exact FP data                                                       |
| `e052081f7` | FP edges (`f`, `f_emulf2`, `f_emulf4`, `f_bf16`), `cp_csr_frm_v`, `cp_csr_fflags_voun`                         |
| `dd060485c` | `cp_fp_subdot` on the W>1 rows                                                                                 |
| `4fd96e97a` | `Zvvmttls.csv`, run-time natural LD for transposing tiles, `cp_custom_tile_crossmode`                          |
| `0c44e37ae` | IME encodings in `RISCV_decode_pkg.svh` and `disassemble()`                                                    |
| `07a604f4d` | Regenerated IME covergroups after a rebase                                                                     |
| `a4e9bc82b` | Privileged suite `ExceptionsZvvm` (`testplans/priv/ExceptionsZvvm.csv`, `priv/extensions/ExceptionsZvvm.py`)   |

Suites. Each unprivileged suite expands per SEW (`Zvvmm8` … `Zvvmm64`), like `Vx`:

| Suite            | Testplan                            | Content                                                               |
| ---------------- | ----------------------------------- | --------------------------------------------------------------------- |
| `Zvvmm`          | `testplans/Zvvmm.csv`               | 13 integer MACC rows (W=1, 2, 4, 8; Int4); 4 tile-MACC rows           |
| `Zvvfmm`         | `testplans/Zvvfmm.csv`              | 8 FP MACC rows: FP16/32/64, FP16/BF16→FP32, FP32→FP64, FP16/BF16→FP64 |
| `Zvvmtls`        | `testplans/Zvvmtls.csv`             | `vmtl.v`, `vmts.v`                                                    |
| `Zvvmttls`       | `testplans/Zvvmttls.csv`            | `vmttl.v`, `vmtts.v`; cross-mode pairs with `vmtl.v`/`vmts.v`         |
| `ExceptionsZvvm` | `testplans/priv/ExceptionsZvvm.csv` | Illegal-instruction cases and `vstart` for MACC and tile instructions |

Code in `generators/testgen/src/testgen/`:

- `asm/vector_helpers.py`: `ime_lambdas`, `ime_lambda_condition`, `ime_vtype_value`, `ime_extend_label`,
  `load_ime_vtype`. λ lives in `vtype` bits XLEN-2:XLEN-4 and only `vsetvl` can set it. `lambda_=None` emits an
  `#if/#elif` chain over `UDB_SUPPORTED_LAMBDA_SEW<sew>_<λ>` that picks the smallest supported λ. `load_ime_vtype`
  supports VL = n columns, `"half"`, `"vlmax"`, `"random"`, per-λ register values and `keep_vl`.
- `data/params.py`: `lambda_`, `altfmt_a`, `altfmt_b`, `imm_lambda`, `ld`. `formatters/registry.py`: `fixed_emul`.
- `formatters/types/mmacc_type.py`: `MMACC` and `FMMACC`. C is a 16-register window at v0 or v16
  (`fixed_emul={"vd": 16}`), loaded and checked as two m8 groups. `vd` does not overlap `vs1`/`vs2`. For FP, `vs1`
  does not overlap `vs2`. Base-suite coverpoint generators run at VL=VLMAX with extended data labels. FP data is
  exact (sparse small integers, half-integer C), so results do not depend on psm, rnd or `frm`.
- `formatters/types/tile_type.py`: `VLT` and `VST`. One data label per SEW serves every tile test. The natural LD of
  `vmttl.v`/`vmtts.v` (M = VLEN/(SEW·λ)) is computed at run time from `vlenb`.
- Coverpoints in `coverpoints/vector/`: `cr_lambda_lmul`, `cp_altfmt`, `cp_tile_vl`, `cp_tile.py` (`cp_ld`,
  `cp_imm_lambda`, `cr_tile_vtype_agnostic`), `cp_custom_tile_macc`, `cp_custom_tile_crossmode`, `cp_fp_subdot`.
- `priv/extensions/ExceptionsZvvm.py`: four generators (Zvvmm, Zvvfmm, Zvvmtls, Zvvmttls). The tests serve both
  XLENs, so `vtype` is an assembler expression over `UDB_MXLEN`.
- `io/templates.py`: `IME_SUITE_PREFIXES`. `io/testplans.py`: suite expansion.

Coverage (`generators/coverage/`, `framework/src/act/fcov/coverage/`): `sample_MMACC/FMMACC/VLT/VST` templates and
one template per IME coverpoint; `vtype` decode of λ, `altfmt_a` and `altfmt_b`; `ime_column_vl`, `ime_ld_check`;
IME encodings in `RISCV_decode_pkg.svh` and `disassemble.svh`.

Generated IME tests are not checked in: `.gitignore` covers `tests/rv64i/Zv*` and `tests/priv/**/*.S`. The
covergroups under `coverpoints/` are checked in.

## 6. How to build and run

```bash
uv run covergroupgen testplans --extensions Zvvmm8,Zvvmm16,Zvvmm32,Zvvmm64
uv run testgen testplans -o tests --extensions Zvvmm8,Zvvmm16,Zvvmm32,Zvvmm64
uv run act config/ime/qemu-ime-rv64/test_config.yaml --workdir work --test-dir tests \
  --extensions Zvvmm8,Zvvmm16,Zvvmm32,Zvvmm64 --enable-experimental-extensions -k
for d in work/qemu-ime-rv64/elfs/rv64i/Zvvmm*; do ./run_tests.py "$(cat config/ime/qemu-ime-rv64/run_cmd.txt)" $d; done
```

- Use the per-SEW suite names. `EXTENSIONS=Zvvmm` selects nothing.
- `make tests` stamps ignore `EXTENSIONS`, Make run targets have no keep-going option, and `run_tests.py` also runs
  stale ELFs in `work/<config>/elfs`. Call `uv run` directly as above, and remove stale ELFs before a run.
- `ExceptionsZvvm` ELFs are under `work/<config>/elfs/priv/ExceptionsZvvm`.
- QEMU does not decode `vmttl.v`/`vmtts.v`, so `Zvvmttls` runs only with Sail as DUT. Make a scratch copy of
  `config/ime/qemu-ime-rv64` with `rvmodel_macros.h` and `link.ld` from `config/sail/sail-rv64-max`, enable
  `Zvvmttls` in the UDB yaml and `sail.json`, and set `run_cmd.txt` to `sail_riscv_sim_ime --config <abs sail.json>`.
  This only shows that the tests build and run, because Sail is both DUT and reference.
- Coverage: there is no Questa or VCS here, so `make coverage` has never run. `reports/ime-poc/slang_check.py` in the
  docs worktree compiles the coverage testbench with pyslang:
  `uv run --no-project --with pyslang python <docs>/reports/ime-poc/slang_check.py "$PWD" work/<config>/env ZVVMM32_COVERAGE,...`.

## 7. Verification status and known failures

On 2026-11-06, with Sail `a545cc41` as reference:

| Suite                     | DUT  | Result                                                                   |
| ------------------------- | ---- | ------------------------------------------------------------------------ |
| `I`                       | QEMU | 51/51                                                                    |
| `Zvvmm` SEW 8, 32, 64     | QEMU | 13/13 files pass                                                         |
| `Zvvfmm` SEW 32, 64       | QEMU | 7/7 files pass                                                           |
| `Zvvmtls`                 | QEMU | 8/8 files pass                                                           |
| `Zvvmm` + `Zvvfmm` SEW 16 | QEMU | 5 files fail at the Sail signature build: `EMUL_C`=16 (Sail deviation 1) |
| `Zvvmttls`                | Sail | 16/16 files pass                                                         |
| `ExceptionsZvvm`          | Sail | 5/5 files pass                                                           |
| `ExceptionsZvvm`          | QEMU | fails at the first QEMU deviation (below)                                |

Open Sail deviations from the specification. The tests follow the specification and keep these bins:

1. **`EMUL_C`=16 raises illegal-instruction** in every MACC instruction. Filed as
   [Openchip-Software/sail-riscv#10](https://github.com/Openchip-Software/sail-riscv/issues/10), with a reproducer and
   a fix sketch. It blocks all SEW=16 MACC files at VLEN 256 (λ=1).
2. **W>1 FP MACC adds each product into C** instead of forming the sub-dot-product sum S first. Draft issue with
   reproducer: `reports/issues/sail-ime-wmmacc-partial-sum/ISSUE.md`, not filed. The `cp_fp_subdot` bins pass on QEMU
   only because QEMU has the same deviation. The `vf8wmmacc.vv` rows that Sail added in `128a5b74` have it too.

Fixed in Sail: the tile register index at LMUL>1 (`a545cc41`), the natural LD for a zero value in `rs2` (`c1d96b3e`),
and the trap for a masked tile load into `v0` (`fd88fd86`).

QEMU deviations (Report 2, findings 31 and 32). QEMU does not trap on MACC with `vstart` != 0 or VL not a multiple of
λ·LMUL. It does not trap on tile loads and stores with `vill`, immediate λ L64 (it double-traps instead), VL not a
multiple, or a masked load into `v0`. To see one case, run one coverpoint at a time from a scratch copy of the CSV.
QEMU `-d int` shows the traps.

Other facts:

- FP rounding: for W=1, Sail rounds the product (rnd=frm) and QEMU fuses it (rnd=xct). Both are legal, so FP data
  keeps every product and partial sum exact.
- GCC names the W=4 instructions `vqwmmacc.vv`, `vfqwmmacc.vv`, `vfqwimmacc.vv`. Use the specification names
  `vqmmacc.vv`, `vfqmmacc.vv`, `vfqimmacc.vv`. The `.insn` macros accept both.
- ACT caps VLEN at 1024 (`RVTEST_VLEN_MAX`), so λ ≥ 16 bins stay uncovered.

## 8. Next steps

| Step                                                                                                 | Depends on            |
| ---------------------------------------------------------------------------------------------------- | --------------------- |
| Rebase both branches onto `act4` (now at `7569d06d6`, 14 commits ahead)                              | —                     |
| File the W>1 partial-sum Sail issue (draft ready)                                                    | —                     |
| Step 3a: `cp_custom_tile_layout` and `cp_custom_tile_roundtrip` (tile layout at LMUL>1, design §4.4) | —                     |
| `ramp` bin of the integer MACC rows                                                                  | —                     |
| Rounding-sensitive data for `cp_csr_frm_v`                                                           | psm/rnd disclosure    |
| `vf8wmmacc.vv` rows in `Zvvfmm.csv`                                                                  | Sail deviation 2      |
| Mixed FP16/BF16 rows, OFP8, OFP4, BF16 output, microscaling (design steps 8 and 9)                   | Sail support          |
| Review the `cp_ime_vl_not_multiple` bins of `ExceptionsZvvm`                                         | ARC draft merged      |
| Coverage simulation run                                                                              | Questa, VCS or RTL    |
| Pull request to `act4`                                                                               | user approval to push |

## 9. Open questions

1. **User decision pending.** May the MACC `vd` group overlap `vs1` or `vs2`? The specification is silent. Sail
   allows it and computes in place. The tests keep the non-overlap constraint until the user decides.
2. Which `psm` and `rnd` does the target implementation disclose for each (SEW, W, λ)? G=1 is confirmed.
3. Does the Sail fork support RV32? Only RV64 has been run.
