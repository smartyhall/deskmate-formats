# Experimental RSX VGA raster

The [manifest](manifest.json) records the 23 fresh native reopens,
all pixel-identical to their frozen baseline crops. The renderer PNGs
use the independent fixed-resolution Normal-zoom profile. Their
companion SVGs remain the separately authored scalable arc projection.
Both use the same FIGs and recorded viewport.

| Featured drawing | PR #120 foreground IoU | Quadratic SVG | RSX raster |
| --- | ---: | ---: | ---: |
| Primitive and style chart | 51.1% | 51.3% | 92.8% |
| Cedar Workshop | 45.7% | 46.5% | 85.0% |
| Cedar Lake | 80.8% | 80.8% | 99.9% |
| Graphical typography | 13.6% | 13.6% | 15.7% |

The RSX raster's exact RGB agreement on the foreground union is
92.3% for the chart, 85.0% for the workshop, 99.6% for Cedar Lake
and 15.7% for typography. D01, D02, D04, D05, D06, D07C, D11, D12,
D16A, D16B, D18 and D20 have complete foreground agreement and match
the native drawing colors. D23 contains an external-font label and
remains omitted. Screen-phase fill tiles, palette quantization and
one-pixel line placement explain much of the improvement.

The stage still approximates curve stepping and polygon scan
conversion. Its solid one-pixel strokes leave visible line-weight and
dash errors. It omits text. Those remaining differences are visible in
the [interactive gallery](../../compare.html).
