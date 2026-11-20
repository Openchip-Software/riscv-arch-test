# IME: the specification does not define the sign of `fp_internal_zero()` or of an exact zero group sum

## Summary

The specification starts the psm=0 partial sum S at `fp_internal_zero()` and does not say whether that zero is +0 or −0.
It also does not say which sign `fp_internal_add` gives an exact zero sum of two operands with opposite signs.
`fp_internal_add` takes no rounding-mode argument, so the IEEE 754 rule, which depends on the rounding direction, cannot be applied as declared.

Sail starts S at +0 and applies the IEEE 754 rule for exact zero sums under `frm`.
With C = −0 and a group whose products are all −0, Sail writes +0 to C under every rounding mode except RDN.
IEEE 754 arithmetic on the same values gives −0.
The specification permits either result, because it is silent.

This is a gap in the specification, not a confirmed Sail defect.
It is recorded so that ACT tests do not assume a sign that the specification does not define.

## Specification text

riscv/integrated-matrix-extension @ [`e99d9065`](https://github.com/riscv/integrated-matrix-extension/tree/e99d90653b08006c225da60ff058492e4fd842a5) (2026-11-09), `src/unpriv/integrated-matrix.adoc`.

Declaration of `fp_internal_zero`, lines 4934–4935:

```sail
// Zero value of the abstract internal FP representation.
val fp_internal_zero : unit -> fp_internal
```

Declaration of `fp_internal_add`, lines 4937–4942.
The function has no rounding-mode parameter:

```sail
// Exact internal addition of two abstract internal FP values.
// Finite sums are represented exactly in fp_internal.
// Special values are handled according to the participating FP values.
// ...
val fp_internal_add : (fp_internal, fp_internal) -> fp_internal
```

The prose description of `fp_internal_add`, lines 1839–1845, covers finite sums and special values.
It does not mention the sign of a zero sum.

`fp_group_sum`, lines 5011–5021, folds the products into S starting from `fp_internal_zero()`:

```sail
      var S : fp_internal = fp_internal_zero();
      foreach (k from k_lo to k_hi) {
        ...
        S = fp_internal_add(S, prod)
      };
```

`fp_gemm`, lines 5260–5264, then computes `fp_add(acc, round_group_sum(S))` or `fp_add_internal(acc, S)`.
Both helpers follow the C accumulator format rules, so the sign of S decides the sign of C when C and S are both zero.

The text that does define a zero sign is not about S:

- `fp_zero` (lines 4839–4840) returns "the positive zero bit pattern" of a concrete format. `fp_group_sum` does not call it.
- `fp_mul_exact` (lines 1830–1833) keeps signed-zero operands exact, so a product of −0 and a positive value is −0.

## Related rule elsewhere in the specification

The vector unordered sum reduction in `src/unpriv/vector-common.adoc`, lines 4058–4059 (`norm:vfredusum_additive_impl`), defines the additive identity for the same purpose:

> The additive identity is +0.0 when rounding down (towards -∞) or -0.0 for all other rounding modes.

That value is a true identity: x + identity = x for every x, including both zeros.
If `fp_internal_zero()` followed this rule, S for a group of all −0 products would be −0, and C = −0 would stay −0.
The IME text does not reference this rule.

## Sail behaviour

Openchip-Software/sail-riscv `fix-ime-int-emulc16` @ `7707a9a1`.

`ime_fp_group_sum` in `model/extensions/IME/ime_mx.sail`, line 172, starts S at +0:

```sail
  var S : ime_fpx = IME_FPX_FIN(0b0, 0, 0);
```

`ime_fpx_add` in `model/extensions/IME/ime_fp.sail`, lines 161–183, gives an exact zero sum the common sign of two equal-signed zeros.
Otherwise it returns −0 with RDN rounding (round-down) and +0 with any other rounding mode.
It reads the rounding mode from `frm`, which the specification's `fp_internal_add` does not receive.

`ime_fp_gemm`, lines 229–231, rounds S to the C format and adds it to C with `ime_fp_add`.

## Expected vs. actual

Each case uses a group whose products are all −0, for example A[i, k] = −0.0 and B[k, j] = +1.0.
C₀ = −0.

| `frm` | S in Sail | C after `round(C₀ + S)` in Sail | IEEE 754 sum of C₀ and the products | Specification |
| ----- | --------- | ------------------------------- | ----------------------------------- | ------------- |
| RNE   | +0        | +0                              | −0                                  | not defined   |
| RTZ   | +0        | +0                              | −0                                  | not defined   |
| RUP   | +0        | +0                              | −0                                  | not defined   |
| RMM   | +0        | +0                              | −0                                  | not defined   |
| RDN   | −0        | −0                              | −0                                  | not defined   |

The Sail column follows from the code above: +0 + (−0) is +0 except with RDN rounding, and −0 + (+0) is +0 except with RDN rounding.
It was derived by reading the code, not by running the model.

If any product in the group is +0, or C₀ is +0, IEEE 754 also gives +0 except with RDN rounding.
Sail agrees with IEEE 754 in those cases.
The difference is limited to C₀ = −0 with every product of every group equal to −0.

The microscaled integer path, `ime_mx.sail` line 272, converts the integer dot product with `ime_fpx_of_int`, which returns +0 for 0.
C₀ = −0 then also becomes +0 except with RDN rounding.
An integer dot product has no sign of zero, so this case has no IEEE 754 reference value.

## Questions for the specification

1. Is the value of `fp_internal_zero()` +0, −0, or dependent on `frm`?
2. Which sign does `fp_internal_add` give an exact zero sum of operands with opposite signs, given that it has no rounding-mode argument?
3. Is the sign of a zero C result after `vf*mmacc.vv` intended to be architecturally significant?
   If it is not, the specification can say that the sign of a zero result is implementation-defined, as RVBNA does for its dot products (`src/unpriv/rvbna.adoc`, lines 290 and 303).

## Impact on ACT tests

- A test that writes C = −0 and uses all −0 products has no defined expected sign.
  Sail produces +0 for it except with RDN rounding.
  An implementation that starts S at −0 produces −0 and is equally conforming.
- Until the specification answers question 1 or 3, tests should avoid C = −0 with all-zero groups.
  Alternatively, the test can compare zero results without their sign.
- If the specification adopts the rule of `norm:vfredusum_additive_impl`, Sail must start S at −0 for every rounding mode except RDN and at +0 with RDN rounding.
