# Print Companion document observations

These observations come from files written by the five original branches
on the Tandy 1000 RSX OEM DeskMate 03.04.04 installation. The
[application survey](../research/print-companion-20261123.md#native-application-survey)
gives the creation sequence. The
[fixture manifest](../../tests/fixtures/application-generated/manifest.json)
and [evidence manifest](../evidence/print-companion-20261123.json) record
the original guest paths, lengths, and SHA-256 values. The independent
FAT16 reader and 7-Zip 26.05 extracted identical bytes.

| File | Length | Byte-level observations |
| --- | ---: | --- |
| `W0414155.CRD` | 242 | NUL-terminated description at offset 0. Two spans contain the face name `Cobb` at offsets 0x2b and 0x98. Two NUL-terminated strings begin at 0xda and 0xe5 and match the Front and Inside panes. The value 13 immediately before the strings matches the byte length of the inside text including its terminator. |
| `W0414325.NOT` | 127 | Description at offset 0 and `Cobb` at 0x2b. The body begins at 0x6b, with CR between the two lines and a terminal NUL. The bytes at 0x17–0x69 match those of the two-panel card in this trial. |
| `W0414444.PER` | 188 | Description at 0 and `Cobb` at 0x2a. NUL-terminated date, salutation, body, and closing begin at 0x76, 0x87, 0x96, and 0xaf. The little-endian values at 0x6a, 0x6c, 0x6e, and 0x70 are 17, 15, 25, and 11 and match the lengths of those strings including terminators. |
| `W0414359.NTG` | 205 | Description at 0 and `Dixon` at 0x31. The literal two-line entry and its second line are absent from the extracted bytes. The description persisted across cold boot, but explicit Open showed a blank body. The warm Open alone had overstated persistence. |
| `W0415039.NOT` | 239 | Illustrated control. Existing shared graphics reader parses the 106-byte form at 0x6b as a line followed by two style or auxiliary records. The same text as the unillustrated notice begins at 0xdb. |
| `LABLINE.FIG` | 195 | `14 46 49 47` header. The existing Draw reader parses the object at list offset 14 as one line, in addition to its page and style records. Native Draw recovered the line on Edit from Graphics Manager. |

The first four files live in separate application directories under
`DESKMATE/DOCUMENT`. Save As asks for a description, and the application
chooses the `W…` basename. Only one basename per type was examined. The
common leading layout suggests related editor containers, while each
file's remaining layout needs tests that change one field at a time.
The existing recovery suite has no writer for these four extensions.

Graphics Manager created its file under `DESKMATE/DOCUMENT/ILLSTRTN`
and launched the original Draw editor. The thumbnail browser's
Illustrations and Stationery classes and the installed `.DA` files
identify external resource leads. Cards, Notices, Personal Letters,
and Name Tags also contain a `*.FIG` reference in their installed
modules. A matched Notices control selected LABLINE.FIG through Graphics →
Illustration and saved **MOON LINE NOTICE**. The file gained 112
bytes before the otherwise unchanged text. A little-endian 112 at
0x67 matches that extent. The first 106 bytes are a bounded, parseable
display list and strokes, with a line using stored coordinates that
differ from the original FIG. The remaining six bytes have unverified
semantics. These results establish that this Notices path embeds a
graphics form. They do not establish how Stationery or the other editors
store graphics.

The related `.PRN` files are printer jobs generated from the card.
The IBM stream encodes columns of printer dots, and the HP stream
encodes PCL raster rows. Neither capture provides a lossless path
back to the editor's document fields. See the
[printer-stream description](../research/print-companion-20261123.md#two-print-streams-from-one-card).
