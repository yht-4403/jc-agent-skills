# Diagram Guidance

## Flowchart
For sequential processes, cause-and-effect, decision trees.

- **Spacing**: 60px minimum between boxes, 24px padding inside boxes, 12px between text and edges.
- **Layout**: Prefer single-direction flows. Keep diagrams simple — max 4-5 nodes per diagram.
- **Cycles don't get drawn as rings.** Build a stepper in HTML instead. Only fall back to a linear SVG with curved return arrow when there's one input and one output total.
- Keep all nodes the same height when they have the same content type (single-line = 44px, two-line = 56px).
- Every `<text>` inside a box needs `dominant-baseline="central"`.

Single-line node example (44px):
```svg
<g class="node c-blue" onclick="sendPrompt('...')">
  <rect x="100" y="20" width="180" height="44" rx="8" stroke-width="0.5"/>
  <text class="th" x="190" y="42" text-anchor="middle" dominant-baseline="central">T-cells</text>
</g>
```

Two-line node example (56px):
```svg
<g class="node c-blue" onclick="sendPrompt('...')">
  <rect x="100" y="20" width="200" height="56" rx="8" stroke-width="0.5"/>
  <text class="th" x="200" y="38" text-anchor="middle" dominant-baseline="central">Dendritic cells</text>
  <text class="ts" x="200" y="56" text-anchor="middle" dominant-baseline="central">Detect foreign antigens</text>
</g>
```

## Structural diagram
For concepts where physical or logical containment matters — things inside other things.

- Outermost container: large rounded rect, rx=20-24, lightest fill (50 stop), 0.5px stroke.
- Inner regions: medium rounded rects, rx=8-12, next shade fill (100-200 stop).
- 20px minimum padding inside every container. Max 2-3 nesting levels.
- **Database schemas / ERDs — use mermaid.js `erDiagram`, not SVG.**

## Illustrative diagram
For building *intuition* — physical cross-sections or abstract spatial metaphors.

- **Physical subjects**: draw simplified versions (cross-sections, cutaways). A water heater is a tank with a burner underneath.
- **Abstract subjects**: invent spatial metaphors. A transformer is a stack of horizontal slabs. A hash function is a funnel scattering items into buckets.
- **Color encodes intensity**, not category. Warm ramps = heat/energy/active. Cool ramps = cold/calm/dormant.
- **Prefer interactive over static.** If the real-world system has a control, give the diagram that control.
- One `<linearGradient>` per diagram permitted (continuous physical properties only).
- CSS `@keyframes` animation permitted (`transform` and `opacity` only, loops under ~2s). Wrap in `@media (prefers-reduced-motion: no-preference)`.
- Place labels *outside* the drawn object with thin leader lines.

## Diagram type routing

| User says | Type | What to draw |
|-----------|------|-------------|
| "how do LLMs work" | Illustrative | Token row, stacked layer slabs, attention threads |
| "transformer architecture" | Structural | Labelled boxes: embedding, attention heads, FFN, layer norm |
| "what are the training steps" | Flowchart | Forward → loss → backward → update |
| "TCP handshake sequence" | Flowchart | SYN → SYN-ACK → ACK |
| "how does TCP work" | Illustrative | Two endpoints, numbered packets in flight, an ACK returning |
| "explain the Krebs cycle / event loop" | HTML stepper | Click through stages. Never a ring. |
| "draw the database schema" | mermaid.js | `erDiagram` syntax. Not SVG. |