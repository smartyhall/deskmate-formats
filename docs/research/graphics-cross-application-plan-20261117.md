# Proposed campaign: DeskMate Draw, Filer graphics and Text picture embedding

**Planning checkpoint: 2026-11-17. This is not a completed native experiment.**
The immediately preceding Filer/Text campaign is [PR #110](https://github.com/smartyhall/deskmate-formats/pull/110); at the time of this plan it was under review and not integrated into `main`. Recheck the repository/PR state when starting. Do not describe PR-only observations as merged results.

## Research questions

1. Does Draw store the same graphics-form primitives, element payloads or geometry conventions used by Form Setup/Filer?
2. What transformation, if any, maps an independent Draw picture into a Text document's embedded-picture payload?
3. How does Form Setup serialize graphical data into the ASCII-constrained Filer GRAPHICS table? Can its decoded contents be compared to Draw's graphics form or to a picture pasted into Text?
4. Which similarities reflect a common on-disk serialization versus only common runtime drawing APIs?
5. Can independent readers safely identify and preserve an embedded Text picture without misinterpreting its internal bytes as Text control codes?

The key principle is to compare **three representations of a controlled graphic**: a native Draw file, its Text clipboard-pasted representation, and a comparable Form Setup/Filer graphic. Raw whole-file equality is neither expected nor required.

## Primary documentation already available to the operator

The operator-provided *DeskMate Development System 03.05.00 Development Guide*, Appendix A, **DeskMate 3 File Formats**, contains relevant sections on **Draw**, **Filer/Form Setup**, and **Text** (in the operator's 493-page PDF, approximately PDF pages 482–491). This document is not committed to the repository and must not be assumed present in the Windows lab. These are **historical documentation claims**, not yet native evidence from this campaign:

- **Draw:** Its file consists of a 22-byte Page Setup header (offsets 0–21), FORM HEADER (22–39), FORM-SIZE-BUF (40–43), a graphics form beginning at offset 44, and 64 bytes of palette information. The guide describes the form end in terms of the list and strokes sizes. The palette has sixteen four-byte entries (palette index plus red, green and blue). Validate actual native outputs independently; do not assume every feature or variant follows one profile.
- **Filer/Form Setup:** The guide says GRAPHICS stores binary graphic data in an "encrypted" representation because the database accepts only ASCII data. Treat the word "encrypted" as the manual's terminology; **do not assume modern cryptography or a particular escaping/encoding algorithm**. Its LAYOUTS and GRAPHICS definitions are described as static, DATA as user-defined. Prior native QRECORD evidence shows a minimal file may have no GRAPHICS table.
- **Text:** Pasting a Draw picture converts an ASCII document to non-ASCII Text format. Embedded picture paragraphs begin with **0x01**, end with **0x02**, and must follow a CRLF or another picture. Immediately after the 0x01 are a two-byte clipboard picture length and a two-byte display-column value; the Draw picture payload follows, then a repeated two-byte length and the 0x02 terminator. The guide gives the display path through `vid-draw-form`. **Embedded payload bytes may themselves look like 0x1A or other control codes; readers must traverse by the recorded length, not scan blindly for delimiters or EOF.**
- **Text, broader roadmap:** The guide also documents bold/underline controls, paragraph margins, fields, and optional headers/footers. These are useful next targets for the Text reader but must not be conflated with observed support in [PR #110](https://github.com/smartyhall/deskmate-formats/pull/110), which covers only measured plain and default-header formatted streams.

Source labels and field layouts above are condensed research notes, not a reproduction of the manual. The source should be checked directly if the operator makes it available in the experiment environment. The documented layouts are strong leads, **not** substitute hashes, actual application writes, or a decoded Filer graphic.

## Phase A — native Draw baseline

Use the established 86Box native socket and disposable cloned installations. Identify the observed Draw entry point, supported drawing/editing commands, native extension, and export/copy behavior. Capture the precise source application version and installed-file provenance.

Build a comparative native corpus, adapting to the UI actually supported:

| Trial | Minimal source operation | Variable isolated |
| --- | --- | --- |
| D00 | Save empty drawing | Header and empty form |
| D01 | Add one horizontal line | Primitive framing |
| D02 | Extend the same line | Endpoint/dimension |
| D03 | Move line | Coordinates |
| D04 | Add one rectangle | Primitive type |
| D05 | Resize and separately move rectangle | Geometry |
| D06 | Alter one color/line/pattern attribute | Styling/palette |
| D07 | Add ellipse/circle, if supported | Different primitive |
| D08 | Two shapes with known drawing order | Multiple elements/order |
| D09 | Text object, if supported | Text primitive |
| D10 | Remove one shape | Deletion/rewriting |

Prefer one-variable mutations from an exact known parent. Independently repeat a save without semantic edits and compare bytes/mtime. Analyze known offsets from the guide but validate where a graphics form and palette actually start/end, numeric endianness, repeated structures and position/attribute fields. A minimal bounded read-only Draw structural dumper is welcome if grounded; a general renderer is optional.

## Phase B — Form Setup/Filer graphics

Start from a new clean Form Setup-generated database **with no graphics**, and separately retain unmodified shipped CARMAINT/INVNTORY as private comparators. The operator has **no preserved manually modified Filer files**; do not hunt for them or misattribute generated artifacts.

Create one graphical form element at a time, if native Form Setup supports it: simple line, rectangle, translated/resized variant, style change, two elements, and a removal. Also test graphic plus data field, where meaningful. Capture which of GRAPHICS, LAYOUTS, metadata and auxiliary files change, and whether adding the first object creates the GRAPHICS table.

Compare corresponding Draw and Form Setup objects first at the logical/structural level. Because the Filer GRAPHICS representation is described as ASCII-compatible "encrypted" binary graphics, **lack of raw-byte matches is not a negative result**. Look for encoded lengths, high-level record boundaries, recurring alphabets, and measured mutation relationships before attempting any reversible decoding hypothesis.

On disposable CARMAINT/INVNTORY copies, modify a single visible graphical element, if the UI permits, to link a specific picture to stored records. Preserve all original shipped material privately. Do not assume the number of GRAPHICS rows equals the number of visible drawing primitives.

## Phase C — Draw picture embedded in Text (high-priority bridge)

Once D01 and a second distinguishable Draw specimen are preserved, test **actual native copy/paste from Draw into Text**. The Development Guide explicitly supports this in principle, so try this early rather than leaving it as a distant optional exercise. Discover the real UI commands; don't invent menu keys. If cross-application clipboard control proves problematic, document the blockage and continue A/B.

Suggested descendants:

1. TP00 — simple unformatted Text paragraph and save; no picture.
2. TP01 — same text plus one pasted D01 graphic; native save/reopen and visual confirmation.
3. TP02 — same source picture at a changed placement column, if supported.
4. TP03 — a different Draw picture embedded, using the same Text surroundings.
5. TP04 — two pictures separated by text or by another picture, if the UI supports it.
6. TP05 — remove the picture or invoke To ASCII on a clone; examine actual behavior, preserving source.
7. TP06 — optional long/complex picture to test length/count/embedded control-byte handling.

For each, preserve the independent Draw source, Text source/parent, clipboard interaction trace, stopped-disk Text bytes, screenshots/visible result, file size/hash and semantic/byte difference. Isolate the **picture span** using the documented 0x01/0x02 framing and leading/trailing length checks. Compare the embedded drawing payload to the relevant portion of the Draw file; note clipboard translation, palette treatment and placement metadata. Distinguish visual equivalence from exact payload identity.

**Reader safety:** `src/deskmate_formats/text.py` in PR #110 deliberately fails closed on unsupported controls. Do not silently strip embedded pictures or treat an internal `0x1A` as EOF. First implement an optional bounded structural *inspector* that validates recorded lengths and identifies picture spans without decoding them. Only extend extraction once native cases establish how to handle omitted/placeholder picture content. Add adversarial tests for truncated lengths, mismatched trailing length, internal `0x02`/`0x1A`, and malformed picture-paragraph placement.

## Phase D — cross-application analysis and outputs

Evaluate these possibilities independently:

- Same serialized graphics-form payload inside different outer wrappers;
- Common primitives with differing serialization or ASCII-safe transformation;
- Shared video/form-manager runtime services but distinct file formats;
- No demonstrated relation.

Revisit static program/resource analysis only for concrete remaining ambiguities (e.g., `FORM HEADER`, `FORM-SIZE-BUF`, `vid-draw-form`, encoding path), preserving source identity and avoiding broad speculative disassembly.

Deliver a documented Draw corpus, controlled Form Setup graphics specimens, at least one attempted Draw→Text embedding experiment, a three-way comparison, and byte-level receipts. Publish eligible original **application-generated synthetic** fixtures with hashes, license sidecars and checks, but never shipped software, untouched commercial files, private raw guest images or user data. Native actions and findings must be attributed separately from guide-derived expectations and synthetic tests. Use a dedicated branch and review PR; do not self-merge.

## Working priority order

1. Recheck/complete the PR #110 baseline review and avoid conflicting unfinished work.
2. Generate D00–D05 and locate Draw's form/palette structure.
3. Attempt native D01→Text paste immediately; identify/validate the embedded-picture envelope.
4. Generate minimal Form Setup graphics and compare all three representations.
5. Investigate additional attributes, encoded Filer graphics and CARMAINT artwork.
6. Extend bounded inspectors/tests; document the shortest next discriminating experiment.

Success is an evidenced answer about the relationship, **not** necessarily complete support for all Draw/Filer/Text graphics in one campaign.
