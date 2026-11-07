##################################
# tile_type.py
#
# Integrated Matrix Extension tile loads (vmtl.v, vmttl.v) and tile stores (vmts.v, vmtts.v).
# constantino.gomez@openchip.com October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from dataclasses import replace
from typing import Literal

from testgen.asm.helpers import write_sigupd
from testgen.asm.vector_helpers import (
    VectorLoad,
    handle_parameter_exclusions,
    ime_extend_label,
    ime_lambda_condition,
    ime_lambdas,
    load_ime_vtype,
    load_vec_regs,
    prep_mask_v,
    write_sigupd_v_len,
)
from testgen.constants import VLEN_MAX
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter

# The spec requires only that a masked tile load does not write v0 (spec: tile load/store legality rules)
vlt_config = InstructionTypeConfig(
    required_params={"vd", "rs1", "rs2"},
    instruction_class=["load"],
    vector_data=VectorTypeConfig(masked_constraints={("vd", "v0")}),
)
vst_config = InstructionTypeConfig(
    required_params={"vs3", "rs1", "rs2"},
    instruction_class=["store"],
    vector_data=VectorTypeConfig(),
)

# Every LD is at most 2*linesize, so a tile with VL <= VLMAX spans less than 2*LMUL*VLEN/8 bytes from rs1.
# One data label per SEW covers that span at LMUL=8 and VLEN=VLEN_MAX.
TILE_SPAN_REGS = 16


def tile_data_label(test_data: TestData, sew: int) -> str:
    """Register the data label that every tile load and store of this SEW reads or writes."""
    label = f"ime_tile_data_e{sew}"
    if label not in test_data.vector_labels:
        test_data.register_vector_data(label, sew, random_elements=TILE_SPAN_REGS * VLEN_MAX // sew)
    return label


# The transposing instructions of Zvvmttls. Their natural LD is M, the row count, instead of linesize.
TRANSPOSING = ("vmttl.v", "vmtts.v")


def tile_ld_value(ld: str, line_lambda: int, lmul: int) -> int:
    """
    Return the LD value in elements that rs2 holds for vmtl.v and vmts.v. linesize = lambda*LMUL, which is also their
    natural LD. "zero" puts 0 in a register other than x0: the specification then selects the natural LD. LD of a
    transposing instruction is computed at run time instead (tight = M, padded = M + 1, double = 2*M).
    """
    linesize = line_lambda * lmul
    return {"zero": 0, "tight": linesize, "padded": linesize + 1, "double": 2 * linesize}[ld]


def tile_operands(params: InstructionParams, reg: int) -> str:
    """Return the operands of a tile load or store: register group, base, LD, immediate lambda and mask."""
    operands = f"v{reg}, (x{params.rs1}), x{params.rs2}"
    if params.imm_lambda is not None:
        operands += f", L{params.imm_lambda}"
    if params.maskval is not None:
        operands += ", v0.t"
    return operands


def tile_setup(
    instr_str: str, test_data: TestData, params: InstructionParams, data_reg: Literal["vd", "vs3"]
) -> tuple[list[str], list[int], str]:
    """
    Emit the setup shared by tile loads and stores: mask, the register group loaded at VLMAX, rs1, LD and vtype.
    Return the setup lines, the background lambdas of the preprocessor chain, and the lambda gate.
    """
    assert params.sew is not None and params.lmul is not None and params.rs1 is not None and params.rs2 is not None
    assert test_data.test_chunk is not None, f"format of {instr_str} must be used with an active TestChunk"
    sew = params.sew
    lmul = int(params.lmul)

    # Base-suite callers pass VL=1 and one-element data labels. They run at VL=VLMAX with a full register group.
    if params.vector_suite == "base":
        params.vl = "vlmax"
        label = getattr(params, f"{data_reg}_val_pointer")
        setattr(params, f"{data_reg}_val_pointer", ime_extend_label(test_data, label, data_reg, sew, lmul))
    ld = params.ld or "padded"

    data_label = tile_data_label(test_data, sew)
    reg_label = getattr(params, f"{data_reg}_val_pointer")
    test_data.test_chunk.vector_labels.extend(
        [(data_label, *test_data.vector_labels[data_label]), (reg_label, *test_data.vector_labels[reg_label])]
    )

    # An immediate lambda sets the line size. vtype.lambda then takes a different supported value, so the test
    # also shows that the immediate overrides vtype.
    if params.imm_lambda is not None:
        background = [value for value in ime_lambdas(sew) if value != params.imm_lambda]
        condition = f"{ime_lambda_condition(sew, [params.imm_lambda])} && {ime_lambda_condition(sew, background)}"
    else:
        background = ime_lambdas(sew) if params.lambda_ is None else [params.lambda_]
        condition = ime_lambda_condition(sew, background)

    setup: list[str] = []
    if params.maskval is not None:
        setup.extend(prep_mask_v(params.maskval, test_data, params))
    load_code, _ = load_vec_regs([VectorLoad(reg=data_reg)], replace(params, vl="vlmax"), test_data)
    setup.extend(load_code)
    setup.append(f"LA (x{params.rs1}, {data_label})")

    # The natural LD of a transposing tile instruction is M = VLEN/(SEW*lambda), which depends on VLEN. Each lambda
    # branch loads log2(SEW*lambda/8) into rs2, and M = vlenb >> rs2 is computed after vtype is set.
    transposed = instr_str in TRANSPOSING
    runtime_ld = transposed and params.rs2 != 0 and ld != "zero"

    def ld_loads(line_lambda: int) -> list[tuple[int, int]]:
        assert params.rs2 is not None
        if params.rs2 == 0:
            return []
        if runtime_ld:
            return [(params.rs2, (sew * line_lambda).bit_length() - 1 - 3)]
        return [(params.rs2, tile_ld_value(ld, line_lambda, lmul))]

    ld_desc = "natural, rs2 = x0" if params.rs2 == 0 else ld
    line = "M = VLEN/(SEW*lambda)" if transposed else "linesize = lambda*LMUL"
    setup.append(f"# LD = {ld_desc}; {line}")
    setup.extend(
        load_ime_vtype(params, test_data, lambdas=background, line_lambda=params.imm_lambda, per_lambda=ld_loads)
    )
    if runtime_ld:
        vlenb_reg = test_data.int_regs.get_register(exclude_regs=[0])
        setup.extend([f"csrr x{vlenb_reg}, vlenb", f"srl x{params.rs2}, x{vlenb_reg}, x{params.rs2}"])
        if ld == "padded":
            setup.append(f"addi x{params.rs2}, x{params.rs2}, 1")
        elif ld == "double":
            setup.append(f"slli x{params.rs2}, x{params.rs2}, 1")
        test_data.int_regs.return_register(vlenb_reg)
    return setup, background, condition


def check_vtype_kept(test_data: TestData, params: InstructionParams) -> list[str]:
    """After an instruction with an immediate lambda, record vtype: the immediate must not change vtype.lambda."""
    if params.imm_lambda is None:
        return []
    vtype_reg = test_data.int_regs.get_register(exclude_regs=[0])
    lines = [
        "# An immediate lambda does not change vtype.lambda",
        f"csrr x{vtype_reg}, vtype",
        write_sigupd(vtype_reg, test_data),
    ]
    test_data.int_regs.return_register(vtype_reg)
    return lines


@add_instruction_formatter("VLT", vlt_config)
def format_vlt(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.vd is not None and params.vd_val_pointer is not None, "vd must be provided for VLT"
    assert params.lmul is not None and params.sew is not None, "lmul and sew must be provided for VLT"

    setup, background, condition = tile_setup(instr_str, test_data, params, "vd")
    test = [f"{instr_str} {tile_operands(params, params.vd)}"]

    # A tile load leaves inactive and tail elements undisturbed whatever vta and vma are. Writing tu, mu with the
    # same VL before the check makes the signature check strict.
    check = [
        *check_vtype_kept(test_data, params),
        *load_ime_vtype(replace(params, ta=False, ma=False), test_data, lambdas=background, keep_vl=True),
        *write_sigupd_v_len(test_data, params, params.lmul),
    ]
    if params.maskval is not None:
        test_data.vec_regs.return_register(0)

    handle_parameter_exclusions(params.lmul, setup, check, ime_condition=condition)
    return setup, test, check


@add_instruction_formatter("VST", vst_config)
def format_vst(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.vs3 is not None and params.vs3_val_pointer is not None, "vs3 must be provided for VST"
    assert params.lmul is not None and params.sew is not None, "lmul and sew must be provided for VST"
    assert params.temp_reg is not None, "temp_reg must be provided for VST"

    setup, _, condition = tile_setup(instr_str, test_data, params, "vs3")
    test = [f"{instr_str} {tile_operands(params, params.vs3)}"]

    # Read back the whole span the store can reach, 2*LMUL registers from rs1. The lines and the gaps between them
    # (which must keep their values) are both checked.
    test_data.vec_regs.deallocate_operand("vs3")
    lmul = int(params.lmul)
    read_lmul = min(2 * lmul, 8)
    segments = 2 if lmul == 8 else 1
    read_reg = test_data.vec_regs.get_register(lmul=read_lmul, segments=segments, exclude_regs=[0])
    stride_reg = test_data.int_regs.get_register(exclude_regs=[0])
    check = [
        *check_vtype_kept(test_data, params),
        f"# Read back {2 * lmul} registers of memory from x{params.rs1}",
        f"vsetvli x{params.temp_reg}, x0, e{params.sew}, m{read_lmul}, tu, mu",
        f"vle{params.sew}.v v{read_reg}, (x{params.rs1})",
    ]
    if segments == 2:
        check.extend(
            [
                f"csrr x{stride_reg}, vlenb",
                f"slli x{stride_reg}, x{stride_reg}, 3",
                f"add x{stride_reg}, x{params.rs1}, x{stride_reg}",
                f"vle{params.sew}.v v{read_reg + 8}, (x{stride_reg})",
            ]
        )
    test_data.int_regs.return_register(stride_reg)
    if params.maskval is not None:
        test_data.vec_regs.return_register(0)
    check.extend(
        write_sigupd_v_len(
            test_data, replace(params, vd=read_reg, maskval=None), read_lmul, segments=segments, check_reg=read_reg
        )
    )
    test_data.vec_regs.return_register(read_reg)

    handle_parameter_exclusions(params.lmul, setup, check, ime_condition=condition)
    return setup, test, check
