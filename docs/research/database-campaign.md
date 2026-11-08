# Database implementation campaign — evidence and checkpoints

Base: `0d8c9e9cb538c65c382cd4f5478048e4397c6bb7`; started 2026-11-07.
See [current progress](../../PROJECT_STATUS.md). All new results here are offline.

## M1: shared structures

`deskmate_formats.database` reads one directory page, one index page per
table, DBCOLS definitions and low-ID page-local variable records. It retains
the immutable full input, raw descriptors/tokens, raw schema fields and raw rows.
Bounds: 6–64 complete 1,024-byte pages, at most 163 entries with a complete
zero sentinel per index. Unknown headers/layouts/framing fail explicitly.
It checks duplicate IDs/targets, overlapping records, cross-table page aliases,
directory/index counts and complete schema positions. App semantics stay outside.

Sources: [cross-application matrix](cross-application-db.md),
[fixed metadata](cross-application-evidence.json), and E15–E19. Shared
service thunks are not used as proof of a universal storage policy.
The Filer DBCOLS next-ID counterexample prevents a generic max-ID+1 check;
application writers must impose their own verified policy.

Additional live-index targets can identify further data pages. Optional
`allow_retired=True` recognizes only the observed `44` low-ID framing on
starting/live-targeted pages. It does not discover unreferenced retired-only
pages, recover records, assign deletion semantics, or reclaim space. Other
pages remain opaque in the full input; they are never presumed free.
No page-header bitmap, linkage, free list or allocation codec is implemented.

Independent synthetic fixtures cover both magic profiles, sorted schema index
versus physical order, empty tables, additional pages, retained rows and
malformed bounds/aliases. Existing native E01/E02/Alarm fixtures provide a
separate framing oracle. Synthetic acceptance does not establish native support.
The original Calendar parser remains unchanged at this checkpoint.

## Operational limits

No native socket, emulator, RAM, guest save, model child or infrastructure
change was used. Requested emulated execution: **0 ms**; actual guest-clock
delta: **not measured**. Full historical private fixture suites require the
unlocated DOSLAB archive. Original commercial/media/private inputs are untouched.

## M2: useful Calendar generation, explicit SDK profile

The default observed-only profile and its adversarial/corpus tests are preserved.
An explicit `profile='sdk'` adds Gregorian-valid dates representable by the
documented byte bias (1980–2138), all seven weekdays, ordinary non-midnight
quarter hours and `31`/`71` Alarm values. The SDK gives the general formulas;
the prior 3.05 static add-path review supports date/weekday biasing. These are
document/source findings, not new application observations. Actual UI year limits
and midnight/blank-time contexts remain unqualified. Reserved time sentinels,
overnight, recurrence, reminders and annual-event generation are excluded.

Rehashed private SDK Development Guide and Calendar 3.05 module match
[source identities](sdk-source-identities.md); hashes and output receipt are in
[campaign metadata](../evidence/database-campaign.json).

Reproduce from a source checkout with `PYTHONPATH=src`:

```sh
python tools/generate_calendar_sample.py tests/fixtures/application-generated/calendar/e02-86box-historical-match.cln NEW-OUTPUT.cln
python -m deskmate_formats.calendar.cli NEW-OUTPUT.cln --profile sdk --json
```

Result: **29 appointments across October 23–November 5, 2026 (14 days)**,
28 new occurrences plus the original LPHa124. 6,144 bytes, 278 row bytes free,
133 index slots free. SHA-256
`85ad05d6bf58540e32349bbb559301d36aced164741b03b09b30d63f22d636ac`.
Insertion is reverse chronological; indexes are chronological with no tied
starts. Original row bytes/IDs/addresses, header and schema pages are unchanged.
Raw LE16 slot walks, bounded delimiter scans, literal vectors, weekday checks,
source preservation and index uniqueness provide independent offline controls.
The durable private archive retains the actual output and receipt; generated
bytes are not mislabeled as application-generated Git fixtures.

The 30-day/60-addition attempt fails before publication at the page-capacity
guard. No partial output is published. Additional-page reading succeeds on
independently assembled page-6 targets; writers reject multipage/retired layouts.
E15's four allocation-associated header changes and E19's five differ; neither
supports a general bitmap/free-list interpretation. Allocation remains blocked.

Local offline common-reader checks additionally read the published-hash empty
ADR (27/0/15/1 rows) and CARMAINT sample (28/22/4/0 rows). CARMAINT SHA-256
`ca5ea9d77dc7545e761457ddc9d40c0b5aca427d7f787a19038d61495f4c67e7`.
INVNTORY (`62316203c555e42cddc47b118f4a34ef1c60362e684d2b90a978fb3675d9c6fe`)
fails explicitly: its schema row at 0x0898 has five stored values, not six.
Missing trailing-field/default semantics remain unsupported; no padding is
invented. These private inputs remain outside Git and unchanged.

M2 checks: 42 Calendar-focused tests and 37 adversarial parser tests passed;
Ruff, REUSE, repository audit and whitespace checks passed. No generated output
was opened or saved in DeskMate. The full-month target is not achieved.

M1 validation: baseline 284 portable tests passed (130.787 s); six new structural
tests passed (0.019 s); Ruff, REUSE and repository audit passed. Commands use
`PYTHONPATH=src`: `python -m unittest discover -s tests/portable -v`, focused
`-p test_database.py`, `python -m ruff check src tests/portable tools`,
`python -m reuse lint`, `python tools/audit_repository.py`, `git diff --check`.
