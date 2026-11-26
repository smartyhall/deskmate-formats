# Reference authoring and migration conventions

The reference site will distinguish current technical guidance from evidence
about how that guidance was obtained. Keep it generator-independent.

## Source roles and page identifiers

The [page map](page-map.json) assigns durable logical IDs and candidate routes
to existing public Markdown documents. A `dated-research` page is a preserved
experiment; it is not made current merely by appearing in navigation.
A `manufacturer-reference` page faithfully paraphrases the particular
edition cited and distinguishes documented features from native tests.
A `dated-snapshot` preserves a laboratory specification as of its stated
checkpoint. A `current-guide` can summarize what is presently supported,
but must explicitly cite capabilities, versions and unresolved boundaries.
A `site-plan` page records an editorial or architectural decision.

Future synthesized native-format specifications should be new maintained
documents where needed, not edits that erase dated experiments. Retarget
the logical page ID to the reviewed new source, then retain deep links and
relevant original section anchors; document any redirects at migration time.
The page map is a staging list, not a URL redirect engine.

## Evidence and references

A substantive field description should state:
- Application, runtime and source release/version.
- Field offsets, byte order, encoding and the exact supported profile.
- Confirmation level: **documented**, **native-confirmed**, **inferred**,
  **contradicted** or **unresolved**, with the basis for each.
- Verifiable synthetic test case(s), file identity and limitations.
- Source report and evidence identifiers, with private originals outside Git.
- Implementation capability (read, write, preview, export, unsupported)
  independently of format knowledge.

Use original manufacturer references as attribution to a *particular edition*,
not universal compatibility claims. Keep site language clear when a candidate
decoder uses interpretation rather than proven semantics. Link to source
documentation rather than duplicating pages in the site scaffold.

## Portable text and URLs

Use repository-relative Markdown links in source material. Keep internal page
IDs stable when filenames move. A future renderer must resolve those links
against the source map, preserve anchors, and generate redirects for changed
routes. Avoid hardcoded absolute deployment URLs and theme-specific tags in
the canonical source. No generator-specific front matter is required now.
Use machine-readable metadata for section order and page role.

## Interface and media

Choose the generator only after comparing accessible navigation and search,
deep-link compatibility, Markdown extensions, catalog rendering, safe asset
handling, incremental builds and the BOOTSTRA.386 adapter. Prioritize content
and data independence from CSS, templates and runtime JavaScript.

Screenshots require separate explicit clearance under
[visual asset workflow](visual-assets.md). Reproductions and historical
captures must be labeled as such. Prefer native resolution, descriptive
text alternatives, keyboard navigation, no-JavaScript fallbacks and
reduced-motion controls. Don't introduce a JavaScript-dependent boot
animation that makes content unavailable.

## Before a repository split

Inventory canonical source ownership, cross-repo links, downstream packages,
fixture identifiers, versioned schemas, licensing and redirects. Create a
reviewed migration plan; do not move current implementation sources, change
packages or publish a site solely by virtue of this staging metadata.

## Reader-oriented navigation (accepted direction, 2026-11-25)

Follow the [navigation restructuring handoff](navigation-restructure.md).
The target primary sections are DeskMate, File Formats, Recovery, Research,
and Project, in that reading order. Each hub is a substantive introduction,
annotated resource guide, and link to neighbouring hubs, not merely a list.
Do not add primary sections just because the source corpus grows. Use
subsection metadata and cross-links for application/release/evidence
relationships. Keep internal planning accessible but subordinate. Retain
source roles independently of reader navigation and use readable labels.

Existing page IDs, routes and anchors are public compatibility contracts;
section assignments must not dictate URL prefixes. The
[baseline](published-route-baseline.json) protects the pre-redesign route set.
The original rendered article-content anchors are captured from the pinned
source revision; Home/Search are route-only and layout chrome is not pinned.
Never refresh from a changed build merely to silence failures. Add new
routes/anchors after reviewed publication. Deliberate retirement requires
explicit review, an appropriate redirect or fragment alias, and a documented
baseline edit; do not use additive capture to remove existing entries.
Explain links to the source repository rather than automatically mapping all
documents or pursuing a numerical coverage target. Continue to distinguish
dated evidence from current specifications and apply the existing rights and
image-review rules. Review actual desktop/mobile previews and no-JavaScript
navigation before merging layout changes.

## Report dates and review attachments

A page's `date` in the [page map](page-map.json) records when the source says the
work happened: a date in the title, an explicit statement in the report, or the
date suffix that the report's own filename carries. Do not infer a date from a
Git commit, a filesystem timestamp, or the date a page was added to the map.
Leave the value null when the source records none, and say on the section hub
that the entry is undated rather than guessing; the Research hub names the two
entries that have no recorded run date.

Relative links resolve against the source file. A destination that does not
exist is a build failure rather than a repository link, so a mistyped path
cannot become a quietly broken external URL that no site check inspects. Exact
filename case is checked too, because the Linux build and GitHub are
case-sensitive even when the author's workstation is not.

Screenshots supplied for pull-request review belong under
`docs/site/review/<pull-request>/` with a REUSE sidecar. They are review
attachments, never published assets: nothing there is copied into the site,
listed in the image manifest, or included in the source distribution. Delete
the directory when the review closes, and use the documented image-manifest
route for anything that should appear on the published site.
