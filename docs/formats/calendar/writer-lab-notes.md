# Bounded experimental Calendar writer — Phase III-A

`calendar_writer_poc.py` now supports repeated **append-only** additions in the
observed 6,144-byte, single-data/index-page profile. The original E07→E08 byte-perfect
regression remains. Existing parser/CLI code and preserved fixtures are unchanged.

```powershell
# From DOSLAB: default append remains BETA456, using a NEW output file.
py -3.13 -B ANALYSIS\SCRIPTS\calendar_writer_poc.py source.cln new-output.cln
# Optional JSON array of appointments, applied in the listed insertion order:
py -3.13 -B ANALYSIS\SCRIPTS\calendar_writer_poc.py source.cln new-output.cln --appointments additions.json
py -3.13 -B -m unittest discover -s ANALYSIS\SCRIPTS -p 'test_calendar*.py' -v
```

Each JSON object requires exactly `date` (ISO date), `start_minutes`, `end_minutes`
and `description`. Example: `{"date":"2027-11-01","start_minutes":660,"end_minutes":720,"description":"BETA456"}`.
API: immutable `Appointment`, `append_appointment(bytes,event) -> bytes`,
`capacity(bytes)` and `write_new(path,bytes)`. Source reads are bounded to6,145bytes.

Accepted dates: 2026-10-23,2026-10-24,2026-11-01,2027-11-01. Accepted time values:
09:00,09:15,10:00,10:15,11:00,12:00, with start<end. Descriptions must be1..120
printable ASCII characters; control characters/non-ASCII are rejected. The schema
limit120 is a conservative structural cap; application validation here used
seven-character descriptions, not every accepted length. Duration stays empty
and Protected stays raw ASCII1 (hex31). Other opaque values are rejected for new
records. Alarm encoding is not known; those literals reproduce the observed
alarm-off profile and are not interpreted as a general alarm flag.

The parser validates all source structures. Existing user values must be fully
decoded and use the supported opaque profile. Tied date/start keys are rejected,
including duplicate appointments; tie sorting remains unknown. Physical rows are
never edited/moved: new records append before the list marker. ID and counters
derive from metadata/maxID, addresses from indexed row ends. Index triples are
inserted in chronological date/start order, with the internal entry first.
This preserves all old row bytes/addresses, but their index slots can change.
Capacity reserves both the data list marker and one complete zero index sentinel;
both pages and low-ID framing must fit. No page allocation, deletion, editing,
compaction, arbitrary schemas, long IDs or general rewriting is implemented.

Every result is parsed and existing-row preservation checked before return.
`write_new` stages a complete validated file in the destination directory, flushes
and fsyncs it, then atomically publishes a hard link and removes the temporary
name. Existing destinations, including source aliases, cannot be overwritten.
Unsupported hard-link filesystems fail without an overwrite fallback; directory
crash durability remains filesystem dependent. CLI exit0 success/2 error.

Phase III-A generated five user events from verified E07. Insertion order after
existing LPHa124: BETA456(2027-11-01,11–12), EARLY26(2026-10-23,09–10),
MID2026(2026-11-01,10–11), LATEOCT(2026-10-24,09:15–10:15).
Physical order retains insertion order; index order is EARLY26,LATEOCT,MID2026,
LPHa124,BETA456. Independent screenshots verified all events in DeskMate itself.
An unchanged EARLY26 Change Event OK was submitted, then Calendar exited cleanly.
All6,144 database bytes and all126 installed-file contents were preserved exactly.
This demonstrates compatibility of this chronological index with this sample;
it does not prove unsorted indexes would fail or identify Calendar's search code.
No-op submission may not force a write when nothing changed; the final binary
identity establishes absence of observed normalization, not an internal write trace.

Artifacts: `EXPERIMENTS/PHASE3A/multi_record` contains generated file, complete
before/after trees/manifests, insertion sequence, parser outputs, capacity,
source backups and screenshots. Reports: `ANALYSIS/PHASE3A_REPORT.md`,
`PHASE3A_roundtrip_comparison.json/.md`, `PHASE3A_VALIDATION.json` and
`LOGS/PHASE3A_TESTS.txt`. Prior PoC output/report/source copies remain preserved.

Tests cover multiple appends, insertion/index order differences, all sample
values, preservation, independent E08 identity, atomic output/failure cleanup,
capacity arithmetic/guard failures, malformed files and unsupported input. Capacity
guard exhaustion tests inject capacity limits; no nearly full database was
generated, even by tests. Actual multi-page allocation remains untested.

E15 is **proposed only** in PHASE3A_REPORT.md. Current sample has864 data bytes,
157 index entries and106 low IDs free. Thirty-six24byte rows fit by space, but
only15 distinct supported date/start keys remain. A proposed11 additions with
fixed60-character descriptions (77byte rows) would leave17bytes; a twelfth77byte
event entered by DeskMate would not fit this page. That length has not yet been
verified in DeskMate; E15 must first load/inspect the generated pre-boundary
fixture and stop on any rejection/truncation before the boundary addition.
No near-capacity database or E15 was generated/performed in Phase III-A.
