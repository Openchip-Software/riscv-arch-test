# SPDX-License-Identifier: Apache-2.0
# Compile the ACT functional coverage testbench with pyslang, as framework/src/act/riscv-arch-test.do does with
# vlog. It checks the covergroups for syntax and elaboration errors when neither Questa nor VCS is available.
#
# Usage, from the riscv-arch-test checkout:
#   uv run --no-project --with pyslang python slang_check.py "$PWD" work/<config>/env ZVVMM32_COVERAGE,...
import sys

from pyslang.driver import Driver  # pyright: ignore[reportMissingImports]  # installed by uv run --with pyslang

repo, udb_dir, defines = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
fcov = f"{repo}/framework/src/act/fcov"
cov = f"{repo}/coverpoints"
incdirs = [udb_dir, f"{repo}/tests/env", cov, f"{cov}/unpriv", f"{cov}/priv", fcov]
args = ["slang", "--top", "testbench", "--timescale", "1ns/1ns", "-Wno-unused", "--ignore-unknown-modules"]
args += [f"-I{d}" for d in incdirs] + [f"-D{d}" for d in defines]
args += [f"{fcov}/{f}" for f in ("rvviTrace.sv", "riscv_arch_test.sv", "testbench.sv")]
driver = Driver()
driver.addStandardArgs()
assert driver.parseCommandLine(" ".join(args))
assert driver.processOptions()
parsed = driver.parseAllSources()
comp = driver.createCompilation()
reported = driver.reportCompilation(comp, False)
errors = [d for d in comp.getAllDiagnostics() if d.isError()]
print("parsed", parsed, "reported", reported, "errors", len(errors))
sys.exit(1 if errors or not parsed else 0)
