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

## Representative images in research pull requests

For Codex research PRs with meaningful visual output, include a **proportional,
representative selection of exemplar images** in the PR description or linked,
reviewable committed assets. Illustrate the most important researched
applications, controls, sequences, or comparisons; a large capture inventory
is not itself a reviewable selection. Provide a short factual caption for
each image (release/version, state or test, and what the image supports), and
retain traceable provenance and native/synthetic distinctions. Use contact
sheets where they help compare states, with access to individual native-size
images when visual detail is evidence.

The existing standing authorization covers eligible synthetic-content
DeskMate screenshots. Review actual pixels, attribution, metadata, and public
paths as for any reference image; do not assume raw private screenshots are
safe for GitHub PRs. An image included as PR evidence is **not automatically
approved for the public site**, which requires the image manifest and page
placement. For wholly nonvisual work, explain that no appropriate visual
exemplars exist rather than inventing imagery or staging additional emulator
activity without authorization.

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

## Reviewing actual pixels through a CI preview artifact

Confirmed by independent ChatGPT review of PR #187 on 2026-11-27.
The GitHub connector's ordinary file/URL fetch and blob fetch are text-only:
a PNG fetch failed with a UTF-8 decoding error. This is a transport
limitation, not a reason to infer pixels from alt text or accept an image
without inspecting it.

Use an exact-head Actions preview artifact as a binary transport:

1. Read the PR head SHA and find the completed successful **Reference site
   preview** workflow for that exact revision. Confirm the artifact name,
   numeric ID, expiration status, and originating run. Do not substitute
   an artifact from a different branch/revision.
2. In ChatGPT with the GitHub connector, use its workflow-run artifact
   listing and **download workflow artifact** actions (rather than its
   text fetch actions). The download produces a ZIP file reference; in
   the tested session it was also mounted under `/mnt/data/`. Inspect the
   actual tool-returned file path or materialize the returned file reference
   if necessary. Do not invent a sandbox filename or rely on a temporary
   signed download URL surviving another conversation. A local reviewer
   can equivalently use the authenticated GitHub Actions UI or
   `gh run download RUN_ID --name ARTIFACT_NAME --dir OWNED_REVIEW_DIR`
   and verify the same bytes.
3. Read the ZIP's member inventory without wholesale extraction. Select the
   exact expected relative path, reject duplicate matches, enforce a
   reasonable uncompressed size cap, and extract only the required public
   derivative to a scratch file. For the native-size PNG, calculate
   SHA-256 and Git blob SHA-1 (`sha1(b"blob " + str(len(data)).encode("ascii")
   + b"\\0" + data)`); compare against the exact-head repository tree
   and `website/reference-images.json`, along with dimensions and size.
   If a build transforms the image, identify that difference instead of
   claiming it is the same source blob.
4. Open the extracted PNG with an image-capable viewer and inspect the
   actual pixels at native size. Check visible private information,
   credentials, irrelevant host content, UI state, caption, alternative
   text, and attribution/rights. Record the exact head, run, artifact ID,
   member path, hashes, and disposition in the independent PR review.
   Do not publish the ZIP, temporary URLs, unrelated files, or raw private
   evidence. Expired/missing artifacts or mismatched bytes remain explicit
   review blockers unless an equivalent exact-byte route is available.

Worked example (not a promise that the artifact remains available):

- [PR #187](https://github.com/smartyhall/deskmate-formats/pull/187),
  head `0edd94c3662b15c39206ebb01c87a7ed1d2a00ad`,
  [preview run 45966788527](https://github.com/smartyhall/deskmate-formats/actions/runs/45966788527).
- Artifact `deskmate-reference-preview`, ID `15183960287`.
- Member `assets/reference/collection-01/ui.desktop.accessories-menu.png`
  corresponds to `website/src/assets/reference/collection-01/ui.desktop.accessories-menu.png`.
- 19,662 bytes, 640 × 480; Git blob
  `6ad8d0bdd130f765e37b7dfe2a28d8f21770cb19`;
  SHA-256 `2d0b16f4ebf7e819f7dedca67a0cef866306e4ca344d747ba44171c6a90db620`.
- [Independent review](https://github.com/smartyhall/deskmate-formats/pull/187#pullrequestreview-6085713486)
  inspected the image and found a caption/alt-text menu-name correction.
  It did not require another emulator session.

A preview artifact proves the checked-out derivative was present in the
build when its bytes match. It is not proof of original capture provenance,
historical software rights, successful live publication, or the correctness
of every image in the artifact. The ordinary publication checklist still applies.

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
