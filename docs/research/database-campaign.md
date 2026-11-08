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

M1 validation: baseline 284 portable tests passed (130.787 s); six new structural
tests passed (0.019 s); Ruff, REUSE and repository audit passed. Commands use
`PYTHONPATH=src`: `python -m unittest discover -s tests/portable -v`, focused
`-p test_database.py`, `python -m ruff check src tests/portable tools`,
`python -m reuse lint`, `python tools/audit_repository.py`, `git diff --check`.
