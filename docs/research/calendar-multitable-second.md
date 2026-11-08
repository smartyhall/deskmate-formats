# DeskMate 3.05 — Native specimen with two named calendars

2026-11-08, America/New_York. **This document describes a user-uploaded native specimen, not a newly generated file or a controlled emulator run by Codex.**

## Direct artifact and provenance

- Published **unaltered** operator-uploaded file: [`native-second-empty-calendar-operator.cln`](../../tests/fixtures/application-generated/calendar/native-second-empty-calendar-operator.cln).
- Original upload name: `PERSONAL(2).CLN`; 10,240 bytes; SHA-256 `338487558d9992452db15858de1ba9cf790c26abf990ba70b47bbc9dc8d011f5`.
- Independently verified source: [`sdk-30-days-allocator-tool-generated.cln`](../../tests/fixtures/application-generated/calendar/sdk-30-days-allocator-tool-generated.cln); 8,192 bytes; SHA-256 `d35b10c8e8f0b04e41cd6d16a27b9825531353b00ab503e94b7abd3a11499106`.
- The operator reports that **all 61 synthetic PERSONAL appointments** and their displayed alarm states appeared correctly in DeskMate 3.05, then that an **additional empty calendar named “Second”** was created in the original application before this file was supplied.
- This report has no independent emulator PID/epoch, detailed action ledger, independently hashed installed input at the guest boundary, installed-tree manifest or reopen test. Creation through the application is **operator-reported**. The uploaded result's exact bytes and comparison are verified.

## Byte-level findings

| Structure | Before | After |
| --- | --- | --- |
| Total pages | 8 | 10 |
| Named calendar count at header offset `0x15` | 1 | 2 |
| Named calendars | `PERSONAL` | `PERSONAL`, `SECOND` |
| `DBCOLS` count | 13 | 20 |
| `DBCOLS` next ID | 29 | 36 |
| `PERSONAL` record count, including config | 62 | 62 |
| `PERSONAL` data chain | 4→6→7 | 4→6→7, unchanged |
| `SECOND` data/index pages | None | 8 / 9 |
| `SECOND` rows | None | 1 configuration row, 0 appointments |
| `SECOND` next ID | None | 17 |

The new `SECOND` descriptor declares seven columns and has its own page 8 data and page 9 index. Its configuration record (ID 16) is an exact byte copy of the existing `PERSONAL` configuration record; its index locator is `(8, 0, 16)`. Seven new `DBCOLS` schema rows have owner `SECOND`. The packed twelve-bit page map marks pages 8 and 9 at `0xFF8` and the next extent marker at entry 10 as `0xFFF`. No old data-chain link was modified.

**Original appointment payload preservation:** pages 4, 6 and 7 are byte-for-byte identical to the source fixture. All **62 PERSONAL index locators** are preserved in the same logical order, including the configuration row.

**Native index maintenance:** page 5 was rewritten: the four index-group slot occupancy changes from `[41,21,0,0]` to `[20,21,21,0]`, without changing logical locator order. The first ten-byte boundary/routing region changes from `ff ff ff ff ff ff ff ff ff 00` to `8f 6b 80 01 68 01 b9 01 bd 01`. The exact trigger/algorithm for rebalancing is not proven by this comparison.

Observed changed-byte counts in original pages 0–7: `5,48,207,28,0,237,0,0`. The native specimen adds exactly two 1,024-byte pages. See [structured evidence](../evidence/calendar-multitable-second.json).

## Current reader compatibility boundary

The existing common `database.parse_bytes` reader rejects this genuine native
specimen with `unsupported_layout` at file offset `0x1400`, because its
originally measured `INDEX_HEADER` constant requires four empty `FF×9/00`
routing-header slots. DeskMate rewrote the PERSONAL index routing boundaries
while preserving all 62 logical index triples. This is a **known reader
limitation, not corruption in the native file**. The fixture is retained
unchanged. A portable regression checks the exact specimen hash and raw
PERSONAL page preservation while explicitly documenting the current parser
rejection; future multi-table read support should replace that rejection test
with successful native parsing and verified table isolation.

## What remains unknown

This specimen establishes the native on-disk existence of two named Calendar tables and their page allocations **for this file**. It does not prove the complete general create/delete/rename algorithm, assignment of active-calendar UI selection or other sidecar settings, case-insensitive name collation, calendar count limits, index partition rules or write persistence after editing appointments. A single-file comparison cannot establish that no other installed files changed.

**Next native evidence:** retain this exact input unchanged; on an independently copied disposable installation, add one synthetic appointment *only to SECOND*, save, close, and return the full resulting `.CLN` and installed-tree hashes. Confirm that `PERSONAL`'s 61 events survive unchanged. This is a proposal, **not** authorization to operate an emulator or mutate guest state.

Related: [issue #81](https://github.com/smartyhall/deskmate-formats/issues/81), [Calendar display issue #71](https://github.com/smartyhall/deskmate-formats/issues/71), [SDK schema study](sdk-calendar-database.md).
