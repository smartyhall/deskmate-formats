# RSX raster with measured axis-aligned strokes

The [manifest](manifest.json) records a fresh native reopen of all
23 frozen FIGs. Every drawing-area reference matched its original
pixel bytes. The independent raster adds the measured horizontal
and vertical style and weight combinations. Diagonal, shape-outline
and text limits from the earlier raster milestone remain.

On the primitive and style chart, foreground overlap rose from
92.8% to 95.8% and exact foreground RGB agreement rose from 92.3%
to 95.4%. The stroke profile also raised Cedar Lake's exact
foreground RGB agreement from 99.6% to 99.8%. It leaves the
workshop at 85.0% foreground overlap and typography at 15.7%.
All comparisons use the original backgrounds, viewport and masks.

The [boundary report](../../../../docs/evidence/draw-comparison-boundaries-20261119.json)
adds symmetric nearest-boundary Manhattan distances to the earlier
foreground metrics. It does not change the baseline. Filled
patterns create internal foreground boundaries. The measured mean
for the chart declines from 5.995 pixels at PR #120 to 0.328.
The technical plan and typography illustrate metric tradeoffs.
Their mean boundary distances rise slightly against the baseline
even though their foreground overlap improves. Missing labels
and antialiasing in the scalable reference affect those distances.
