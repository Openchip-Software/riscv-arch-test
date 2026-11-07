##################################
# constants.py
#
# Package-wide constants for testgen.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Package-wide constants for testgen."""

# Assembly indentations
INDENT = "  "


def indent_asm(line: str) -> str:
    """Add INDENT to an assembly line unless it's already indented, a label, comment, or preprocessor directive."""
    if not line or line[0] in (" ", "\t", "#", "\n", "/"):
        return line
    colon_pos = line.find(":")
    if colon_pos > 0 and all(c.isalnum() or c == "_" for c in line[:colon_pos]):
        return line
    return f"{INDENT}{line}"


# =============================================================================
# Test Generation Configuration
# =============================================================================

# Max testcases per test file before splitting into multiple files. Individual test
# chunks won't be split, so if one test chunk exceeds this, the file will exceed this limit.
TESTCASES_PER_FILE = 1000
TESTCASES_PER_PRIV_FILE = 512

# Default number of traps allocated for a privileged test that does not specify its own count.
PRIV_TRAP_SIGUPD_COUNT = 1500

# =============================================================================
# Extension Configuration
# =============================================================================

# Integrated Matrix Extension (IME) extensions. These are the extensions that the ACT UDB overlay
# framework/src/act/data/udb_overlays/ime/ext/ defines. testgen does not depend on the act package,
# so it cannot read the overlay, and the names are listed here.
IME_EXTENSIONS = frozenset(
    {
        # Family extensions
        "Zvvmm",
        "Zvvfmm",
        "Zvvmtls",
        "Zvvmttls",
        # Computational extensions
        "Zvvbf16fp32mm",
        "Zvvbf16fp64mm",
        "Zvvbf16mm",
        "Zvvfp16fp32mm",
        "Zvvfp16fp64mm",
        "Zvvfp16mm",
        "Zvvfp32fp64mm",
        "Zvvfp32mm",
        "Zvvfp64mm",
        "Zvvi16i32mm",
        "Zvvi16i64mm",
        "Zvvi16mm",
        "Zvvi32i64mm",
        "Zvvi32mm",
        "Zvvi4i16mm",
        "Zvvi4i32mm",
        "Zvvi4i8mm",
        "Zvvi64mm",
        "Zvvi8i16mm",
        "Zvvi8i32mm",
        "Zvvi8i64mm",
        "Zvvi8mm",
        "Zvvofp4bf16mm",
        "Zvvofp4fp16mm",
        "Zvvofp4fp32mm",
        "Zvvofp4ofp8mm",
        "Zvvofp8bf16mm",
        "Zvvofp8fp16mm",
        "Zvvofp8fp32mm",
        "Zvvofp8fp64mm",
        "Zvvofp8mm",
        # Microscaling extensions
        "Zvvxi4bf16mm",
        "Zvvxi4fp16mm",
        "Zvvxi4fp32mm",
        "Zvvxi8bf16mm",
        "Zvvxi8fp16mm",
        "Zvvxi8fp32mm",
        "Zvvxi8fp64mm",
        "Zvvxni4bf16mm",
        "Zvvxni4fp16mm",
        "Zvvxni4fp32mm",
        "Zvvxni8bf16mm",
        "Zvvxni8fp16mm",
        "Zvvxni8fp32mm",
        "Zvvxni8fp64mm",
        "Zvvxnofp4bf16mm",
        "Zvvxnofp4fp16mm",
        "Zvvxnofp4fp32mm",
        "Zvvxnofp4ofp8mm",
        "Zvvxnofp8bf16mm",
        "Zvvxnofp8fp16mm",
        "Zvvxnofp8fp32mm",
        "Zvvxnofp8fp64mm",
        "Zvvxofp4bf16mm",
        "Zvvxofp4fp16mm",
        "Zvvxofp4fp32mm",
        "Zvvxofp4ofp8mm",
        "Zvvxofp8bf16mm",
        "Zvvxofp8fp16mm",
        "Zvvxofp8fp32mm",
        "Zvvxofp8fp64mm",
    }
)

EXPERIMENTAL_EXTENSIONS = frozenset({"Zibi", *IME_EXTENSIONS})

# Extensions that should generate RV32E/RV64E variants
# TODO: Add Zcmp and Zcmt when implemented
E_EXTENSION_TESTS = frozenset(
    {
        "I",
        "M",
        "Zmmul",
        "Zca",
        "Zcb",
        "Zba",
        "Zbb",
        "Zbs",
    }
)

# =============================================================================
# FLEN Mapping
# =============================================================================


def get_flen_for_extensions(extensions: list[str]) -> int:
    """Get the required FLEN for canonical extension components."""
    if "Q" in extensions:
        return 128
    if "D" in extensions:
        return 64
    return 32


# =============================================================================
# Coverpoint Configuration
# =============================================================================

# Coverpoints that don't need dedicated test generation
# (they are already covered by other tests)
SKIP_COVERPOINTS = frozenset(
    {
        # FP classification - covered elsewhere
        "cp_fclass",
    }
)

# =============================================================================
# Vector Configuration
# =============================================================================
MIN_SEW_MIN = 8
ELEN_MAX = 64
VLEN_MAX = 1024
