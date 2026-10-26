#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compare the Sail signature (.sig) of each converted test with the ime-test-gen golden values."""

import json
import sys
from pathlib import Path

tests, build = Path(sys.argv[1]), Path(sys.argv[2])
total = bad = 0
for golden_file in sorted(tests.rglob("*.golden.json")):
    rel = golden_file.relative_to(tests).with_suffix("")
    sig = [int(x, 16) for x in (build / rel).with_suffix(".sig").read_text().split()]
    golden = json.loads(golden_file.read_text())
    words = sig[1 : 1 + len(golden)]  # word 0 is the canary
    mism = [(g, w) for g, w in zip(golden, words) if (g["value"] & (2**64 - 1)) != w]
    total += len(golden)
    bad += len(mism)
    print(f"{rel.name}: {len(golden)} checks, {len(mism)} mismatches")
    for g, w in mism[:3]:
        print(f"  {g['label']}[{g['index']}]: golden=0x{g['value'] & (2**64 - 1):016x} sail=0x{w:016x}")
print(f"TOTAL: {total} checks, {bad} mismatches between Sail and the Rust golden model")
