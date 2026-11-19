# DeskMate Typography Laboratory

## Lossless native resource model

`deskmate-font validate LOCAL.FF1` reconstructs the file from decoded
contours and advances, separate headers and descriptors, and preserved
opaque sections. The reconstructed files matched the pinned original
Cobb, Dixon and Marin bytes at 61,503, 42,049 and 55,782 bytes. Tests
exercise synthetic directories, malformed records, integer ranges and
relocation. The native resource representation retains the original
variant order and descriptor bytes, glyph auxiliary bytes, inner padding
and trailing data.

| Offset | Meaning or observed relation |
| --- | --- |
| Outer +0 | Measured profile starts BD 7A 00 01 01 |
| Outer +8, +10, +12 | Em word, variant count, word 1 in all three originals |
| Outer +14, +16 | First character code and count |
| Outer +18 | Four signed resource bounds, repeated at inner +22 |
| Outer +30, +32, +34, +36 | Directory-relative 54, descriptor stride 46, inner start minus 16, word 16 |
| Outer +38 | Absolute optional tail pointer, zero for Cobb |
| Outer +54 | Family identifier candidate, Cobb 1, Dixon 2, Marin 14 |
| Descriptor +0 | NUL-terminated name in 32 bytes |
| Descriptor +32 | Face-dependent word, Cobb 1024, Dixon 0, Marin 4104 |
| Descriptor +34 | Variant identifier candidate, base Cobb 100, Dixon 50, Marin 7 |
| Descriptor +36–38 | Variant-dependent bytes, including percentage-like values |
| After descriptors +2 | Inner relative nominal advance table offset |
| Inner +0, +4 | Signature 1E F3 01 01 and length including its own header |
| Inner +12, +14, +16 | Em, first character code, and count |
| Inner +38, +46 | Second nominal-table offset candidate and glyph offset-table position |

Each original font has one glyph bank shared by its ten descriptor
records. This establishes the shared storage model. The exact variant
transform semantics and the role of the remaining metric and style
words are open. For new resources, the constructor synthesizes the
outer and inner global bounds from stored outline controls and uses
the measured 32–255, 1,000-em profile. It uses one named descriptor
and sets the optional tail pointer to zero.

## Portable commands

```powershell
python -m pip install ".[fonts]"
deskmate-font create --family Dixon --output DIXON.FF1
deskmate-font inspect DIXON.FF1
deskmate-font validate DIXON.FF1
deskmate-font roundtrip DIXON.FF1 --output COPY.FF1
deskmate-font export DIXON.FF1 --output GRID.OTF
deskmate-font import LOCAL.OTF --family Dixon --output CONVERT.FF1
```

The optional FontTools dependency is used for CFF and TrueType
interchange. Ordinary native reading and serialization have no new
dependency. The CLI reports exact byte identity and structural
coverage. Use a new output file and keep commercial-derived resources
private. The Dixon naming and default IDs select the tested research
slot on a disposable copy of native DeskMate.

## Modern outline interchange

FF1 Y coordinates increase downward from the baseline. OpenType Y
coordinates increase upward. The exporter flips the sign, retains
cubic controls and nominal advances, and synthesizes ascender and
descender values from the actual ink. Its default style is Regular.
OpenType re-import with the same coordinates reproduces the mapped
Lab Grid outlines and nominal advances exactly. The control slot
at DEL is omitted from the Unicode map.

The importer uses a provisional CP437 map for 223 bytes from the
measured 224-slot range, with no codepoint for 127. It resolves
TrueType composite transformations and implied on-curves through
FontTools. It elevates quadratic segments to cubics before integer
rounding. Missing slots have zero advance and no ink. It reports
missing codepoints and source feature tables outside the interchange.
Dynamic layout, kerning, hint programs, color and bitmap layers, original
family/style descriptors and native auxiliary data are outside the
conversion. Variable and CFF2 inputs are rejected. Keep the native
resource model for exact preservation.

The licensed conversion controls are TeX Gyre Bonum Regular from CTAN
(GUST Font License, LPPL 1.3c or later) and Liberation Mono Regular
from Debian fonts-liberation2 2.1.5-1 (SIL OFL 1.1, reserved names
including Liberation). The converted artifacts stay private with
their source notices. The [round-trip measure](../../tools/experimental/typography_roundtrip.py)
uses FontTools for outline and advance auditing and Pillow FreeType
for baseline-aligned coverage overlap. Modern raster overlap includes
the original font rasterizer's treatment of hints. It is separate
from DeskMate screenshot agreement.
