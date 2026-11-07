##################################
# cp_tile.py
#
# Coverpoints for Integrated Matrix Extension tile loads and stores.
# constantino.gomez@openchip.com October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from typing import Literal

from testgen.asm.vector_helpers import ime_lambdas
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.params import PresetMask
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.vector_params import generate_random_vector_params

TILE_LDS: list[Literal["x0", "zero", "tight", "padded", "double"]] = ["x0", "zero", "tight", "padded", "double"]


@add_coverpoint_generator("cp_ld")
def make_ld(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate tile load and store tests for each kind of leading dimension LD:
    x0 and zero (rs2 = x0, or a register that holds 0) both select the natural LD; tight = linesize;
    padded = linesize + 1; double = 2*linesize. linesize = lambda*LMUL.
    """
    test_chunks = []
    for ld in TILE_LDS:
        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            1,
            suite="length",
            vl="vlmax",
            ld=ld,
            ta=False,
            ma=False,
            rs2=0 if ld == "x0" else None,
        )

        desc = f"cp_ld (Test LD = {ld})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"ld_{ld}", coverpoint)

        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks


@add_coverpoint_generator("cp_imm_lambda")
def make_imm_lambda(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate tile load and store tests with each immediate lambda. vtype.lambda holds a different supported lambda,
    so each test also shows that the immediate overrides vtype.lambda and leaves it unchanged.
    """
    assert test_data.config.sew is not None, "SEW must be set for vector tests"
    test_chunks = []
    for imm_lambda in ime_lambdas(test_data.config.sew):
        params = generate_random_vector_params(
            test_data, instr_name, instr_type, 1, suite="length", vl="vlmax", imm_lambda=imm_lambda, ta=False, ma=False
        )

        desc = f"cp_imm_lambda (Test immediate lambda = L{imm_lambda})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"L{imm_lambda}", coverpoint)

        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks


@add_coverpoint_generator("cr_tile_vtype_agnostic")
def make_tile_vtype_agnostic(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate masked tile loads at VL = VLMAX/2 for each vta and vma. A tile load leaves inactive and tail elements
    undisturbed whatever vta and vma are, so every test expects the same undisturbed elements.
    """
    test_chunks = []
    for vta in (False, True):
        for vma in (False, True):
            params = generate_random_vector_params(
                test_data,
                instr_name,
                instr_type,
                1,
                suite="length",
                masked=True,
                maskval=PresetMask.VLMAX_D2_P1_ONES,
                vl="half",
                ta=vta,
                ma=vma,
            )

            desc = f"cr_tile_vtype_agnostic (Test vta = {int(vta)}, vma = {int(vma)})"
            bin_name = f"vta_{int(vta)}_vma_{int(vma)}"
            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

            test_chunks.append(tc)
            return_testcase_registers(test_data, params)

    return test_chunks
