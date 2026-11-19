# RSX raster with oblique line pens and slanted brushes

Draw 03.05.00 freshly reopened all 23 frozen FIGs on the RSX.
Both stable crops per drawing match the original native reference.
The independent projection keeps the local FF1 paths and adds
an integer centerline, dash phase and square stamps for oblique
lines. Supported slanted brush nibs sweep a scan-converted
quadrilateral. The companion SVG presents the scalable geometry.

| Featured drawing | Foreground overlap | Exact RGB on foreground union | Mean / p95 boundary distance |
| --- | ---: | ---: | ---: |
| Primitive and style chart | 96.31% | 95.87% | 0.285 / 0 px |
| Cedar Workshop | 85.94% | 85.92% | 0.106 / 1 px |
| Cedar Lake | 99.91% | 99.84% | 0.009 / 0 px |
| Graphical typography | 43.76% | 43.76% | 1.283 / 4 px |

The primitive chart improves from 95.84% foreground overlap in the
[FF1 milestone](../vga-ff1-03/README.md). The other three featured
foreground results are unchanged. The native line experiment independently
matched all 288 oblique controls, and the retained freehand brush control
reached 97.77%. Brush edge stepping and more general primitive and
viewport behavior remain open. The [manifest](manifest.json) binds each
frozen input and capture. See the
[pen experiments](../../../../docs/research/draw-ii-20261119.md#oblique-lines-and-slanted-brushes).
