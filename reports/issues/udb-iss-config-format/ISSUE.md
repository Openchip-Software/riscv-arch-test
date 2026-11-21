<!-- SPDX-License-Identifier: Apache-2.0 -->

<!-- Target: riscv/riscv-unified-db. Not filed. -->

# `cpp_hart_gen` ISS rejects configuration files in the format that the rest of UDB accepts

## Summary

The configuration that `rake gen:cpp_hart` builds from is not accepted by the ISS at run time (`iss -c <config>`).
riscv-arch-test writes its UDB configurations in the current format, and the ISS needs a converted copy.

Checked at Openchip-Software/riscv-unified-db `ime/fp-mx` @ `f0045fec`, which merges riscv/riscv-unified-db `main` @ `176fc360`.

## Differences

| Field                            | Accepted by the generator            | Accepted by the ISS                                      |
| -------------------------------- | ------------------------------------ | -------------------------------------------------------- |
| `$schema`                        | the current configuration schema URL | `https://riscv.org/udb/schemas/config_schema-0.1.0.json` |
| `implemented_extensions` entries | `{ name: Zve64d, version: "1.0.0" }` | `[Zve64d, "1.0.0"]`                                      |

With the other form, the ISS exits with a schema error before it loads the ELF.

## Expected behavior

The ISS accepts the same configuration file that the generator built it from.

## Suggested fix

Validate the run-time configuration with the same schema and loader as `rake gen:cpp_hart`, or accept both entry forms.

## Note before filing

Confirm the exact schema URL that the generator accepts on current `main`, and paste the ISS error text.
Neither was kept from the run.
