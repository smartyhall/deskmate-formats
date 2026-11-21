# Standing secondary workstream: visual evidence curation

Operator direction 2026-11-20. Complements the [preservation ecosystem
roadmap](preservation-roadmap.md) and [archival format coverage](archive-format-coverage.md).

## Scheduling and scope

Periodically, especially after screenshot-heavy campaigns and when primary
work is complete with authorized capacity remaining, inventory and curate
existing research captures. Select bounded, independently reviewable
increments; checkpoint and record usage under AGENTS.md. Do not require
fresh native sessions to inventory existing evidence. Do not launch an
emulator, access unrelated files, dispatch new turns or spend additional
quota solely under this workstream. Existing native-control rules apply.

The [future site visual-asset workflow](site/visual-assets.md) describes the
separate, review-gated transition from this private catalog to an eventual
public UI atlas and independently authored DeskMate design system.

## Private inventory

Locate available captures in project-controlled research output directories,
private evidence archives and experiment manifests. Inventory incrementally.
Preserve original bytes, paths or durable private locators, and SHA-256.
Deduplicate exact bytes without deleting source occurrences; use perceptual
similarity only to group candidate near-duplicates, preserving differences
in focus, cursor, selection, video mode and transient states. Treat missing
or inaccessible captures as gaps, not evidence of a screenshot's contents.
Use existing evidence and targeted visual inspection to classify images;
do not infer unobserved interactions from a still image.

Maintain a machine-readable private manifest or SQLite catalog with stable
capture and occurrence IDs, source hash, experiment/run, source locator,
capture method, observed dimensions and color representation, application
and version, runtime version, display mode, machine/emulator configuration,
screen or dialog, control and state tags, workflow step, related evidence
and document anchors. Record unknown fields explicitly; distinguish directly
observed, inherited from receipts, inferred and unverified labels. Record
timestamp and sequence only when supported. Preserve raw framebuffer and
host-composited screenshots as different evidence classes. Link resource
analysis, palettes and geometry observations where independently established.

## Classification and exemplars

Begin with desktop and launcher, menus, window chrome, dialogs, alerts,
keyboard and mouse focus, selected/disabled controls, buttons, scrollbars,
list and edit fields, file selectors, application workspaces, errors,
intermediate workflow states and video-mode differences. Extend taxonomy
for application-specific widgets and third-party products. Group sequences
using experiment receipts rather than inferred order. Keep a coverage
matrix by runtime/application/version, display mode and UI/workflow state;
distinguish observed, cataloged, exemplary, missing and not applicable.

For documentation, select legible, representative captures that substantiate
a specific claim, workflow or visual convention. Prefer native unmodified
frames with synthetic data and known provenance. Select comparisons or
sequences where a single still cannot demonstrate behavior. Record why an
exemplar was selected, its source ID/hash, exact anchor, caption, alt text,
observed state and any limitations. Use stable IDs instead of private paths
in public text. For future design-system work, record measured pixel geometry,
palette, typography and control-state observations separately from aesthetic
interpretation; do not present independent recreations as original captures.

Generate private contact sheets, thumbnail indexes or local galleries as
useful. Derivatives are separate from immutable originals: record cropping,
integer scaling, annotation or any redaction and preserve the transformation
recipe. Use nearest-neighbor scaling for native pixel-art evidence; label
crops and annotations. Do not retouch originals or synthesize missing evidence.

## Publication boundary

Raw framebuffer captures, private screenshots, private paths and unrelated
or personal information remain private under AGENTS.md. The request to
provide exemplars does not itself waive publication restrictions. Prepare
private exemplars and public-safe captions, evidence IDs, and proposed
documentation placements now. Publish actual images only where eligible
under an existing narrow grant (e.g. qualified Draw comparison imagery) or
a subsequent explicit authorization, after reviewing actual pixels,
provenance, third-party rights and applicable audit rules. Do not broaden
the binary audit or publish unreviewed historical assets. Independently
authored illustrations may be published under existing rules when clearly
labeled. Keep public catalog metadata sanitized; do not expose private
locators, sensitive contents or raw logs.

## Outputs and acceptance

Each pass should report counts of inventoried occurrences, exact identities,
reviewed and selected exemplars, coverage gaps and unresolved labels;
update private catalog and documentation linkage proposals; and preserve
a resumable checkpoint. Keep inventory tools reusable and read-only against
original evidence. Test with eligible synthetic images and manifests;
validate deduplication, stable IDs, metadata uncertainty, path containment,
derivative provenance and publication filters. Run relevant repository
checks for publishable changes and submit reviewable commits/PRs.
Prioritize existing screenshots; schedule targeted gap-filling only in
separately authorized future native campaigns.
