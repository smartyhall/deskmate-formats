# deskmate-formats

Independent preservation of the native file formats used by Tandy DeskMate.
The long-term objective is complete technical documentation and independently
developed tools to inspect, read, write and convert standard DeskMate application
files. **Calendar is the first implemented format, not the project boundary.**

This is an early, evidence-driven project. It is not affiliated with Tandy and
contains no DeskMate executables, disk images or complete installed snapshots.
The original DOSLAB archive remains the authority for experimental evidence.

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

E15 is proposed only; this repository transition performs no new format experiment.

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
The repository remains local with no remote or publication configured.
