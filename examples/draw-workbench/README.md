# DeskMate Draw Workbench — Classic interface

Open [workbench.html](workbench.html) directly from a local checkout.
It is a single offline HTML file with the four frozen Draw examples.
Rebuild it with `python tools/experimental/build_draw_workbench.py`.

The independently styled interface follows the native function-key menu
organization and uses the observed open, select, zoom, draw and Save As
workflows. More detailed native dialogs remain research references.
See the [native interface observations](../../docs/research/draw-native-ui-20261119.md).

The operator requests a faithful reconstruction of original DeskMate Draw
rather than a contemporary editor with decorative retro styling. The
authoritative reference is the running DeskMate 03.05.00 Draw application
in the established RSX laboratory. Use private native captures and actual
interaction receipts for interface details, not an imagined mockup.
A concept illustration in a simulated AROS browser is aesthetic direction
only; it is not evidence of actual AROS compatibility or native UI details.

## Implemented interface

- Open or drop a local FIG. Pan by dragging or with the arrow keys after
  focusing the canvas. Use Normal, Fit drawing or the zoom buttons. The
  mouse wheel zooms at the pointer.
- Choose **File → New** to start an unsaved canvas. Draw lines, rectangles,
  ellipses, polylines or polygons on a qualified flat list. Click twice or
  drag for a two-point tool. For paths, click each point and press Enter
  to finish. Escape cancels the draft. Arrow keys move the drawing cursor
  and Space places a point.
- Select an object or group in the canvas. Use **Options → Toggle
  inspector** to access the display list and select a record there. Inspect native
  coordinate words, resolved bounds, raw attributes, group children,
  palette indices and external-font metadata.
- Edit a top-level line's position or palette index, or resize an ordered
  top-level rectangle. Reorder existing roots and change the palette.
  In the packed flat profile, delete a top-level element or group the
  whole drawing. Break a supported single group. The label editor accepts
  a permutation of the existing ASCII label for the qualified outline
  profile. Undo and redo keep up to 32 prior document models.
- Download the original FIG byte for byte or save the edited copy as a
  new FIG. SVG and PNG export the current scalable viewport. The optional
  generic text mode is explicitly marked as a substitution in the view
  and exported SVG.
- Use **Options → Load local FF1 fonts** to render
  supported external base-face labels. Files stay in the current browser
  session. The Workbench resolves the internal family name, reports
  missing faces or unsupported styles, and includes the projected curves
  in scalable exports. Use **Clear fonts** to release the session copies.
  The renderer uses nominal advances and unhinted outlines. See the
  [FF1 measurements](../../docs/research/draw-ii-20261119.md).
- With a local FF1 loaded, choose **Tools → Text**. Click or press Space
  at the desired left baseline. Choose a family, type a printable ASCII
  label, and enter its point size and width percentage. Save the FIG and
  install the matching FF1 on the native machine to reopen the drawing
  in DeskMate. The verified profile uses filled, left-justified outline text.

The visible menu strip follows Help F1, File F2, Edit F3, Actions F4,
Zoom F5, Options F6 and Tools F7. Use Shift+1 through Shift+7 if your
browser reserves a function key. Press `O` to open a FIG directly.
Use Up/Down to navigate an open menu. The viewport displays a scalable
projection. The separate comparison gallery shows measured RSX rasters.

## Native validation

Chromium opened and edited D01 and D04 from a file URL, downloaded both
FIGs, and exercised selection, undo/redo, exact original download and
SVG/PNG export. The two emitted FIGs matched the Python writer byte for
byte. Original Draw opened them on the RSX. The moved green line was
then moved again in the native keyboard workflow and saved as a new FIG.
The resized rectangle was saved directly. Both native saves reopened
in original Draw and in Chromium. Both were independently extracted
from the stopped FAT16 image. See the
[round-trip evidence](../../docs/research/draw-writing-20261119.md).

Draw II also created new line, rectangle and grouped drawings entirely
in Chromium. Native Draw reopened all three. The group was selected,
moved using the native keyboard workflow and saved. Its four leaves
retained their styles, order and palette, with the native save flattening
the group. Chromium reopened and downloaded all three extracted native
saves byte for byte. [Draw II round trip](../../docs/research/draw-ii-20261119.md).

## Classic interface research

Reproduce the native layout, title and menu strips, menu labels and order,
function-key assignments, dialogs, tool symbols, palette, borders, pointer,
selection handles, status messages, keyboard-only operation, and drawing
and object workflows. Measure these through the native socket. Derive a
documented visual/interaction reference table. Independently author the
HTML/CSS/JavaScript and icons, and use eligible fonts or independent
pixel-font approximations; original executables, proprietary font files,
icons and original full screenshots remain private. Do not invent labels
or shortcuts based on the mockup when native behavior is known.

The default Classic interface should resemble original Draw as closely as
practical. Add modern QoL in the same visual language, as though Tandy
had extended Draw in a subsequent release: undo/redo, numerical position
and size dialogs, optional object tree and raw-record inspector, mouse-wheel
zoom, drag-and-drop open, downloadable Save As, SVG/PNG export and truthful
compatibility diagnostics. Offer an Original Interface option to hide
extensions if practical. Browser-reserved keys require a documented
alternative. No fake fidelity percentages, hardware memory counters or
unsupported commands presented as functional.

## Implementation and conformance

Prefer an offline single-file HTML deliverable with reproducible build
from source, no CDN, backend, accounts or document uploads. Use plain
browser capabilities where feasible; no promise of compatibility with an
actual AROS browser until tested. Keep application code under this tree
(or a documented equivalent) and the gallery under `../draw-comparison/`.

Native graphics forms are the authoritative model, not SVG. Preserve
exact coordinate fields, object identity/order, attributes, palette,
group references, raw unknown records and outer-container metadata.
Use the Python codec or a conformance-tested browser implementation;
avoid two incompatible undocumented formats. Offer local FIG viewing,
zoom/pan, selection and inspection, original-byte download and export
before enabling editing. Then enable only native-validated operations:
move/resize/recolor, supported primitives, ordering/grouping, palette
and text where qualified. No-edit round trips must preserve exact bytes.
Unsupported records must survive, or dependent edits must be refused with
specific reasons; keep user originals untouched. Undo/redo restores the
native document model. Test browser-generated FIG through original Draw
open/edit/save/reopen and browser reopen. Use published native synthetic
fixtures and automate Python/browser semantic and byte conformance.
Publish a working viewer early, and prioritize native research over
unqualified editor feature polish.

The comparison gallery's four featured drawings should be useful
built-in examples when available. See [comparison plan](../draw-comparison/README.md).
