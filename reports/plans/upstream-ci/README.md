<!-- SPDX-License-Identifier: Apache-2.0 -->

# Upstream CI for the IME tests: work packages

Goal: merge the Integrated Matrix Extension (IME) tests into upstream `riscv/riscv-arch-test` (branch `act4`) with
CI that runs them. Each file below is one work package for one repository. Each file is self-contained, so an agent
working in that repository needs only that file.

State as of 2026-11-09.

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

Critical path: 01 (fix integer `EMUL_C`=16, publish a fork release) → 06 (the IME pull request). 05 and 09 can start
now. 02, 03 and 04 run in parallel and shorten 07 and 08.

## Shared facts

- IME specification pinned at commit `6effbcae`. The ARC review branch changes some rules (see 06).
- Source of truth: the specification. Where it is silent, follow the Sail fork and record "spec silent; Sail
  behaviour". Never use QEMU, GCC or the Rust `ime-test-gen` golden model as the source of truth.
- ACT import branch: `Openchip-Software/riscv-arch-test`, branch `port-ime-tests-to-act4`, three commits on `act4`
  `7569d06d6`:
  - `0bb9717a4` Keep ExtraExtensions rows in per-SEW covergroups (generic fix, work package 05).
  - `98595c2a5` Add tests for the Integrated Matrix Extension (work package 06).
  - `8ada25d12` Add an IME DUT configuration with the SDK QEMU (Openchip fork only, never upstream).
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
