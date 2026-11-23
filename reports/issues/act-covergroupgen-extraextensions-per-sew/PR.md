<!-- SPDX-License-Identifier: Apache-2.0 -->

<!-- Target: riscv/riscv-arch-test, base act4. Pull request draft, not opened. Branch
upstream-bugfix/covergroupgen-extraextensions-per-sew @ e254e5250, on act4 @ 95ca74cb2. -->

# Keep ExtraExtensions rows in per-SEW covergroups

`read_testplans` in `generators/coverage/src/covergroupgen/generate.py` stored the testplan rows that have an
`ExtraExtensions` entry under the testplan name, for example `Zvbc`. A vector testplan expands into per-SEW suites.
The covergroup jobs look up these rows under the per-SEW name, for example `Zvbc64`. covergroupgen therefore wrote no
covergroup for these rows, while testgen still generated their tests. A testplan in which every row has an
`ExtraExtensions` entry raised `KeyError: ()`.

Each per-SEW suite now receives the `ExtraExtensions` rows whose `EFFEW` column selects its SEW. A testplan in which
every row has an `ExtraExtensions` entry now has an empty base testplan.

No current per-SEW testplan has an `ExtraExtensions` column, so `make tests` produces no change in the generated
files. The fix was checked with a copy of `testplans/Zvbc.csv` that gives `vclmul.vx` the entry `Zbc`. With the fix,
`Zvbc64_coverage.svh` gets a `Zvbc64Zbc_vclmul_vx_cg` covergroup inside `` `ifdef ZBC_SUPPORTED ``. Without the fix,
this covergroup is missing.
