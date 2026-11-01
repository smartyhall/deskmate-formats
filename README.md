# deskmate-formats

**Preserving Tandy DeskMate file formats through reverse engineering, open
specifications, and independent tools.**

This public, evidence-driven digital-preservation project aims to document the
native file formats used by Tandy DeskMate and develop independent tools to
inspect, read, write, export and eventually convert them. **DeskMate 3.05
Calendar is the first implemented format, not the project boundary.**

The project is not affiliated with Tandy. It does not distribute original
DeskMate executables, disk images, real user databases or complete installed
snapshots. Original experimental evidence is preserved separately in DOSLAB;
the repository's portable tests use independently generated synthetic data.

## Project status

| Area | Status | What is available or being investigated |
|---|---|---|
| **Calendar 3.05** (`PERSONAL.CLN`) | **Experimental tools** | Read-only parsing, indexed record inspection, text/JSON output, and a narrowly bounded append writer for verified six-page layouts |
| **Calendar storage research** | **Ongoing** | Documented page allocation and deleted-record retention; general allocation, record reuse, editing and recovery are not yet implemented |
| **DeskMate screen-state research** | **Exploratory** | Partial Calendar schedule text recovered from read-only emulator RAM captures; not a general screen reader or automation interface |
| **Other DeskMate applications** | **Future work** | Address Book, Filer, Text, Worksheet and Draw have no validated storage models or implementations yet |

The tools are experimental and support only explicitly measured cases. See
[compatibility](docs/compatibility.md) for exact limits and the
[format inventory](docs/inventory.md) for the broader preservation scope.

## Current functionality

* A read-only DeskMate 3.05 Calendar PERSONAL.CLN parser: validated six-page layout,
  indexed record enumeration, opaque internal row, raw fields and text/JSON output.
* An experimental bounded append writer: measured date/time mappings, printable
  ASCII descriptions, capacity checks and atomic no-overwrite new output.
* A five-appointment generated sample was visually accepted by DeskMate. After
  unchanged-event OK and clean exit, all database bytes and installed-file contents
  were identical. This is narrow application evidence, not general compatibility.

Only four dates and six quarter-hour time values are decoded. Alarm semantics,
multi-page allocation, long IDs, editing, deletion, arbitrary text, tied index keys
and general conversion are unsupported. Other applications have **no implementation
or validated storage model**. See [compatibility](docs/compatibility.md).

## Installation and use

Python 3.13 or 3.14 is the verification target; runtime uses the standard library.

```sh
python -m venv .venv
# Activate with .venv/bin/activate (POSIX) or .venv/Scripts/Activate.ps1 (PowerShell).
python -m pip install .
deskmate-calendar path/to/PERSONAL.CLN
deskmate-calendar path/to/PERSONAL.CLN --json
# Read source and publish a NEW output file; defaults to the measured BETA456 case.
deskmate-calendar-append source.cln new-output.cln
deskmate-calendar-append source.cln new-output.cln --appointments additions.json
```

The JSON batch is an array of objects with exactly `date`, `start_minutes`,
`end_minutes` and `description`. Example:
`[{"date":"2027-11-01","start_minutes":660,"end_minutes":720,"description":"BETA456"}]`.
Use disposable inputs and new output paths. Hard-link publication requires a
supporting filesystem and fails safely without an overwrite fallback.

Python API: `deskmate_formats.calendar.personal.parse_bytes/parse_file` and
`deskmate_formats.calendar.writer.Appointment/append_appointment/capacity/write_new`.
The implementation remains Calendar-specific; no shared engine is asserted.

## Tests and development

```sh
python -m pip install '.[dev]'
python -m unittest discover -s tests/portable -v
python -m reuse lint
python -m ruff check src tests/portable tools
python tools/audit_repository.py
python -m build
```

Portable tests generate synthetic bytes without opening DOSLAB. Private tests are
separate and require an explicit `DOSLAB_ROOT`; the complete original 72-test lab
suite is **not** claimed portable. See [test/evidence instructions](docs/evidence/README.md).
CI builds and installs the wheel, checks imports/entry points and runs only portable
tests on Windows/Linux with Python 3.13/3.14. CI has no emulator, archival fixtures,
publication steps, external paid services or AI dependencies.

## Documentation

* [Format inventory](docs/inventory.md) and [architecture](docs/architecture.md)
* [Observed container structures](docs/containers/README.md)
* [Calendar specification](docs/formats/calendar/CALENDAR_FORMAT.md) with original
  evidence/confidence distinctions and historical experiment checkpoints retained
* [Experimental method](docs/experiments/methodology.md), [Phase III-A](docs/experiments/phase-iii-a.md)
* [Evidence provenance](docs/evidence/README.md), [verification](docs/verification.md)
* [Interoperability roadmap](docs/interoperability.md), [contributing](CONTRIBUTING.md)

[E15](docs/experiments/e15-page-boundary.md) observed Calendar allocating one extra
data page for a 24-byte BOUND12 record when 17 bytes remained. The parser and
writer retain their conservative six-page scope; no general allocator is implemented.

[E16](docs/experiments/e16-page-reclamation.md) observed that deleting the sole
page-6 event leaves the seven-page file and retired payload on disk. Page-reuse
and deletion-marker semantics remain unimplemented and experimentally unresolved.

[Screen-state research](docs/research/screen-state.md) recovered partial Calendar
schedule text through read-only RAM captures; it is not a general screen API.
[Phase II](docs/research/screen-state-mcp.md) corrected the MCP port and verified
one targeted read; repeatability was blocked at that checkpoint.
[Phase III](docs/research/screen-state-phase3.md) demonstrates repeated targeted
MCP reads and two interface views across restarts; date entry was blocked at
that checkpoint. The [offline RAM helper](docs/research/ram-analysis.md) preserves raw
context and distinguishes physical addresses from capture offsets.
[BIOS keyboard research](docs/research/mcp-keyboard-input.md) verifies DOS input
and repeated Calendar date navigation on the stock SDL1 build, resolving the
masked-field editing blocker. A separate stdio MCP configuration is prepared for
later review; the tests used an isolated local client, not a new Codex registration.
[The integration follow-up](docs/research/mcp-keyboard-integration.md) confirms
natural date overtyping and complete unfocused navigation. A restricted keyboard
MCP entry is now persisted locally; active tool visibility awaits a later session.

## Contributing

Corrections to the specifications, reproducible observations, independently
authored tests and interoperability tooling are welcome. See
[CONTRIBUTING.md](CONTRIBUTING.md) and the repository's issue templates.
Please do not submit DeskMate binaries, disk images, original user data or
private laboratory memory dumps as fixtures.

## Licensing

Software: **GPL-3.0-or-later**. Formal technical specifications:
**GPL-3.0-or-later OR CC-BY-4.0**. General documentation:
**GPL-3.0-or-later OR CC-BY-SA-4.0**. Recipients may choose either offered license
for a dual-licensed file, respecting attribution/conditions of the chosen license.
Adjacent REUSE-compatible .license sidecars provide exact per-file declarations.

Copyright (c) 2026 Michael A. Hall, except where another accurate notice applies.
No ownership or redistribution rights are claimed over original DeskMate software,
media, databases, manuals or third-party works. Complete standard texts are in
[LICENSES](LICENSES); [LICENSE](LICENSE) is the software GPL text.
See [LICENSING.md](LICENSING.md) and [CONTRIBUTING.md](CONTRIBUTING.md).
The repository is publicly hosted. GitHub Actions runs the portable
Windows/Ubuntu Python 3.13/3.14 matrix on pushes and pull requests. See
[dependency maintenance](docs/dependency-maintenance.md) for update review.
