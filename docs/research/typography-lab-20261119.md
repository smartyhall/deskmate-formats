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
| Outer +8, +10, +12 | Em word, variant count, outline-family count |
| Outer +14, +16 | First character code and count |
| Outer +18 | Four signed resource bounds, repeated at inner +22 |
| Outer +30, +32, +34, +36 | Variant directory offset 54, stride 46, bank-directory offset and bank stride 16 |
| Outer +38 | Absolute optional tail pointer, zero for Cobb |
| Variant +0 | ID word, base Cobb 1, Dixon 2, Marin 14 |
| Variant +2–4 | Variant-dependent bytes, including percentage-like values at +3 |
| Variant +12 | NUL-terminated name in 32 bytes |
| Variant +44 | Face-dependent word, base Cobb 1024, Dixon 0, Marin 4104 |
| Bank +0, +2 | Word 1 and absolute 32-bit outline-bank pointer |
| Bank +14 | Inner relative nominal advance table offset |
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
private. Use a distinct name and unused base ID for a new face on a
disposable copy. The Dixon profile is also available as a replacement control.

## Modern outline interchange

FF1 Y coordinates increase downward from the baseline. OpenType Y
coordinates increase upward. The exporter flips the sign, retains
cubic controls and nominal advances, and synthesizes ascender and
descender values from the actual ink. Its default style is Regular.
OpenType re-import with the same coordinates reproduces the mapped
Lab Grid outlines and nominal advances exactly. The control slot
at DEL is omitted from the Unicode map.

The direct interchange uses 223 Unicode mappings over the
224-slot range. The native mapping targets 191 supported display bytes.
The importer resolves
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

Draw 03.05.00 discovered Labgrid alongside Cobb, Dixon and Marin after
copying the single-variant LABGRID.FF1 into the clone's DeskMate directory
and launching Draw from DOS. Selecting Labgrid in native Text Options
and drawing a new label worked. The native save reopened as Labgrid.
Two single-variant modern conversions coexisted as Lab Serif and Lab Mono.
Their DOS filenames, BONUM.FF1 and MONOFONT.FF1, differ from their internal
family names. These trials used the existing configuration.

The early short-directory trials used incorrect outline-bank descriptors.
Ghidra 12.1.4 verified the native directory access in a stripped MZ image
at synthetic 1000:0000 with the 0x200-byte file header removed.
DMFONT.RES (SHA-256 c23c440793c4bc154ea8af14fd195e45018e5af581a0b197109380f8d0da4be4)
uses a wildcard scan at file 0x24bc, tests the signature/version near
0x2564, and reads the first variant offset and record size from header
+30 and +32 around 0x260a–0x2671. File insertion compares names at
variant +12. The wildcard literal is at 0x98fc. The scan loop allows
up to 24 iterations in this routine.

The replacement profile rendered with no auxiliary bytes in any glyph
and no pair table. It also rendered with the 28 bytes between the inner
header and advance table omitted. The corrected independent single
variant uses the absolute bank pointer. Alternate directories,
overlapping internal names and live rescan behavior remain open.

A native grid tested all 128 extended bytes using eight marker stems
in each physical FF1 glyph. The module table at 0x92ce agrees with
all but the crowded C1 cell. A separate oval-versus-rectangle probe
confirmed the table's C1 → 255 entry. For attributes 01 FF 00 00 00 00 in the measured
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
deskmate-font create --family Labgrid --face-id 28 --output LABGRID.FF1
deskmate-font import LOCAL.OTF --family "Lab Serif" --face-id 29 --native-text-map --output CONVERT.FF1
deskmate-font specimen CONVERT.FF1 --text "AV WA Ag fy" --output SPEC.FIG
```

Both TeX Gyre Bonum Regular and Liberation Mono Regular rendered through
this procedure, including ASCII, accented Latin, different sizes and
non-default width percentages. Their named copies were saved and
reopened on the same disposable system.

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

## Hints, placement and display modes

A Dixon control used the same I H E L O I label at 9, 12, 16, 24, 32,
48 and 60 points. Removing every marker-2 auxiliary section changed 4,
26, 59, 123, 139, 131 and 154 pixels in those rows. The unchanged
paths rendered in every case. Editing just the third word of Dixon
I's first X row from 92 to 230 changed 42 pixels at 24 points and
zero at the six other measured sizes. Each I gained one 21-pixel
column at its right edge. Removing auxiliary data produced the same
right edge in that I. This isolates a size-dependent stem effect in
a row whose first two words match I's stored edges (91 and 186).
The interpolation and grid-fitting rules remain open.

The synthetic repeated-I grid spans eight point-size and width settings.
Within each row every native stem has the same pixel width despite
fractional nominal origins along the row. For (point size, width percent)
of (10,100), (12,100), (15,100), (19,125), (24,100), (29,75), (36,95),
and (48,100), the native widths were respectively 3, 3, 5, 6, 7, 6, 8,
and 11 pixels. All left edges were within one pixel of truncating the
nominal projected outline start. A straight floor-of-accumulation
model with the nominal exact advance cannot fit every row by adjusting
only its origin. The independent projection retains nominal advances
and its existing scan converter.

The mode grid changes only byte 20 or 21 of otherwise identical Labgrid
records. Byte 20 values 0–15 show distinct outline-size and fallback
classes, including the correct outline at 01 FF, small bitmap-like
projections, and Cobb-like outlines. Byte 21 changes geometry and
family resolution with byte 20 held at 1. The exact bit semantics
remain open and the renderer keeps its existing guard. After the
new remap, all 23 frozen Draw rasters still match the previous pen
milestone byte for byte. The typography gallery covers additional
cases without replacing any earlier comparison.

## Native saves and reproducible fixtures

The installed Labgrid resource has 5,664 bytes and SHA-256
b57cf48e972b1025c7a4e1925bccb9b909e332ef5135d51941cc5a9ee2c3c484.
The [exact FF1 fixture](../../tests/fixtures/application-generated/draw/typography-lab-grid.ff1)
reproduces via the CLI above. The ten-descriptor Dixon reference used
for the first comparison milestone remains reproducible with
`create --family Dixon --dixon-slot` (6,078 bytes, SHA-256
ceba26564c5e0d0d631504ed264a5c202e97fbf6c9d600d6e2e631fe65952967).
The two independent FAT16 extractors agreed on the installed Labgrid,
Lab Serif and Lab Mono file bytes and each published FIG.

| Published FIG | Verified workflow |
| --- | --- |
| [Labgrid native authoring](../../tests/fixtures/application-generated/draw/typography-labgrid-native.fig) | Select Labgrid, draw and save a 24 pt label |
| [Browser Labgrid input](../../tests/fixtures/application-generated/draw/typography-browser-labgrid.fig) and [native edit](../../tests/fixtures/application-generated/draw/typography-browser-labgrid-native.fig) | Three browser runs opened in Draw. Clear the first run and reauthor AV OI 10! at 32 pt and 115%. Save As and reopen |
| [Browser Lab Mono input](../../tests/fixtures/application-generated/draw/typography-browser-mono.fig) and [native save](../../tests/fixtures/application-generated/draw/typography-browser-mono-native.fig) | Load the converted TrueType resource offline, create runs, change a label's length, size and width, save FIG, reopen and save in original Draw |
| [Lab Serif](../../tests/fixtures/application-generated/draw/typography-serif-native.fig) and [Lab Mono](../../tests/fixtures/application-generated/draw/typography-mono-native.fig) | Named modern conversions display ASCII and accented CP437 specimens, then save and reopen |

The separate modern FF1s have SHA-256
78b232e749d6a18fe1c422d4fa93e65a8d4547a405cfdef2ab9d96b3e5b7f7c6
for Lab Serif (31,127 bytes) and
07e0f36aef45ee684b728f48f233b1a0b023657958826aed10ef6f923f31bc81
for Lab Mono (39,104 bytes). Both were independently regenerated with
`--native-text-map`, using IDs 29 and 30 respectively. The modern fonts
and converted resources stay private. The public FIGs carry references
and synthetic labels without embedded glyph banks.

Native Save As recalculated the three cache words at 84–89 even when
the label, family, size and width were unchanged. For the first
Dixon-slot browser label, the writer cache was (356,353,3100), and
native Save As stored (417,389,3103). The replacement Labgrid run's
native cache was (394,366,2417). The Python and browser constructors
use the shared modeled bounds for supported records. Their emitted
bytes match each other under the portable test. Exact native cache
equivalence remains open.

The principal disposable RSX run ended through the authenticated socket
at 1,413,202 emulated ms and 91,119 frames. The stopped FAT16 disk
has SHA-256 5fa0f78f88989b68eaa0f32e765d1d130f22df5eb63fd71725aa21812386989d.
The starting stopped image (75fa3a3eec1f2ddf820df855edfe044548bfbcfbf68f42b2a3f94085ac064e585)
and original resources stayed unchanged. Oracle intents and frames,
three acquired FAT12 images, native-staged FIG/FF1 pairs, placement
and auxiliary controls, Ghidra files and held-step receipts are under
`C:/DeskMateLab/private-evidence/typography-20261119`. The initial
graphics mode grid reached a display but subsequent inputs showed no
normal completion. The native print follow-up therefore used a fresh
clone of the stopped disk.

In the private OEM FF1 → CFF → FF1 probe, all 191 mapped nominal
advances match for each original font. Raw contour sequences differ
in 12 Cobb glyphs, one Dixon glyph and 57 Marin glyphs. After merging
adjacent collinear line subdivisions, all drawn sequences match.
The interchange still drops variant identities, hint data, pair
tables and unmapped glyph semantics. The lossless native writer retains
the exact original bytes for all three files.

## Native printing

Draw File → Print → File, with the IBM GRAPHIC driver selected, printed
the same browser-authored BRTYPE.FIG twice. LABIBM.PRN used the independent
Dixon-slot glyph bank and OEMIBM.PRN used the pinned original Dixon.
Two FAT16 extractors agreed on the exact bytes. Both streams contain
printer setup, positioning and 13 ESC L graphics bands, with a final
form feed. The paired profiles verify that the driver rasterizes the
installed outlines to device dots in this path.

| Stream | Bytes | Ink dots | Inclusive dot bounds | SHA-256 |
| --- | ---: | ---: | --- | --- |
| LABIBM.PRN | 3079 | 6804 | (76,108)–(444,284) | 157bf7d8d1068c0c6af395f9cf1e589d6154ee6fbe7921a7a1f52f9755c8214e |
| OEMIBM.PRN | 2849 | 4568 | (80,108)–(434,286) | f2603727c84faecde25c1d8b320642d11430660dc1fd7207e8a0d164f448066e |

The [bounded IBM stream decoder](../../tools/experimental/typography_ibm_print.py)
reconstructs 120 × 72 dpi dot positions from the captured commands and
keeps the raw print streams private. A static comparison found an
extended-byte table at DMPDLASR.RES file offset 0x3f7a that differs
from the display table. LaserJet output, printer-resident substitution,
print-specific kerning and outline-only styles remain open.

The follow-up clone ended at 407,725 emulated ms and 27,989 frames.
Its stopped disk SHA-256 is
9d31712f6b2ec56377d51de7f90c071743e19dc473c6fed476da69074428b05c.
The two clones account for 1,820,927 emulated ms and 119,108 frames.
The automation executable hash is
e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d
and its source checkout revision is 855258da966f1594f568350be59e8e1eca082ed1.
The original program and ROM identities follow the pinned RSX oracle.

## Continuation

- Start with `hintthk-repaint`, `hintoff-repaint` and the pinned original
  Dixon trial. Trace the marker-2 reader in DMFONT.RES and derive how the
  two stem lists and their third words modify the outline at 24 points.
- Use ADVANCE.FIG and the known single-variant Labgrid geometry to
  separate glyph-local pixel snapping, character-origin quantization
  and winding. Retain the 23-case frozen Draw suite as a regression set.
- Use the exact Uf edit fixtures and native cache words to qualify
  justification, rotation, hollow modes and general placement. The current
  browser exposes base-outline authoring and editing. An exact native
  pixel display and additional original dialogs remain open.
- Repeat the named-face trials through Text pictures and Filer cards and
  reports. The shared graphics renderer routes the measured base-outline
  bytes in those formats. Native cross-application creation was outside
  the completed trial set.
- Extend the single-variant controls to alternate em units, character
  ranges, filename collisions and rescan timing. Recover the purpose of
  unresolved bank and metric fields before offering more profiles.
- Compare IBM raster jobs with LaserJet output and pair-table mutations.
  The earlier Marin AV result remains scoped to the observed VGA mode.
- Use the [ecosystem inventory](../ecosystem/acquisitions.md) for First
  Publisher, its FNT resource maps and the Atech font lead. Express
  Publisher and the native DeskMate Q&A Write program remain unacquired.
