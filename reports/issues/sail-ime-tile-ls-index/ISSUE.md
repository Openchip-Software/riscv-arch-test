# IME: `vmtl.v`/`vmts.v` use the flat element index instead of `tile_reg_idx`, so tiles are transposed in registers when LMUL>1

## Summary

The tile load and store instructions in `model/extensions/IME/ime_mem_insts.sail` read and write vector register elements at the sequential tile index `i`.
The IME specification requires the register-group element index `tile_reg_idx(i, LMUL, λ, VLEN/SEW)`.
Both indices are equal only when LMUL=1.
For LMUL>1, the Sail model places every tile element in the wrong register element.
The same defect affects all four tile instructions: `vmtl.v`, `vmttl.v`, `vmts.v` and `vmtts.v`.

The matrix multiply instructions in the same file index A, B and C with `ime_mat_{A,B,C}_idx`, which call `ime_tile_reg_idx`.
They agree with the specification.
The loads and stores do not, so a C tile written by `vmmacc.vv` and stored with `vmts.v` at LMUL>1 reaches memory transposed.
QEMU (`x-zvvm=true`) and the IME Rust golden model follow the specification.

Affected commit: Openchip-Software/sail-riscv `cgomez/0.16-plus-ime` @ [`c69e3e22`](https://github.com/Openchip-Software/sail-riscv/tree/c69e3e2274eb75f0b803fbc282bf9c10e5e2717b).
The flat index was introduced in `3d7909d1` ("feat(ime): implement Sail IME tile and matrix operations").

## Specification requirement

riscv/integrated-matrix-extension @ `6effbcae` (2026-08-04), `src/integrated-matrix.adoc`, lines 4247–4256:

```sail
// Map sequential tile element index i to the flat register-group element index.
// linesize = lambda * LMUL; elements within one tile row span LMUL registers.
function tile_reg_idx(i : int, LMUL : int, lambda : int, elems_per_reg : int) -> int = {
  let linesize     : int = lambda * LMUL;
  let line         : int = i / linesize;
  let elem_in_line : int = i % linesize;
  let regoff       : int = elem_in_line / lambda;
  let elementoff   : int = line * lambda + elem_in_line % lambda;
  regoff * elems_per_reg + elementoff
}
```

The `vmtl.v` operation, lines 5925–5941:

```sail
      let flat_idx : int =
        tile_reg_idx(i, LMUL, eff_lambda, elems_per_reg);
      let mem_off : int =
        (i / linesize) * LD + (i % linesize);
      ...
          write_single_element(EEW, flat_idx, vd, elem),
```

`vmts.v` (lines 6055–6062), `vmttl.v` (line 6222) and `vmtts.v` (line 6359) use the same `flat_idx`.
The specification also states that inactive elements of a tile load are left undisturbed and that `vtype.vma` does not apply (lines 5853–5855).

## Offending code

Load, [`ime_mem_insts.sail#L64-L92`](https://github.com/Openchip-Software/sail-riscv/blob/c69e3e2274eb75f0b803fbc282bf9c10e5e2717b/model/extensions/IME/ime_mem_insts.sail#L64-L92):

```sail
  foreach (i from 0 to (num_elem - 1)) {
    if mask[i] == 0b1 then {
      ...
        32 => match vmem_read(rs1, to_bits_unsafe(xlen, byte_offset), 4, Load(Vector), false, false, false) {
               Ok(elem) => write_single_element(32, i, vd, elem),     // L81: flat index i
      ...
    } else {
      write_single_element(SEW, i, vd, result[i])                     // L90: flat index i
    }
  };
```

Lines 73, 77, 81 and 85 write the loaded element at register-group element `i`.
Line 90 writes inactive and tail elements at register-group element `i`.

Store, [`ime_mem_insts.sail#L160`](https://github.com/Openchip-Software/sail-riscv/blob/c69e3e2274eb75f0b803fbc282bf9c10e5e2717b/model/extensions/IME/ime_mem_insts.sail#L160):

```sail
      let data = read_single_element(SEW, i, vs3);
```

The helper that implements the specification already exists, [`ime_utils.sail#L98-L107`](https://github.com/Openchip-Software/sail-riscv/blob/c69e3e2274eb75f0b803fbc282bf9c10e5e2717b/model/extensions/IME/ime_utils.sail#L98-L107):

```sail
function ime_tile_reg_idx(i : nat, group : nat, lambda_value : nat, elems_per_reg : nat) -> nat = {
```

It is used by `ime_mat_A_idx`, `ime_mat_B_idx` and `ime_mat_C_idx` ([`ime_utils.sail#L132-L139`](https://github.com/Openchip-Software/sail-riscv/blob/c69e3e2274eb75f0b803fbc282bf9c10e5e2717b/model/extensions/IME/ime_utils.sail#L132-L139)), and through them by `vmmacc.vv` ([`ime_mem_insts.sail#L250-L256`](https://github.com/Openchip-Software/sail-riscv/blob/c69e3e2274eb75f0b803fbc282bf9c10e5e2717b/model/extensions/IME/ime_mem_insts.sail#L250-L256)).
It is not used by the tile loads and stores.

## Expected vs. actual

Configuration: RV64, VLEN=256, SEW=32, LMUL=2, λ=1, vl=16, LD=2.
Elements per register (`epr`) = 8 and `linesize` = 2.
The specification maps tile element `i` to register-group element `tile_reg_idx(i, 2, 1, 8) = (i % 2) * 8 + i / 2`.
So even tile elements go to `v8` and odd tile elements go to `v9`.

| Step | Register or memory | Spec / QEMU | Sail @ c69e3e22 |
| --- | --- | --- | --- |
| 1. `vmtl.v v8` from `A = 0..15`, then `vse32.v v8` | `v8[0..7]` | `0 2 4 6 8 10 12 14` | `0 1 2 3 4 5 6 7` |
| | `v9[0..7]` | `1 3 5 7 9 11 13 15` | `8 9 10 11 12 13 14 15` |
| 2. `vid.v v16` (`v16`,`v17` = `0..15`), then `vmts.v v16` | `mem[0..7]` | `0 8 1 9 2 10 3 11` | `0 1 2 3 4 5 6 7` |
| | `mem[8..15]` | `4 12 5 13 6 14 7 15` | `8 9 10 11 12 13 14 15` |
| 3. `vmtl.v` then `vmts.v`, same geometry | `mem[0..15]` | `0..15` | `0..15` |

Step 3 shows why the defect is hidden by round-trip tests: the load and the store apply the same wrong mapping, so they cancel.

Sail output (`sail.out`):

```
Sail RISC-V git: 0.16-8-gc69e3e22
config: VLEN=256 SEW=32 LMUL=2 lambda=1 vl=16 LD=2
1 vmtl.v A=0..15; vse32.v v8,v9: 0 1 2 3 4 5 6 7 | 8 9 10 11 12 13 14 15
2 vid.v v16,v17; vmts.v -> mem:  0 1 2 3 4 5 6 7 | 8 9 10 11 12 13 14 15
3 vmtl.v + vmts.v round trip:    0 1 2 3 4 5 6 7 | 8 9 10 11 12 13 14 15
```

QEMU output (`qemu.out`):

```
QEMU emulator version 10.2.50
config: VLEN=256 SEW=32 LMUL=2 lambda=1 vl=16 LD=2
1 vmtl.v A=0..15; vse32.v v8,v9: 0 2 4 6 8 10 12 14 | 1 3 5 7 9 11 13 15
2 vid.v v16,v17; vmts.v -> mem:  0 8 1 9 2 10 3 11 | 4 12 5 13 6 14 7 15
3 vmtl.v + vmts.v round trip:    0 1 2 3 4 5 6 7 | 8 9 10 11 12 13 14 15
```

## Reproducer

Files: `repro.c`, `start.S`, `link.ld`, `sail-ime.json`, `run.sh`.
An HTML illustration of the mapping and the outputs is attached: `sail-ime-tile-ls-index.html`.
The program runs in M-mode, prints over the HTIF console and exits through `tohost`.
The same ELF runs on Sail and on QEMU's `spike` machine.

```sh
SAIL=/path/to/sail_riscv_sim SDK_SIF=/path/to/sdk-2026.10.14.sif ./run.sh
```

`run.sh` does the following:

```sh
riscv64-openchip-linux-gnu-gcc -march=rv64gcv_zvvmm_zvvmtls -mabi=lp64d -mcmodel=medany \
  -O2 -nostdlib -nostartfiles -ffreestanding -T link.ld start.S repro.c -o repro.elf
sail_riscv_sim --enable-experimental-extensions --config-override sail-ime.json repro.elf > sail.out
qemu-system-riscv64 -nographic -machine spike -cpu max,vlen=256,x-zvvm=true -bios none -kernel repro.elf > qemu.out
```

`sail-ime.json` enables `Zvvmm`, `Zvvmtls` and `Zvvmttls` and sets `vlen_exp` to 8.

## Suggested fix

Index register elements with `ime_tile_reg_idx` in both loops.
Remove the `else` branch of the load.
With the corrected index, that branch would overwrite already-loaded elements: inactive element `i` writes register-group element `i`, which is the destination of a different tile element.
The specification also leaves inactive and tail elements undisturbed and ignores `vtype.vma` and `vtype.vta`.

```diff
--- a/model/extensions/IME/ime_mem_insts.sail
+++ b/model/extensions/IME/ime_mem_insts.sail
@@ -68,26 +68,25 @@ function clause execute VMTLTYPE(lambda_field, mode, vm, rs2, rs1, vd) = {
       let byte_offset = mem_off * SEW_bytes;
+      let flat_idx = ime_tile_reg_idx(i, LMUL, lambda_nat, vlen / SEW);
       match SEW {
         8  => match vmem_read(rs1, to_bits_unsafe(xlen, byte_offset), 1, Load(Vector), false, false, false) {
-               Ok(elem) => write_single_element(8, i, vd, elem),
+               Ok(elem) => write_single_element(8, flat_idx, vd, elem),
 ...    (same change for 16, 32 and 64)
       }
-    } else {
-      write_single_element(SEW, i, vd, result[i])
     }
   };
@@ -157,7 +156,7 @@ function clause execute VMTSTYPE(lambda_field, mode, vm, rs2, rs1, vs3) = {
       let byte_offset = mem_off * SEW_bytes;
-      let data = read_single_element(SEW, i, vs3);
+      let data = read_single_element(SEW, ime_tile_reg_idx(i, LMUL, lambda_nat, vlen / SEW), vs3);
```

The full patch is in `sail-fix.diff`.
With this patch applied to c69e3e22, the reproducer prints the same values as QEMU (`sail-fixed.out`):

```
1 vmtl.v A=0..15; vse32.v v8,v9: 0 2 4 6 8 10 12 14 | 1 3 5 7 9 11 13 15
2 vid.v v16,v17; vmts.v -> mem:  0 8 1 9 2 10 3 11 | 4 12 5 13 6 14 7 15
3 vmtl.v + vmts.v round trip:    0 1 2 3 4 5 6 7 | 8 9 10 11 12 13 14 15
```

## Impact

- Every tile held in a register group with LMUL>1 is transposed relative to the specification.
  For `vmmacc.vv`, the C tile uses `EMUL_C = VLEN/(SEW·λ²)` registers, so every C store is affected unless EMUL_C=1.
- A and B tiles loaded at LMUL>1 feed `vmmacc.vv` with the wrong elements.
- When this model is the ACT reference model, the expected signatures of every IME test that loads or stores a tile at LMUL>1 are wrong.
  A conforming implementation, such as QEMU, then fails those tests.
- Tests that load and store with the same geometry, or that read C back with `vse<sew>.v`, do not detect the defect.
