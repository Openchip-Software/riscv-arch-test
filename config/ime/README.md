# ACT Configuration for the Integrated Matrix Extension (IME)

These configurations bring up IME (Zvvm\*) testing. The toolchain comes from the OpenChip SDK image. The
reference model is the Sail IME fork, Openchip-Software/sail-riscv branch `cleanup/ime-0.9.0`. The tests
follow the IME specification at commit 58810918 (v0.9.0-on-main with exact E8M0 block scales).

| Config                 | DUT                                                                | VLEN  | Reference model |
| ---------------------- | ------------------------------------------------------------------ | ----- | --------------- |
| `qemu-ime-rv64`        | SDK `qemu-system-riscv64` 10.2.50, `-cpu max,vlen=256,x-zvvm=true` | 256   | Sail IME fork   |
| `sail-ime-rv64`        | Sail IME fork                                                      | 1024  | Sail IME fork   |
| `sail-ime-rv64-v16384` | Sail IME fork                                                      | 16384 | Sail IME fork   |

## Common to all configurations

- The Zvvm extensions, the `SUPPORTED_LAMBDA_SEW*` parameters and the `ZVVM_FP_*` disclosure parameters
  come from riscv-unified-db branch `ime/fp-mx` (Openchip-Software fork). No UDB release defines them yet,
  so ACT uses a local checkout of that branch through `UDB_LOCAL_PATH` (see Setup). The extension version
  is 0.9.0.
- The lambda lists contain the values that the specification permits for the VLEN of the configuration:
  VLEN/(SEW\*lambda^2) is 1, 2, 4, 8 or 16. The Sail fork supports exactly these values.
- The `ZVVM_FP_*` parameters disclose the floating-point profile of the DUT: the group size G, the partial-sum
  mode psm and the rounding rnd of a group partial sum. Sail computes G=1, psm=0, rnd=frm. Tests whose result
  depends on rnd are generated for rnd=frm and run only on a DUT that discloses it.
- In UDB each type extension (for example Zvvfp16fp32mm) requires its family extension (Zvvfmm), and a family
  alone enables no type. In Sail a family flag enables every type of its family. Each `sail.json` therefore
  sets the families Zvvmm and Zvvfmm to false and each type that the UDB configuration declares to true.
- The UDB configurations declare the 13 integer types Zvvi4i8mm to Zvvi64mm and the floating-point types that
  `testplans/Zvvfmm.csv` covers: Zvvfp16mm, Zvvfp32mm, Zvvfp64mm, Zvvfp16fp32mm, Zvvfp16fp64mm,
  Zvvfp32fp64mm, Zvvbf16fp32mm and Zvvbf16fp64mm.

## `qemu-ime-rv64`

`qemu-ime-rv64` is `config/qemu/qemu-rv64-max` adapted to the SDK QEMU:

- VLEN is 256 (`vlen=256`, UDB `VLEN: 256` and `Zvl256b`, `sail.json` `vlen_exp: 8`).
- QEMU 10.2.50 has no Q and no `smpmpmt` property. Q is removed from the UDB configuration, and
  `smpmpmt=false` is removed from the run command.
- `svade=true` is set because QEMU 10.2.50 does not enable Svade by default, and the UDB configuration
  and `sail.json` claim Svade and Svadu.
- The stateen `C` and `SE0` types and `HEDELEG_IAM_WRITABLE` follow the write masks in the QEMU source.
- QEMU does not decode `vmttl.v` and `vmtts.v`, so Zvvmttls is not declared, and `sail.json` disables it.
- QEMU adds each product to C with one fused multiply-add, rounded with `frm`. For W=1 this is G=1, psm=0,
  rnd=xct. For W>1 QEMU also adds product by product, which no disclosure describes, and the configuration
  repeats the W=1 profile.

## `sail-ime-rv64`

`sail-ime-rv64` is `config/sail/sail-rv64-max` with the IME. Sail is both the DUT and the reference model, so
this configuration shows that the tests build and run, and it runs the tests that `qemu-ime-rv64` skips:
Zvvmttls and the tests gated on rnd=frm.

- VLEN is 1024, as in `sail-rv64-max`. The lambda lists are `SUPPORTED_LAMBDA_SEW8: [4, 8]`,
  `SUPPORTED_LAMBDA_SEW16: [2, 4, 8]`, `SUPPORTED_LAMBDA_SEW32: [2, 4]` and `SUPPORTED_LAMBDA_SEW64: [1, 2, 4]`.
- The floating-point disclosure is Sail's: G=1, psm=0, rnd=frm.
- The stateen and `hedeleg` parameters follow `sail.json`.

## `sail-ime-rv64-v16384`

`sail-ime-rv64-v16384` is `sail-ime-rv64` with VLEN 16384. It covers the lambda values 16 and 32, which no VLEN
up to 1024 permits. It is a local test, not a CI configuration.

By default testgen sizes the IME tests for VLEN 1024 (`IME_VLEN_MAX` in `testgen/constants.py`), and a build for
this config stops with the `RVTEST_VLEN_MAX` error from `check_defines.h`. Generate the tests for this config with
`ACT_IME_VLEN_MAX=16384`, for example `ACT_IME_VLEN_MAX=16384 uv run testgen testplans -o tests --extensions ...`.
Regenerate without the variable before building for any other config.

- UDB `VLEN: 16384` with `Zvl2048b` to `Zvl16384b`, and `sail.json` `vlen_exp: 14`.
- The lambda lists are `SUPPORTED_LAMBDA_SEW8: [16, 32]`, `SUPPORTED_LAMBDA_SEW16: [8, 16, 32]`,
  `SUPPORTED_LAMBDA_SEW32: [8, 16]` and `SUPPORTED_LAMBDA_SEW64: [4, 8, 16]`. The `ZVVM_FP_*` disclosure has an entry
  for each of these lambda values.
- One Sail run of an IME test takes up to several minutes at this VLEN, so `test_config.yaml` sets
  `ref_model_timeout: 3600`. Run the DUT with a longer per-test timeout as well, for example
  `run_tests.py --timeout 3600`. Run it on a compute node.

## The IME in ACT

The IME extensions are experimental in ACT. An IME test requires its Zvvm extensions in
`REQUIRED_EXTENSIONS` and its lambda values as params, for example `SUPPORTED_LAMBDA_SEW32: 1`. ACT
selects IME tests only with `--enable-experimental-extensions` (Make: `ENABLE_EXPERIMENTAL_EXTENSIONS=True`).
ACT removes the IME extensions from `-march`, and the IME instructions assemble through the `.insn`
macros in `tests/env/rvtest_experimental.h`.

## Setup

The tools are wrappers in `config/ime/bin`. They need three settings:

```bash
export PATH=$PWD/config/ime/bin:$PATH
export SDK_SIF=/path/to/sdk-<date>.sif                      # OpenChip SDK image, run with apptainer
export SAIL_IME_SIM=/path/to/sail-riscv/build/c_emulator/sail_riscv_sim   # Sail IME fork, cleanup/ime-0.9.0
```

- `openchip-sdk-run` runs a command with `apptainer exec "$SDK_SIF"`. The run command uses it for QEMU.
- `riscv64-openchip-linux-gnu-{gcc,as,objdump,nm}` run the SDK tools in the image. ACT runs
  `gcc -print-prog-name=as` and then `as -march=help` on the host, so the `gcc` wrapper answers with the
  path of the host-side `as` wrapper.
- `sail_riscv_sim_ime` runs `$SAIL_IME_SIM` with `--enable-experimental-extensions`. The model enables
  the Zvvm\* extensions only with that flag.

apptainer must be able to bind the repository and the work directory into the image.

UDB locks files under `$XDG_DATA_HOME` (default `~/.local/share`) with `flock`. On an NFS home directory
`flock` fails with `EBADF`. Set `XDG_DATA_HOME` to a directory on a local disk before running ACT:

```bash
export XDG_DATA_HOME=/tmp/$USER-xdg-data
```

UDB 0.1.18 does not define IME. Point `UDB_LOCAL_PATH` at a checkout of riscv-unified-db branch `ime/fp-mx`.
The ACT Gemfile then takes the `udb`, `udb-gen`, `udb_helpers` and `idlc` gems from that checkout, and UDB
reads the architecture data in its `spec/std/isa`:

```bash
git clone -b ime/fp-mx https://github.com/Openchip-Software/riscv-unified-db.git
export UDB_LOCAL_PATH=$PWD/riscv-unified-db
```

UDB writes resolved data under `<checkout>/gen`. On NFS, make `gen` a symlink to a local disk. Bundler
rewrites `framework/src/act/data/Gemfile.lock` for the local gems; do not commit that change.

## Building and running

The IME configurations are not run in CI (`ci.yaml`). Generate the IME suites and run one configuration:

```bash
uv run testgen testplans -o tests --extensions Zvvmm32,Zvvfmm32,ExceptionsZvvm
uv run act config/ime/sail-ime-rv64/test_config.yaml --test-dir tests --workdir <work> \
  --extensions Zvvmm32,Zvvfmm32,ExceptionsZvvm --enable-experimental-extensions -k
./run_tests.py "$(cat config/ime/sail-ime-rv64/run_cmd.txt)" <work>/sail-ime-rv64/elfs/rv64i/Zvvmm32
```

The suites are per accumulator width: `Zvvmm8` to `Zvvmm64`, `Zvvfmm8` to `Zvvfmm64`, `Zvvmtls8` to
`Zvvmtls64`, `Zvvmttls8` to `Zvvmttls64`, and the privileged suite `ExceptionsZvvm`. Without
`--enable-experimental-extensions`, ACT skips the IME tests.

## Known issues

- QEMU adds each product of a W>1 floating-point multiply-accumulate to C on its own. The specification forms
  the partial sum of the W products first. The W>1 Zvvfmm files fail on `qemu-ime-rv64` at `cp_fp_subdot`.
- QEMU does not trap on several reserved IME cases, for example a multiply-accumulate with `vstart` != 0.
  ExceptionsZvvm fails on `qemu-ime-rv64`.
- The QEMU source maps A and B elements with the layout of the IME specification before commit 3c1b4457: each
  register holds lambda K elements of a row instead of lambda\*W. No test result shows this yet, because the W>1
  files stop at `cp_fp_subdot` first.
- The QEMU exclusions in `config/qemu/ci.yaml` also apply to this QEMU. For example, the
  `Svadu_sv*_Svadu_fault` tests fail.
