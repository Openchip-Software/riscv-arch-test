##################################
# cp_custom_tile_crossmode.py
#
# Integrated Matrix Extension: a tile load and a tile store of different modes (order-preserving and transposing).
# constantino.gomez@openchip.com October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from dataclasses import replace

from testgen.asm.vector_helpers import (
    handle_parameter_exclusions,
    ime_lambda_condition,
    ime_lambdas,
    load_ime_vtype,
    write_sigupd_v_len,
)
from testgen.constants import VLEN_MAX
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters.types.tile_type import tile_data_label

IME_LMULS = [1, 2, 4, 8]
TILE_REG, READ_REG = 0, 16
SPAN_REGS = 16

# Labelled transposing instruction -> (load, store) of the pair
CROSSMODE_PAIRS = {"vmtts.v": ("vmtl.v", "vmtts.v"), "vmttl.v": ("vmttl.v", "vmts.v")}


def ld_lines(instr: str, ld: str, ld_reg: int, tmp_reg: int, sew: int, lambda_value: int, lmul: int) -> list[str]:
    """
    Load LD for one instruction of the pair. "nat" uses x0 and needs no code. "pad" is linesize + 1 for an
    order-preserving instruction and M + 1 for a transposing one, with M = VLEN/(SEW*lambda) = vlenb >> log2(SEW*lambda/8).
    """
    if ld == "nat":
        return []
    if instr in ("vmttl.v", "vmtts.v"):
        shift = (sew * lambda_value).bit_length() - 1 - 3
        return [
            f"csrr x{tmp_reg}, vlenb",
            f"srli x{ld_reg}, x{tmp_reg}, {shift}",
            f"addi x{ld_reg}, x{ld_reg}, 1",
        ]
    return [f"LI(x{ld_reg}, {lambda_value * lmul + 1})"]


@add_coverpoint_generator("cp_custom_tile_crossmode")
def make_tile_crossmode(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Load a tile with one mode and store it with the other, at the same vtype and VL = VLMAX: vmtl.v then vmtts.v, or
    vmttl.v then vmts.v. The destination window then holds the transpose of the source tile. The check reads back
    2*LMUL registers of memory from the destination; the gaps between lines keep their values.
    """
    assert test_data.config.sew is not None, "SEW must be set for vector tests"
    sew = test_data.config.sew
    load_instr, store_instr = CROSSMODE_PAIRS[instr_name]

    src_label = tile_data_label(test_data, sew)
    dst_label = f"ime_tile_dst_e{sew}"
    if dst_label not in test_data.vector_labels:
        test_data.register_vector_data(dst_label, sew, random_elements=SPAN_REGS * VLEN_MAX // sew)

    test_chunks = []
    for lambda_value in ime_lambdas(sew):
        for lmul in IME_LMULS:
            for ld in ("nat", "pad"):
                tc = test_data.begin_test_chunk()
                tc.code.append(
                    f"# Testcase cp_custom_tile_crossmode ({load_instr} then {store_instr}, lambda = {lambda_value}, "
                    f"lmul = {lmul}, LD = {ld})"
                )
                label_line = test_data.add_testcase(f"lmul{lmul}_lambda{lambda_value}_ld{ld}", coverpoint)
                for label in (src_label, dst_label):
                    tc.vector_labels.append((label, *test_data.vector_labels[label]))

                test_data.vec_regs.consume_registers(list(range(32)))
                temp_reg, src_reg, dst_reg, load_ld, store_ld, tmp_reg = test_data.int_regs.get_registers(
                    6, exclude_regs=[0]
                )
                params = InstructionParams(
                    sew=sew, lmul=lmul, lambda_=lambda_value, vl="vlmax", ta=False, ma=False, temp_reg=temp_reg
                )
                load_rs2 = f"x{load_ld}" if ld == "pad" else "x0"
                store_rs2 = f"x{store_ld}" if ld == "pad" else "x0"
                load_line = f"{load_instr} v{TILE_REG}, (x{src_reg}), {load_rs2}"
                store_line = f"{store_instr} v{TILE_REG}, (x{dst_reg}), {store_rs2}"

                setup = [
                    *load_ime_vtype(params, test_data),
                    f"LA (x{src_reg}, {src_label})",
                    f"LA (x{dst_reg}, {dst_label})",
                    *ld_lines(load_instr, ld, load_ld, tmp_reg, sew, lambda_value, lmul),
                    *ld_lines(store_instr, ld, store_ld, tmp_reg, sew, lambda_value, lmul),
                ]
                # The labelled instruction is the transposing one
                if instr_name == load_instr:
                    test = [label_line, load_line, store_line]
                else:
                    test = [load_line, label_line, store_line]

                read_lmul = min(2 * lmul, 8)
                segments = 2 if lmul == 8 else 1
                check = [
                    f"# Read back {2 * lmul} registers of memory from {dst_label}",
                    f"vsetvli x{temp_reg}, x0, e{sew}, m{read_lmul}, tu, mu",
                    f"vle{sew}.v v{READ_REG}, (x{dst_reg})",
                ]
                if segments == 2:
                    check.extend(
                        [
                            f"csrr x{tmp_reg}, vlenb",
                            f"slli x{tmp_reg}, x{tmp_reg}, 3",
                            f"add x{tmp_reg}, x{dst_reg}, x{tmp_reg}",
                            f"vle{sew}.v v{READ_REG + 8}, (x{tmp_reg})",
                        ]
                    )
                test_data.vec_regs.return_registers(list(range(READ_REG)))
                check.extend(
                    write_sigupd_v_len(
                        test_data, replace(params, vd=READ_REG), read_lmul, segments=segments, check_reg=READ_REG
                    )
                )
                test_data.vec_regs.return_registers(list(range(READ_REG, 32)))
                test_data.int_regs.return_registers([temp_reg, src_reg, dst_reg, load_ld, store_ld, tmp_reg])

                handle_parameter_exclusions(lmul, setup, check, ime_condition=ime_lambda_condition(sew, [lambda_value]))
                tc.code.extend(["\n".join(setup), "\n".join(test), "\n".join(check)])
                test_chunks.append(test_data.end_test_chunk())

    return test_chunks
