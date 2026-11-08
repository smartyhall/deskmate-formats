# Compatibility and supported versions

The table below describes the unchanged default Calendar `observed` profile.
The explicit experimental `sdk` profile is described after it.

| Component | Current supported scope |
|---|---|
| Python | Portable CI on Windows/Ubuntu with Python 3.13/3.14; selected historical local validation on Windows |
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
archival byte-perfect or application tests. The repository is publicly hosted. CI runs portable tests on Windows/Ubuntu
with Python 3.13/3.14, without original commercial media, private archives or
live DeskMate. Historical local results remain in [verification.md](verification.md).

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
structural checks. On 2026-11-07 the operator reported reviewing all 29
appointments across the 14 dates in DeskMate 3.05: all appeared as expected,
including their displayed alarm states. This is successful **operator-reported
native display/read inspection**, beyond a parser self-round-trip. It remains
tool-generated. [Exact candidate and evidence limits](research/calendar-14-days-operator-report.md).
No independently rehashed guest-loaded file, installed-tree capture, native
edit/rewrite specimen or alarm-firing test was supplied. Other encodings,
arbitrary times, 30-day capacity and record lifecycle operations remain unqualified.

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
reconstruction or network synchronization. The operator-reported Calendar
display inspection does not establish native save persistence or Address Book
multicontact compatibility.

## Separate experimental new-file Calendar builder

The explicitly opt-in `calendar.experimental_new.build_new(..., experimental=True)`
starts only from exact hash-pinned E02, can append fresh data pages 6 and 7, and
rejects a ninth page, existing multipage inputs, ties, unsupported fields and more
than 100 additions. It is separate from the six-page `observed`/`sdk` append APIs,
which are unchanged. Static DMDB 3.05 paths decode MSB-first packed-12 page chains
and reproduce both published E15/E19 header transitions. Reuse, deletion, packing,
index growth and general allocator support are not enabled.

A deterministic 61-appointment / 30-date / eight-page candidate passes a separate
raw-byte checker. It is **tool-generated; native open/save acceptance pending**.
See [source locations, commands, exact hash and limits](research/dmdb-page-allocator.md).
The complete [30-day binary](../tests/fixtures/application-generated/calendar/sdk-30-days-allocator-tool-generated.cln)
and [expected appointments](../tests/fixtures/application-generated/calendar/sdk-30-days-allocator-tool-generated.expected.json)
are now included in Git for review; they remain excluded from wheel/sdist.
The [operator guide](research/calendar-30-day-native-acceptance.md) covers all
30 dates and data pages 4, 6 and 7, with a separate optional persistence trial.
Publication and independent offline validation do not establish native acceptance.

## Manual UI time-normalization evidence (not a native codec claim)

In a separately observed DOSBox-X Add Event experiment, full-minute input
5:08 PM–5:31 PM was displayed after save as **5:00 PM–5:45 PM**. This is
consistent with outward quarter-hour rounding for that example; it does **not**
prove universal UI behavior or constrain all possible stored time bytes.
[Research note](research/calendar-ui-time-normalization.md). Native writer
profiles still accept only their documented quarter-hour values; the proposed
CalDAV precision-preservation behavior is a [future sync policy](interoperability.md),
not an implemented converter.
