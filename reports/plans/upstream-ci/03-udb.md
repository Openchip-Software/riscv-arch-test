<!-- SPDX-License-Identifier: Apache-2.0 -->

# 03: Upstream the IME definitions to riscv-unified-db

Repository: `riscv/riscv-unified-db` (UDB). Source files: the ACT overlay at
`framework/src/act/data/udb_overlays/ime/` on `Openchip-Software/riscv-arch-test`, branch `port-ime-tests-to-act4`
(local clone `~/repo/ime/riscv-arch-test`).

State as of 2026-11-09. ACT pins the `udb` gem 0.1.18 (`framework/src/act/data/Gemfile`). ACT has bumped the UDB gem
about once a month (2026-08-17, 2026-09-29, 2026-10-23).

## Why

UDB 0.1.18 does not define the IME extensions, so the ACT branch adds an overlay mechanism to
`framework/src/act/parse_udb_config.py`. Upstream ACT may not want a new mechanism for one extension. The precedent is
Zibi, which UDB defines in `spec/std/isa/ext/Zibi.yaml`. If a UDB release defines IME before the ACT pull request
merges, the ACT pull request can drop the overlay mechanism.

## What the overlay contains

- 65 extension files under `ext/`: the family extensions Zvvmm, Zvvfmm, Zvvmtls and Zvvmttls, 31 computational
  extensions and 30 microscaling extensions. Each computational extension requires its family extension, which
  matches GCC 16.1.
- 4 parameter files under `param/`: `SUPPORTED_LAMBDA_SEW8` to `SUPPORTED_LAMBDA_SEW64`. Each lists the λ values the
  implementation supports for one accumulator width. A constraint rejects λ when VLEN/(SEW·λ²) is not in
  {1, 2, 4, 8, 16}.
- License: `BSD-3-Clause-Clear OR Apache-2.0`, so the files can move into UDB without relicensing.

## Tasks

1. Check the UDB contribution guide and how UDB marks unratified extensions (look at Zibi's `state` and version
   fields). Mark the IME extensions the same way.
2. Move the 69 files into UDB's layout (`spec/std/isa/ext/`, `spec/std/isa/param/` or the current equivalents). Keep
   the specification commit `6effbcae` in each file's description or reference fields.
3. Run UDB's own validation and tests.
4. Open the pull request. Answer review questions about λ parameter naming. ACT test headers use the names as
   `params` (for example `SUPPORTED_LAMBDA_SEW32: 1`), so any rename must be reported to the ACT work.
5. When a UDB gem release contains the definitions, report the version to the ACT work (packages 06 and 08).

## Acceptance

- A released `udb` gem defines the 65 IME extensions and the four λ parameters.
- The ACT configs in `config/ime` resolve against that release without the overlay.
