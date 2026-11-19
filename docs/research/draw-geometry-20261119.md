# Native Draw arc geometry and VGA fill patterns

The [Draw capture procedure](draw-oracle-20261119.md) was used for
independent synthetic arc and fill grids. The trials used the same Draw
03.05.00 RSX installation. The crops and stopped media remain private.
The two grids were Save As files independently extracted with 7-Zip and
the direct FAT16 reader. The [fixture manifest](../../tests/fixtures/application-generated/manifest.json)
pins both the independently authored candidates and the native saves.

## UA geometry

The SDK's 44-byte `UA` contains inline graphical attributes at
bytes 20–27, original local extents at 28–31 and three signed coordinate
pairs at 32–43. Transform the two base points (A,B) and apogee (P)
from the local extents into the stored world bounds. The measured curve is
the quadratic Bézier from (A) to (B) with control point
`2P − (A + B)/2`. Thus (P) lies at parameter one half. For equal
endpoint heights and a centered apogee, the curve is a parabola across the
horizontal span. A circle or half ellipse placed several plainly visible
samples more than eight native pixels from the measured curve.

The grid varies endpoint order, rise, apogee position, chord angle and
nonuniform positive scaling. Against 1,001 evenly spaced points on the
quadratic projected with the fixed Normal mapping, the mean nearest
distance from observed pixels for the ten supported samples ranged
from 0.35 to 0.64 pixels. The maximum was 1.58 pixels. The collinear
control drew its horizontal chord. The one control with reversed y
bounds produced a horizontal line near the first y bound rather than the
transformed curve. The independent projection reports unsupported extents
for that case. The comparison assesses curve geometry independently of
native stepping, stroke weights, pixel rounding and fill behavior.

The shared SVG projection emits a quadratic path with the line color
from inline attribute byte 20. This makes the geometry available in the
Draw, Text and Filer projections when a compatible form contains an arc.
The updated projection still approximates arc strokes as solid and
unfilled. The separate
[arc length investigation](draw-brideshw-20261118.md) qualifies the
explicit legacy recovery mode.

## Rectangular fill-pattern origin

PATSTUD repeats styles 0–15 in two grids, offset from each other by a
nonintegral multiple of the sampled tile sizes. Every rectangle uses
stored foreground index 10, background index 3 and outline index 2. The
interiors show background-only for index 0, foreground-only for index 1,
and two-color tiles for indices 2–15. Both copies give matching tile
phases in framebuffer coordinates. At Two times zoom, the eight
sufficiently visible styles preserve the same screen tile, including phase
and pixel period. Fill geometry therefore scales with zoom while the
observed tile stays locked to screen pixels in this VGA viewport.

The minimal measured widths range from one to 16 pixels. All
nonconstant rows except the vertical stripe's single repeated row have
a 19-pixel vertical repeat. This test covers two positions and two zooms
without scrolling. It leaves the driver implementation, other video
modes and palette/line interaction open.

The experimental shared raster renderer uses these screen-phase tiles
and the observed VGA palette conversion. The default palette channel
values 0, 64, 128 and 192 appear as 0, 64, 129 and 194. The candidate
calculation truncates the stored channel to six bits and expands it
using `floor(channel6 × 255 / 63)`. The independent 640 × 418 result
matched all pixels of the 32-rectangle pattern control, including the
outline and both sampled origins. The result does not establish DAC
rounding for values outside the tested palette.

Line thickness and style still use a solid one-pixel approximation
in the independent raster. The featured chart qualifies only several
concrete combinations. Its horizontal line at style 0 and width 0
draws 53 consecutive pixels. Style 2 with width 2 spans four rows,
and style 3 with width 3 spans six. Style 4 with width 0 has an
eight-pixel motif. Style 1 with width 1 leaves no measured pixels
in its expected band. The chart varies width and style together, so
the profile leaves those combinations as measurements pending a
one-variable-at-a-time stroke grid.

## One-variable stroke control

The native-saved 96-line grid crosses styles 0–7 with weights 0–3 in
three orientations. At Normal zoom the horizontal and vertical lines
share the same major-axis color masks for each style and weight.
Weights 0 and 1 have one- and two-pixel thickness respectively,
with distinct repeating masks. Style 1 is invisible for those
weights. Weights 2 and 3 use solid four- and six-pixel bands for
all eight sampled styles, including style 1. Their end caps extend
by one/two and two/three pixels on the measured ascending spans.

The independent raster applies the measured masks and caps to
axis-aligned lines. The [stroke metrics](../evidence/draw-stroke-masks-20261119.json)
show exact matching colors for all 64 sampled axis-aligned masks.
Fifty-five entire neighborhoods also match. Neighboring diagonal
stroke pixels account for the remaining neighborhood differences.
Diagonal thickness, diagonal dash phase, descending spans and
overlap with other drawing colors still need targeted qualification.

The same raster function accepts a shared graphics form and palette.
Its current viewport, VGA color mapping and tile phase apply to the
standalone RSX Draw capture. Native Text and Filer contexts may use
different origins, clipping and backgrounds.

## Brush records and native dispatch

The original serial-mouse Brush and Filled Brush control saves two
`UP` records, with eight and six points respectively. Both carry line
attribute bytes 1 and 18 at +22 and +23 in the measured default brush.
The open stroke has zero fill/connect flags. The filled-brush stroke
sets both flags to `ff` and retains the default `fe` pattern. It closes
the contour, with an unfilled interior in that capture. The native
brush traces widen with direction. The shared projections preserve
the recorded point path and closure and approximate the wide stroke.
This distinguishes the measured brush serialization from the
separate historical `B` records labeled bevel in the SDK.

Ghidra 12.1.4 decoded the load image of the pinned
`DRAW.PDM` (512-byte MZ header excluded, synthetic 16-bit x86 base
`1000:0000`). The dispatch at file offsets `0x9467–0x9486` checks
`U/A` and `U/P` separately. The `UA` callee at file `0x960e`
contains a transform branch that maps each local coordinate pair
`(x,y)` to `(yext-y,x)` and exchanges the x/y extents. It operates
on the inline fields +28–43. That part of the listing concerns record
transformation. The curve formula above comes from framebuffer
measurements and does not depend on identifying the Video Manager
raster routine.

The private run also produced a valid-group Break Object control,
contrasting with the disabled command in the PIPES trial. The
[writing report](draw-writing-20261119.md) records the native break,
make and reflect outcomes.
