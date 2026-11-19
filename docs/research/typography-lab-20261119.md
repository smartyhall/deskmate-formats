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

## Native installation and byte map

Draw 03.05.00 loaded the independently constructed ten-descriptor face
through the Dixon slot on a disposable RSX clone. Rename the clone's
original DIXON.FF1 to a backup and copy the candidate into the same
directory as DIXON.FF1. Reenter Draw from DOS. The native descriptor
remains Dixon. This procedure was tested on the pinned 3.05 machine.
The generated files contain a single independent outline bank and a
ten-entry variant directory built from measured style constants.

Single-descriptor candidates and two-descriptor tests fell back to
System in the observed setup. A full ten-descriptor Dixon shell around
the geometric bank rendered with no pair table and zero auxiliary bytes
in each glyph. The fully independent ten-descriptor bank also rendered
when the 28 bytes between the inner header and advance table were
omitted. The ten-descriptor fourth-family trial with fresh IDs, a physical
LABGRID.FF1, and a matching Labgrid label rendered the bitmap fallback.
This did not establish additive installation or successful dialog selection.
DMFONT.RES contains a wildcard FF1 pattern, an explicit COBB.FF1 string,
and literals for Cobb, Dixon, Marin and System. Discovery and dialog
enumeration require separate tracing.

A native grid tested all 128 extended bytes using eight binary marker
stems in each physical FF1 glyph. All 128 marker rows decoded without an
ambiguous result. For attributes 01 FF 00 00 00 00 in the measured
base-outline profile, bytes 80–DF map to 96 distinct slots and E0–FF
silently select slot 32. The sampled ASCII controls matched their raw
codes. Import with `--native-text-map` to assign Unicode CP437
characters to the measured physical slots. Export with the same flag to
reverse that interpretation. Direct CP437 slot mapping remains available
for geometric interchange and testing. See the shared mapping in
[font_resources.py](../../src/deskmate_formats/font_resources.py).
Unicode interpretation follows CP437 input text. The raster probe measures
routing from bytes to glyphs, independently of character names.

```powershell
deskmate-font create --family Dixon --dixon-slot --output DIXON.FF1
deskmate-font import LOCAL.OTF --family Dixon --dixon-slot --native-text-map --output CONVERT.FF1
deskmate-font specimen CONVERT.FF1 --text "AV WA Ag fy" --output SPEC.FIG
```

Both TeX Gyre Bonum Regular and Liberation Mono Regular rendered through
this procedure, including the source ASCII, accented Latin, different
sizes and non-default width percentages. Their native-mapped copies were
saved and reopened on the same disposable system. Distinct outlines are
visible although the saved family field continues to be Dixon.

## Geometry and modern raster comparisons

Direct mapping controls use the full 223-codepoint interchange repertoire.

| Source | Shared coverage | Maximum sampled error in 1,000-em units | Maximum ink bound error | Advance error | FreeType overlap at 12 / 24 / 48 / 96 px |
| --- | ---: | ---: | ---: | ---: | --- |
| Bonum Regular | 166 | 0 | 0 | 0 | 75.48% / 83.32% / 90.38% / 95.97% |
| Liberation Mono Regular | 223 | 0.6961 | 0.5000 | 0.0977 | 80.35% / 89.88% / 91.97% / 96.58% |

Neither comparison changed the contour counts or contour orientation.
The TrueType control had three segment-sequence differences after CFF
encoding. Ink bound measures omit isolated move points. The sampled
deviation is measured over matching subdivisions. The CFF source
ascent and descent (1069 and −268) export as 930 and −241 from ink bounds.
The TrueType source hhea metrics are 832.52 and −300.29 on the 1,000-em
scale, with an export of 833 and −300. Line gaps in both controls are zero.

Exact source hashes are
`8ad5a53ae61d710fe1773f4ecc7fdf6dde7df1df59faa4492a24def95077d6b3`
for CTAN's texgyrebonum-regular.otf and
`6b3809450cf6253b36d157198dc15004a5fbade9abad5543c377feb7bb29139c`
for Debian's LiberationMono-Regular.ttf. Use the original archive notices.
[CTAN TeX Gyre](https://ctan.org/pkg/tex-gyre)
· [Debian Liberation fonts](https://deb.debian.org/debian/pool/main/f/fonts-liberation2/)

## Graphical text and comparison library

The Python writer and offline Workbench construct left-justified filled
base-outline runs. The authoring cache encloses the modeled glyph points
and nominal text width. The existing packed-list writer preserves other
supported leaves. The browser uses local FF1 file input, Tools → Text,
and a baseline placement followed by family, text, size and width fields.
The browser path currently authors printable ASCII. Python accepts CP437
bytes via Unicode input. Native rotation, hollow and other styles remain
outside this writing profile.

A headless Chromium trial loaded the exact geometric FF1 with no HTTP
requests, placed three outlines and downloaded a FIG. Original Draw
opened that download and displayed the synthetic contours at 19, 36
and 48 points and widths of 75, 100 and 125 percent. Native Save As
reopened with the same appearance. The
[typography comparison v1](../../examples/typography-comparison/v1/README.md)
binds the exact original specimen FIGs, crops and independent raster outputs.
