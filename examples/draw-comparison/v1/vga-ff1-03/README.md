# RSX raster with local FF1 outlines

All 23 frozen FIGs were freshly reopened in Draw 03.05.00. Their
stable native drawing crops match the frozen reference pixel for pixel.
The independent raster projects decoded Cobb line and cubic contours
with nominal advances. It uses palette slot 1 for the measured outline
ink. The companion SVG retains scalable cubics. The original FF1 file
stays local and the manifest records its SHA-256.

| Featured drawing | Foreground overlap | Exact RGB on foreground union | Mean / p95 boundary distance |
| --- | ---: | ---: | ---: |
| Primitive and style chart | 95.84% | 95.40% | 0.328 / 0 px |
| Cedar Workshop | 85.94% | 85.92% | 0.106 / 1 px |
| Cedar Lake | 99.91% | 99.84% | 0.009 / 0 px |
| Graphical typography | 43.76% | 43.76% | 1.283 / 4 px |

The typography raster was previously at 15.74% foreground overlap.
The new result covers all six outline-text runs. Alternate native modes
in some runs and the independent scan converter's unhinted geometry
account for visible shape, spacing and boundary differences. The
primitive chart and Cedar Lake are unchanged from the axis-stroke
milestone. See the [manifest](manifest.json) and the
[Draw II typography evidence](../../../../docs/research/draw-ii-20261119.md).
