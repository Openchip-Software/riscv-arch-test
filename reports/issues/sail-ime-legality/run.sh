#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Build legal.elf with the SDK GCC and run it on the IME Sail fork.
# Usage: SAIL=/path/to/sail_riscv_sim SDK_SIF=/path/to/sdk.sif ./run.sh
set -euo pipefail
cd "$(dirname "$0")"
SDK_SIF=${SDK_SIF:-/srv/nfs/shared/home/constantino.gomez/repo/ime/sdk-2026.10.14.sif}
SAIL=${SAIL:-/srv/nfs/shared/home/constantino.gomez/repo/ime/sail-riscv/build-016/c_emulator/sail_riscv_sim}
sdk() { apptainer exec "$SDK_SIF" "$@"; }
CFLAGS=(-march=rv64gcv_zvvmm_zvvmtls_zvvmttls -mabi=lp64d -mcmodel=medany -O2 -nostdlib -nostartfiles
  -ffreestanding -T link.ld)

sdk riscv64-openchip-linux-gnu-gcc "${CFLAGS[@]}" start.S legal.c -o legal.elf
"$SAIL" --enable-experimental-extensions --config-override sail.json legal.elf >sail.out 2>&1 || true
cat sail.out
