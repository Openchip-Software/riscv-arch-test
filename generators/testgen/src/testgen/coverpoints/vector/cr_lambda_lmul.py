##################################
# cr_lambda_lmul.py
#
# constantino.gomez@openchip.com October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.vector_helpers import ime_lambdas
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.vector_params import generate_random_vector_params

IME_LMULS = [1, 2, 4, 8]


@add_coverpoint_generator("cr_lambda_lmul")
def make_lambda_lmul(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate IME tests crossing lambda with every integer LMUL at VL=VLMAX.

    A lambda is legal only when VLEN/(SEW*lambda^2) is at least 1, so lambdas that no VLEN up to VLEN_MAX allows
    are not generated. Each testcase is guarded by UDB_SUPPORTED_LAMBDA_SEW<SEW>_<lambda> in its formatter.
    """
    assert test_data.config.sew is not None, "SEW must be set for vector tests"
    sew = test_data.config.sew

    test_chunks = []
    for lambda_value in ime_lambdas(sew):
        for lmul in IME_LMULS:
            params = generate_random_vector_params(
                test_data,
                instr_name,
                instr_type,
                lmul,
                suite="length",
                vl="vlmax",
                lambda_=lambda_value,
                ta=False,
                ma=False,
            )

            desc = f"cr_lambda_lmul (Test lambda = {lambda_value}, lmul = {lmul}, vl = vlmax)"
            bin_name = f"lambda_{lambda_value}_lmul_{lmul}_vl_vlmax"

            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

            test_chunks.append(tc)
            return_testcase_registers(test_data, params)

    return test_chunks
