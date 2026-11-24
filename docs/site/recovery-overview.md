# Preserving and recovering files

The purpose of our preservation tools is to help people retain the documents they created with DeskMate and, where possible, use their contents on a modern computer. The original file is irreplaceable. A recovered text document, spreadsheet, picture, or audio file is a useful projection of that original, not a substitute for preserving it.

Start with a copy of the original media or files. Keep the original bytes unchanged, and record the source and version of DeskMate when known. Different applications and releases may use the same filename extension; identification should come from file structure and provenance, not the extension alone.

## What can be recovered?

The [DeskMate Preservation Workbench](../preservation-workbench.md) is the practical guide to our offline command-line tools. It explains how to inspect a file, export a verified recovery bundle, examine the result, and check the preserved byte identities.

Depending on the measured input profile, the workbench can produce modern previews and exports for spreadsheets, text, drawings, Filer records, calendars, address books, recordings, and musical scores. Examples include CSV, plain text, SVG, iCalendar, vCard, WAV, and MIDI. Not all features of every file can be faithfully reproduced. The workbench's documentation identifies known omissions, opaque data, approximations, and compatibility restrictions.

## Three stages of recovery

**Identify.** Inspect the original structure and decide whether the input belongs to a supported profile. The [application inventory](../inventory.md) and [technical reference](technical-overview.md) explain the relevant file families and evidence.

**Export.** Create a separate recovery bundle with the original bytes, derived data, and available modern previews. Keep the manifest alongside the recovered artifacts. Do not overwrite the native source.

**Verify.** Use the workbench's verification operation to check the bundle against its recorded file identities. Examine diagnostics and compare the resulting content with the original application if possible. A successful bundle check verifies its recorded integrity; it does not certify that every historical feature was understood.

The [software and releases guide](software-overview.md) leads to native installation procedures if the original application is required for comparison.

## Preserving the printed appearance

There is a difference between recovering editable content and reproducing what a historical printer would have printed. Our [Print Companion and native printing study](../research/print-companion-20261123.md) records an example of original printer output captured from DeskMate and reconstructed as a PDF. This is a measured experiment, not a general-purpose print converter for every application or printer.

## Follow the evidence

If a file is unsupported, retain it intact. An unresolved structure may become readable as research progresses. The next stop is [Research, evidence, and the project](research-overview.md), which explains how native tests, historic documentation, and independent comparisons inform the recovery tools.
