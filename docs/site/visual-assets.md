# Visual atlas and publication workflow

This document translates the private evidence inventory into reference-site
illustrations. The operator's 2026-11-21 standing approval permits **ordinary
documentary UI screenshots using synthetic or public sample content** and the
project's own illustrations to enter a reviewed site PR without separately
authorizing every image. This does not grant rights in software binaries or
third-party artwork. See [visual evidence curation](../visual-evidence-curation.md)
and the [first inventory report](../research/visual-evidence-first-pass-20261120.md).

## Inventory already established

The expanded private catalog's dated checkpoint records **2,348 image
occurrences, 1,525 exact SHA-256 identities, and 262 possible-similarity
groups** across ten collected roots, with zero reported observation gaps in
that pass. These are *capture identities*, not 1,525 usable screenshots or
1,525 distinct interface states. Revisit the live private catalog for current
counts; do not substitute this historical snapshot for a fresh inventory.

The public research report includes short opaque occurrence-ID prefixes for
reviewed examples of: Draw File and Zoom menus; Draw Save and font dialogs;
Calendar day navigation; Worksheet selected cells and disabled menus; and
Express Publisher's monochrome Save As view. These prefixes are not raw capture paths or vendor licenses. Keep full
occurrences and private locators in the private evidence collection; publish
only selected, inspected, well-captioned documentation images with the site
manifest. Contact sheets may be shared as review aids without automatically
becoming public website assets.

## Atlas coverage to measure

| Family | Representative states | Current public evidence | Gap or next qualification |
| --- | --- | --- | --- |
| Desktop/runtime | Desktop, launch, task switch, menu chrome | Partial native index captures | Runtime versions, alternate video modes, dismissal behavior |
| Common controls | Enabled/disabled, focus, selection, modal alert, list, edit, scroll, file picker | Menu and dialog exemplars in the first report | Keyboard traversal sequences and component measurements |
| Calendar / Address Book / Filer | Open, edit, save, add/delete, indexes, help | Calendar and Filer research captures | Field-level dialog sequences and Help navigation |
| Text / Draw / Worksheet | Editing, embedded graphics, fonts, print, page setup | Draw and Worksheet examples | Cross-application visual controls and native save confirmations |
| Music / Sound | Transport, instrument controls, editor, error states | Private native campaigns | Exact audio-device/version context and representative state sequences |
| Third-party / runtime extensions | Installer, launched workspace, file dialogs | Express Publisher example | Exact product/release attribution and UI variability |

Use explicit state labels: *observed*, *reviewed*, *selected candidate*,
*authorized for publication*, *published*, *missing*, *not applicable*.
A capture can be observed without being reviewed or legally publishable.
Do not treat one captured screen as proof of an entire workflow.

## Selection and future site asset contract

For a proposed exemplar, maintain a **private** record with the full
occurrence ID, exact source SHA-256, source locator, capture method,
application/runtime versions, guest/video mode, experiment and observed
state. Track the differences between raw guest framebuffer, host screenshot
and synthetic reconstruction.

The **public** record, once cleared, should contain:

- Stable descriptive asset ID (for example, `ui.draw.save-dialog.focus`).
- Target reference-page ID from [page-map.json](page-map.json) and exact
  section anchor where the image substantiates a claim.
- Reviewed caption, alt text, intrinsic dimensions and content warning when
  necessary, with a factual observation separated from interpretation.
- Public derivative filename and SHA-256, transformation recipe
  (crop, nearest-neighbor scale, annotation), and attribution/rights basis.
- Reviewed origin class: original application capture, eligible synthetic
  native comparison, or independently drawn illustration.
- Immutable evidence reference and review decision, **without private paths,
  credentials, personal data or full raw captures**.

Routine synthetic-content interface captures and independently authored
illustrations may be included directly in an image PR under the standing
operator authorization, after inspecting pixels and checking provenance.
Do not require another ad hoc operator permission for each normal screenshot.
Use `website/reference-images.json` and put final PNG derivatives under
`website/src/assets/reference/`; the repository audit checks the declared
hash, size, dimensions, metadata-free PNG structure and sidecar.
Redactions or annotations create a derivative and must not replace
the private original. A near-duplicate hash is only a triage lead.

## A useful DeskMate-derived design system

Build a measured *design evidence* table separately from the gallery:
application/runtime/version, frame dimensions, palette and device mode,
window borders and shadows, menu geometry, focus decorations, button states,
typeface/resource dependencies, cursor shapes and keyboard labels. The first
catalog reports four recurring measured RGB values in some RSX frames;
those values are observations, not a universal DeskMate palette.

Use those measurements later to make an independently authored theme.
Until then, BOOTSTRA.386 is the planned initial presentation layer; do not
confuse its DOS look with authentic DeskMate GUI behavior.

## Ready-for-publication checklist

1. Original capture identified, byte-preserved and independently inspected.
2. Provenance and native/synthetic status established; no inferred UI states.
3. Standing documentary-image authorization or a more specific third-party
   permission/rationale recorded; distinguish project rights from vendor art.
4. Private paths, names, incidental sensitive content and third-party
   restrictions reviewed.
5. Derivative generated reproducibly, linked to original and hashed.
6. Caption, alt text, viewport scaling and contextual claim reviewed.
7. Include the actual suitable PNG and correct manifest/sidecar in a reviewable
   PR; normal synthetic-content UI screenshots need no additional per-file
   approval outside the established independent PR review.
8. Avoid a full manual scan, redistributable software/media archive, unrelated
   copyrighted art or any personal/credential-bearing screen content.

The inventory and the publication collection are intentionally separate.
