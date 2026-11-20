<!-- SPDX-License-Identifier: Apache-2.0 -->

# 06: ACT: the IME tests and a Sail CI job

Repository: `riscv/riscv-arch-test`, target branch `act4`. Source: the IME commits on
`Openchip-Software/riscv-arch-test`, branch `cgomez/ime-udb-0.9.0` (local clone `~/repo/ime/riscv-arch-test`).
Reports and the handoff are in the docs worktree `~/repo/ime/riscv-arch-test-docs`, `reports/plans/HANDOFF.md`.

State as of 2026-11-20. Blocked on a Sail fork release (package 01) and a UDB release with IME (package 03).

## Why

This is the IME pull request itself. It must run in upstream CI, and every expected result in it must follow the IME
specification.

## Contents of the pull request

- The IME commits, squashed: the experimental-extension handling and `.insn` macros, the IME decode in the coverage
  disassembler, and the suites `Zvvmm`, `Zvvfmm`, `Zvvmtls`, `Zvvmttls` and `ExceptionsZvvm`. The UDB overlay of
  `98595c2a5` is already removed (`49b999ce9`).
- A `udb` gem bump to the release of package 03.
- Not `config/ime`. Its wrappers run the OpenChip SDK through apptainer, which upstream cannot use.
- Not the covergroupgen fix. It goes upstream separately (package 05).

## Tasks

### A. Update the tests for the new Sail release

1. Done on the branch: the `sail.json` files use the schema of `cleanup/ime-0.9.0`, and every IME suite passes with
   Sail `0ebfc810` as DUT (`config/ime/sail-ime-rv64`). If the release differs from `0ebfc810`, rerun and explain
   every signature difference.
2. In `sail.json`, keep the family flags `Zvvmm` and `Zvvfmm` false and enable each declared type. A Sail family flag
   enables every type of the family.
3. If the ARC review draft has merged by then, review the `cp_ime_vl_not_multiple` bins for tile loads and stores in
   `ExceptionsZvvm`. The draft makes every 0 ≤ VL ≤ VLMAX legal for them (Sail issue #8). Spec `58810918` still
   requires a multiple of λ·LMUL, so the bins expect a trap today.
4. AGENTS.md rule: if Sail still deviates from the specification in some case, do not generate that testcase. Keep
   its coverage bins, so coverage reports them as missing. Do not exclude a whole suite such as `Zvvmm16`.

### B. Configuration

1. Add `config/sail/sail-rv64-experimental/`, modelled on `config/spike/spike-rv64-experimental/`:
   - `test_config.yaml` with `compiler_exe: riscv64-unknown-elf-gcc`, `objdump_exe: riscv64-unknown-elf-objdump` and
     `ref_model_exe: sail_riscv_sim`. ACT already passes `--enable-experimental-extensions` to Sail, so no wrapper is
     needed.
   - The UDB config with the IME extensions, VLEN 256, the λ lists and Sail's FP profile (G=1, psm=0, rnd=frm).
     `config/ime/sail-ime-rv64` (VLEN 1024) is a working example.
   - `sail.json` from task A.1 with Zvvmttls enabled. Sail is the DUT here, so Zvvmttls can run.
   - `link.ld` and `rvmodel_macros.h` from `config/sail/sail-rv64-max`.
   - `run_cmd.txt`: `sail_riscv_sim {debug:--trace --trace-output __TRACEFILE__} --config config/sail/sail-rv64-experimental/sail.json`.
2. Add `sail-rv64-experimental` to `exclude_configs` in `config/sail/ci.yaml`. Otherwise the matrix runs it with the
   official Sail 0.16 and no experimental flag, and Sail 0.16 may reject the IME keys in `sail.json`.
3. Add a README for the config. It states that the reference model is temporarily a fork release, why, and the
   upstream Sail pull request that will replace it.

### C. CI

1. In `.github/actions/setup-tools/action.yml`, add an input `sail-repo` with default `riscv/sail-riscv`. Use it in
   the download URL. Add it to both Sail cache keys (restore and save). Without it, the fork and the official release
   share the key `act4-sail-<os>-<arch>-0.16`.
2. In `.github/workflows/regress.yml`, add a job `sail-rv64-experimental` copied from `spike-rv64-experimental`:
   - `setup-tools` with `install-architecture-tools: "true"`, `sail-repo: Openchip-Software/sail-riscv` and
     `sail-version: <tag from package 01>`.
   - Build: `ENABLE_EXPERIMENTAL_EXTENSIONS=True EXTENSIONS=<IME suites> CONFIG_FILES=config/sail/sail-rv64-experimental/test_config.yaml make elfs`.
   - Run: `./run_tests.py "$(cat config/sail/sail-rv64-experimental/run_cmd.txt)" work/sail-rv64-experimental/elfs`.
   - Upload logs as the Spike job does.
   - Use per-SEW suite names (`Zvvmm8` … `Zvvmm64`). `EXTENSIONS=Zvvmm` selects nothing.
3. Do not generalize `ci_config.py` in this pull request. That is a separate refactor for the maintainers (package
   08).

### D. Before opening the pull request

1. Complete package 09, or state in the pull request which checks are still open.
2. Follow AGENTS.md "Before Committing": `mise run prek`, `make tests` with a clean generated diff, the narrowest
   regression, and documentation builds.
3. Write a short pull request description. State the interim Sail fork dependency and link the upstream Sail
   proposal (package 02).

## Acceptance

- All IME suites in the new job pass with the fork release as both DUT and reference.
- No generated testcase embeds a result that contradicts the specification.
- The existing matrix, `check-tests`, `ctp-build` and lint jobs pass.
