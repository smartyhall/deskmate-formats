> Historical lab parser notes; package commands and current limitations are documented in the root README and compatibility.md. Relative lab evidence stays private.

# Initial read-only PERSONAL.CLN parser

Python 3.10+ and standard library only; validated here with installed Python 3.13.
Run from the DOSLAB directory (or use absolute paths):

```powershell
py -3.13 -B ANALYSIS\SCRIPTS\calendar_personal_cli.py EXPERIMENTS\PHASE2\E08_two_events\files\DESKMATE\PERSONAL.CLN
py -3.13 -B ANALYSIS\SCRIPTS\calendar_personal_cli.py EXPERIMENTS\PHASE2\E08_two_events\files\DESKMATE\PERSONAL.CLN --json
py -3.13 -B -m unittest discover -s ANALYSIS\SCRIPTS -p test_calendar_personal.py -v
```

Expected E08 listing: ID `0x11`, LPHa124, 2027-11-01 Monday, 09:15–10:15;
ID `0x12`, BETA456, same date, 11:00–12:00. ID `0x10` is displayed separately
as an opaque internal/control row and excluded from appointment counts.
Times use 24-hour `HH:MM`, without an inferred timezone. Noon is `12:00`.

`calendar_personal.py` exposes `parse_file(path)` and `parse_bytes(bytes)`;
`calendar_personal_cli.py` handles presentation only. The file API opens `rb`,
reads at most 6,145 bytes, and never writes a database. The CLI writes only stdout
and errors to stderr: exit 0 for a structurally accepted database, 2 for an input
error. JSON contains separate `appointments` and `internal_records` arrays,
record IDs, offsets, lengths, raw record/field hex and warnings. Raw offsets are
zero-based; row length includes its row terminator, excludes the list terminator.

## Supported scope and undecoded output

This first implementation deliberately recognizes the observed 6,144-byte,
six-page layout. It validates the `.FIL` magic, metadata page, table/page roles,
index headers, pointer/ID uniqueness and bounds, indexed schema, field framing,
row coverage, list markers, padding and observed counter relations. Appointment
addresses come from index triples, not fixed appointment offsets or descriptions.
The known metadata page and table/index layout remain format-profile assumptions.
Low IDs with `80 + one low-ID byte` framing are accepted below `0x80`; that is a
conservative framing restriction, not proof of the complete ID codec.

Decoded dates are limited to the four observed mappings: 2026-10-23,
2026-10-24, 2026-11-01 and 2027-11-01. Decoded weekday values are Sunday,
Monday, Friday and Saturday. Decoded time bytes are A4, A5, A8, A9, AC and B0
(09:00, 09:15, 10:00, 10:15, 11:00 and 12:00). The documented formulas are
applied only to these measured mappings. Other calendar-valid dates and unknown
weekday/time values are preserved raw with `null` / `<undecoded>` and warnings;
an impossible date or a conflicting decoded weekday is an error.

Printable ASCII descriptions within the declared 120-byte limit are decoded;
non-ASCII/non-printable descriptions remain raw. This does not establish a
general text/escape codec or experimentally validate all description lengths.
Duration and Protected are **always undecoded**, even when empty or `31`.
**Alarm is not decoded:** alarm-off UI observations do not identify its storage.
An exit-0 result can contain undecoded values; consumers must inspect warnings.

The internal row is recognized by its observed field signature and ID, not by
an invalid date alone. An unknown variant is rejected rather than silently
discarded. All its bytes remain available. Unknown header bytes and table tokens
are retained; undocumented header semantics/checksums are not validated.

Growth/linked pages, index holes/tombstones, unknown schemas, long IDs, unindexed
data and unrecognized structural layouts are rejected with `CalendarParseError`
(stable `code`, message, and offset where available). Count equals enumerated
rows and next-ID equals maximum ID + 1 only in this supported profile. E09's
observed trailing-record deletion restored the E07 bytes and satisfies these
checks without changing parsing logic. E12 also supports deletion of a physically interior row with compaction and
renumbering. Other layouts and deletion patterns remain unverified and can
invalidate these relations. E10's same-sized replacement
addition reused ID0x12, record0x103F and index0x1434 without parser changes. This
supports the observed tail-reuse case, not general free-space allocation. There is no writer, salvage mode,
GUI dependency or speculative/extrapolating decoding option.

## Tests

The suite checks all E00–E14 fixture hashes, counts, descriptions, dates and times,
internal-row exclusion and unchanged source bytes/mtime. It covers truncated
files, corrupt headers/schema/indexes/records, duplicate targets/IDs, malformed
dates, unsupported values, CLI output/errors, read-only opens and records moved
and indexes reordered in memory. Synthetic byte mutations are never saved as
experiment databases. Set `DOSLAB_ROOT` if fixtures are elsewhere; missing
fixtures fail the tests rather than silently skipping them.

E09 returns one user appointment (LPHa124); the trailing BETA456 record and index
entry are absent, and its entire database equals E07. The regression suite has
55 tests including E09's raw deletion, E10's reuse, E11's growth/relocation, E12's interior deletion/renumbering, E13's restoration, E14's non-trailing shrink/compaction
and their CLI outputs. Parsing logic remains unchanged for these fixtures.

E10 returns LPHa124 plus GAMMA45. Compared with E08, only the seven description
bytes differ; all allocation metadata is identical. No parsing logic changed.

E11 grows the first logical description to LPHa124XYZ. Actual layout differs from
a simple +3 following-row shift: GAMMA45 moves to 0x1027/ID0x11, while the enlarged
LPHa124XYZ moves to 0x103F/ID0x12 (27 bytes). Both index entries still resolve;
index order differs from physical row order. IDs are snapshot-local storage
identifiers and did not remain stable even for the untouched logical GAMMA45
event. Its bytes after the two-byte row prefix remain identical. The parser
already resolves this case through index targets without code changes.

Description lengths 4, 7 and 10 are now experimentally observed; other lengths and
encodings remain outside experimental coverage even where the parser can retain
or decode their raw ASCII representation. No general growth/compaction policy
is established from this single edit.

E12 deletes physically interior GAMMA45. LPHa124XYZ moves backward by the
deleted row's length and changes ID0x12 to ID0x11; its complete payload after
the row prefix is unchanged. The trailing index entry and unused data tail
are zero-filled. The unchanged parser enumerates only LPHa124XYZ. Regression
checks derive relocation and index targets from parsed baseline rows rather
than hardcoding the survivor's physical address.

E13 shortens the sole description LPHa124XYZ to LPHa124. The 27-byte row
becomes 24 bytes, retaining its ID, address, index entry and all other fields.
Row/list terminators move backward three bytes and released space is zero-filled.
The complete database equals E07 and E09 byte for byte. The unchanged parser
returns exactly one LPHa124 appointment with the documented date and times.
The final snapshot cannot distinguish in-place shrinkage from delete/reinsert
of a sole trailing row; no universal update algorithm is established.

E14 branches from E11 and shrinks only GAMMA45 to GAMM. GAMM stays at its
old address with ID0x11 and shortens24→21bytes; the untouched LPHa124XYZ row
shifts backward3bytes with its complete27bytes and ID0x12 unchanged. Only its
index address is adjusted. Counters stay3/19; the list marker moves back3 and
the freed tail is zero-filled. The unchanged parser follows the new index
target and returns both correct events. This matches hypothesis A's final
layout and differs from the simple remove/compact/append hypothesis B;
intermediate operations are still unobserved. New relocation tests derive
addresses from parsed E11 rows, not fixed appointment locations.

Next proposed experiment: a controlled first data-page allocation boundary,
adding fixed seven-character appointments through Calendar with preserved
before/after boundary checkpoints. Observe actual new page references, index
targets, metadata, record framing and size; no allocation outcome is assumed.
The current parser intentionally rejects unsupported multi-page layouts and
must only be extended after new evidence. No E15 experiment has been performed.
