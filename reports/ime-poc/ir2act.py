#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Proof of concept: convert ime-test-gen IR (--emit-ir JSON) into ACT4 test files.

Mapping:
  IR section            -> one ACT test file  tests/rv64i/<suite>/<suite>-<section-id>-00.S
  IR test               -> one testcase (label <suite>_<instr>_cg_<family>_<config>)
  IR vlen_guard         -> test header param  VLEN: <n>
  ConfigureVtype        -> LI + vsetvl with a statically tracked vtype (lambda, altfmt, sew, lmul)
  AltfmtSetup/Clear     -> vsetvl x0, x0 with updated altfmt bits
  TileLoadOp/StoreOp    -> vmtl.v / vmttl.v / vmts.v / vmtts.v on fixed registers A=v0 B=v8 C=v16
  TileZero              -> vmv.v.i
  Mmacc                 -> v[w|q|8w]mmacc.vv (integer only in this proof of concept)
  Compare               -> one scalar load + RVTEST_SIGUPD per element
  DeclareArray(ref)     -> not emitted; written to <file>.golden.json for a cross-check against Sail

Expected values in the ACT build come from the reference model, not from C_ref.
Tests that use any other IR action are skipped and listed on stderr.
"""

import argparse
import json
import re
import sys
from pathlib import Path

TILE_REG = {"A": "v0", "B": "v8", "C": "v16", "CLo": "v16", "CHi": "v24"}
LAMBDA_ENC = {1: 1, 2: 2, 4: 3, 8: 4, 16: 5, 32: 6, 64: 7}
LOG2 = {1: 0, 2: 1, 4: 2, 8: 3}
INT_MMACC = {1: "vmmacc.vv", 2: "vwmmacc.vv", 4: "vqwmmacc.vv", 8: "v8wmmacc.vv"}
LOAD = {
    (1, True): "lb",
    (1, False): "lbu",
    (2, True): "lh",
    (2, False): "lhu",
    (4, True): "lw",
    (4, False): "lwu",
    (8, True): "ld",
    (8, False): "ld",
}
DIRECTIVE = {1: ".byte", 2: ".half", 4: ".word", 8: ".dword"}
SUPPORTED = {
    "LambdaProbe",
    "DeclareArray",
    "DeclareOutput",
    "ConfigureVtype",
    "AltfmtSetup",
    "AltfmtClear",
    "TileLoadOp",
    "TileStoreOp",
    "TileZero",
    "Mmacc",
    "Compare",
    "Dump",
}
SIG_MARGIN = 10


class Unsupported(Exception):
    pass


def sanitize(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


class Vtype:
    """Static model of vtype: the generated code is straight-line, so every vtype value is known."""

    def __init__(self) -> None:
        self.lam = 1
        self.alt_a = self.alt_b = self.alt = 0
        self.sew = 1
        self.lmul = 1

    def raw(self) -> int:
        v = LOG2[self.lmul] | (LOG2[self.sew] << 3)
        v |= self.alt << 8
        v |= self.alt_b << 57
        v |= self.alt_a << 58
        v |= LAMBDA_ENC[self.lam] << 60
        return v


def int_bits(fmt: dict) -> tuple[int, bool]:
    if "Int" not in fmt:
        raise Unsupported(f"non-integer format {fmt}")
    return fmt["Int"]["bits"], fmt["Int"]["signed"]


def convert_test(test: dict, suite: str, instr_hint: list[str]) -> tuple[list[str], list[str], list[str], list[dict]]:
    """Return (code, data, strings, golden) for one IR test."""
    arrays: dict[str, dict] = {}
    outputs: dict[str, dict] = {}
    code: list[str] = []
    golden: list[dict] = []
    vt = Vtype()
    tid = test["id"]
    family = sanitize(tid.split(".")[0])
    config = sanitize(".".join(tid.split(".")[1:]))
    instr = None

    for action in test["actions"]:
        # serde writes unit variants (e.g. AltfmtClear) as a bare string.
        ((kind, a),) = action.items() if isinstance(action, dict) else ((action, {}),)
        if kind not in SUPPORTED:
            raise Unsupported(kind)
        if kind == "DeclareArray":
            arrays[a["name"]] = a
        elif kind == "DeclareOutput":
            outputs[a["name"]] = a
        elif kind == "ConfigureVtype":
            vt.sew, vt.lam, vt.lmul = a["esz"], a["lambda"], a["lmul"]
            code += [
                f"  LI(x6, {a['vl']})",
                f"  LI(x7, 0x{vt.raw():016x})  # {a['label']}: e{8 * vt.sew} m{vt.lmul} lambda={vt.lam}",
                "  vsetvl x9, x6, x7",
            ]
        elif kind in ("AltfmtSetup", "AltfmtClear"):
            vt.alt_a, vt.alt_b, vt.alt = (a["a"], a["b"], a["acc"]) if kind == "AltfmtSetup" else (0, 0, 0)
            code += [
                f"  LI(x7, 0x{vt.raw():016x})  # altfmt A={vt.alt_a} B={vt.alt_b} acc={vt.alt}",
                "  vsetvl x0, x0, x7",
            ]
        elif kind in ("TileLoadOp", "TileStoreOp"):
            if a["masked"] or a["as_storage"] or a["imm_lambda"]:
                raise Unsupported(f"{kind} with mask, as_storage or immediate lambda")
            mnem = {"Vmtl": "vmtl.v", "Vmttl": "vmttl.v", "Vmts": "vmts.v", "Vmtts": "vmtts.v"}[a["op"]]
            reg = TILE_REG[a["dst"] if kind == "TileLoadOp" else a["src"]]
            mem = a["src"] if kind == "TileLoadOp" else a["dst"]
            code += [f"  LA(x8, {sanitize(tid)}_{mem})", f"  LI(x9, {a['ld']})", f"  {mnem} {reg}, (x8), x9"]
        elif kind == "TileZero":
            code.append(f"  vmv.v.i {TILE_REG[a['dst']]}, 0")
        elif kind == "Mmacc":
            if a["kind"] != "Int":
                raise Unsupported("FP mmacc")
            abits, _ = int_bits(a["a_fmt"])
            cbits, _ = int_bits(a["c_fmt"])
            instr = INT_MMACC[cbits // abits]
            code += [
                f"{suite}_{sanitize(instr)}_cg_{family}_{config}:",
                f"  {instr} {TILE_REG[a['c']]}, {TILE_REG[a['a']]}, {TILE_REG[a['b']]}",
            ]
        elif kind == "Compare":
            if a["compare_mode"] != "Exact":
                raise Unsupported(f"compare mode {a['compare_mode']}")
            out, ref = outputs[a["output"]], arrays[a["reference"]]
            esz = ref["sew_bits"] // 8
            load = LOAD[(esz, ref["signed"])]
            label = f"{suite}_{sanitize(instr or 'vmmacc.vv')}_cg_{family}_{config}"
            code.append(f"  LA(x8, {sanitize(tid)}_{out['name']})")
            for i in range(a["size"]):
                code += [
                    f"  {load} x10, 0(x8)",
                    f"  RVTEST_SIGUPD(x2, x5, x4, x10, {label}, {label}_str)",
                    f"  addi x8, x8, {esz}",
                ]
                v = ref["data"][i]
                golden.append({"label": label, "index": i, "value": v & ((1 << 64) - 1) if v < 0 else v})
        # LambdaProbe and Dump have no ACT equivalent: lambda support is a DUT property, dumps are debug output.

    if instr is None:
        raise Unsupported("no Mmacc action")
    instr_hint.append(instr)
    label = f"{suite}_{sanitize(instr)}_cg_{family}_{config}"
    data = [f"# {tid}"]
    for name, arr in arrays.items():
        if name == "C_ref":
            continue
        esz = arr["sew_bits"] // 8
        vals = [v & ((1 << (8 * esz)) - 1) for v in arr["data"]]
        data += [".balign 8", f"{sanitize(tid)}_{name}:"]
        for k in range(0, len(vals), 8):
            data.append(f"  {DIRECTIVE[esz]} " + ", ".join(f"0x{v:x}" for v in vals[k : k + 8]))
    for name, out in outputs.items():
        esz = {
            "int8_t": 1,
            "uint8_t": 1,
            "int16_t": 2,
            "uint16_t": 2,
            "int32_t": 4,
            "uint32_t": 4,
            "int64_t": 8,
            "uint64_t": 8,
        }[out["ctype"]]
        fill = out["fill"].get("Sentinel", 0) if isinstance(out["fill"], dict) else 0
        data += [".balign 8", f"{sanitize(tid)}_{name}:", f"  .fill {out['size'] * esz}, 1, 0x{fill:x}"]
    strings = [
        f'{label}_str: .string "\\"test: {tid}; cg: {suite}_{sanitize(instr)}_cg; cp: {family}; bin: {config}\\""'
    ]
    header = [f"# Testcase {tid}: {test['desc']}"]
    return header + code, data, strings, golden


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ir", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True, help="ACT test directory (contains env/)")
    ap.add_argument("--suite", default="Zvvmm")
    ap.add_argument("--march", default="rv64iv_zicsr_zifencei_zvmma")
    args = ap.parse_args()

    ir = json.loads(args.ir.read_text())
    suite_dir = args.out / "rv64i" / args.suite
    suite_dir.mkdir(parents=True, exist_ok=True)
    skipped: dict[str, int] = {}
    total = 0
    for section in ir["sections"]:
        by_vlen: dict[int, list] = {}
        for t in section["tests"]:
            by_vlen.setdefault(t["vlen_guard"], []).append(t)
        for vlen, tests in sorted(by_vlen.items()):
            code, data, strings, golden, instrs = [], [], [], [], []
            for t in tests:
                try:
                    c, d, s, g = convert_test(t, args.suite, instrs)
                except Unsupported as e:
                    skipped[str(e)] = skipped.get(str(e), 0) + 1
                    continue
                code += c + [""]
                data += d
                strings += s
                golden += g
            if not golden:
                continue
            total += len(strings)
            section_id = sanitize(section["title"].split(":")[0]).replace("_", "-")
            name = f"{args.suite}-{section_id}-V{vlen}-00.S"
            header = [
                f"// Generated by ir2act.py from ime-test-gen IR: {section['title']}",
                "// SPDX-License-Identifier: Apache-2.0",
                "",
                "##### START_TEST_CONFIG #####",
                "# REQUIRED_EXTENSIONS: ['V']",
                "# params:",
                "#   MXLEN: 64",
                f"#   VLEN: {vlen}",
                f"# MARCH: {args.march}",
                "##### END_TEST_CONFIG #####",
                "",
                f"#define SIGUPD_COUNT {len(golden) + SIG_MARGIN}",
                '#include "riscv_arch_test.h"',
                "",
                "RVTEST_BEGIN",
                "",
            ]
            footer = [
                "RVTEST_CODE_END",
                "",
                "RVTEST_DATA_BEGIN",
                *data,
                "",
                *strings,
                "",
                "RVTEST_DATA_END",
                "",
                "RVTEST_SIG_SETUP",
                "",
            ]
            (suite_dir / name).write_text("\n".join(header + code + footer))
            (suite_dir / name).with_suffix(".golden.json").write_text(json.dumps(golden))
            print(f"{name}: {len(strings)} testcases, {len(golden)} checks")
    print(f"total testcases: {total}", file=sys.stderr)
    for reason, n in sorted(skipped.items()):
        print(f"skipped {n}: {reason}", file=sys.stderr)


if __name__ == "__main__":
    main()
