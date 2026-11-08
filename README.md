# deskmate-formats

**Preserving Tandy DeskMate file formats through reverse engineering, open
specifications, and independent tools.**

This public, evidence-driven digital-preservation project aims to document the
native file formats used by Tandy DeskMate and develop independent tools to
inspect, read, write, export and eventually convert them. **DeskMate 3.05
Calendar is the first implemented format, not the project boundary.**

The project is not affiliated with Tandy. It does not distribute original
DeskMate executables, installation media, ROMs, disk images, real user databases
or complete installed snapshots. Application-generated documents containing
controlled synthetic test data are eligible for byte-exact preservation as
[research fixtures](tests/fixtures/application-generated/README.md), including
native schemas, indexes and metadata. Private inputs and raw lab evidence
remain archived outside Git.

## Project status

| Area | Status | What is available or being investigated |
|---|---|---|
| **Calendar 3.05** (`PERSONAL.CLN`) | **Experimental tools** | Measured default plus SDK multipage/multicalendar reader; exact-source SECOND creation and first-event writers reproduce both native two-calendar byte oracles; general creation/allocation remains unsupported |
| **Calendar storage research** | **Ongoing** | E15–E19 document page growth, retained deletion data, and append behavior; no general allocator or deleted-record recovery implementation |
| **DeskMate screen-state research** | **Exploratory** | Partial Calendar schedule text recovered from read-only emulator RAM captures; not a general screen reader or automation interface |
| **Address Book 3.05** (`PERSONAL.ADR`) | **Conservative codec** | Schema-aware reader and experimental empty-to-one writer; all four A01–A04 native hashes reproduced offline; multicontact insertion remains unsupported |
| **Cross-application database architecture** | **Offline structural and call evidence** | Named DMDB binding/call thunks in all three applications and a conditional DESK INT E0 dispatch path; actual runtime vector, callback selection and record-operation dispatch remain unresolved |
| **Filer 3.05** | **Static research and one scoped native observation** | Shipped CARMAINT sample opened and exited without disk changes; disabled print commands remain unexplained. F00–F02 schema/record experiments and Filer codec are not complete |
| **86Box automation** | **DOS baseline validated** | Authenticated native client, verified Tandy RSX DOS 5.00 baseline, original guest canary, and a read-only MCP bridge tested with a synthetic native peer |
| **Other DeskMate applications** | **Future work** | Text, Worksheet and Draw have no validated storage models or implementations yet |

These experimental capabilities include SDK-derived, offline-tested cases that
have **not** all been accepted in the native application. See the dated
[project status](PROJECT_STATUS.md), [compatibility](docs/compatibility.md)
for exact limits and [format inventory](docs/inventory.md) for scope.

## Current functionality

* A read-only DeskMate 3.05 Calendar PERSONAL.CLN parser: validated six-page layout,
  indexed record enumeration, opaque internal row, raw fields and text/JSON output.
* An experimental bounded append writer: measured date/time mappings, printable
  ASCII descriptions, capacity checks and atomic no-overwrite new output.
* A five-appointment generated sample was visually accepted by DeskMate. After
  unchanged-event OK and clean exit, all database bytes and installed-file contents
  were identical. This is narrow application evidence, not general compatibility.

The default reader decodes four dates, six quarter-hour time values and the stored Alarm
setting for ordinary timed appointments. Multi-page allocation, long IDs,
editing, deletion, arbitrary text, tied index keys and general conversion are
outside the default scope. The explicit `--profile sdk` adds ordinary date/time
codecs and additional-page reading; it does not allocate pages. New combinations
remain offline-verified only. See [compatibility](docs/compatibility.md) and
[campaign progress](PROJECT_STATUS.md).

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
The reader exposes `alarm_enabled` on records and in JSON, with the complete
Protected field retained in the raw output.

For ordinary SDK-derived Calendar values, pass `profile='sdk'` or CLI
`--profile sdk`; default calls keep the measured limits. Generate the reproducible
14-day sample with `tools/generate_calendar_sample.py SOURCE.cln NEW-OUTPUT.cln`.
The source must be an appropriate six-page disposable template; the documented
sample uses the committed synthetic E02 native fixture.

The SDK reader exposes `db.calendars` and `db.calendar(name)`, with separate
configuration records and calendar-scoped IDs. Both native two-calendar fixtures
parse correctly. The separate, explicitly experimental SECOND creation and
first-appointment APIs reproduce their exact A/B bytes from pinned sources.
See the [multicalendar campaign](docs/research/calendar-multicalendar-reader-writer.md)
for complete generated binary downloads, independent validation, commands and
strict limits. General balancing, arbitrary names and native reopen/selection
acceptance remain unresolved.

Address Book API: `deskmate_formats.addressbook.Contact`, `parse_bytes/parse_file`,
`create_contact` and `write_new`. CLIs: `deskmate-addressbook SOURCE.adr` and
`deskmate-addressbook-create EMPTY.adr NEW-OUTPUT.adr --contact contact.json`.
The JSON object requires `first_name`, `last_name`, `city` and `work_phone`.
Only empty-to-one creation is implemented. See the
[Address Book checkpoint](docs/research/addressbook-codec.md) and
[versioned interchange API/examples](docs/interoperability.md).

## Reproducible Windows 10 laboratory (experimental)

The [Windows 10 Pro ISO deployment recipe](deployment/windows10/README.md) tracks
VM setup for DeskMate reverse engineering across ESXi and VirtualBox. This is
**source only**, not Windows media, a validated unattended release, or a
redistributable bundle of third-party binaries. The recipe documents current
WinGet/bootstrap, autologon and Delivery Optimization settings, private-media
boundaries, verification tests, and outstanding live installation checks.

## Read-only Observatory

Publish explicit agent events with `deskmate-observer-event` and view them
alongside separately published machine observations over localhost. The
[Observatory v2 guide](docs/research/observatory-v2-m0-m1.md) includes a
synthetic demo, private journal recovery and the read-only query API.
For a new Codex CLI task, use the opt-in
[Codex JSONL wrapper](docs/research/observatory-v2-m2.md) to send bounded
telemetry through the same journal.

The [Supervisor S0 protocol guide](docs/research/codex-supervisor-s0.md)
describes offline-tested app-server ownership and durable receipts; the
[S1 task intake guide](docs/research/codex-supervisor-s1.md) covers verified
Git discovery, manual operator decisions and read-only queue reporting. The
[operator driver](docs/research/codex-supervisor-operator-driver.md) supplies
installable S0 commands and a separately gated synthetic-only S2 bridge.
Real model dispatch requires new explicit authorization and live validation.

## Tests and development

```sh
python -m pip install '.[dev]'
python -m unittest discover -s tests/portable -v
python -m reuse lint
python -m ruff check src tests/portable tools
python tools/audit_repository.py
python -m build
```

Portable tests use synthetic data and may load committed application-generated
test fixtures without opening DOSLAB. Private tests are separate and require an
explicit `DOSLAB_ROOT`; the complete original 72-test lab suite is **not** claimed portable. See [test/evidence instructions](docs/evidence/README.md).
CI builds and installs the wheel, checks imports/entry points and runs only portable
tests on Windows/Linux with Python 3.13/3.14. CI has no emulator, archival fixtures,
publication steps, external paid services or AI dependencies.

## Documentation

* [Format inventory](docs/inventory.md) and [architecture](docs/architecture.md)
* [Observed container structures](docs/containers/README.md)
* [Cross-application architecture and comparison matrix](docs/research/cross-application-db.md),
  [component findings](docs/research/database-components.md),
  [read-only inspection tool](docs/research/structural-inspection.md), and
  [F00–F02 native runbook](docs/research/filer-native-runbook.md)
* [Audited database call map and next static task](docs/research/database-call-review.md),
  [integration and verification](docs/research/database-integration.md)
* [Issue 22: one Calendar lookup candidate and its exact dispatch blocker](docs/research/lookup-trace-22.md)
* [Calendar INT E0 static dispatch and unresolved runtime binding](docs/research/calendar-binding-25.md)
* [Controlled Calendar Alarm differential](docs/research/calendar-alarm-encoding.md)
* DeskMate SDK crosswalks for [Calendar and DMCSR](docs/research/sdk-calendar-dmcsr.md)
  and [Calendar database requests and storage](docs/research/sdk-calendar-database.md),
  with the [observer verification plan](docs/research/sdk-semantic-observer-plan.md)
* [86Box automation source review and proposed MCP observation policy](docs/research/86box-automation-preflight-23.md)
* [Read-only 86Box MCP setup and observation policy](docs/research/86box-readonly-mcp.md)
* [Read-only browser observatory and synthetic demo](docs/research/86box-observer-design.md)
* [Observatory v2 functional specification](docs/research/observatory-v2-spec.md),
  [proposed Codex laboratory supervisor](docs/research/codex-supervisor-design.md),
  and [deferred headless research appliance roadmap](docs/research/headless-research-appliance-roadmap.md)
* [Live RSX / DOS 5.00 baseline, provenance and BIOS findings](docs/research/rsx-dos5-baseline.md),
  [native automation client](docs/research/86box-client.md)
* [Visible and unattended launch modes](docs/research/86box-visible-operation.md),
  [read-only browser observer](docs/research/86box-observer-design.md)
* [Original guest canary: measured source, register, RAM and screen correspondence](docs/research/86box-guest-canary.md)
* [Calendar specification](docs/formats/calendar/CALENDAR_FORMAT.md) with original
  evidence/confidence distinctions and historical experiment checkpoints retained
* [Experimental method](docs/experiments/methodology.md), [Phase III-A](docs/experiments/phase-iii-a.md)
* [Evidence provenance](docs/evidence/README.md), [verification](docs/verification.md)
* [Interoperability contract and future sync policy](docs/interoperability.md),
  [manual Calendar time-normalization observations](docs/research/calendar-ui-time-normalization.md),
  and [contributing](CONTRIBUTING.md)

[E15](docs/experiments/e15-page-boundary.md) observed Calendar allocating one extra
data page for a 24-byte BOUND12 record when 17 bytes remained. The default parser
and writers retain their conservative six-page scope; the explicit SDK reader
can enumerate bounded additional data pages. No general allocator is implemented.

[E16](docs/experiments/e16-page-reclamation.md) observed that deleting the sole
page-6 event leaves the seven-page file and retired payload on disk. Page-reuse
and deletion-marker semantics remain unimplemented and experimentally unresolved.

[E17](docs/experiments/e17-reuse.md) and [E18](docs/experiments/e18-reuse-variants.md)
showed that new records of 20, 24, and 37 bytes were appended after a deleted
page-six row rather than reusing its retired slot. [E19](docs/experiments/e19-space-pressure.md)
observed another page allocation under storage pressure without compaction.
These experiments do not establish a general allocation or reclamation algorithm.

[Address Book Phase I](docs/research/addressbook-phase1.md) documents a no-edit
control and two independent synthetic single-contact observations, including
measured variable-length first-name storage. [Phase II](docs/research/addressbook-phase2.md)
adds phone-length and City-field controls. Both predate implementation.
The later [codec checkpoint](docs/research/addressbook-codec.md) implements the
verified field subset and generates 25 separate single-contact files. A single
populated multicontact book still requires native index evidence.

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
Preserve application-generated synthetic test files with hashes and provenance.
Do not submit DeskMate executables, installation media, ROMs, disk images, real
user data or private laboratory memory dumps as fixtures.

## Licensing

Software: **GPL-3.0-or-later**. Formal technical specifications:
**GPL-3.0-or-later OR CC-BY-4.0**. General documentation:
**GPL-3.0-or-later OR CC-BY-SA-4.0**. Recipients may choose either offered license
for a dual-licensed file, respecting attribution/conditions of the chosen license.
Adjacent REUSE-compatible .license sidecars provide exact per-file declarations.

Copyright (c) 2026 Michael A. Hall, except where another accurate notice applies.
No ownership or redistribution rights are claimed over original DeskMate software,
installation media, real user databases, manuals or third-party works. Native
format structures and facts are not claimed as project-owned copyright. Complete standard texts are in
[LICENSES](LICENSES); [LICENSE](LICENSE) is the software GPL text.
See [LICENSING.md](LICENSING.md) and [CONTRIBUTING.md](CONTRIBUTING.md).
The repository is publicly hosted. GitHub Actions runs the portable
Windows/Ubuntu Python 3.13/3.14 matrix on pushes and pull requests. See
[dependency maintenance](docs/dependency-maintenance.md) for update review.
