#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Build repro.elf with the SDK GCC and run it on the IME Sail fork and on the SDK QEMU.
# Usage: SAIL=/path/to/sail_riscv_sim SDK_SIF=/path/to/sdk.sif [SAIL_FIXED=/path/to/patched/sail_riscv_sim] ./run.sh
set -euo pipefail
cd "$(dirname "$0")"
SDK_SIF=${SDK_SIF:-/srv/nfs/shared/home/constantino.gomez/repo/ime/sdk-2026.10.14.sif}
SAIL=${SAIL:-/srv/nfs/shared/home/constantino.gomez/repo/ime/sail-riscv/build-016/c_emulator/sail_riscv_sim}
sdk() { apptainer exec "$SDK_SIF" "$@"; }

sdk riscv64-openchip-linux-gnu-gcc -march=rv64gcv_zvvmm_zvvmtls -mabi=lp64d -mcmodel=medany \
  -O2 -nostdlib -nostartfiles -ffreestanding -T link.ld start.S repro.c -o repro.elf
sdk riscv64-openchip-linux-gnu-objdump -d repro.elf >repro.objdump

{
  "$SAIL" --build-info | sed -n 2p
  "$SAIL" --enable-experimental-extensions \
    --config-override sail-ime.json repro.elf
} >sail.out 2>&1
{
  sdk qemu-system-riscv64 --version | head -1
  sdk qemu-system-riscv64 -nographic -machine spike \
    -cpu max,vlen=256,x-zvvm=true -bios none -kernel repro.elf
} >qemu.out 2>&1
if [ -n "${SAIL_FIXED:-}" ]; then
  {
    echo "Sail RISC-V git: 0.16-8-gc69e3e22 + sail-fix.diff"
    "$SAIL_FIXED" --enable-experimental-extensions \
      --config-override sail-ime.json repro.elf
  } >sail-fixed.out 2>&1
fi
diff -u qemu.out sail.out || true
