# Reference-site preparation (generator-independent)

This directory prepares a future **DeskMate and Tandy reference knowledge base**
without publishing a website or relocating the authoritative research files.
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

## Planned reference navigation

1. System architecture and common services.
2. Built-in applications and their native file formats.
3. Cross-application interchange, shared resources and runtime behavior.
4. Recovery tools, verified compatibility and limitations.
5. Experimental evidence, dated reports and unresolved questions.
6. Versioned software releases, SDK material and the wider Tandy ecosystem.
7. Visual atlas and design-system evidence (after individual image review).

A page may have a planned route without yet being a final specification. The
page map deliberately references existing Markdown rather than copying it into
a second source tree. When a maintained specification is authored, replace the
mapped source by review and retain the historical evidence as a dated record.

## Presentation and delivery are later decisions

The **initial theme will be based on
[BOOTSTRA.386](https://github.com/kristopolous/BOOTSTRA.386)**; a later,
separately authored theme should use measured DeskMate UI conventions for
DeskMate/Tandy material. This is a presentation decision, not a dependency of
the documentation or metadata. The generator, deployment target and repository
split are not selected. In particular, this directory is **not** a generated
site root and no build or publishing workflow is enabled.

Before choosing a BOOTSTRA.386 release, assess its Bootstrap compatibility,
upstream attribution, redistribution terms, keyboard access, reduced-motion,
contrast and no-JavaScript behavior; do not adopt a visual effect that hides
the page when scripting is unavailable. Preserve semantic HTML and readable
fallbacks when introducing the theme.

## Current safety boundary

No raw native screen captures, copyrighted source scans, proprietary
applications, ROMs, original archival records, private evidence paths, or
commercial media are site assets. The private inventory is not the public
media directory. An image may enter a future public site only after an
explicitly documented publication basis and review of its actual contents.
Previously authorized, manifest-checked synthetic Draw comparisons are a
narrow exception, not blanket permission for UI screenshots.

## Validation

From the repository root:

    python tools/check_reference_pages.py

The checker uses only the Python standard library. Portable tests cover the
page-map contract, duplicate routes, missing files and path containment.
This step prepares navigation and source ownership; it does not render a site.
