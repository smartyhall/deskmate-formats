# Draw visual comparison library

The [frozen suite](suite-v1.json) contains four original Draw documents
and 19 native FIG diagnostic controls. The
[PR #120 baseline](v1/baseline-pr120/README.md) compares every drawing
with the corresponding independent projection. The
[planning manifest](suite-plan-v1.json) records the original test design
and pins the related Text and Filer controls.

The [quadratic SVG milestone](v1/arc-vector-01/README.md),
[experimental RSX raster](v1/vga-raster-01/README.md) and
[axis-stroke raster](v1/vga-strokes-02/README.md) preserve the
same native inputs and viewport with separately measured output modes.

Open [compare.html](compare.html) from a local checkout. Use the featured
cards or diagnostic selector, then switch between side-by-side, overlay,
A/B and difference views. Zoom and pan stay linked. The 1:1 control shows
one image pixel per CSS pixel, and larger scales use nearest-neighbor
enlargement. Open the separate SVG link for scalable geometry. The gallery
loads its local catalog and artifacts directly from disk. After publishing a
milestone, regenerate `catalog.js` with
`python tools/experimental/build_draw_gallery.py` in an environment with
the project package importable.

## Purpose and featured specimens

Maintain a permanent, public, longitudinal visual comparison gallery
analogous to the Music listening library. The featured gallery is four
new original drawings, designed to be recognizable and useful beyond
isolated primitive tests:

| Case ID | Drawing | Coverage |
| --- | --- | --- |
| primitives-styles | Primitive and style chart | Geometry, line weights, dashes, fills, palette, brush and clipping |
| technical-plan | Architectural / technical floor plan | Dimensions, fine lines, door arcs, labels, coordinate precision |
| compound-landscape | Original house/landscape illustration | Layering, nested groups, transforms, repeated objects, patterned fills |
| typography | Graphical typography specimen | Embedded strokes, external fonts, size, spacing, rotation |

The plan manifest defines the intended features, not a claim that
every feature works in native Draw. Create the actual specimens in
native Draw where feasible, using the existing serial-mouse/keyboard
automation. Exact native saves with independent stopped-disk extraction
are preferred. If tool-assisted creation is needed, distinguish
tool-generated, native-open-accepted and native-resaved bytes. Do not
fabricate native acceptance. Use independently authored graphics and
labels, not reproductions of historical artwork. Freeze the real FIG
bytes, exact object attributes and capture settings before changing
the renderer. Include eligible native source files in the existing
`tests/fixtures/application-generated/draw/` manifest, rather than
duplicating them in the gallery. The four featured drawings should
appear prominently in the comparison page, with the earlier 19
diagnostic files available in a secondary view. The related Text
picture and Filer card/report controls are additional shared-engine
regressions, not substitutes for the featured drawings.

## Layout and immutable baselines

The repository provides the following structure:

- `suite-plan-v1.json`: planned case IDs, requirements and pinned
  existing diagnostic/cross-application inputs.
- `suite-v1.json`: frozen actual featured FIG paths,
  hashes, object/feature coverage, capture profile, metric versions.
- `v1/baseline-pr120/`: first genuine matched native/independent
  comparisons using the pinned renderer, before any fidelity changes.
- `v1/<milestone-id>/`: immutable later comparisons with manifests.
- `compare.html`: offline comparison gallery.
- [Draw Workbench](../draw-workbench/README.md): separate application
  source and interface design, not a substitute for the gallery.

For each case and milestone publish eligible `<case>-native.png`,
`<case>-renderer.png`, `<case>-diff.png`, and where useful
`<case>-renderer.svg`. Each milestone manifest binds case/source
hash, renderer revision and mode, native machine/viewport identity,
capture and extraction recipe, output paths/hashes/dimensions, mapping
parameters, metrics, font-resource identities when used, omissions and
limitations. Keep the full framebuffer original privately; crop only
the drawing area with recorded integer boundaries. Use matched dimensions
and an explicit common world-to-pixel mapping. Preserve the original
renderer SVG, and rasterize it reproducibly rather than silently changing
its geometry to improve the baseline. Record any alignment and rasterizer
configuration. Do not label a renderer approximation as native output.
Retain earlier results; a changed fixture, mapping or metric is a newly
versioned comparison or clearly labeled additional mode.

Re-capture the fixed drawings natively and regenerate the independent
outputs at major rendering/interpreter milestones. Canonical reference
reuse is allowed only when a fresh capture has the same verified bytes
(or if unavailable, explicitly label the prior reference and blocker).
Include actual downloadable comparison images, not just hashes. Gallery
controls: side-by-side, linked pan/zoom, slider overlay, A/B switch,
pixel diff, details/metrics, version and case selector. Prefer an
offline gallery with no external services; direct static links must work.
Do not require the editor to view comparison artifacts.

## Measurements and provenance

Pin the original native VGA framebuffer/crop, palette, viewport origin,
zoom, background, display mode, and cursor/selection-free repaint state.
Record emulator build and guest/application identities. Use the existing
86Box native socket; no host screenshot or RDP input substitution.
Measure foreground masks, per-color agreement, pixel equality on relevant
regions, intersection-over-union, boundary distances, stroke widths,
pattern correspondence, and omitted records. Report exact-pixel and
vector-projection results separately. A large blank background must not
dominate the fidelity score. Where no comparable reference exists, state
that limitation. Keep original assets, native screenshots and detailed
traces in the private laboratory.

## Publication and test contract

The repository audit permits manifest-listed comparison PNGs and safe
renderer SVGs in the versioned library. Validation covers canonical paths,
exact source linkage, unique entries, hashes,
dimensions, bounded decoded pixel counts and file/aggregate sizes,
PNG signature and chunk integrity, allowed pixel encodings, decompression
bounds, absence of unexpected payloads/metadata, licensing and symlinks.
The standalone and supervisor audits share the validator. Wheels and
source distributions exclude the comparison images and vectors. The
source distribution retains provenance metadata and REUSE notices.

Publish drawing-only crops of original synthetic documents where rights
permit; do not include proprietary application UI chrome, raw font
assets, historical artwork or logos in the public comparison corpus.
A drawing with original external-font text can be a private diagnostic
if its public raster output has an unresolved rights issue; document the
reason and use a cleared equivalent for the public typography case.
The operator's goal is actual accessible comparisons, not a blanket
ban on original work produced by Draw. Document any real contrary terms
and seek review; never assert rights the project does not hold.

The [native oracle report](../../docs/research/draw-oracle-20261119.md) records
the capture procedure and coordinate observations. See also the
[prior native graphics report](../../docs/research/graphics-native-20261117.md)
and [standing policy](../../AGENTS.md).
