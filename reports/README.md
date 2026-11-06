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

## Proof of concept (`ime-poc/`)

These files back Report 2, Section 15. The DUT configurations contain absolute paths
to the author's home directory and the SDK image. Adjust them before use. The toolchain
wrappers and job scripts that the configurations name are machine-specific and are not
checked in. Report 2 describes them.

| Path                | Purpose                                                                              |
| ------------------- | ------------------------------------------------------------------------------------ |
| `ir2act.py`         | Converts `ime-test-gen --emit-ir` JSON (integer MACC) into ACT test files.           |
| `make_sail_json.py` | Converts an ACT 0.16 `sail.json` to the schema of the IME Sail fork.                 |
| `crosscheck.py`     | Compares Sail signatures with the Rust golden values.                                |
| `slang_check.py`    | Compiles the ACT coverage testbench with pyslang when no Questa or VCS is available. |
| `config/`           | DUT configurations: the IME Sail fork as DUT, and the SDK QEMU as DUT.               |

## Sail issue draft (`issues/sail-ime-tile-ls-index/`)

These files back Report 2, Sections 16 and 16a. They document that the IME Sail fork's `vmtl.v` and
`vmts.v` use the flat element index instead of `tile_reg_idx`. The issue is a draft and is not filed.
`a545cc41` fixed the bug on 2026-11-06, so the issue no longer needs filing.

| Path                          | Purpose                                                                      |
| ----------------------------- | ---------------------------------------------------------------------------- |
| `ISSUE.md`                    | Issue text for Openchip-Software/sail-riscv.                                 |
| `sail-ime-tile-ls-index.html` | The issue rendered as one HTML file.                                         |
| `repro.c`, `start.S`          | Bare-metal reproducer at VLEN=256, SEW=32, LMUL=2, lambda=1.                 |
| `link.ld`, `sail-ime.json`    | Linker script and Sail configuration override for the reproducer.            |
| `run.sh`                      | Builds the reproducer with the SDK GCC and runs it on Sail and the SDK QEMU. |
| `sail-fix.diff`               | Patch for `ime_mem_insts.sail` at `c69e3e22`.                                |
| `qemu.out`, `sail.out`        | Output of `run.sh` on the SDK QEMU and on Sail `c69e3e22`.                   |
| `sail-fixed.out`              | Output of `run.sh` on Sail with `sail-fix.diff`, when `SAIL_FIXED` is set.   |
| `repro.elf`, `repro.objdump`  | Build outputs of `run.sh`.                                                   |

`run.sh` takes `SDK_SIF`, `SAIL` and, optionally, `SAIL_FIXED` from the environment. The defaults
are paths on the author's machine.

## Sail issue draft (`issues/sail-ime-wmmacc-partial-sum/`)

These files back Report 2, Section 16b. They document that the IME Sail fork's `vfwmmacc.vv`,
`vfqmmacc.vv` and `vf8wmmacc.vv` add each product into C instead of forming the sub-dot-product sum first.
The issue is a draft and is not filed. It is pinned to `a545cc41`. There is no patch yet.

| Path                           | Purpose                                                                    |
| ------------------------------ | -------------------------------------------------------------------------- |
| `ISSUE.md`                     | Issue text for Openchip-Software/sail-riscv.                               |
| `fprnd.c`, `start.S`           | Bare-metal probe at VLEN=256, λ=1: W=1, W=2 and W=4 cases.                 |
| `link.ld`, `sail.json`         | Linker script and Sail configuration override for the probe.               |
| `run.sh`                       | Builds the probe with the SDK GCC and runs it on Sail and the SDK QEMU.    |
| `qemu.out`, `sail.out`         | Output of `run.sh` on the SDK QEMU and on Sail `c69e3e22`.                 |
| `qemu-mixed.out`               | Output of `fprnd-mixed.elf` on the SDK QEMU: adds a mixed-format W=1 case. |
| `fprnd.elf`, `fprnd-mixed.elf` | Build outputs of `run.sh`.                                                 |

`run.sh` takes `SDK_SIF` and `SAIL` from the environment. The defaults are paths on the author's
machine.

## Sail issue drafts (`issues/sail-ime-legality/`)

These files back Report 2, Section 16a (Sail fork update, 2026-11-06). They document two legality checks of the
IME Sail fork at `a545cc41` that disagree with the specification. The issues are drafts and are not filed.

| Path                   | Purpose                                                                              |
| ---------------------- | ------------------------------------------------------------------------------------ |
| `ISSUE-emulc16.md`     | Issue text: matrix multiply-accumulate traps for `EMUL_C`=16.                        |
| `ISSUE-tile-vl.md`     | Issue text: tile loads and stores do not trap when VL is not a multiple of λ·LMUL.   |
| `legal.c`, `start.S`   | Bare-metal probe at VLEN=256 with a trap handler that records `mcause`; serves both. |
| `link.ld`, `sail.json` | Linker script and Sail configuration override for the probe.                         |
| `run.sh`               | Builds the probe with the SDK GCC and runs it on Sail.                               |
| `sail.out`             | Output of `run.sh` on Sail `a545cc41`.                                               |

`run.sh` takes `SDK_SIF` and `SAIL` from the environment. The defaults are paths on the author's
machine.

## Sail verification patch (`issues/sail-ime-verification-patch/`)

`sail-specfix.diff` fixes the three Sail deviations that the ACT IME tests hit: the tile register index, the
natural LD for a register that holds 0, and `EMUL_C`=16. It is a scratch patch for verifying the tests. Sail
`a545cc41` fixes the first two, so only `EMUL_C`=16 still needs it. Report 2,
Section 16a, step 3, gives the results. See its `README.md`.

## Plans (`plans/`)

| Path                         | Purpose                                                                                     |
| ---------------------------- | ------------------------------------------------------------------------------------------- |
| `HANDOFF.md`                 | Self-contained handoff for the next agent or engineer: setup, rules, status and next steps. |
| `ime-act-testplan-design.md` | Full testplan design (option C) behind Report 2, Section 16b.                               |
