<!-- SPDX-License-Identifier: Apache-2.0 -->

# 09: ACT: checks to run before the IME pull request

Repository: `Openchip-Software/riscv-arch-test`, branch `port-ime-tests-to-act4` (local clone
`~/repo/ime/riscv-arch-test`). These are checks only; report the results to package 06.

State as of 2026-11-09.

## Environment

```bash
cd ~/repo/ime/riscv-arch-test
source ~/tools/act4/env.sh   # mise, uv, prek; sets XDG_DATA_HOME on local disk (UDB flock fails on NFS)
export PATH=$PWD/config/ime/bin:$PATH
export SDK_SIF=~/repo/ime/sdk-2026.10.14.sif
export SAIL_IME_SIM=~/repo/ime/sail-riscv/build-016/c_emulator/sail_riscv_sim
```

The upstream GCC is at `~/tools/act4/gcc/riscv/bin/riscv64-unknown-elf-gcc` (16.1). With it, all IME suites build and
20 sample files pass with Sail as DUT. IME tests need `--enable-experimental-extensions` (`act`) or
`ENABLE_EXPERIMENTAL_EXTENSIONS=True` (Make). Use per-SEW suite names, for example `Zvvmm32`.

## Checks

1. **CTP documentation build.** The `ctp-build` job runs on every pull request and reads `testplans/**`. Build it
   locally from `docs/ctp` (`make docker-pull-latest && make`; see `AGENTS.md` for `SKIP_DOCKER`). Confirm that the
   IME testplans and extensions do not break it, and look at how they appear in the output.
2. **Clang.** Upstream CI also runs `sail-rv64-max-clang` with LLVM 23. Build the IME suites with a Clang config and
   check that the `.insn` macros in `tests/env/rvtest_experimental.h` assemble. Compare the instruction words with the
   GCC build.
3. **RV32.** Check whether the Sail fork supports IME on RV32. `ExceptionsZvvm` already handles both XLENs. If RV32
   works, propose an RV32 config for package 06.
4. **Other VLENs.** The λ gating depends on VLEN. Run the IME suites with Sail as DUT at VLEN 128 and 512 by changing
   the UDB config (`VLEN`, `Zvl*b`, λ lists) and `sail.json` (`vlen_exp`). Report whether a second CI config is worth
   adding.
5. **Sail config schema.** With the new fork release, check whether `sail_riscv_sim` rejects the current
   `config/ime/qemu-ime-rv64/sail.json`, and list the keys it needs (see package 06, task A.1).

## Acceptance

- One line per check: passed, failed with the reason, or not possible with the reason.
