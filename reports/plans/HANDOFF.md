<!-- SPDX-License-Identifier: Apache-2.0 -->

# Handoff: IME tests in ACT4

Read this file first. It is self-contained: what exists, how to run it, the rules, the status and the next steps.

- [udb-0.9.0.md](udb-0.9.0.md): log of the move to riscv-unified-db and spec `58810918`, step by step.
- [ime-act-testplan-design.md](ime-act-testplan-design.md): the testplan design (option C).
- [upstream-ci/](upstream-ci/README.md): work packages for upstream CI.
- [progress-2026-11-21.md](progress-2026-11-21.md): progress summary and what is missing.
- [../issues/INDEX.md](../issues/INDEX.md): bugs and issues found, with drafts to file (none filed).

State as of 2026-11-21.

## 1. Goal

Bring the IME tests into ACT4 (`riscv-arch-test`) in native ACT form: testplan CSVs, instruction formatters,
coverpoint generators and covergroup templates. UDB defines the extensions and parameters. Expected values come from
the IME Sail fork. The tests started as a port of the Rust generator `ime-test-gen` (`riscv-ime-arch-tests`).

## 2. Repositories and pins

All paths are under `/srv/nfs/shared/home/constantino.gomez/` (written `~/`).

| What                    | Where                                                                            | Pin                                                               |
| ----------------------- | -------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| ACT4, code              | `~/repo/ime/riscv-arch-test`, branch `cgomez/ime-udb-0.9.0`                      | 15 commits on `act4` `7569d06d6` (section 5)                      |
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
| `5494a1432` | `Zvvofp8{fp16,bf16,fp32,fp64}mm`: OFP8 inputs, E4M3 and E5M2 through `altfmt_A` and `altfmt_B`     |
| `483225a9a` | `Zvvofp4{fp16,bf16,fp32}mm`: OFP4 (E2M1) inputs, every E2M1 encoding as an edge                    |
| `42f233275` | `Zvvx[n]ofp8*`, `Zvvx[n]ofp4*` (FP16/BF16/FP32 C): microscaled FP MACC (vm=0), `cp_scale`          |
| `89c7fdb33` | `Zvvx[n]i8*`, `Zvvx[n]i4*`: microscaled integer-input MACC (`vfwimmacc.vv` and the W=4, W=8 forms) |
| `588fc52d6` | ExceptionsZvvm: microscaled illegal cases, an operand on v0 and bs=1 with W·LMUL > SEW             |
| `a833181b0` | Fallback disassembler: vm=0 `vmmacc.vv` and `vfmmacc.vv`, so `cp_ime_vm0` is sampled               |
| `87073e242` | IME FP covergroups sample only their own formats (`altfmt`, `altfmt_A`, `altfmt_B`)                |

Suites. Each unprivileged suite expands per SEW (`Zvvmm8` … `Zvvmm64`).

| Suite            | Testplan                            | Content                                                                                                                                                                                        |
| ---------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Zvvmm`          | `testplans/Zvvmm.csv`               | 13 integer MACC rows (W=1, 2, 4, 8; Int4); 4 tile-MACC rows                                                                                                                                    |
| `Zvvfmm`         | `testplans/Zvvfmm.csv`              | 16 FP MACC rows: FP16, BF16, FP32, FP64, FP16/BF16→FP32, FP32→FP64, FP16/BF16→FP64, OFP8→FP16/BF16/FP32/FP64, OFP4→FP16/BF16/FP32; 28 microscaled rows (`FMMACC_MX`), 14 of them integer-input |
| `Zvvmtls`        | `testplans/Zvvmtls.csv`             | `vmtl.v`, `vmts.v`                                                                                                                                                                             |
| `Zvvmttls`       | `testplans/Zvvmttls.csv`            | `vmttl.v`, `vmtts.v`; cross-mode pairs with `vmtl.v` and `vmts.v`                                                                                                                              |
| `ExceptionsZvvm` | `testplans/priv/ExceptionsZvvm.csv` | Illegal-instruction and `vstart` cases for MACC and tile instructions                                                                                                                          |

Code in `generators/testgen/src/testgen/`:

- `asm/vector_helpers.py`: `ime_lambdas`, `ime_lambda_condition`, `ime_vtype_value`, `ime_extend_label`,
  `load_ime_vtype`. Only `vsetvl` sets λ. `lambda_=None` emits an `#if/#elif` chain over
  `UDB_SUPPORTED_LAMBDA_SEW<sew>_<λ>` that picks the smallest supported λ.
- `data/params.py`: `lambda_`, `ime_guard`, `altfmt_a`, `altfmt_b`, `altfmt` (`vtype[8]`, the C format),
  `imm_lambda`, `ld`.
- `formatters/types/mmacc_type.py`: `MMACC` and `FMMACC`. C is a 16-register window at v0 or v16, loaded and checked
  as two m8 groups. FP data is exact in every order (small integers in A and B, half-integers in C), so the result
  does not depend on the FP profile. The input and C formats come from the row's type extension. For OFP8 rows,
  `altfmt_A` and `altfmt_B` from the coverpoint select E4M3 or E5M2 per operand. A widening row with an FP16 or BF16
  C puts at most one nonzero input in each storage element, so a dot product has at most 64 nonzero terms.
  `FMMACC_MX` (vm=0) loads the E8M0 scale pairs into v0 and sets `vtype.bs` for `Zvvxn*` rows. The C window is then
  v16, and A and B share v8 at LMUL=8. Random scales give a combined exponent of −1, 0 or 1. Edge, `cp_fp_subdot`
  and `cp_fp_rnd` data use unit scales. A BF16 C also zeroes the odd A and B storage elements.
- `data/edges.py`: E4M3, E5M2 and E2M1 edge tables. The `f_ofp8` and `f_ofp4` edge variants use them.
- `formatters/types/tile_type.py`: `VLT` and `VST`.
- `coverpoints/vector/`: `cr_lambda_lmul` (variant `_lte4`), `cp_altfmt` (variant `cp_altfmt_ofp8`), `cp_tile_vl`,
  `cp_tile.py`, `cp_custom_tile_macc`, `cp_custom_tile_crossmode`, `cp_fp_subdot`, `cp_fp_rnd`, `cp_scale`,
  `cp_mx_bs`.
- covergroupgen: a row of type T samples through `covergroup_case_sample_<T>.sv` when it exists. `FMMACC` samples
  only vm=1 and `FMMACC_MX` only vm=0.
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

| Config          | Result                                                                                                   |
| --------------- | -------------------------------------------------------------------------------------------------------- |
| `sail-ime-rv64` | 93/93 files pass at `a833181b0`, Zvvmttls and ExceptionsZvvm included                                    |
| `qemu-ime-rv64` | Integer and tile suites pass. Fail: the 12 W>1 Zvvfmm files, ExceptionsZvvm 7/7, and `Zvvbf16mm` (below) |
| UDB C++ ISS     | 9,716 of 9,858 IME results equal Sail; the other 142 have different setup (udb-0.9.0.md, step 5)         |

The 78 files on Sail: the earlier 42 plus 4 OFP8, 3 OFP4 and 28 microscaled files, and an eighth ExceptionsZvvm file.
Only the Zvvfmm suites were re-run (44/44) for these steps, and ExceptionsZvvm (8/8) for its microscaled illegal cases.
For step 5, every IME suite was re-run at `a833181b0`: 93/93 files pass on Sail.
On QEMU, the OFP8 and OFP4 files with an FP16, FP32 or FP64 C fail first at `cp_fp_subdot` (deviation 4).
`Zvvofp8bf16mm` and `Zvvofp4bf16mm` fail at their first testcase (deviation 5). Every OFP edge, `cp_altfmt_ofp8` and
`cr_lambda_lmul` testcase before `cp_fp_subdot` passes on QEMU.

QEMU deviations from the spec. An ELF stops at the first one, so later bins of a failing file are not measured.

1. MACC with `vstart` ≠ 0 or with VL not a multiple of λ·LMUL runs instead of trapping.
2. Tile loads and stores with `vill`, immediate λ L64 (double trap), VL not a multiple, or masked `vd = v0` run
   instead of trapping.
3. [Unverified] `vmttl.v` and `vmtts.v` were reported as not decoded. QEMU `d856b96` decodes both
   (`trans_rvzvmtls.c.inc`, behind `ext_zvvmtls`), and the SDK binary contains their helpers. Run a Zvvmttls file on
   QEMU before reporting anything.
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

- Mixed FP16 and BF16 inputs (`altfmt_A` ≠ `altfmt_B`) need both 16-bit extensions. No covergroup samples them
  until the mixed rows exist.
- ACT caps VLEN at 1024, so bins for λ ≥ 16 stay uncovered.
- The microscaled covergroups sample only vm=0, but they do not check `vtype.bs`. `cp_mx_bs` records it. They have
  no `cp_vs1` or `cp_vs2`: with vm=0 the C window must be v16, so A and B can only be in v1–v15. The unscaled rows
  cover the operand fields, which vm does not change.
- The microscaled QEMU path is not run: QEMU needs `x-zvvfmmmx=true`, and the command line stays as shipped. That
  path also rounds the scale product to FP32 and then to the C format, which the spec forbids.
- No RV32 configuration exists.
- GCC names the W=4 instructions `vqwmmacc.vv`, `vfqwmmacc.vv` and `vfqwimmacc.vv`. The CSVs use the spec names. The
  `.insn` macros accept both.

## 8. Next steps

| Step                                                                                                         | Notes                  |
| ------------------------------------------------------------------------------------------------------------ | ---------------------- |
| Mixed FP16/BF16 rows; `vf8wmmacc.vv` rows; tile layout tests (design §4.4); `ramp` bin; `frm`-sensitive data | design §9              |
| Upstream work packages; pull request to `act4`                                                               | needs approval to push |
| File the issue drafts in `reports/issues/INDEX.md`                                                           | needs approval         |

For each new FP group:

1. Add the extensions to `sail-ime-rv64` (UDB yaml and `sail.json`).
2. Add them to `qemu-ime-rv64` only if QEMU decodes them. See `trans_vfmmacc_vv` and the `ext_zvvfmm*` flags in
   `riscv-ime-qemu` `d856b96`.
3. Extend `Zvvfmm.csv` and add the edge values of the new formats.
4. Check the `.insn` macros and `RISCV_decode_pkg.svh`.

Step 5 tools are in `~/repo/ime/act-udb-work`: `iss-job.sh act-ime-rv64` builds the ISS on a compute node from
`udb-iss` with `udb-iss-act-diagnostic.patch` applied, and `ime-cmp-one.sh <out> <elf>` compares one ELF with Sail.
The patch is diagnostic only. The UDB bugs it works around have issue drafts in `reports/issues/` (`udb-*`).

When `ime/fp-mx` merges into `ime/0.9.0`, move the `udb-act` worktree to `ime/0.9.0`. Nothing else changes.

## 9. Open questions

1. Which FP profile does the target implementation disclose for each (SEW, W, λ)? The configs disclose only the QEMU
   and Sail profiles.
2. Does the Sail fork support RV32?
3. When the spec ARC review draft merges, review the `ExceptionsZvvm` VL bins and the λ/KLEN naming.
4. Can an E5M2 NaN be signaling? The spec defers OFP8 special values to "the rules of the operand formats". Sail
   treats every E5M2 NaN as quiet. The 0x7D edge testcase presets `fflags.NV`, so it passes either way.
