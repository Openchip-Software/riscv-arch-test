# IME: tile loads and stores execute when `VL` is not a multiple of λ × `LMUL`

## Summary

The four tile instructions `vmtl.v`, `vmttl.v`, `vmts.v` and `vmtts.v` in `model/extensions/IME/ime_mem_insts.sail` do not check `VL`.
The IME specification requires an illegal-instruction exception when `VL` is not a multiple of `effective_lambda * LMUL`, the tile line size.
Sail executes the instruction instead and transfers the first `VL` tile elements.

The matrix multiply-accumulate instructions in the same file do check `VL` (`unsigned(vl) % storage_K != 0`).

Affected commit: Openchip-Software/sail-riscv `cgomez/0.16-plus-ime` @ [`a545cc41`](https://github.com/Openchip-Software/sail-riscv/tree/a545cc412ba022edae38b87f2caf8f2f54caf1e9).
`fd88fd86` ("Trap masked tile loads with vd = v0") fixed the other legality check that was missing from the tile loads.

## Specification requirement

riscv/integrated-matrix-extension @ `6effbcae` (2026-08-04), `src/integrated-matrix.adoc`.

Common legality rules for tile loads and stores, line 2353:

> - `VL` shall be a multiple of `effective_lambda * LMUL`.

The Exceptions paragraph of `vmtl.v`, lines 5868–5881, lists the condition as an illegal-instruction condition:

> _Illegal Instruction_ is raised if any of the following conditions holds:
>
> - `vtype.vlmul` does not encode LMUL in {1, 2, 4, 8}.
> - No effective lambda is selected.
> - The effective lambda is not supported for the current (`VLEN`, `SEW`) configuration. [...]
> - `VL` is not a multiple of `effective_lambda * LMUL`.
> - _vd_ is not aligned for LMUL, or its register group extends past `v31`.
> - `vm=0` and the destination register group overlaps `v0`.

`vmts.v` (line 6018), `vmttl.v` (line 6175) and `vmtts.v` (line 6321) list the same condition.

The SAIL code of the specification checks it in `decode_tile_ls_geometry` (lines 4217–4231), which all four instructions call:

```sail
  let linesize      : int = lambda * LMUL;
  ...
  let num_elem      : int = unsigned(vl);

  if num_elem % linesize != 0 then
    return Illegal_Instruction();
```

## Offending code

[`ime_mem_insts.sail#L35-L41`](https://github.com/Openchip-Software/sail-riscv/blob/a545cc412ba022edae38b87f2caf8f2f54caf1e9/model/extensions/IME/ime_mem_insts.sail#L35-L41), in `execute VMTLTYPE`:

```sail
  if not(valid_vtype()) |
     illegal_vstart(VSTART_LOAD_STORE, num_elem, EMUL_pow) |
     not(valid_reg_group(vd, EMUL_pow)) |
     not(valid_rd_mask(vd, vm)) |
     not(ime_lambda_supported_value_for_vsew(lambda_value, vtype[vsew])) |
     lambda_value == 0
  then return Illegal_Instruction();
```

[`ime_mem_insts.sail#L130-L135`](https://github.com/Openchip-Software/sail-riscv/blob/a545cc412ba022edae38b87f2caf8f2f54caf1e9/model/extensions/IME/ime_mem_insts.sail#L130-L135), in `execute VMTSTYPE`, has the same structure without `valid_rd_mask`.
Neither list contains a check of `vl` against `cols = lambda_nat * LMUL`.

## Expected vs. actual

Configuration: RV64, `VLEN` = 256, `SEW` = 32, λ = 2, `LMUL` = 2.
The line size λ × `LMUL` is 4.

| Case                     | `VL` | Specification                 | Sail @ `a545cc41` |
| ------------------------ | ---- | ----------------------------- | ----------------- |
| `vmtl.v v8, (a0), zero`  | 4    | executes                      | executes          |
| `vmtl.v v8, (a0), zero`  | 1    | illegal instruction, mcause 2 | executes          |
| `vmts.v v8, (a0), zero`  | 1    | illegal instruction, mcause 2 | executes          |
| `vmttl.v v8, (a0), zero` | 1    | illegal instruction, mcause 2 | executes          |
| `vmtts.v v8, (a0), zero` | 1    | illegal instruction, mcause 2 | executes          |

Sail output (`sail.out`):

```
vmtl.v  VL=4: expected none, got none
vmtl.v  VL=1: expected 2, got none
vmts.v  VL=1: expected 2, got none
vmttl.v VL=1: expected 2, got none
vmtts.v VL=1: expected 2, got none
```

## Reproducer

Files: `legal.c`, `start.S`, `link.ld`, `sail.json`, `run.sh`.
The program runs in M-mode with `mstatus.VS` set and prints over the HTIF console.
The trap handler in `start.S` records `mcause` and resumes at the next instruction.
For each case, `legal.c` prints the expected and the observed `mcause`, or `none` when no trap was taken.

```sh
SAIL=/path/to/sail_riscv_sim SDK_SIF=/path/to/sdk-2026.10.14.sif ./run.sh
```

`run.sh` does the following:

```sh
riscv64-openchip-linux-gnu-gcc -march=rv64gcv_zvvmm_zvvmtls_zvvmttls -mabi=lp64d -mcmodel=medany \
  -O2 -nostdlib -nostartfiles -ffreestanding -T link.ld start.S legal.c -o legal.elf
sail_riscv_sim --enable-experimental-extensions --config-override sail.json legal.elf > sail.out
```

`sail.json` enables `Zvvmm`, `Zvvfmm`, `Zvvmtls` and `Zvvmttls` and sets `vlen_exp` to 8.

## Suggested fix

In `execute VMTLTYPE` and `execute VMTSTYPE`, return `Illegal_Instruction()` when `unsigned(vl) % cols != 0`.
`cols` is computed after the existing legality checks, so the check goes next to `if cols == 0`.

## Impact

- A program that sets `VL` to a value that is not a multiple of the line size gets a partial tile transfer instead of a trap.
- When this model is the ACT reference model, the `cp_ime_vl_not_multiple` bins of the `ExceptionsZvvm` suite expect no trap.
  A conforming implementation traps on them and fails the test.
