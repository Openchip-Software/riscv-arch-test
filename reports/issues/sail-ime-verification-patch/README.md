<!-- SPDX-License-Identifier: Apache-2.0 -->

# Sail verification patch

`sail-specfix.diff` applies to the IME Sail fork at `c69e3e22` (branch `cgomez/0.16-plus-ime`). It is a scratch
patch, used only to verify ACT tests whose expected values differ from the unpatched Sail. It is not proposed as a
Sail change as it stands.

It contains three fixes:

| Fix                                                                                                                                                                                                           | Work item | Report 2   |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | ---------- |
| Tile loads and stores use `ime_tile_reg_idx`, not the flat element index (`sail-fix.diff` of `sail-ime-tile-ls-index/`)                                                                                       | 1         | §16, §16a  |
| Tile loads and stores select the natural LD when the value of `rs2` is 0, not only when `rs2` is `x0`                                                                                                         | 12        | finding 21 |
| MACC accepts `EMUL_C`=16. `ime_read_c` and `ime_write_c` address the upper 8 registers of C as a second group, because `read_single_element` and `write_single_element` assert a group of at most 8 registers | 11        | finding 20 |

Status on 2026-11-06: the Sail fork at `a545cc41` contains the first two fixes (`a545cc41` and `c1d96b3e`).
Only the `EMUL_C`=16 fix is still needed. `../sail-ime-legality/ISSUE-emulc16.md` describes it.

Build: copy the Sail fork source at `c69e3e22`, apply the patch, and build `sail_riscv_sim` as for the unpatched
fork. On 2026-10-28 the build was at `~/tools/act4/sail-specfix/build-specfix/c_emulator/sail_riscv_sim`.

Use: `export SAIL_IME_SIM=<that binary>`, then build and run the IME suites as in `plans/HANDOFF.md`.
