##################################
# cp_mx_bs.py
#
# constantino.gomez@openchip.com November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_mx_bs")
def make_mx_bs(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate one microscaled multiply-accumulate with the block size of the row: cp_mx_bs_32 for a Zvvx* row
    (vtype.bs = 0) and cp_mx_bs_16 for a Zvvxn* row (vtype.bs = 1). The formatter sets vtype.bs from the row.
    """
    block_size = coverpoint.removeprefix("cp_mx_bs_")
    params = generate_random_vector_params(
        test_data, instr_name, instr_type, 1, suite="length", vl="vlmax", ta=False, ma=False
    )
    desc = f"cp_mx_bs (Test block size {block_size})"
    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"bs_{block_size}", coverpoint)
    return_testcase_registers(test_data, params)
    return [tc]
