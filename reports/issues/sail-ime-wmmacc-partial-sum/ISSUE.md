# IME: `vfwmmacc.vv`/`vfqmmacc.vv` add each product into C instead of forming the sub-dot-product sum S first

## Summary

`execute_ime_fp_gemm` in `model/extensions/IME/ime_mem_insts.sail` accumulates every scalar product into the C element on its own.
For W>1, the IME specification requires the W products of a sub-dot-product to be reduced into a partial sum S before C is updated.
C is then updated once per group with `round_frm(C + S)`.
The two results can differ whenever one of the per-product additions into C is inexact.
No (G, psm, rnd) tuple describes the per-product result.
That includes G=1, psm=0, rnd=frm, which the comment at `ime_mem_insts.sail#L515-L518` discloses.

Affected rows: `vfwmmacc.vv` FP16 or BF16 into FP32, `vfwmmacc.vv` FP32 into FP64, `vfqmmacc.vv` FP16 or BF16 into FP64, and `vf8wmmacc.vv` OFP4 into FP32 or OFP8 into FP64.
The W=1 rows of `vfmmacc.vv` are not affected: a sub-dot-product of W=1 holds one product.

Affected commit: Openchip-Software/sail-riscv `cgomez/0.16-plus-ime` @ [`a545cc41`](https://github.com/Openchip-Software/sail-riscv/tree/a545cc412ba022edae38b87f2caf8f2f54caf1e9).
The defect was first observed at `c69e3e22`. `128a5b74` ("Implement IME vf8wmmacc.vv (W=8 FP matmul)") added the W=8 rows with the same accumulation loop.

## Specification requirement

riscv/integrated-matrix-extension @ `6effbcae` (2026-08-04), `src/integrated-matrix.adoc`.

Sub-dot-products, lines 1352–1359:

> When `W` > `1`, the `W` narrow input-element pairs packed within one accumulator-width (`SEW`-bit) position form a natural computational unit called a _sub-dot-product_.
> The `W` multiplications of (`SEW÷W`)-bit elements are performed and their products summed.

Accumulation and rounding model, lines 1361–1412:

- The λ sub-dot-products of each `LMUL=1` step are split into groups of G sub-dot-products, with G a power of two and 1 ≤ G ≤ λ (lines 1376–1384).
  A group with G sub-dot-products is a dot product of G × W elements.
- The group is reduced into a partial sum S (lines 1386–1397).
  With psm=0, S is exact: "the contributing products and sums are computed in sufficiently precise internal form, without rounding to the C accumulator format".
  With psm=1, S is a disclosed non-exact reduction.
- S is then rounded with `frm` (rnd=frm), rounded to odd (rnd=rto) or kept exact (rnd=xct) (lines 1399–1405).
- "After each group, the partial sum `S`, or the rounded value derived from `S`, is accumulated into the running value of C by computing C ← round_frm(C + S)" (lines 1407–1412).

The SAIL code of the specification, `fp_group_sum` (lines 4446–4490), forms S over `k_lo .. k_hi`, which spans the G·W products of the group:

```sail
  let k_lo   : int = k_base + g0 * g.W;
  let k_hi   : int = k_base + (g0 + g_len) * g.W - 1;

  match psm {
    PSM_EXACT => {
      var S : fp_internal = fp_internal_zero();
      foreach (k from k_lo to k_hi) {
        ...
        let prod : fp_internal = fp_mul_exact(a_bits, fmt_A, b_bits, fmt_B);
        S = fp_internal_add(S, prod)
      };
      S
    },
```

`fp_gemm` (lines 4677–4716) updates C once per group:

```sail
        foreach (g0 from 0 to (g.lambda - 1) by G) {
          let S : fp_internal =
            fp_group_sum(i, j, step, g0, G, g, fmt_A, fmt_B, fmt_C, psm, vs1, vs2);
          match round_group_sum(S, rnd, g.EEW_C, fmt_C, rm) {
            Some(S_bits) => acc = fp_add(acc, S_bits, g.EEW_C, fmt_C, rm),
            None()       => acc = fp_add_internal(acc, S, g.EEW_C, fmt_C, rm)
          }
        }
```

With G=1, a group is one sub-dot-product, so C is updated once per W products.

## Offending code

[`ime_mem_insts.sail#L612-L628`](https://github.com/Openchip-Software/sail-riscv/blob/a545cc412ba022edae38b87f2caf8f2f54caf1e9/model/extensions/IME/ime_mem_insts.sail#L612-L628), the FP16/BF16 into FP32 row:

```sail
          var acc : bits(32) = read_single_element(32, c_flat, vd);
          foreach (k from 0 to (K_eff - 1)) {
            ...
            let a = ime_fp16_or_bf16_to_fp32(rm_3b, altfmt_A, read_single_element(16, a_flat, vs1));
            let b = ime_fp16_or_bf16_to_fp32(rm_3b, altfmt_B, read_single_element(16, b_flat, vs2));
            let prod = fp_mul(rm_3b, a, b);
            acc = fp_add(rm_3b, acc, prod)                    // L623: one rounding into C per product
          };
```

The loop runs over all K_eff = λ·W·LMUL products and rounds into `acc` after each one.
The FP32 into FP64 row (lines 629–645, `fp_add` at line 640) and the FP16/BF16 into FP64 row (lines 646–662, `fp_add` at line 657) have the same structure.
So do the W=8 rows: OFP4 into FP32 (lines 663–679, `fp_add` at line 674) and OFP8 into FP64 (lines 680–696, `fp_add` at line 691).

The comment at [`ime_mem_insts.sail#L515-L518`](https://github.com/Openchip-Software/sail-riscv/blob/a545cc412ba022edae38b87f2caf8f2f54caf1e9/model/extensions/IME/ime_mem_insts.sail#L515-L518) discloses G=1, psm=0, rnd=frm, and describes the W=1 behaviour: "Each product is rounded to the C format and then accumulated into C under the dynamic frm".
For W>1, G=1 and psm=0 require the exact sum of the W products of one sub-dot-product before C is updated.

## Expected vs. actual

Configuration: RV64, VLEN=256, λ=1, LMUL=1, vl=1, `frm` = RNE.
A[0, k] are the packed inputs in element 0 of `vs1`, and B[k, 0] the packed inputs in element 0 of `vs2`.
The other rows of A are zero, so only C[0,0] changes.
In each case, every product is exact in the C format, every product is at most half an ULP of C₀, and the W products add up to one ULP of C₀.

| Case                             | A[0, k], B[k, 0]                   | C₀  | Specification, psm=0, any G, any rnd | Sail @ a545cc41          |
| -------------------------------- | ---------------------------------- | --- | ------------------------------------ | ------------------------ |
| `vfwmmacc.vv` FP16→FP32 (SEW=32) | A = B = (2⁻¹², 2⁻¹²)               | 1.0 | `0x3f800001`, no flags               | `0x3f800000`, NX         |
| `vfwmmacc.vv` FP32→FP64 (SEW=64) | A = (2⁻²⁶, 2⁻²⁶), B = (2⁻²⁷, 2⁻²⁷) | 1.0 | `0x3ff0000000000001`, no flags       | `0x3ff0000000000000`, NX |
| `vfqmmacc.vv` FP16→FP64 (SEW=64) | A = B = (0.5, 0.5, 0.5, 0.5)       | 2⁵² | `0x4330000000000001`, no flags       | `0x4330000000000000`, NX |

The specification column follows from the model above.
S is exact under psm=0: 2⁻²³, 2⁻⁵² and 1.0.
S is representable in the C format, so rnd=frm, rnd=rto and rnd=xct all leave it unchanged.
λ=1, so G=1.
C₀ + S is exact, so `round_frm(C₀ + S)` raises no flag.

Sail adds each product separately.
The first row shows the mechanism: 1 + 2⁻²⁴ is a tie and rounds to the even value 1.0, and so does the second addition.

Sail output (`sail.out`), identical at `c69e3e22` and `a545cc41`:

```
W2 f16>f32 rne C[0,0]=0x3f800000 fflags=0x00000001
W2 f32>f64 rne C[0,0]=0x3ff0000000000000 fflags=0x00000001
W4 f16>f64 rne C[0,0]=0x4330000000000000 fflags=0x00000001
```

The SDK QEMU (`x-zvvm=true`, `riscv-ime-qemu` @ `d856b96`) prints the same values (`qemu.out`).
It also adds each product into C on its own, with one fused multiply-add per product.
QEMU therefore does not conform either and cannot serve as the reference for this fix.

## Reproducer

Files: `fprnd.c`, `start.S`, `link.ld`, `sail.json`, `run.sh`.
The program runs in M-mode with `mstatus.FS` and `mstatus.VS` set, prints over the HTIF console and exits through `tohost`.
The same ELF runs on Sail and on QEMU's `spike` machine.

```sh
SAIL=/path/to/sail_riscv_sim SDK_SIF=/path/to/sdk-2026.10.14.sif ./run.sh
```

`run.sh` does the following:

```sh
riscv64-openchip-linux-gnu-gcc -march=rv64gcv_zvvmm_zvvfmm -mabi=lp64d -mcmodel=medany \
  -O2 -nostdlib -nostartfiles -ffreestanding -T link.ld start.S fprnd.c -o fprnd.elf
sail_riscv_sim --enable-experimental-extensions --config-override sail.json fprnd.elf > sail.out
qemu-system-riscv64 -nographic -machine spike -cpu max,vlen=256,x-zvvm=true -bios none -kernel fprnd.elf > qemu.out
```

`sail.json` enables `Zvvmm`, `Zvvfmm`, `Zvvmtls` and `Zvvmttls` and sets `vlen_exp` to 8.
The SDK GCC names `vfqmmacc.vv` `vfqwmmacc.vv`, so `fprnd.c` uses that name.

`fprnd.c` also prints two W=1 cases (`W1 f32 rne`, `W1 f32 rup`).
They are not part of this issue.
Sail rounds the product before the addition (rnd=frm) and QEMU fuses them (rnd=xct).
The specification permits both.
`fprnd-mixed.elf` adds a mixed-format W=1 case that runs on QEMU only (`qemu-mixed.out`).

## Suggested fix

For W>1, reduce the W products of each sub-dot-product into an exact partial sum, then round it once with `frm` and add it to C once.
This implements the disclosed G=1, psm=0, rnd=frm:

```
foreach sub-dot-product s in 0 .. λ·LMUL - 1:
    S   = exact sum of the W products of s      // no rounding
    S_r = round_frm(S) to the C format          // rnd=frm
    acc = round_frm(acc + S_r)
```

The sum must be exact.
A wider IEEE format is not enough: the products of two FP16 or BF16 values can differ in exponent by more than the significand of FP32 or FP64.
The specification declares an exact internal form, `fp_internal`, with `fp_mul_exact` and `fp_internal_add` (lines 4394–4405), and rounds it in `round_group_sum` (line 4523).
Sail integers can hold the scaled significands.

## Impact

- Every W>1 result where a per-product addition rounds differs from the specification.
- When this model is the ACT reference model, the expected values of such tests are wrong.
  A conforming implementation then fails them.
  QEMU passes them, because it has the same deviation.
- The ACT testplan design adds bins that detect the deviation.
  They fail on a conforming implementation until Sail is fixed.
- Tests whose products and partial sums are exact in the C format, with exact running sums, do not detect the defect.
