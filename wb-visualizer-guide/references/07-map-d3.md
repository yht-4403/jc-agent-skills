# Geographic maps (D3 choropleth)

**Never invent coordinates** — no hand-drawn SVG paths, no inline GeoJSON. Fetch real topology or don't draw a map.

## Topology sources

| Coverage | URL | Projection | Object key |
|----------|-----|------------|------------|
| US states | `https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json` | `d3.geoAlbersUsa()` | `.states` |
| World countries | `https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json` | `d3.geoNaturalEarth1()` | `.countries` |
| Per-country subdivisions | `https://cdn.jsdelivr.net/npm/datamaps@0.5.10/src/js/data/{iso3}.topo.json` | varies | `.{iso3}` |

Fetch the topology URL first and check the real `id` and `properties.name` fields before building the component. CSP blocks `raw.githubusercontent.com` and other unlisted domains.

```html
<div id="map" style="width: 100%;"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/topojson/3.0.2/topojson.min.js"></script>
<script>
const values = { 'California': 39, 'Texas': 30, 'New York': 19 };
const isDark = matchMedia('(prefers-color-scheme: dark)').matches;
const color = d3.scaleQuantize([0, 40], isDark ? d3.schemeBlues[5].slice().reverse() : d3.schemeBlues[5]);
const svg = d3.select('#map').append('svg').attr('viewBox', '0 0 900 560').attr('width', '100%');
const path = d3.geoPath(d3.geoAlbersUsa().scale(1100).translate([450, 280]));
d3.json('https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json').then(us => {
  svg.selectAll('path').data(topojson.feature(us, us.objects.states).features).join('path')
    .attr('d', path)
    .attr('stroke', isDark ? 'rgba(255,255,255,.15)' : '#fff')
    .attr('fill', d => color(values[d.properties.name] ?? 0));
});
</script>
```