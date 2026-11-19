# DeskMate Draw Workbench — Classic interface

**Status:** design specification; no web application is implemented here.

The operator requests a faithful reconstruction of original DeskMate Draw
rather than a contemporary editor with decorative retro styling. The
authoritative reference is the running DeskMate 03.05.00 Draw application
in the established RSX laboratory. Use private native captures and actual
interaction receipts for interface details, not an imagined mockup.
A concept illustration in a simulated AROS browser is aesthetic direction
only; it is not evidence of actual AROS compatibility or native UI details.

## Classic UI

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
