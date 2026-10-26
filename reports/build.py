#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Assemble a report: inline shared CSS/JS and SVG figures into one HTML file.

Placeholders in reports/src/<name>.src.html:
  <!--@STYLE-->          contents of src/report.css
  <!--@SCRIPT-->         contents of src/report.js
  <!--@FIG:<stem>-->     contents of figures/<stem>.svg
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build(name: str) -> Path:
    src = (ROOT / "src" / f"{name}.src.html").read_text()
    src = src.replace("<!--@STYLE-->", "<style>\n" + (ROOT / "src/report.css").read_text() + "</style>")
    src = src.replace("<!--@SCRIPT-->", "<script>\n" + (ROOT / "src/report.js").read_text() + "</script>")

    def fig(m: re.Match[str]) -> str:
        path = ROOT / "figures" / f"{m.group(1)}.svg"
        if not path.exists():
            print(f"warning: missing figure {path.name}", file=sys.stderr)
            return f'<p class="missing">Figure {m.group(1)} missing.</p>'
        svg = path.read_text()
        return re.sub(r"^<\?xml[^>]*>\s*", "", svg)

    src = re.sub(r"<!--@FIG:([\w-]+)-->", fig, src)

    # {{src:path:12-34}} or {{src:path}} -> link to the file at the pinned commit.
    # <!--@REPO:<base-url>--> sets the base; {{src2:...}} uses <!--@REPO2:...-->.
    repos = dict(re.findall(r"<!--@(REPO2?):(\S+?)-->", src))

    def cite(m: re.Match[str]) -> str:
        base = repos.get("REPO2" if m.group(1) == "src2" else "REPO")
        path, lines = m.group(2), m.group(3)
        label = f"{path}:{lines}" if lines else path
        if base is None:
            return f'<span class="src">{label}</span>'
        anchor = ""
        if lines:
            a, _, b = lines.partition("-")
            anchor = f"#L{a}" + (f"-L{b}" if b else "")
        return f'<a class="src" href="{base}/{path}{anchor}" target="_blank" rel="noopener">{label}</a>'

    src = re.sub(r"\{\{(src2?):([^:}]+)(?::([\d-]+))?\}\}", cite, src)
    out = ROOT / f"{name}.html"
    out.write_text(src)
    return out


if __name__ == "__main__":
    for n in sys.argv[1:]:
        print(build(n))
