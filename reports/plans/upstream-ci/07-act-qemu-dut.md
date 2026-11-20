<!-- SPDX-License-Identifier: Apache-2.0 -->

# 07: ACT: IME QEMU as an independent DUT in CI

Repository: `riscv/riscv-arch-test`, target branch `act4`. Separate pull request, after package 06 merges.
Reference config: `config/ime/qemu-ime-rv64` on `Openchip-Software/riscv-arch-test`, branch `cgomez/ime-udb-0.9.0`
(local clone `~/repo/ime/riscv-arch-test`). That config uses the OpenChip SDK image; this package builds QEMU from
source instead.

State as of 2026-11-20. Blocked on package 04 (a pinned QEMU commit and the deviation issues).

## Why

The Sail job in package 06 runs Sail against itself. It shows that the tests build and run, but it cannot find a
model bug. A second implementation, checked against Sail's expected results, does. Keep this a separate pull request:
upstream maintainers may not want a vendor QEMU fork in their CI, and rejecting it must not block the tests.

## Tasks

1. Add `.github/scripts/install-qemu-ime.sh`, modelled on `.github/scripts/install-qemu.sh`. Clone
   `https://github.com/Openchip-Software/riscv-ime-qemu`, check out a pinned `QEMU_IME_COMMIT`, then run
   `./configure --prefix="$INSTALL_DIR" --target-list=riscv32-softmmu,riscv64-softmmu`, `make -j"$(nproc)"` and
   `make install`. Add the SPDX header and the usage comment.
2. Add a Renovate `customManagers` entry in `renovate.json` for `QEMU_IME_COMMIT`, modelled on the Spike entry
   (`github-digest`, `currentValueTemplate: master`).
3. Add `config/qemu-ime/`. It cannot share `config/qemu/ci.yaml`, because `install_script` is set once per simulator
   directory.
   - `ci.yaml`: `install_script: .github/scripts/install-qemu-ime.sh`, the `apt_packages` QEMU needs, and
     `exclude_extensions` for each open deviation from package 04, with the issue link on the line above. Follow the
     comment style of `config/qemu/ci.yaml`.
   - `qemu-ime-rv64/`: based on `config/ime/qemu-ime-rv64` with `riscv64-unknown-elf-gcc`, `sail_riscv_sim`, and the
     run command
     `qemu-system-riscv64 {debug:-d in_asm,int,mmu,unimp,cpu,fpu,vpu,exec,nochain -D __TRACEFILE__} -nographic -semihosting -icount shift=1 -machine virt,aia=aplic-imsic,aia-guests=7 -cpu max,vlen=256,x-zvvm=true,svade=true,pmu-mask=0xfffffff8,smdbltrp=true,ssdbltrp=true -bios`.
   - Do not declare Zvvmttls while QEMU cannot decode `vmttl.v` and `vmtts.v`.
4. The matrix job does not pass the experimental flag. Add a dedicated job `qemu-ime-rv64` in `regress.yml`, modelled
   on `spike-rv64-experimental`. Restrict `EXTENSIONS` to the IME suites, so the QEMU 10.2 deviations outside IME do
   not matter. Either set `ci_enabled: false` in `config/qemu-ime/ci.yaml` or list the config in `exclude_configs`, so
   the matrix does not also run it.
5. Expected exclusions, unless package 04 fixes them first: `cp_fp_subdot` cases (QEMU rounds each product),
   `ExceptionsZvvm` cases for vstart, VL multiple, vill, L64 and masked-v0, `Zvvbf16mm` (`vtype[8]` needs
   `x-zvfbfa`), and Zvvmttls.
6. The QEMU config discloses rnd=xct, so the `cp_fp_rnd` testcases (gated on rnd=frm) do not run on it.

## Acceptance

- The job builds QEMU from source, caches it by script hash, and passes with the listed exclusions.
- Every exclusion has a public issue link.
