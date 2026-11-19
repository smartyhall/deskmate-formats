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
flat list operations are available in the Python writer.

## Grouping, native transforms and Text writing

The Python writer wraps known flat leaves in one `OO` and can flatten
one group of directly owned known leaves. It preserves the leaves'
original bytes and display order. The writer allocates fresh
top-level tags when ungrouping because the saved children have
no per-child directory tags. Both independent candidates were opened,
saved and reopened in original Draw. Their canvases matched exactly.

Break Object was enabled on this valid group. It removed the group
without changing a leaf or a pixel. Make Object on those leaves
rebuilt the same bounds and offsets, with a new top-level identity.
On a separate copy, Flip horizontal reflected the children around
`(600 + 3501) / 2 = 2050.5` world units and removed the group wrapper.
The ellipse's x bounds changed from 1080.5–3500 to 601–3020.5.
The rectangle's changed from 600–2000 to 2101–3501.
The native result shows a change to serialized child geometry and
ownership for this operation. It does not establish how all native
transforms handle arbitrary or nested groups.

The experimental
[cross-writing tool](../../tools/experimental/draw_cross_writing_trials.py)
also generated one replacement Text picture form in the existing
synthetic `ARC SAMPLE` document. It sets display column 3, constructs
both duplicated payload lengths and preserves the measured trailing
byte `0x19`. Text reopened and displayed the new green arc and striped
rectangle, saved the candidate and reopened the native output.
The native save changed four form-header bytes at file positions
53–56. The picture's 123-byte length, column, suffix, leaves and
surrounding text survived. This qualifies one existing-envelope
replacement. General Text insertion and Filer database allocation
and index writing remain outside the verified profile.

The grouping, Text and brush run ended at 182,942 emulated ms
and 11,346 frames. The exact sources, independent candidates and
native saves have separate entries in the fixture manifest.

## Palette and fixed-length outline labels

Changing palette index 10 in the D07C rectangle to stored RGB
`(192,64,192)` changed the native line pixels to `(194,64,194)`.
Draw Save As preserved all 143 candidate bytes. The writer changes
the existing entry's channels and retains its index and position.

In the native Dixon/Marin control the writer changed `DIXON 24`
to `DIXON 42` by permuting the existing printable ASCII bytes.
Native Draw displayed both the changed Dixon and untouched Marin
labels and then saved and reopened the result. The native save
rewrote bytes 32, 172 and 250, including the Dixon right edge
from 2780 to 2768 world units. The same glyph set can therefore
produce a different native width in a different order. The writer
changes only the label bytes and leaves stored geometry and
resource metadata available for the native application. Arbitrary
text changes and recalculation of native extents remain unqualified.
This trial ended at 60,368 emulated ms and 3,852 frames.
