# E17: append after a retained deleted record — 2026-11-01

## Result

Calendar **did not reuse the deleted record's slot or ID**. It appended the
24-byte REUSE17 record at **0x1818**, the previous page-6 list marker, with new
ID **0x22**. The original 24-byte retired BOUND12 span at 0x1800 is unchanged,
including leading44 and historical ID21; neither its address nor ID is indexed.
The retained page is used again, but its retired record storage is not reclaimed
by this insertion. No new page is allocated; the file remains **7,168 bytes**.

Exactly **35 byte positions** change in PERSONAL.CLN. The other125 files are
byte-identical, with no files added or removed. All17 original indexed rows
(16 appointments plus the internal row) retain their raw bytes, IDs and physical
locations. Only the final two original index entries move to later index slots.
This is one observed insertion, not a general free-list or allocation algorithm.

## Baseline, operation and evidence

The complete E16 post-deletion126-file manifest and exact database were verified
before independent before/run copies were made. Source and preserved before:
7,168 bytes, SHA-256
`818c44af2f351cc764dfd48a82b3d8ae1dd0b5f733c8549dbdd902f67eed05ea`.
Before observations independently confirm17live index triples, count00017,
opaque token001, next-ID candidate00034, deleted prefix44 at1800 and03at1818.
The original E16 and earlier evidence were never mounted writable or modified.

Branch `experiment/e17-reuse` starts at main
`0697693021f1d465b984e3197ac3afe85a6491f5`, independently of the unmerged keyboard
branch. The [keyboard prerequisite checkpoint](https://github.com/smartyhall/deskmate-formats/commit/90738e11ec7af4e482636a7a1f6a97192d1918a4)
demonstrated direct date replacement and full unfocused operation. This experiment
uses the pinned upstream BIOS-input server through the local stdio SDK; newly
registered Codex tools are not claimed active. No host keyboard simulation,
AUTOTYPE, emulator replacement or debugger memory write was used.

Find Date11012026 displayed the four survivors FILL009, FILL010, MID2026 and
FILL011, without BOUND12. Event opened with no item selected: Enter alone made
no change; Down selected Add, then Enter opened one Add Event dialog. Initial
Start/End fields were blank, AM options selected, date11/1/2026 and alarm unchecked.
Start1100 entered11:00; Tab visited its AM/PM group and then End Time. End1200,
Tab and Right focused PM; **Space actually selected PM**. This distinction was
checked visually. Tab reached Description; exactly REUSE17 was entered. Tab
passed the alarm without toggling it, then reached OK.

Before the sole submission, an independent screenshot verified **November1,2026,
11:00AM–12:00PM, REUSE17, alarm off**. One Enter submitted it. The day schedule
showed REUSE17 once alongside all four previous events. Subsequent non-editing
Find Date checks displayed the five October23 events, five October24 events and
LPHa124/BETA456 on November1,2027, all with their established values. Thus all16
survivors were visually present as well as independently compared in binary.
Calendar exited normally to DOS, then the emulator exited normally before the
complete after snapshot. No corrective second insertion, deletion or edit occurred.

Twenty-seven numbered screenshots, actual per-operation MCP requests/replies,
raw BIOS captures, scripts, complete before/run/after installations and SHA-256
manifests remain private under DOSLAB
`EXPERIMENTS/PHASE2/E17_deleted_reuse`. All14original emulator/profile/debugger
executable hash-and-mtime guards and the complete source manifest pass afterward.

After SHA-256:
`a220b4657e85e0d9986975ca6ab741296f986ed617326a26b2cf73e1bde0bae1`.

## Structural observations

| Item | E16 before | E17 after |
|---|---|---|
| File size/pages |7168 / seven1024-byte pages|unchanged|
| Count0435..0439 |00017|00018|
| Opaque token043B..043D |001|001|
| Next-ID candidate043F..0443 |00034 decimal|00035 decimal|
| Retired row1800..1817 |44 / ID21 / BOUND12|all24bytes unchanged, still unindexed|
| New live row |absent|1818..182F, length24, ID22, REUSE17|
| Byte1818 |03 list marker|80 live-row prefix|
| New list marker |not applicable|03at1830|
| Page6 zero tail |999bytes after1818|975bytes after1830|
| New index entry |absent|1482: `(6,0018,0022)`, bytes `06 00 18 00 22 00`|
| LPHa124 index |1482: `(4,0027,0011)`|same triple at1488|
| BETA456 index |1488: `(4,003F,0012)`|same triple at148E|
| Index zero tail |882bytes from148E|876bytes from1494|

The other15 original index triples keep their slots and values. Every original
triple still resolves to the identical record address/ID/raw bytes. The whole
original PERSONAL data page4, schema pages2/3 and header page0 are unchanged.
The internal row at1000 is unchanged. Only1024-byte blocks1,5,6 differ.
Header0026..0027 remains006F and002A..002B remains8FFF; no descriptor change or
new page linkage is observed. Their numeric semantics remain unknown.

The new row's seven raw schema fields are date8F6C62, weekday62, empty Duration,
startAC, endB0, Protected31 and ASCII REUSE17. The visible alarm was off, but this
does not identify an alarm byte: Duration/Protected interpretations remain opaque.
The new ID equals the prior decimal next-ID candidate34 and the candidate advances
to35 in this operation. This does not restore max-live-ID+1 as a universal rule;
E16 remains a counterexample before insertion.

## Exhaustive fixed-offset differences

There are no size/appended/removed ranges. The table lists every changed byte;
all unlisted positions are identical. Raw machine-readable deltas and page hashes
remain private. No heuristic insertion alignment was used.

| Offset | E16 | E17 |
|---|---|---|
| `0x0439` | `37` | `38` |
| `0x0443` | `34` | `35` |
| `0x1482` | `04` | `06` |
| `0x1484` | `27` | `18` |
| `0x1486` | `11` | `22` |
| `0x148A` | `3F` | `27` |
| `0x148C` | `12` | `11` |
| `0x148E` | `00` | `04` |
| `0x1490` | `00` | `3F` |
| `0x1492` | `00` | `12` |
| `0x1818` | `03` | `80` |
| `0x1819` | `00` | `22` |
| `0x181A` | `00` | `8F` |
| `0x181B` | `00` | `6C` |
| `0x181C` | `00` | `62` |
| `0x181D` | `00` | `01` |
| `0x181E` | `00` | `62` |
| `0x181F` | `00` | `01` |
| `0x1820` | `00` | `01` |
| `0x1821` | `00` | `AC` |
| `0x1822` | `00` | `01` |
| `0x1823` | `00` | `B0` |
| `0x1824` | `00` | `01` |
| `0x1825` | `00` | `31` |
| `0x1826` | `00` | `01` |
| `0x1827` | `00` | `52` |
| `0x1828` | `00` | `45` |
| `0x1829` | `00` | `55` |
| `0x182A` | `00` | `53` |
| `0x182B` | `00` | `45` |
| `0x182C` | `00` | `31` |
| `0x182D` | `00` | `37` |
| `0x182E` | `00` | `01` |
| `0x182F` | `00` | `02` |
| `0x1830` | `00` | `03` |

## Interpretation, limits and next experiment

Confirmed: this equal-length replacement-size insertion appends to the retained
page and uses a fresh ID, leaving the retired span intact. It does not physically
reuse the old24-byte slot even though its own row is also24bytes. The opaque001
token persists alongside the retired row; that association does not prove a deleted
record count or free-list meaning. This result does not say what happens under
space pressure, with multiple holes, or on another page/application/version.

The next discriminating pair starts **independently from E16 twice**: a3-character
description (20-byte row, fitting the retired24-byte span but exceeding page4's17
remaining bytes) and a20-character description (37-byte row, exceeding that span
but well inside the previously demonstrated60-character input length). Hold date,
11AM–noon and alarm-off fixed. This tests whether size changes slot choice without
confounding a record that fits the original data page. No E17 result is a baseline
for those variants. General allocation/writing remains unimplemented.

## Verification scope

Focused private regression tests check the complete35-position delta, checksums,
index insertion, retained retired span, stable original rows and continued runtime
rejection of seven-page inputs. They use external original fixtures, not public
binary data. Production parser/writer and CI are unchanged. Checks executed for
this branch are recorded in the sprint checkpoint; no unexecuted historical suite
or hosted CI result is claimed.

Local verification: **3 focused E17 private tests passed**, **65 portable tests passed** once on Windows Python3.13, and Ruff passed for the new test file. REUSE/SPDX and content audits are required before push; no historical laboratory suite or hosted matrix result is claimed.
