##################################
# cp_scale.py
#
# constantino.gomez@openchip.com November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from typing import Any

from testgen.constants import IME_VLEN_MAX
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.registry import get_instruction_type_config
from testgen.formatters.types.mmacc_type import (
    E8M0_BIAS,
    E8M0_NAN,
    WIDENING,
    fp_bits,
    fp_input_format,
    fp_operand_format,
    fp_output_format,
    mx_scale_data,
)
from testgen.instructions.vector_params import generate_random_vector_params

E8M0_MIN = 0x00  # 2^-127
E8M0_MAX = 0xFE  # 2^127

# Combined exponent eA + eB - 254 below the smallest subnormal exponent of C, and the partial sum S = 2^4 that keeps
# S * 2^e exactly representable in C. FP64 has no such exponent: every combined exponent is at least -254.
UNDERFLOW_EXPONENT = {"fp16": -26, "bf16": -136, "fp32": -152}
UNDERFLOW_INPUT = 4.0
# Combined exponent above the largest exponent of C, and S = 2^-2 from FP inputs that keeps S * 2^e in range. An
# integer S is at least 1 in magnitude, so integer inputs use S = 0 instead. FP64 has no such exponent.
OVERFLOW_EXPONENT = {"fp16": 16, "bf16": 128, "fp32": 128}
OVERFLOW_INPUT = 0.5


@add_coverpoint_generator("cp_scale")
def make_scale(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Microscaled multiply-accumulate with edge E8M0 block scales. Every result is exact in the C format, or rounded
    once from an exact scaled partial sum, so it does not depend on the grouping, partial-sum or rounding choices.

    nan_a, nan_b: scale_A or scale_B of element 0 is 0xFF. Row 0 or column 0 of C is the default NaN, with no flags.
    min_max, max_min: every scale pair is (2^-127, 2^127) or (2^127, 2^-127). The combined exponent is 0, although
    each scale alone is out of range of C.
    underflow, overflow: every scale pair has the combined exponent of UNDERFLOW_EXPONENT or OVERFLOW_EXPONENT. A is
    zero except in element 0 and B is constant, so S is A[0][0] * B or zero.
    """
    assert test_data.config.sew is not None, "SEW must be set for vector tests"
    sew = test_data.config.sew
    w = WIDENING[instr_name]
    input_family = fp_input_format(test_data, sew, w)
    input_fmt = fp_operand_format(input_family, altfmt=False)
    output_fmt = fp_output_format(test_data, sew)
    vector_data = get_instruction_type_config(instr_type).vector_data
    assert vector_data is not None, "IME multiply-accumulates are vector instructions"
    lane_bits = sew // w

    cases: list[tuple[str, str, dict[str, int], float | None]] = [
        ("nan_a", "scale_A of row 0, block 0 is NaN", {"first_a": E8M0_NAN}, None),
        ("nan_b", "scale_B of column 0, block 0 is NaN", {"first_b": E8M0_NAN}, None),
        ("min_max", "every scale_A is 2^-127 and every scale_B 2^127", {"a": E8M0_MIN, "b": E8M0_MAX}, None),
        ("max_min", "every scale_A is 2^127 and every scale_B 2^-127", {"a": E8M0_MAX, "b": E8M0_MIN}, None),
    ]
    if output_fmt in UNDERFLOW_EXPONENT:
        half = UNDERFLOW_EXPONENT[output_fmt] // 2 + E8M0_BIAS
        desc = f"combined exponent {UNDERFLOW_EXPONENT[output_fmt]} below the {output_fmt} range"
        cases.append(("underflow", desc, {"a": half, "b": half}, UNDERFLOW_INPUT))
    if output_fmt in OVERFLOW_EXPONENT:
        half = OVERFLOW_EXPONENT[output_fmt] // 2 + E8M0_BIAS
        value = 0.0 if input_family in ("i4", "i8") else OVERFLOW_INPUT
        desc = f"combined exponent {OVERFLOW_EXPONENT[output_fmt]} above the {output_fmt} range, S = {value**2}"
        cases.append(("overflow", desc, {"a": half, "b": half}, value))

    test_chunks = []
    for bin_name, desc, scales, value in cases:
        if "first_a" in scales or "first_b" in scales:
            first = (scales.get("first_a", E8M0_BIAS), scales.get("first_b", E8M0_BIAS))
            scale_label = mx_scale_data(
                test_data, scale_a=E8M0_BIAS, scale_b=E8M0_BIAS, first=first, label=f"v0_scale_{bin_name}"
            )
        else:
            scale_label = mx_scale_data(
                test_data, scale_a=scales["a"], scale_b=scales["b"], label=f"v0_scale_{bin_name}"
            )

        labels: dict[str, Any] = {"scale_val_pointer": scale_label}
        if value is not None:
            # A[0][0] = value and every other element of A is 0; every element of B is value
            count = IME_VLEN_MAX // sew
            lane = fp_bits(value, input_fmt)
            a = [lane] + [0] * (count - 1)
            b = [sum(lane << (i * lane_bits) for i in range(w))] * count
            for reg, data in (("vs1", a), ("vs2", b)):
                labels[f"{reg}_val_pointer"] = f"{reg}_scale_{bin_name}"
                test_data.register_vector_data(labels[f"{reg}_val_pointer"], sew, elements=data)

        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            1,
            suite="length",
            vl="vlmax",
            ta=False,
            ma=False,
            additional_no_overlap=vector_data.edge_no_overlap if value is not None else None,
            **labels,
        )
        tc = format_single_testcase(
            instr_name, instr_type, test_data, params, f"cp_scale (Test {desc})", bin_name, coverpoint
        )

        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks
