# File formats

DeskMate documents are ordinary DOS files with their own internal structure.
Each program writes a format that reflects the way that program thinks: a
worksheet stores cells, formulas, and labels; a drawing stores object records
and a font; a calendar stores appointments and its own indexes. This section
explains those structures, the conventions shared between them, and the limits
of what has actually been verified.

The pages here are of two kinds, and the distinction matters. Manufacturer
references reproduce what Tandy documented, including its terminology and its
gaps. Maintained guides describe structures the project has re-derived and
confirmed against real files. Where a structure is inferred rather than
confirmed, the page says so.

## Start here

1. [Architecture and scope boundaries](../architecture.md) explains how the
   independent format library is organized and what it deliberately does not
   claim.
2. [Built-in application and format inventory](../inventory.md) maps each
   application to the format it writes, which is the quickest way to find the
   right page.
3. [Tandy Appendix A format crosswalk](../reference/tandy-format-crosswalk.md)
   aligns the manufacturer's names and structures with the project's own.

## Architecture and shared structures

- [Architecture and scope boundaries](../architecture.md) covers the component
  boundaries, the supported operations, and the separation between the generic
  library and application-specific profiles.
- [Common Page Setup header](../reference/tandy-common-headers.md) documents a
  structure shared by several programs, which is why it is described once
  rather than repeated per format.

## Application format guides

These are the maintained, per-application references:

- [Tandy Filer format reference](../reference/tandy-filer-format.md)
- [Tandy Text format reference](../reference/tandy-text-format.md)
- [Tandy Draw format reference](../reference/tandy-draw-format.md)
- [Tandy Worksheet format reference](../reference/tandy-worksheet-format.md)
- [Tandy Address Book format reference](../reference/tandy-addressbook-format.md)
- [Note Pad and Corkboard file format](../reference/deskmate-corkboard-format.md)
- [Print Companion document observations](../reference/deskmate-print-companion-formats.md)
- [DeskMate Calendar laboratory specification](../formats/calendar/CALENDAR_FORMAT.md)
  is a dated laboratory specification retained as historical evidence; a
  maintained successor specification is still outstanding.

## Manufacturer and platform reference

- [Tandy Appendix A format crosswalk](../reference/tandy-format-crosswalk.md)
  is the index to the manufacturer's own format appendix.
- [Common Page Setup header](../reference/tandy-common-headers.md) documents the
  shared header structure used by Tandy's printing paths.

## Sources and evidence boundaries

A manufacturer reference records what the vendor published, including
behavior that later observation contradicted. A maintained guide records what
this project has verified against files it created or holds. A dated snapshot
records a point-in-time understanding that has not been revisited. Those roles
are shown on each page rather than merged into a single confident voice.

Read, write, and export capability is not implied by a documented structure.
Supported operations are stated per format in [Recovery](recovery.md), and
unsupported records are preserved rather than silently rewritten.

## Continue

- Previous: [DeskMate](deskmate.md).
- Next: [Recovery](recovery.md) for the tools that read and write these files.
- Evidence behind the format claims: [Research](research.md).
