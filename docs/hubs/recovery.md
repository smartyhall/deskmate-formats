# Recovery

This section is for the person holding an old disk or a folder of files and
wanting to read, inspect, or export what is inside. It is deliberately
separate from the research sections: you should not have to read a laboratory
report to recover a document.

The order of operations matters more than the software. Preserve the original
first, work on a copy, and only then attempt conversion. A recovered file that
has lost an unsupported record is worse than an unread file that is still
intact.

## Start here

1. **Preserve the original.** Copy the media or files to a working location and
   record what you copied, from where, and when. Do not edit the original.
2. [DeskMate Preservation Workbench](../preservation-workbench.md) is the
   practical entry point: what the tools do, which operations are supported,
   and what the workbench deliberately refuses to do.
3. [Architecture and scope boundaries](../architecture.md) explains the
   supported-operation boundary, so you can tell an unimplemented feature from
   a broken one.

## Tools and supported operations

- [DeskMate Preservation Workbench](../preservation-workbench.md) documents the
  recovery tools and their intended workflow.
- [Compatibility and supported versions](../compatibility.md) is the authoritative
  list of measured profiles, and of the operations that are deliberately not
  supported for each one.
- [Command-line tools](../recovery/cli.md) says which installed command to reach for when
  you would rather work in a terminal than through a bundle.
- [Built-in application and format inventory](../inventory.md) identifies which
  program writes which format, which determines what a file is likely to be.
- [File Formats](../formats.md) is the structural reference behind the tools,
  including the structures that are only partly understood.

## Where the limits are

Recovery support is per format and per operation. Reading a file, previewing
it, exporting it, and writing it back are four different capabilities, and one
does not imply another. When an operation is not supported, the workbench is
expected to stop rather than write a plausible-looking but incorrect file.
[Compatibility and supported versions](../compatibility.md) states the measured
profiles; a format page describing a structure is not a claim that the tools
can rewrite it.

Format documentation is not a capability claim. A page in
[File Formats](../formats.md) may describe a structure precisely while the
recovery tools support only part of it, or none of it yet.

## Sources and evidence boundaries

Statements about supported operations come from tests against real and
synthetic files, not from the format description alone. Where a recovery claim
rests on a single observed file, it is reported as such and not generalised to
every release.

## Continue

- Previous: [File Formats](../formats.md).
- Next: [Research](../research.md) if you want the evidence behind a claim.
- Background: [DeskMate](../deskmate.md) for the software and its releases.
