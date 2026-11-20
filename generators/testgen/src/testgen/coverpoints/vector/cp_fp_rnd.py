##################################
# cp_fp_rnd.py
#
# Integrated Matrix Extension: the disclosed rounding rnd of a floating-point group partial sum.
# constantino.gomez@openchip.com November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.vector_helpers import ime_lambdas
from testgen.constants import VLEN_MAX
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.random import random_range
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.registry import get_instruction_type_config
from testgen.formatters.types.mmacc_type import (
    C_WINDOW_REGS,
    WIDENING,
    fp_bits,
    fp_c_range,
    fp_input_format,
    fp_operand_format,
    fp_output_format,
)
from testgen.instructions.vector_params import generate_random_vector_params

FRM_NAMES = ["rne", "rtz", "rdn", "rup", "rmm"]
PRECISION = {"fp16": 11, "bf16": 8, "fp32": 24, "fp64": 53}

# (SEW, W) -> (C0, [(A, B) for the nonzero products of C[0][0]]) for W > 1. The products are exact, and their sum S is
# not exact in fp<SEW>. C0 = -round(S), so a rounded S gives 0 and an unrounded S gives the rounding error of S.
WIDENING_VALUES = {
    (32, 2): (-1.0, [(1.0, 1.0), (2.0**-15, 2.0**-15)]),  # S = 1 + 2^-30
    (64, 2): (-1.0, [(1.0, 1.0), (2.0**-30, 2.0**-30)]),  # S = 1 + 2^-60
    (64, 4): (-(2.0**30), [(2.0**15, 2.0**15), (2.0**-24, 2.0**-24)]),  # S = 2^30 + 2^-48
}

# OFP8 inputs, (SEW, W) -> (A and B format, C0, products). E4M3 spans 2^-9 to 448. An FP64 C needs the E5M2 range,
# 2^-16 to 57344.
OFP8_VALUES = {
    (16, 2): ("e4m3", -1.0, [(1.0, 1.0), (2.0**-6, 2.0**-6)]),  # S = 1 + 2^-12
    (32, 4): ("e4m3", -(2.0**16), [(2.0**8, 2.0**8), (2.0**-9, 2.0**-9)]),  # S = 2^16 + 2^-18
    (64, 8): ("e5m2", -(2.0**30), [(2.0**15, 2.0**15), (2.0**-16, 2.0**-16)]),  # S = 2^30 + 2^-32
}

# OFP4 inputs: E2M1 products are multiples of 2^-2 up to 36. A sum of W <= 8 of them is exact in FP16 and FP32, so
# only a BF16 C (8 significant bits) has data. S = 3 * 36 + 2^-2 = 108.25 needs 9 significant bits.
OFP4_BF16_VALUES = ("e2m1", -108.0, [(6.0, 6.0), (6.0, 6.0), (6.0, 6.0), (0.5, 0.5)])


def rnd_values(
    sew: int, w: int, input_family: str, output_fmt: str
) -> tuple[str, float, list[tuple[float, float]]] | None:
    """The A and B format, C0 and the nonzero (A, B) products of C[0][0], or None when the row has no such data."""
    if input_family == "ofp8":
        return OFP8_VALUES.get((sew, w))
    if input_family == "ofp4":
        return OFP4_BF16_VALUES if output_fmt == "bf16" else None
    if w > 1:
        values = WIDENING_VALUES.get((sew, w))
        return None if values is None else (input_family, *values)
    if input_family != output_fmt:
        return None
    # W = 1: S = (1 + 2^-(p-1)) * (1 + 2^-(p-2)) = 1 + 3 * 2^-(p-1) + 2^-(2p-3). Rounded in the C format, S loses
    # 2^-(2p-3) in every rounding mode except rup, which rounds S up to 1 + 4 * 2^-(p-1). C0 + S is exact in the C
    # format.
    p = PRECISION[input_family]
    return input_family, -1.0, [(1.0 + 2.0 ** -(p - 1), 1.0 + 2.0 ** -(p - 2))]


@add_coverpoint_generator("cp_fp_rnd")
def make_fp_rnd(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    FP multiply-accumulate where the group partial sum S of C[0][0] is not exact in the C format, and C0 + S is.
    With rnd = frm the implementation adds round(S) to C0; with rnd = xct it adds S. The results differ in every
    rounding mode. Sail computes rnd = frm, so each testcase runs only on a DUT that discloses rnd = frm and psm = 0
    for its (SEW, W, lambda). All other products are zero, so the group size G does not change S. One bin per frm value
    and lambda.
    """
    assert test_data.config.sew is not None, "SEW must be set for vector tests"
    sew = test_data.config.sew
    w = WIDENING[instr_name]
    input_family = fp_input_format(test_data, sew, w)
    output_fmt = fp_output_format(test_data, sew)
    values = rnd_values(sew, w, input_family, output_fmt)
    if values is None:
        return []
    input_fmt, c0, products = values
    altfmt_ofp8 = input_fmt == "e5m2"
    assert fp_operand_format(input_family, altfmt_ofp8) == input_fmt
    lane_bits = sew // w
    lmul = 1
    vector_data = get_instruction_type_config(instr_type).vector_data
    assert vector_data is not None, "IME multiply-accumulates are vector instructions"
    edge_no_overlap = vector_data.edge_no_overlap

    test_chunks = []
    for lambda_value in ime_lambdas(sew):
        index = lambda_value.bit_length() - 1
        guard = (
            f"defined(UDB_ZVVM_FP_RND_SEW{sew}_W{w}_IDX{index}_FRM)"
            f" && ((UDB_ZVVM_FP_PSM_SEW{sew}_W{w}_MASK & {1 << index}) == 0)"
        )
        for frm, frm_name in enumerate(FRM_NAMES):
            count = VLEN_MAX * lmul // sew
            a = [sum(fp_bits(av, input_fmt) << (i * lane_bits) for i, (av, _) in enumerate(products))] + [0] * (
                count - 1
            )
            b = [sum(fp_bits(bv, input_fmt) << (i * lane_bits) for i, (_, bv) in enumerate(products))] + [0] * (
                count - 1
            )
            c_count = VLEN_MAX * C_WINDOW_REGS // sew
            c_range = fp_c_range(output_fmt)
            c = [fp_bits(c0, output_fmt)] + [
                fp_bits(random_range(-c_range, c_range) + 0.5, output_fmt) for _ in range(c_count - 1)
            ]
            labels = {}
            for reg, data in (("vs1", a), ("vs2", b), ("vd", c)):
                labels[f"{reg}_val_pointer"] = f"{reg}_rnd_l{lambda_value}_{frm_name}"
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
                lambda_=lambda_value,
                ime_guard=guard,
                altfmt_a=altfmt_ofp8,
                altfmt_b=altfmt_ofp8,
                additional_no_overlap=edge_no_overlap,
                **labels,
            )
            desc = (
                f"cp_fp_rnd (Test a partial sum that is not exact in {output_fmt}, rnd = frm, lambda = {lambda_value}, "
                f"frm = {frm_name})"
            )
            tc = format_single_testcase(
                instr_name, instr_type, test_data, params, desc, f"frm_l{lambda_value}_{frm_name}", coverpoint
            )
            test_chunks.append(tc)
            return_testcase_registers(test_data, params)

    return test_chunks
