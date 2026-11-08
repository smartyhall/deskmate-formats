# Compatibility and supported versions

The table below describes the unchanged default Calendar `observed` profile.
The explicit experimental `sdk` profile is described after it.

| Component | Current supported scope |
|---|---|
| Python | Local verification on 3.13/3.14 Windows; initial four hosted Windows/Ubuntu CI jobs passed (owner-reported) |
| DeskMate | Only the documented Tandy DeskMate 3.05 Calendar observed subset |
| Files | Exactly 6,144 bytes, single observed data/index page per table, validated schema, low IDs |
| Dates | 2026-10-23,2026-10-24,2026-11-01,2027-11-01 |
| Time values | 09:00,09:15,10:00,10:15,11:00,12:00; writer requires start<end |
| Text | Reader decodes printable ASCII; writer accepts 1..120 printable ASCII characters; 7/10-character historical descriptions and E15 60-character generated descriptions application-verified |
| Alarm and raw fields | Reader reports `alarm_enabled` for ordinary timed appointments with empty Duration and exact Protected byte `31` (off) or `71` (on). Other cases return null. Duration and Protected stay raw in output. Writer accepts the empty/`31` profile. |
| Index ordering | Writer uses chronological date/start ordering, rejects ties; compatible with checked five-event sample |

Read-only parsing can preserve unsupported values as raw/null with warnings, but
rejects unknown structural layouts. Bounded append preserves existing physical row
bytes/IDs/addresses, may move index entries, and rejects extra pages. There is no
editing/deletion/compaction allocator, general text escaping or stable logical ID
promise. E11/E12 demonstrate IDs can change after application edits/deletions.

The private original 72 tests remain in DOSLAB. Their migrated counterparts use
the installed package and external fixtures; additional direct E07→E08/E09→E10
regressions are private as well. Synthetic success does not substitute for the
archival byte-perfect or application tests. The repository is privately hosted; the owner reports successful initial CI on
Windows/Ubuntu and Python 3.13/3.14. Historical local results remain in
verification.md; hosted CI uses only portable tests.

E15 observed a seven-page application-produced file after one allocation. The
default parser and both writer profiles reject it; the explicit `sdk` reader can
read bounded additional data pages without decoding allocation metadata.
The accepted six-page near-capacity preflight remains supported. See
[the E15 report](experiments/e15-page-boundary.md).

E16 observed deletion without truncation: the seven-page file retains a 44-prefixed
unindexed row and descriptor token001. The default profile rejects it. The shared
reader recognizes observed retired-row framing on starting/live-targeted pages;
unreferenced pages remain opaque. No reclamation is implemented. See
[E16](experiments/e16-page-reclamation.md).

## Experimental SDK Calendar profile

Opt in with `parse_bytes(data, profile='sdk')`, `parse_file(path, profile='sdk')`,
`append_appointment(data, event, profile='sdk')`, `capacity`/`write_new` with the
same keyword, or CLI `--profile sdk`. Existing calls retain their measured limits.

- Gregorian-valid dates in the byte-representable years 1980–2138, seven weekdays
  checked against the date, ordinary quarter hours 00:15–23:45 with start < end.
  Those year bounds are arithmetic bounds, not native UI qualification.
- Empty Duration and exact Protected `31`/`71` for writing ordinary events.
  Midnight, blank-time sentinels, overnight, reminders and annual events remain
  unsupported for generation. No timezone, recurrence or arbitrary text encoding.
- Reader: 6–64 complete pages, one directory page/two known tables, one index
  page per table, low IDs; additional live-index-targeted data pages and observed
  retired-row framing. Full source bytes must be retained to preserve opaque pages.
- Writer: six pages, no retired rows, original known schema and append policy;
  no allocation, editing, deletion or general index growth. Tied starts rejected.

[SDK/source findings](research/sdk-calendar-database.md) support the codec formulas;
the [campaign report](research/database-campaign.md) records generated artifacts
and evidence levels. A 29-appointment, 14-day output passes offline independent
structural checks. **It has not been opened or saved in DeskMate.** Historical
five-event acceptance does not qualify these newly generated combinations.

## Address Book profile and interchange

The [Address Book codec](research/addressbook-codec.md) reads the observed
10,240-byte four-table schema, preserving all sixteen contact fields and the full
source. Four populated field meanings are exposed; other schema names remain raw.
The experimental writer accepts an empty DATA table and creates exactly one
contact. It reproduces all four independently published A01–A04 whole-file hashes.
It refuses second insertion, extra pages, retired rows and unknown schemas.
Twenty-five synthetic contacts exist as 25 separate files, not one populated book.

[Version 1 interchange](interoperability.md) provides strict Python/JSON semantic
values and explicit loss reporting. It does not provide byte-preserving native
reconstruction or network synchronization. New native open/save tests were not run.
