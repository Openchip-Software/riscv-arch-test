#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Build fprnd.elf with the SDK GCC and run it on the IME Sail fork and on the SDK QEMU.
# fprnd-mixed.elf adds a mixed-format W=1 case. It runs on QEMU only: the Sail fork rejects
# altfmt_A or altfmt_B != 0 for W=1.
# Usage: SAIL=/path/to/sail_riscv_sim SDK_SIF=/path/to/sdk.sif ./run.sh
set -euo pipefail
cd "$(dirname "$0")"
SDK_SIF=${SDK_SIF:-/srv/nfs/shared/home/constantino.gomez/repo/ime/sdk-2026.10.14.sif}
SAIL=${SAIL:-/srv/nfs/shared/home/constantino.gomez/repo/ime/sail-riscv/build-016/c_emulator/sail_riscv_sim}
sdk() { apptainer exec "$SDK_SIF" "$@"; }
CFLAGS=(-march=rv64gcv_zvvmm_zvvfmm -mabi=lp64d -mcmodel=medany -O2 -nostdlib -nostartfiles -ffreestanding -T link.ld)
QEMU=(qemu-system-riscv64 -nographic -machine spike -cpu "max,vlen=256,x-zvvm=true" -bios none -kernel)

sdk riscv64-openchip-linux-gnu-gcc "${CFLAGS[@]}" start.S fprnd.c -o fprnd.elf
sdk riscv64-openchip-linux-gnu-gcc "${CFLAGS[@]}" -DMIXED start.S fprnd.c -o fprnd-mixed.elf

{
  "$SAIL" --build-info | sed -n 2p
  "$SAIL" --enable-experimental-extensions \
    --config-override sail.json fprnd.elf
} >sail.out 2>&1 || true
{
  sdk qemu-system-riscv64 --version | head -1
  timeout 60 apptainer exec "$SDK_SIF" "${QEMU[@]}" fprnd.elf
} \
  >qemu.out 2>&1 || true
{
  sdk qemu-system-riscv64 --version | head -1
  timeout 60 apptainer exec "$SDK_SIF" "${QEMU[@]}" fprnd-mixed.elf
} \
  >qemu-mixed.out 2>&1 || true
diff -u qemu.out sail.out || true
