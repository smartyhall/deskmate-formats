# Technical reference

DeskMate presented related programs through a consistent interface. Underneath that interface, however, its applications use a variety of document structures, shared resources, and version-specific conventions. This section brings the technical material together by subject, so a reader can begin with the system as a whole or go directly to the format of interest.

The reference is evidence-based and incomplete. Manufacturer descriptions, measured native behavior, independent implementations, and open hypotheses are kept distinct. A file that our reader accepts is not necessarily writable by our tools, and a finding for one edition is not automatically valid for another.

## Start with the system

The [architecture and scope guide](../architecture.md) explains the relationship between DeskMate's environment, applications, and our preservation tools. The [Tandy Appendix A format crosswalk](../reference/tandy-format-crosswalk.md) connects the original developer documentation to the application's file families and makes explicit where native experiments are still needed.

The [common Page Setup header](../reference/tandy-common-headers.md) describes a manufacturer-documented structure relevant to document layout. The [database component study](../research/database-components.md) examines the executable resources behind the shared database machinery and distinguishes observed module references from unresolved runtime behavior.

## Records, contacts, schedules, and notes

Calendar, Address Book, and Filer are useful starting points for understanding DeskMate's database-backed applications. Their related structures do not mean that their schemas or record semantics are interchangeable.

The [Calendar laboratory specification](../formats/calendar/CALENDAR_FORMAT.md) preserves a dated record of the calendar investigations. The [Tandy Address Book reference](../reference/tandy-addressbook-format.md) and [Tandy Filer reference](../reference/tandy-filer-format.md) describe manufacturer-documented layouts and selected corroborating observations. For the much smaller Note Pad and Corkboard accessory, consult the [fixed-buffer format reference](../reference/deskmate-corkboard-format.md), which is distinct from the message and household databases.

## Writing, illustration, and printed documents

The [Tandy Text reference](../reference/tandy-text-format.md) covers the word processor's documented file structures, while the [Tandy Draw reference](../reference/tandy-draw-format.md) concerns drawings and their graphics records. Shared graphics deserve careful comparison because the same illustration may be embedded inside a different application container.

The [Print Companion document observations](../reference/deskmate-print-companion-formats.md) describe native greeting cards, letters, notices, name tags, and their relationship with Draw illustrations. The recovered printer streams are separate artifacts: they describe the output sent to a printer rather than a reversible representation of the original editable document.

## Numbers, sound, and music

The [Tandy Worksheet reference](../reference/tandy-worksheet-format.md) is the starting point for spreadsheet structures and manufacturer-described field meanings. The native study and recovery tool have more narrowly measured behavior, particularly when interpreting stored formula results.

The [native Sound research](../research/sound-native-20261118.md) records measured recordings and instrument profiles. The [native Music research](../research/music-native-20261118.md) describes score structure and experiments with original playback. Both are dated research reports rather than comprehensive specifications.

## Using the reference

For an existing document, start with the originating application and its version, then consult the corresponding reference and [recovery guidance](recovery-overview.md). For the underlying experiments and their limitations, continue to [Research, evidence, and the project](research-overview.md). The [software overview](software-overview.md) provides the release context for these technical findings.
