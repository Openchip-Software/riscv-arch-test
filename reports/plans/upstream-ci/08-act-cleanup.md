<!-- SPDX-License-Identifier: Apache-2.0 -->

# 08: ACT: remove the interim pieces

Repository: `riscv/riscv-arch-test`, target branch `act4`. Runs after package 06 merges, as upstream Sail and UDB
releases arrive.

State as of 2026-11-20. Nothing to do yet.

## Why

Package 06 uses a Sail fork release as reference model. It should go once upstream Sail provides IME. The ACT-local
UDB overlay is already removed.

## Tasks

1. **Upstream Sail contains IME** (package 02).
   - Remove the `sail-repo` and `sail-version` overrides from the `sail-rv64-experimental` job, so it uses the same
     Sail as the rest of CI.
   - Keep the `sail-repo` input in `setup-tools` only if another job still uses it. Otherwise remove it.
   - Update the `sail.json` files for the official release's schema, and update the config README.
   - Rerun the IME suites and diff the signatures against the fork release. Explain every difference.
2. **Optional refactor, for the maintainers to decide.** Add an `enable_experimental_extensions` key to the per-simulator
   `ci.yaml`, and pass it through `.github/scripts/ci_config.py` and the matrix job. The dedicated jobs
   `spike-rv64-experimental`, `sail-rv64-experimental` and `qemu-ime-rv64` could then become matrix entries. Propose
   it in an issue first.

## Acceptance

- No IME job downloads anything from an Openchip repository except the QEMU source in package 07.
