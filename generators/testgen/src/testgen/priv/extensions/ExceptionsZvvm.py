##################################
# priv/extensions/ExceptionsZvvm.py
#
# Illegal-instruction and vstart tests for the Integrated Matrix Extension (IME)
# constantino.gomez@openchip.com October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""
ExceptionsZvvm: the IME cases that raise an illegal-instruction exception, and vstart on tile loads and stores.

Each trap case sets up a legal IME vtype and then breaks one rule of the instruction. The trap handler records the
trap; the instruction never runs, so it needs no data. Each case is guarded by the type extension of its row
(<EXT>_SUPPORTED), by ELEN, and by the lambda values the DUT supports.
"""

from collections.abc import Callable
from pathlib import Path

from testgen.asm.helpers import write_sigupd
from testgen.asm.vector_helpers import ime_lambda_condition, ime_lambdas, load_ime_vtype
from testgen.data.params import InstructionParams
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters.registry import format_instruction
from testgen.formatters.types.tile_type import TRANSPOSING, tile_data_label
from testgen.instructions.vector_params import generate_random_vector_params
from testgen.io.testplans import TestPlanData, read_testplan
from testgen.priv.registry import add_priv_test_generator

TESTPLAN = Path("./testplans/priv/ExceptionsZvvm.csv")
SEWS = [8, 16, 32, 64]

# Type extension that provides each multiply-accumulate at each accumulator SEW (integer and FP encoding maps).
# The FP entries are the FP16, FP32 and FP64 rows.
MACC_TYPE_EXTENSION = {
    ("vmmacc.vv", 8): "ZVVI8MM",
    ("vmmacc.vv", 16): "ZVVI16MM",
    ("vmmacc.vv", 32): "ZVVI32MM",
    ("vmmacc.vv", 64): "ZVVI64MM",
    ("vwmmacc.vv", 8): "ZVVI4I8MM",
    ("vwmmacc.vv", 16): "ZVVI8I16MM",
    ("vwmmacc.vv", 32): "ZVVI16I32MM",
    ("vwmmacc.vv", 64): "ZVVI32I64MM",
    ("vqmmacc.vv", 16): "ZVVI4I16MM",
    ("vqmmacc.vv", 32): "ZVVI8I32MM",
    ("vqmmacc.vv", 64): "ZVVI16I64MM",
    ("v8wmmacc.vv", 32): "ZVVI4I32MM",
    ("v8wmmacc.vv", 64): "ZVVI8I64MM",
    ("vfmmacc.vv", 16): "ZVVFP16MM",
    ("vfmmacc.vv", 32): "ZVVFP32MM",
    ("vfmmacc.vv", 64): "ZVVFP64MM",
    ("vfwmmacc.vv", 32): "ZVVFP16FP32MM",
    ("vfwmmacc.vv", 64): "ZVVFP32FP64MM",
    ("vfqmmacc.vv", 64): "ZVVFP16FP64MM",
}

# funct6 and funct3 of the multiply-accumulates without a microscaled form, for the vm=0 encoding
MACC_VM0_ENCODING = {"vmmacc.vv": (0x38, 0), "vfmmacc.vv": (0x14, 1)}

# Register groups of the trap cases: A and B at LMUL <= 8, C at v16
A_REG, B_REG, C_REG, TILE_REG = 0, 8, 16, 8


def arch_lines(sew: int, fp: bool) -> tuple[list[str], list[str]]:
    """Enable the assembler's Zve64 at SEW=64, as ExceptionsV does."""
    if sew < 64:
        return [], []
    return [".option push", f".option arch, +{'zve64d' if fp else 'zve64x'}"], [".option pop"]


class TrapCase:
    """Builds one test chunk per (instruction, SEW) for a trap case."""

    def __init__(self, test_data: TestData, row: TestPlanData, coverpoint: str) -> None:
        self.test_data = test_data
        self.row = row
        self.coverpoint = coverpoint
        self.fp = row.instr_type == "FMMACC"
        self.is_tile = row.instr_type in ("VLT", "VST")

    def guard(self, sew: int, extra: list[str]) -> str:
        """Preprocessor guard: type extension, ELEN and any extra condition."""
        terms = [f"(UDB_ELEN >= {sew})", *extra]
        if not self.is_tile and (self.row.instr_name, sew) in MACC_TYPE_EXTENSION:
            terms.insert(0, f"defined({MACC_TYPE_EXTENSION[(self.row.instr_name, sew)]}_SUPPORTED)")
        return "#if " + " && ".join(terms)

    def instruction(self, vd: int | None = None, vs1: int = A_REG, vs2: int = B_REG, addr_reg: int = 0) -> str:
        """The instruction under test, with the given register groups."""
        if self.is_tile:
            reg = TILE_REG if vd is None else vd
            return f"{self.row.instr_name} v{reg}, (x{addr_reg}), x0"
        return f"{self.row.instr_name} v{C_REG if vd is None else vd}, v{vs1}, v{vs2}"

    def chunk(
        self,
        sew: int,
        bin_name: str,
        desc: str,
        lmul: int,
        body: Callable[[int, int, int], list[str]],
        *,
        extra_guard: list[str] | None = None,
        lambda_value: int | None = None,
        record_vstart: bool = False,
    ) -> TestChunk:
        """
        One trapping testcase: set a legal IME vtype at VL=VLMAX, then body(temp_reg, vtype_reg, addr_reg) breaks a
        rule and runs the instruction (its last line). A tile instruction gets a valid address in addr_reg in case it
        does not trap. record_vstart records vstart after the trap and clears it.
        """
        test_data = self.test_data
        tc = test_data.begin_test_chunk()
        tc.code.append(f"# Testcase {self.coverpoint} ({desc}, SEW = {sew})")
        label_line = test_data.add_testcase(
            f"{bin_name}_sew_{sew}", self.coverpoint, f"{test_data.config.testsuite}_{self.row.instr_name}_cg"
        )
        temp_reg, vtype_reg, addr_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])
        params = InstructionParams(sew=sew, lmul=lmul, lambda_=lambda_value, vl="vlmax", temp_reg=temp_reg)
        lambdas = ime_lambdas(sew) if lambda_value is None else [lambda_value]
        pre, post = arch_lines(sew, self.fp)
        lines = [
            self.guard(sew, [ime_lambda_condition(sew, lambdas), *(extra_guard or [])]),
            *pre,
            *load_ime_vtype(params, test_data, lambdas=lambdas),
        ]
        if self.is_tile:
            label = tile_data_label(test_data, sew)
            tc.vector_labels.append((label, *test_data.vector_labels[label]))
            lines.append(f"LA (x{addr_reg}, {label})")
        body_lines = body(temp_reg, vtype_reg, addr_reg)
        lines.extend([*body_lines[:-1], label_line, body_lines[-1]])
        if record_vstart:
            lines.extend([write_sigupd(None, test_data, "vstart"), "csrw vstart, x0"])
        lines.extend([*post, "#endif"])
        test_data.int_regs.return_registers([temp_reg, vtype_reg, addr_reg])
        # The instruction traps, so the testcase writes no signature of its own
        tc.code.append("\n".join(lines))
        return test_data.end_test_chunk()


def vtype_keep(temp_reg: int, vtype_reg: int, avl: str, change: list[str] | None = None) -> list[str]:
    """Rewrite vtype from its current value, optionally changed, with AVL from avl (a register or x0)."""
    return [f"csrr x{vtype_reg}, vtype", *(change or []), f"vsetvl x{temp_reg}, {avl}, x{vtype_reg}"]


def trap_cases(test_data: TestData, row: TestPlanData, coverpoint: str) -> list[TestChunk]:
    """Generate the trap cases of one coverpoint for one row."""
    case = TrapCase(test_data, row, coverpoint)
    chunks: list[TestChunk] = []
    reserved = [sew for sew in SEWS if sew not in row.sews_supported]

    instr = case.instruction
    for sew in reserved if coverpoint == "cp_ime_reserved_sew" else row.sews_supported:
        match coverpoint:
            case "cp_vill":
                chunks.append(
                    case.chunk(
                        sew,
                        "vill",
                        "vtype.vill = 1",
                        1,
                        lambda t, v, a: [f"addi x{v}, x0, -1", f"vsetvl x{t}, x0, x{v}", instr(addr_reg=a)],
                    )
                )
            case "cp_ime_vstart":
                # A nonzero vstart is reserved for multiply-accumulate
                chunks.append(
                    case.chunk(
                        sew,
                        "vstart_one",
                        "vstart = 1",
                        1,
                        lambda t, v, a: [f"LI (x{t}, 1)", f"csrw vstart, x{t}", instr()],
                        record_vstart=True,
                    )
                )
            case "cp_ime_vl_not_multiple":
                # At LMUL=2, lambda*LMUL >= 2, so VL = 1 is not a multiple of it
                chunks.append(
                    case.chunk(
                        sew,
                        "vl_one_lmul_2",
                        "VL = 1 at LMUL = 2",
                        2,
                        lambda t, v, a: [f"LI (x{t}, 1)", *vtype_keep(t, v, f"x{t}"), instr(addr_reg=a)],
                    )
                )
            case "cp_ime_lmul_fractional":
                # vlmul = 111 (LMUL = 1/2) is reserved for IME instructions. The guard keeps vtype itself legal.
                chunks.append(
                    case.chunk(
                        sew,
                        "lmul_f2",
                        "LMUL = 1/2",
                        1,
                        lambda t, v, a: (
                            vtype_keep(t, v, "x0", [f"andi x{v}, x{v}, -8", f"ori x{v}, x{v}, 7"]) + [instr(addr_reg=a)]
                        ),
                        extra_guard=[f"(UDB_ELEN >= {2 * sew})", "defined(TEST_LMULf2_SUPPORTED)"],
                    )
                )
            case "cp_ime_vd_misaligned":
                if case.is_tile:
                    chunks.append(
                        case.chunk(
                            sew,
                            "vd_odd_lmul_2",
                            f"register group v{TILE_REG + 1} at LMUL = 2",
                            2,
                            lambda t, v, a: [instr(vd=TILE_REG + 1, addr_reg=a)],
                        )
                    )
                else:
                    # vd must be aligned to EMUL_C = VLEN/(SEW*lambda^2); v17 is misaligned when EMUL_C >= 2
                    for lambda_value in ime_lambdas(sew):
                        chunks.append(
                            case.chunk(
                                sew,
                                f"vd_v17_lambda_{lambda_value}",
                                f"vd = v{C_REG + 1}, lambda = {lambda_value}",
                                1,
                                lambda t, v, a: [instr(vd=C_REG + 1)],
                                extra_guard=[f"(UDB_VLEN / ({sew} * {lambda_value * lambda_value}) >= 2)"],
                                lambda_value=lambda_value,
                            )
                        )
            case "cp_ime_vs1_misaligned":
                chunks.append(
                    case.chunk(sew, "vs1_odd_lmul_2", "vs1 = v1 at LMUL = 2", 2, lambda t, v, a: [instr(vs1=A_REG + 1)])
                )
            case "cp_ime_vs2_misaligned":
                chunks.append(
                    case.chunk(sew, "vs2_odd_lmul_2", "vs2 = v9 at LMUL = 2", 2, lambda t, v, a: [instr(vs2=B_REG + 1)])
                )
            case "cp_ime_vm0":
                funct6, funct3 = MACC_VM0_ENCODING[row.instr_name]
                chunks.append(
                    case.chunk(
                        sew,
                        "vm_0",
                        f"{row.instr_name} with vm = 0, which has no microscaled form",
                        1,
                        lambda t, v, a, f6=funct6, f3=funct3: [
                            f"_rvtest_ime_mmacc {f6:#x}, {f3}, 0, v{C_REG}, v{A_REG}, v{B_REG}"
                        ],
                    )
                )
            case "cp_ime_reserved_sew":
                chunks.append(
                    case.chunk(
                        sew,
                        "reserved_sew",
                        f"{row.instr_name} at SEW = {sew}, a reserved encoding-map cell",
                        1,
                        lambda t, v, a: [instr()],
                    )
                )
            case "cp_ime_masked_vd_v0":
                chunks.append(
                    case.chunk(
                        sew,
                        "vd_v0_masked",
                        "masked tile load into v0",
                        1,
                        lambda t, v, a: [f"{row.instr_name} v0, (x{a}), x0, v0.t"],
                    )
                )
            case "cp_ime_imm_lambda_unsupported":
                # lambda = 64 needs VLEN >= SEW*4096, so no DUT with VLEN <= VLEN_MAX supports it
                chunks.append(
                    case.chunk(
                        sew,
                        "imm_L64",
                        "immediate lambda L64",
                        1,
                        lambda t, v, a: [f"{row.instr_name} v{TILE_REG}, (x{a}), x0, L64"],
                        extra_guard=[f"!defined(UDB_SUPPORTED_LAMBDA_SEW{sew}_64)"],
                    )
                )
            case _:
                raise ValueError(f"Unknown ExceptionsZvvm coverpoint {coverpoint}")
    return chunks


def tile_vstart(test_data: TestData, row: TestPlanData, coverpoint: str) -> list[TestChunk]:
    """
    A nonzero vstart is legal for tile loads and stores. Execution resumes at element vstart, elements before it are
    not written, and vstart is 0 afterwards. The VLT and VST checks cover the destination; the vstart value after the
    instruction is recorded as well.
    """
    chunks: list[TestChunk] = []
    for sew in row.sews_supported:
        for bin_name, vstart_lines in (
            ("vstart_one", lambda t: [f"LI (x{t}, 1)", f"csrw vstart, x{t}"]),
            ("vstart_half", lambda t: [f"csrr x{t}, vl", f"srli x{t}, x{t}, 1", f"csrw vstart, x{t}"]),
        ):
            tc = test_data.begin_test_chunk()
            tc.code.append(f"# Testcase {coverpoint} ({bin_name}, SEW = {sew})")
            label_line = test_data.add_testcase(
                f"{bin_name}_sew_{sew}", coverpoint, f"{test_data.config.testsuite}_{row.instr_name}_cg"
            )
            params = generate_random_vector_params(
                test_data, row.instr_name, row.instr_type, 1, suite="length", vl="vlmax", sew=sew, ld="padded"
            )
            setup, test, check = format_instruction(row.instr_name, row.instr_type, test_data, params)
            vstart_reg = test_data.int_regs.get_register(exclude_regs=[0])
            vstart_record = [write_sigupd(None, test_data, "vstart")]
            pre, post = arch_lines(sew, False)
            # format_instruction wraps setup and check in the lambda guard, so the vstart lines go inside it
            check_lines = check.split("\n")
            assert check_lines[-1] == "#endif"
            tc.code.extend(
                [
                    f"#if (UDB_ELEN >= {sew})",
                    *pre,
                    setup,
                    *vstart_lines(vstart_reg),
                    label_line,
                    test,
                    *vstart_record,
                    "\n".join(check_lines),
                    *post,
                    "#endif",
                ]
            )
            test_data.int_regs.return_register(vstart_reg)
            return_testcase_registers(test_data, params)
            chunks.append(test_data.end_test_chunk())
    return chunks


def exceptions_zvvm(test_data: TestData, rows: Callable[[TestPlanData], bool]) -> list[TestChunk]:
    """Generate the ExceptionsZvvm tests of the testplan rows that rows() selects."""
    chunks: list[TestChunk] = []
    for row in read_testplan(TESTPLAN):
        if not rows(row):
            continue
        for coverpoint in row.coverpoints:
            if coverpoint == "cp_ime_vstart" and row.instr_type in ("VLT", "VST"):
                chunks.extend(tile_vstart(test_data, row, coverpoint))
            else:
                chunks.extend(trap_cases(test_data, row, coverpoint))
    return chunks


VECTOR_DEFINES = ["#define RVTEST_VECTOR", "#define VDSEW 64", "#define RVTEST_SEW 8"]


@add_priv_test_generator(
    "ExceptionsZvvm", required_extensions=["Zvvmm", "Zve32x"], extra_defines=VECTOR_DEFINES, testcases_per_file=100
)
def make_exceptions_zvvmm(test_data: TestData) -> list[TestChunk]:
    """Integer multiply-accumulate (Zvvmm)."""
    return exceptions_zvvm(test_data, lambda row: row.instr_type == "MMACC")


@add_priv_test_generator(
    "ExceptionsZvvm",
    required_extensions=["Zvvfmm", "Zve32f", "F"],
    extra_defines=VECTOR_DEFINES,
    testcases_per_file=100,
)
def make_exceptions_zvvfmm(test_data: TestData) -> list[TestChunk]:
    """Floating-point multiply-accumulate (Zvvfmm)."""
    return exceptions_zvvm(test_data, lambda row: row.instr_type == "FMMACC")


@add_priv_test_generator(
    "ExceptionsZvvm", required_extensions=["Zvvmtls", "Zve32x"], extra_defines=VECTOR_DEFINES, testcases_per_file=100
)
def make_exceptions_zvvmtls(test_data: TestData) -> list[TestChunk]:
    """Order-preserving tile loads and stores (Zvvmtls)."""
    return exceptions_zvvm(
        test_data, lambda row: row.instr_type in ("VLT", "VST") and row.instr_name not in TRANSPOSING
    )


@add_priv_test_generator(
    "ExceptionsZvvm", required_extensions=["Zvvmttls", "Zve32x"], extra_defines=VECTOR_DEFINES, testcases_per_file=100
)
def make_exceptions_zvvmttls(test_data: TestData) -> list[TestChunk]:
    """Transposing tile loads and stores (Zvvmttls)."""
    return exceptions_zvvm(test_data, lambda row: row.instr_name in TRANSPOSING)
