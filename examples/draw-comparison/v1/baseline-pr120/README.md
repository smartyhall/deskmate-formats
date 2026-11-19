# Initial comparison milestone

The [manifest](manifest.json) binds four original featured drawings and
nineteen diagnostic controls to matching 640 × 418 native, renderer and
difference PNGs. It also records hashes of the unchanged SVG output
from renderer revision `5e1b24f8d8d262ac165b125474f7807163afbcc1`.

| Drawing | Native reference | Independent projection | Difference |
| --- | --- | --- | --- |
| Primitive and style chart | [PNG](primitives-styles-native.png) | [PNG](primitives-styles-renderer.png) · [SVG](primitives-styles-renderer.svg) | [PNG](primitives-styles-diff.png) |
| Cedar Workshop | [PNG](technical-plan-native.png) | [PNG](technical-plan-renderer.png) · [SVG](technical-plan-renderer.svg) | [PNG](technical-plan-diff.png) |
| Cedar Lake | [PNG](compound-landscape-native.png) | [PNG](compound-landscape-renderer.png) · [SVG](compound-landscape-renderer.svg) | [PNG](compound-landscape-diff.png) |
| Graphical typography | [PNG](typography-native.png) | [PNG](typography-renderer.png) · [SVG](typography-renderer.svg) | [PNG](typography-diff.png) |

Native output is a drawing-only, unscaled VGA framebuffer crop. Each
actually opened source was verified on the stopped clone by two extraction
methods. The featured files were tool-authored, opened and saved with
native Draw Save As, then reopened for the baseline. The frozen
[suite manifest](../../suite-v1.json) records their exact source identities
and attributes. The plan and typography use original labels and the local
Cobb font. Typography uses one external font reference, with no rotation
or embedded-stroke samples. The primitive chart lacks brush specimens.
The landscape contains independently sized repeated features and a nested
group, with no demonstrated native group transform.

Chromium rasterizes the SVG into a common 640 × 418 viewport at device
scale 1. The browser wrapper replaces only the SVG's tight viewport with a
fixed `0 0 8000 4840` view box, disables aspect-ratio preservation for
the measured separate x/y scales, and uses the stored palette background
outside the original SVG background rectangle. It applies no fitted
alignment or geometric correction to individual drawings. The stored
companion SVG is the original standalone projection.

Foreground pixels are pixels different from that side's background RGB.
Foreground IoU divides the mask intersection by the mask union.
Exact foreground RGB agreement divides shared foreground pixels with equal
raw RGB by the foreground union. It is sensitive to VGA DAC conversion
and Chromium antialiasing. Whole-frame exact RGB is recorded separately.
Cyan in the difference image marks native-only pixels, gold marks
renderer-only pixels, magenta marks overlap with differing RGB, and
gray marks exact foreground overlap. See the
[oracle report](../../../../docs/research/draw-oracle-20261119.md)
and [baseline builder](../../../../tools/experimental/draw_comparison_baseline.py).
