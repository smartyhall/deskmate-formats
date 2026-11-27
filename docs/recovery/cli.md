# Command-line tools

The project installs a set of console commands alongside the Python package.
This page says which command to reach for and what each one is for. It is a
map, not a reference: run `<command> --help` for the authoritative options of
the version you have installed, and check
[Compatibility and supported versions](../compatibility.md) before relying on any
operation.

Work on a copy. None of these commands is a substitute for preserving the
original media, and the writing commands are deliberately narrow.

## Document recovery

| Command | Purpose |
| --- | --- |
| `deskmate-preserve` | Inspect, export, and verify Preservation Workbench bundles. This is the general entry point for a folder of documents. |
| `deskmate-calendar` | Read and inspect Calendar files. Presentation is kept separate from the parser, so diagnostics stay readable. |
| `deskmate-calendar-append` | Bounded, append-only writer for the observed six-page Calendar profile. It refuses work outside that profile rather than approximating. |
| `deskmate-addressbook` | Read Address Book diagnostics, or create a new one-contact experimental file. |
| `deskmate-addressbook-create` | The creation entry point for the same experimental one-contact profile. |

`deskmate-preserve export --ff1 LOCAL.FF1` projects supported unrotated outline
labels using an explicitly supplied local base face; the bundle records the
family and its hash and preserves the original document.

## Formats and media

| Command | Purpose |
| --- | --- |
| `deskmate-font` | Inspect, build, and interchange measured Draw font (FF1) outlines. |
| `deskmate-sound` | Read Sound recordings and instrument sample descriptors. |
| `deskmate-music` | Read Music scores and preserve their serialized event streams. |

## Laboratory automation, not recovery

These commands exist for the research lab. They need emulator or agent
resources, they are covered by separate authorization, and they are not part of
recovering a document:

- `deskmate-86box-mcp` — read-only MCP stdio service with an optional loopback
  browser observatory.
- `deskmate-86box-observer` — deterministic fictional scenes for testing the
  observer without an emulator.
- `deskmate-observer-event`, `deskmate-observer-codex` — publish explicit
  events to a private local Observatory journal.
- `deskmate-supervisor-task`, `deskmate-supervisor-s0`,
  `deskmate-supervisor-s2`, `deskmate-supervisor-s3` — explicit, gated
  supervisor preparation and dispatch commands.

They are listed so that a reader who finds them in `pip` output knows what they
are and that they are out of scope for recovery.

## Choosing between reading and writing

Reading a file, previewing it, exporting it, and writing it back are separate
capabilities. A command that reads a profile successfully does not imply that
it can write that profile, and the experimental writers reject documents
outside the profile they were measured against instead of producing a
plausible but incorrect result.

## Sources and evidence boundaries

The purposes above are taken from the module descriptions of the entry points
declared in `pyproject.toml`, and the export example is the one documented in
[Compatibility and supported versions](../compatibility.md). Supported profiles
and their limits are stated there and in
[DeskMate Preservation Workbench](../preservation-workbench.md); this page does
not expand them.

## Continue

- [Recovery](../hubs/recovery.md) for the workflow this fits into.
- [Compatibility and supported versions](../compatibility.md) for measured
  profiles.
