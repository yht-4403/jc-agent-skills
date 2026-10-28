# UI Components

## Aesthetic
Flat, clean, white surfaces. Minimal 0.5px borders. Generous whitespace. No gradients, no shadows (except functional focus rings). Everything should feel native to the host UI.

## Tokens
- Borders: always `0.5px solid var(--color-border-tertiary)` (or `-secondary` for emphasis)
- Corner radius: `var(--border-radius-md)` for most elements, `var(--border-radius-lg)` for cards
- Cards: white bg (`var(--color-background-primary)`), 0.5px border, radius-lg, padding 1rem 1.25rem
- Form elements (input, select, textarea, button, range slider) are pre-styled — write bare tags.
- Buttons: pre-styled with transparent bg, 0.5px border-secondary. If it triggers sendPrompt, append a ↗ arrow.
- **Round every displayed number.** Use `Math.round()`, `.toFixed(n)`, or `Intl.NumberFormat`.
- Spacing: use rem for vertical rhythm (1rem, 1.5rem, 2rem), px for component-internal gaps (8px, 12px, 16px)

## Metric cards
`background: var(--color-background-secondary)`, no border, `border-radius: var(--border-radius-md)`, padding 1rem. Muted 13px label above, 24px/500 number below. Use in grids of 2-4 with `gap: 12px`.

## Layout
- Editorial (explanatory content): no card wrapper, prose flows naturally
- Card (bounded objects like a contact record, receipt): single raised card wraps the whole thing
- Don't put tables here — output them as markdown in your response text instead
- Grid: use `minmax(0, 1fr)` to clamp overflow
- Table overflow: use `table-layout: fixed` in constrained layouts (≤700px)

## Mockup presentation
Contained mockups (mobile screens, chat threads, modals) should sit on a background surface. Full-width mockups (dashboards, settings pages) do not need an extra wrapper.

## Pattern 1: Interactive explainer
Use HTML for the interactive controls — sliders, buttons, live state displays, charts. No card wrapper. Whitespace is the container. Use `sendPrompt()` to let users ask follow-ups.

## Pattern 2: Compare options
Use `repeat(auto-fit, minmax(160px, 1fr))`. Featured card: `border: 2px solid var(--color-border-info)` (the only scenario where 2px border is allowed). Badge: `background: var(--color-background-info); color: var(--color-text-info); font-size: 12px`.

## Pattern 3: Data record
Wrap in a single raised card. Avatar/initials circle: 44px, `background: var(--color-background-info)`, `color: var(--color-text-info)`, `font-weight: 500`.

```html
<div style="background: var(--color-background-primary); border-radius: var(--border-radius-lg); border: 0.5px solid var(--color-border-tertiary); padding: 1rem 1.25rem;">
  <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
    <div style="width: 44px; height: 44px; border-radius: 50%; background: var(--color-background-info); display: flex; align-items: center; justify-content: center; font-weight: 500; font-size: 14px; color: var(--color-text-info);">MR</div>
    <div>
      <p style="font-weight: 500; font-size: 15px; margin: 0;">Maya Rodriguez</p>
      <p style="font-size: 13px; color: var(--color-text-secondary); margin: 0;">VP of Engineering</p>
    </div>
  </div>
</div>
```