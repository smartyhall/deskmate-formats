# DeskMate Draw recovery handoff

The campaign head `dcb10ce63e5bd44bc9fc4497d64aaa3b0d4d5b94` and
integrated main `b3aa1a7170f8754902bf6bd3fa825420775a4509` had identical
trees. The campaign checkout, index, stashes and detached PR #120
baseline contained no unpublished work. All four main portable and
packaging jobs passed. The recovery used the existing captures and did
not advance an emulator. The [campaign report](draw-campaign-20261119.md)
provides the integrated results and original session times.

## External fonts

The verified FF1 glyph directory gives 224 code extents and nominal
advances for each of Cobb, Dixon and Marin. The outstanding contour
problem starts inside those extents. The first three words in some
sampled records are consistent with a short header containing geometry,
but contour counts, coordinate encoding, curve commands and winding
remain unverified. The [font report](draw-fonts-20261119.md) pins the
actual resource hashes and explains the validated directory.

Recovery identified a **candidate pair-adjustment table** after the
glyph block. The little-endian pointer at outer byte 38 equals the
glyph end for Dixon and Marin. Cobb has pointer zero and no tail.
The Dixon and Marin tails each have a ten-byte header of five words,
then strictly sorted, unique four-byte records. The first two bytes
of each record look like a character pair and the last two like a
signed adjustment. The meaning of header words 3 and 4, units and
actual native application remain open.

| Family | Tail offset | Tail bytes | Header words | Pairs | AV / VA words |
| --- | ---: | ---: | --- | ---: | --- |
| Dixon | 41,683 | 366 | 1, 366, 255, 300, 89 | 89 | −173 / −173 |
| Marin | 55,184 | 598 | 1, 598, 255, 300, 147 | 147 | −244 / −219 |

The table contains no adjacent pairs from `DIXON 24`, `DIXON 42`
or `MARIN 24` in the corresponding face. It cannot account for
the observed Dixon width change by simply looking up adjacent pairs.
Run the [pair-table probe](../../tools/experimental/draw_ff1_spacing_probe.py)
with `PYTHONPATH=src`, a local FF1 file and labels such as `AV`,
`VA`, `"DIXON 24"` and `"DIXON 42"`.

Start the next native typography run with single characters such
as `I`, `H` and `O` at a large point size, then use `AV`, `VA`,
`A V` and standalone characters at the same size to measure glyph
origins and total extents. Vary width and point size separately.
Use the Marin AV/VA asymmetry to test the pair-table interpretation
and its scaling. A bounding box alone cannot distinguish placement
adjustments from glyph ink bounds. Keep original outlines private
and regenerate the frozen comparison suite when rendering changes.

## Stroke and brush readback

Reanalysis of the saved Normal-zoom pixels quantified the still
unsupported oblique stroke footprints. Each group below combines the
eight line styles at the indicated stored weight in `STROKES.FIG`.
The foreground mask counts green pixels in bounded neighborhoods
around the projected diagonal. The source grid was tool-authored,
displayed natively and later saved as the committed
`stroke-grid-native.fig`. The captured input was the earlier
`STROKES.FIG`. These measurements apply to its one positive slope.

| Stored weight | Native pixels | Independent pixels | Intersection | Union |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 209 | 456 | 200 | 465 |
| 1 | 491 | 456 | 219 | 728 |
| 2 | 2,397 | 456 | 456 | 2,397 |
| 3 | 3,771 | 456 | 456 | 3,771 |

In the saved `BRUSHES.FIG` frame the open eight-point `UP` uses
1,616 native yellow pixels and the closed six-point `UP` uses 2,821.
The independent footprint uses 192 and 320 pixels, respectively.
The intersections are 179 and 318 pixels. Those counts quantify
a footprint gap and do not identify the brush kernel. To separate
pen shape from stepping, measure single straight brush gestures at
one length and width in opposite directions and at multiple slopes.
For ordinary oblique lines, vary orientation independently of style
and weight. The previous axis-stroke masks remain qualified only
for the tested axis-aligned cases.

## Private evidence and rerun anchors

The private campaign directory is
`C:/DeskMateLab/private-evidence/draw-native-20261119`. All eight
`stopped.img` hashes, 120 extracted file entries and 100 repaint
frames match their corresponding receipts. Full frames, disk images,
Ghidra projects and commercial
resources remain there or in the prior graphics campaign's archive.

| Area | Private evidence relative to the campaign directory |
| --- | --- |
| Baseline and viewport | Root `native-profile.json`, `verified-disk.json`, `map-normal-stable.png`, `map-zoom-2x.png` |
| PIPES and BRIDESHW | `failures/inputs/` and matching reopen/repaint frames, native saves under `failures/extracted/DESKMATE/` |
| Arc geometry and patterns | `geometry/`, including `arcstud-repaint.png` and `patstud-repaint.png` |
| Text and Filer clipboard | `shared/`, including `XARCH.FIG`, `TXARC.DOC` and `GARC.FIL` in the extracted tree |
| Oblique strokes and brushes | `shared/strokes-repaint.png`, `group-cross/brushes-repaint.png`, `recovery-pixel-check.py` |
| Native writing | `milestone/`, `stroke-milestone/`, `group-cross/`, `attrs/`, each with extraction and verification receipts |
| Browser QA and Classic UI | Root `gallery-qa.cjs`, `workbench-qa.cjs`, `browser-roundtrip.cjs`, `final-browser-qa.cjs` and private screenshots; native font dialog and selection captures under `shared/` and `group-cross/` |
| Static Draw decode | `static-draw/DrawDispatch.java`, `DrawDispatchMore.java`, `DrawGroupOffsets.java`, `ghidra-payload.log`, `ghidra-more.log`, `ghidra-group.log` |

The installed FF1 files and `DRAW.PDM` are under
`C:/DeskMateLab/private-evidence/graphics-native-20261117/glyphs/after/extracted/files/DESKMATE`.
SDK layout declarations are under
`C:/DeskMateLab/references/oldskool/extracted/sdk-3.03/Development-Disk-1`
in `CSRBASE.H`, `CSRFORM.H` and `DMDECL.H`. Manufacturer PDFs are
under `C:/DeskMateLab/SDK-Uploads`.

The valid Ghidra project imports the **stripped** MZ load image at
synthetic `1000:0000` with `x86:LE:16:Real Mode`. Map a Draw file
offset by subtracting `0x200` before adding the synthetic base.
The first raw-import attempt did not produce the intended mapping.
Use the payload logs for the group accessor at file `0x7ba3`, the
recursive caller at `0x7bd8`, the UA/UP dispatch at `0x9467`, and
the UA transform at `0x960e`. These are file offsets, with no
runtime segment assignment implied. The group caller includes a
font test, leaving its role in PIPES repaint unproven. The
original and native resave still match; the five-reference
substitution still differs by 108 pixels. Trace the actual repaint
caller before assigning meaning to that difference.

For new native work, clone a verified stopped disk with its
original configuration and NVRAM into a new machine directory.
Use the pinned Tandy 1000 RSX, 25 MHz 386SX, 4 MiB, internal VGA and
COM1 serial mouse profile. Keep controls on the authenticated
loopback socket. The [oracle procedure](draw-oracle-20261119.md)
documents the launch and stop/extraction commands. The harness
retains intent, receipt and PNG for each label. Wait for the DOS
copy summary before ejecting a staged floppy. Pace dialog input,
use extended Down scan code `0x150`, and confirm a highlighted
menu command with Enter when the mouse action only highlights it.
The [UI notes](draw-native-ui-20261119.md) distinguish browser shortcuts
from native ones.

The native writer trials, Text replacement picture, Filer clipboard
transfer and browser round trip are already represented in the
merged campaign. There were no pending saved controls to promote in
these areas. The frozen suite and all four rendering milestones are
integrated. This recovery changes evidence and documentation only, so
the existing milestone PNGs and SVGs keep their identities.

## Usage

The original completion receipt preceded usage exhaustion. The
[recovered rollout tail](../evidence/codex-usage/20261119-draw-pr122-recovered-tail.json)
ends with the repeated event at 08:52:22.622 UTC. Its last event
with meter data, at 08:52:22.393 UTC, records 100% for the
300-minute window and 30% for the 10,080-minute window. The final
repeated event contains no meter values. The resumed recovery
observations belong to the new assignment. The recovery recorded
zero additional emulated milliseconds.
