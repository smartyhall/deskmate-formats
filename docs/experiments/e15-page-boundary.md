# E15: first data-page boundary — 2026-10-31

## Result and limits

DeskMate accepted the writer-prepared near-capacity database unchanged, then
accepted one application-entered BOUND12 event. The closed database grew from
6,144 to 7,168 bytes: one additional 1,024-byte page, page 6 at 0x1800. This is
one observed allocation, not a general allocator specification. Production parser
and writer remain unchanged and reject the seven-page result as unsupported.

The owner simplified the crossing event before its sole submission: exactly
`BOUND12`, November 1, 2026, 11:00 AM–12:00 PM, alarm off. Seven description bytes
plus 17 framing/field bytes require 24 bytes, exceeding the 17 available bytes.
The originally proposed 60-character/77-byte event also exceeded 17 bytes, but
was never saved. This amendment changes no pre-boundary fixture or collected
evidence. Long unsaved clipboard entry/focus corrections were inspected, then
the field was cleared and the final short value entered with paced keystrokes.
An approval-service usage-limit interruption occurred before the final revision;
the rejected action was not executed, and later normal review succeeded. No
Computer Use troubleshooting, environment reconfiguration or extra GUI experiment
was performed. Guest Calendar showed October 31, 2026; the event date was verified
explicitly rather than inferred from the guest clock.

## Verified preparation and application gate

All 295 Phase III-A root-manifest entries and both complete 126-file installed
snapshots matched their preserved hashes/inventories. Its generated and closed
databases were identical. The prior disposable RUN was retained; E15 used a
separate copy of the closed Phase III-A tree.

The writer added the eleven planned keys, FILL001..FILL011 each followed by 53
literal X characters, preserving all old row bytes/IDs/locations. Descriptions
are 60 ASCII characters and records 77 bytes. Sixteen users plus the internal row
give count 00017 and next-ID candidate 00033 (decimal); rows occupy 1006 bytes,
list marker 03 at 0x13EE, 17 zero bytes at 0x13EF..0x13FF. IDs 0x16..0x20 are
new; the chronological index has 17 entries and 146 remaining append slots with
a complete zero sentinel reserved. Exact insertion sequence, locations, final
parsed index entries and all fields are retained privately as JSON.

Independent full-desktop screenshots show all eleven complete descriptions
wrapped as 48+12 characters on the October 23/24 and November 1, 2026 schedules,
with their expected dates/times. All five original appointments were visible
on their four dates. FILL001 was inspected in Change Event (head/tail, alarm
off) and submitted unchanged. Calendar exited to DOS normally. All 126 file
contents, including the generated database, were byte-identical after preflight;
no files were added/removed. This passed the gate before BOUND12 was submitted.

## Boundary insertion and exhaustive comparison

The final Add Event screenshot verifies exactly BOUND12, 11/1/2026, 11:00 AM,
12:00 PM, alarm unchecked. One OK submitted it. Find Date then displayed the
saved event alongside FILL009, FILL010, MID2026 and FILL011. Escape returned to
the DOS prompt before the full post-insertion snapshot.

Only PERSONAL.CLN changed; the other 125 installed file contents are identical,
with no added/removed files. There are 14 changed positions in the old 6144-byte
extent and 1024 appended bytes (1038 differing/added positions in 13 raw runs).

| Structure | Observed change |
|---|---|
| Header 0x0026..0x0027 | FF 8F → 00 6F |
| Header 0x002A..0x002B | F0 00 → 8F FF |
| Count 0x0435..0x0439 | 00017 → 00018 (includes internal row) |
| Next-ID candidate 0x043F..0x0443 | 00033 → 00034, decimal |
| Original schema data/index pages 2/3 | Entire pages unchanged |
| Original PERSONAL data page 4 | Entire page unchanged, including all 17 old rows, 03 and 17 trailing zeros |
| PERSONAL index page 5 | Insert new entry at 0x1482, shift last two entries six bytes right |
| New page 6 | New row at 0x1800..0x1817, 03 at 0x1818, 999 zero bytes 0x1819..0x1BFF |

New index bytes at 0x1482..0x1487 are `06 00 00 00 21 00`: the existing
little-endian page/offset/ID interpretation resolves (6,0,0x21) to 0x1800.
LPHa124 moves only in the index, 0x1482→0x1488; BETA456 index 0x1488→0x148E.
Their record locations and IDs do not change. All earlier index entries remain
unchanged. The original 40-byte index header remains identical; 18 live entries
end at 0x1493, followed by 876 zero bytes, retaining a complete zero sentinel.
The chronological order places the 2026 BOUND12 entry before both 2027 events.

The new 24-byte row is:

```text
80 21 8F 6C 62 01 62 01 01 AC 01 B0 01 31 01 42 4F 55 4E 44 31 32 01 02
```

It has ID 0x21; date 2026-11-01, Sunday, start AC=11:00, end B0=noon;
Duration empty and Protected raw ASCII 31, with exact description BOUND12.
Alarm-off is visual evidence; no alarm codec is inferred. Each old complete row
occurs exactly once at its prior address, including the internal row at 0x1000.
No split row, duplicate/abandoned row, relocation or compaction was observed.
The earlier page's terminator and unused bytes were not consumed or replaced.

Page 1 changed only the two counter digits. Its table descriptor page numbers
remain 4 and 5; no additional explicit linkage was observed there or in page 4.
The index now directly targets page 6. The four header changes correlate with
allocation, but bitmap/free-list/checksum/linkage meanings are unproven. Do not
derive a general page-map codec or claim checksums absent from this single case.

Preflight SHA-256:
`ed43356dac2b6351429f785e4b868b4458f6bc1a68f05f447477da30021862a4`.
Closed post-insertion SHA-256:
`42517ab1f90f9e7b6c5cf184219bc301254db33adf3f875a36347237743f1380`.

## Evidence, regression scope and next experiment

The private laboratory E15_data_page_boundary directory contains generated bytes,
insertion sequence, parser/capacity results, source verification, procedure
amendment, complete pre_before/pre_after/after trees and SHA-256 manifests,
screenshots, helpers, exhaustive per-file/per-byte comparison and allocation
analysis. No installed tree, real database or screenshot enters this repository.
The generated/preflight file parses as 16 users; the seven-page result fails
with `unsupported_layout`, as intended. No speculative reader/writer extension
was made. New portable tests use independent synthetic bytes; private regressions
check exact generation/preflight identity, old-page preservation, observed raw
index/new row and safe rejection of the new layout.

Recommend E16, separately authorized: delete only BOUND12 from a verified E15
copy and examine whether page 6 is reclaimed/truncated, whether header bytes
restore, and whether the entire database returns to the preserved preflight
state. This would distinguish page reclamation from merely clearing a row.
No such deletion or additional experiment was performed here.
