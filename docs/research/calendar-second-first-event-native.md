# DeskMate 3.05 — FIRST event in SECOND named calendar

Recorded 2026-11-08. User-uploaded binary evidence, synthetic data only.

## Original file and native source

- Native output, published unchanged: [`native-second-first-event-operator.cln`](../../tests/fixtures/application-generated/calendar/native-second-first-event-operator.cln), original user upload `PERSONAL(3).CLN`.
- Size **10,240 bytes**. SHA-256 **`b9c9a4cae3cffac1bc337f7b378ea25df74efd3b6771e117c6e0fc3f81b77084`**.
- Source: [`native-second-empty-calendar-operator.cln`](../../tests/fixtures/application-generated/calendar/native-second-empty-calendar-operator.cln), 10,240 bytes, SHA-256 `338487558d9992452db15858de1ba9cf790c26abf990ba70b47bbc9dc8d011f5`. This is the exact file previously created by original DeskMate after the operator added empty `SECOND`.
- Operator-reported action: in original DeskMate 3.05 add an ordinary appointment **only** to `SECOND`, date 2026-10-24, 11:00–12:00, description `SECOND ONLY 001`, alarm off, then save/exit. Guest action and save are **operator-reported**. Independently verified evidence here consists of the two full files and byte comparisons, not an instrumented emulator session, complete installed-tree manifest, or independent reopen.

The uploaded original file's Git blob SHA-1 (`8a270493d9aba135cc78ca87e0d7a1796aa000ce`) matches the GitHub-published binary content. The source and output SHA-256 values were independently computed from original uploaded files, then compared.

## Verified changes

| Field | Empty SECOND | After first SECOND event |
| --- | --- | --- |
| File pages | 10 | 10 |
| SECOND rows including configuration | 1 | 2 |
| SECOND ordinary events | 0 | 1 |
| SECOND next record ID | 17 | 18 |
| SECOND data page | 8 | 8 |
| SECOND index page | 9 | 9 |
| PERSONAL appointments | 61 | 61, source bytes unchanged |

The new record is ID **17**, page **8**, in-page offset **39** (file offset `0x2027`), **32 bytes**. It encodes date 2026-10-24, 11:00–12:00, `SECOND ONLY 001`, Protected `31` (alarm off). Its complete record-plus-marker bytes at `0x2027–0x2047` are:

```text
80 11 8F 6B 79 01 68 01 01 AC 01 B0 01 31 01 53
45 43 4F 4E 44 20 4F 4E 4C 59 20 30 30 31 01
02 03
```

Page 9's new six-byte SECOND index entry, at `0x242E`, is `08 00 27 00 11 00`: locator `(8, 39, 17)`. The preexisting SECOND config record index remains `(8,0,16)`.

Exactly **38 byte positions change** relative to the empty-SECOND source:

| File location | Changed positions | Description |
| --- | ---: | --- |
| Page 1 `0x0464`, `0x046E` | 2 | ASCII row count `00001→00002` and next-ID `00017→00018` |
| Page 8 `0x2027–0x2047` | 33 | New event row, followed by new `03` row-list terminator |
| Page 9 `0x242E–0x2433` | 3 | Nonzero bytes of new six-byte index locator |
| Pages 0, 2, 3, 4, 5, 6, 7 | **0** | Exactly unchanged |

The three original PERSONAL data pages (4, 6, 7) and PERSONAL's reorganized index page (5) are **byte-for-byte identical** to the source. This is strong evidence of table-local row/ID/index updates for the observed simple append. ID 17 already exists in PERSONAL, so record IDs are **table-scoped**.

## Interpretation and limits

This is a *native-produced result supplied by the operator*, not an implementation test of our writer. No code in the project is claimed to generate this result yet. The current strict common reader does not yet accept the rebalanced PERSONAL index routing structure in either native two-calendar specimen. Keep both as immutable byte oracles while building safe multitable read and narrowly bounded write support in [issue #81](https://github.com/smartyhall/deskmate-formats/issues/81).

Do not infer full native save/reopen acceptance from operator action reports, arbitrary insertion, deleted-record reclamation, index splitting, table rename/delete, additional page allocation, or alarm firing.
