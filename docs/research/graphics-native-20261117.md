# Native DeskMate Draw, Text and Filer graphics

Draw, Text and Form Setup in the DeskMate 03.05.00 installation share a
serialized graphics-form representation. Native Copy and Paste transferred a
line, rectangle, ellipse and a three-primitive selection. The three containers
retain the same element structure and style bytes for the measured shapes.
Clipboard transfer wraps selections in an object group and relocates their
coordinates. Form Setup then encodes the binary form for its database. Its
36-line control and shipped forms demonstrate that a GRAPHICS row can store
one fragment of a form containing many display elements.

[Structured evidence](../evidence/graphics-native-20261117.json) records
full specimen hashes, parent identities, raw differences and disk lineage.
The [fixture manifest](../../tests/fixtures/application-generated/manifest.json)
describes the 36 exact synthetic native files and clipboard source hashes.
The prior QRECORD fixture supplies the graphics-free control with identical bytes.

## Reproduction and evidence scope

The branch starts at `9001e8864d7b9e1c5d0ec2deea77b3adf2679901`, which
includes PRs #110 and #111. Six independent boot sessions used lineage-checked
disposable copies of the earlier RSX DOS 5 installation. The machine was a
Tandy 1000 RSX with a 25 MHz 386SX, 4 MiB RAM and internal VGA. The 86Box
automation source revision was `855258da966f1594f568350be59e8e1eca082ed1`.
The binary SHA-256 was
`e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d`.
The ROM collection revision was `908394b690f7da28f47727d9876774fd672c4ed3`,
with RSX BIOS SHA-256
`17984fe7c31ab6b51c96272ba8ee89580eb139aab01399a1b865f6743f3334f2`.

| Session | Terminal emulated time (ms) | Frames | Native scope |
| --- | ---: | ---: | --- |
| draw | 64,026 | 4,031 | Draw launch, keyboard-mode line, first paste into Text |
| corpus | 155,321 | 9,555 | Reopen, Text position and adjacent pictures, Draw rectangle, first Form Setup pastes |
| extended | 140,224 | 8,628 | Draw edits, group failure, start-of-stream Text picture, shipped card/report views |
| serial | 167,797 | 10,387 | Socket mouse selection and coordinate controls, graphics deletions and Form Setup edits |
| pressure | 70,362 | 4,351 | 36 independently drawn lines, reopen, two-row GRAPHICS storage |
| boundary | 80,271 | 4,955 | 1,016-byte GRAPHICS chunk, valid grouping and a patterned polygon |

The controller used authenticated loopback commands with the guest held
between time steps. It retained request/reply receipts, actual make/break codes,
relative mouse commands, frame hashes and PNGs. Saves were checked through the
application title and resulting display, DOS exit, stopped disk extraction with
7-Zip and an independent FAT16 directory/cluster read. The six terminal times
sum to 678,001 ms. A captured frame shows only the resulting visible state,
and menu transitions can repaint after returning to the application.

Original disks, commercial files, modified shipped databases, screenshots,
Ghidra listings, private vectors and journals stay in
`C:/DeskMateLab/private-evidence/graphics-native-20261117`. Each session has
a prepared receipt, before inventory, actual stepped actions, final inventory
and stopped image. The extractions agree byte-for-byte for all published files.

## Draw native controls and file layout

From DOS in the installation directory, `DESK DRAW` opens an untitled
canvas and `DESK DRAW D01.FIG` reopens a saved drawing. F2 offers New, Open,
Save, Save As, Page Setup, Print, Exit and Run as state permits. The F7 tool
list showed Select, Line, Rectangle, Ellipse, Text, Brush, Filled Brush, Arc,
Polyline and Polygon. F3 provided clipboard commands, Select All, Move, Resize
and corner edits. F4 provided Duplicate, ordering, transforms and group commands.
Line, rectangle, ellipse, text, move, resize, color change, individual
selection and deletion were exercised, along with grouping and patterned
polygon creation. Brush, arc, ordering commands and printing were observed
in menus.

The baseline configured a PS/2 mouse in 86Box while native F10 → Setup showed
**Serial mouse, COM1**. Draw F6 → Use keyboard enabled arrow positioning and
Space start/finish on that baseline. For the last three sessions, the
disposable machines used 86Box's `msserial` device. Relative pointer and button commands
then worked over the native socket. The ROM, disk contents at clone time and
DeskMate mouse settings were preserved across that change.

Every usable native FIG has the following outer structure. Offsets are zero-based
and ranges exclusive at the end.

| Bytes | Native observation |
| --- | --- |
| `0–22` | Page Setup prefix with signature `14 46 49 47`. The guide assigns `14` to Draw88 and `10` to Draw. The installed application's ordinary Draw title saved the `14 FIG` profile. |
| `22–40` | 18-byte FORM HEADER. First two bytes are flags. The words at 24 and 26 match list size in words and strokes size in bytes. Remaining bytes are preserved. |
| `40–44` | Little-endian list and stroke byte counts. List count equals twice the word count at 24. Stroke count duplicates the word at 26. |
| `44–(44 + list bytes + stroke bytes)` | Display list followed by the stroke region. Length arithmetic determines the boundary. |
| Next two bytes | `10 00` precedes the palette. Its value agrees with the number of entries. |
| Next 64 bytes | Sixteen `index, red, green, blue` entries. The measured indices cover 0–15. Entry 1 is `01 C0 C0 00`. |
| Last byte | Zero in the measured FIG files, retained as an opaque trailer. |

This confirms the Appendix A header sizes and region start. The palette
starts two bytes beyond the documented form-end arithmetic, and the file
contains one extra byte after the entries.

| Control | Native result |
| --- | --- |
| D00 | Empty initial canvas and deletion of a sole line both disabled Save As. No empty FIG was obtained. |
| D01 / D02 | The horizontal line at `(800,985)–(1200,985)` was reopened and resized to end at `(1625,985)`. Its start, y values and style bytes stayed fixed. |
| D03 | The first keyboard move sequence did not move the geometry. The saved result is byte-identical to D12. |
| D04 / D05 / D06 | A rectangle at `(600,985)–(2000,2305)` was the independent parent. Resize held the upper left and changed both lower-right coordinates. Move translated both endpoints by `(800,1760)` with dimensions preserved. |
| D07 / D07C | The initial keyboard weight attempt produced no measured style change. A socket mouse color selection changed the rectangle's line index from 1 to 10, leaving its palette and bounds intact. The line changed visibly from yellow to green. |
| D09 / D10 | D09 added a partially off-canvas ellipse to D04. D10 added `GRAPH7Q9`. An extended `Uf` record contains the literal string and font metadata. |
| D11 / D17 | D17 has line, rectangle and ellipse in that display order. The D11 deletion leaves the first two records and rewrites the directory and packed list. |
| D12 | Reopen and Save As without edits preserved the entire list, strokes and palette. Byte 32 changed from 1 to 2, so whole-file identity does not hold for this control. |
| D13 / D14 | Make Object on D10 produced an 18,229-byte file with implausible list references and repeated tags. Follow-on Duplicate and Clear attempts produced an out-of-memory dialog. The outer lengths still parse. These files remain private and the supported reader rejects their lists. |
| D16A / D16B | Independent serial-mouse drawings with the same horizontal drag, translated one native screen pixel, changed each stored x integer by +13 with y, width and style intact. |
| D18 | 36 independent line drags across a six-by-six grid produced a 979-byte FIG with an 866-byte list. Native reopen displayed the grid. This is a separate clean growth control. |
| D19 / D21 | Make Object on the compact D17 selection produced one valid group. Selecting it activated Break Object. D21 restores three top-level entries. All three leaf records match D17 byte-for-byte in both controls. |
| D20 / D22 | Reopening D20 confirms a four-sided outline. Applying diagonal hatching to the selected polygon changes its pattern byte from `FE` to `09` at element offset 24. Its five stored points, including the repeated start, stay identical. |

## Shared form payload

The [Tandy Draw reference](../reference/tandy-draw-format.md) predicts the
outer layout. The local 3.03 SDK `CSRFORM.H` describes element structures and
the Technical Reference describes display-list management. Their respective
SHA-256 identities are
`4f51eb854cc5a250cc3ee8d36fb9e105c4a6594c230d99a796ab154912a284a3` and
`c4ce5457339234071ef46ac0ec021b7e2674b77cb869103389193ce2bed1352a`.
The following combines captured bytes with independently described structural
names. The use of specific print units and unmeasured modifier semantics remain
inferred.

- A little-endian count precedes pairs of word offset and tag. The pairs are
  in display order. The physical records may run in reverse creation order,
  as on D17. Offsets count words from the list start.
- Each element has type and modifier bytes followed by four integer/fraction
  coordinate pairs. Negative integer bounds occur in D09. The parser retains
  each original 16-bit member. A 16.16 projection fits the fractional
  coordinates from native scaling and the measured shipped artwork.
- `L 00` takes 20 bytes including its two style bytes. `R FE` and
  `E FE` take 24 bytes with line and pattern attributes. D07C establishes the
  rectangle line-color byte at element offset 18. D02 and D16 establish
  endpoint behavior independently of display scaling.
- `OO` stores an 18-byte bounding record before a word count and the
  group's word-offset part list. One Text picture wraps all selected Draw
  objects in this structure. Form Setup stores an independent group for each
  pasted picture. Nested groups occur in shipped card artwork.
- Extended `U` records carry a word size at offset 18. Shipped `UP` records
  match a fixed header with style, two extents, fill/connect bytes and a
  point count followed by pairs of local 16-bit points. `UA` and the
  Draw `Uf` subtype remain opaque. Text strokes in shipped forms stay intact.

The 400-world-unit D01 line appears with identical type, modifier, attributes
and endpoint separation in all three applications. Draw stores its origin as
`(800,985)`, Text stores the relocated origin as `(100,110)`, and Form Setup
stores the card origin as `(1000,1100)`. The three containers therefore carry
the same serialized **record grammar and geometry**, with a transformation
of coordinates and grouping at clipboard/export boundaries. Complete
payloads and their reserved form-header words can differ. There is no
separate FIG palette block in measured Text or Filer payloads.

## Draw pictures in Text

Draw F3 → Select All followed by Ctrl+Insert copied a picture. Draw F2 → Run
with `TEXT.PDM` launched Text inside the same DeskMate session. Shift+Insert
pasted at the Text cursor. Escape returned to Draw. Returning all the way to
DOS did not preserve the usable clipboard in the measured sequence.
`DESK TEXT TP01.DOC` on the next boot visibly reopened the pasted line with
`BEFORE LINE` and `AFTER LINE` around it.

In the measured default formatted DOC prefix, a picture envelope is
`01 | length:u16le | column:u16le | payload[length] | length:u16le | 02`.
TP01 starts the envelope at 35, payload at 40, and following ordinary text at
114. Its 71 payload bytes include the form header, size buffer, list, strokes
and one unexplained final byte. That extra byte counts toward both envelope
lengths. Its value varies among native pictures. TP03 begins the picture
directly at offset 22, a native extension to the placement rule summarized
in the Appendix A reference. TP04 has adjacent envelopes and ordinary text
immediately follows the final `02` without a new CRLF.

TP02 changes only file offset 38, the low byte of the zero-based display
column, from 0 to 3. TP06 contains the complete compact D17 selection of
three shapes. TP07 copies just the selected ellipse from that same Draw
file. The first attempt to paste the wider D10 selection into an empty Text
document produced an explicit width error. Shift+Down from the picture
position selected TP06's whole picture and Delete removed it in TP05.
Native To ASCII also removed the picture and formatted header, preserving
the two lines of ordinary text in TPASCII.

## Form Setup graphics and database storage

`DESK FORMSET` created G00 with the same FTXT_A field and default report
sections as the earlier QRECORD. G00's bytes are identical to
`qrecord-empty.fil`. There is no GRAPHICS table in this control. DOS COPY
created exact mutation parents. Draw File → Run launched `FORMSET.PDM`
with the cloned file. The editor accepted the Draw clipboard via Shift+Insert.
A native mouse selection enabled Clear, Move Picture and Size Picture.
G02, an earlier attempted keyboard picture selection, made no file change.

| Comparison | Database effect |
| --- | --- |
| G00 → G01 | Added GRAPHICS data and index pages 8 and 9. Header, directory, DBCOLS data and index changed. The existing LAYOUTS and DATA pages stayed byte-identical. |
| G01 vs G03 | Independent pastes from G00 translate the same line. 57 byte positions differ, all on GRAPHICS data page 8. |
| G04 → G05 | Pasting a second picture adds another top-level group to the same GRAPHICS row. 144 positions change on page 8. |
| G04 → GMOVE / GSIZE | 58 / 23 positions change on page 8. Move preserves dimensions and size preserves the integer top-left. The resized end coordinates include nonzero fraction words. |
| G05 → GDEL | Selecting and deleting the rectangle leaves the line and one GRAPHICS row. 152 positions change on page 8. |
| G00 → GCOL | The pasted D07C rectangle retains color index 10. Its placement differs from G04. |
| G00 → G18 | One pasted 36-primitive picture grows GRAPHICS to data pages 8 and 10 with index page 9. Its indexed `F`, `&` chunks have 1,015 and 392 encoded bytes. |
| G00 → G20 | Placing that picture at x 1800 instead of 1000 produces 1,016- and 373-byte chunks, as predicted from the byte escapes at the boundary. The indexed rows now occupy pages 10 and 11 and page 8 stays empty. |

The measured transform replaces binary bytes `00–07` with `07` and a
second byte in `40–47`. Other bytes, including high-bit bytes, pass through.
The GRAPHICS columns are `RECORD` (width 1) and `BITS` (declared width
1,018). The largest observed chunk has 1,016 stored bytes. `F` starts the card
form, `R` starts the report form, and `&` continues the current form. Decode
in index order and validate against the form sizes. G18 de-escapes and
reassembles to exactly 842 bytes with a single group and 36 line records.
G20 has the same decoded extent and same 36 line geometries under uniform
translation. Its first chunk preserves the escape pair that begins at
offset 1,014.
The three forms sent between applications exercise shared serialization beyond
any assumption based on the rendering API.

## Shipped CARMAINT and INVNTORY

The original commercial bytes were hash-pinned to the
[cross-application baseline](cross-application-db.md). Only disposable
copies were opened. Form Setup Report → Define showed the separate report
artwork for both files.

| Database | Card form | Report form |
| --- | --- | --- |
| CARMAINT | `F & &`, 2,198 decoded bytes. One outer group of 39 parts, including nested artwork groups, line segments, polylines and a title. | `R`, 606 decoded bytes. One group with a title and 492 stroke bytes. |
| INVNTORY | `F`, 612 decoded bytes. Three nested group records enclose 11 lines forming the card outline. | `R &`, 1,037 decoded bytes. One group with a title and separate stroke data. |

The left and right car wheel groups at display-list byte offsets 422 and 272
each contain five near-concentric ellipses. The outer bounds of the two wheel
groups project to x about 147–220 and 398–471 at the measured card view scale,
matching the native wheel positions. The larger `UP` records link to the
body and shadow contours. Independent SVG previews recover the wheels, car
outline and inventory border. They retain geometric shapes and use
approximate styles, with native fonts, arc reconstruction and fill patterns
still outstanding. The renderer lists omitted element types in SVG metadata.

Clicking the car selected both the illustration and its card title as a
single picture. Deleting it from CDEL removed both visible items. The report
title still displayed. The sole saved GRAPHICS row is the report form, now
at page 6 under ID 16. Its decoded 606 bytes are identical to the matched
CEDIT report-view control. LAYOUTS rows stayed identical through deletion.
The report-view controls CEDIT and IEDIT changed seven and six file byte
positions respectively on GRAPHICS pages. The differences decode entirely
to the last four FORM HEADER bytes. The display lists and strokes remain
identical to the shipped inputs. INVNTORY's older DBCOLS entries omit the
final uniqueness field on non-self-schema descriptors. The Filer reader
accepts that profile and retains the five stored fields.

## Static checks and Drawlist

The installed Draw module contains a `DMEFORM` resource-name candidate at
file offset 77576. Form Setup contains `DMFORM` at offset 76. The installed
runtime also contains both resources and a clipboard accessory. Resource-name
matches are static leads. Native transfers and decoded typed records establish
the shared serialization independently.

The repository MZ inspector verified the 512-byte FORMSET.PDM executable
header. A private, bounded Ghidra 12.1.4 decode of its 16-bit load image
corroborated the codec. At file offset `0x5E77` the encoder checks output
position against 1,015 before emitting a byte or pair. The low-byte path
writes the `07` prefix at `0x5E8D` and sets bit 6 at `0x5E96`. At
`0x5FCB–0x5FDB` the decoder tests for `07`, consumes the next byte and
clears bit 6. The predicted 1,016-byte chunk was then confirmed by G20.
These file offsets identify the inspected instructions. A runtime trace of
the Video Manager selector remains open.

The SDK Development Guide documents `DRAWLIST.PDM`. No executable under
that name was located in the staged installed tree, the available unpacked SDK,
or listings of the staged DeskMate and SDK ZIP archives. There is no native
Drawlist output to compare.

## Readers and usage

```powershell
python -m deskmate_formats.draw tests/fixtures/application-generated/draw/d17.fig
python -m deskmate_formats.draw --svg tests/fixtures/application-generated/draw/d17.fig > preview.svg
python -m deskmate_formats.text --inspect tests/fixtures/application-generated/text/tp04.doc
python -m deskmate_formats.filer --graphics tests/fixtures/application-generated/filer/g18.fil
```

`text.parse_file` returns ordinary text, absolute picture offsets, display
columns and unchanged payloads. The ordinary text projection indexes each
picture's insertion point. The existing text-only extractor continues to
reject documents containing pictures. `graphics.parse_bytes` accepts the
shared payload, with `text_picture=True` for the measured Text trailer.
`filer_graphics.decode` returns each row location, encoded chunk, binary
payload and parsed form. The FIG reader validates duplicated sizes, directory
and group bounds and palette extent. The SVG preview renders lines,
rectangles, ellipses and polylines in display order, retaining unsupported
records through the reader API.

The portable tests use exact published files plus malformed lengths, picture
placement, escape and group-pointer controls. The readers are read-only.
The next discriminating experiments are independent arc and brush controls,
stroke-font reconstruction, and comparison against an actual Drawlist-generated
array if the utility becomes available.
