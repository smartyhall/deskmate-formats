# Native FIG editing and browser round trip

The [Python writer](../../src/deskmate_formats/draw_writer.py) validates
the FIG and keeps its serialized page setup, form header, strokes,
palette and trailer. Its
[shared list edits](../../src/deskmate_formats/graphics_edit.py) replace
only known fixed-size top-level record fields. Exact-copy mode retains
the entire input, including the measured legacy arc length when
explicitly enabled. Editing such a recovered input remains outside
the qualified profile. The first edits are move/recolor line and resize
an ordered rectangle about its top-left. The fixed 16.16 arithmetic
accepts exact fractional values.

The offline [Workbench](../../examples/draw-workbench/workbench.html)
produced the tool-generated FIGs via its actual UI. Chromium and the
Python writer independently produced identical bytes. A held RSX
clone opened both figures in Draw 03.05.00. The browser-created file
and the exact native follow-up save are both preserved as fixtures.

| Operation | Browser output | Native result |
| --- | --- | --- |
| Move D01 by `(425.5,390.25)` and recolor to palette index 10 | `BMOVE.FIG`, line `(1225.5,1375.25)–(1625.5,1375.25)` | Native keyboard edit moved both endpoints by `(300,-8)` and retained green. `BMOVESAV.FIG` reopened with bounds `(1525.5,1367.25)–(1925.5,1367.25)`. |
| Set D04 dimensions to `1855.5 × 1020.25` | `BRECT.FIG`, rectangle `(600,985)–(2455.5,2005.25)` | Draw Save As preserved geometry, style and palette. Only file byte 32 changed from 1 to 2. `BRECTSAV.FIG` reopened with the same rectangle. |

The line keyboard sequence was entered through the Edit menu with the
intent to test a resize. The saved coordinates establish a translation.
The observed result qualifies a native edit, with no claim that the
sequence selected Resize. The copied line and rectangle in the untouched
original source fixtures retain their earlier identities.

The run ended at 266,089 emulated ms and 16,461 frames. The
stopped disk has SHA-256
`3a51176f7bb7ccc8668caf343c55a76ae831cdbdf19fa3cd9cb6908ec8e0f335`.
Independent 7-Zip and FAT16 extractions agreed on all four round-trip
files. Chromium opened both extracted native saves, displayed the
expected bounds in the inspector and downloaded them unchanged.
Exact file identities, source identities and provenance classes are in the
[fixture manifest](../../tests/fixtures/application-generated/manifest.json).

## Flat display-list edits

The Python writer also appends a line, ellipse, open polyline or closed
polygon and deletes a top-level record in the qualified packed flat
format. Before relocating records, it checks the allocator words,
directory packing, original record lengths and the empty stroke bank.
Reordering only rewrites the top-level entries and preserves physical
record locations. Existing content survives byte-for-byte in the
surviving records. Empty lists and structures requiring unqualified
group or resource relocation receive a specific refusal.

[draw_writer_trials.py](../../tools/experimental/draw_writer_trials.py)
generated five candidates. Original Draw opened all five, displayed the
expected results, saved them under new names and reopened the resaves.
Independent stopped-disk extraction matched 7-Zip. Native Save As
changed byte 32 for appends. It also renumbered top-level tags in the
delete and reorder controls while preserving the leaves and their
relative drawing order. Rectangular outline pixels cover the ellipse
after the order change. That reordered canvas differs from the
ellipse-over-rectangle canvas in 153 pixels inside crop bounds
`[97,110,161,200]`. The session ended at 301,250 emulated ms and
18,619 frames, including the stroke milestone recaptures.

The browser exposes the three verified in-place edits. The additional
flat list operations are qualified in the Python writer. Group
creation, ungrouping, palette writes and graphical-text editing
remain separate compatibility goals.
