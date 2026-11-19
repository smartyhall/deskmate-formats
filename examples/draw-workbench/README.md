# DeskMate Draw Workbench — Classic interface

Open [workbench.html](workbench.html) directly from a local checkout.
It is a single offline HTML file with the four frozen Draw examples.
Rebuild it with `python tools/experimental/build_draw_workbench.py`.

The first implementation uses an independently designed period-style
interface. It follows the observed open, select, zoom, edit and Save As
workflow. The native title/menu organization, tool interactions and
dialogs remain documented research references for further work.
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
- Select an object in the canvas or its display-list row. Inspect native
  coordinate words, resolved bounds, raw attributes, group children,
  palette indices and external-font metadata.
- Edit a top-level line's position or palette index, or resize an ordered
  top-level rectangle. The editor preserves all enclosing bytes and
  unrelated records. Undo and redo keep up to 32 prior models.
- Download the original FIG byte for byte or save the edited copy as a
  new FIG. SVG and PNG export the current scalable viewport. The optional
  generic text mode is explicitly marked as a substitution in the view
  and exported SVG.
- Open **Preview limits** and select **Load local FF1 fonts** to render
  supported external base-face labels. Files stay in the current browser
  session. The Workbench resolves the internal family name, reports
  missing faces or unsupported styles, and includes the projected curves
  in scalable exports. Use **Clear fonts** to release the session copies.
  The renderer uses nominal advances and unhinted outlines. See the
  [FF1 measurements](../../docs/research/draw-ii-20261119.md).

The browser uses `O` or the Open FIG button in place of application-level
function keys. In the native program F2 opens File, F3 Edit, F4 Actions,
F5 Zoom, F6 Options and F7 Tools. Browser Find and Reload often reserve
F3 and F5, respectively. Native menu placement and behavior were
observed over the RSX socket. The browser does not claim the complete
native menu set or keyboard-mode drawing.

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
