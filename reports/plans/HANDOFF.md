<!-- SPDX-License-Identifier: Apache-2.0 -->

# Handoff: IME tests in ACT4

Read this file first. It is self-contained: what exists, how to run it, the rules, the status and the next steps.

- [udb-0.9.0.md](udb-0.9.0.md): log of the move to riscv-unified-db and spec `58810918`, step by step.
- [ime-act-testplan-design.md](ime-act-testplan-design.md): the testplan design (option C).
- [upstream-ci/](upstream-ci/README.md): work packages for upstream CI.

State as of 2026-11-20.

## 1. Goal

Bring the IME tests into ACT4 (`riscv-arch-test`) in native ACT form: testplan CSVs, instruction formatters,
coverpoint generators and covergroup templates. UDB defines the extensions and parameters. Expected values come from
the IME Sail fork. The tests started as a port of the Rust generator `ime-test-gen` (`riscv-ime-arch-tests`).

## 2. Repositories and pins

All paths are under `/srv/nfs/shared/home/constantino.gomez/` (written `~/`).

| What                    | Where                                                                            | Pin                                                               |
| ----------------------- | -------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| ACT4, code              | `~/repo/ime/riscv-arch-test`, branch `cgomez/ime-udb-0.9.0`                      | 8 commits on `act4` `7569d06d6` (section 5)                       |
| ACT4, reports           | `~/repo/ime/riscv-arch-test-docs` (worktree), branch `docs/act-ime-reports`      |                                                                   |
| UDB                     | Openchip-Software/riscv-unified-db `ime/fp-mx`, worktree `~/repo/ime/udb-act`    | `f0045fec`; will merge into `ime/0.9.0`                           |
| Sail (reference)        | Openchip-Software/sail-riscv `cleanup/ime-0.9.0`, worktree `~/repo/ime/sail-act` | `0ebfc810`; binary in `~/repo/ime/sail-act/build-act/c_emulator/` |
| Sail, OFP8 accumulators | Openchip-Software/sail-riscv `cgomez/ime-ofp8-acc`                               | `2cb7eefb`; pending PR, not used yet                              |
| IME specification       | riscv/integrated-matrix-extension, local clone `~/repo/ime/ime-spec`             | `58810918` = v0.9.0-on-main + `324c62b7` (exact E8M0 scales)      |
| SDK image (GCC, QEMU)   | `~/repo/ime/sdk-2026.10.14.sif`                                                  | QEMU = Openchip-Software/riscv-ime-qemu `vrull/ime-wip` `d856b96` |

UDB, Sail and the tests follow the same spec commit. The local `ime-spec` clone is checked out at a later commit
(`e99d9065`). Read the pinned text with `git -C ~/repo/ime/ime-spec show 58810918:src/unpriv/integrated-matrix.adoc`.

## 3. Environment

```bash
cd ~/repo/ime/riscv-arch-test
source ~/tools/act4/env.sh
export PATH=$PWD/config/ime/bin:$PATH SDK_SIF=~/repo/ime/sdk-2026.10.14.sif
export SAIL_IME_SIM=~/repo/ime/sail-act/build-act/c_emulator/sail_riscv_sim
```

`env.sh` activates mise (Ruby, uv, bundler) and sets `UDB_LOCAL_PATH=~/repo/ime/udb-act`. It also moves every cache
that NFS breaks to `/tmp/$USER-*`:

- `XDG_DATA_HOME`: UDB uses `flock`, which fails on NFS.
- `BUNDLE_PATH`, `PREK_HOME`, `UV_CACHE_DIR`: installs onto NFS hang in the NFS server-side copy (`handle_async_copy`).
  A hung process survives `pkill`; use `kill -9`.
- `/tmp` is lost on reboot. The next ACT or prek run reinstalls.

Other facts:

- `UDB_LOCAL_PATH` makes bundler rewrite `framework/src/act/data/Gemfile.lock`. Restore it before each commit:
  `git checkout -- framework/src/act/data/Gemfile.lock`.
- `~/repo/ime/udb-act/gen` points to `/tmp/$USER-udb-act-gen`.
- `config/ime/bin` wraps the SDK GCC, binutils and QEMU (`apptainer exec $SDK_SIF`) and Sail (always with
  `--enable-experimental-extensions`). See `config/ime/README.md`.
- Simulator runs take seconds and run on the login host. Sail builds and long sweeps go to a compute node with the
  `moon-job` skill. Sail builds with `~/repo/ime/sail-riscv-work/build.sh <src> <build>` (about 30 minutes).
- `mise run prek` takes several minutes on the first run after a reboot, while it builds the hook environments.

## 4. Rules

1. `AGENTS.md` in `riscv-arch-test` applies.
2. **Source of truth.** The spec at `58810918` decides. Where it is silent, the Sail fork decides. QEMU, GCC and the
   Rust golden model never decide.
   - Sail contradicts the spec: the bins follow the spec and stay in place, with no `ignore_bins` and no exclusion.
   - The spec permits several behaviours: use data whose result does not depend on the choice, or gate the testcase
     on the UDB disclosure parameters (section 5).
3. **Where work goes.** Code on `cgomez/ime-udb-0.9.0`. Reports in the docs worktree. After each code step, update
   `udb-0.9.0.md` and this file, and commit there. Rebase both branches when `act4` moves.
4. **Commits.** `mise run prek` passes first. `git commit -s`, no AI trailers. Subject imperative, at most 72
   characters. Body: what was wrong and what it is now. Do not push without approval.
5. **OFP8 tests that Sail cannot run** go on the set-aside list in `udb-0.9.0.md`, with the test name, the extension
   and the Sail error. Do not work around them on this branch.

## 5. Current implementation

Commits on `cgomez/ime-udb-0.9.0`, oldest first. The first three are `port-ime-tests-to-act4`.

| Commit      | What                                                                                               |
| ----------- | -------------------------------------------------------------------------------------------------- |
| `0bb9717a4` | covergroupgen: `ExtraExtensions` rows in per-SEW testplans get covergroups (generic fix)           |
| `98595c2a5` | All IME suites, `.insn` macros, IME decode in coverage, and a UDB overlay (removed by `49b999ce9`) |
| `8ada25d12` | `config/ime/qemu-ime-rv64`: SDK QEMU as DUT                                                        |
| `49b999ce9` | IME definitions from UDB `ime/fp-mx` instead of the overlay; Zvvm versions 0.9.0                   |
| `b186cce44` | Sail `cleanup/ime-0.9.0` as reference; `config/ime/sail-ime-rv64` (Sail as DUT, VLEN 1024)         |
| `413966b5a` | `cp_ime_vd_overlap` in ExceptionsZvvm (spec `5bcd3946`)                                            |
| `aaa0c329c` | `cp_fp_rnd`: rnd-dependent data, gated on the UDB FP disclosure                                    |
| `59666b161` | `Zvvbf16mm`: BF16 accumulator through `vtype.altfmt`                                               |

Suites. Each unprivileged suite expands per SEW (`Zvvmm8` … `Zvvmm64`).

| Suite            | Testplan                            | Content                                                                           |
| ---------------- | ----------------------------------- | --------------------------------------------------------------------------------- |
| `Zvvmm`          | `testplans/Zvvmm.csv`               | 13 integer MACC rows (W=1, 2, 4, 8; Int4); 4 tile-MACC rows                       |
| `Zvvfmm`         | `testplans/Zvvfmm.csv`              | 9 FP MACC rows: FP16, BF16, FP32, FP64, FP16/BF16→FP32, FP32→FP64, FP16/BF16→FP64 |
| `Zvvmtls`        | `testplans/Zvvmtls.csv`             | `vmtl.v`, `vmts.v`                                                                |
| `Zvvmttls`       | `testplans/Zvvmttls.csv`            | `vmttl.v`, `vmtts.v`; cross-mode pairs with `vmtl.v` and `vmts.v`                 |
| `ExceptionsZvvm` | `testplans/priv/ExceptionsZvvm.csv` | Illegal-instruction and `vstart` cases for MACC and tile instructions             |

Code in `generators/testgen/src/testgen/`:

- `asm/vector_helpers.py`: `ime_lambdas`, `ime_lambda_condition`, `ime_vtype_value`, `ime_extend_label`,
  `load_ime_vtype`. Only `vsetvl` sets λ. `lambda_=None` emits an `#if/#elif` chain over
  `UDB_SUPPORTED_LAMBDA_SEW<sew>_<λ>` that picks the smallest supported λ.
- `data/params.py`: `lambda_`, `ime_guard`, `altfmt_a`, `altfmt_b`, `altfmt` (`vtype[8]`, the C format),
  `imm_lambda`, `ld`.
- `formatters/types/mmacc_type.py`: `MMACC` and `FMMACC`. C is a 16-register window at v0 or v16, loaded and checked
  as two m8 groups. FP data is exact in every order (small integers in A and B, half-integers in C), so the result
  does not depend on the FP profile. The input and C formats come from the row's type extension.
- `formatters/types/tile_type.py`: `VLT` and `VST`.
- `coverpoints/vector/`: `cr_lambda_lmul`, `cp_altfmt`, `cp_tile_vl`, `cp_tile.py`, `cp_custom_tile_macc`,
  `cp_custom_tile_crossmode`, `cp_fp_subdot`, `cp_fp_rnd`.
- `priv/extensions/ExceptionsZvvm.py`: four generators. `vtype` is an assembler expression over `UDB_MXLEN`.

FP disclosure. UDB has the parameters `ZVVM_FP_{GROUPING,PSM,RND}_SEW<s>_W<w>`, with one entry per λ. It emits macros
such as `UDB_ZVVM_FP_RND_SEW32_W2_IDX0_FRM` (string values in uppercase) and `UDB_ZVVM_FP_PSM_SEW32_W2_MASK`. Sail
computes G=1, psm=0, rnd=frm, so a profile-dependent testcase is generated for that profile and gated on it.

| Config          | DUT         | VLEN | FP profile          | IME extensions                     |
| --------------- | ----------- | ---- | ------------------- | ---------------------------------- |
| `qemu-ime-rv64` | SDK QEMU    | 256  | G=1, psm=0, rnd=xct | all tested types, without Zvvmttls |
| `sail-ime-rv64` | Sail (fork) | 1024 | G=1, psm=0, rnd=frm | all tested types and Zvvmttls      |

`sail.json` sets the family flags `Zvvmm` and `Zvvfmm` to false and each declared type to true, because a Sail family
flag enables every type of the family.

Generated tests are not checked in (`.gitignore`: `tests/rv64i/Zv*`, `tests/priv/**/*.S`). Covergroups under
`coverpoints/` are checked in.

## 6. How to build and run

```bash
E=Zvvfmm8,Zvvfmm16,Zvvfmm32,Zvvfmm64          # per-SEW names; EXTENSIONS=Zvvfmm selects nothing
uv run covergroupgen testplans --extensions $E
uv run testgen testplans -o tests --extensions $E
~/repo/ime/act-udb-work/run-suites.sh sail-ime-rv64 <workdir> "$SAIL_IME_SIM" $E
```

- `run-suites.sh <config> <workdir> <sail> <suites>` sources `env.sh`, builds with `act -k`, runs every ELF directory
  with `run_tests.py`, and restores `Gemfile.lock`. Logs are in `<workdir>/<config>/elfs/rv64i/logs/`.
- `make tests` uses stamps that ignore `EXTENSIONS`, so call `testgen` and `covergroupgen` directly.
- To check that existing tests do not change, generate from `HEAD` in a scratch worktree into another directory and
  compare with `diff -r`.
- An ELF stops at its first failing testcase. To find it, build with `act ... --debug`, run QEMU with
  `-d int -D <log>`, and look up the trap `epc` in the `.elf.objdump`.
- Coverage: no Questa or VCS here. `reports/ime-poc/slang_check.py` in the docs worktree compiles the testbench with
  pyslang:
  `uv run --no-project --with pyslang python <docs>/reports/ime-poc/slang_check.py "$PWD" work/<config>/env ZVVMM32_COVERAGE,...`.

## 7. Status

Results with Sail `0ebfc810`, all suites at all SEWs:

| Config          | Result                                                                                                  |
| --------------- | ------------------------------------------------------------------------------------------------------- |
| `sail-ime-rv64` | 42/42 files pass, Zvvmttls and ExceptionsZvvm included                                                  |
| `qemu-ime-rv64` | Integer and tile suites pass. Fail: the 5 W>1 Zvvfmm files, ExceptionsZvvm 7/7, and `Zvvbf16mm` (below) |

QEMU deviations from the spec. An ELF stops at the first one, so later bins of a failing file are not measured.

1. MACC with `vstart` ≠ 0 or with VL not a multiple of λ·LMUL runs instead of trapping.
2. Tile loads and stores with `vill`, immediate λ L64 (double trap), VL not a multiple, or masked `vd = v0` run
   instead of trapping.
3. `vmttl.v` and `vmtts.v` are not decoded.
4. W>1 FP MACC adds each product into C with its own rounding. The spec forms the group sum S first, so
   `cp_fp_subdot` fails.
5. `vtype[8]` (`altfmt`) is reserved unless `x-zvfbfa=true`. `vsetvl` then sets `vill`, and a BF16-accumulator MACC
   traps. The spec lists Zve32f as the only dependency of `Zvvbf16mm`, and Sail writes the bit when IME is enabled.
   With `x-zvfbfa=true` the `Zvvbf16mm` file passes. The QEMU command line is not changed.
6. [Inferred] QEMU uses the A/B register layout of spec `6effbcae`: λ K elements per register instead of λ·W
   (spec `3c1b4457`). It should fail W>1 at LMUL>1. Item 4 hides this today.

Spec gap, not a deviation: the spec does not define the sign of `fp_internal_zero()` or of an exact zero group sum.
Tests must not depend on it. See `reports/issues/ime-fp-internal-zero-sign/ISSUE.md`.

Known limits:

- Covergroups do not check `altfmt`, `altfmt_A` or `altfmt_B`. The `Zvvfp16mm` and `Zvvbf16mm` covergroups both
  sample every `vfmmacc.vv` at SEW=16. The FP16 and BF16 input rows at SEW=32 and 64 have the same problem.
- ACT caps VLEN at 1024, so bins for λ ≥ 16 stay uncovered.
- No RV32 configuration exists.
- GCC names the W=4 instructions `vqwmmacc.vv`, `vfqwmmacc.vv` and `vfqwimmacc.vv`. The CSVs use the spec names. The
  `.insn` macros accept both.

## 8. Next steps

| Step                                                                                                         | Notes                                          |
| ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------- |
| 4.2 OFP8: `Zvvofp8mm`, `Zvvofp8{bf16,fp16,fp32,fp64}mm`. Then OFP4: `Zvvofp4{bf16,fp16,fp32,ofp8}mm`         | OFP8-accumulator rows go on the set-aside list |
| 4.3 Microscaling `Zvvx*` (vm=0): `FMMACC_MX`, `MMACC_MX`, `cp_scale`, E8M0 edges, block-scale LMUL limits    | spec `0a13020a`, `324c62b7`                    |
| 5 UDB ISS cross-check: run every IME ELF through the UDB C++ ISS and triage each mismatch                    | diagnostic only, not committed to ACT          |
| Coverage: filter the IME FP covergroups on `altfmt`, `altfmt_A` and `altfmt_B`                               | section 7                                      |
| Mixed FP16/BF16 rows; `vf8wmmacc.vv` rows; tile layout tests (design §4.4); `ramp` bin; `frm`-sensitive data | design §9                                      |
| Upstream work packages; pull request to `act4`                                                               | needs approval to push                         |

For each new FP group:

1. Add the extensions to `sail-ime-rv64` (UDB yaml and `sail.json`).
2. Add them to `qemu-ime-rv64` only if QEMU decodes them. See `trans_vfmmacc_vv` and the `ext_zvvfmm*` flags in
   `riscv-ime-qemu` `d856b96`.
3. Extend `Zvvfmm.csv` and add the edge values of the new formats.
4. Check the `.insn` macros and `RISCV_decode_pkg.svh`.

Phase 5 tools: `~/.cache/ime-cleanup/zt/iss-build.sh ~/repo/ime/udb-act rv64-ime-v256-grp iss` builds the ISS on a
compute node (needs `gcc14.sif`). Run an ELF with `iss -m rv64-ime-v256-grp -c cfgs/rv64-ime-v256-grp.yaml <elf>`.
First check that the ISS config matches the ACT config (VLEN, λ lists, FP profile) and that the ISS runs the ACT boot
code. If the boot code needs features the ISS lacks, limit the run to Zvvmm and Zvvfmm.

When `ime/fp-mx` merges into `ime/0.9.0`, move the `udb-act` worktree to `ime/0.9.0`. Nothing else changes.

## 9. Open questions

1. Which FP profile does the target implementation disclose for each (SEW, W, λ)? The configs disclose only the QEMU
   and Sail profiles.
2. Does the Sail fork support RV32?
3. When the spec ARC review draft merges, review the `ExceptionsZvvm` VL bins and the λ/KLEN naming.
