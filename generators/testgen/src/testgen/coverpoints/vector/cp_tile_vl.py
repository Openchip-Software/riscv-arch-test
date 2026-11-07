##################################
# cp_tile_vl.py
#
# constantino.gomez@openchip.com October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from typing import Literal

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.vector_params import generate_random_vector_params

# One C column (VL = lambda*LMUL), VLMAX/2, VLMAX and a random multiple of lambda*LMUL
TILE_VLS: list[int | Literal["half", "vlmax", "random"]] = [1, "half", "vlmax", "random"]
TILE_VL_LMUL = 2


@add_coverpoint_generator("cp_tile_vl")
def make_tile_vl(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate IME tests at VL values that are multiples of lambda*LMUL, with the smallest supported lambda.
    """
    test_chunks = []
    for vl in TILE_VLS:
        params = generate_random_vector_params(
            test_data, instr_name, instr_type, TILE_VL_LMUL, suite="length", vl=vl, ta=False, ma=False
        )

        vl_name = "one_column" if vl == 1 else vl
        desc = f"cp_tile_vl (Test vl = {vl_name}, lmul = {TILE_VL_LMUL})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"vl_{vl_name}", coverpoint)

        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks
