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

The 30-day/60-addition attempt succeeds for 39 additions (40 total appointments)
then fails before publication at the page-capacity
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

## M3: Address Book checkpoint

See [reader/writer, exact-hash controls and multicontact gate](addressbook-codec.md).
Eight portable tests and two focused private oracle tests passed. All four
published native hashes match. Twenty-five fictional contacts were generated in
25 separate files; multicontact and preferred 50–100-contact book targets remain
unmet. No optional field meanings or index sorting rules were invented.

## M4: compatibility assessment

`tools/validate_database_campaign.py` imports no production parser/writer. It
independently scans physical row framing, LE16 index slots, count/next-ID values
for these fixed experimental profiles, weekday correspondence and chronological
uniqueness. It checks all source rows/unknown-byte preservation and all 25 ADR
contacts against their receipts. All checks passed. Six altered Calendar outputs
(header, original row, page pointer, offset, index tail and count) were rejected.
The script is an experiment checker, not another supported general database API.
Checker hash and derived counts are in [campaign metadata](../evidence/database-campaign.json).

| Claim | Evidence class / confidence | Limit |
| --- | --- | --- |
| Common directory/schema/index/framing | Existing actual Calendar fixtures and local original-byte ADR/CARMAINT reads; high within declared profile | INVNTORY omitted trailing schema value rejected |
| Ordinary general date/weekday codec | Prior pinned SDK and 3.05 static findings, literal-vector and Gregorian boundary tests | New combinations and representable year bounds not UI-qualified |
| Ordinary quarter hours | SDK bitfields; six historical runtime values; new independent literal/offline tests | Midnight/blank/sentinel contexts excluded |
| 29-event / 14-day Calendar | Tool-generated and independently checked offline, source rows/header/schema preserved | No native open/navigation/save |
| Address Book empty-to-one | Four exact independently published whole-file native hash matches; high byte confidence | Newly generated reconstructions, not recovered historical originals |
| 25 varied contacts | 25 separate one-contact generated files, raw values and unknown bytes checked | No native 25-contact book or multiple-contact insertion policy |
| Additional-page/retired reading | Published E15–E19 structures plus independent synthetic page-6/retired controls | Original E15–E19 files unavailable; opaque retired-only pages not discovered |
| Allocation-header semantics | Unresolved | No bitmap/free-list algorithm or writer growth claimed |

The incomplete 30-day attempt is also preserved: 39 additions, **40 total events**,
21 distinct dates, 12 row bytes free. SHA-256
`c59b898ab28b6e958c52a2d69ac658da702cf8636a1a4fbd586902104914e6f6`.
It is a reverse-insertion capacity prefix, not a complete 30-day schedule. The
independent checker also accepted its structural postconditions.

New native validation remains **NOT RUN**. A separately authorized Calendar
trial should use an identified disposable clone and pinned generated-file hash,
verify all fourteen dates/morning/afternoon values through the authenticated socket,
then preserve before/after manifests across one explicitly identified controlled
save. A no-op OK cannot prove a backend write occurred. Any actual edit must be
specified beforehand and compared for logical preservation even if IDs relocate.
Alarm storage is covered; alarm delivery is not. Address Book's smallest second
contact discriminant is in its [codec report](addressbook-codec.md).
No uncertain guest action may be replayed, and no existing emulator ownership is
assumed. No exact-stop runtime backend trace or new RAM inspection was attempted.

## M5: interoperability-facing API

`deskmate_formats.interchange` supplies version-1 semantic JSON envelopes,
CalendarItem/ContactItem data objects, strict import validation and explicit
ConversionIssue loss reports. Seven focused tests passed, including versioned
examples with 29 events and 25 contacts, strict unknown-property/type rejection,
snapshot IDs, supported semantic round trips and rejection/reporting of opaque
field loss. The [contract](../interoperability.md) separates implemented APIs
from future CalDAV/CardDAV work and corrects the stale E15 roadmap statement.
No recurrence, timezone, text normalization or external UID is invented.
Native snapshots remain the preservation unit; native edit/delete and full
byte-preserving JSON reconstruction remain unsupported.

## Final validation and preservation

- Complete portable suite: **313 passed**, 125.563 seconds, using `PYTHONPATH=src`.
- Focused private Address Book oracle: **2 passed**, 0.060 seconds, with an
  explicitly selected hash-pinned empty source. No full historical private suite.
- Ruff passed for source, portable tests, tools and the new private oracle test.
- REUSE passed: **274/274** authored files covered. Repository/archive audit:
  **555** source files, three unchanged application-generated fixtures and four
  unchanged synthetic JSONL fixtures; wheel/source archive checks passed.
- `python -m build` built the wheel and source distribution. An isolated
  `python -I` wheel-only import/generation smoke check reproduced the 14-day
  Calendar hash and A01 native hash, checked CLI targets and source examples.
- Updated Markdown relative links/fences and `git diff --check` passed.

The initial non-isolated build failed because host setuptools was absent; the
standard disposable build backend environment succeeded without changing host
dependencies. Early REUSE/audit checks exposed an untracked log/cache and a
Windows text-encoding/newline issue; these were corrected before successful
checks/commits. A private-oracle invocation without its explicit environment
skipped; the subsequent explicit-baseline run above executed both tests.

Actual generated files, receipts, independent positive/negative checks, tool/source
snapshots, hashes and validation logs are durably retained in the private campaign
archive. The public [evidence metadata](../evidence/database-campaign.json)
contains only non-sensitive hashes/counts/synthetic values. Original commercial
inputs, public native fixtures and historical private evidence are unchanged.
