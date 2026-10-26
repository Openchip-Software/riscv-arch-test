#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check that every {{src:path:a-b}} citation names an existing file and in-range lines."""

import re
import sys
from pathlib import Path

roots = {"src": Path(sys.argv[2]), "src2": Path(sys.argv[3]) if len(sys.argv) > 3 else None}
text = Path(sys.argv[1]).read_text()
bad = 0
for kind, path, lines in re.findall(r"\{\{(src2?):([^:}]+)(?::([\d-]+))?\}\}", text):
    root = roots[kind]
    f = root / path
    if not f.is_file():
        print(f"missing file: {kind}:{path}")
        bad += 1
        continue
    if lines:
        n = len(f.read_text(errors="replace").splitlines())
        last = int(lines.split("-")[-1])
        if last > n:
            print(f"out of range: {kind}:{path}:{lines} (file has {n} lines)")
            bad += 1
print(f"{bad} problem(s)")
sys.exit(1 if bad else 0)
