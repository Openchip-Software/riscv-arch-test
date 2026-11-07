##################################
# cp_custom_tile_macc.py
#
# Integrated Matrix Extension multiply-accumulate with tile-loaded A and B and a tile-stored C.
# constantino.gomez@openchip.com October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from dataclasses import replace

from testgen.asm.vector_helpers import (
    handle_parameter_exclusions,
    ime_lambda_condition,
    ime_lambdas,
    ime_vtype_value,
    load_ime_vtype,
    write_sigupd_v_len,
)
from testgen.constants import VLEN_MAX
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

IME_LMULS = [1, 2, 4, 8]
UDB_VLENS = [128, 256, 512, 1024]
A_REG, B_REG, C_REG = 0, 8, 16
C_WINDOW_REGS = 16


def tile_macc_data(sew: int, lambda_value: int, lmul: int) -> tuple[list[int], list[int]]:
    """
    Return the A and B tiles in memory, row-major with LD = K = lambda*LMUL, for M rows at VLEN_MAX.
    With K >= 2: A[i] = (i, 1, 0, ...) and B_tile[j] = (f, j, 0, ...), so C[i][j] = f*i + j names its row and column.
    f is 256, or 16 at SEW=8. With K = 1: A[i] = 1 and B_tile[j] = j, so C[i][j] = j.
    """
    k = lambda_value * lmul
    rows = VLEN_MAX // (sew * lambda_value)
    mask = (1 << sew) - 1
    factor = 256 if sew >= 16 else 16
    a = [0] * (rows * k)
    b = [0] * (rows * k)
    for i in range(rows):
        if k == 1:
            a[i] = 1
            b[i] = i & mask
        else:
            a[i * k], a[i * k + 1] = i & mask, 1
            b[i * k], b[i * k + 1] = factor & mask, i & mask
    return a, b


@add_coverpoint_generator("cp_custom_tile_macc")
def make_tile_macc(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    vmmacc.vv with A and B loaded by vmtl.v at the tile LMUL with the natural LD, and C stored by vmts.v.

    C is zeroed, A and B come from memory, and the C tile is stored at LMUL = EMUL_C = VLEN/(SEW*lambda^2) with
    LD = M. EMUL_C depends on VLEN, so an #if chain over UDB_VLEN selects the store. EMUL_C = 16 is stored as two
    LMUL=8 halves: the second half holds the next 8*lambda columns of each row. The check reads back 16 registers of
    memory from the C destination.
    """
    assert test_data.config.sew is not None, "SEW must be set for vector tests"
    sew = test_data.config.sew
    xlen = test_data.xlen

    out_label = f"ime_tile_macc_c_e{sew}"
    if out_label not in test_data.vector_labels:
        test_data.register_vector_data(out_label, sew, random_elements=C_WINDOW_REGS * VLEN_MAX // sew)

    test_chunks = []
    for lambda_value in ime_lambdas(sew):
        for lmul in IME_LMULS:
            a, b = tile_macc_data(sew, lambda_value, lmul)
            a_label = f"ime_tile_macc_a_e{sew}_l{lambda_value}_m{lmul}"
            b_label = f"ime_tile_macc_b_e{sew}_l{lambda_value}_m{lmul}"
            test_data.register_vector_data(a_label, sew, elements=a)
            test_data.register_vector_data(b_label, sew, elements=b)

            tc = test_data.begin_test_chunk()
            tc.code.append(f"# Testcase cp_custom_tile_macc (Test lambda = {lambda_value}, lmul = {lmul})")
            label_line = test_data.add_testcase(f"lmul{lmul}_lambda{lambda_value}", coverpoint)
            for label in (a_label, b_label, out_label):
                tc.vector_labels.append((label, *test_data.vector_labels[label]))

            # A, B and C use fixed register groups. The C window is reused for the read-back.
            test_data.vec_regs.consume_registers(list(range(32)))
            temp_reg, addr_reg, ld_reg, vtype_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])
            params = InstructionParams(
                sew=sew, lmul=lmul, lambda_=lambda_value, vl="vlmax", ta=False, ma=False, temp_reg=temp_reg
            )

            setup = [
                f"# Zero the C window v{C_REG}-v{C_REG + C_WINDOW_REGS - 1}",
                f"vsetvli x{temp_reg}, x0, e{sew}, m8, tu, mu",
                f"vmv.v.i v{C_REG}, 0",
                f"vmv.v.i v{C_REG + 8}, 0",
                *load_ime_vtype(params, test_data),
                f"# A (v{A_REG}) and B (v{B_REG}) by tile loads with the natural LD",
                f"LA (x{addr_reg}, {a_label})",
                f"vmtl.v v{A_REG}, (x{addr_reg}), x0",
                f"LA (x{addr_reg}, {b_label})",
                f"vmtl.v v{B_REG}, (x{addr_reg}), x0",
            ]
            test = [label_line, f"{instr_name} v{C_REG}, v{A_REG}, v{B_REG}"]

            check = ["# Store C at LMUL = EMUL_C = VLEN/(SEW*lambda^2) with LD = M = lambda*EMUL_C"]
            branches = [vlen for vlen in UDB_VLENS if sew * lambda_value * lambda_value <= vlen]
            for i, vlen in enumerate(branches):
                emul_c = vlen // (sew * lambda_value * lambda_value)
                check.append(f"{'#if' if i == 0 else '#elif'} UDB_VLEN == {vlen}")
                store_lmul = min(emul_c, 8)
                vtype = ime_vtype_value(replace(params, lmul=store_lmul), lambda_value, xlen)
                assert isinstance(vtype, int), "unprivileged tests know XLEN"
                check.extend(
                    [
                        f"LI(x{vtype_reg}, {vtype:#x})",
                        f"vsetvl x{temp_reg}, x0, x{vtype_reg}",
                        f"LA (x{addr_reg}, {out_label})",
                    ]
                )
                if emul_c <= 8:
                    check.append(f"vmts.v v{C_REG}, (x{addr_reg}), x0")
                else:
                    half_offset = 8 * lambda_value * sew // 8
                    check.extend(
                        [
                            f"# EMUL_C = 16: two LMUL=8 halves, LD = {lambda_value * emul_c}",
                            f"LI(x{ld_reg}, {lambda_value * emul_c})",
                            f"vmts.v v{C_REG}, (x{addr_reg}), x{ld_reg}",
                            f"addi x{addr_reg}, x{addr_reg}, {half_offset}",
                            f"vmts.v v{C_REG + 8}, (x{addr_reg}), x{ld_reg}",
                        ]
                    )
            check.append("#endif")
            check.extend(
                [
                    f"# Read back 16 registers of memory from {out_label}",
                    f"vsetvli x{temp_reg}, x0, e{sew}, m8, tu, mu",
                    f"LA (x{addr_reg}, {out_label})",
                    f"vle{sew}.v v{C_REG}, (x{addr_reg})",
                    f"csrr x{ld_reg}, vlenb",
                    f"slli x{ld_reg}, x{ld_reg}, 3",
                    f"add x{addr_reg}, x{addr_reg}, x{ld_reg}",
                    f"vle{sew}.v v{C_REG + 8}, (x{addr_reg})",
                ]
            )
            test_data.vec_regs.return_registers(list(range(C_REG)))
            check.extend(write_sigupd_v_len(test_data, replace(params, vd=C_REG), 8, segments=2))
            test_data.vec_regs.return_registers(list(range(C_REG, 32)))
            test_data.int_regs.return_registers([temp_reg, addr_reg, ld_reg, vtype_reg])

            handle_parameter_exclusions(lmul, setup, check, ime_condition=ime_lambda_condition(sew, [lambda_value]))
            tc.code.extend(["\n".join(setup), "\n".join(test), "\n".join(check)])
            test_chunks.append(test_data.end_test_chunk())

    return test_chunks
