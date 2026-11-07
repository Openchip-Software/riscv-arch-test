##################################
# cp_fp_subdot.py
#
# Integrated Matrix Extension: the partial sum of a widening floating-point multiply-accumulate.
# constantino.gomez@openchip.com October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.constants import VLEN_MAX
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.random import random_range
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.types.mmacc_type import C_WINDOW_REGS, WIDENING, fp_bits, fp_input_format
from testgen.instructions.vector_params import generate_random_vector_params

FRM_NAMES = ["rne", "rtz", "rdn", "rup", "rmm"]

# (SEW, W) -> (C0, A value, B value). Each of the W products A*B is exact and equals ULP(C0)/W.
SUBDOT_VALUES = {
    (32, 2): (1.0, 2.0**-12, 2.0**-12),  # ULP(1.0) in fp32 = 2^-23
    (64, 2): (1.0, 2.0**-26, 2.0**-27),  # ULP(1.0) in fp64 = 2^-52
    (64, 4): (2.0**52, 0.5, 0.5),  # ULP(2^52) in fp64 = 1
}


@add_coverpoint_generator("cp_fp_subdot")
def make_fp_subdot(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Widening FP multiply-accumulate (W > 1) where the W products of one sub-dot-product of C[0][0] add up to exactly
    one ULP of C0, and every other product is zero. The specification forms the partial sum S of the W products
    before C is updated, so a conforming implementation returns C0 + 1 ULP with no flags in every rounding mode.
    Adding each product to C on its own rounds every step instead. One bin per frm value.
    """
    assert test_data.config.sew is not None, "SEW must be set for vector tests"
    sew = test_data.config.sew
    w = WIDENING[instr_name]
    c0, a_value, b_value = SUBDOT_VALUES[(sew, w)]
    input_fmt = fp_input_format(test_data, sew, w)
    lane_bits = sew // w
    lmul = 1

    test_chunks = []
    for frm, frm_name in enumerate(FRM_NAMES):
        count = VLEN_MAX * lmul // sew
        a = [sum(fp_bits(a_value, input_fmt) << (i * lane_bits) for i in range(w))] + [0] * (count - 1)
        b = [sum(fp_bits(b_value, input_fmt) << (i * lane_bits) for i in range(w))] + [0] * (count - 1)
        c_count = VLEN_MAX * C_WINDOW_REGS // sew
        c = [fp_bits(c0, f"fp{sew}")] + [fp_bits(random_range(-128, 128) + 0.5, f"fp{sew}") for _ in range(c_count - 1)]
        labels = {}
        for reg, data in (("vs1", a), ("vs2", b), ("vd", c)):
            labels[f"{reg}_val_pointer"] = f"{reg}_subdot_{frm_name}"
            test_data.register_vector_data(labels[f"{reg}_val_pointer"], sew, elements=data)

        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            lmul,
            suite="length",
            vl="vlmax",
            ta=False,
            ma=False,
            csr_frm_val=frm,
            **labels,
        )
        desc = f"cp_fp_subdot (Test W products adding up to one ULP of C0, frm = {frm_name})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"ulp_{frm_name}", coverpoint)

        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks
