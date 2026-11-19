# DeskMate typography comparison v1

These pairs use original project specimen layouts on the Tandy 1000 RSX
VGA Normal viewport. The native columns are cropped drawing pixels
from Draw 03.05.00. The independent columns use the shared nominal
advance and unhinted raster projection. Each image is 640 × 418 pixels.
[Capture and input identities](manifest.json)

| Face | Native Draw | Independent raster | Foreground intersection / union |
| --- | --- | --- | ---: |
| Lab Grid | [PNG](lab-grid-native.png) | [PNG](lab-grid-independent.png) | 85.62% |
| TeX Gyre Bonum conversion | [PNG](bonum-native.png) | [PNG](bonum-independent.png) | 52.87% |
| Liberation Mono conversion | [PNG](liberation-mono-native.png) | [PNG](liberation-mono-independent.png) | 78.50% |

All specimens use the Dixon installation slot. Lab Grid holds original
geometric contours and blank fallback slots. The two modern conversions
use the measured Draw base-outline remap for CP437 accents. Printed
point sizes span 12–48 and widths span 75–125%. Remaining differences
include native origin quantization, accumulated advances and pixel fill.
Small-size font hinting remains unresolved. The manifest records exact
FIG and FF1 hashes for each matched pair.

TeX Gyre Bonum Regular is distributed by the TeX Gyre project under
the GUST Font License and LPPL 1.3c or later. Liberation Mono Regular
comes from Debian fonts-liberation2 2.1.5-1 under SIL OFL 1.1. The
attribution in these rows identifies the outlines used to render the
specimens. The image notices apply to the project specimens and
comparison artifacts. The source and converted modern font files
remain private with their upstream notices. The numerical modern-to-modern
FreeType controls are separate from these native captures.
[Research report and recipes](../../../docs/research/typography-lab-20261119.md)

The [gallery generator](../../../tools/experimental/typography_gallery.py)
recreates these PNGs from the archived FIGs, font candidates and hashed
native frames. The existing [Draw library](../../draw-comparison/README.md)
retains its earlier published milestones.
