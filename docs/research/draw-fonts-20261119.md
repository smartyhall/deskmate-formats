# Graphical font references in DeskMate Draw

The native Draw F6 Text dialog exposed Cobb, Dixon, Marin and System as
outline choices, with point size, percentage width, left/center/right
justification and style controls. A new document authored entirely in
Draw used the original test labels `DIXON 24` and `MARIN 24`. Both
used 24 points and 100% width. A fresh open of the exact native save
showed the appropriate installed faces. The test document is in the
[fixture manifest](../../tests/fixtures/application-generated/manifest.json).
Original resources and full captures remain private.

The `Uf` record has a 30-byte, NUL-padded ASCII family name at
26–55, the observed point-size word at 56–57 and width word at
58–59. The reader retains the remaining descriptor through byte 95
and the six earlier attribute bytes at 20–25. The declared CP437 text
length is at 96–97 and the measured zero word at 98–99. Text bytes
start at 100 and may be followed by one padding byte. The corpus
showed both missing terminal padding and nonzero padding in a few
records. This reader separates the label from its padding and keeps
the complete original record.

The 205 readable historical figures with explicit arc recovery
contain 382 `Uf` records. The observed families were Marin (237),
Dixon (125), Cobb (18), System (1) and Rockwell (1).
These counts identify references rather than glyph availability.

The local `font_resources` reader inspects the pinned FF1 family files
without copying glyphs. The three installed files use a 46-byte
variant descriptor at offset `0x42`. Each exposes ten names,
including the base family and thin, condensed, wide, expanded and
hollow variants. The common header has values 32 and 224 at
positions 14 and 16. Those values are consistent with the covered
byte-code range, pending glyph-directory verification.

| Local resource | Bytes | SHA-256 |
| --- | ---: | --- |
| COBB.FF1 | 61,503 | `891e9f07ed2d9fd5f5c8e75d0facd3d4094e891096a6e77a6a8b3db1518a265f` |
| DIXON.FF1 | 42,049 | `f6cd8cedd1b1a3e6180a8cfca2206f8a5d20c5866bad3629caaf4a87793ff1d7` |
| MARIN.FF1 | 55,782 | `6ecdba8a835ce2b37481552e9d72027c9b3481e5ee1a2a03566b5e22cd85f0a4` |

Run `python -m deskmate_formats.font_resources /path/to/local.ff1`
to inspect a local resource. The browser and Python preview default
to reporting external runs as omissions. Their optional generic
monospace previews identify the substitution explicitly. Geometry,
advances, rotation and other exact FF1 glyph behavior remain open.
The browser also renders the same unrotated embedded-stroke subset
with fixed cell advances as the shared scalable Python projection.
