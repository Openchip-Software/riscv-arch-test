<!-- SPDX-License-Identifier: Apache-2.0 -->

# Technical reports

| Report                                              | File                      |
| --------------------------------------------------- | ------------------------- |
| 1. ACT4: components, workflow and examples          | `act-architecture.html`   |
| 2. IME test generator: analysis and ACT integration | `ime-testgen-to-act.html` |

Each report is one self-contained HTML file. Open it in a browser. Report 2 describes the state of 2026-11-07
(overlay, Sail `a545cc41`, spec `6effbcae`); `plans/HANDOFF.md` has the current state.

## Rebuild

The sources are in `src/` and the SVG figures in `figures/`. To rebuild:

```sh
python3 reports/build.py act-architecture ime-testgen-to-act
python3 reports/check_cites.py reports/src/act-architecture.src.html .
python3 reports/check_cites.py reports/src/ime-testgen-to-act.src.html ../riscv-ime-arch-tests .
```

`build.py` inlines `src/report.css`, `src/report.js` and the figures. It also turns
each `{{src:path:lines}}` placeholder into a link pinned to the commit named in the
source file. `check_cites.py` checks that every cited file exists and that every
cited line range is inside the file.

## Tools (`ime-poc/`)

`slang_check.py` compiles the ACT coverage testbench with pyslang when no Questa or VCS is available.
`plans/HANDOFF.md` gives the command.

## Issue drafts (`issues/`)

`ime-fp-internal-zero-sign/ISSUE.md`: spec gap, not filed. The spec does not define the sign of `fp_internal_zero()`
or of an exact zero group sum, so C = −0 with all −0 products has no defined result. Sail starts S at +0. Cited at
spec `e99d9065` and Sail `7707a9a1`.

`sail-ime-wmmacc-partial-sum/`: obsolete draft, kept because Report 2 links to it. The W>1 partial-sum bug it
describes is fixed in Sail (`ime_fp_group_sum`). The SDK QEMU still has it.

Filed Sail issues are tracked on GitHub, not here. `EMUL_C`=16 is
[Openchip-Software/sail-riscv#10](https://github.com/Openchip-Software/sail-riscv/issues/10), fixed in
`cleanup/ime-0.9.0`.

## Plans (`plans/`)

| Path                         | Purpose                                                                                     |
| ---------------------------- | ------------------------------------------------------------------------------------------- |
| `HANDOFF.md`                 | Self-contained handoff for the next agent or engineer: setup, rules, status and next steps. |
| `udb-0.9.0.md`               | Log of the move to riscv-unified-db and spec `58810918`, one section per step.              |
| `ime-act-testplan-design.md` | Full testplan design (option C) behind Report 2, Section 16b.                               |
| `upstream-ci/`               | Work packages for upstream CI, one self-contained file per repository.                      |
