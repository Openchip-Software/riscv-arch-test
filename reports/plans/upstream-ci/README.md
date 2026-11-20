<!-- SPDX-License-Identifier: Apache-2.0 -->

# Upstream CI for the IME tests: work packages

Goal: merge the Integrated Matrix Extension (IME) tests into upstream `riscv/riscv-arch-test` (branch `act4`) with
CI that runs them. Each file below is one work package for one repository. Each file is self-contained, so an agent
working in that repository needs only that file.

State as of 2026-11-20. Packages 01-09 were written on 2026-11-09; the facts below are current.

| File                                                       | Repository                            | Depends on   |
| ---------------------------------------------------------- | ------------------------------------- | ------------ |
| [01-sail-fork.md](01-sail-fork.md)                         | `Openchip-Software/sail-riscv`        | —            |
| [02-sail-upstream.md](02-sail-upstream.md)                 | `riscv/sail-riscv`                    | 01           |
| [03-udb.md](03-udb.md)                                     | `riscv/riscv-unified-db`              | —            |
| [04-qemu-ime.md](04-qemu-ime.md)                           | `Openchip-Software/riscv-ime-qemu`    | —            |
| [05-act-covergroupgen-fix.md](05-act-covergroupgen-fix.md) | `riscv/riscv-arch-test`               | —            |
| [06-act-ime-tests-ci.md](06-act-ime-tests-ci.md)           | `riscv/riscv-arch-test`               | 01 (release) |
| [07-act-qemu-dut.md](07-act-qemu-dut.md)                   | `riscv/riscv-arch-test`               | 04, 06       |
| [08-act-cleanup.md](08-act-cleanup.md)                     | `riscv/riscv-arch-test`               | 02, 03, 06   |
| [09-act-verification.md](09-act-verification.md)           | `riscv/riscv-arch-test` (checks only) | —            |

Critical path: 01 (publish a fork release of `cleanup/ime-0.9.0`) and 03 (a UDB release with IME) → 06 (the IME pull
request). 05 and 09 can start now. 02 and 04 run in parallel and shorten 07 and 08.

## Shared facts

- IME specification pinned at commit `58810918` (v0.9.0-on-main plus exact E8M0 block scales). UDB, Sail and the
  tests follow the same commit.
- Source of truth: the specification. Where it is silent, follow the Sail fork and record "spec silent; Sail
  behaviour". Never use QEMU, GCC or the Rust `ime-test-gen` golden model as the source of truth.
- ACT branch: `Openchip-Software/riscv-arch-test` `cgomez/ime-udb-0.9.0`, eight commits on `act4` `7569d06d6`
  (list in `../HANDOFF.md` §5):
  - `0bb9717a4`: generic covergroupgen fix (work package 05).
  - `98595c2a5`, `49b999ce9`, `413966b5a`, `aaa0c329c`, `59666b161`: the IME tests (work package 06). `49b999ce9`
    removes the UDB overlay of `98595c2a5`.
  - `8ada25d12`, `b186cce44`: the `config/ime` DUT configurations (Openchip fork only, never upstream).
- UDB: the IME definitions come from `Openchip-Software/riscv-unified-db` `ime/fp-mx` through the ACT Gemfile
  variable `UDB_LOCAL_PATH`.
- Reference model: `Openchip-Software/sail-riscv` `cleanup/ime-0.9.0` `0ebfc810`.
- Upstream ACT CI facts that every package must respect:
  - The reference model is the official `riscv/sail-riscv` release, downloaded in
    `.github/actions/setup-tools/action.yml` (input `sail-version`, default `0.16`). The cache key is
    `act4-sail-<os>-<arch>-<sail-version>`.
  - The matrix job (`.github/workflows/regress.yml`, job `regress`, discovered by `.github/scripts/ci_config.py`)
    never passes `ENABLE_EXPERIMENTAL_EXTENSIONS`. Experimental extensions run in a dedicated job,
    `spike-rv64-experimental` (Zibi on Spike).
  - Simulators are built from source by `.github/scripts/install-<sim>.sh` at a pinned version. The cache key is the
    script's hash. Renovate (`renovate.json`, `customManagers`) bumps each pin.
  - Configs under `config/sail/` run Sail as DUT against Sail as reference. Their README says they only debug
    self-checking tests and collect coverage.
- The upstream GCC (`riscv64-unknown-elf-gcc` 16.1) builds every IME suite. The `.insn` macros in
  `tests/env/rvtest_experimental.h` remove the need for an IME compiler. Clang is not verified (09).
