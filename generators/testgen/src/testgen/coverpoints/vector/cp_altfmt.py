##################################
# cp_altfmt.py
#
# constantino.gomez@openchip.com October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.vector_params import generate_random_vector_params

# Integer IME multiply-accumulate: vtype.altfmt_A=1 makes A unsigned and vtype.altfmt_B=1 makes B unsigned
INTEGER_SIGNEDNESS = {"ss": (False, False), "su": (False, True), "us": (True, False), "uu": (True, True)}


@add_coverpoint_generator("cp_altfmt")
def make_altfmt(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate one IME multiply-accumulate test per signedness of A and B, with the smallest supported lambda.
    """
    test_chunks = []
    for name, (altfmt_a, altfmt_b) in INTEGER_SIGNEDNESS.items():
        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            1,
            suite="length",
            vl="vlmax",
            altfmt_a=altfmt_a,
            altfmt_b=altfmt_b,
            ta=False,
            ma=False,
        )

        desc = f"cp_altfmt (Test A {'unsigned' if altfmt_a else 'signed'}, B {'unsigned' if altfmt_b else 'signed'})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, name, coverpoint)

        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks
