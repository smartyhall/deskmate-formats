# First private visual evidence inventory

The first pass inventoried 1,895 image occurrences and 1,175 distinct
SHA-256 identities across five available roots. It found 720 repeated
occurrences and 218 candidate similarity groups. The latter share
dimensions and a first-frame luminance difference hash. An exact
SHA-256 match is evidence of identical bytes. A similarity match can
group visually distinct focus, cursor, color or selection states.

| Collection | Occurrences |
| --- | ---: |
| Draw native campaign | 549 |
| Draw II | 583 |
| Filer and Text | 209 |
| Sampled Music | 546 |
| Windows 98 sealed baseline | 8 |

One named shared-graphics root was unavailable at the submitted locator.
It remains a coverage gap. The inventory measured file format, pixel
dimensions, Pillow pixel mode and frame count. Unknown state and runtime
labels remain null. The catalogs retain every occurrence path privately,
including dissimilar screenshots of the same workflow and exact duplicates.
The catalog does not assign native capture provenance from a filename.

## Visually reviewed exemplars

The native Draw exemplars show 640×480 frames from the RSX Draw campaign.
The IDs below are prefixes of the private catalog's occurrence IDs.

| ID | Observed state | Proposed anchor |
| --- | --- | --- |
| `54f5dee981ecd695` | File menu open. Its title shows F2 and the About item has a separator. The pointer rests over Edit. | Draw menu hierarchy and keyboard shortcuts |
| `1270753db578d17b` | Zoom menu open, with Normal checked. Two times, four times, half and quarter are visible. | Choice menus and selection marks |
| `012393daf91f7ad5` | Save File dialog over the primitive/style drawing. Filename text is selected and the Save button has a dotted outline. | Modal layout and focus treatment |
| `fb5f2c49100704c8` | Text dialog with outline mode, Dixon selected, 24 point size, 100% width, left justification and outlined OK button. | Draw typography controls |
| `bd9f266c6cb5e92d` | 1440×1654 host-browser composite showing the comparison gallery. | Independent gallery documentation |

Screenshots labeled as Open Dialog in the source directory included a
frame visually identical to the File menu and a frame showing the
workspace. This limits filename-based classification. Disabled controls,
original file selector state, keyboard traversal, and alternate display
modes remain gaps in the reviewed exemplar set. The interface reference
should distinguish the graphical palette, focus marks and spacing
observed in the guest from separately authored implementation assets.

## Repeat the inventory

Use Python with Pillow installed. Pass each existing private evidence
root and its stable label separately to
`python tools/visual_evidence.py PRIVATE.json --root LABEL DIRECTORY`.
Use the same output and labels for subsequent runs. Unchanged entries
reuse observations based on locator, size and file times. The optional
`--labels` JSON supplies reviewed root-level provenance. Keep outcome
labels based on visual inspection in a separate private exemplar manifest.

## Expanded pass

The next pass located the shared graphics captures at the November 17
root and added Calendar, Worksheet, Express Publisher and the native
application index. There are now 2,348 occurrences, 1,525 SHA-256
identities and 262 similarity groups. The original five roots reused
unchanged observations. The ten supplied roots had zero observation
gaps. Twelve native-index bitmaps were included in addition to its PNG
captures. The measured bitmap reader treats still formats without an
explicit frame count as one frame.

| Additional collection | Occurrences |
| --- | ---: |
| Shared graphics | 183 |
| Calendar | 113 |
| Worksheet | 82 |
| Express Publisher | 41 |
| Native application index | 34 |

Three additional 640×480 exemplars expand the interface anchors.

| ID | Observed state | Proposed anchor |
| --- | --- | --- |
| `1d22f4bb829552c6` | Calendar day view, with a highlighted appointment time range and Previous and Next navigation flanking the date. | Schedule navigation and selected rows |
| `b17d38e0b3ef1acf` | Worksheet Edit menu with dithered Paste and a yellow selected cell visible behind it. | Disabled controls and document selection |
| `128875a5bc6ffb4e` | Express Publisher monochrome Save As dialog with a drive list, document and template selectors, and the underlying page ruler. | Third-party file dialogs and monochrome controls |

The native File menu, Zoom menu, font chooser, Calendar day view and
Worksheet menu each used four decoded RGB colors. The shared measured
values are RGB 0/0/129, 194/194/194, 129/0/0 and 194/194/0. The Save
File exemplar has 15 RGB values because its underlying synthetic
drawing uses additional colors. The Express Publisher Save As frame
has only white and black. These values describe the captured frames
and the measured rendering path. The private exemplar manifest keeps
the pixel counts and capture provenance.
