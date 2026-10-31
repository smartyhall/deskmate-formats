> Laboratory specification snapshot, 2026-10-31. Relative evidence paths refer to the private DOSLAB archive, not files shipped here. Historical checkpoint statements are retained; see compatibility.md for current staged capabilities.

# DeskMate 3.05 Calendar: initial PERSONAL.CLN specification

Validated through E14 on 2026-10-31 against the preserved fixtures. This is an evidence-based description of these fixtures. The initial read-only parser below supports an explicit subset; no general decoder or writer is claimed. Absolute offsets are zero-based. **Confirmed** means directly observed or reproduced; **probable** means a structural interpretation supported by repeated examples; **speculative** means an untested semantic explanation.

## Evidence and provenance

All paths below are relative to DOSLAB. Each experiment preserves a complete 126-file installed tree, a manifest with SHA-256 hashes, and action metadata. Calendar was exited cleanly to the DOS prompt before collection. No originals or functioning installation files were edited.

| Experiment | PERSONAL.CLN location | Observed appointment |
|---|---|---|
| E00 | `EXPERIMENTS/PHASE2/E00_default/files/DESKMATE/PERSONAL.CLN` | Default, no user appointment; an existing internal row is present |
| E01 | `EXPERIMENTS/PHASE2/E01_one_event/files/DESKMATE/PERSONAL.CLN` | 2026-10-23, 09:00–10:00 AM, `LPHa123`, alarm off |
| E02 | `EXPERIMENTS/PHASE2/E02_description_change/files/DESKMATE/PERSONAL.CLN` | Same values, description `LPHa124` |
| E03 | `EXPERIMENTS/PHASE2/E03_start_0915/files/DESKMATE/PERSONAL.CLN` | 2026-10-23, **09:15–10:00 AM**, `LPHa124`, alarm off |
| E04 | `EXPERIMENTS/PHASE2/E04_end_1015/files/DESKMATE/PERSONAL.CLN` | 2026-10-23, **09:15–10:15 AM**, `LPHa124`, alarm off |
| E05 | `EXPERIMENTS/PHASE2/E05_date_20261024/files/DESKMATE/PERSONAL.CLN` | **2026-10-24**, 09:15–10:15 AM, `LPHa124`, alarm off; October 23 verified empty |
| E06 | `EXPERIMENTS/PHASE2/E06_date_20261101/files/DESKMATE/PERSONAL.CLN` | **2026-11-01**, 09:15–10:15 AM, `LPHa124`, alarm off; October 24 verified empty |
| E07 | `EXPERIMENTS/PHASE2/E07_date_20271101/files/DESKMATE/PERSONAL.CLN` | **2027-11-01**, 09:15–10:15 AM, `LPHa124`, alarm off; November 1, 2026 verified empty |
| E08 | `EXPERIMENTS/PHASE2/E08_two_events/files/DESKMATE/PERSONAL.CLN` | **Two appointments on 2027-11-01:** unchanged `LPHa124` 09:15–10:15 AM; exact `BETA456` 11:00 AM–12:00 PM, alarm off |
| E09 | `EXPERIMENTS/PHASE2/E09_delete_beta456/files/DESKMATE/PERSONAL.CLN` | Deleted only BETA456; **LPHa124, 2027-11-01, 09:15–10:15 AM** remains. File contents exactly equal E07 |
| E10 | `EXPERIMENTS/PHASE2/E10_reuse_gamma45/files/DESKMATE/PERSONAL.CLN` | Added exact **GAMMA45, 2027-11-01, 11:00 AM–12:00 PM, alarm off**; LPHa124 unchanged; ID/address/index slot reused |
| E11 | `EXPERIMENTS/PHASE2/E11_description_growth/files/DESKMATE/PERSONAL.CLN` | **LPHa124XYZ**09:15–10:15AM and GAMMA45 11AM–noon,2027-11-01; both logical events relocate/reassign IDs; counters unchanged |
| E12 | `EXPERIMENTS/PHASE2/E12_delete_gamma45/files/DESKMATE/PERSONAL.CLN` | Deleted physically interior GAMMA45; LPHa124XYZ unchanged, compacted to1027 and reassigned ID11; counters decrement, tail cleared |
| E13 | `EXPERIMENTS/PHASE2/E13_description_shrink/files/DESKMATE/PERSONAL.CLN` | Shrunk LPHa124XYZ→LPHa124; ID/address/index stable,27→24bytes, exact E07/E09 database and126-file-content restoration |
| E14 | `EXPERIMENTS/PHASE2/E14_interior_shrink/files/DESKMATE/PERSONAL.CLN` | Branch from E11; GAMMA45→GAMM24→21bytes at1027/ID11; unchanged LPHa row shifts103F→103C,ID12 stable; counters unchanged |

Every file is 6,144 bytes. SHA-256:

```text
E00 c556b7f57102fc5432ce926317c8c0aa95cf8992d7fb64a72e2f270e4c517890
E01 5a3ff71dbd9654cc98cbda22e5f42e651c7792419c0c856b4bf0cfc5fa3ab508
E02 0af0896163c24c992fa515ddca8c45a31496250d6ba84c9f08e28020a07fe0d9
E03 9dd6ae28520ef1784ca7ff4ac32d6d6ec783a75e4a1ef5d2ffce42e8245d0e23
E04 3b3af8962ff220534a78dc48086c4e843a0899e84c7dd9ed5c426825a7385e15
E05 bf0f450da5e64d25f407da0b71e7bbc9239f257cb91e2df09b90bd80a4f56e11
E06 d93fdd0cb6d4bb4893dda2fefb2ea6ed117a6780e469e2b047b0a593193ff78d
E07 aac152dcea193fa88e26c1b11b176284ec9959a2c5239f86dad7990e23e9034e
E08 8a11fecd1d4e61266730602a7fda239edfce22870f509bee66a91e021d1913d6
E09 aac152dcea193fa88e26c1b11b176284ec9959a2c5239f86dad7990e23e9034e
E10 853f4340ccb3fc6a144479524d7d1e0b0e5acee5788a6bebc7b6c541bafc07a3
E11 3bca1cd401464a09064692a9173880d0e464b7b5e8559eb3eed912911e6449b1
E12 27aa61ddc40bfaa7685abe88741a368ade44bb8693365c7d0fe0cb2c5d5d3ed0
E13 aac152dcea193fa88e26c1b11b176284ec9959a2c5239f86dad7990e23e9034e
E14 c4521c0f63ecf60b0abe959a03c5f2ceb84cb695fb2e26d656190a0a893ab3fd
```

**Confirmed:** the earlier launch-only B00→E00 experiment changed none of the 126 file contents. Every recorded experiment transition through E14 changed only `DESKMATE/PERSONAL.CLN`; other files' contents were identical. No separate event index, checksum, temporary file, or preference file was observed in these closed-tree comparisons. Transient files created and removed during execution were not traced.

E02 started from an E01 copy verified against all 126 manifest hashes. Enter opened October 23's day schedule; Enter on the selected event opened Change Event. The dialog confirmed the date, normalized 9:00/10:00 AM times and alarm off. End, Backspace, `4` changed only the description input. The complete `LPHa124` was visually verified before Enter saved it; the saved day schedule showed the new label and unchanged times. Escape exited Calendar cleanly. E02 did not edit time; the later E03 time edit is described below.

## Independent report verification

`ANALYSIS/DeskMate_Calendar_Initial_Format_Findings.md` is preserved separately and unchanged. Its E00/E01 hashes, sizes, 30 changed byte positions, six runs, schema literals, record bytes and index arithmetic match the preserved files exactly. Its date/time interpretations and counter semantics remain hypotheses. Its suggested page purposes are supported but do not constitute a universal format specification.

The prediction that E02 might change only the description byte was **not** borne out: one additional byte changed in the pre-existing row. This is new evidence, not an error in the report's E00/E01 comparison.

## File organization

**Confirmed:** bytes `0x0000–0x0003` are `03 46 49 4C` (`.FIL`) in all fixtures. The first byte's semantics and remaining header fields are unknown.

**Probable:** a 1,024-byte page organization. The file divides into six such units; 13 schema index triples and two PERSONAL index triples resolve correctly using `page*1024 + in_page_offset`. Growth, page allocation and multi-page tables have not been tested.

| Candidate page | Absolute range | Observed contents / probable role |
|---:|---|---|
| 0 | `0000–03FF` | `.FIL` header and unknown metadata |
| 1 | `0400–07FF` | Delimited table metadata naming DBCOLS and PERSONAL |
| 2 | `0800–0BFF` | 13 DBCOLS schema rows: six describing DBCOLS, seven describing PERSONAL |
| 3 | `0C00–0FFF` | 13 triples pointing to the page-2 rows |
| 4 | `1000–13FF` | Pre-existing row at `1000`, appended appointment at `1027` |
| 5 | `1400–17FF` | Triples pointing to page-4 rows; first 40 bytes have an unexplained repeating pattern |

E00 is empty **of user appointments**, not physically empty: row prefix `80 10` at `0x1000` and its index entry already exist. This row has an unusual date-like value and a description payload including `@PaSsWoRd@=`. An internal/control or preferences role is probable; its complete semantics are unknown.

## Embedded column definitions

**Confirmed literal structure:** each observed DBCOLS row begins with `80` and a low ID byte, then six `01`-separated values, followed by `01 02`. The first six rows name the metadata columns `cname`, `owner`, `pos`, `len`, `type`, `uniq`. The following seven rows all have owner `PERSONAL` and uniqueness literal `0`.

| Schema row offset | ID | Position | Name | Declared length | Type literal |
|---|---:|---:|---|---:|---|
| `0898` | `16` | 1 | Date | 3 | C |
| `08B3` | `17` | 2 | DayOfWeek | 1 | C |
| `08D3` | `18` | 3 | Duration | 1 | C |
| `08F2` | `19` | 4 | StartTime | 1 | C |
| `0912` | `1A` | 5 | EndTime | 1 | C |
| `0930` | `1B` | 6 | Protected | 1 | C |
| `0950` | `1C` | 7 | Description | 120 | K |

IDs in this table are hexadecimal; positions and lengths are decimal. The meanings of type literals C/N/K, uniqueness constraints and the enforcement of declared lengths have not been tested. In particular, Description is not a fixed 120-byte area in the observed record: its seven ASCII bytes are immediately followed by framing bytes.

## Appointment record and framing

**Confirmed bytes:** the E01 appointment occupies `0x1027–0x103E`; `0x103F` contains `03`. E00 had `03` at `0x1027`, followed by padding. E02 through E07 retain the record at the same address and length.

```text
        prefix  Date     sep DOW sep empty Start sep End sep Prot sep Description          sep end/list
E01:    80 11   8F 6B 78 01  67  01  01    A4  01  A8  01  31  01  4C 50 48 61 31 32 33  01 02 03
offset: 1027    1029          102D          1030     1032     1034     1036                103D
```

| Absolute offset | Relative to `1027` | Observed bytes | Interpretation and confidence |
|---|---:|---|---|
| `1027–1028` | +0 | `80 11` | Confirmed row prefix; index ID is 0011. Dedicated marker vs variable-length ID encoding unresolved |
| `1029–102B` | +2 | E01–E04 `8F 6B 78`, E05 `8F 6B 79`, E06 `8F 6C 62`, E07 `90 6C 62` | Confirmed date field; component formulas supported for tested years/months/days |
| `102C` | +5 | `01` | Probable field separator, repeated throughout schema and data |
| `102D` | +6 | Friday `67`, Saturday `68`, Sunday `62`, Monday `63` | Confirmed tested values; `0x61 + weekday` (Sunday=1) fits, Tuesday–Thursday untested |
| `102E` | +7 | `01` | Separator |
| `102F` | +8 | `01` | Empty Duration field ending here; this is not a measured duration value of 1 |
| `1030` | +9 | E01/E02 `A4`, E03 `A5` | **Confirmed StartTime location:** isolated 09:00→09:15 AM edit changes only this byte |
| `1031` | +10 | `01` | Separator |
| `1032` | +11 | E01–E03 `A8`, E04 `A9` | **Confirmed EndTime location:** isolated 10:00→10:15 AM edit changes only this byte |
| `1033` | +12 | `01` | Separator |
| `1034` | +13 | `31` | Candidate Protected field; literal ASCII `1`, semantic meaning untested |
| `1035` | +14 | `01` | Separator |
| `1036–103C` | +15 | E01 `4C 50 48 61 31 32 33` | **Confirmed** description `LPHa123`; E02 final byte is `34` |
| `103D` | +22 | `01` | Probable final field separator |
| `103E` | +23 | `02` | Probable row terminator; analogous schema rows use it |
| `103F` | +24 | `03` | Probable row-list terminator, displaced from E00's `1027` |

Control-byte escaping, embedded delimiters, longer IDs, long descriptions and record movement are unknown. Do not hardcode these absolute offsets for other databases.

## Index and counters

**Confirmed arithmetic and repeated structure:** little-endian 16-bit triples beginning at index-page offset `0x28` resolve to known row prefixes/IDs in these fixtures.

```text
0x1428: 04 00 00 00 10 00  -> page 4, offset 0000, ID 0010 -> 0x1000
0x142E: 04 00 27 00 11 00  -> page 4, offset 0027, ID 0011 -> 0x1027
```

The second triple is zero in E00 and populated identically in E01 through E07. The analogous 13 triples at `0x0C28` point to every schema row, with matching IDs. Interpreting these as a row index is **probable with strong repeated support**; sorting, deletion, ID reuse and page-header semantics remain untested.

**Confirmed changes in PERSONAL table metadata:** ASCII `00001` at `0x0435–0439` becomes `00002`; ASCII `00017` at `0x043F–0443` becomes `00018`. An allocated/active row count and next-ID counter are probable interpretations. E00 already has one internal row, and E01's new index ID is decimal 17. Deletion is needed to distinguish active from allocated counts. E02 through E07 leave both strings unchanged.

## Exact comparisons and the extra E02 byte

E00→E01 has exactly **30** differing positions in six contiguous runs:

| Offset(s), inclusive | Before → after | Observed role |
|---|---|---|
| `0439` | `31 → 32` | Table metadata string |
| `0443` | `37 → 38` | Table metadata string |
| `1027–103F` | `03` + 24 zero bytes → 25 bytes shown above | Appended appointment and moved list marker |
| `142E` | `00 → 04` | New triple's page low byte |
| `1430` | `00 → 27` | New triple's offset low byte |
| `1432` | `00 → 11` | New triple's ID low byte |

E01→E02 has exactly **two** differing positions in two one-byte runs:

| Offset | E01 → E02 | Confidence |
|---|---|---|
| `103C` | `33 → 34` (`3 → 4`) | **Confirmed** final description character, changed in place |
| `100D` | `63 → 65` (`c → e`) | **Confirmed** raw change in second description-payload byte of existing row ID 10; purpose unknown |

The appointment's other bytes, both index pages, file header, schema, counters and file size are unchanged. No record relocation or separate checksum change is identified. This does **not** prove checksums are absent: the extra byte remains unexplained. A persisted display/view preference is **speculative**, because E01 ended in month view while E02 used day view. An edit-triggered control value is another possibility; these experiments do not isolate the cause.

```text
0x1000 E01: 80 10 20 20 FF 01 01 01 01 01 30 01 69 63 61 61
0x1000 E02: 80 10 20 20 FF 01 01 01 01 01 30 01 69 65 61 61
0x1030 E01: A4 01 A8 01 31 01 4C 50 48 61 31 32 33 01 02 03
0x1030 E02: A4 01 A8 01 31 01 4C 50 48 61 31 32 34 01 02 03
```

## E03: isolated start-time edit

**Procedure:** verified all 126 files of E02, copied them to disposable `EXPERIMENTS/PHASE2/RUN`, and reused the existing DOSBox configuration without changes. Calendar restored the day schedule directly. Enter opened the selected event. Keyboard navigation focused StartTime; End and two Backspaces removed only the minutes `00`, then `1`, `5` entered `15`. Before saving, the Change Event dialog visibly showed **10/23/2026, 9:15 AM, 10:00 AM, LPHa124, alarm off**. Enter saved it; the daily schedule visibly confirmed 9:15 AM–10:00 AM and LPHa124. Escape exited cleanly to the DOS prompt. The full tree and manifest were then preserved under `E03_start_0915`; `E03_input_verification.json` records the verified input.

**Confirmed result:** exactly one byte differs across all 6,144 bytes of PERSONAL.CLN:

| Offset | E02 → E03 | Interpretation |
|---|---|---|
| `1030` (decimal 4144) | `A4 → A5` | StartTime, incremented once for 09:00→09:15 AM |

There are no inserted/removed bytes or file-size changes. The other 125 file contents are identical. Header, schema, table counters, indexes, appointment ID, date, DayOfWeek, empty Duration, EndTime A8, Protected byte and description are unchanged.

The **entire existing internal row `0x1000–0x1026` is identical**, including `0x100D = 65` in both E02 and E03. Thus the extra E02 byte is not a value that must change on every appointment edit. E02 restored day view at E03 startup; E03 also ended in day view. These observations strengthen the saved-view/state explanation for the earlier `63→65` change, but do not prove its exact meaning. No checksum or other metadata byte changed in response to this isolated start-time edit; universal absence of checksums is not established.

```text
0x1000 E02/E03: 80 10 20 20 FF 01 01 01 01 01 30 01 69 65 61 61
0x1030 E02:     A4 01 A8 01 31 01 4C 50 48 61 31 32 34 01 02 03
0x1030 E03:     A5 01 A8 01 31 01 4C 50 48 61 31 32 34 01 02 03
```

The prediction documented before E03 **passed exactly**. Supporting byte-level reports are `ANALYSIS/E02_E03_comparison.json` and `.md`.

## E04: isolated end-time edit

**Procedure:** verified all 126 E03 manifest hashes and copied the tree to disposable RUN; reused the unchanged DOSBox configuration. Calendar opened in day view. Enter opened the event, two Shift+Tabs focused EndTime, and End / Backspace twice / `1` / `5` replaced minutes `00` with `15`. Before saving, the dialog visibly showed **10/23/2026, 9:15 AM start, 10:15 AM end, LPHa124, alarm off**. Enter saved it; the daily schedule confirmed 9:15 AM–10:15 AM and the unchanged description. Escape exited cleanly to DOS before collecting `E04_end_1015/files` and its full 126-file manifest. Input hashes are recorded in `E04_input_verification.json`.

**Confirmed result:** exactly one differing byte across the complete 6,144-byte database:

| Offset | E03 → E04 | Interpretation |
|---|---|---|
| `1032` (decimal 4146) | `A8 → A9` | EndTime incremented once for 10:00→10:15 AM |

No other byte changed. The prediction passed exactly. StartTime remains A5 at `1030`; the date bytes, DayOfWeek, empty Duration, description, Protected byte, record ID, framing, header, schema, table counters and both index pages remain identical. There is no insertion, deletion, relocation or size change. The other 125 file contents are unchanged.

The entire internal record at `0x1000–0x1026` remains identical, including `0x100D = 65`. Thus neither the isolated E03 start edit nor E04 end edit changed that internal record. Its earlier E02 change remains unexplained; the observed behavior continues to fit saved display state better than a mandatory per-edit revision value. Its exact meaning is not confirmed.

```text
0x1000 E03/E04: 80 10 20 20 FF 01 01 01 01 01 30 01 69 65 61 61
0x1030 E03:     A5 01 A8 01 31 01 4C 50 48 61 31 32 34 01 02 03
0x1030 E04:     A5 01 A9 01 31 01 4C 50 48 61 31 32 34 01 02 03
```

Reports: `ANALYSIS/E03_E04_comparison.json` and `.md`. No checksum or metadata byte changed during either isolated time edit; this observation does not establish universal absence of checksums.

## E05: isolated date edit, with both days verified

**Procedure:** verified all 126 E04 manifest hashes and copied the tree to disposable RUN. Reused the unchanged DOSBox profile; its guest system date stayed October 23. In Change Event, changed only the event date from `10/23/2026` to `10/24/2026`. Before saving, the dialog visibly showed **10/24/2026, 9:15 AM start, 10:15 AM end, LPHa124, alarm off**. Enter saved the edit. The displayed **Friday October 23 schedule was empty**. Search → Find Date → `10/24/2026` then displayed **Saturday October 24**, containing **LPHa124, 9:15–10:15 AM**. Escape exited Calendar cleanly to DOS before collecting the complete `E05_date_20261024/files` tree and manifest. Input hashes are in `E05_input_verification.json`.

Navigation was recorded: Right, Page Down and Tab did not advance the day; Display menu was inspected without changing view mode. Find Date was used successfully. Day view remained selected, but its displayed date changed October 23→24. This could have introduced saved-state differences; the byte comparison below shows no internal-record change in this run.

**Confirmed result:** exactly two differing byte positions, in two one-byte runs, across the complete 6,144-byte file:

| Offset | E04 → E05 | Observed association |
|---|---|---|
| `102B` (decimal 4139) | `78 → 79` | Last byte of Date field: `8F 6B 78 → 8F 6B 79` for October 23→24 |
| `102D` (decimal 4141) | `67 → 68` | Schema-named DayOfWeek field, Friday→Saturday |

No other byte changed. The first two date bytes (`1029–102A`) remain `8F 6B`. Time values A5/A9, description LPHa124, empty Duration, Protected byte, separators and terminators are identical. The other 125 filesystem contents are unchanged, and no files were added or removed. There is no size change, inserted region or removed region.

**Record/update behavior:** the row remains at `0x1027` with prefix `80 11` and ID `0x0011`. Its index triple at `0x142E` remains `04 00 27 00 11 00`; both index pages are byte-identical. Table strings `00002` and `00018`, header and schema are unchanged. The net persisted result is an **in-place edit**. There is **no on-disk evidence of deletion, reinsertion, new ID allocation or relocation** in these final snapshots. Transient implementation operations were not traced and cannot be excluded merely from final-state comparison.

**Internal record:** every byte in `0x1000–0x1026` is identical, including `0x100D = 65`. Navigating to the new displayed day introduced no observable internal-row change in this run. Its earlier E02 change remains unexplained.

```text
0x1027 E04: 80 11 8F 6B 78 01 67 01 01 A5 01 A9 01 31 01
0x1027 E05: 80 11 8F 6B 79 01 68 01 01 A5 01 A9 01 31 01
0x1036 both: 4C 50 48 61 31 32 34 01 02 03
0x142E both: 04 00 27 00 11 00
```

Reports: `ANALYSIS/E04_E05_comparison.json` and `.md`. Full snapshots, manifests and UI observations support the conclusion; it is not based only on the two targeted offsets.

## E06: month-boundary prediction test

**Procedure:** verified all 126 E05 manifest hashes and copied the tree to disposable RUN. Reused the existing profile and guest system date (October 23). Used Search → Find Date to locate the October 24 event, then changed only its Event Date to `11/01/2026`. Visually verified **November 1, 2026, 9:15–10:15 AM, LPHa124, alarm off** before saving. October 24's saved day schedule was empty. Find Date `11/01/2026` displayed **Sunday November 1, 2026**, containing the unchanged description/time range. Escape exited cleanly to DOS before preserving the complete `E06_date_20261101/files` tree and manifest. The year stayed 2026 throughout.

**Confirmed:** exactly three differing byte positions in two contiguous runs:

| Offset | E05 → E06 | Prediction/result |
|---|---|---|
| `1029` | `8F → 8F` | Unchanged, as predicted; this is not a year-encoding test |
| `102A` | `6B → 6C` | Predicted month byte change, matched |
| `102B` | `79 → 62` | Predicted day byte change, matched |
| `102D` | `68 → 62` | Predicted Saturday→Sunday byte change, matched |

All other bytes are identical. PERSONAL.CLN remains 6,144 bytes; no insertion, deletion, size increase or record relocation is visible in the final snapshots. Record prefix `80 11` remains at `1027`, and index triple `04 00 27 00 11 00` remains at `142E`. Header, schema, counters, both index pages, time bytes A5/A9, description, alarm-related observed state and framing are unchanged. The entire internal record `1000–1026`, including `100D = 65`, is unchanged. The other 125 file contents are identical; no filesystem files were added/removed. Transient implementation actions were not traced.

```text
0x1027 E05: 80 11 8F 6B 79 01 68 01 01 A5 01 A9 01 31 01
0x1027 E06: 80 11 8F 6C 62 01 62 01 01 A5 01 A9 01 31 01
0x1036 both: 4C 50 48 61 31 32 34 01 02 03
0x142E both: 04 00 27 00 11 00
```

The complete comparison matched the prospective component-encoding prediction. The alternative **plain raw big-endian serial-day-counter** prediction `8F 6B 81` did not occur and that model is rejected for these observations. Other transformed encodings are not ruled out in general. Reports: `ANALYSIS/E05_E06_comparison.json` and `.md`; input verification is `E06_input_verification.json` beside the experiment directories.

## E07: isolated year edit

**Procedure:** verified all 126 E06 file hashes and copied the complete tree to disposable RUN. Located November 1, 2026 through Find Date. In Change Event, changed only the last year digit, producing **11/1/2027**, and visually verified 9:15–10:15 AM, LPHa124 and alarm off before saving. The old Sunday November 1, 2026 schedule was empty after save. Find Date showed the event under **Monday November 1, 2027** with unchanged description/time range. Escape exited Calendar cleanly to DOS before preserving `E07_date_20271101/files` and its complete manifest. DOS system date/profile remained unchanged.

**Confirmed result:** exactly two differing byte positions, in two one-byte runs, across the full 6,144-byte file:

| Offset | E06 → E07 | Interpretation |
|---|---|---|
| `1029` (decimal 4137) | `8F → 90` | Year 2026→2027; prospective prediction matched |
| `102D` (decimal 4141) | `62 → 63` | Derived Sunday→Monday; prospective prediction matched |

Month/day `6C 62`, start/end A5/A9, description, empty Duration, Protected byte and framing are identical. Record prefix `80 11` stays at `1027`; index triple `04 00 27 00 11 00` remains at `142E`. Header, schema, both index pages and counters `00002`/`00018` are unchanged. The entire internal record `1000–1026`, including `100D = 65`, is unchanged. No additional files were created/deleted; the other 125 file contents are identical. No final-state relocation, deletion or reinsertion is evident; transient implementation operations were not traced.

```text
0x1027 E06: 80 11 8F 6C 62 01 62 01 01 A5 01 A9 01 31 01
0x1027 E07: 80 11 90 6C 62 01 63 01 01 A5 01 A9 01 31 01
0x1036 both: 4C 50 48 61 31 32 34 01 02 03
0x142E both: 04 00 27 00 11 00
```

Both predictions passed, with no other byte differences. Reports: `ANALYSIS/E06_E07_comparison.json` and `.md`; baseline verification is recorded in `E07_input_verification.json`.

## E08: second appointment and index enumeration

**Completed October 30, 2026.** This experiment follows the user's updated values, superseding the earlier proposed beta567/11:00–11:15 test. A previously verified E07 copy in RUN was preserved across the Computer Use interruption; the diagnostic confirmed all 126 RUN file contents still matched E07 before this continuation. E07 itself remains unchanged.

### Procedure and visual evidence

Used the existing SDL1/software-rendering profile and running DOSBox-X session. Brought its window forward with Windows window management and used independent full-desktop .NET captures. No native Computer Use retry, MCP troubleshooting, configuration change, installation or disassembly occurred. Navigation used foreground-checked Windows keyboard events into SDL1; field text used DOSBox-X's observed native clipboard-paste menu command (4104). AUTOTYPE was not used. Initial window-message/mouse inputs had no visible effect and were not treated as success.

Find Date located **Monday November 1, 2027** and visibly showed the existing **LPHa124, 09:15–10:15 AM**. Event → Add opened a separate new-event dialog. Final pre-save values were visually verified as **11/1/2027, 11:00 AM–12:00 PM, BETA456, alarm unchecked**. Clipboard input preserved the exact requested description; no alternate marker was needed. The dialog initially focused StartTime, and field/mask navigation caused unsaved input mistakes. Those were caught in fresh screenshots, cleared and corrected before the sole save. They are recorded as action provenance, not additional experiments.

After save, the day schedule visibly displayed **both** appointments independently with the requested descriptions/times. Escape returned cleanly to the **C:\DESKMATE>** prompt before collection. Entry system/day view displayed October 30, 2026, unlike the historical October 23 notes; no system-date command was sent. This observed difference did not produce any internal-record or unrelated database change.

Complete snapshot: `EXPERIMENTS/PHASE2/E08_two_events/files` and `manifest.json`, 126 installed files with SHA-256/size inventory. UI observations: `E08_visual_observations.json` beside the experiment directories and embedded in the manifest. Evidence screenshots/action scripts are in `E08_two_events/evidence`; decisive screenshots are `E08_14_original_verified.png`, `E08_25_new_event_verified.png`, `E08_26_both_appointments.png` and `E08_27_clean_exit.png`.

### Complete byte comparison

Only `DESKMATE/PERSONAL.CLN` differs. All other **125 file contents** are identical; no installed files were added or removed. Both databases are **6,144 bytes**. E08 SHA-256: `8a11fecd1d4e61266730602a7fda239edfce22870f509bee66a91e021d1913d6`.

Exactly **30 byte positions in six contiguous runs** differ. This table and the full new-record bytes account for every difference:

| Offset(s), inclusive | E07 → E08 | Observation |
|---|---|---|
| `0439` | `32 → 33` | Count string `00002 → 00003` |
| `0443` | `38 → 39` | Candidate next-ID string `00018 → 00019` |
| `103F–1057` | `03` + 24 zero bytes → bytes below | New 24-byte row plus displaced list terminator |
| `1434` | `00 → 04` | New index target page low byte |
| `1436` | `00 → 3F` | New index target in-page offset low byte |
| `1438` | `00 → 12` | New index ID low byte |

```text
0x103F: 80 12 90 6C 62 01 63 01 01 AC 01 B0 01 31 01
0x104E: 42 45 54 41 34 35 36 01 02 03
```

### Record, index and metadata results

| Property | Observed result |
|---|---|
| New row location | `0x103F–0x1056` inclusive, **24 bytes** |
| New prefix/identifier | `80 12`, index ID **0x0012** (decimal 18) |
| New Date | `1041–1043: 90 6C 62` (same date as original) |
| New DayOfWeek | `1045: 63` (Monday) |
| New Duration | Empty; separator at `1047`, no measured duration byte |
| New StartTime/EndTime | `1048: AC` / `104A: B0`, matching 11:00 AM/noon under the quarter-hour hypothesis |
| New Protected literal | `104C: 31`; semantics still untested |
| New Description | `104E–1054: 42 45 54 41 34 35 36` = exact ASCII `BETA456` |
| Row/list framing | Separator `1055: 01`, row terminator `1056: 02`, list terminator `1057: 03` |
| New index slot | `1434–1439: 04 00 3F 00 12 00` → (page 4, offset 003F, ID 0012) → absolute `103F` |
| Prior index slots | `1428–1433` byte-identical; internal ID10 and original ID11 still resolve correctly |
| Table count | `0435–0439: 00002 → 00003` |
| Candidate next ID | `043F–0443: 00018 → 00019` |
| Original appointment | All **24 bytes at `1027–103E` unchanged**, ID11 unchanged, no relocation |
| Internal/control row | All **39 bytes at `1000–1026` unchanged**, including `100D = 65` |
| File/pages | `0x1800` bytes before/after; six candidate 1,024-byte pages, no file growth or persisted evidence of an additional page |

The old list terminator at `103F` was replaced by the new record; `03` now follows it at `1057`. The first appointment's row terminator is at `103E`, so replacing the following list terminator does **not** modify its row. No existing index entry, schema byte, page header or metadata outside the two count-string bytes changed. The observed new record fits within the existing candidate data page; the new index fits within the existing index page. Final snapshots show no relocation or rewritten existing row; transient implementation behavior was not traced.

**Hypotheses tested, not assumed:** new ID `0x12`, count +1 and candidate next-ID +1 **all passed**. The count now equals two live appointments plus the pre-existing internal row. Its precise active-versus-allocated semantics still require deletion evidence; similarly, next-ID behavior under deletion/reuse is untested. All 30 differences are explained by the observed addition; **no unexpected differences** were found. This does not prove universal absence of checksums.

Reports: `ANALYSIS/E07_E08_comparison.json` (all changed files, exact raw runs, row/index evidence and hypotheses), `.md` (human-readable result) and `LOGS/E08_validation_20261030.json`. Reproduction: `ANALYSIS/SCRIPTS/analyze_e08.py` against preserved snapshots; `validate_e08.py` verifies both complete manifests and exact expected differences. Both are fixture-specific analysis/validation, not a general parser. The older `validate_first_record.py` and `CALENDAR_FIELDS.json` retain their documented E00–E07 scope.

## E09: deletion of trailing BETA456 appointment

**Completed October 30, 2026.** Verified all 126 preserved E08 file hashes/sizes and exact inventory, copied the full tree to RUN, and reverified. Prior RUN was retained separately; all prior experiment files remain unchanged. The existing SDL1/software-rendering emulator was at a visually verified clean DOS prompt before copying. Reused it without configuration changes, launching Calendar with `desk calendar`. Native Computer Use was not retried and no MCP troubleshooting/disassembly occurred.

### Application procedure and preserved evidence

Find Date displayed **Monday November 1, 2027** with both **LPHa124, 09:15–10:15 AM** and **BETA456, 11:00 AM–12:00 PM**. Selected BETA456, opened Event → Remove, and visually confirmed the **This event only** option was selected; the bulk-removal option was not selected. Confirmed once. The saved day schedule then showed only LPHa124 at the original time, with BETA456 absent. Escape returned Calendar cleanly to `C:\DESKMATE>` before collection.

Input and verification used the previously successful foreground-checked Windows keyboard/native emulator clipboard workflow and independent full-desktop .NET screenshots. No appointment description, date or time was edited. The guest date display remained October 30, 2026; no DOS date command was sent.

Complete snapshot: `EXPERIMENTS/PHASE2/E09_delete_beta456/files` plus its SHA-256/size/mtime `manifest.json`, 126 installed files. `E09_input_verification.json` and `E09_visual_observations.json` are beside the experiment directories. Screenshots and action scripts are under `E09_delete_beta456/evidence`; key captures are `E09_06_both_before_deletion.png`, `E09_07_beta_selected.png`, `E09_09_remove_result.png`, `E09_10_after_deletion.png` and `E09_11_clean_exit.png`.

### Independent E08 → E09 comparison

Only `DESKMATE/PERSONAL.CLN` changed; the other **125 file contents** are identical. No installed files were added or removed. Both files are **6,144 bytes** (`0x1800`, six candidate 1,024-byte pages). Exactly **30 differing byte positions in six contiguous runs**:

| Offset(s), inclusive | E08 → E09 | Observed effect |
|---|---|---|
| `0439` | `33 → 32` | Count string `00003 → 00002` |
| `0443` | `39 → 38` | Candidate next-ID string `00019 → 00018` |
| `103F–1057` | New 24-byte record + `03` → `03` + 24 zero bytes | Last row removed; row-list terminator restored to `103F` |
| `1434` | `04 → 00` | Last index slot page low byte cleared |
| `1436` | `3F → 00` | Last index slot offset low byte cleared |
| `1438` | `12 → 00` | Last index slot ID low byte cleared |

```text
0x103F E08: 80 12 90 6C 62 01 63 01 01 AC 01 B0 01 31 01
0x104E E08: 42 45 54 41 34 35 36 01 02 03
0x103F E09: 03 followed by 24 zero bytes through 0x1057
0x1434 E08: 04 00 3F 00 12 00
0x1434 E09: 00 00 00 00 00 00
```

The **24-byte original appointment at `1027–103E` is unchanged**, as are its ID11 and index entry. The **39-byte internal row at `1000–1026` is unchanged**, including `100D = 65`. Both surviving index entries `1428–1433` remain byte-identical. The deleted ID12 record occupied `103F–1056`; its old list marker was at `1057`. In E09, `103F` is the list terminator and `1040–1057` is zero. The remaining data-page tail is zero; the third index slot is all zero. No surviving record relocation or index-entry shift occurred, and no tombstone/new free-list marker is visible in these final bytes. The header, schema, index-page headers, unrelated metadata and remaining pages are unchanged. No page allocation/file-size change is observed.

### Independent E07 → E09 comparison

All **126 installed file contents** match E07, with **zero database byte differences**. E09's PERSONAL.CLN is exactly E07's original one-appointment database:

`aac152dcea193fa88e26c1b11b176284ec9959a2c5239f86dad7990e23e9034e`

Thus no second-record history remains in these final installed file contents. This statement does not erase the provenance logs, new snapshot manifests or modification timestamps, and it makes no claim about host filesystem remnants, physical disk erasure, transient state or other deletion cases. Both comparisons were computed directly against their respective preserved baselines, not inferred by reversing the E07/E08 report. Their JSON includes an explicit database comparison even when zero files changed.

### Interpretation bounded to this deletion

E09 deletes the **last physical/indexed appointment and highest ID**, not an interior row. Here the count decreases by one and still equals the internal row plus live appointments. This supports present-row counting in this case but does not distinguish active from allocated-slot semantics for interior deletion. The candidate next-ID value also decreases by one: a monotonic high-water allocator is inconsistent with this observed add/delete sequence. Actual reuse of ID12 remains untested until another record is added. Recalculation as max live ID + 1 is consistent, not established as a universal rule.

The final row area was cleared to the same logical tail/list marker/zero padding as E07. No tombstone is observed for this tail deletion; do not infer that all deletions erase bytes, compact indexes, move records, reclaim pages or preserve this counter relationship. No checksum-specific change or unexplained differing byte was found; universal checksum absence remains unproven.

### Existing parser verification and regression

Before any code changes, the existing parser accepted E09 and returned exactly **one user appointment: ID11 LPHa124, 2027-11-01 Monday, 09:15–10:15**, plus the opaque internal ID10. It did not count ID12 or BETA456. Initial output and parser hash are preserved in `ANALYSIS/E09_initial_parser_result.json`; pre-E09 parser/CLI/tests/README copies are in E09 evidence. The parser and CLI implementations were **not changed**. No unsupported deletion structure was introduced in this fixture.

Added E09 to the authoritative regression fixture list and two focused tests for the raw trailing-deletion result and CLI exclusion of the deleted appointment. **45 tests pass across E00–E09** with expected counts `[0,1,1,1,1,1,1,1,2,1]`, including all prior malformed-input and relocation cases. E09 human/JSON CLI smoke checks pass. All **1,260 installed file hashes/inventories** across the ten manifests match; no preserved database was modified. Current README documents the supported tail-deletion case while leaving other deletion patterns unsupported/unverified.

Reports: `E08_E09_comparison.json/.md`, `E07_E09_comparison.json/.md`, `E09_deletion_evidence.json`, `E09_initial_parser_result.json`, `PARSER_E09_listing.txt`, `PARSER_E09.json`, `PARSER_VALIDATION.json` under ANALYSIS; `LOGS/E09_validation.json` and `PARSER_TESTS.txt`. `ANALYSIS/SCRIPTS/validate_e09.py` asserts the observed deletion evidence without modifying input. The earlier 43-test report is retained in LOGS with `_before_E09` suffix.

## E10: same-sized replacement record reuse

**Completed October 30, 2026.** Started from the preserved E09 snapshot, verified all 126 file contents/sizes and exact inventory, copied its complete tree to RUN and reverified. Retained prior RUN separately. E09's one-appointment database was not edited in place; earlier snapshots/manifests remain unchanged.

### Procedure and visual evidence

Reused the existing SDL1/software-rendering emulator at a visually verified DOS prompt. Launched Calendar, used Find Date for November 1, 2027, and visually confirmed **LPHa124, 09:15–10:15 AM** was the sole appointment. Event → Add created exactly one new appointment. Before the sole save the dialog visibly showed **11/1/2027, 11:00 AM–12:00 PM, exact GAMMA45, alarm unchecked**. No input-description alteration occurred. The saved **Monday November 1, 2027** day schedule displayed both appointments with their requested values. Escape returned cleanly to `C:\DESKMATE>` before collection.

Used the successful foreground-checked Windows keyboard/native DOSBox-X clipboard workflow and independent full-desktop .NET screenshots. No native Computer Use retries, MCP troubleshooting, software installation, profile changes, database writing code or additional experiment. Guest system date display remained October 30, 2026; no DOS date command was sent.

Snapshot: `EXPERIMENTS/PHASE2/E10_reuse_gamma45/files` and `manifest.json`, all **126 installed files** with SHA-256, size and mtime. Input/visual observations are in `E10_input_verification.json` and `E10_visual_observations.json` beside the experiment directories. Screenshots/action scripts and pre-E10 parser/test/README copies are under `E10_reuse_gamma45/evidence`. Decisive captures: `E10_05_original_before_add.png`, `E10_10_new_event_verified.png`, `E10_11_both_appointments.png`, `E10_12_clean_exit.png`.

E10 PERSONAL.CLN SHA-256: `853f4340ccb3fc6a144479524d7d1e0b0e5acee5788a6bebc7b6c541bafc07a3`.

### Independent E09 → E10 allocation comparison

Only `DESKMATE/PERSONAL.CLN` differs; the other **125 file contents** are identical, with no installed files added/removed. The database remains **6,144 bytes**, six candidate 1,024-byte pages. Exactly **30 differing positions in six contiguous runs**:

| Offset(s), inclusive | E09 → E10 | Observed role |
|---|---|---|
| `0439` | `32 → 33` | Count string `00002 → 00003` |
| `0443` | `38 → 39` | Candidate next-ID string `00018 → 00019` |
| `103F–1057` | `03` + 24 zero bytes → new row + `03` below | New 24-byte appointment plus moved list marker |
| `1434` | `00 → 04` | Reused index slot page low byte |
| `1436` | `00 → 3F` | Reused index slot in-page offset low byte |
| `1438` | `00 → 12` | Reused index slot record ID low byte |

```text
0x103F: 80 12 90 6C 62 01 63 01 01 AC 01 B0 01 31 01
0x104E: 47 41 4D 4D 41 34 35 01 02 03
0x1434: 04 00 3F 00 12 00  -> page4, offset003F, ID0012
```

The row occupies **103F–1056 inclusive (24 bytes)**, with prefix **80 12** and index ID **0012**. Its list terminator is at **1057**. Date `90 6C 62`, Monday `63`, empty Duration, StartTime `AC`, EndTime `B0`, Protected literal `31`, and ASCII `GAMMA45` match the observed schema and intended event. Alarm was verified off in the application; storage semantics remain undecoded.

All six primary predictions **passed**: ID12, record address103F, index slot1434, count2→3, candidate next-ID18→19 and size6144. The original LPHa124 row **1027–103E (24 bytes)**, internal row **1000–1026 (39 bytes, including100D65)** and both earlier index entries **1428–1433** remain byte-identical. No record relocation, schema/header change, new page or unexplained byte difference was found.

### Independent E08 → E10 replacement comparison

Only PERSONAL.CLN differs; other125filecontents are identical, with no added/removed installed files. Exactly **seven differing bytes in one run at 104E–1054**:

| E08 hex / text | E10 hex / text |
|---|---|
| `42 45 54 41 34 35 36` / `BETA456` | `47 41 4D 4D 41 34 35` / `GAMMA45` |

Every other database byte is identical, including both row identifiers, dates/times, field framing, counts, index targets and page layout. Therefore the prospective description-only comparison prediction also passed. This is a direct comparison against E08, not an inference from allocation metadata alone. Content comparisons do not claim equal timestamps or snapshot/provenance metadata.

### Conclusions and bounds

The E08→E09→E10 lifecycle demonstrates **actual reuse of the deleted highest ID, former tail record address and former trailing index slot for this same-sized replacement**. The candidate next-ID value rolls back on deletion and advances again on reuse; a strictly monotonic allocation counter is inconsistent with this sequence. A record ID alone is consequently not a permanent event identity across this demonstrated delete/re-add lifecycle: ID12 names BETA456 in E08 and GAMMA45 in E10.

No inference about best-fit/first-fit allocation, interior holes, arbitrary deletion order, larger/smaller replacement rows, linked-page allocation or ID-width boundaries is established. The two descriptions are equal-length ASCII; variable-length behavior remains untested. No extra checksum/revision byte changed outside the replacement description when comparing E08/E10, but universal absence of those mechanisms remains unproven. **No unexpected differences** were observed.

### Parser and automated validation

The existing parser accepted E10 without modification and enumerated ID11 LPHa124 2027-11-01 Monday09:15–10:15 and ID12 GAMMA45 11:00–12:00, excluding opaque internalID10. Parser/CLI source hashes are unchanged; their pre-E10 copies are preserved in evidence. Added E10 to the authoritative fixture list and focused reuse/CLI regressions. **47 tests pass across E00–E10**, including the previous45 tests, malformed inputs and in-memory relocation checks. Expected appointment counts are `[0,1,1,1,1,1,1,1,2,1,2]`. Human/JSON E10 CLI smoke checks passed. All **1,386 installed-file hashes and inventories** across eleven manifests match; preserved databases/manifests remain unchanged.

Reports under ANALYSIS: `E09_E10_comparison.json/.md`, `E08_E10_comparison.json/.md`, `E10_reuse_evidence.json`, `PARSER_E10_listing.txt`, `PARSER_E10.json`, `PARSER_VALIDATION.json`. Current test log is `LOGS/PARSER_TESTS.txt`; `E10_validation.json` records the test/hash/prediction results. Earlier45test reports are retained in LOGS with `_before_E10` suffix. `compare_calendar.py` can reproduce either raw comparison from the preserved paths; collection/action scripts are archived in E10 evidence.

## E11: non-trailing description growth and relocation

**Completed October 30, 2026.** Verified all 126 preserved E10 file hashes/sizes and exact inventory; copied the complete installed tree to RUN and reverified. Prior RUN and all prior snapshots/manifests remain preserved. The existing SDL1/software-rendering emulator was at a visibly confirmed DOS prompt before copying; no configuration change or new tool installation was required.

### Controlled UI edit and evidence

Launched Calendar and used Find Date for **Monday November 1, 2027**. Confirmed **LPHa124 09:15–10:15 AM** and **GAMMA45 11:00 AM–12:00 PM**. Opened Change Event on the first appointment; its date, times and unchecked alarm were visually verified. With description focused, End plus native clipboard paste appended only `XYZ`. The complete **LPHa124XYZ** (10 ASCII characters) and all other dialog values were verified before the sole save. The saved schedule showed both appointments with their original times and the requested descriptions. Escape returned cleanly to `C:\DESKMATE>` before collection.

Used the established foreground-checked Windows keyboard/native DOSBox-X clipboard workflow with independent full-desktop .NET screenshots. No native Computer Use retries, MCP troubleshooting, disassembly, database writer or additional experiment. The guest date display remained October 30, 2026; no DOS date command was sent.

Snapshot: `EXPERIMENTS/PHASE2/E11_description_growth/files` and SHA-256/size/mtime `manifest.json`, all126installedfiles. Input/visual observations: `E11_input_verification.json` and `E11_visual_observations.json` beside experiment directories. Screenshots, action scripts, initial raw analysis and pre-E11 parser/test/README copies are in `E11_description_growth/evidence`; decisive captures are `E11_05_both_before_edit.png`, `E11_06_change_event.png`, `E11_07_description_verified.png`, `E11_08_both_after_edit.png`, `E11_09_clean_exit.png`.

E11 PERSONAL.CLN SHA-256: `3bca1cd401464a09064692a9173880d0e464b7b5e8559eb3eed912911e6449b1`.

### Observed physical records, logical events and index entries

The simple **GAMMA45 +3 forward shift to1042 hypothesis failed**. Both logical events changed storage locations and row IDs, while the existing ID set10/11/12 and table counters remained unchanged:

| Logical appointment | E10 ID / address / row length | E11 ID / address / row length |
|---|---|---|
| LPHa124 → LPHa124XYZ,09:15–10:15 | `11 / 1027 / 24` | **`12 / 103F / 27`** |
| GAMMA45,11:00–12:00 | `12 / 103F / 24` | **`11 / 1027 / 24`** |
| Internal/control | `10 / 1000 / 39` | `10 / 1000 / 39`, all bytes unchanged |

Data-page order changed from **internal → LPHa124 → GAMMA45** to **internal → GAMMA45 → LPHa124XYZ**. The enlarged record did not remain at1027; it occupies103F–1059 inclusive. GAMMA45 moved backward24bytes to1027–103E. The list terminator moved from1057 to105A because total used row storage grew by3bytes.

```text
E11 0x1027: 80 11 90 6C 62 01 63 01 01 AC 01 B0 01 31 01
E11 0x1036: 47 41 4D 4D 41 34 35 01 02
E11 0x103F: 80 12 90 6C 62 01 63 01 01 A5 01 A9 01 31 01
E11 0x104E: 4C 50 48 61 31 32 34 58 59 5A 01 02 03
```

| Index slot | E10 triple | E11 triple | E11 logical target |
|---|---|---|---|
| `1428` | `04 00 00 00 10 00` | unchanged | Internal at1000,ID10 |
| `142E` | `04 00 27 00 11 00` | **`04 00 3F 00 12 00`** | LPHa124XYZ at103F,ID12 |
| `1434` | `04 00 3F 00 12 00` | **`04 00 27 00 11 00`** | GAMMA45 at1027,ID11 |

The two six-byte user index triples swapped slots and continue to match their row prefixes/IDs. The logical index order remains LPHa then GAMMA even though physical order is reversed; this proves index order need not equal physical address order in this fixture, not a general index sorting-key rule. Neither event receives a previously unused ID in the final snapshot: ID11 and ID12 are reassigned between them. The earlier raw-ID-keyed preservation map in initial analysis is not a logical-event identity map; the augmented analysis records these logical matches explicitly.

### Complete E10 → E11 comparison

Only `DESKMATE/PERSONAL.CLN` changed. Other **125 installed file contents** are identical; no installed files were added/removed. Both databases remain **6,144 bytes**, six candidate1024bytepages. Exactly **28 byte positions in ten contiguous runs** differ; the report table below records all raw bytes. Of these,24positions are in the data page and4 in the user index page. No header, table metadata, schema, schema-index or index-header byte changed.

Offset1030/1032 now contains GAMMA's AC/B0 instead of LPHa's A5/A9, and1048/104A now contains LPHa's A5/A9 instead of GAMMA's AC/B0. Those are **changes of which logical record occupies an address**, not edits to either appointment's times. GAMMA45's complete22byte payload after its two-byte row prefix is identical before/after; only its prefix ID changes12→11 while the row relocates. LPHa's date/weekday/Duration/start/end/Protected/framing fields are unchanged relative to its own row; description is exactly the old seven bytes plus58595A (XYZ), and ID changes11→12.

Count `0435–0439` stays **00003** and candidate next-ID `043F–0443` stays **00019**. The entire **39byte internal row1000–1026**, including100D65, remains identical. The grown record's final separator/row terminator are at1058/1059; list marker03 is at105A, and105B–13FF is zero padding. Three bytes of prior padding were consumed, with no file growth, additional-page evidence or new free-space/tombstone marker.

There is one complete active GAMMA payload and one complete active LPHa124XYZ payload in the observed data page; neither old complete24byte row remains elsewhere in that page. The initial parser's coverage and zero-tail checks also succeed. No duplicate/abandoned row, unindexed nonzero tail, unexplained metadata alteration or unexplained differing byte is present in the final file. This does not rule out transient copies or filesystem-level remnants.

### Bounded interpretation and identity implications

**Unexpected relative to the simple growth hypothesis:** physical order reverses, both logical IDs change, and both user index entries are retargeted; GAMMA does not move to1042. **No byte differences remain unexplained** after matching logical records by the verified description/time payloads.

The result is consistent with removing the edited row, compacting the unchanged row backward, and appending the enlarged row, with compact/reassigned storage IDs. Final snapshots alone do not prove that transient implementation sequence or a general compaction/allocation algorithm. Only a7→10 ASCII growth with these two user rows, IDs and available same-page padding was tested.

E11 strengthens the ID limitation beyond E10's delete/re-add case: an **untouched logical event's ID and location can change when another event grows**. Raw row IDs are useful snapshot-local references but cannot alone be treated as stable appointment identity across edits. This evidence does not establish the complete row-ID codec or all renumbering rules. Counter constancy here establishes no new live row in the net result, not absence of transient allocation.

### Existing parser and regression results

The existing parser accepted E11 before any modification and correctly returned **LPHa124XYZ, November1,2027,09:15–10:15 AM** and **GAMMA45, November1,2027,11:00 AM–12:00 PM**, excluding the internal record. It followed the swapped index targets and variable-length row boundaries without hardcoded E11 addresses. **Parser and CLI implementations remain unchanged.**

Added E11 fixture expectations by logical description rather than assuming ID11 always denotes LPHa, and explicit regression checks for both relocations, reassigned IDs, preserved payloads, index-to-prefix agreement,27/24byte lengths, zero tail and no duplicate/abandoned rows. The actual-location constants occur only in fixture assertions, not parsing logic. **49 tests pass across E00–E11**, retaining compatibility with all prior47 tests, malformed-input checks and synthetic relocation tests. E11 text/JSON CLI smoke checks passed. All **1,512 preserved installed-file hashes/inventories** across twelve manifests match; input bytes/mtime remain unchanged in fixture tests.

Reports: `ANALYSIS/E10_E11_comparison.json/.md`, `E11_growth_evidence.json`, `PARSER_E11_listing.txt`, `PARSER_E11.json`, `PARSER_VALIDATION.json`; `LOGS/PARSER_TESTS.txt`, `E11_validation.json`. Earlier47test results are retained with `_before_E11` suffix. Initial parser output/hash and raw index-resolved analysis are retained in E11 evidence. `compare_calendar.py` reproduces the raw comparison from the preserved paths.

## E12: physically interior deletion, compaction and reassigned ID

**Completed October 31, 2026.** Started from the complete E11 snapshot, verified its exact 126-file inventory, sizes and SHA-256 hashes, then copied and reverified it as RUN. The prior RUN was retained separately. No preserved fixture, original media, installed application or emulator configuration was modified.

### Controlled deletion and visual evidence

Using the existing SDL1/software-rendering profile, independent full-desktop captures and foreground-checked Windows keyboard/native DOSBox-X clipboard input, launched Calendar and navigated to Monday November 1, 2027. Both **LPHa124XYZ, 09:15–10:15 AM** and **GAMMA45, 11:00 AM–12:00 PM** were visually verified. Selected GAMMA45 and used Event > Remove > **This event only** > OK. A fresh capture showed only LPHa124XYZ with its unchanged time. Escape returned cleanly to `C:\DESKMATE>` before collection. No event property editor or alarm input was used; the preserved baseline alarm-off setting and every stored survivor field remained unchanged. Alarm storage is still undecoded by the parser.

The first launch-command paste did not appear at the DOS prompt; an independent screenshot confirmed the empty prompt before one successful retry. No appointment input was repeated. No native Computer Use retry, MCP troubleshooting, new installation, disassembly or additional experiment was performed. The task crossed local midnight: preparation and pre-deletion captures began October 30; deletion/clean exit and analysis completed October 31. The guest date display remained October 30, 2026; no DOS date change was sent.

Preservation: `EXPERIMENTS/PHASE2/E12_delete_gamma45/files` contains all **126 installed files**, with SHA-256/size/mtime `manifest.json`. Input verification, visual observations and screenshots are preserved separately as evidence. Decisive captures: `E12_07_both_before_deletion.png`, `E12_08_gamma_selected.png`, `E12_09_remove_dialog.png`, `E12_10_after_deletion.png`, `E12_11_clean_exit.png`. Collection/action scripts, initial parser result and pre-E12 source copies are retained under `E12_delete_gamma45/evidence`, with an evidence hash manifest.

E12 PERSONAL.CLN SHA-256: `27aa61ddc40bfaa7685abe88741a368ade44bb8693365c7d0fe0cb2c5d5d3ed0`.

### Observed record and index maintenance

GAMMA45 was physically non-trailing, but was the last logical/index appointment. These are different orderings: E11's data order was internal → GAMMA45 → LPHa124XYZ, while its user index order was LPHa124XYZ → GAMMA45.

| Item | E11 | E12 |
|---|---|---|
| Internal row | ID `10`, address `1000`, length 39 | All bytes, ID, address and index unchanged |
| GAMMA45 | ID `11`, address `1027`, length 24, index `1434` | Deleted; no active or abandoned complete row/payload found |
| LPHa124XYZ | ID `12`, address `103F`, length 27, index `142E` | **ID `11`, address `1027`, length 27**, index `142E` |
| PERSONAL count `0435–0439` | `00003` | **`00002`**, includes internal row |
| Candidate next-ID `043F–0443` | `00019` | **`00018`** |
| List terminator | `03` at `105A` | `03` at **`1042`** |

The survivor moves backward exactly **24 bytes**, the deleted row's length. Its two-byte row prefix changes `80 12` → `80 11`; the following **25 bytes are identical** to its own E11 payload, including date, weekday, empty Duration, times, Protected, complete description and row terminator. This is relocation and renumbering, not a change to appointment properties.

```text
E12 0x1027: 80 11 90 6C 62 01 63 01 01 A5 01 A9 01 31 01
E12 0x1036: 4C 50 48 61 31 32 34 58 59 5A 01 02 03

Index 1428: 04 00 00 00 10 00  (unchanged internal row)
Index 142E: 04 00 3F 00 12 00 -> 04 00 27 00 11 00
Index 1434: 04 00 27 00 11 00 -> 00 00 00 00 00 00
```

The retained logical index slot now resolves to the compacted row and agrees with its new prefix ID. The complete trailing six-byte index entry is zero, as is the remaining index tail. There is no additional slot movement: the deleted event already occupied the last logical index slot, so this experiment does **not** test deletion of a non-last index entry.

### Exhaustive binary comparison

E11 → E12 changes only `DESKMATE/PERSONAL.CLN`; the other **125 installed file contents** are identical, with no added/removed files. The database remains **6,144 bytes**, with the same six candidate 1,024-byte pages and unchanged table page references. There is no allocation/header/schema/index-header change.

Exactly **46 byte positions in ten contiguous runs** differ: `0439`, `0443`, `1030`, `1032`, `1036–105A`, `1430`, `1432`, `1434`, `1436`, `1438`. Per candidate page, changed-position counts are **0, 2, 0, 0, 39, 5**. Raw before/after bytes for every run appear in `ANALYSIS/E11_E12_comparison.json/.md`.

The two metadata bytes implement the observed counter decrements. The changes at `1030` and `1032` replace GAMMA's old time bytes with the survivor's unchanged A5/A9; the long data run replaces GAMMA's description with LPHa124XYZ and clears the old tail. Five changed index bytes retarget/renumber the survivor and clear the trailing entry. The internal row's **39 bytes at `1000–1026`**, including `100D=65`, are identical.

The final survivor occupies `1027–1041`; `1042` is the list marker and **`1043–13FF` is entirely zero**. In particular, the newly freed 24-byte range `1043–105A` is zero-filled. The deleted row's former region is reused by the survivor, rather than replaced wholly by zeros. Its common framing/date/Protected bytes can remain equal at their absolute addresses. The former survivor address `103F` is now inside the compacted row's description tail, not a second row. Neither the full old survivor row nor the full deleted GAMMA row/payload nor ASCII `GAMMA45` occurs elsewhere in the final file. The survivor payload occurs exactly once. No tombstone, gap, duplicate row, unindexed data, alternate free-space marker or unexplained differing byte is present in this closed snapshot. These observations describe logical file contents and do not imply secure erasure of host storage or absence of transient copies.

### What this confirms, and what remains a hypothesis

**Confirmed in this fixture:** deleting a physically interior user row compacts the following 27-byte user row backward, decrements its ID, retargets its retained index entry, clears the last index entry, reduces both counters by one and zero-fills the freed data tail. An untouched logical appointment's raw ID is therefore not stable across this deletion. The resulting physical ID/address sequence is consistent with the dense ordering seen in E11; IDs should be treated as snapshot-local references.

**Supported interpretation:** E12 strengthens the proposed delete-and-compact explanation for E11's growth result: removal can move a later physical row backward and reassign its ID, leaving room for an enlarged edited event to be appended. Final before/after snapshots do not establish E11's transient call sequence, a universal ordinal-ID codec, handling of several subsequent rows, deletion from a non-last logical index slot, page allocation, or behavior across multiple data pages. No general database-engine algorithm is claimed.

### Parser and preservation verification

The existing read-only parser accepted E12 **before any source changes**, correctly enumerating exactly one user appointment: **LPHa124XYZ — Monday November 1, 2027, 09:15–10:15 AM**, ID `11`, 27-byte row, plus the separate internal/control row. It follows the index target and bounded variable-length framing. **Parser and CLI implementations remain byte-for-byte unchanged.**

Added E12 to the fixture expectations and two regression tests covering survivor payload preservation, relative relocation by the deleted row length, reassigned IDs, index-to-prefix/address agreement, cleared trailing index, dynamic list marker/zero tail, counters, internal-row preservation, and text/JSON output. The new relocation regression derives addresses from the parsed E11 records rather than hardcoding E12's appointment location.

**51 tests pass across E00–E12**, including all previous 49 checks and malformed-input cases. Both actual CLI modes passed. All **1,638 preserved installed-file hashes and exact inventories across 13 fixture manifests** match; fixture read-only tests confirm unchanged database bytes/mtime. The E12 snapshot's evidence manifest is also verified. Reports: `ANALYSIS/E12_deletion_evidence.json`, `E11_E12_comparison.json/.md`, `PARSER_E12_listing.txt`, `PARSER_E12.json`, `PARSER_VALIDATION.json`; `LOGS/PARSER_TESTS.txt`, `E12_validation.json`. Previous validation logs are retained with `_before_E12` suffix.

## E13: description shrinkage and exact binary restoration

**Completed October 31, 2026.** Verified all 126 E12 snapshot file hashes, sizes and the exact inventory against its preserved manifest, copied the complete installed tree to RUN and reverified it. Prior RUN and all earlier fixtures remain preserved. The existing emulator was at a visually confirmed clean DOS prompt before copying; the working SDL1/software-rendering profile was reused unchanged.

### Controlled edit and provenance

Calendar showed the sole **LPHa124XYZ** appointment on **Monday November 1, 2027, 09:15–10:15 AM**. Change Event opened with description focused. Sent **End, Backspace, Backspace, Backspace**, removing only XYZ. Before the sole save, an independent full-desktop screenshot verified the complete **LPHa124** description, event date11/1/2027, start9:15AM, end10:15AM and unchecked alarm. The saved schedule showed the correct shortened description and unchanged times. Escape returned cleanly to `C:\DESKMATE>` before preservation.

Used the established foreground-checked Windows keyboard workflow, DOSBox-X native clipboard for launch/date entry, and independent .NET desktop screenshots. No native Computer Use retry, MCP troubleshooting, setup, configuration changes, database writer, broad disassembly or additional experiment. The guest date display remained October30,2026 and was not changed. Host experiment/collection date was October31,2026.

Snapshot: `EXPERIMENTS/PHASE2/E13_description_shrink/files` contains all126 installed files; `manifest.json` records SHA-256, sizes and mtimes. Input verification and visual observations are preserved beside the experiment directories and copied into E13 evidence. Decisive screenshots under `E13_description_shrink/evidence`: `E13_05_before_edit.png`, `E13_06_change_event.png`, **`E13_07_verified_before_save.png`**, `E13_08_after_save.png`, `E13_09_clean_exit.png`. Scripts, initial parser result/raw evidence and pre-E13 source copies are preserved, with a separate evidence hash manifest. Original and experimental database files were never rewritten by analysis tooling.

### Complete E12 → E13 comparison

Only `DESKMATE/PERSONAL.CLN` changed; other **125 installed file contents** are identical, no installed files added/removed. Both databases remain **6,144 bytes**, with unchanged six-page organization and table page references. Exactly **six byte positions in one contiguous run** differ, all within the existing PERSONAL data page:

| Offset | E12 bytes | E13 bytes | Meaning in this fixture |
|---|---|---|---|
| `103D–1042` | `58 59 5A 01 02 03` | `01 02 03 00 00 00` | XYZ removed, field/row/list markers moved back3bytes; released tail zero-filled |

All bytes outside this run are identical. No unexplained metadata, preference, schema, header or auxiliary-file changes were observed. Per candidate page, differing-position counts are **0,0,0,0,6,0**.

| Item | E12 | E13 |
|---|---|---|
| Appointment description | LPHa124XYZ,10ASCII bytes | LPHa124,7ASCII bytes |
| Appointment ID / address | `11 / 1027` | **unchanged** |
| Complete row length | 27bytes | **24bytes** |
| Final description field separator | `01` at1040 | `01` at103D |
| Row terminator | `02` at1041 | `02` at103E |
| List terminator | `03` at1042 | `03` at103F |
| PERSONAL record count | `00002` | unchanged, includes internal row |
| Candidate next-ID | `00018` | unchanged |
| Internal row | ID10,1000,length39 | all bytes/address/ID unchanged |
| Entire PERSONAL index page | Entries1428internal,142Eappointment | all bytes unchanged |

E13 appointment bytes:

```text
0x1027: 80 11 90 6C 62 01 63 01 01 A5 01 A9 01 31 01
0x1036: 4C 50 48 61 31 32 34 01 02 03
```

The row prefix and all fields before Description are identical, including the date, stored weekday, empty Duration, start/end bytes, Protected and field separators. Description is exactly the prior description minus XYZ. The same `01 02` field/row framing is retained. Released bytes **1040–1042 are zero**, and **1040–13FF is entirely zero**. No abandoned long row, duplicate appointment, unindexed nonzero data, gap or tombstone appears in the final supported data page. This is a logical-file observation, not a host-disk erasure claim.

The retained appointment index at **142E–1433** remains `04 00 27 00 11 00`, resolving page4/offset27/ID11 correctly. The internal index remains unchanged; index tail starting1434 stays zero. Count bytes0435–0439 and candidate next-ID043F–0443 remain00002/00018. The internal row1000–1026 including100D65 is identical. All allocation metadata/page headers, schema pages and total size remain unchanged.

### Independent E07 and E09 restoration checks

Direct byte-by-byte comparisons against **each independently preserved baseline** found **zero differences across all6,144 database bytes**. E13, E07 and E09 share SHA-256:

`aac152dcea193fa88e26c1b11b176284ec9959a2c5239f86dad7990e23e9034e`

Both complete installed-tree comparisons also found **all126 file contents identical**, with no added/removed files. Thus the database and complete installed-tree contents returned exactly to the earlier one-appointment state. Snapshot timestamps, manifests and evidence retain their distinct provenance; equality of file contents does not erase that history. No unexpected differences were found.

Reports: `ANALYSIS/E12_E13_comparison.json/.md`, `E07_E13_comparison.json/.md`, `E09_E13_comparison.json/.md`. Raw before/after parser results, page-change counts, counters and binary regions: `ANALYSIS/E13_shrinkage_evidence.json`.

### Interpretation: what shrinkage does and does not prove

**Confirmed:** for this sole trailing appointment, a10→7ASCII description edit leaves ID/location/index/counters unchanged, shortens the row by3bytes, moves its terminal framing/list marker backward by3 and zero-fills the released tail. All stated restoration predictions passed.

This outcome is **compatible with** deleting the only user row and reinserting the shorter event, reusing the same ID/address as observed for trailing lifecycle reuse. It does **not independently establish** that sequence: an in-place shortening or a general packed-page rewrite produces the same final bytes when there is no following user record. E11's growth relocation and E12's direct deletion/compaction still support delete/compact/reinsert as an explanation of those earlier changes, but E13 cannot distinguish it from alternatives. No transient calls or intermediate states were traced. Non-trailing shrinkage and page-boundary allocation remain untested; do not infer a universal modification policy from this case.

### Parser and regression verification

The existing parser accepted E13 before any implementation change, returning exactly **LPHa124 — November1,2027,Monday,09:15–10:15**, ID11,length24, plus the separate internal/control row. It uses index targets and bounded row framing; no E13 address was added to parsing logic. **Parser and CLI implementations remain byte-for-byte unchanged.** Alarm remains undecoded in parser output; its off state was visually verified in the application.

Added E13 fixture expectations and two regressions: relative row shrinkage and dynamic framing/zero tail, preserved other raw fields/metadata/internal row, unchanged ID/address/index, exact entire-file equality to E07 and E09, and text/JSON single-event output. New regression addresses are derived from parsed records. **53 tests pass across E00–E13**, including all prior51 and malformed-input/read-only checks. Actual text/JSON CLI subprocess checks pass. All **1,764 installed-file hashes and exact inventories across14 preserved fixture manifests** match; the read-only tests confirm unchanged source database bytes/mtime. Preserved experiment evidence manifests are also verified, with per-manifest counts in `LOGS/E13_validation.json`.

Updated test/README and format/status documentation; no parser rewrite, writer or further GUI experiment. Current results: `ANALYSIS/PARSER_VALIDATION.json`, `PARSER_E13_listing.txt`, `PARSER_E13.json`, `LOGS/PARSER_TESTS.txt`, `E13_validation.json`. Previous51-test logs retained with `_before_E13` suffix.

## E14: physically non-trailing shrinkage preserves IDs and compacts the following row

**Completed October 31, 2026. Branch: E11, explicitly not E13.** Verified the complete E11 installed-tree inventory and all126 file sizes/SHA-256 hashes against its preserved manifest. Copied E11/files to the separate disposable RUN tree and reverified it; prior RUN was retained under a dated `RUN_before_E14_*` directory. All previous experiment snapshots/manifests remain unchanged. The existing emulator was independently captured at a clean DOS prompt before copying. The working SDL1/software-rendering profile was reused without changes.

### Controlled edit and visual evidence

On **Monday November 1, 2027**, Calendar visibly showed **LPHa124XYZ,09:15–10:15 AM** and **GAMMA45,11:00 AM–12:00 PM**. Selected the second logical appointment, GAMMA45 (physically first after the internal row), and opened Change Event. With Description focused, **End and three Backspace keys** removed only A45, producing **GAMM**. The complete pre-save dialog verified date11/1/2027, start11:00AM, end12:00PM and unchecked alarm. One Enter saved it; the saved schedule showed **LPHa124XYZ09:15–10:15** and **GAMM11:00–12:00** on the same correct date. LPHa's properties were never edited. Escape returned cleanly to `C:\DESKMATE>` before collection.

Used the established foreground-checked Windows keyboard/native DOSBox-X clipboard workflow and independent full-desktop .NET captures. No native Computer Use retry, MCP troubleshooting, setup, configuration changes, database writer, broad disassembly or additional experiment. Guest date display remained October30,2026; no DOS date command was sent. Host action/collection date was October31,2026.

Complete snapshot: `EXPERIMENTS/PHASE2/E14_interior_shrink/files` (126 files), with SHA-256/size/mtime `manifest.json`. Input verification and visual observations are retained alongside experiment directories and copied into E14 evidence. Decisive screenshots under `E14_interior_shrink/evidence`: `E14_05_both_before_edit.png`, `E14_06_change_gamma.png`, **`E14_07_verified_before_save.png`**, `E14_08_both_after_save.png`, `E14_09_clean_exit.png`. Initial index-resolved raw analysis/parser output, pre-E14 source copies and action/analysis scripts are preserved with a separate evidence manifest. Analysis never writes an experiment database.

E14 PERSONAL.CLN SHA-256: `c4521c0f63ecf60b0abe959a03c5f2ceb84cb695fb2e26d656190a0a893ab3fd`.

### Actual physical layout and hypotheses

**Hypothesis A's final-layout predictions passed. Hypothesis B's remove/compact/append final layout did not occur.** Physical order remains internal → edited GAMM → unchanged LPHa124XYZ; logical/index order remains internal → LPHa124XYZ → GAMM.

| Logical record | E11 ID / address / length | E14 ID / address / length |
|---|---|---|
| Internal/control | `10 / 1000 / 39` | All bytes, ID, location and index unchanged |
| GAMMA45 → GAMM | `11 / 1027 / 24` | **`11 / 1027 / 21`** |
| LPHa124XYZ | `12 / 103F / 27` | **`12 / 103C / 27`**, complete raw record unchanged |

GAMM stays at its original address and retains its ID. Its row is exactly the original prefix/fields plus the four ASCII characters GAMM and the original `01 02` framing, omitting A45. All other stored fields are identical. The following LPHa row shifts backward exactly3bytes and is **byte-for-byte identical over all27bytes, including its ID prefix**, not merely its decoded date/time/description. No ID reassignment occurs in this experiment.

```text
E14 0x1027: 80 11 90 6C 62 01 63 01 01 AC 01 B0 01 31 01
E14 0x1036: 47 41 4D 4D 01 02
E14 0x103C: 80 12 90 6C 62 01 63 01 01 A5 01 A9 01 31 01
E14 0x104B: 4C 50 48 61 31 32 34 58 59 5A 01 02 03
```

The modified GAMM description ends1039; final field separator/row terminator move103D/103E→**103A/103B**. LPHa's final field separator/row terminator move1058/1059→**1055/1056**. The list terminator moves105A→**1057**. **1058–13FF is entirely zero**; the newly released three bytes1058–105A are zero-filled. Rows are contiguous, with no gap, tombstone, duplicate/unindexed row or abandoned long GAMMA record in the final supported data page. The shifted LPHa row occurs exactly once. The old address103F is inside its relocated record, not a second record. Logical-file observations do not imply secure host-storage erasure or absence of transient copies.

| Index slot | E11 triple | E14 triple | Meaning |
|---|---|---|---|
| `1428` | `04 00 00 00 10 00` | unchanged | Internal at1000,ID10 |
| `142E` | `04 00 3F 00 12 00` | **`04 00 3C 00 12 00`** | Same LPHa row/ID, updated address103C |
| `1434` | `04 00 27 00 11 00` | unchanged | Shortened GAMM at1027,ID11 |

Only **1430:3F→3C** changes in the entire index page. No index entry is swapped, inserted, cleared or reassigned; all targets still agree with their row IDs. The zero index tail after1439 is unchanged.

### Exhaustive E11 → E14 comparison

Only `DESKMATE/PERSONAL.CLN` changed; the other **125 installed file contents** are identical. No installed files were added or removed. The database remains **6,144 bytes**, with unchanged six candidate1,024bytepages and unchanged page-reference metadata.

Exactly **32 byte positions in four contiguous runs** differ: **103A–1043 (10),1045 (1),1047–105A (20),1430 (1)**. Per candidate page, counts are **0,0,0,0,31,1**. All before/after bytes appear in `ANALYSIS/E11_E14_comparison.json/.md`; the unchanged positions within the shifted data span explain the split runs in an absolute-offset comparison.

The31 data-byte differences implement removal of A45, the following row/list-marker backward shift and cleared tail. The sole index-byte difference retargets that shifted row. No differences remain unexplained. PERSONAL count0435–0439 remains**00003**, including the internal row; candidate next-ID043F–0443 remains**00019**. Both user IDs and the ID set10/11/12 remain unchanged. The full39-byte internal record1000–1026, including100D65, and its index are identical. No file/header, table-counter, schema, allocation, index-header, preference or auxiliary-file byte changes were observed.

### Bounded interpretation relative to E11–E13

E14 is direct evidence of a **packed shrink preserving physical order and record IDs** while adjusting a later record's address. It is consistent with in-place shortening plus compaction or a same-order packed-page rewrite. The particular hypothesis B outcome—moving LPHa to1027 and appending GAMM near1042 with reordered IDs—does not describe this final snapshot.

E11's7→10 growth reversed the two user records' physical order and reassigned IDs; E12's explicit physical-interior deletion moved the survivor and decremented its ID; E13's sole trailing10→7 shrink restored the earlier one-event bytes but could not distinguish update models. E14 shows that **growth, deletion and shrinkage need not have the same final allocation/ID behavior**. A universal claim that every description modification removes the row, renumbers following rows and appends the replacement is inconsistent with E14's final layout. A size-dependent strategy is a plausible hypothesis, not an observed internal routine.

No calls, intermediate states or implementation branches were traced. A more elaborate delete/reinsert routine that reconstructs original order/IDs cannot be ruled out purely from final bytes. This single7→4 shrink with one following row and ample same-page padding does not establish arbitrary lengths, several following rows, all update algorithms, general ID encoding or multi-page behavior. IDs remain snapshot-local references: E14 preserves them, but E11/E12 show they can change on other operations.

### Parser, tests and preservation verification

The existing parser accepted E14 **before any implementation change**, following the changed index target and returning exactly **LPHa124XYZ,2027-11-01Monday09:15–10:15** and **GAMM,2027-11-01Monday11:00–12:00**, plus the separate internal/control row. **Parser and CLI implementations remain byte-for-byte unchanged.** Alarm remains undecoded; alarm off for the edited event was verified in Calendar and all unknown field values were preserved.

Added E14 fixture expectations and two focused regressions: relative three-byte shrink/relocation, stable IDs/physical order, complete unchanged LPHa raw row, other GAMM fields unchanged, index-to-row agreement, unchanged counters/internal row, dynamic list marker/zero tail/no duplicate long row, and both text/JSON listings. Relocation checks derive addresses from E11's parsed records rather than hardcoding E14's row locations in parsing logic.

**55 tests pass across E00–E14**, retaining all prior53 and malformed-input/read-only checks. Actual CLI text/JSON subprocess checks pass. All **1,890 installed-file hashes and exact inventories across15 preserved fixture manifests** match; read-only fixture tests confirm unchanged database bytes/mtime. All existing fixture evidence manifests are verified separately with per-manifest counts in `LOGS/E14_validation.json`.

Reports: `ANALYSIS/E11_E14_comparison.json/.md`, `E14_shrinkage_evidence.json`, `PARSER_E14_listing.txt`, `PARSER_E14.json`, `PARSER_VALIDATION.json`; `LOGS/PARSER_TESTS.txt`, `E14_validation.json`. Prior53-test validation logs retained with `_before_E14` suffix. Updated format/status/test/README documentation; no new database-writing functionality or further experiment.

## Experimentally supported date/time formulas

**Confirmed observations:** 2026-10-23 → `8F 6B 78`; 2026-10-24 → `8F 6B 79`; 2026-11-01 → `8F 6C 62`; 2027-11-01 → `90 6C 62`. E06's month boundary distinguishes component fields from a plain raw serial day counter; E07 independently supports the year increment.

| Field | Candidate rule | Evidence and confidence |
|---|---|---|
| Month at `102A` | `0x61 + month` | Confirmed observed mappings October(10)=6B and November(11)=6C; prospective E06 prediction passed. General rule probable; other months untested |
| Day at `102B` | `0x61 + day` | Confirmed observed mappings 1=62, 23=78, 24=79. General rule probable; remaining days untested |
| DayOfWeek at `102D` | `0x61 + weekday`, Sunday=1 through Saturday=7 | Confirmed Sunday=62, Monday=63, Friday=67, Saturday=68; predicted wrap and year-derived change both passed. Tuesday–Thursday untested |
| Year at `1029` | `0x61 + (year - 1980)` | E07 experimentally confirms 2026=8F, 2027=90 and the predicted +1 increment. The formula fits both values; other years, range limits and boundary behavior remain untested |

The complete proposed component encoding is now **experimentally supported for the tested values**, including the year rule. It is not a fully validated year/month/day range specification. In particular, 1980 itself, leap days, month-end dates and year limits have not been tested. Plain raw little-endian day counting failed E05; plain raw big-endian serial counting failed E06.

For a future read-only record decoder, interpret bytes as **unsigned** and apply the inverse relations:

```text
year    = 1980 + (year_byte - 0x61)
month   = month_byte - 0x61
day     = day_byte - 0x61
weekday = weekday_byte - 0x61     # Sunday=1 ... Saturday=7
```

Validate the resulting calendar date and compare the derived weekday; preserve raw bytes alongside decoded values. Values outside tested ranges are extrapolations, not additional experimental confirmation.

**Confirmed local mappings:** StartTime 09:00 AM is A4 and 09:15 AM is A5; EndTime 10:00 AM is A8 and 10:15 AM is A9. Independent E03 and E04 edits directly identify both time bytes and their +1 increments for the tested +15-minute changes.

**Probable encoding hypothesis:** `0x80 + minutes_since_midnight / 15`. It fits all four observed values and passed prospective predictions for separate start and end edits. It does not yet establish all-day behavior, the bias independently of other affine possibilities, rounding, valid input precision, or handling of non-quarter-hour times. ASCII, BCD and ordinary two-byte DOS packed time are not the literal one-byte representation shown here; a database-level encoding could still transform another representation.

The supported inverse for these timed values is `minutes_since_midnight = 15 * (unsigned_time_byte - 0x80)`; hours/minutes follow division/remainder by 60. Empty/untimed fields, sentinel values, other times and rounding are not yet characterized. These equations document findings; no decoder implementation was added in this run.

## Read-only decoder feasibility — historical assessment before implementation

**Yes: sufficient evidence exists for a conservative decoder of the observed appointment-record subset. No: a general DeskMate Calendar database reader is not yet established. No decoder is implemented here.** The existing fixture validator remains test tooling that asserts known evidence and raw spans; it is not being expanded into a general reader.

A subsequent implementation could accept a verified row from the known PERSONAL schema, retain its raw bytes/ID and offsets, split the observed seven delimited fields, and decode the supported date, weekday, time and short ASCII description values. It should validate lengths/date/weekday/time consistency and report confidence. It must preserve empty Duration, raw Protected and any unknown bytes without assigning untested semantics. Alarm storage has not been independently identified: the UI was always alarm off, so a reader must not invent an alarm flag interpretation.

For database traversal, use validated index targets and schema rather than hardcoding `0x1027`. The internal row at `0x1000` does not fit the normal valid-date pattern and must be returned as opaque/unsupported, not silently treated as an appointment or as proof of deletion. Unexpected row prefixes, identifiers, escaping/control bytes, malformed lengths or out-of-bounds pointers should produce an explicit unsupported/error result rather than guessed output.

The major remaining obstacles to a general reader are multiple live appointment records, record allocation/index enumeration beyond one event, long/multi-byte IDs, deletion/tombstones, linked or growing pages, text escaping/encoding and unsupported field/date/time values. A narrow record decoder could be tested against E01–E07's known outputs (and E00's absence of a user appointment), preserving unknown data. A multi-record experiment is the most useful next step before claiming database-wide coverage. A writer remains out of scope.

## Initial read-only parser — implementation and validation

Implemented on October 30, 2026: `ANALYSIS/SCRIPTS/calendar_personal.py`, separate `calendar_personal_cli.py`, automated `test_calendar_personal.py` and `README_PARSER.md`. This supersedes the earlier proposed implementation milestone; historical E00–E08 experiment conclusions and evidence remain unchanged. No GUI operation or new experiment was performed.

The parser opens files only in binary read mode and bounds reads to the supported 6,144-byte layout plus one byte for oversize detection. It validates magic `03 46 49 4C`, the six-page boundary, observed metadata descriptors, index headers/tails, page/offset bounds, unique IDs/targets, row prefix/index-ID agreement, indexed DBCOLS schema, field counts/widths, row/list framing, row coverage/padding and observed counter relations. Unsupported structures fail with `CalendarParseError` codes/messages/offsets; the CLI exits 2 without a partial listing.

**Structural corroboration across E00–E08:** the table descriptor's zero-based token 2 agrees with the known data page (DBCOLS 2, PERSONAL 4), and token 7 agrees with the corresponding index page (3/5). Those remain page-reference candidates interpreted only within the supported profile; the parser does not infer general table/page allocation. Both index-page headers match four repeats of nine FF bytes plus 00, followed by contiguous six-byte little-endian triples at in-page offset 28 and a zero tail. Each indexed data page consists of contiguous, non-overlapping rows ending in 01 02, followed by 03 and zero padding. All indexed schema targets/IDs and PERSONAL targets/IDs reconcile. This validates use of the profile on these fixtures, not universal marker/allocator semantics.

Individual appointment addresses are resolved from the PERSONAL index triples; there are no hardcoded appointment offsets or description-based searches in parsing logic. A synthetic in-memory test reorders the three E08 physical rows and index entries, moving both appointments and the internal row, and confirms the parser follows updated targets. This is an implementation test, not a new observed DeskMate allocation experiment.

The internal/control row is recognized by ID10 plus the exact observed field signature: Date `20 20 FF`, four empty DayOfWeek/Duration/StartTime/EndTime fields, Protected literal `30`, and description `i[ce]` + twelve ASCII `a` bytes + `@PaSsWoRd@=`. All fields remain opaque. ID10 with another signature is rejected; other rows with invalid dates are not silently hidden as internal rows. The signature covers both E00/E01 and E02–E08 versions and is not a general internal-record classification rule.

Normal output includes IDs, dates, stored weekday, times, printable ASCII descriptions, raw record/index locations, lengths and all raw fields. JSON separates `appointments` and `internal_records`; the text listing explicitly excludes internal rows. The experimentally supported formulas decode only the four observed complete dates, Sunday/Monday/Friday/Saturday and time bytes A4/A5/A8/A9/AC/B0. Other calendar-valid dates or unknown weekday/time values remain null/undecoded with warnings; no speculative extrapolation mode exists. Impossible dates, conflicting decoded weekdays and reversed/overnight times are rejected under this profile. Duration/Protected remain raw even for familiar literals. Alarm has no decoded field. Non-ASCII descriptions remain raw, not guessed text; a declared 120-byte cap is a conservative structural limit, not experimental proof of every description length/encoding. Unknown header bytes are retained, not checksum-validated.

**Validation:** 43 automated tests passed, including all nine fixture cases with exact documented appointment values/counts (E00 zero, E01–E07 one, E08 two), read-only opens and unchanged source bytes/mtime, truncated inputs, invalid/duplicate/hidden index references, corrupt schema/row/list structures, bad dates/weekday consistency, raw preservation of unknown values, row relocation and CLI output/errors. Human/JSON CLI subprocess smoke checks passed. All 1,134 installed-file hashes/inventories across the nine preserved manifests matched after validation; no fixture database or manifest was modified. Evidence: `ANALYSIS/PARSER_VALIDATION.json`, `LOGS/PARSER_TESTS.txt`, `ANALYSIS/PARSER_E08_listing.txt` and `PARSER_E08.json`.

Remaining limits: the six-page/table-role profile, single data/index page per table, low-ID row framing, contiguous allocation/zero-tail indexes, known internal signature, tested date/time values and short ASCII subset. Growth, linked pages, index holes/tombstones, deletion, ID reuse, general text escaping and alarm semantics are unsupported. The count/index agreement and max-ID+1 candidate next-ID relation are profile checks, not universal conclusions.

## Next experiment — E15 proposed only after Phase III-A

Phase III-A's application-verified five-event output now supplies the proposed base. The earlier E14/39-seven-character-addition plan is superseded: the bounded writer rejects tied date/start keys and has only15 unused keys, so7character additions cannot fill the page under current value restrictions. Proposed11 fixed60character appends would leave17bytes; DeskMate would add the twelfth77byte row. Validate the longer descriptions in the pre-boundary application load first. The exact keys, capacity arithmetic, failure gates and application-owned crossing procedure are in `ANALYSIS/PHASE3A_REPORT.md` and the Phase III-A section below. No near-capacity database or E15 was generated/performed here.

## Reproduction and unresolved questions

`ANALYSIS/SCRIPTS/compare_calendar.py` generates JSON and Markdown comparisons using absolute offsets, lengths, hex and ASCII. `validate_first_record.py` checks all eight manifests (1,008 file hashes), exact comparisons, schema literals, field spans, unchanged E03–E07 internal row and index targets, and writes `ANALYSIS/CALENDAR_FIELDS.json`. This is a fixture-specific validator, not a decoder implementation. Run it with installed Python 3.14; no Ghidra or MCP session is required.

Supporting reports: `ANALYSIS/E00_E01_comparison.{json,md}`, `ANALYSIS/E01_E02_comparison.{json,md}`, `ANALYSIS/E02_E03_comparison.{json,md}`, `ANALYSIS/E03_E04_comparison.{json,md}`, `ANALYSIS/E04_E05_comparison.{json,md}`, `ANALYSIS/E05_E06_comparison.{json,md}` and `ANALYSIS/E06_E07_comparison.{json,md}`. `CALENDAR_FIELDS.json` records raw offsets separately from interpretation/confidence. The independent report remains separate, with its hash recorded there.

Remaining questions: untested year/date boundaries and month/day/weekday values; exact meaning of100D and the internal row; full time precision; C/N/K semantics and escaping; full row-ID encoding; page allocation/growth; multiple-event index behavior; counter semantics; checksums; deletion and record reuse. The E00–E07 material above records the earlier experiments; E08 is the sole newly completed experiment in the current continuation. The E08 experiment itself did not implement a parser; the implementation section above documents the subsequent independent read-only milestone.

## Independent revalidation — 2026-10-30

E07 was already preserved when this conversation resumed. Independently verified the exact inventories, sizes and all 1,008 manifest hashes for E00–E07, directly compared all 126 E06/E07 files, reproduced the existing E06_E07 comparison exactly, and reran the existing fixture assertions successfully. Only the two predicted database bytes differ; no unexpected differences were found. Prior recorded visual checks and clean exit are preserved in E07's manifest; they were not independently repeated during this audit. Evidence: `LOGS/E07_revalidation_20261030.json` and its `.py` reproduction script. No decoder or additional experiment was implemented/performed. This audit leaves all experiment snapshots and manifests unchanged.

## E08 decoder feasibility update

E08 supplies the previously missing example of two simultaneously live appointments with independent index entries and preserved original bytes. This supports the proposed narrow read-only enumeration milestone. It does not establish a general DeskMate database/page allocator or complete alarm/date/time/text codecs. New observed time mappings are 11:00 AM = AC and 12:00 PM = B0, consistent with the quarter-hour rule; they came from a new-record addition rather than separate isolated time edits. The earlier single-record feasibility discussion remains historical and its multi-record evidence gap is narrowed by E08, not all remaining format gaps resolved.

E09 adds one supported trailing-deletion fixture without changing parser logic. Broader deletion/tombstone, interior compaction, allocator reuse and variable-length storage remain unresolved. Historical pre-E09 parser limits above are bounded by this newly observed case.

E10 demonstrates same-sized trailing ID/address/index reuse without parser changes. Historical statements that reuse was untested are bounded by the E10 evidence above; interior reuse and variable-length storage remain unresolved.

E11 now provides actual variable-length growth, relocation, index-order/physical-order divergence and reassigned logical-event IDs without parser changes. Historical statements that variable-length storage was untested are bounded by this single7→10case; other lengths, shrinkage, interior deletion, page growth and general allocator behavior remain unresolved.

E12 adds direct evidence for physically interior deletion with survivor compaction/renumbering and a zero-filled freed tail. Earlier historical references to untested interior deletion are superseded by this bounded fixture; non-last logical index deletion, several subsequent rows, shrinkage and multi-page allocation remain untested.

E13 adds directly observed sole-row10→7 shrinkage and exact E07/E09 binary restoration. Earlier historical references to untested shrinkage are now bounded by this case; non-trailing shrinkage, transient update algorithms and page allocation remain unresolved.

E14 adds direct non-trailing7→4 shrinkage with stable IDs/order and following-row compaction. Historical blanket delete/reinsert explanations are limited by this counterexample to the simple append model; actual internal algorithm, several following rows and page allocation remain unresolved.

## Experimental writer reconstruction — 2026-10-31

Isolated `ANALYSIS/SCRIPTS/calendar_writer_poc.py` constructs only the E08 BETA456 appointment from semantic date/time/description values and explicit opaque Duration(empty)/Protected(31) inputs, starting from an E07-like one-event byte snapshot. It does not read E08. Existing parser validates input/output; ID, row address, index position and counter values are calculated from existing rows/metadata. Metadata token positions are located within validated descriptors rather than patching copied E08 ranges. CLI output is a separate new file, opened exclusively; source/pre-existing output overwrite is refused. Known single-page boundaries and low IDs only; capacity checks reject extra pages.

Generated `EXPERIMENTS/WRITER_POC/E07_to_E08/PERSONAL.CLN` is6144bytes and exactly equals independently preserved E08 over every byte, SHA2568a11fecd1d4e61266730602a7fda239edfce22870f509bee66a91e021d1913d6. Calculated new ID12,address103F,length24,index1434; count2→3,next18→19. E07→generated has30 differing positions/6runs. Both original/internal rows remain unchanged. This is synthetic reconstruction evidence, not a new GUI experiment or proof of general write compatibility. No alarm codec is inferred from Protected. Parser/CLI unchanged.

Six focused writer tests plus55 existing parser regressions pass (61total). E07/E08 complete252-file manifests verified and source file bytes/mtimes/manifests unchanged; output artifact manifest verified. Reports WRITER_POC_VALIDATION.json, WRITER_POC_E08_comparison.json/.md, WRITER_POC_input_output_comparison.json; LOGS/WRITER_POC_TESTS.txt. See README_WRITER_POC.md for exact accepted values and rejection behavior. No repeated append, other values/source states, index sorting, edit/delete/compaction, page allocation or application load test implemented. Historical no-writer statements above describe earlier checkpoints; this is a deliberately constrained exception.

Next toward nearly full data: separately validate a bounded repeated fixed-size append variant against application fixtures and establish index ordering for proposed date/time/tie cases, then generate and preserve a last-fitting single-page state while rejecting overflow. Do not extrapolate this single reconstruction into allocator behavior. E15 was not begun and no further features/experiments were performed here.

## Phase III-A: bounded multi-record writer and application acceptance — 2026-10-31

# Phase III-A: bounded multi-record generation and DeskMate validation

Completed October31,2026. No E15, near-capacity database, installations, native
Computer Use diagnostics, broad disassembly or unrelated experiments performed.

The append writer now derives every record ID, physical location, table counter
and page/offset index triple from the parsed source. It keeps old physical records
unchanged, appends a framed new row, updates the list marker/count/next-ID and
inserts chronological index triples. Both page limits, a retained index sentinel
and low-ID framing are checked before any write. Only measured date/time mappings,
non-tied date/start keys and printable ASCII descriptions are accepted. Unknown
Duration/Protected semantics are preserved as explicit supported raw literals;
alarm is not decoded. The read-only parser is unchanged. Output publication uses
a flushed same-directory temporary file and atomic no-overwrite hard link.

Chronological index insertion was an explicit hypothesis before this application
check. Earlier E11/E14 showed physical/index order could differ; they did not
prove a universal sorting rule. This sample validates this ordering for distinct
date/start keys, without showing whether unsorted input would also be accepted.
Ties, unknown codecs, multi-page tables, editing/deletion/compaction remain rejected.

## Exact sample and insertion order

Base: complete verified E07 snapshot; original internal ID10 and LPHa124 retained.
Every user row is24bytes. Addresses below are hexadecimal, times24hour.

| Insertion | Description | Date | Start–end | ID | Physical address | Index slot |
|---:|---|---|---|---|---|---|
| Existing | LPHa124 | 2027-11-01 | 09:15–10:15 | 11 | 1027 | 1440 |
| 1 | BETA456 | 2027-11-01 | 11:00–12:00 | 12 | 103F | 1446 |
| 2 | EARLY26 | 2026-10-23 | 09:00–10:00 | 13 | 1057 | 142E |
| 3 | MID2026 | 2026-11-01 | 10:00–11:00 | 14 | 106F | 143A |
| 4 | LATEOCT | 2026-10-24 | 09:15–10:15 | 15 | 1087 | 1434 |

Physical order: internal,LPHa124,BETA456,EARLY26,MID2026,LATEOCT. Index order:
internal,EARLY26,LATEOCT,MID2026,LPHa124,BETA456. Calendar's checked day schedules
show the expected date and time order; the2027 day shows LPHa124 then BETA456.
Cross-date correctness was checked by Find Date on each of the four dates, not
by inferring a global display list from parser output.

Counter is00006 (five user rows plus internal); next-ID candidate00022 (decimal).
Internal row remains39bytes; used row data is39+5×24=159bytes, list marker03 at109F,
zero padding10A0–13FF. Six index entries occupy36bytes after the40byte header;
index tail begins144C. File is6,144bytes; generated SHA-256:
`e48066b2b78fb73ec414271ae4404468529628c840dfac3f7c374621544bc243`.

## Application verification and roundtrip

Existing emulator was visibly at clean DOS prompt before replacing disposable
RUN with a verified E07 installed-tree copy and independently generated database.
Prior RUN was retained. Full126-file before snapshot was preserved. Existing
SDL1/software profile, foreground-checked Windows keys/native clipboard and
independent full-desktop screenshots were used. Guest date stayedOctober30,2026;
no system-date command or environment configuration change.

All five appointment descriptions, dates and times were visually verified in
Calendar: `P3A_05_early_verified.png`, `P3A_10_late_verified.png`,
`P3A_13_mid_verified.png`, `P3A_16_two_2027_verified.png`. EARLY26 Change Event
showed correct complete values and unchecked alarm (`P3A_06_noop_dialog.png`);
Enter submitted OK with no field changes, and the saved schedule was captured07.
Escape returned cleanly to DOS (`P3A_17_clean_exit.png`) before collection.

Full126-file after snapshot was preserved. Direct comparison found **zero database
byte differences and all126 installed-file contents identical**, no added/removed
files. Generated and closed database hashes match. No records, indexes, counters,
internal bytes or padding were normalized in the observed closed file. Submission
of unchanged OK may be optimized as no write; internal disk-write calls were not
traced. This is application acceptance and observed no-normalization evidence,
not proof of a forced rewrite, arbitrary writer compatibility or allocation rules.

`EXPERIMENTS/PHASE3A/multi_record` preserves generated bytes, insertion sequence,
parser outputs, complete before/after trees/manifests, old sources and evidence.
`ANALYSIS/PHASE3A_roundtrip_comparison.json/.md` records exhaustive comparison;
`PHASE3A_VALIDATION.json` and `LOGS/PHASE3A_TESTS.txt` record final tests/hash audit.
All E00–E14 fixtures and previous PoC evidence remain unchanged.

## Proposed E15: writer-prepared page boundary, application-owned allocation

**Plan only: do not execute as part of Phase III-A.** Use the verified five-event
PhaseIII-A output. Current capacity, reserving list marker and one complete zero
index sentinel:864data bytes,157index entries,106 lowIDs. A seven-character event
uses24bytes, so36 would fit by space, but only15 non-tied date/start keys remain
under this writer's four-date/five-usable-start restriction. Repeated same-time
events are deliberately rejected; do not silently relax that rule to fill a page.

Use fixed60-character ASCII descriptions instead:17framing/field bytes+60=77bytes.
**Eleven** additions require847bytes and leave17bytes. The next77byte appointment
will not fit the observed data page. This is safe under the validated structural
profile; the60character length itself has not yet been application-verified.

Use known dates in chronological order and these allowed start/end pairs:
09:00–10:00,09:15–10:15,10:00–11:00,10:15–11:00,11:00–12:00. Exclude the five
sample keys. The first11 unused keys are:

| Date | Start times (end from pairs above) |
|---|---|
| 2026-10-23 | 09:15,10:00,10:15,11:00 |
| 2026-10-24 | 09:00,10:00,10:15,11:00 |
| 2026-11-01 | 09:00,09:15,10:15 |

Descriptions should be uniquely labeled `FILL001`…`FILL011` padded with literal
ASCII X to exactly60characters. Proposed application-only crossing event:
November1,2026,11:00AM–12:00PM, `BOUND12` padded with X to60characters,alarmoff.
Its date/start key is unused. No file containing these additions was generated.

Proposed procedure:

1. Verify the PhaseIII-A artifact manifest and regenerate only in a new disposable
   output. Append the11 planned events, reject any capacity/schema anomaly, and
   validate parser/manifest. Expected user count16,total count17,nextID00033,
   used rows1006bytes,list marker13EE,17zero bytes13EF–13FF. Seventeen index entries
   use102bytes plus40byte header, leaving882zero bytes and146 append slots with
   sentinel reservation. IDs remain within the low-ID framing range.
2. Clone an isolated installed tree. Load this pre-boundary file in DeskMate;
   inspect existing events and the full new descriptions in dialogs. If Calendar
   rejects, truncates or changes60character data, stop and preserve that evidence;
   do not proceed to an allocation claim. Exit cleanly and preserve the complete
   accepted pre-boundary tree/manifests. Compare any normalization first.
3. Reopen only that accepted copy. Enter the one crossing event through Calendar,
   visually verify full values before saving, then exit cleanly. Preserve complete
   post-boundary tree/manifests even if the application reports an error.
4. Compare every byte/file. Inspect whether Calendar grows/links/moves pages,
   changes descriptors/index targets/IDs, spills a row or rejects the addition.
   Do not assume a seventh page or a specific linkage codec. Current parser must
   reject unsupported layouts; preserve raw evidence before extending it.

A practical large-file generator, tie semantics, long IDs, checksums/opaque fields
and any general writer remain outside this milestone. E15 has not begun.

## Final automated verification

72 tests passed:55 original parser regressions,6 evolved PoC tests (including exact E08 identity),11 multi-record/CLI/application-fixture/capacity/atomic tests. Exact E10 reconstruction also passed. Capacity guard exhaustion uses injected limits rather than producing a forbidden near-full file. All1,890 installed-file hashes/inventories acrossE00–E14 match; all prior evidence manifests and the original PoC artifact manifest match. Both126-file PhaseIII-A snapshot manifests and current evidence hashes match. Parser/CLI implementation hashes remain unchanged. Full per-manifest counts are in PHASE3A_VALIDATION.json.

## E15: observed first extra PERSONAL data page — 2026-10-31

A verified writer-generated 6144-byte preflight database held 17 rows (16 users),
with 17 zero bytes free after the page-4 list marker at 13EE. Calendar displayed
all eleven 60-character generated descriptions, then exited with all126 file
contents unchanged. The user revised the crossing event to exactly BOUND12
(2026-11-01 Sunday,11:00–12:00,alarmoff). Its24-byte row exceeds17free bytes;
the original77-byte proposal also exceeded17 but was never saved.

One application insertion grew the closed file to7168bytes. New page6 starts
1800 with row ID21: `80 21 8F 6C 62 01 62 01 01 AC 01 B0 01 31 01 42 4F 55 4E 44 31 32 01 02`;
03 at1818, then999zeros. Existing index page5 adds `(6,0,21)` encoded
`06 00 00 00 21 00` at1482; two2027 entries shift6bytes right, no old row
relocates or changes ID. The full old data page4 including internal row,03 and
17zero tail is identical. Schema pages2/3 and index header also identical.
Count00017→00018,next-ID candidate00033→00034(decimal); descriptor page numbers
unchanged. Only other old-extent changes are header0026..27 FF8F→006F and
002A..2B F000→8FFF: allocation-associated opaque values, not a decoded page map.
OnlyPERSONAL.CLN changed among126files:14old positions plus1024appended bytes.

This confirms one new whole-row data page addressed through the existing index,
not general page linkage, reuse, allocator or checksum semantics. New-page03
coexists with the unchanged old-page03. The conservative parser intentionally
rejects this seven-page file with unsupported_layout; writer remains bounded.
See the E15 experiment report for exact hashes, all byte runs and evidence.

## E16: deletion leaves a retained, unindexed page-6 row — 2026-10-31

From the fully verified E15 seven-page copy, Calendar removed only BOUND12 via
Event→Remove→This event only. All16survivors were visuallyverified; normalDOSexit
preceded collection. File remains7168bytes, not6144. Exactly11bytes differ from
E15after:0439 38→37(count00018→00017);043D 30→31(opaque token000→001);
index1482/1484/1486 06/00/21→04/27/11,148A/148C 27/11→3F/12,
148E/1490/1492 04/3F/12→00/00/00;1800 80→44. Allotherbytes unchanged.

Candidate next-ID00034(decimal) is retained; maxliveID20hex+1 is33decimal,
so maxliveID+1 is not a universal rule. Opaque descriptor token5(zero-based)
000→001 is associated with this deletion; its meaning remains unconfirmed.
Newprefix44(ASCII D) is consistent with a tombstone but not a general marker
codec. The entire retired row payload,ending0102,03at1818 and999zero tail remain.
No liveindex entry references page6/ID21. Indexpage5 fully matches preflight,
lastslot148E..1493 cleared;17entries. All oldlive rowIDs/addresses/rawbytes and
internalrow1000 unchanged; fullpages2/3/4 unchanged fromE15.

Headerpage0 is entirely unchanged fromE15:0026..27=006F,002A..2B=8FFF.
These values therefore do not simply reverse when the only livepage6row is
removed. File retention is observed; free/allocated/reusable page state and
header/free-list/checksum encodings remain unknown. No new page linkage observed.

Against6144bytepreflight, firstextent differs at0026,0027,002A,002B,043D,0443,
plus1024retainedpagebytes; no byte-perfect restoration. SHA256E16:
818c44af2f351cc764dfd48a82b3d8ae1dd0b5f733c8549dbdd902f67eed05ea.
OnlyPERSONAL.CLN changes among126files againsteitherreference. Both production
reader/writer intentionally reject E16; observed001 andretaineddeletedrows do
not extend supported structures. See E16report for allrawbytes andhypotheses.
