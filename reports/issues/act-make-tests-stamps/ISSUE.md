<!-- SPDX-License-Identifier: Apache-2.0 -->

<!-- Target: riscv-non-isa/riscv-arch-test (act4). Not filed. Check whether an issue already exists. -->

# `make tests` stamps ignore `EXTENSIONS`, so a filtered run hides suites from a later full run

## Summary

`make tests` runs `covergroupgen` and `testgen` behind the stamps `$(STAMP_DIR)/covergroupgen.stamp` and `$(STAMP_DIR)/testgen.stamp`.
The stamps depend on the generator sources, the testplans and the Makefile, but not on `EXTENSIONS` or `EXCLUDE_EXTENSIONS`.

Checked at `act4` @ `7569d06d6`, `Makefile` lines 203–213.

## Effect

1. `EXTENSIONS=I make tests` generates only the I suite and writes both stamps.
2. A later `make tests` with no filter sees current stamps and does nothing.
   The other suites are not generated.

The opposite order fails too: after a full run, `EXTENSIONS=<suite> make tests` does nothing, even after the suite's generated files are deleted.

## Expected behavior

`make tests` generates the suites that `EXTENSIONS` and `EXCLUDE_EXTENSIONS` select, whatever the previous run selected.

## Suggested fix

Write the filter values into a file that changes only when they change, and make both stamps depend on it.
Another option is one stamp per suite.

## Workaround

Call `uv run covergroupgen testplans --extensions ...` and `uv run testgen testplans -o tests --extensions ...` directly, or delete the stamps.
