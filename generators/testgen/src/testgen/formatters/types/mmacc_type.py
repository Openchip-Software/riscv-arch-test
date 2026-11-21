##################################
# mmacc_type.py
#
# Integrated Matrix Extension integer multiply-accumulate (vmmacc.vv and its widening forms).
# constantino.gomez@openchip.com October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import math
import struct
from dataclasses import replace

from testgen.asm.vector_helpers import (
    VectorLoad,
    handle_parameter_exclusions,
    handle_vector_fp,
    ime_extend_label,
    ime_lambda_condition,
    ime_lambdas,
    ime_overlay,
    load_ime_vtype,
    load_vec_regs,
    write_sigupd_v_len,
)
from testgen.constants import IME_VLEN_MAX
from testgen.data.params import InstructionParams
from testgen.data.random import random_range
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter

# C occupies EMUL_C = VLEN/(SEW*lambda^2) registers, which can be 16. A window of 16 registers at v0 or v16 fits
# every VLEN. The specification forbids vd to overlap vs1 or vs2.
mmacc_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(
        overlap_constraints={("vd", "vs1"), ("vd", "vs2")},
        fixed_emul={"vd": 16},
        maskable=False,
        require_zero_vstart=True,
        vlen_max=IME_VLEN_MAX,
        shared_data=True,
    ),
)

C_WINDOW_REGS = 16
# E5M2 0x7D: a signaling NaN under the IEEE convention
NV_PRESET_EDGE = "_edge_e5m2_sNaN_payload1_"
C_WINDOW_LMUL = 8
C_WINDOW_SEGMENTS = 2
# Labels of data built by cp_fp_subdot, cp_fp_rnd and cp_scale carry these tags. The formatter keeps that data.
DEDICATED_DATA_TAGS = ("_subdot_", "_rnd_", "_scale_")
# Only storage elements whose index is a multiple of this stride hold nonzero A and B inputs (see fp_exact_data)
NONZERO_STRIDE = {"fp16": 2, "bf16": 4}


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
        vlen_max=IME_VLEN_MAX,
        shared_data=True,
    ),
)

# Microscaled floating-point multiply-accumulate (vm=0). v0 holds the paired E8M0 block scales, and no operand may
# overlap it. The C window is then v16-v31, and A and B are in v1-v15. At LMUL=8 both are v8. The specification lets
# A and B overlap. A and B with edge values or other dedicated data stay in separate registers.
fmmacc_mx_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    instruction_class=["vector_fp"],
    vector_data=VectorTypeConfig(
        overlap_constraints={("vd", "vs1"), ("vd", "vs2"), ("v0", "vd"), ("v0", "vs1"), ("v0", "vs2")},
        fixed_emul={"vd": 16},
        maskable=False,
        require_zero_vstart=True,
        edge_no_overlap={("vs1", "vs2")},
        vlen_max=IME_VLEN_MAX,
        shared_data=True,
    ),
)

# Widening factor W of each multiply-accumulate mnemonic. vfwimmacc.vv, vfqimmacc.vv and vf8wimmacc.vv take
# integer inputs and a floating-point C; they exist only with vm=0.
WIDENING = {
    "vfmmacc.vv": 1,
    "vfwmmacc.vv": 2,
    "vfqmmacc.vv": 4,
    "vf8wmmacc.vv": 8,
    "vfwimmacc.vv": 2,
    "vfqimmacc.vv": 4,
    "vf8wimmacc.vv": 8,
}
# E8M0 block scales: bias 127, 0xFF is NaN. A paired-scale element holds scale_A in bits 7:0 and scale_B in bits 15:8.
E8M0_BIAS = 127
E8M0_NAN = 0xFF
SCALE_PAIR_BITS = 16
# Random scales: scale_A is 2^0 or 2^1 and scale_B is 2^-1 or 2^0, so the combined exponent is -1, 0 or 1
RANDOM_SCALES_A = (E8M0_BIAS, E8M0_BIAS + 1)
RANDOM_SCALES_B = (E8M0_BIAS - 1, E8M0_BIAS)
FP_PACK = {16: "<e", 32: "<f", 64: "<d"}
# OCP OFP formats: (exponent bits, mantissa bits, bias)
OFP_FORMATS = {"e4m3": (4, 3, 7), "e5m2": (5, 2, 15), "e2m1": (2, 1, 1)}


def fp_bits(value: float, fmt: str) -> int:
    """
    Encode an exactly representable finite value in e2m1, e4m3, e5m2, fp16, bf16, fp32 or fp64, or an integer value
    in two's complement i4 or i8.
    """
    if fmt in ("i4", "i8"):
        width = int(fmt[1:])
        assert value.is_integer() and -(2 ** (width - 1)) <= value < 2 ** (width - 1), f"{value} is not an {fmt}"
        return int(value) & ((1 << width) - 1)
    if fmt in OFP_FORMATS:
        ebits, mbits, bias = OFP_FORMATS[fmt]
        sign = 1 << (ebits + mbits) if math.copysign(1.0, value) < 0 else 0
        if value == 0:
            return sign
        exponent = max(math.frexp(abs(value))[1] - 1, 1 - bias)
        significand = abs(value) / 2.0 ** (exponent - mbits)
        assert significand.is_integer(), f"{value} is not exact in {fmt}"
        biased = exponent + bias if significand >= 2**mbits else 0
        assert biased < 2**ebits, f"{value} is out of range for {fmt}"
        return sign | (biased << mbits) | (int(significand) & (2**mbits - 1))
    if fmt == "bf16":
        return int.from_bytes(struct.pack("<f", value), "little") >> 16
    width = int(fmt[2:])
    return int.from_bytes(struct.pack(FP_PACK[width], value), "little")


def ime_type_extensions(test_data: TestData) -> list[str]:
    """
    Return the type extensions of a row. A microscaling extension Zvvx<type> or Zvvxn<type> is returned as the
    unscaled extension Zvv<type> with the same input and C formats.
    """
    extensions = []
    for ext in test_data.config.extra_extensions:
        prefix = next((prefix for prefix in ("Zvvxn", "Zvvx") if ext.startswith(prefix)), None)
        extensions.append("Zvv" + ext.removeprefix(prefix) if prefix else ext)
    return extensions


def mx_block_size_16(test_data: TestData) -> bool:
    """Return True for a Zvvxn* row, which tests block size 16 (vtype.bs = 1). Zvvx* rows test block size 32."""
    return any(ext.startswith("Zvvxn") for ext in test_data.config.extra_extensions)


def fp_input_format(test_data: TestData, sew: int, w: int) -> str:
    """
    Return the input format family of a row from its type extension: ofp4 for Zvvofp4*, ofp8 for Zvvofp8*, i4 or i8
    for the integer inputs of Zvvxi4* and Zvvxi8*, bf16 when the extension names bf16 as input, else IEEE at SEW/W
    bits.
    """
    extensions = ime_type_extensions(test_data)
    for ext in extensions:
        if ext.startswith(("Zvvofp4", "Zvvofp8")):
            return ext[3:7]
        if ext.startswith(("Zvvi4", "Zvvi8")):
            return ext[3:5]
    if any("bf16" in ext for ext in extensions):
        return "bf16"
    return f"fp{sew // w}"


def fp_operand_format(input_family: str, altfmt: bool) -> str:
    """Return the format of one input operand. For OFP8, its altfmt_A or altfmt_B bit selects E5M2 over E4M3."""
    if input_family == "ofp8":
        return "e5m2" if altfmt else "e4m3"
    if input_family == "ofp4":
        return "e2m1"
    return input_family


def fp_output_format(test_data: TestData, sew: int) -> str:
    """Return the C format of a row: bf16 when its type extension ends in bf16mm (Zvv<in>bf16mm), else fp<SEW>."""
    if any(ext.endswith("bf16mm") for ext in ime_type_extensions(test_data)):
        return "bf16"
    return f"fp{sew}"


def fp_c_range(output_fmt: str) -> int:
    """Largest |k| of a C value k + 0.5. A BF16 C has 8 significant bits, so the C range and the input range shrink."""
    return 31 if output_fmt == "bf16" else 128


def fp_exact_data(
    test_data: TestData,
    reg: str,
    sew: int,
    w: int,
    input_fmt: str,
    output_fmt: str,
    emul: float,
    background: float | None = None,
    mx: bool = False,
) -> str:
    """
    Return a label of SEW-wide storage elements that fills emul registers at IME_VLEN_MAX with exact FP data. The
    label is registered once per instruction and shared by every testcase with the same arguments.

    A and B inputs are sparse integers in [-2, 2], packed W per storage element. C holds half-integers k + 0.5 with
    |k| <= 128, so no C value is ever zero. The bounds below hold for every value of the random data.

    A dot product has lambda*W*LMUL terms. Up to IME_VLEN_MAX, lambda*LMUL is at most 256 at SEW=16, the only SEW of
    an FP16 or BF16 C. A widening row with an FP16 or BF16 C puts at most one nonzero input in each storage element.
    For an FP16 or BF16 C, only the storage elements whose index is a multiple of NONZERO_STRIDE hold nonzero inputs.
    Register r of A holds row i in the storage elements r*M*lambda + i*lambda + t, 0 <= t < lambda. A row then has at
    most lambda*LMUL/stride nonzero storage elements when lambda >= stride, and at most LMUL when lambda < stride.

    - FP16 C: stride 2, so a dot product has at most 128 nonzero products, each at most 4 in magnitude. Every running
      sum stays below 512 + 128.5 < 1024, where fp16 resolves 0.5.
    - BF16 C: the inputs are in [-1, 1], |k| <= 31 and the stride is 4, so a dot product has at most 64 nonzero
      products of magnitude 1. Every running sum stays below 64 + 31.5 < 128, where bf16 resolves 0.5.
    - FP32 and FP64 C: at most 1024 products of magnitude 4, so every running sum stays below 2^14, also with mx.

    With mx set (microscaled rows), the random block scales multiply each partial sum by 2^-1, 2^0 or 2^1, so every
    value is a multiple of 0.5. The stride doubles: an FP16 C sum stays below 64*4*2 + 128.5 < 1024, and a BF16 C
    sum below 32*2 + 31.5 < 128.

    Every value is therefore exact in fp16, bf16 (inputs only), fp32 and fp64, in every order of summation. Integers
    in [-2, 2] are exact in E4M3, E5M2 and E2M1.

    With background set, every input element (or every C element) holds that value instead.
    """
    count = int(IME_VLEN_MAX * emul) // sew
    background_name = "" if background is None else "_bg" + str(background).replace("-", "m").replace(".", "p")
    label = f"{reg}_fp_{input_fmt}_{output_fmt}_w{w}_e{sew}_n{count}{background_name}{'_mx' if mx else ''}"
    if label in test_data.vector_labels:
        return label
    lane_bits = sew // w
    c_range = fp_c_range(output_fmt)
    input_range = 1 if output_fmt == "bf16" else 2
    one_lane = w > 1 and output_fmt in ("fp16", "bf16")
    stride = NONZERO_STRIDE.get(output_fmt, 1) * (2 if mx and output_fmt in NONZERO_STRIDE else 1)
    elements = []
    for index in range(count):
        if reg == "vd":
            value = background if background is not None else random_range(-c_range, c_range) + 0.5
            elements.append(fp_bits(value, output_fmt))
        else:
            if background is not None:
                lanes = [background] * w
            elif index % stride:
                lanes = [0] * w
            elif one_lane:
                lanes = [0.0] * w
                lane = random_range(0, w - 1)
                lanes[lane] = random_range(-input_range, input_range) if random_range(0, 3) == 0 else 0
            else:
                lanes = [random_range(-input_range, input_range) if random_range(0, 3) == 0 else 0 for _ in range(w)]
            elements.append(sum(fp_bits(float(v), input_fmt) << (i * lane_bits) for i, v in enumerate(lanes)))
    test_data.register_vector_data(label, sew, elements=elements)
    return label


def fp_edge_data(
    test_data: TestData, reg: str, edge_label: str, sew: int, w: int, input_fmt: str, output_fmt: str, emul: float
) -> tuple[str, str]:
    """
    Return the background and head labels for reg with the edge value of edge_label in input element 0 (C element 0
    for vd). An A or B edge has a background of 0, a C edge a background of exact random C values. The head is
    storage element 0 of the background with the edge value in its first lane.
    """
    elements, _ = test_data.vector_labels[edge_label]
    lane_bits = sew // w if reg != "vd" else sew
    label = fp_exact_data(test_data, reg, sew, w, input_fmt, output_fmt, emul, background=None if reg == "vd" else 0.0)
    data, _ = test_data.vector_labels[label]
    mask = (1 << lane_bits) - 1
    head = f"{reg}_fp_edge_ime_{test_data.test_count:03d}"
    test_data.register_vector_data(head, sew, elements=[(data[0] & ~mask) | (elements[0] & mask)])
    return label, head


def mx_scale_data(
    test_data: TestData,
    scale_a: int | None = None,
    scale_b: int | None = None,
    first: tuple[int, int] | None = None,
    label: str | None = None,
) -> str:
    """
    Register a label of paired E8M0 scales that fills v0 at IME_VLEN_MAX. Every scale_A is scale_a and every scale_B
    is scale_b. A scale left as None is a random choice of RANDOM_SCALES_A or RANDOM_SCALES_B for each element. first
    replaces the (scale_A, scale_B) pair of element 0: row 0 of A and column 0 of B^T in block 0. Without first and
    label, every testcase with the same scale_a and scale_b shares one label.
    """
    if first is None and label is None:
        label = "v0_scale_ime_" + "_".join("r" if scale is None else str(scale) for scale in (scale_a, scale_b))
        if label in test_data.vector_labels:
            return label
    pairs = [
        (
            scale_a if scale_a is not None else RANDOM_SCALES_A[random_range(0, 1)],
            scale_b if scale_b is not None else RANDOM_SCALES_B[random_range(0, 1)],
        )
        for _ in range(IME_VLEN_MAX // SCALE_PAIR_BITS)
    ]
    if first is not None:
        pairs[0] = first
    label = label or f"v0_scale_ime_{test_data.test_count:03d}"
    test_data.register_vector_data(label, SCALE_PAIR_BITS, elements=[a | (b << 8) for a, b in pairs])
    return label


@add_instruction_formatter("FMMACC", fmmacc_config)
def format_fmmacc(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_fp_mmacc(instr_str, test_data, params, mx=False)


@add_instruction_formatter("FMMACC_MX", fmmacc_mx_config)
def format_fmmacc_mx(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """
    Microscaled multiply-accumulate (vm=0) with block size 32 for a Zvvx* row and 16 for a Zvvxn* row. Random data
    gets random block scales (see fp_exact_data). Edge values and the data of cp_fp_subdot and cp_fp_rnd get unit
    scales, so their results are the unscaled results. cp_scale builds its own scales.
    """
    return format_fp_mmacc(instr_str, test_data, params, mx=True)


def format_fp_mmacc(
    instr_str: str, test_data: TestData, params: InstructionParams, *, mx: bool
) -> tuple[list[str], list[str], list[str]]:
    assert params.sew is not None and params.lmul is not None, "sew and lmul must be provided for FMMACC"
    assert params.csr_frm_val is not None, "FMMACC tests run with a dynamic rounding mode"
    w = WIDENING[instr_str]
    input_family = fp_input_format(test_data, params.sew, w)
    output_fmt = fp_output_format(test_data, params.sew)

    # BF16 inputs are selected by altfmt_A = altfmt_B = 1, a BF16 C by altfmt = 1. For OFP8 inputs, the coverpoint
    # chooses altfmt_A and altfmt_B (E4M3 = 0, E5M2 = 1). OFP4 inputs require altfmt_A = altfmt_B = 0.
    if input_family != "ofp8":
        params.altfmt_a = params.altfmt_b = input_family == "bf16"
    params.altfmt = output_fmt == "bf16"
    input_fmts = {
        "vs1": fp_operand_format(input_family, params.altfmt_a),
        "vs2": fp_operand_format(input_family, params.altfmt_b),
        "vd": output_fmt,
    }
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
    nv_preset = any(NV_PRESET_EDGE in (getattr(params, f"{reg}_val_pointer") or "") for reg in ("vs1", "vs2"))
    dedicated = edge_reg is not None or any(
        tag in (getattr(params, f"{reg}_val_pointer") or "") for reg in ("vs1", "vs2") for tag in DEDICATED_DATA_TAGS
    )
    if mx:
        assert not (dedicated and params.vs1 == params.vs2), "A and B with dedicated data need separate registers"
        params.bs = mx_block_size_16(test_data)
        if params.scale_val_pointer is None:
            unit = None if not dedicated else E8M0_BIAS
            params.scale_val_pointer = mx_scale_data(test_data, scale_a=unit, scale_b=unit)
    backgrounds: dict[str, float | None] = {"vs1": None, "vs2": None, "vd": None}
    heads: dict[str, str] = {}
    if edge_reg == "vd":
        backgrounds["vs1"] = backgrounds["vs2"] = 0.0
    elif edge_reg is not None:
        backgrounds["vs2" if edge_reg == "vs1" else "vs1"] = 1.0
    for reg, emul in (("vs1", params.lmul), ("vs2", params.lmul), ("vd", C_WINDOW_REGS)):
        if any(tag in (getattr(params, f"{reg}_val_pointer") or "") for tag in DEDICATED_DATA_TAGS):
            continue  # cp_fp_subdot, cp_fp_rnd and cp_scale build complete data
        input_fmt = input_fmts[reg]
        if reg == edge_reg:
            label, heads[reg] = fp_edge_data(
                test_data, reg, getattr(params, f"{reg}_val_pointer"), params.sew, w, input_fmt, output_fmt, emul
            )
        else:
            label = fp_exact_data(
                test_data, reg, params.sew, w, input_fmt, output_fmt, emul, background=backgrounds[reg], mx=mx
            )
        setattr(params, f"{reg}_val_pointer", label)
    if params.vs1 == params.vs2:
        params.vs2_val_pointer = params.vs1_val_pointer  # A and B share one register and its data
    params.vector_suite = "length"

    setup, test, check = mmacc_code(instr_str, test_data, params, scale_label=params.scale_val_pointer, heads=heads)
    handle_vector_fp(setup, check, params.csr_frm_val, test_data)
    if nv_preset:
        # The specification does not say whether an E5M2 NaN can be signaling. With NV already set, fflags and the
        # canonical NaN result are the same either way.
        setup[setup.index("fsflagsi 0b00000 # clear all fflags")] = "fsflagsi 0b10000 # set only NV"
    return setup, test, check


@add_instruction_formatter("MMACC", mmacc_config)
def format_mmacc(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return mmacc_code(instr_str, test_data, params)


def mmacc_code(
    instr_str: str,
    test_data: TestData,
    params: InstructionParams,
    *,
    scale_label: str | None = None,
    heads: dict[str, str] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    """
    Load A, B and the C window, run the multiply-accumulate and check the C window. With scale_label, v0 holds those
    block scales and the instruction has vm=0. heads maps vs1, vs2 or vd to a label whose one storage element is
    written over element 0 of that operand after its data is loaded.
    """
    heads = dict(heads or {})
    assert params.vs1 is not None and params.vs1_val_pointer is not None, "vs1 must be provided for MMACC"
    assert params.vs2 is not None and params.vs2_val_pointer is not None, "vs2 must be provided for MMACC"
    assert params.vd is not None and params.vd_val_pointer is not None, "vd must be provided for MMACC"
    assert params.temp_reg is not None, "temp_reg must be provided for MMACC"
    assert params.sew is not None, "sew must be provided for MMACC"
    assert params.lmul is not None, "lmul must be provided for MMACC"
    assert params.maskval is None, "MMACC instructions are not maskable"
    assert test_data.test_chunk is not None, "format_mmacc must be used with an active TestChunk"

    # Every MMACC testcase checks the whole C window. Base-suite callers pass VL=1 and register short data labels
    # (one element, or one edge value at the input width). They run at VL=VLMAX with shared background data in A, B
    # and the C window, and their labels are written over element 0.
    if params.vector_suite == "base":
        params.vl = "vlmax"
        for reg, emul in (("vs1", params.lmul), ("vs2", params.lmul), ("vd", C_WINDOW_REGS)):
            label = getattr(params, f"{reg}_val_pointer")
            background, heads[reg] = ime_extend_label(test_data, label, reg, params.sew, emul)
            setattr(params, f"{reg}_val_pointer", background)

    # A preset vd reserves only its first register, so reserve the whole window before temporaries are taken
    test_data.vec_regs.allocate_operand("vd", params.vd, C_WINDOW_REGS, suppress_overlap=True)

    labels = [params.vs1_val_pointer, params.vs2_val_pointer, params.vd_val_pointer, *heads.values()]
    if scale_label is not None:
        labels.append(scale_label)
    test_data.test_chunk.vector_labels.extend(
        (label, *test_data.vector_labels[label]) for label in dict.fromkeys(labels)
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
    ]
    if "vd" in heads:
        setup.extend(ime_overlay(params.vd, heads["vd"], params.sew, params.temp_reg))
    setup.append(f"# A (vs1 = v{params.vs1}) and B (vs2 = v{params.vs2}) at LMUL={params.lmul}, VL=VLMAX")
    test_data.int_regs.return_register(stride_reg)

    # A and B are loaded at VLMAX whatever the test VL is. load_ime_vtype sets the test VL.
    load_code, _ = load_vec_regs([VectorLoad(reg="vs1"), VectorLoad(reg="vs2")], replace(params, vl="vlmax"), test_data)
    setup.extend(load_code)
    for reg in ("vs1", "vs2"):
        if reg in heads:
            setup.extend(ime_overlay(getattr(params, reg), heads[reg], params.sew, params.temp_reg))
    if scale_label is not None:
        setup.extend(
            [
                "# v0: paired E8M0 block scales, scale_A in bits 7:0 and scale_B in bits 15:8 of each element",
                f"vsetvli x{params.temp_reg}, x0, e{SCALE_PAIR_BITS}, m1, tu, mu",
                f"LA (x{params.temp_reg}, {scale_label})",
                f"vle{SCALE_PAIR_BITS}.v v0, (x{params.temp_reg})",
            ]
        )
    setup.extend(load_ime_vtype(params, test_data))

    scale_operand = ", v0.scale" if scale_label is not None else ""
    test = [f"{instr_str} v{params.vd}, v{params.vs1}, v{params.vs2}{scale_operand}"]

    # Free A and B so that the signature check has room for its temporaries
    test_data.vec_regs.deallocate_operand("vs2")
    test_data.vec_regs.deallocate_operand("vs1")

    check = [
        f"# Check the C window at e{params.sew}, m{C_WINDOW_LMUL}, VL=VLMAX. vta=0, so elements beyond VL are unchanged",
        f"vsetvli x{params.temp_reg}, x0, e{params.sew}, m{C_WINDOW_LMUL}, tu, mu",
        *write_sigupd_v_len(test_data, params, C_WINDOW_LMUL, segments=C_WINDOW_SEGMENTS),
    ]

    lambdas = ime_lambdas(params.sew) if params.lambda_ is None else [params.lambda_]
    ime_condition = ime_lambda_condition(params.sew, lambdas)
    if params.ime_guard is not None:
        ime_condition = f"{ime_condition} && {params.ime_guard}"
    handle_parameter_exclusions(params.lmul, setup, check, ime_condition=ime_condition)

    return (setup, test, check)
