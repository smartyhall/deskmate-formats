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
start at 100 and may be followed by padding. The historical corpus
showed zero or one padding byte, including nonzero padding in a few
records. The native-saved typography control also uses two zero bytes
after some even-length strings. This reader separates the label from its padding and keeps
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
positions 14 and 16.

Each sampled file also has a glyph block starting at `0x212`,
immediately after the outer variant directory and its four-byte
descriptor. Its little-endian length at inner +4 bounds the glyph
block. Cobb reaches exact EOF, while Dixon and Marin retain a
separate trailing region.
The inner header repeats first code 32 and count 224 and has word
1000 at +12. The two-byte nominal advance table begins at inner
+76. The 224-entry little-endian 32-bit offset table follows at
+524. Offsets are relative to the inner block, increase strictly
and start at +1420 immediately after both tables. This identifies
each glyph's stored extent without decoding its contour bytes.

Using the adjacent advance words and 24 points at 1,000 world
units per inch gives 1,800 world units for the Cobb `VECTOR 42`,
matching the native extent. The same estimate gives 1,516.3 for
Dixon `DIXON 24` and 1,660.7 for Marin `MARIN 24`. Their observed
widths are 1,530 and 1,683. The native Dixon permutation changes
the saved width while keeping the same glyph counts. Those results
separate nominal character advances from the native text extent.

| Local resource | Bytes | SHA-256 |
| --- | ---: | --- |
| COBB.FF1 | 61,503 | `891e9f07ed2d9fd5f5c8e75d0facd3d4094e891096a6e77a6a8b3db1518a265f` |
| DIXON.FF1 | 42,049 | `f6cd8cedd1b1a3e6180a8cfca2206f8a5d20c5866bad3629caaf4a87793ff1d7` |
| MARIN.FF1 | 55,782 | `6ecdba8a835ce2b37481552e9d72027c9b3481e5ee1a2a03566b5e22cd85f0a4` |

Run `python -m deskmate_formats.font_resources /path/to/local.ff1`
to inspect a local resource. Add `--glyph-index` for bounded record
extents and nominal advances. The browser and Python preview default
to reporting external runs as omissions. Their optional generic
monospace previews identify the substitution explicitly. Geometry,
advances, rotation and other exact FF1 glyph behavior remain open.
The browser also renders the same unrotated embedded-stroke subset
with fixed cell advances as the shared scalable Python projection.

The [recovery handoff](draw-recovery-handoff-20261119.md#external-fonts)
identifies candidate pair-adjustment tables after the Dixon and Marin
glyph blocks and proposes a native test of their effect on placement.
