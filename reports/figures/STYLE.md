# Figure style contract (inline SVG embedded in the report HTML)

- Output: one standalone `<svg>` element, no XML prolog, no <style> block with global selectors,
  no external fonts/images. `viewBox` set, `width="100%"`, no fixed height; `role="img"` and a <title>.
- Colors: ONLY these CSS custom properties (the page defines them for light and dark themes):
  --ground (page bg), --surface (box fill), --surface-2 (alternate fill), --ink (text/strong lines),
  --muted (secondary text, thin lines), --rule (borders, grid),
  --accent (teal: ACT framework / generation), --accent-soft (teal tint fill),
  --accent-2 (rust: DUT / device side), --accent-2-soft (rust tint fill),
  --ref (violet: reference model / Sail), --ref-soft (violet tint fill),
  --ok (green, pass), --bad (red, fail).
  Use them as `fill="var(--surface)"`, `stroke="var(--rule)"`. Every shape gets an explicit fill (use fill="none" for lines).
- Text: `font-family="var(--font-sans)"` for labels, `var(--font-mono)` for file names, commands, flags.
  Font sizes 12-14 (labels), 11 (annotations). Minimum 11. Text must fit inside its box: size boxes to the text.
- Arrows: define one <marker> per color inside <defs> with a unique id prefix per figure (e.g. `f3-arrow`),
  stroke-width 1.5. Lines must not cross text.
- Layout: horizontal flows max ~1000 units wide; leave 16 units margin inside the viewBox for outer labels.
- Labels use the report's vocabulary exactly as given in the spec (do not paraphrase names).
- Keep it legible at 720px rendered width.
