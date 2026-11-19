<!-- SPDX-License-Identifier: Apache-2.0 -->

# IME on riscv-unified-db ime/fp-mx and spec 58810918

Started 2026-11-19. Code branch `cgomez/ime-udb-0.9.0` in `~/repo/ime/riscv-arch-test`, on `port-ime-tests-to-act4`.

## Pins

| What           | Where                                                                            | Commit                                                        |
| -------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| UDB            | Openchip-Software/riscv-unified-db `ime/fp-mx`, worktree `~/repo/ime/udb-act`    | `f0045fec2ee773e3753375d238c1dad66f593c91`                    |
| Sail reference | Openchip-Software/sail-riscv `cleanup/ime-0.9.0`, worktree `~/repo/ime/sail-act` | `0ebfc810f523fd225d02edbb78d375737141e825`                    |
| IME spec       | riscv/integrated-matrix-extension                                                | `58810918` (= v0.9.0-on-main + `324c62b7`, exact E8M0 scales) |

Before this work the tests followed spec `6effbcae` (same IME text as `3763fa96`, the v0.9 freeze of 2026-08-04) and
Sail `cgomez/0.16-plus-ime` `a545cc41`.

`ime/fp-mx` will merge into `ime/0.9.0`. Then move the `udb-act` worktree to `ime/0.9.0`; nothing else changes.

## Environment

```bash
source ~/tools/act4/env.sh   # mise, XDG_DATA_HOME and BUNDLE_PATH on local disk, UDB_LOCAL_PATH=~/repo/ime/udb-act
export PATH=$PWD/config/ime/bin:$PATH SDK_SIF=~/repo/ime/sdk-2026.10.14.sif
export SAIL_IME_SIM=~/repo/ime/sail-act/build-act/c_emulator/sail_riscv_sim
```

- `env.sh` was recreated on 2026-11-19. mise is the binary that `riscv-unified-db/bin/mise` bootstraps
  (`~/.local/share/mise/bootstrap/mise-2026.10.17`, linked as `~/tools/act4/bin/mise`).
- `bundle install` onto NFS hangs in the NFS server-side copy (`handle_async_copy`) while it installs `prism.so`.
  `BUNDLE_PATH=/tmp/$USER-act-bundle` avoids it. `/tmp` is lost on reboot; the next ACT run reinstalls.
- `UDB_LOCAL_PATH` makes bundler rewrite `framework/src/act/data/Gemfile.lock`. Restore it before each commit.
- `~/repo/ime/udb-act/gen` points to `/tmp/$USER-udb-act-gen`.
- Helper scripts in `~/repo/ime/act-udb-work/`: `fp_disclosure.py` prints the `ZVVM_FP_*` parameters for a config,
  `phase1-run.sh` builds and runs suites on `qemu-ime-rv64`.

## Step 1: overlay replaced by UDB (`49b999ce9`)

- The overlay `framework/src/act/data/udb_overlays/ime` and the `arch_overlay` handling in `parse_udb_config.py` are
  removed. `parse_udb_config.py` is the `act4` version again.
- `toolchain.py` lists the 65 IME extensions, as `testgen/constants.py` does.
- `qemu-ime-rv64.yaml`: Zvvm versions 1.0.0 → 0.9.0. The UDB on `ime/fp-mx` is newer than gem 0.1.18 and rejects
  five Sdext/SCONTEXT parameters; it requires the stateen `C`/`SE0` types and `HEDELEG_IAM_WRITABLE`. The values come
  from the write masks in the SDK QEMU (`target/riscv/csr.c`).
- QEMU FP disclosure: G=1, psm=0, rnd=xct. QEMU adds each product to C with one `float*_muladd` rounded with `frm`
  (`trans_rvzvvmm.c.inc`). For W>1 it also adds product by product, which no disclosure describes; the config repeats
  the W=1 profile.
- Check: `extensions.txt` unchanged. `rvtest_config.h` differs only in version macros, the base parameters above and
  115 new `UDB_ZVVM_FP_*` lines. Zvvmm32, Zvvfmm32 and Zvvmtls32 with Sail `a545cc41`: 10/10 files pass on QEMU, as
  before.

## Step 2: Sail cleanup/ime-0.9.0 and `sail-ime-rv64` (`b186cce44`)

- Sail built on moon with `~/repo/ime/sail-riscv-work/build.sh ~/repo/ime/sail-act ~/repo/ime/sail-act/build-act`
  (job 65550, about 30 minutes with a cold z3 cache).
- This Sail needs three new `sail.json` keys: `base.misa_implemented`, `H.hedeleg_zero_writable` and the Sdtrig
  `mcontrol6` access-size tables (Sail defaults; not checked against QEMU).
- `config/ime/sail-ime-rv64`: `sail-rv64-max` (VLEN 1024) with the IME, Zvvmttls and Sail's profile. Sail is the DUT.

## Step 3: new tests for spec 58810918 (`413966b5a`, `aaa0c329c`)

- `cp_ime_vd_overlap` (ExceptionsZvvm): `vs1`/`vs2` = base of C, `vs2` = last register of C per λ, and VL = 0.
- `cp_fp_rnd` (Zvvfmm): a partial sum S that is not exact in the C format, gated on rnd=frm and psm=0.

Results with Sail `0ebfc810` (all suites at all SEWs, ExceptionsZvvm):

| Config          | Result                                                                                                                                                                         |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `sail-ime-rv64` | 41/41 files pass, Zvvmttls and ExceptionsZvvm included. SEW=16 MACC builds again (EMUL_C=16 fixed in Sail).                                                                    |
| `qemu-ime-rv64` | Integer and tile suites pass. The 5 W>1 Zvvfmm files fail at `cp_fp_subdot` (QEMU adds products one by one). ExceptionsZvvm fails 7/7 at `cp_ime_vstart` (QEMU does not trap). |

The ELFs stop at the first failure, so later bins of the failing QEMU files are not measured.

UDB macro forms: string values are uppercase (`UDB_ZVVM_FP_RND_SEW32_W2_IDX0_XCT`). Boolean arrays emit only
`UDB_ZVVM_FP_PSM_SEW<s>_W<w>_MASK`.

## Decisions

- **Family flags.** In UDB each type extension requires its family; a family alone enables no type. In Sail a family
  flag (`Zvvmm`, `Zvvfmm`) enables every type of the family (`currentlyEnabled` in `ime_types.sail`), OFP8 included.
  The `sail.json` files therefore set the families to false and each declared type to true, so Sail implements
  exactly the rows that the UDB config declares.
- **Gated FP tests.** Sail computes rnd=frm only. A test that depends on rnd is generated for rnd=frm and gated on
  `UDB_ZVVM_FP_RND_SEW<s>_W<w>_IDX<i>_FRM` and psm=0. QEMU discloses xct and skips them; their bins stay open there.
- **Sail as DUT.** `config/ime/sail-ime-rv64` is `config/sail/sail-rv64-max` (VLEN 1024) plus the IME extensions,
  Zvvmttls, the λ lists for VLEN 1024 and Sail's profile. It runs the gated tests and Zvvmttls.

## Spec delta 6effbcae → 58810918 and the ACT tests

| Spec commit                                                            | Change                                                                                 | ACT impact                                                                                                                               |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `5bcd3946`                                                             | `vd` shall not overlap `vs1` or `vs2`, regardless of VL                                | New `cp_ime_vd_overlap` in ExceptionsZvvm (base, last register of C, VL = 0). The MMACC formatter already kept them apart.               |
| `3c1b4457`                                                             | Each A/B register holds λ·W consecutive K elements per row (was λ)                     | No generator change: testgen does not model the layout, Sail computes the values. QEMU uses the old mapping and should fail W>1, LMUL>1. |
| `cc42d98d`                                                             | N = VL/(λ·LMUL); VL not a multiple stays illegal                                       | None. `cp_ime_vl_not_multiple` stays.                                                                                                    |
| `e4bf2c19`                                                             | `vta=1`: each tail element independently unchanged or all ones; VL = 0 updates nothing | None: MACC tests use `vta=0`.                                                                                                            |
| `26b0fd87`, `d74d8d85`, `fcca60a8`                                     | W=1 term is the exact product; products may leave the C exponent range                 | None: FP data is exact under every profile.                                                                                              |
| `fcc718d4`, `2a1fc11f`, `9eea6c86`, `dbc788ec`                         | Intrinsics text (immediate λ, mask type, `__riscv_vsetlambda`)                         | None. The immediate-λ rule matches `cp_ime_imm_lambda_unsupported`.                                                                      |
| `37840bb8`                                                             | psm=1 rules                                                                            | Gated tests require psm=0.                                                                                                               |
| `ad2d5f22`, `7ac568a5`, `0a13020a`, `e06eca02`, `40446383`, `324c62b7` | Block scales (E8M0, exact, LMUL limits, count)                                         | Step 4 (microscaling).                                                                                                                   |

## OFP8 tests set aside

Sail `0ebfc810` decodes the OFP8 accumulator rows and raises illegal instruction for them. The pending Sail branch
`cgomez/ime-ofp8-acc` (`2cb7eefb`) implements them. Tests for these extensions are listed here and handled with that
PR:

| Extension                           | Rows                        | Status              |
| ----------------------------------- | --------------------------- | ------------------- |
| `Zvvofp8mm`                         | `vfmmacc.vv` SEW=8          | no testplan row yet |
| `Zvvofp4ofp8mm`                     | `vfwmmacc.vv` SEW=8         | no testplan row yet |
| `Zvvxofp4ofp8mm`, `Zvvxnofp4ofp8mm` | `vfwmmacc.vv` SEW=8, `vm=0` | no testplan row yet |
