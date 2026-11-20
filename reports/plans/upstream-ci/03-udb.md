<!-- SPDX-License-Identifier: Apache-2.0 -->

# 03: Upstream the IME definitions to riscv-unified-db

Repository: `riscv/riscv-unified-db` (UDB). Source: `Openchip-Software/riscv-unified-db`, branch `ime/0.9.0`, with
the FP disclosure and IDL work on `ime/fp-mx` (`f0045fec`, PR #1 into `ime/0.9.0`). Local clone
`~/repo/ime/riscv-unified-db`.

State as of 2026-11-20. ACT pins the `udb` gem 0.1.18 (`framework/src/act/data/Gemfile`), which has no IME. The ACT
branch takes UDB from a worktree of `ime/fp-mx` through the Gemfile variable `UDB_LOCAL_PATH`. ACT has bumped the UDB
gem about once a month.

## Why

Upstream ACT CI installs the released `udb` gem. The IME pull request (package 06) needs a release that defines IME.
The precedent for an unratified extension is Zibi (`spec/std/isa/ext/Zibi.yaml`).

## What the fork defines

- 65 extensions at version 0.9.0, state `development`: the families Zvvmm, Zvvfmm, Zvvmtls and Zvvmttls, the
  computational types and the microscaling types. Each type requires its family, as GCC does.
- `SUPPORTED_LAMBDA_SEW8` … `SUPPORTED_LAMBDA_SEW64`: the λ values per accumulator width. A constraint rejects λ when
  VLEN/(SEW·λ²) is not in {1, 2, 4, 8, 16}.
- `ZVVM_FP_{GROUPING,PSM,RND}_SEW<s>_W<w>` and `ZVVM_FP_PSM1_ALGORITHM`: the FP profile disclosure.
- IDL `operation()` for all Zvvm instructions, and Zvvm tests for the C++ ISS.
- The spec pin `324c62b7`, merged on spec `main` as `58810918`.

## Tasks

1. Merge `ime/fp-mx` into `ime/0.9.0`.
2. Check the UDB contribution guide and how UDB marks unratified extensions. Open the upstream pull request, split
   as the maintainers prefer.
3. Answer review questions about parameter names. ACT uses the names in macros (`UDB_SUPPORTED_LAMBDA_SEW<n>_<λ>`,
   `UDB_ZVVM_FP_RND_SEW<s>_W<w>_IDX<i>_<VALUE>`), so report every rename to the ACT work.
4. When a `udb` gem release contains the definitions, report the version (packages 06 and 08).

## Acceptance

- A released `udb` gem defines the 65 IME extensions and the λ and FP disclosure parameters.
- The ACT configs in `config/ime` validate against that release without `UDB_LOCAL_PATH`.
