##################################
# mmacc_type.py
#
# Integrated Matrix Extension integer multiply-accumulate (vmmacc.vv and its widening forms).
# constantino.gomez@openchip.com October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import struct
from dataclasses import replace

from testgen.asm.vector_helpers import (
    VectorLoad,
    handle_parameter_exclusions,
    handle_vector_fp,
    ime_extend_label,
    ime_lambda_condition,
    ime_lambdas,
    load_ime_vtype,
    load_vec_regs,
    write_sigupd_v_len,
)
from testgen.constants import VLEN_MAX
from testgen.data.params import InstructionParams
from testgen.data.random import random_range
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter

# C occupies EMUL_C = VLEN/(SEW*lambda^2) registers, which can be 16. A window of 16 registers at v0 or v16 fits
# every VLEN. The specification does not say whether vd may overlap vs1 or vs2; the tests keep them apart.
mmacc_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(
        overlap_constraints={("vd", "vs1"), ("vd", "vs2")},
        fixed_emul={"vd": 16},
        maskable=False,
        require_zero_vstart=True,
    ),
)

C_WINDOW_REGS = 16
C_WINDOW_LMUL = 8
C_WINDOW_SEGMENTS = 2


# Floating-point multiply-accumulate. A, B and C hold small integers and half-integers, so every product, partial
# sum and C value is exact in every format and every order (see fp_exact_data). The result is then the same for
# every grouping, partial-sum mode and rounding that the specification permits. A and B stay in separate registers:
# an edge value in A or B must meet the background of the other operand, not itself.
fmmacc_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    instruction_class=["vector_fp"],
    vector_data=VectorTypeConfig(
        overlap_constraints={("vd", "vs1"), ("vd", "vs2"), ("vs1", "vs2")},
        fixed_emul={"vd": 16},
        maskable=False,
        require_zero_vstart=True,
    ),
)

# Widening factor W of each multiply-accumulate mnemonic
WIDENING = {"vfmmacc.vv": 1, "vfwmmacc.vv": 2, "vfqmmacc.vv": 4, "vf8wmmacc.vv": 8}
FP_PACK = {16: "<e", 32: "<f", 64: "<d"}


def fp_bits(value: float, fmt: str) -> int:
    """Encode an exactly representable value in fp16, bf16, fp32 or fp64."""
    if fmt == "bf16":
        return int.from_bytes(struct.pack("<f", value), "little") >> 16
    width = int(fmt[2:])
    return int.from_bytes(struct.pack(FP_PACK[width], value), "little")


def fp_input_format(test_data: TestData, sew: int, w: int) -> str:
    """Return the input format of a row: bf16 when its type extension names bf16, else IEEE at SEW/W bits."""
    if any("bf16" in ext for ext in test_data.config.extra_extensions):
        return "bf16"
    return f"fp{sew // w}"


def fp_exact_data(
    test_data: TestData, reg: str, sew: int, w: int, input_fmt: str, emul: float, background: float | None = None
) -> str:
    """
    Register a label of SEW-wide storage elements that fills emul registers at VLEN_MAX with exact FP data.

    A and B inputs are sparse integers in [-2, 2], packed W per storage element. C holds half-integers k + 0.5 with
    |k| <= 128, so no C value is ever zero. A dot product has at most lambda*W*LMUL <= 64 terms at fp16 (VLEN_MAX
    limits lambda), so every running sum stays below 512 in magnitude, where fp16 still has a 0.25 resolution. Every
    value is therefore exact in fp16, bf16 (inputs only), fp32 and fp64.

    With background set, every input element (or every C element) holds that value instead.
    """
    count = int(VLEN_MAX * emul) // sew
    lane_bits = sew // w
    elements = []
    for _ in range(count):
        if reg == "vd":
            value = background if background is not None else random_range(-128, 128) + 0.5
            elements.append(fp_bits(value, f"fp{sew}"))
        else:
            lanes = [
                background if background is not None else (random_range(-2, 2) if random_range(0, 3) == 0 else 0)
                for _ in range(w)
            ]
            elements.append(sum(fp_bits(float(v), input_fmt) << (i * lane_bits) for i, v in enumerate(lanes)))
    label = f"{reg}_fp_ime_{test_data.test_count:03d}"
    test_data.register_vector_data(label, sew, elements=elements)
    return label


def fp_edge_data(test_data: TestData, reg: str, edge_label: str, sew: int, w: int, input_fmt: str, emul: float) -> str:
    """
    Register exact background data for reg with the edge value of edge_label in input element 0 (C element 0 for
    vd). An A or B edge has a background of 0, a C edge a background of exact random C values.
    """
    elements, _ = test_data.vector_labels[edge_label]
    lane_bits = sew // w if reg != "vd" else sew
    label = fp_exact_data(test_data, reg, sew, w, input_fmt, emul, background=None if reg == "vd" else 0.0)
    data, _ = test_data.vector_labels[label]
    mask = (1 << lane_bits) - 1
    edge_data = [(data[0] & ~mask) | (elements[0] & mask), *data[1:]]
    edge_label_full = f"{reg}_fp_edge_ime_{test_data.test_count:03d}"
    test_data.register_vector_data(edge_label_full, sew, elements=edge_data)
    return edge_label_full


@add_instruction_formatter("FMMACC", fmmacc_config)
def format_fmmacc(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.sew is not None and params.lmul is not None, "sew and lmul must be provided for FMMACC"
    assert params.csr_frm_val is not None, "FMMACC tests run with a dynamic rounding mode"
    w = WIDENING[instr_str]
    input_fmt = fp_input_format(test_data, params.sew, w)

    # BF16 inputs are selected by altfmt_A = altfmt_B = 1
    params.altfmt_a = params.altfmt_b = input_fmt == "bf16"
    if params.vector_suite == "base":
        params.vl = "vlmax"

    # An edge value from cp_vd_edges, cp_vs1_edges or cp_vs2_edges is the only nonzero product of its C elements, so
    # every implementation computes round_frm(C + edge) for them:
    #   A edge: A = edge in element 0 and 0 elsewhere, B = +1.0.
    #   B edge: B = edge in element 0 and 0 elsewhere, A = +1.0.
    #   C edge: C = edge in element 0, A = B = 0.
    edge_reg = next(
        (reg for reg in ("vs1", "vs2", "vd") if "_edge_" in (getattr(params, f"{reg}_val_pointer") or "")), None
    )
    backgrounds: dict[str, float | None] = {"vs1": None, "vs2": None, "vd": None}
    if edge_reg == "vd":
        backgrounds["vs1"] = backgrounds["vs2"] = 0.0
    elif edge_reg is not None:
        backgrounds["vs2" if edge_reg == "vs1" else "vs1"] = 1.0
    for reg, emul in (("vs1", params.lmul), ("vs2", params.lmul), ("vd", C_WINDOW_REGS)):
        if "_subdot_" in (getattr(params, f"{reg}_val_pointer") or ""):
            continue  # cp_fp_subdot builds complete data
        if reg == edge_reg:
            label = fp_edge_data(test_data, reg, getattr(params, f"{reg}_val_pointer"), params.sew, w, input_fmt, emul)
        else:
            label = fp_exact_data(test_data, reg, params.sew, w, input_fmt, emul, background=backgrounds[reg])
        setattr(params, f"{reg}_val_pointer", label)
    params.vector_suite = "length"

    setup, test, check = format_mmacc(instr_str, test_data, params)
    handle_vector_fp(setup, check, params.csr_frm_val, test_data)
    return setup, test, check


@add_instruction_formatter("MMACC", mmacc_config)
def format_mmacc(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.vs1 is not None and params.vs1_val_pointer is not None, "vs1 must be provided for MMACC"
    assert params.vs2 is not None and params.vs2_val_pointer is not None, "vs2 must be provided for MMACC"
    assert params.vd is not None and params.vd_val_pointer is not None, "vd must be provided for MMACC"
    assert params.temp_reg is not None, "temp_reg must be provided for MMACC"
    assert params.sew is not None, "sew must be provided for MMACC"
    assert params.lmul is not None, "lmul must be provided for MMACC"
    assert params.maskval is None, "MMACC instructions are not maskable"
    assert test_data.test_chunk is not None, "format_mmacc must be used with an active TestChunk"

    # Every MMACC testcase checks the whole C window. Base-suite callers pass VL=1 and register short data labels
    # (one element, or one edge value at the input width). They run at VL=VLMAX, and their labels are extended to
    # fill A, B and the C window.
    if params.vector_suite == "base":
        params.vl = "vlmax"
        for reg, emul in (("vs1", params.lmul), ("vs2", params.lmul), ("vd", C_WINDOW_REGS)):
            label = getattr(params, f"{reg}_val_pointer")
            setattr(params, f"{reg}_val_pointer", ime_extend_label(test_data, label, reg, params.sew, emul))

    # A preset vd reserves only its first register, so reserve the whole window before temporaries are taken
    test_data.vec_regs.allocate_operand("vd", params.vd, C_WINDOW_REGS, suppress_overlap=True)

    test_data.test_chunk.vector_labels.extend(
        [
            (params.vs1_val_pointer, *test_data.vector_labels[params.vs1_val_pointer]),
            (params.vs2_val_pointer, *test_data.vector_labels[params.vs2_val_pointer]),
            (params.vd_val_pointer, *test_data.vector_labels[params.vd_val_pointer]),
        ]
    )

    stride_reg = test_data.int_regs.get_register(exclude_regs=[0])
    setup = [
        f"# C window v{params.vd}-v{params.vd + 15}: two m{C_WINDOW_LMUL} loads",
        f"vsetvli x{params.temp_reg}, x0, e{params.sew}, m{C_WINDOW_LMUL}, tu, mu",
        f"LA (x{params.temp_reg}, {params.vd_val_pointer})",
        f"vle{params.sew}.v v{params.vd}, (x{params.temp_reg})",
        f"csrr x{stride_reg}, vlenb",
        f"slli x{stride_reg}, x{stride_reg}, 3",
        f"add x{params.temp_reg}, x{params.temp_reg}, x{stride_reg}",
        f"vle{params.sew}.v v{params.vd + C_WINDOW_LMUL}, (x{params.temp_reg})",
        f"# A (vs1 = v{params.vs1}) and B (vs2 = v{params.vs2}) at LMUL={params.lmul}, VL=VLMAX",
    ]
    test_data.int_regs.return_register(stride_reg)

    # A and B are loaded at VLMAX whatever the test VL is. load_ime_vtype sets the test VL.
    load_code, _ = load_vec_regs([VectorLoad(reg="vs1"), VectorLoad(reg="vs2")], replace(params, vl="vlmax"), test_data)
    setup.extend(load_code)
    setup.extend(load_ime_vtype(params, test_data))

    test = [f"{instr_str} v{params.vd}, v{params.vs1}, v{params.vs2}"]

    # Free A and B so that the signature check has room for its temporaries
    test_data.vec_regs.deallocate_operand("vs2")
    test_data.vec_regs.deallocate_operand("vs1")

    check = [
        f"# Check the C window at e{params.sew}, m{C_WINDOW_LMUL}, VL=VLMAX. vta=0, so elements beyond VL are unchanged",
        f"vsetvli x{params.temp_reg}, x0, e{params.sew}, m{C_WINDOW_LMUL}, tu, mu",
        *write_sigupd_v_len(test_data, params, C_WINDOW_LMUL, segments=C_WINDOW_SEGMENTS),
    ]

    lambdas = ime_lambdas(params.sew) if params.lambda_ is None else [params.lambda_]
    handle_parameter_exclusions(params.lmul, setup, check, ime_condition=ime_lambda_condition(params.sew, lambdas))

    return (setup, test, check)
