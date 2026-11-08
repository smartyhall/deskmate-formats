# Practical database compatibility: Phase II

Started 2026-11-07 (America/New_York), clean checkout of fetched `origin/main`
`6c742800f88a63551cb5cd5ba9dc9991bc9a7ead`; branch
`codex/database-phase-ii`, [draft PR #73](https://github.com/smartyhall/deskmate-formats/pull/73).
The previous campaign branch and two other worktrees were preserved. Remote
open-PR inventory was empty before creating this draft; issues #69–#71 were open.
Machine: existing Windows lab, Python **3.13.17**; `PYTHONPATH=src`. No host
dependencies, guest files, configuration or NVRAM were changed.

## Completed evidence reconciliation

The [operator report](calendar-14-days-operator-report.md) establishes successful
operator-reported display of all 29 appointments / 14 dates and alarm states in
DeskMate 3.05. The published 6,144-byte candidate and E02 source remain byte-exact.
Current status, compatibility, interchange and fixture provenance were updated;
historical reports/receipts remain unchanged. Issue #69 records the milestone
but stays open for independently hash-pinned loaded identity and controlled-save
persistence. No alarm-firing result or native rewrite specimen was supplied.

## Address Book: source findings and available evidence

The private empty ADR preserved by the SDK dialog-portability experiment was
rehash-verified: **10,240 bytes**,
`cb890e6d7ba96fafb5a5d3991e208f4de862bee485f6ce32696e989c97d3394c`.
The two focused private writer tests execute against it; generated A01–A04 still
match all four published native hashes. Original A01–A04 archives remain
unlocated. Existing reconstructions are **tool-generated**, even when hashes
match. No new multicontact application-produced evidence appears in issue #70.

Rehashed SDK inputs match [the source identity record](sdk-source-identities.md):

| Input | SHA-256 | Finding / limit |
| --- | --- | --- |
| Development Guide PDF | `8081d5cd34305982844ab3598ebfbdf8887e7e369d1174a88a7631cba08439e0` | One-based PDF p.477 describes DATA ordering by LastName, then FirstName. SDK 3.03 source finding, not observed 3.05 insertion behavior. |
| DMDB.H | `47c2ff4638d8ab1bcc12aeab3e2dd5b51ccfeef9bbddb1a014912c831df4d5aa` | Names ADD_ROW, DEFINE_INDEX, PACK_TABLE and GET_RECORD_LOCATION operations; does not give an on-disk allocation-header codec. |
| DMDB.INC | `2ea33422d68ab2402ca2b83a1c1f5d7fee80db9c36000a8609d42712ce299a29` | Independently pinned assembler interface; no runtime dispatch trace inferred. |
| 3.05 DMDB.R89 | `799444bb8c04632d261f61498ba269f9352e5528718f2e0a89512bf6ef7b808f` | Static input identity verified; no new allocation routine identified. |
| 3.05 DMDBUPD.RES | `9e77a2081ebb3a9549903f5d337580c65d6e0a3f603185064d4c82e16327cf4f` | Static input identity verified; hash verification alone establishes no storage semantics. |

PDF p.477 also describes version-dependent widths; the observed 3.05 schema,
including Title width 10 and sixteen fields, remains authoritative for this
bounded codec. Last-name ordering is now source-supported, while physical
append policy, IDs/counters and secondary/tied/case ordering still require native
evidence. This run does **not** enable a multicontact writer. The actual generated
sample collection remains **25 separate files with one contact each**.

## Minimal next operator trial: one second contact

**Prepared, not authorized or executed.** A separate scoped grant must identify
the disposable installation, machine/build/ROM/config hashes, owned emulator
PID/creation identity and reset epoch, source file and exactly one insertion/save.
Use a visible 86Box window; control exclusively via the authenticated loopback
socket. No Computer Use, host input, RAM capture or uncertain mutation replay.

1. Select a fresh disposable A01 installation, with existing First `TEST`, Last
   `USER A`, City blank, Work Phone `202-555-0142`. Verify PERSONAL.ADR SHA-256
   `19215ea147c65b259eb963fd240e9931d96e77f92d1001f0f7edf89024076ac8`.
   If using a byte-identical tool reconstruction, explicitly record that origin;
   do not claim recovery of original A01. Preserve the full before installed-tree
   manifest, exact ADR bytes, config/NVRAM backup and protected-media hashes.
2. Open Address Book and confirm exactly the existing contact. Use Address → Add
   once. Verify actual inline-field focus before each input; enter First `ZULU`,
   Last `ALPHA`, City blank, Work Phone `555-0100`, all other user fields blank.
   Preserve private screenshots covering all values before the sole save.
3. Use the previously observed Escape/Yes save-and-exit path only when the actual
   prompt and selected answer are verified. One confirmed submission only. If
   acknowledgement is ambiguous, stop and reconcile; never repeat the action.
4. Preserve the immediate saved ADR, full after tree and action/socket receipts
   before any optional read-only reopen. Report exact requested emulated time
   and actual guest-clock delta, or explicitly unknown. Reopening requires scope
   in that trial's grant; no further save or corrective edit is implied.
5. Run the offline diagnostic on **copies** of complete before/after ADR files:

   ```powershell
   python tools/experimental/database_trial_report.py addressbook BEFORE.adr AFTER.adr > NEW-PRIVATE-REPORT.json
   ```

   Use a new private receipt path and retain SHA-256 of input files, report and
   diagnostic source. The tool reads at most 65,537 bytes per input and writes
   only stdout. JSON success means a structural report was produced, **not**
   that all trial predicates passed or native acceptance was established.
   Require `before_is_published_A01`, inspect **every** `trial_checks` value,
   including an empty `unrelated_changed_offsets` list, and review raw deltas.
   Keep full raw reports private until synthetic-content/provenance review.

Predeclared **predictions, not observed results**:

| Feature | Bounded append hypothesis | Discriminating / rejection result |
| --- | --- | --- |
| Old row | ID 0x10, address 0x1000, all 61 bytes unchanged | Relocation/rewrite invalidates this append profile; analyze, do not force-fit. |
| New row | ID 0x11, sixteen fields/defaults, 56 bytes at 0x103D..0x1074; marker 03 at 0x1075 | A different frame, ID, location or default needs new analysis. |
| Index | LastName hypothesis: `(4,61,17)` then `(4,0,16)`; raw `04 00 3D 00 11 00 04 00 00 00 10 00` | Old then new is consistent with either first-name or insertion order for this pair; those two are **not distinguished** by this trial. |
| Counters | DATA count `00001→00002`; next-ID candidate `00017→00018`; opaque `000` unchanged | Different values reject the predicted counter profile. |
| Preservation | 10,240 bytes; header, schema, NAMES/CONFIG, old row and other 125 installed files unchanged | Any additional change is retained and explained before implementing a writer. |

Only row framing, count/next-ID tokens and DATA index changes predicted above
are allowed by the diagnostic's narrow preservation comparison. It separately
reports exact fixed-offset deltas and full page hashes. One successful pair still
does not qualify arbitrary secondary ordering, ties/collation or 20–30-contact
capacity. No independently opened multicontact book is claimed.

## Calendar growth: evidence recovered from reports, not original bytes

`DOSLAB_ROOT` is unset. The existing lab's private-evidence/baseline inventories,
documented campaign archive and its provenance identify no original
`EXPERIMENTS/PHASE2/E15_data_page_boundary` or `E19_space_pressure` archive.
The old campaign likewise records them as unlocated. No whole-disk search,
guessed archive root or regeneration substituted for originals. Only documented
paths/identifiers were used. When the operator supplies the preserved DOSLAB
root, the exact expected paths are:

- E15: `EXPERIMENTS/PHASE2/E15_data_page_boundary/pre_after/files/DESKMATE/PERSONAL.CLN`
  and `after/files/DESKMATE/PERSONAL.CLN` under that experiment.
- E19: `EXPERIMENTS/PHASE2/E19_space_pressure/segment12/after/files/DESKMATE/PERSONAL.CLN`
  and `segment13/after/files/DESKMATE/PERSONAL.CLN` under that experiment.

The diagnostic embeds published whole-file hash pairs and header deltas from
[E15](../experiments/e15-page-boundary.md) and
[E19](../experiments/e19-space-pressure.md), independently checked against their
existing private regression oracles. It reports hash matches explicitly; a
matching synthetic delta cannot authenticate a missing original.

| Offset | E15 published crossing | E19 published crossing |
| --- | --- | --- |
| 0x0026 | FF→00 | unchanged |
| 0x0027 | 8F→6F | unchanged |
| 0x0029 | unchanged | FF→00 |
| 0x002A | F0→8F | 8F→7F |
| 0x002B | 00→FF | FF→F8 |
| 0x002C | unchanged | 00→FF |
| 0x002D | unchanged | 00→F0 |

E15: 6→7 pages, new `(6,0,0x21)` target at index 0x1482, 24-byte BOUND12
row at 0x1800 and marker 0x1818. Old data page 4/schema pages remain unchanged;
count 17→18 and next candidate 33→34. E19: 7→8 pages, new `(7,0,0x2E)` target
at 0x14CA, 77-byte P1913 row at 0x1C00 and marker 0x1C4D. Old pages 4/6,
including retired BOUND12 and twelve appended rows, remain unchanged; count
29→30 and next candidate 46→47. Both preserve old indexed rows/locations and
relative index order. **These are published historical observations**, not new
original-byte measurements in this run.

The fifth E19 header-byte change disproves treating E15's four changed offsets
as a universal update footprint. Neither transition specifies bitmap, free-list,
linkage, page-reuse or checksum semantics. SDK interface names and shared DMDB
call thunks do not resolve that gap. No multipage writer or new full-month
candidate is defensible from this evidence alone.

When original files are available, run each comparison without guest execution:

```powershell
python tools/experimental/database_trial_report.py e15 E15-BEFORE.cln E15-AFTER.cln > NEW-PRIVATE-E15.json
python tools/experimental/database_trial_report.py e19 E19-BEFORE.cln E19-AFTER.cln > NEW-PRIVATE-E19.json
```

Review every published-observation predicate, every delta and all unchanged
pages; preserve complete inputs and hashes. The raw walker inspects starting
and live-index-targeted pages, including observed retired framing. Unreferenced
pages remain opaque; it is not retired-row recovery or a general schema validator.
Passing checks reproduces a **specific transition**, not an allocator.

## Offline deliverables and observation limits

Seven new portable tests independently assemble both Address Book order
possibilities, E15/E19-shaped synthetic growth and malformed/adversarial inputs.
They detect altered old/retired bytes, unexpected counters/fields/header bytes,
bad pointers/aliases/duplicate targets, missing sentinels and oversize inputs.
Synthetic inputs intentionally fail original whole-file hash predicates.
An independent raw-field/SDK-bitfield walk additionally compares **every**
committed Calendar item (including IDs, weekday, times, description and Alarm)
to the version-1 expected JSON. No production parser/writer is used by the
diagnostic or this semantic check. Existing source-byte preservation checks
remain in place; no duplicate general checker or native writer was added.

No emulator launch/connection, keyboard input, RAM capture, guest save or
installed-file replacement occurred. Requested emulated execution: **0 ms**;
actual guest-clock delta **not measured**. Native inspection elapsed time from
the operator report is **unknown**. The future sync rounding and external-time
precision-preservation policy remains unchanged and unimplemented.

Validation counts and durable artifact hashes are recorded in the accompanying
[Phase II evidence receipt](../evidence/database-phase-ii.json). The single
highest-value next operator action is the separately authorized **A01→two-contact
trial above**, returning complete before/after bytes and installation manifests.
