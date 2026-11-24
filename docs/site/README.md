# Reference-site source map and editorial planning

The [DeskMate reference website](https://deskmate.retroconnect.org/) is now
**operational**, using Eleventy, the reviewed page map, and approved native
screenshots. This directory remains the generator-independent source map and
editorial workplan, not the generated site root. The reference is growing and
is **not** a finished comprehensive archive.
See the [long-term preservation roadmap](../preservation-roadmap.md) for the
agreed repository boundaries. The present repository remains the incubator for
core format readers, writers, fixtures, research and workbenches.

## What is here

- [Page map](page-map.json): stable page IDs, intended routes, and links to
  existing source documents. This is a staging index, **not** an assertion
  that all indexed sources are finished or canonical specifications.
- [Core-format and application workplan](format-workplan.md): evidence-first
  experiments needed to determine which behaviors and storage structures
  DeskMate applications really share.
- [Visual asset workflow](visual-assets.md): a path from private capture
  inventory to reviewed documentation exemplars, comparisons and a measured
  DeskMate design vocabulary.
- [Authoring rules](authoring.md): source roles, citations, cross-links,
  durable identifiers, accessibility and future migration constraints.

The existing [Tandy Appendix A crosswalk](../reference/tandy-format-crosswalk.md)
is a manufacturer-derived reference. The
[Calendar laboratory specification](../formats/calendar/CALENDAR_FORMAT.md)
is a dated snapshot. The [compatibility matrix](../compatibility.md) describes
currently supported implementation boundaries. These three source roles must
not be silently conflated by a site builder.

## Reference navigation and ongoing coverage

The public navigation follows five editorial overviews, in a suggested reading order:

1. [Discover DeskMate](../history/introduction.md).
2. [Software and releases](software-overview.md).
3. [Technical reference](technical-overview.md).
4. [Preserving and recovering files](recovery-overview.md).
5. [Research, evidence, and the project](research-overview.md).

The sidebar remains a short topic guide, not an expanded table of every article.
Each overview explains the subject and links directly to its detailed pages.
The underlying page map retains every existing ID, route, source, and role;
the full collection is still indexed for search. A new mapped detail page
must be introduced by an explanatory link from its assigned overview. The
website test checks this reachability so the compact sidebar cannot silently
hide new material.

A page may have a planned route without yet being a final specification. The
page map deliberately references existing Markdown rather than copying it into
a second source tree. When a maintained specification is authored, replace the
mapped source by review and retain the historical evidence as a dated record.

## Current presentation and delivery

The site uses **Eleventy 3**, a root-mounted GitHub Pages custom domain, and
the **unmodified [BOOTSTRA.386](https://github.com/kristopolous/BOOTSTRA.386)**
theme with separate site-layout CSS. [Website build and publishing instructions](https://github.com/smartyhall/deskmate-formats/blob/main/website/README.md)
describe the Node.js build, approved image manifest, source-map renderer,
preview/link checks, and deployment workflows. A later DeskMate-derived theme
remains a separate research/design milestone; keep the current semantic HTML,
keyboard access, no-JavaScript navigation, contrast, and reduced-motion needs
under review. The page map remains generator-neutral for future migration.

## Current safety boundary

Raw private evidence, complete applications, ROMs, commercial media,
credentials, personal records and private locators remain outside Git. The
private inventory is not automatically a public media directory. The
operator's 2026-11-21 documentary-image grant, however, authorizes ordinary
selected software-interface screenshots made with synthetic/public content,
project-generated illustrations and appropriate public reference figures,
without separate operator permission for each image. Use the manifest and
review requirements in [Visual assets](visual-assets.md); preserve third-party
rights and prohibit bulk extraction or redistribution of proprietary media.

## Validation

From the repository root:

    python tools/check_reference_pages.py

The checker uses only the Python standard library. Portable tests cover the
page-map contract, duplicate routes, missing files and path containment.
To validate and build the **actual** site, follow the
[Eleventy website instructions](https://github.com/smartyhall/deskmate-formats/blob/main/website/README.md): run `npm test`,
`npm run build`, and the generated-site link audit. GitHub Actions also
checks the approved image manifest and publication boundary.
