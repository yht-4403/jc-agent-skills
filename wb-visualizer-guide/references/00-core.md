# Visualizer Core Design System

## Philosophy
- **Seamless**: Users shouldn't notice where the host UI ends and your widget begins.
- **Flat**: No gradients, mesh backgrounds, noise textures, or decorative effects. Clean flat surfaces.
- **Compact**: Show the essential inline. Explain the rest in text.
- **Text goes in your response, visuals go in the tool** — All explanatory text, descriptions, introductions, and summaries must be written as normal response text OUTSIDE the tool call. The tool output should contain ONLY the visual element.

## Streaming
Output streams token-by-token. Structure code so useful content appears early.
- **HTML**: `<style>` (short) → content HTML → `<script>` last.
- **SVG**: `<defs>` (markers) → visual elements immediately.
- Prefer inline `style="..."` over `<style>` blocks — inputs/controls must look correct mid-stream.
- Keep `<style>` under ~15 lines.
- Gradients, shadows, and blur flash during streaming DOM diffs. Use solid flat fills instead.

## Rules
- No `<!-- comments -->` or `/* comments */` (waste tokens, break streaming)
- No font-size below 11px
- No emoji — use CSS shapes or SVG paths
- No gradients, drop shadows, blur, glow, or neon effects
- No dark/colored backgrounds on outer containers (transparent only — host provides the bg)
- **Typography**: h1 = 15px, h2 = 14px, h3 = 13px — all `font-weight: 500`. Body text = 13px, weight 400, `line-height: 1.6`. **Two weights only: 400 regular, 500 bold.** Never use 600 or 700.
- **Sentence case** always. Never Title Case, never ALL CAPS.
- Never use `position: fixed`
- No DOCTYPE, `<html>`, `<head>`, or `<body>` — just content fragments.
- **Local images**: to show an image from the session workspace inside the widget, reference it by absolute path (`<img src="/abs/path.png">`; for SVG use `<image href="/abs/path.png">`). The host rewrites local paths to a loadable form automatically — do NOT hand-write `data:` base64 or custom protocols.
- **CDN allowlist (CSP-enforced)**: scripts, fonts and other external resources may ONLY load from `cdnjs.cloudflare.com`, `esm.sh`, `cdn.jsdelivr.net`, `unpkg.com`.

## CSS Variables

| Category | Variables |
|----------|-----------|
| Backgrounds | `--color-background-primary` (white), `-secondary` (surfaces), `-tertiary` (page bg), `-info`, `-danger`, `-success`, `-warning` |
| Text | `--color-text-primary` (black), `-secondary` (muted), `-tertiary` (hints), `-info`, `-danger`, `-success`, `-warning` |
| Borders | `--color-border-tertiary` (0.15α, default), `-secondary` (0.3α, hover), `-primary` (0.4α), semantic `-info/-danger/-success/-warning` |
| Typography | `--font-sans`, `--font-serif`, `--font-mono` |
| Layout | `--border-radius-md` (8px), `--border-radius-lg` (12px — preferred for most components), `--border-radius-xl` (16px) |

## Complexity budget (hard limits)
- Box subtitles: ≤5 words
- Colors: ≤2 ramps per diagram
- Horizontal tier: ≤4 boxes at full width (~140px each)

## Accessibility
- For HTML widgets, begin with a visually-hidden `<h2 class="sr-only">` containing a one-sentence summary.
- SVG widgets use `role="img"` with `<title>` and `<desc>` as first children.