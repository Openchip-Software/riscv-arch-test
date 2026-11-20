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
# OFP8 floating-point multiply-accumulate: altfmt_A and altfmt_B select E4M3 (0) or E5M2 (1) for A and B
OFP8_FORMATS = {
    "e4m3_e4m3": (False, False),
    "e4m3_e5m2": (False, True),
    "e5m2_e4m3": (True, False),
    "e5m2_e5m2": (True, True),
}


@add_coverpoint_generator("cp_altfmt")
def make_altfmt(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate one IME multiply-accumulate test per signedness of A and B, with the smallest supported lambda. The
    cp_altfmt_ofp8 variant generates one test per OFP8 format of A and B instead.
    """
    ofp8 = coverpoint == "cp_altfmt_ofp8"
    test_chunks = []
    for name, (altfmt_a, altfmt_b) in (OFP8_FORMATS if ofp8 else INTEGER_SIGNEDNESS).items():
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

        if ofp8:
            desc = f"cp_altfmt (Test A {name[:4].upper()}, B {name[5:].upper()})"
        else:
            desc = (
                f"cp_altfmt (Test A {'unsigned' if altfmt_a else 'signed'}, B {'unsigned' if altfmt_b else 'signed'})"
            )
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, name, coverpoint)

        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks
