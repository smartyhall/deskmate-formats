# Native Draw campaign report

The [review PR](https://github.com/smartyhall/deskmate-formats/pull/122)
includes the published [PR #121](https://github.com/smartyhall/deskmate-formats/pull/121)
design as a dependency. The independent baseline is the PR #120
merge at `5e1b24f8d8d262ac165b125474f7807163afbcc1`. This report
describes the verified campaign checkpoint.

## Frozen drawings and comparisons

Each original featured drawing was authored independently, opened
in original Draw, saved with native Save As and reopened. On the
stopped RSX clone, the direct FAT16 reader and 7-Zip agreed on
all four saved bytes and all 19 diagnostic sources.

| Case | Native DOS name | Exact FIG | Bytes |
| --- | --- | --- | ---: |
| Primitive and style chart | PSTYLE.FIG | [FIG](../../tests/fixtures/application-generated/draw/suite-v1-primitives-styles.fig) | 1,879 |
| Cedar Workshop | WSHOP.FIG | [FIG](../../tests/fixtures/application-generated/draw/suite-v1-technical-plan.fig) | 1,563 |
| Cedar Lake | LAKEVIEW.FIG | [FIG](../../tests/fixtures/application-generated/draw/suite-v1-compound-landscape.fig) | 1,055 |
| Graphical typography | LETTER.FIG | [FIG](../../tests/fixtures/application-generated/draw/suite-v1-typography.fig) | 967 |

The [frozen manifest](../../examples/draw-comparison/suite-v1.json)
binds the SHA-256 hashes, serialized attributes and child order.
The [offline gallery](../../examples/draw-comparison/compare.html)
provides synchronized side-by-side, overlay, A/B and difference
views. It contains four versioned milestones and 276 PNGs plus
92 SVGs. The three later stages use fresh native reopens verified
pixel-identical to the baseline. The latest stage reports 12
diagnostic controls with exact RGB foreground agreement. D23's
external-font glyphs remain omitted.

| Case | PR #120 foreground IoU | Quadratic SVG | First VGA raster | Axis-stroke raster |
| --- | ---: | ---: | ---: | ---: |
| Primitive chart | 51.1% | 51.3% | 92.8% | 95.8% |
| Cedar Workshop | 45.7% | 46.5% | 85.0% | 85.0% |
| Cedar Lake | 80.8% | 80.8% | 99.9% | 99.9% |
| Typography | 13.6% | 13.6% | 15.7% | 15.7% |

The [stroke milestone](../../examples/draw-comparison/v1/vga-strokes-02/README.md)
gives exact-color agreement and links to symmetric boundary distances.
The latter improve sharply for the chart and landscape. They increase
for the workshop and typography in the native raster comparison.
Font omissions and a difference in the antialiased reference
boundary contribute to those tradeoffs.

## Format, raster and historical results

- The RSX Normal and Two times views share a measured origin at
  framebuffer pixel `(0,62)`. The positive endpoint samples agree
  with `2/25` and `19/220` pixels per world unit at Normal zoom.
  Native clipping and integer-inclusive endpoints were measured on
  one-pixel controls. Fractional boundaries and scrolled viewports
  remain partly characterized. [Oracle report](draw-oracle-20261119.md)
- Three-point `UA` arcs are quadratic. The shared projection
  recovers asymmetric, reversed-endpoint and positively scaled
  arcs. Ten measured native traces were within 1.58 pixels of
  the projected curve. Reflection, polygon/ellipse stepping and
  exact brush width remain incomplete. [Arc and brush geometry](draw-geometry-20261119.md)
- The experimental raster matches all 32 native fill rectangles and
  all 64 axis stroke color masks. The measured VGA tiles remain
  locked to framebuffer phase at the tested positions and two zooms.
  The direct raster leaves diagonals, general stroke contours and
  text approximate or omitted. [Raster evidence](draw-geometry-20261119.md)
- The historical corpus remains 204 of 206 in strict mode and reads
  205 with explicit BRIDESHW-style recovery. The updated SVG draws
  8,704 leaves across the 205 and reports omissions in 122.
  [Inventory](draw-corpus-20261119.md)
- BRIDESHW's 23-word declaration survives native Save As, with a
  fixed 44-byte arc. The native original, corrected copy and native
  resave render identically in the measured viewport. PIPES
  retains the five invalid references. Its native resave matches
  its original pixels, and the proposed repair changes 108 pixels.
  The Ghidra accessor confirms word-offset arithmetic without
  resolving the native repaint path. [BRIDESHW](draw-brideshw-20261118.md) · [PIPES](draw-pipes-20261118.md)
- The expanded `Uf` inspector identifies the five seen reference
  families. FF1 directory inspection identifies Cobb, Dixon and
  Marin variants, 224 glyph extents each and nominal advances from
  user-supplied resources. The independent
  projections offer clearly labeled generic substitutions.
  Exact external glyph interpretation, rotation, advances and
  typography rendering remain the largest omission.
  [Font evidence](draw-fonts-20261119.md)

## Shared graphics and editing

The arc and rectangle transferred natively into a Text picture,
a Filer card and a Filer report. Their bytes after the coordinate
fields agree across the shared forms. The projections use the same
geometry, preserve the Text envelope and respect Filer's escaped
chunks. A tool-generated replacement picture opened and saved
natively in Text. Filer allocation and index mutation remain
unqualified. [Shared graphics](draw-shared-graphics-20261119.md)

The Python writer supports exact no-edit preservation, line
translation/recolor, rectangle resize, flat primitive additions
and deletion, ordering, one-flat-group creation and break,
palette changes and a limited same-glyph ASCII label edit. The
reports separate tool-generated bytes, native-open evidence,
native edits and native saves. Native horizontal reflect physically
changed child coordinates and flattened the measured group.
[Writing and native validation](draw-writing-20261119.md)

The single-file [browser Workbench](../../examples/draw-workbench/workbench.html)
opens local FIGs, inspects palettes/records/groups, pans and zooms,
exports SVG/PNG and downloads untouched originals. It supports the
three in-place edits with undo/redo. Actual Chromium downloads
opened in original Draw. A native keyboard edit and Save As
produced a FIG that Chromium reopened and downloaded unchanged.
The UI uses an independently designed period-style layout and
observed native workflows. Native menus, tool creation, full
keyboard workflows and the full Python editing surface are
continuation targets. [Native UI observations](draw-native-ui-20261119.md)

## Verification, publication and usage

The standalone and supervisor publication audits share the scoped
comparison validator. PNGs use a bounded RGB/RGBA structure, checked
CRC, bounded decompression and an allowlist of chunks. SVGs use the
independent geometry subset. The fixture and comparison manifests
bind all identities. Wheel and sdist omit the visual artifacts and
binary fixtures. The sdist retains provenance metadata. Commercial
resources, historical artworks, full VGA frames and private
experimental media remain in the laboratory.

| Held native session | Emulated ms | Frames |
| --- | ---: | ---: |
| Oracle and baseline | 329,485 | 20,417 |
| Historical failures | 139,830 | 8,697 |
| Arc and pattern controls | 117,473 | 7,355 |
| Arc/raster recapture and browser writer | 266,089 | 16,461 |
| Cross-application, strokes and fonts | 155,018 | 9,616 |
| Axis-stroke recapture and flat writer | 301,250 | 18,619 |
| Grouping, brush and Text writing | 182,942 | 11,346 |
| Palette and label writer | 60,368 | 3,852 |
| Total | 1,552,455 | 96,363 |

The [usage ledger](../evidence/codex-usage/README.md) includes
startup and checkpoint receipts with token totals, window durations,
and read-only account snapshots. The reserved reset stayed intact.
The review PR contains the hosted check outcomes.

## Continuation

The largest remaining visual omission is exact native text. Start with
the pinned Cobb, Dixon and Marin resources and the native outline
controls to correlate glyph contour encodings and native extent
recalculation with the verified directory. Next qualify oblique stroke widths, brush
footprints, axis reversal and scrolled viewports. Use the Ghidra
group accessor as a starting point for a measured PIPES repaint
trace. Keep arbitrary nested-group edits, Text insertion and Filer
allocation behind their respective native file acceptance trials.
