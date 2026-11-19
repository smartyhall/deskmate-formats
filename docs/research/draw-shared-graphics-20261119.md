# Native arc transfer across Draw, Text and Filer

Draw 03.05.00 opened an independent compact drawing containing one
`UA` arc and a patterned rectangle. Native Save As produced
`XARCH.FIG`. Draw F3 → Select all and Ctrl+Insert put both elements on
the clipboard. File → Run started Text in the same DeskMate session.
Shift+Insert pasted the selection after the original label
`ARC SAMPLE`. Text saved and reopened `TXARC.DOC`.

The same clipboard was pasted into a synthetic Form Setup copy of
the graphics-free G00 fixture. First it was placed on the record/card
layout. Report → Define then opened the report layout where a second
paste placed it in the body. The card reopened in native Filer and the
report reopened in native Form Setup. Both retained the arc and the
patterned rectangle.

| Container | Arc upper left | Rectangle upper left | Stored relocation from FIG |
| --- | --- | --- | --- |
| Draw FIG | (950, 520) | (2200, 600) | (0, 0) |
| Text picture | (100, 110) | (1350, 190) | (−850, −410) |
| Filer card `F` | (1800, 660) | (3050, 740) | (+850, +140) |
| Filer report `R` | (2000, 1100) | (3250, 1180) | (+1050, +580) |

The pasted leaves retain the native kinds, sizes, extents,
and exact GATTR/geometry bytes following the coordinate fields.
Text retains its measured picture envelope at display column 0, with
a one-byte payload suffix `19`. The indexed Filer database stores
one 205-byte escaped chunk per section and each decodes into 122
bytes of shared form data. Neither embedded form carries the
standalone FIG palette block. The three applications used the same
observed default palette in this installation. Preservation Workbench
uses its neutral colors for graphics without their own palette.

All three projections use the shared quadratic SVG renderer. A standalone
arc calculation can therefore be tested in the actual Text envelope
and Filer escaped chunks without an application-specific geometry engine.
The RSX raster profile's phase and clipping remain specific to the
standalone Normal viewport.

The session ended at 155,018 emulated ms and 9,616 frames, including
the stroke and font trials. Both stopped-disk extractors agreed.
The exact eligible FIG, DOC and FIL bytes are in the
[application-generated fixture manifest](../../tests/fixtures/application-generated/manifest.json).
