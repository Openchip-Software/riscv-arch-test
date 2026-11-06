# IME: matrix multiply-accumulate raises an illegal-instruction exception for `EMUL_C` = 16

## Summary

`execute_ime_int_gemm` and `execute_ime_fp_gemm` in `model/extensions/IME/ime_mem_insts.sail` reject `EMUL_C` = 16.
The IME specification permits `EMUL_C` ∈ {1, 2, 4, 8, 16}.
`EMUL_C` = `VLEN` ÷ (`SEW` × λ²), so `EMUL_C` = 16 occurs whenever λ² = `VLEN` ÷ (16 × `SEW`).
At `VLEN` = 256 this is `SEW` = 16 with λ = 1.
Every `vmmacc.vv`, `vwmmacc.vv`, `vqmmacc.vv`, `v8wmmacc.vv`, `vfmmacc.vv`, `vfwmmacc.vv` and `vfqmmacc.vv` in such a configuration traps.

Affected commit: Openchip-Software/sail-riscv `cgomez/0.16-plus-ime` @ [`a545cc41`](https://github.com/Openchip-Software/sail-riscv/tree/a545cc412ba022edae38b87f2caf8f2f54caf1e9).

## Specification requirement

riscv/integrated-matrix-extension @ `6effbcae` (2026-08-04), `src/integrated-matrix.adoc`.

Lines 380–383:

> The register-group multiplier of the C register group is `EMUL_C`, computed from the tile geometry:
> `EMUL_C` = (`VLEN` ÷ `SEW`) ÷ λ^2^, where λ is the tile-layout parameter decoded from the `lambda[2:0]` field in `vtype`.
> λ^2^ must divide (`VLEN` ÷ `SEW`), giving `EMUL_C` ∈ {1, 2, 4, 8, 16}.
> The C base register index must be a multiple of `EMUL_C`.

Lines 810–815:

> A nonzero lambda is _architecturally permissible_ for a given (`VLEN`, `SEW`) only when it yields a valid C register group, i.e. when `EMUL_C` = `VLEN` ÷ (`SEW` × λ²) is an integer in {`1`, `2`, `4`, `8`, `16`}.

## Offending code

[`ime_utils.sail#L91-L92`](https://github.com/Openchip-Software/sail-riscv/blob/a545cc412ba022edae38b87f2caf8f2f54caf1e9/model/extensions/IME/ime_utils.sail#L91-L92):

```sail
function ime_group_size_legal(group : nat) -> bool =
  group == 1 | group == 2 | group == 4 | group == 8
```

[`ime_mem_insts.sail#L249`](https://github.com/Openchip-Software/sail-riscv/blob/a545cc412ba022edae38b87f2caf8f2f54caf1e9/model/extensions/IME/ime_mem_insts.sail#L249) in `execute_ime_int_gemm` and [`ime_mem_insts.sail#L562`](https://github.com/Openchip-Software/sail-riscv/blob/a545cc412ba022edae38b87f2caf8f2f54caf1e9/model/extensions/IME/ime_mem_insts.sail#L562) in `execute_ime_fp_gemm` return `Illegal_Instruction()` when `ime_group_size_legal(EMUL_C)` is false.

Accepting 16 in `ime_group_size_legal` is not enough.
The C element accesses then go through `read_single_element` and `write_single_element`, which assert a register group of at most 8 registers ([`vext_control.sail#L56`](https://github.com/Openchip-Software/sail-riscv/blob/a545cc412ba022edae38b87f2caf8f2f54caf1e9/model/extensions/V/vext_control.sail#L56) and line 98):

```sail
  // Register in group. Max LMUL is 8, so this should be in [0, 8).
  let reg_in_group = index / elem_per_reg;
  assert(reg_in_group < 8);
```

## Expected vs. actual

Configuration: RV64, `VLEN` = 256, `LMUL` = 1, `vl` = 1.
`vd` = `v16`, which is aligned to 16 registers.

| Case                                                      | Specification | Sail @ `a545cc41`             |
| --------------------------------------------------------- | ------------- | ----------------------------- |
| `vmmacc.vv v16, v0, v8`, `SEW` = 32, λ = 1, `EMUL_C` = 8  | executes      | executes                      |
| `vmmacc.vv v16, v0, v8`, `SEW` = 16, λ = 1, `EMUL_C` = 16 | executes      | illegal instruction, mcause 2 |

Sail output (`sail.out`):

```
vmmacc.vv SEW=32 lambda=1 EMUL_C=8 : expected none, got none
vmmacc.vv SEW=16 lambda=1 EMUL_C=16: expected none, got 2
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

1. Accept 16 in `ime_group_size_legal`. `ime_group_size_to_pow` already returns 4 for 16.
2. Read and write C through two helpers that split the C group in two halves of 8 registers.
   Flat element indices below 8 × `VLEN` ÷ `SEW` go to `vd`.
   Higher indices go to `vd + 8`, with the index reduced by 8 × `VLEN` ÷ `SEW`.
   Each half then satisfies the assertion in `read_single_element` and `write_single_element`.
3. `valid_reg_group(vd, 4)` already requires `vd` to be a multiple of 16.

A patch of this form, applied to `c69e3e22`, passes the `Zvvmm` and `Zvvfmm` ACT suites at `SEW` = 16.

## Impact

- At `VLEN` = 256, λ = 1 is the smallest λ at `SEW` = 16, and λ = 1 is the λ with the largest C tile.
  An implementation that supports it cannot run any MACC instruction at that λ on Sail.
- When this model is the ACT reference model, every `SEW` = 16 test that uses λ = 1 fails to build its reference signature.
  On the `Zvvmm` and `Zvvfmm` ACT suites, this affects the four `SEW` = 16 `Zvvmm` files and the `SEW` = 16 `Zvvfmm` file.
- Other `VLEN` values have the same problem. Examples: `SEW` = 8 with λ = 1 at `VLEN` = 128, `SEW` = 32 with λ = 1 at `VLEN` = 512, and `SEW` = 64 with λ = 1 or `SEW` = 16 with λ = 2 at `VLEN` = 1024.
