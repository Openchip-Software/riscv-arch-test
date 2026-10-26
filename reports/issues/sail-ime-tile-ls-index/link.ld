/* SPDX-License-Identifier: Apache-2.0 */
OUTPUT_ARCH("riscv")
ENTRY(_start)
SECTIONS
{
  . = 0x80000000;
  .text.init : { *(.text.init) }
  .text      : { *(.text*) }
  . = ALIGN(0x1000);
  .tohost    : { *(.tohost) }
  .rodata    : { *(.rodata*) *(.srodata*) }
  .data      : { *(.data*) *(.sdata*) }
  .bss       : { *(.bss*) *(.sbss*) *(COMMON) }
  . = ALIGN(16);
  . += 0x4000;
  __stack_top = .;
}
