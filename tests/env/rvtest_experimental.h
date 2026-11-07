// Experimental RISC-V extensions header
// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
// SPDX-License-Identifier: Apache-2.0
// Contains a macro for each instruction from an unratified RISC-V extension
// so tests can be compiled without requiring the experimental extensions to
// be implemented in the compiler


#ifndef RISCV_ARCH_TEST_EXPERIMENTAL_H
#define RISCV_ARCH_TEST_EXPERIMENTAL_H

#if defined(__ASSEMBLER__) && defined(ENABLE_EXPERIMENTAL_EXTENSIONS)

.macro beqi rs1, cimm, target
  .if \cimm == -1
    .insn b 0x63, 2, \rs1, x0, \target
  .else
    .insn b 0x63, 2, \rs1, x\cimm, \target
  .endif
.endm

.macro bnei rs1, cimm, target
  .if \cimm == -1
    .insn b 0x63, 3, \rs1, x0, \target
  .else
    .insn b 0x63, 3, \rs1, x\cimm, \target
  .endif
.endm

// Integrated Matrix Extension (Zvvm*)
// Encodings follow src/integrated-matrix.adoc in
// https://github.com/riscv/integrated-matrix-extension at commit 6effbcae.
// The operand syntax is the syntax that GNU as accepts. GNU as names the W=4
// instructions vqwmmacc.vv, vfqwmmacc.vv and vfqwimmacc.vv. The specification
// names them vqmmacc.vv, vfqmmacc.vv and vfqimmacc.vv. Both names are defined.

// Set \sym to the number of vector register \reg.
.macro _rvtest_ime_vreg sym, reg
  .set \sym, -1
  .irp n, 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31
    .ifc \reg, v\n
      .set \sym, \n
    .endif
  .endr
  .if \sym < 0
    .error "invalid vector register: \reg"
  .endif
.endm

// OP-V multiply-accumulate: vd, vs1, vs2 with fixed funct6 and funct3.
.macro _rvtest_ime_mmacc funct6, funct3, vm, vd, vs1, vs2
  _rvtest_ime_vreg .Lrvtest_ime_vd, \vd
  _rvtest_ime_vreg .Lrvtest_ime_vs1, \vs1
  _rvtest_ime_vreg .Lrvtest_ime_vs2, \vs2
  .insn 4, (\funct6 << 26) | (\vm << 25) | (.Lrvtest_ime_vs2 << 20) | (.Lrvtest_ime_vs1 << 15) | (\funct3 << 12) | (.Lrvtest_ime_vd << 7) | 0x57
.endm

// Multiply-accumulate with an optional "v0.scale" operand. v0.scale encodes vm=0.
.macro _rvtest_ime_mmacc_mx funct6, funct3, vd, vs1, vs2, scale
  .ifb \scale
    _rvtest_ime_mmacc \funct6, \funct3, 1, \vd, \vs1, \vs2
  .else
    .ifc \scale, v0.scale
      _rvtest_ime_mmacc \funct6, \funct3, 0, \vd, \vs1, \vs2
    .else
      .error "expected v0.scale: \scale"
    .endif
  .endif
.endm

// OPIVV multiply-accumulate with vm=0 and an optional "v0.scale" operand.
.macro _rvtest_ime_mmacc_imx funct6, vd, vs1, vs2, scale
  .ifnb \scale
    .ifnc \scale, v0.scale
      .error "expected v0.scale: \scale"
    .endif
  .endif
  _rvtest_ime_mmacc \funct6, 0, 0, \vd, \vs1, \vs2
.endm

// Set .Lrvtest_ime_lambda to the lambda[2:0] encoding of the operand L1 ... L64.
.macro _rvtest_ime_lambda opt
  .set .Lrvtest_ime_lambda, 0
  .ifc \opt, L1
    .set .Lrvtest_ime_lambda, 1
  .endif
  .ifc \opt, L2
    .set .Lrvtest_ime_lambda, 2
  .endif
  .ifc \opt, L4
    .set .Lrvtest_ime_lambda, 3
  .endif
  .ifc \opt, L8
    .set .Lrvtest_ime_lambda, 4
  .endif
  .ifc \opt, L16
    .set .Lrvtest_ime_lambda, 5
  .endif
  .ifc \opt, L32
    .set .Lrvtest_ime_lambda, 6
  .endif
  .ifc \opt, L64
    .set .Lrvtest_ime_lambda, 7
  .endif
  .if .Lrvtest_ime_lambda == 0
    .error "expected L1, L2, L4, L8, L16, L32, L64 or v0.t: \opt"
  .endif
.endm

// Tile load or store: vd/vs3, (rs1), rs2 [, L<lambda>] [, v0.t].
// Bits 31:29 hold lambda, bit 28 is 1, bits 27:26 hold the mode and bit 25 holds vm.
// The S-type form places bits 31:25 and bits 11:7 in its immediate.
.macro _rvtest_ime_tile opcode, mode, vd, rs1, rs2, opt1, opt2
  _rvtest_ime_vreg .Lrvtest_ime_vd, \vd
  .set .Lrvtest_ime_lambda, 0
  .set .Lrvtest_ime_vm, 1
  .ifnb \opt1
    .ifc \opt1, v0.t
      .set .Lrvtest_ime_vm, 0
      .ifnb \opt2
        .error "unexpected operand after v0.t: \opt2"
      .endif
    .else
      _rvtest_ime_lambda \opt1
      .ifnb \opt2
        .ifc \opt2, v0.t
          .set .Lrvtest_ime_vm, 0
        .else
          .error "expected v0.t: \opt2"
        .endif
      .endif
    .endif
  .endif
  .set .Lrvtest_ime_f7, (.Lrvtest_ime_lambda << 4) | (1 << 3) | (\mode << 1) | .Lrvtest_ime_vm
  .set .Lrvtest_ime_imm, (((.Lrvtest_ime_f7 << 5) | .Lrvtest_ime_vd) ^ 0x800) - 0x800
  .insn s \opcode, 7, \rs2, .Lrvtest_ime_imm\rs1
.endm

// Zvvmtls
.macro vmtl.v vd, rs1, rs2, opt1, opt2
  _rvtest_ime_tile 0x07, 0, \vd, \rs1, \rs2, \opt1, \opt2
.endm

.macro vmts.v vs3, rs1, rs2, opt1, opt2
  _rvtest_ime_tile 0x27, 0, \vs3, \rs1, \rs2, \opt1, \opt2
.endm

// Zvvmttls
.macro vmttl.v vd, rs1, rs2, opt1, opt2
  _rvtest_ime_tile 0x07, 1, \vd, \rs1, \rs2, \opt1, \opt2
.endm

.macro vmtts.v vs3, rs1, rs2, opt1, opt2
  _rvtest_ime_tile 0x27, 1, \vs3, \rs1, \rs2, \opt1, \opt2
.endm

// Zvvmm: OPIVV with vm=1
.macro vmmacc.vv vd, vs1, vs2
  _rvtest_ime_mmacc 0x38, 0, 1, \vd, \vs1, \vs2
.endm

.macro vwmmacc.vv vd, vs1, vs2
  _rvtest_ime_mmacc 0x39, 0, 1, \vd, \vs1, \vs2
.endm

.macro vqmmacc.vv vd, vs1, vs2
  _rvtest_ime_mmacc 0x3a, 0, 1, \vd, \vs1, \vs2
.endm

.macro vqwmmacc.vv vd, vs1, vs2
  vqmmacc.vv \vd, \vs1, \vs2
.endm

.macro v8wmmacc.vv vd, vs1, vs2
  _rvtest_ime_mmacc 0x3b, 0, 1, \vd, \vs1, \vs2
.endm

// Zvvfmm: OPFVV. vfmmacc.vv has no microscaled form.
.macro vfmmacc.vv vd, vs1, vs2
  _rvtest_ime_mmacc 0x14, 1, 1, \vd, \vs1, \vs2
.endm

.macro vfwmmacc.vv vd, vs1, vs2, scale
  _rvtest_ime_mmacc_mx 0x15, 1, \vd, \vs1, \vs2, \scale
.endm

.macro vfqmmacc.vv vd, vs1, vs2, scale
  _rvtest_ime_mmacc_mx 0x16, 1, \vd, \vs1, \vs2, \scale
.endm

.macro vfqwmmacc.vv vd, vs1, vs2, scale
  vfqmmacc.vv \vd, \vs1, \vs2, \scale
.endm

.macro vf8wmmacc.vv vd, vs1, vs2, scale
  _rvtest_ime_mmacc_mx 0x17, 1, \vd, \vs1, \vs2, \scale
.endm

// Integer-input microscaled forms: OPIVV with vm=0. The scales are always in v0.
// The specification writes a "v0.scale" operand. GNU as rejects it, so it is optional.
.macro vfwimmacc.vv vd, vs1, vs2, scale
  _rvtest_ime_mmacc_imx 0x39, \vd, \vs1, \vs2, \scale
.endm

.macro vfqimmacc.vv vd, vs1, vs2, scale
  _rvtest_ime_mmacc_imx 0x3a, \vd, \vs1, \vs2, \scale
.endm

.macro vfqwimmacc.vv vd, vs1, vs2, scale
  vfqimmacc.vv \vd, \vs1, \vs2, \scale
.endm

.macro vf8wimmacc.vv vd, vs1, vs2, scale
  _rvtest_ime_mmacc_imx 0x3b, \vd, \vs1, \vs2, \scale
.endm

#endif

#endif
