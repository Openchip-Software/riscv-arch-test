#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Derive a sail.json for the IME Sail fork from an ACT sail.json.

ACT pins one Sail release and its configuration schema. The fork may require
keys that the ACT file lacks. This script copies every missing key from the
fork's own default configuration (`--print-default-config`), keeps every key
the ACT file sets, then sets the IME extensions and VLEN.

Usage: make_sail_json.py <sail_riscv_sim> <act sail.json> <out sail.json> [vlen_exp] [--no-ime]
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def load_jsonc(text: str) -> dict:
    return json.loads(re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE))


def fill_missing(dst: dict, defaults: dict, path: str, added: list[str]) -> None:
    for key, value in defaults.items():
        if key not in dst:
            dst[key] = value
            added.append(f"{path}/{key}")
        elif isinstance(value, dict) and isinstance(dst[key], dict):
            fill_missing(dst[key], value, f"{path}/{key}", added)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sim, src, dst = args[:3]
    vlen_exp = int(args[3]) if len(args) > 3 else None
    ime = "--no-ime" not in sys.argv

    defaults = load_jsonc(
        subprocess.run([sim, "--print-default-config"], capture_output=True, text=True, check=True).stdout
    )
    config = load_jsonc(Path(src).read_text())
    added: list[str] = []
    fill_missing(config, defaults, "", added)
    for ext in ("Zvvmm", "Zvvmtls", "Zvvmttls"):
        config["extensions"][ext]["supported"] = ime
    if vlen_exp is not None:
        config["extensions"]["V"]["vlen_exp"] = vlen_exp
    Path(dst).write_text(json.dumps(config, indent=2))
    for key in added:
        print(f"added from fork defaults: {key}", file=sys.stderr)


if __name__ == "__main__":
    main()
