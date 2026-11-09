<!-- SPDX-License-Identifier: Apache-2.0 -->

# 05: ACT: upstream the covergroupgen ExtraExtensions fix

Repository: `riscv/riscv-arch-test`, target branch `act4`. Source commit: `0bb9717a4` on
`Openchip-Software/riscv-arch-test`, branch `port-ime-tests-to-act4` (local clone `~/repo/ime/riscv-arch-test`).

State as of 2026-11-09.

## Why

This fix is independent of IME. A small, generic pull request is easy to review and removes it from the IME pull
request (package 06).

## The bug

`read_testplans` in `generators/coverage/src/covergroupgen/generate.py` stored rows that have an `ExtraExtensions`
entry under the testplan name, for example `Zvbc`. A vector testplan expands into per-SEW suites, and the covergroup
jobs look rows up under the per-SEW name, for example `Zvbc64`. covergroupgen therefore wrote no covergroup for these
rows. testgen still generated their tests, so their coverage was never collected. A testplan whose rows all had an
`ExtraExtensions` entry raised `KeyError`.

No current upstream per-SEW testplan has `ExtraExtensions` rows, so the generated covergroups do not change.

## Tasks

1. Create a branch from upstream `act4` and cherry-pick `0bb9717a4`.
2. Read `AGENTS.md` and follow it. Run `mise run prek` and fix all failures.
3. Run `make tests` and confirm that `git status` shows no generated changes.
4. Add a unit test if the coverage package has a test layout that fits. Otherwise state in the pull request how the
   fix was checked.
5. Open the pull request against `act4`. Keep the description short: what was wrong and what changed.

## Acceptance

- The pull request passes upstream CI, including `check-tests`.
