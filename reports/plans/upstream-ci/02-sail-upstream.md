<!-- SPDX-License-Identifier: Apache-2.0 -->

# 02: Upstream IME to riscv/sail-riscv

Repository: `riscv/sail-riscv`, default branch `master`. Source of the changes: `Openchip-Software/sail-riscv`, branch
`integrated-matrix-extension` (local clone `~/repo/ime/sail-riscv`).

State as of 2026-11-09. Upstream has no IME pull request or issue.

## Why

Upstream ACT CI takes its reference model only from official `riscv/sail-riscv` releases. While IME exists only in
the Openchip fork, ACT must download a fork release (package 06). Upstream ACT maintainers are more likely to accept
that as an interim step if an upstream Sail pull request is already open. When an upstream Sail release contains
IME, ACT can drop the fork (package 08).

## Precedent

Upstream Sail already models an unratified extension: Zibi, enabled only with `--enable-experimental-extensions`.
IME must follow the same rule. The fork already gates the `Zvvm*` extensions behind that flag.

## Tasks

1. Wait for package 01 to fix integer `EMUL_C`=16, so the upstream pull request has no known deviation.
2. Open an issue in `riscv/sail-riscv` that proposes IME as an experimental extension. Link the specification at its
   pinned commit and the fork branch. Ask the maintainers how they want the change split.
3. Split the fork's IME commits into reviewable pull requests against upstream `master`. One possible order:
   `vtype` fields and `vsetvl` handling; tile loads and stores; integer multiply-accumulate; FP multiply-accumulate
   with the exact engine; microscaling. Follow upstream's contribution rules, formatting and test layout.
4. Keep every deviation from the specification out of the pull requests, or document it where the specification is
   silent. The fork declares one deviation: microscaling block scales are applied exactly instead of through the
   specification's `read_block_scales`. Resolve or justify it before review.
5. Track each upstream pull request in the fork's README, so the ACT work knows when a release contains IME.

## Acceptance

- An upstream Sail release contains IME behind `--enable-experimental-extensions`.
- Report the release version to the ACT work (package 08).
