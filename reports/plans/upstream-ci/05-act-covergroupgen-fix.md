<!-- SPDX-License-Identifier: Apache-2.0 -->

# 05: ACT: upstream the covergroupgen ExtraExtensions fix

Repository: `riscv/riscv-arch-test`, target branch `act4`. Source commit: `0bb9717a4` on
`Openchip-Software/riscv-arch-test`, branch `port-ime-tests-to-act4` (local clone `~/repo/ime/riscv-arch-test`).

State as of 2026-11-23.

## Status

Prepared, not pushed, pull request not opened. The user approves the push and the pull request.

- Branch `upstream-bugfix/covergroupgen-extraextensions-per-sew`, commit `e254e5250`, on `upstream/act4` `95ca74cb2`
  (2026-11-23). The cherry-pick of `0bb9717a4` applied without conflicts. The commit message is unchanged.
- Worktree: `/srv/nfs/shared/home/constantino.gomez/repo/ime/riscv-arch-test-bugfix-covergroupgen`.
- The fix also stays on the feature branch `cgomez/ime-udb-0.9.0` as `0bb9717a4`.
- `make tests` on the branch leaves `git status` clean.
- `mise run prek` did not complete: mise is too old for `.mise.toml`, the SDK image has no mise or git, and prek
  0.5.7 hangs while it installs hook environments in the shared cache. Ruff, `ruff format --check`, Pyright and
  codespell pass on `generate.py`. Run `mise run prek` before the push.
- A copy of `testplans/Zvbc.csv` that gives `vclmul.vx` the `ExtraExtensions` entry `Zbc` gets a
  `Zvbc64Zbc_vclmul_vx_cg` covergroup with the fix and none without it. With `Zbc` on every row, the code before the
  fix raises `KeyError: ()`.
- The coverage package has no unit-test layout, so the pull request states how the fix was checked (task 4).
- Pull request description draft: `../../issues/act-covergroupgen-extraextensions-per-sew/PR.md`.

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
