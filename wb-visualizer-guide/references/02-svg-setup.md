# SVG Setup Rules

- viewBox fixed to `"0 0 680 H"`, **680 must not change**, it is the basis for all coordinate calculations. `width="100%"` on root `<svg>`.
- H = bottommost element + 20px, do not guess.
- Safe area: x=40 to x=640, y=40 to y=(H-40). Background transparent.
- One SVG per tool call.
- No rotated text.
- Use 0.5px strokes for diagram borders and edges.
- Every `<path>` or `<polyline>` used as a connector MUST have `fill="none"`.

## Pre-built classes

| Class | Description |
|-------|-------------|
| `class="t"` | sans 14px primary |
| `class="ts"` | sans 12px secondary |
| `class="th"` | sans 14px medium (500) |
| `class="box"` | neutral rect (bg-secondary fill, border stroke) |
| `class="node"` | clickable group with hover effect |
| `class="arr"` | arrow line (1.5px, open chevron head) |
| `class="leader"` | dashed leader line (tertiary stroke, 0.5px) |
| `class="c-{ramp}"` | colored node — apply to `<g>` or rect/circle/ellipse (not paths) |

## Arrow marker (must include in every SVG `<defs>`)

```svg
<defs>
  <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5"
    markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke"
      stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
  </marker>
</defs>
```

## Font size calibration

| Text | Chars | Weight | Size | Rendered width |
|------|-------|--------|------|----------------|
| Title | 12 | 500 | 14px | ~88px |
| Subtitle | 16 | 400 | 13px | ~104px |
| Body | 24 | 400 | 13px | ~156px |
| Caption | 20 | 400 | 12px | ~120px |

Box width formula: `rect_width = max(title_chars × 7, subtitle_chars × 6) + 24`