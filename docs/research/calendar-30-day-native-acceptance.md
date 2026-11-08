# 30-day Calendar: proposed native acceptance trial

Prepared 2026-11-07 (America/New_York). **Tool-generated, independently checked
offline; not application-generated or native-accepted.** This runbook prepares a
future operator trial; it grants no emulator, guest-media or save authorization.
Obtain separate authorization identifying the disposable environment and scope.

## Download and identify the actual file

[Download the complete 8,192-byte Calendar binary](https://raw.githubusercontent.com/smartyhall/deskmate-formats/e9ca441a2adaf260239cf50d3deae07c65a90dbc/tests/fixtures/application-generated/calendar/sdk-30-days-allocator-tool-generated.cln)
and save it as **PERSONAL.CLN**, not an HTML page or PERSONAL.CLN.txt. The
[GitHub file view](https://github.com/smartyhall/deskmate-formats/blob/e9ca441a2adaf260239cf50d3deae07c65a90dbc/tests/fixtures/application-generated/calendar/sdk-30-days-allocator-tool-generated.cln)
also offers Download raw file. Verify **before** installing:

```powershell
(Get-Item -LiteralPath .\PERSONAL.CLN).Length
(Get-FileHash -LiteralPath .\PERSONAL.CLN -Algorithm SHA256).Hash.ToLowerInvariant()
```

Expected size: **8192**. Expected SHA-256:
`d35b10c8e8f0b04e41cd6d16a27b9825531353b00ab503e94b7abd3a11499106`.
Stop if either differs. Repository filename:
`sdk-30-days-allocator-tool-generated.cln`.

Source: unchanged committed
[E02](../../tests/fixtures/application-generated/calendar/e02-86box-historical-match.cln),
6,144 bytes, SHA-256
`0af0896163c24c992fa515ddca8c45a31496250d6ba84c9f08e28020a07fe0d9`.
The merged PR #75 experimental builder at
`32a099e09504bfca1c668b253d325f4e6f54109e` added 60 invented appointments to
E02's LPHa124. Regeneration and the preserved `dmdb-allocator-20261107` binary
agree byte for byte; the independent checker passes. Full source findings remain
in the [historical allocator report](dmdb-page-allocator.md); this publication
receipt is [separate](../evidence/calendar-30-day-publication.json).

## Install only in a disposable environment

1. Identify a newly cloned, disposable DeskMate **03.05.00** installation. Record
   emulator/build revision and executable hash, DOS version, machine/CPU/memory,
   ROM hashes, config/NVRAM hashes, media identity and date/time. Preserve originals
   and config/NVRAM backups outside Git. Never use an existing personal database.
2. After the environment is safely stopped and ownership is confirmed, retain the
   disposable installation's original PERSONAL.CLN and a complete installed-file
   manifest (paths, sizes, SHA-256) privately. Copy the download into that clone's
   DeskMate data directory as PERSONAL.CLN. Do not overwrite the source environment
   or another person's active session. Re-extract/re-hash the installed file before
   launch; it must match the download. Capture an **after-install/before-open**
   manifest and candidate snapshot. No disk formatting is needed.
3. For an authorized automated 86Box trial, use a visible window and control only
   through its authenticated loopback socket. Pin PID/creation identity and reset
   epoch; keep credentials private. No display clicks, host keyboard/mouse injection
   or Computer Use. An operator may instead perform their own manual trial and
   clearly label it operator-reported evidence. Do not launch/control anything
   merely because this runbook exists.

## Read/display checklist: all 30 dates

Open Calendar, navigate to October/November **2026**, and inspect every date below
in day view. Compare both events' complete descriptions, start/end times and
**displayed** alarm states; inspect the event detail view where necessary without
confirming a change. October 23 also contains **09:00–10:00 LPHa124, alarm off,
ID 17, page 4** (the original E02 event). There are three appointments that date
and two on each remaining date: **61 total**, no missing/duplicate rows. Overlap
on October 23 is intentional. Times are 24-hour local wall time; e.g. 14:15 is
2:15 PM. Global Alarm Off does not change the expected per-event checkbox.

In each cell: time range; description; alarm; `record ID/page`. IDs and pages are
offline locations, not necessarily labels displayed by DeskMate. Mark each date
pass/fail, and retain private screenshots/detail observations for both page
transitions: **November 10→11 (page 6→4)** and **October 29→30 (page 7→6)**.
The October 23 E02 event also proves an original page-4 row was reached.

| Date | Morning appointment | Afternoon appointment |
| --- | --- | --- |
| 2026-10-23 | 09:30–10:15; Plan 01 / allocator trial; off; `77/7` | 14:15–15:15; Review 01 / allocator trial; on; `76/7` |
| 2026-10-24 | 09:45–10:30; Plan 02 / allocator trial; off; `75/7` | 14:30–15:30; Call 02 / allocator trial; off; `74/7` |
| 2026-10-25 | 10:00–10:45; Plan 03 / allocator trial; off; `73/7` | 14:45–15:45; Read 03 / allocator trial; off; `72/7` |
| 2026-10-26 | 09:30–10:15; Plan 04 / allocator trial; off; `71/7` | 15:00–16:00; Review 04 / allocator trial; off; `70/7` |
| 2026-10-27 | 09:45–10:30; Plan 05 / allocator trial; off; `69/7` | 14:15–15:15; Call 05 / allocator trial; off; `68/7` |
| 2026-10-28 | 10:00–10:45; Plan 06 / allocator trial; off; `67/7` | 14:30–15:30; Read 06 / allocator trial; on; `66/7` |
| 2026-10-29 | 09:30–10:15; Plan 07 / allocator trial; off; `65/7` | 14:45–15:45; Review 07 / allocator trial; off; `64/7` |
| 2026-10-30 | 09:45–10:30; Plan 08 / allocator trial; off; `63/6` | 15:00–16:00; Call 08 / allocator trial; off; `62/6` |
| 2026-10-31 | 10:00–10:45; Plan 09 / allocator trial; off; `61/6` | 14:15–15:15; Read 09 / allocator trial; off; `60/6` |
| 2026-11-01 | 09:30–10:15; Plan 10 / allocator trial; off; `59/6` | 14:30–15:30; Review 10 / allocator trial; off; `58/6` |
| 2026-11-02 | 09:45–10:30; Plan 11 / allocator trial; off; `57/6` | 14:45–15:45; Call 11 / allocator trial; on; `56/6` |
| 2026-11-03 | 10:00–10:45; Plan 12 / allocator trial; off; `55/6` | 15:00–16:00; Read 12 / allocator trial; off; `54/6` |
| 2026-11-04 | 09:30–10:15; Plan 13 / allocator trial; off; `53/6` | 14:15–15:15; Review 13 / allocator trial; off; `52/6` |
| 2026-11-05 | 09:45–10:30; Plan 14 / allocator trial; off; `51/6` | 14:30–15:30; Call 14 / allocator trial; off; `50/6` |
| 2026-11-06 | 10:00–10:45; Plan 15 / allocator trial; off; `49/6` | 14:45–15:45; Read 15 / allocator trial; off; `48/6` |
| 2026-11-07 | 09:30–10:15; Plan 16 / allocator trial; off; `47/6` | 15:00–16:00; Review 16 / allocator trial; on; `46/6` |
| 2026-11-08 | 09:45–10:30; Plan 17 / allocator trial; off; `45/6` | 14:15–15:15; Call 17 / allocator trial; off; `44/6` |
| 2026-11-09 | 10:00–10:45; Plan 18 / allocator trial; off; `43/6` | 14:30–15:30; Read 18 / allocator trial; off; `42/6` |
| 2026-11-10 | 09:30–10:15; Plan 19 / allocator trial; off; `41/6` | 14:45–15:45; Review 19 / allocator trial; off; `40/6` |
| 2026-11-11 | 09:45–10:30; Plan 20 / allocator trial; off; `39/4` | 15:00–16:00; Call 20 / allocator trial; off; `38/4` |
| 2026-11-12 | 10:00–10:45; Plan 21 / allocator trial; off; `37/4` | 14:15–15:15; Read 21 / allocator trial; on; `36/4` |
| 2026-11-13 | 09:30–10:15; Plan 22 / allocator trial; off; `35/4` | 14:30–15:30; Review 22 / allocator trial; off; `34/4` |
| 2026-11-14 | 09:45–10:30; Plan 23 / allocator trial; off; `33/4` | 14:45–15:45; Call 23 / allocator trial; off; `32/4` |
| 2026-11-15 | 10:00–10:45; Plan 24 / allocator trial; off; `31/4` | 15:00–16:00; Read 24 / allocator trial; off; `30/4` |
| 2026-11-16 | 09:30–10:15; Plan 25 / allocator trial; off; `29/4` | 14:15–15:15; Review 25 / allocator trial; off; `28/4` |
| 2026-11-17 | 09:45–10:30; Plan 26 / allocator trial; off; `27/4` | 14:30–15:30; Call 26 / allocator trial; on; `26/4` |
| 2026-11-18 | 10:00–10:45; Plan 27 / allocator trial; off; `25/4` | 14:45–15:45; Read 27 / allocator trial; off; `24/4` |
| 2026-11-19 | 09:30–10:15; Plan 28 / allocator trial; off; `23/4` | 15:00–16:00; Review 28 / allocator trial; off; `22/4` |
| 2026-11-20 | 09:45–10:30; Plan 29 / allocator trial; off; `21/4` | 14:15–15:15; Call 29 / allocator trial; off; `20/4` |
| 2026-11-21 | 10:00–10:45; Plan 30 / allocator trial; off; `19/4` | 14:30–15:30; Read 30 / allocator trial; off; `18/4` |

The [machine-readable expected listing](../../tests/fixtures/application-generated/calendar/sdk-30-days-allocator-tool-generated.expected.json)
contains all 61 appointments, numeric IDs, page and file offsets, row lengths and
index offsets, plus physical insertion order and page usage. Specifically,
page 4 has 24 indexed rows including the control row (IDs 16–39), page 6 has
24 (40–63), and page 7 has 14 (64–77). There are 62 index entries, data chain
4→6→7, eight database pages. The control row is not an appointment.

Do not edit, toggle alarm controls, acknowledge an update/save dialog or accept
an uncertain prompt during this phase. If inspection requires an unplanned
mutation, stop and record the blocker. After an authorized exit, preserve the
complete CLN and **after-open** installation manifest. Compare against the
before-open snapshot, even if no save was requested: preserve any automatic
changes as observations. Record host elapsed time and exact requested emulated
milliseconds plus observed guest-clock delta (or explicitly unknown).

A successful hash-pinned open/display establishes native read compatibility
only for the observed candidate and inspected fields. It does not establish
edit/save persistence, alarm firing, arbitrary page growth or a general allocator.
If loaded-file identity cannot be independently checked, label the result
operator-reported native display and record that limitation.

## Optional, separately authorized one-edit/save persistence trial

Predeclare this scope before starting, on a **fresh disposable copy of the pinned
candidate**, separate from the display trial. Change only October 23, 2026,
09:30–10:15, **Plan 01 / allocator trial** (original ID 77, page 7, offset 552)
to **Plan 01 / allocator saved**. Keep date, times and alarm **off** unchanged.
This same-length description change tests an actual rewrite; no-op OK is
insufficient. Authorize exactly one edit/confirmed save, exit and read-only
reopen. Do not replay an ambiguous save; retain the state and investigate.

Before editing, preserve exact CLN bytes, installed-tree manifest, configuration
and screenshot of the selected event. After the single confirmed native save and
exit, preserve complete **AFTER-SAVE.CLN**, a new tree manifest, action ledger,
selected-field screenshots and timing records before reopening. Hash both CLNs.
Reopen without another save and verify the changed description persists and all
other 60 appointments, times and alarm states still match the listing.

Use the existing read-only diagnostic on host copies to retain every byte delta,
page hash, index target, live/retired row and descriptor change; no new diagnostic
is needed. From the repository root (NEW-PRIVATE-REPORT.json must be a new private
path):

```powershell
python -c "import sys,json; from pathlib import Path; from tools.experimental.database_trial_report import compare; paths=[Path(p) for p in sys.argv[1:]]; data=[p.open('rb').read(65537) for p in paths]; print(json.dumps(compare(*data,'PERSONAL'),indent=2))" BEFORE.CLN AFTER-SAVE.CLN > NEW-PRIVATE-REPORT.json
python -m deskmate_formats.calendar.cli --json --profile sdk AFTER-SAVE.CLN > NEW-PRIVATE-PARSED.json
```

The before file must match the published hash; the after hash must differ for
this edit. Review decoded semantics against the expected listing with just the
one declared description substitution. Investigate any missing/extra events,
changed date/time/alarm, count/index inconsistency, unexpected page growth,
header/schema changes or unrelated installed-file changes. IDs/row locations
may change during a native edit; preserve and explain the raw deltas rather than
requiring the offline builder's IDs to remain fixed. Diagnostic/parser success
alone does not prove the trial passed. If a bounded diagnostic rejects the save,
retain the full original files and error; do not normalize or repair evidence.

## Return observations and saved-file evidence

Report to [issue #71](https://github.com/smartyhall/deskmate-formats/issues/71):
trial scope (display or edit/save), downloaded/installed/before/after hashes and
sizes, DeskMate version and machine summary, all 30 date outcomes, page-4/6/7
anchors, exact discrepancies, alarm **display** results, timing and limitations.
Keep display and persistence outcomes separate. Provide a durable private
archive identifier for full before/after CLNs, manifests, screenshots, socket
receipts if applicable and diagnostics; do not post full installed trees, media,
ROMs, credentials or private paths. Publish eligible synthetic saved CLNs only
after provenance/rights review, with a manifest, hashes and REUSE sidecar. Do not
replace the original candidate. Never include a real personal database.

## Offline reproduction from a fresh source checkout

Set `PYTHONPATH=src` and use fresh output names. These commands need only Python
and the Git checkout, with no ROMs, commercial executables or live emulator:

```powershell
$env:PYTHONPATH='src'
python tools/experimental/generate_calendar_month.py tests/fixtures/application-generated/calendar/e02-86box-historical-match.cln NEW-MONTH.cln --experimental-new-pages > NEW-MONTH.json
python tools/experimental/check_calendar_multipage.py tests/fixtures/application-generated/calendar/e02-86box-historical-match.cln tests/fixtures/application-generated/calendar/sdk-30-days-allocator-tool-generated.cln tests/fixtures/application-generated/calendar/sdk-30-days-allocator-tool-generated.expected.json
python -m unittest discover -s tests/portable -p test_calendar_multipage.py -v
```

The binary fixtures are Git-only and are deliberately excluded from wheels and
sdists; download/clone this branch or its containing revision to obtain them.
