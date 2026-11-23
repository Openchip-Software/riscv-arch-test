#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Install the Sail RISC-V model with the Integrated Matrix Extension (IME) and the UDB checkout that defines IME.
# Usage: install-sail-ime.sh <install-dir>
# Writes <install-dir>/bin/sail_riscv_sim and <install-dir>/riscv-unified-db, the checkout for UDB_LOCAL_PATH.
# Update SAIL_IME_COMMIT or UDB_IME_COMMIT to rebuild (cache key is derived from this script's hash).
# Interim: replace with release downloads once Sail and the udb gem release IME support.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-sail-ime.sh <install-dir>}"
# Openchip-Software/sail-riscv, branch cleanup/ime-0.9.0
SAIL_IME_COMMIT="0ebfc810f523fd225d02edbb78d375737141e825"
# Openchip-Software/riscv-unified-db, branch ime/fp-mx
UDB_IME_COMMIT="f0045fec2ee773e3753375d238c1dad66f593c91"

# Shallow checkout of one commit
fetch_commit() {
  local url="$1" commit="$2" dir="$3"
  git init --quiet "$dir"
  git -C "$dir" fetch --quiet --depth 1 "$url" "$commit"
  git -C "$dir" checkout --quiet FETCH_HEAD
}

mkdir -p "$INSTALL_DIR"
INSTALL_DIR="$(cd "$INSTALL_DIR" && pwd)"
BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT

fetch_commit https://github.com/Openchip-Software/sail-riscv.git "$SAIL_IME_COMMIT" "$BUILD_DIR/sail-riscv"

# The Sail compiler version that this model commit requires
SAIL_VERSION="$(cat "$BUILD_DIR/sail-riscv/cmake/sail_required_version.txt")"
mkdir -p "$BUILD_DIR/sail"
curl --fail --location --retry 5 --retry-all-errors --retry-delay 5 \
  "https://github.com/rems-project/sail/releases/download/${SAIL_VERSION}-binary/sail-$(uname)-$(arch).tar.gz" |
  tar xz --directory="$BUILD_DIR/sail" --strip-components=1
# The Sail compiler runs the z3 binary that its release bundles
export PATH="$BUILD_DIR/sail/bin:$PATH"

cmake -S "$BUILD_DIR/sail-riscv" -B "$BUILD_DIR/build" -DCMAKE_BUILD_TYPE=Release \
  -DDOWNLOAD_GMP=FALSE -DENABLE_RISCV_TESTS=FALSE -DFIRST_PARTY_TESTS=FALSE
cmake --build "$BUILD_DIR/build" --parallel "$(nproc)" --target sail_riscv_sim
cmake --install "$BUILD_DIR/build" --prefix "$INSTALL_DIR"

rm -rf "$INSTALL_DIR/riscv-unified-db"
fetch_commit https://github.com/Openchip-Software/riscv-unified-db.git "$UDB_IME_COMMIT" "$INSTALL_DIR/riscv-unified-db"
