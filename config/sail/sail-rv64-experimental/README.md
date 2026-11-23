# sail-rv64-experimental

`sail-rv64-experimental` is `config/sail/sail-rv64-max` with the Integrated Matrix Extension (IME). It runs the IME
suites in the `sail-rv64-experimental` job of `.github/workflows/regress.yml`. Sail is both the reference model and
the DUT, so the job shows that the IME tests build, select, and pass their self-checks.

## Interim reference model

The official Sail release does not implement IME. Until it does, this configuration needs:

- The Sail IME fork, Openchip-Software/sail-riscv branch `cleanup/ime-0.9.0`. CI builds it from the commit pinned in
  `.github/scripts/install-sail-ime.sh`.
- The IME definitions from Openchip-Software/riscv-unified-db branch `ime/fp-mx`. The released `udb` gem does not
  define IME, so CI checks out the commit pinned in the same script and sets `UDB_LOCAL_PATH` to it.

Both follow the IME specification at commit `58810918`. When a Sail release and a `udb` gem release define IME, the
job uses those releases, and the pinned commits go.

`config/sail/ci.yaml` excludes this configuration from the matrix. The matrix uses the official Sail release, which
has no IME, and the released `udb` gem, which cannot validate the IME extensions in `sail-rv64-experimental.yaml`.

## Configuration

- VLEN is 1024, as in `sail-rv64-max`. The IME tests are generated for VLEN up to 1024 by default.
- The lambda lists are the values that the specification permits for VLEN 1024, where VLEN/(SEW\*lambda^2) is 1, 2,
  4, 8 or 16: `SUPPORTED_LAMBDA_SEW8: [4, 8]`, `SUPPORTED_LAMBDA_SEW16: [2, 4, 8]`, `SUPPORTED_LAMBDA_SEW32: [2, 4]`
  and `SUPPORTED_LAMBDA_SEW64: [1, 2, 4]`.
- The `ZVVM_FP_*` parameters disclose the floating-point profile of Sail: G=1, psm=0, rnd=frm.
- In Sail a family flag (`Zvvmm`, `Zvvfmm`) enables every type of its family. `sail.json` sets the families to false
  and each type that the UDB configuration declares to true. `Zvvmttls` is enabled.
- The OFP8-accumulator types are not declared. The pinned Sail raises an illegal-instruction exception for them.
- Sail enables IME only with `--enable-experimental-extensions`. ACT passes it to the reference model when
  `ENABLE_EXPERIMENTAL_EXTENSIONS=True`, and `run_cmd.txt` passes it to the DUT.

## Running locally

```bash
.github/scripts/install-sail-ime.sh <install-dir>
export PATH=<install-dir>/bin:$PATH UDB_LOCAL_PATH=<install-dir>/riscv-unified-db
ENABLE_EXPERIMENTAL_EXTENSIONS=True EXTENSIONS=Zvvmm32,Zvvfmm32,ExceptionsZvvm \
  CONFIG_FILES=config/sail/sail-rv64-experimental/test_config.yaml make elfs
./run_tests.py "$(cat config/sail/sail-rv64-experimental/run_cmd.txt)" work/sail-rv64-experimental/elfs
```

The IME suites are per accumulator width: `Zvvmm8` to `Zvvmm64`, `Zvvfmm8` to `Zvvfmm64`, `Zvvmtls8` to
`Zvvmtls64`, `Zvvmttls8` to `Zvvmttls64`, and `ExceptionsZvvm`. `EXTENSIONS=Zvvmm` selects nothing.

With `UDB_LOCAL_PATH` set, Bundler rewrites `framework/src/act/data/Gemfile.lock`. Do not commit that change.
