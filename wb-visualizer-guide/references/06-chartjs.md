# Charts (Chart.js)

## Setup
```html
<div style="position: relative; width: 100%; height: 300px;">
  <canvas id="myChart" role="img" aria-label="Bar chart of quarterly revenue">Fallback text.</canvas>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>
  new Chart(document.getElementById('myChart'), {
    type: 'bar',
    data: { labels: ['Q1','Q2','Q3','Q4'], datasets: [{ label: 'Revenue', data: [12,19,8,15] }] },
    options: { responsive: true, maintainAspectRatio: false }
  });
</script>
```

## Rules
- Every `<canvas>` MUST have `role="img"`, a descriptive `aria-label`, and fallback text between the tags.
- Never rely on color alone to distinguish data series — pair each color with a secondary visual cue.
- Canvas cannot resolve CSS variables. Use hardcoded hex.
- Set height ONLY on the wrapper div, never on the canvas element itself.
- For horizontal bar charts: wrapper div height = `(number_of_bars × 40) + 80` pixels minimum.
- Load UMD build via `cdnjs.cloudflare.com`. Follow with plain `<script>` (no `type="module"`).
- Multiple charts: use unique IDs (`myChart1`, `myChart2`).
- Bubble/scatter charts: pad the scale range ~10% beyond your data range to avoid clipping.
- ≤12 categories: set `scales.x.ticks: { autoSkip: false, maxRotation: 45 }`.
- Negative values: `-$5M` not `$-5M`.

## Legends
Always disable default legend and use custom HTML:

```js
plugins: { legend: { display: false } }
```

```html
<div style="display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 8px; font-size: 12px; color: var(--color-text-secondary);">
  <span style="display: flex; align-items: center; gap: 4px;">
    <span style="width: 10px; height: 10px; border-radius: 2px; background: #3266ad;"></span>Chrome 65%
  </span>
</div>
```