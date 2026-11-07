<!-- SPDX-License-Identifier: Apache-2.0 -->

# Technical reports

| Report                                              | File                      |
| --------------------------------------------------- | ------------------------- |
| 1. ACT4: components, workflow and examples          | `act-architecture.html`   |
| 2. IME test generator: analysis and ACT integration | `ime-testgen-to-act.html` |

Each report is one self-contained HTML file. Open it in a browser.

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

## Sail issue draft (`issues/sail-ime-wmmacc-partial-sum/`)

Draft issue for Openchip-Software/sail-riscv, not filed. The IME Sail fork's W>1 FP multiply-accumulate
instructions (`vfwmmacc.vv`, `vfqmmacc.vv`, `vf8wmmacc.vv`) add each product into C instead of forming the
sub-dot-product sum first. Report 2, finding 30.

| Path                   | Purpose                                                                    |
| ---------------------- | -------------------------------------------------------------------------- |
| `ISSUE.md`             | Issue text.                                                                |
| `fprnd.c`, `start.S`   | Bare-metal probe at VLEN=256, λ=1: W=1, W=2 and W=4 cases.                 |
| `link.ld`, `sail.json` | Linker script and Sail configuration override for the probe.               |
| `run.sh`               | Builds the probe with the SDK GCC and runs it on Sail and the SDK QEMU.    |
| `qemu.out`, `sail.out` | Output of `run.sh` on the SDK QEMU and on Sail.                            |
| `qemu-mixed.out`       | Output of `fprnd-mixed.elf` on the SDK QEMU: adds a mixed-format W=1 case. |

`run.sh` takes `SDK_SIF` and `SAIL` from the environment. The defaults are paths on the author's machine.

Filed Sail issues are tracked on GitHub, not here. `EMUL_C`=16 is
[Openchip-Software/sail-riscv#10](https://github.com/Openchip-Software/sail-riscv/issues/10).

## Plans (`plans/`)

| Path                         | Purpose                                                                                     |
| ---------------------------- | ------------------------------------------------------------------------------------------- |
| `HANDOFF.md`                 | Self-contained handoff for the next agent or engineer: setup, rules, status and next steps. |
| `ime-act-testplan-design.md` | Full testplan design (option C) behind Report 2, Section 16b.                               |
