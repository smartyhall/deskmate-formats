# Address Book 3.05: initial reconnaissance and one-contact controls

## Scope and provenance

This is initial research, **not an implemented Address Book format**. Three
independent disposable installations started from the same complete 126-file
verified DeskMate 3.05 baseline. The original source and historical evidence
remain unchanged. A00 and A01 completed in the previous overnight run but were
unpublished. A02 was interrupted after typing, before its final screenshot/save.
Recovery independently identified the same live emulator and verified its values,
then saved that one contact; neither Add nor a partial text batch was replayed.
All three now have complete before/after snapshots, raw comparisons and guards.

The empty source PERSONAL.ADR is **10,240 bytes**, SHA-256
`cb890e6d7ba96fafb5a5d3991e208f4de862bee485f6ce32696e989c97d3394c`.
Its first four bytes are `03 00 00 00`, unlike Calendar's `03 46 49 4C` signature.
The source contains no visible Address Book entries. No proprietary binary,
database, screenshot, help text or memory capture is published with this report.

## Application observations and negative control

`desk address` opened Address Book — All, Total entries: 0. The visible menus
were File, Edit, List, Address and View. Menu inspection showed formatting/printing,
Run/About/Exit, text editing, list creation/deletion/merge, address Add/Copy/Delete,
membership, Find/Find next/Call, and All/By list views. No list, printing, dialing
or data operation was invoked in reconnaissance. Unavailable controls were visibly
disabled in the empty book. Escape closed menus and exited normally to DOS.

**A00:** all 126 file contents and sizes remained identical; no file was added
or removed. PERSONAL.ADR's working modification time changed, but its creation
time did not. Working-file timestamps were recorded before/after application use,
before copying snapshots, so copy-created timestamps are not confused with guest
changes. This control demonstrates that a timestamp change alone is not evidence
of a database-content modification. It does not prove every no-edit operation is
content-neutral. Exact timestamp values and complete inventories remain private.

## Controlled synthetic contacts

Address → Add starts **inline entry**, not a modal Calendar-style dialog. Focus
begins in Title. Tab transitions were observed through First Name, Last Name,
Address, City, State, Zip Code, Company Name and Work Phone. Title and all optional
user fields were left blank. A01 used First `TEST`, Last `USER A`, Work Phone
`202-555-0142`. This is the fictional name TEST USER A expressed in the actual
application fields. Home Phone, dates, notes and membership were not entered.

The complete values were screenshot-verified before completion. Contextual help
was consulted privately. Enter in Work Phone did not save/finish A01; Escape
opened a Save changes before quitting prompt, with Yes selected. **One Yes
submission** saved and exited. A read-only reopen displayed Total entries: 1,
index label USER A, TEST and the correct phone. It exited without another save
prompt. Immediate saved bytes and final bytes after reopening are identical.

Before optional A02 execution, a private plan fixed all values except First Name:
`TESTLONG` (8 ASCII characters) versus `TEST` (4). This specifically tests payload
growth, rather than creating an arbitrary extra record. A02 used a separate copy
of the same original empty baseline, not A01's result. Its one saved contact also
reopened correctly as Total entries: 1, USER A, TESTLONG and the same phone.
Immediate saved and final bytes match. Neither record was edited or deleted.

| Observation | A00 no edit | A01 TEST | A02 TESTLONG |
|---|---|---|---|
| Total user entries displayed | 0 | 1 | 1 |
| File size | 10240 | 10240 | 10240 |
| Files with changed contents | none | PERSONAL.ADR only | PERSONAL.ADR only |
| Changed byte positions from original | 0 | 66 | 70 |
| New framed span | absent | 0x1000–0x103C, 61 bytes | 0x1000–0x1040, 65 bytes |
| Following 03 byte | 0x1000 | 0x103D | 0x1041 |
| Six-byte entry at 0x1428 | zero | `04 00 00 00 10 00` | identical to A01 |

A01 after SHA-256:
`19215ea147c65b259eb963fd240e9931d96e77f92d1001f0f7edf89024076ac8`.
A02 after SHA-256:
`ae216968bce070f7a5d9619b844e20295428dac628984a05d22f203e032d76a6`.

## Measured storage, with interpretation limits

No separate index file changed. In both contact cases only 1,024-byte blocks
1, 4 and 5 differ; this grouping does not establish page semantics for all ADR
files. Header block 0 and all remaining blocks are unchanged. At 0x0431–0x0435,
ASCII 00000 becomes 00001; at 0x043B–0x043F, 00016 becomes 00017. These are
count/next-identifier candidates, consistent with this one-contact operation;
their general rules are unproved. Opaque 000 at 0x0437–0x0439 is unchanged.

The new region begins `80 10`. A six-byte little-endian interpretation of the new
entry gives `(4,0,0x10)`, consistent with a location of 4×1024+0 = 0x1000 and a
candidate identifier 0x10. There is only one live record in each file, so this
does not establish ordering, relocation, allocation or deletion semantics.
Calendar's pre-existing internal row used 0x10; **that role cannot be transferred
to Address Book**, where the newly added visible contact occupies this span.

Splitting the measured payload on 01 yields sixteen fields, followed by 01 02,
then the separate 03 marker. Empty fields occupy no character padding. Zero-based
field observations: field 0 empty; 1 First; 2 Last; 3–7 empty; 8 Work Phone;
9–10 empty; 11 contains Birthday; 12 empty; 13 contains Anniversary; 14 empty;
15 contains `6E` (ASCII n), whose meaning remains unknown. Birthday/Anniversary
were application-written defaults despite no dates being entered. No alarm,
boolean, membership, date or internal-row interpretation is assigned to n.
No length prefix is observed for these strings; this does not prove unrestricted
delimiter use or encoding support beyond the tested ASCII values.

TEST is at 0x1003, USER A at 0x1008 and phone at 0x1014 in A01. A02 inserts
exactly ASCII LONG after TEST at 0x1007; the remaining row and marker shift four
bytes. All bytes outside the record/marker region are identical **between A01
and A02**, including the candidate identifier, counters and index. The longer
record is 65 rather than 61 bytes. This confirms variable-length storage for
this field/value pair, without implementing a codec or assuming every field is
variable length. Both cases use existing space, with no observed file growth.

## Complete fixed-offset changes

The tables enumerate every changed position against the same empty baseline.
All unlisted bytes are identical; EOF is unchanged. No heuristic insertion
alignment or normalization is applied. Raw deltas, raw bytes and full inventories
remain in the private experiment evidence.

### A01_contact

| Offset | Before | After |
|---|---|---|
| `0x0435` | `30` | `31` |
| `0x043F` | `36` | `37` |
| `0x1000` | `03` | `80` |
| `0x1001` | `00` | `10` |
| `0x1002` | `00` | `01` |
| `0x1003` | `00` | `54` |
| `0x1004` | `00` | `45` |
| `0x1005` | `00` | `53` |
| `0x1006` | `00` | `54` |
| `0x1007` | `00` | `01` |
| `0x1008` | `00` | `55` |
| `0x1009` | `00` | `53` |
| `0x100A` | `00` | `45` |
| `0x100B` | `00` | `52` |
| `0x100C` | `00` | `20` |
| `0x100D` | `00` | `41` |
| `0x100E` | `00` | `01` |
| `0x100F` | `00` | `01` |
| `0x1010` | `00` | `01` |
| `0x1011` | `00` | `01` |
| `0x1012` | `00` | `01` |
| `0x1013` | `00` | `01` |
| `0x1014` | `00` | `32` |
| `0x1015` | `00` | `30` |
| `0x1016` | `00` | `32` |
| `0x1017` | `00` | `2D` |
| `0x1018` | `00` | `35` |
| `0x1019` | `00` | `35` |
| `0x101A` | `00` | `35` |
| `0x101B` | `00` | `2D` |
| `0x101C` | `00` | `30` |
| `0x101D` | `00` | `31` |
| `0x101E` | `00` | `34` |
| `0x101F` | `00` | `32` |
| `0x1020` | `00` | `01` |
| `0x1021` | `00` | `01` |
| `0x1022` | `00` | `01` |
| `0x1023` | `00` | `42` |
| `0x1024` | `00` | `69` |
| `0x1025` | `00` | `72` |
| `0x1026` | `00` | `74` |
| `0x1027` | `00` | `68` |
| `0x1028` | `00` | `64` |
| `0x1029` | `00` | `61` |
| `0x102A` | `00` | `79` |
| `0x102B` | `00` | `01` |
| `0x102C` | `00` | `01` |
| `0x102D` | `00` | `41` |
| `0x102E` | `00` | `6E` |
| `0x102F` | `00` | `6E` |
| `0x1030` | `00` | `69` |
| `0x1031` | `00` | `76` |
| `0x1032` | `00` | `65` |
| `0x1033` | `00` | `72` |
| `0x1034` | `00` | `73` |
| `0x1035` | `00` | `61` |
| `0x1036` | `00` | `72` |
| `0x1037` | `00` | `79` |
| `0x1038` | `00` | `01` |
| `0x1039` | `00` | `01` |
| `0x103A` | `00` | `6E` |
| `0x103B` | `00` | `01` |
| `0x103C` | `00` | `02` |
| `0x103D` | `00` | `03` |
| `0x1428` | `00` | `04` |
| `0x142C` | `00` | `10` |


### A02_longer_name

| Offset | Before | After |
|---|---|---|
| `0x0435` | `30` | `31` |
| `0x043F` | `36` | `37` |
| `0x1000` | `03` | `80` |
| `0x1001` | `00` | `10` |
| `0x1002` | `00` | `01` |
| `0x1003` | `00` | `54` |
| `0x1004` | `00` | `45` |
| `0x1005` | `00` | `53` |
| `0x1006` | `00` | `54` |
| `0x1007` | `00` | `4C` |
| `0x1008` | `00` | `4F` |
| `0x1009` | `00` | `4E` |
| `0x100A` | `00` | `47` |
| `0x100B` | `00` | `01` |
| `0x100C` | `00` | `55` |
| `0x100D` | `00` | `53` |
| `0x100E` | `00` | `45` |
| `0x100F` | `00` | `52` |
| `0x1010` | `00` | `20` |
| `0x1011` | `00` | `41` |
| `0x1012` | `00` | `01` |
| `0x1013` | `00` | `01` |
| `0x1014` | `00` | `01` |
| `0x1015` | `00` | `01` |
| `0x1016` | `00` | `01` |
| `0x1017` | `00` | `01` |
| `0x1018` | `00` | `32` |
| `0x1019` | `00` | `30` |
| `0x101A` | `00` | `32` |
| `0x101B` | `00` | `2D` |
| `0x101C` | `00` | `35` |
| `0x101D` | `00` | `35` |
| `0x101E` | `00` | `35` |
| `0x101F` | `00` | `2D` |
| `0x1020` | `00` | `30` |
| `0x1021` | `00` | `31` |
| `0x1022` | `00` | `34` |
| `0x1023` | `00` | `32` |
| `0x1024` | `00` | `01` |
| `0x1025` | `00` | `01` |
| `0x1026` | `00` | `01` |
| `0x1027` | `00` | `42` |
| `0x1028` | `00` | `69` |
| `0x1029` | `00` | `72` |
| `0x102A` | `00` | `74` |
| `0x102B` | `00` | `68` |
| `0x102C` | `00` | `64` |
| `0x102D` | `00` | `61` |
| `0x102E` | `00` | `79` |
| `0x102F` | `00` | `01` |
| `0x1030` | `00` | `01` |
| `0x1031` | `00` | `41` |
| `0x1032` | `00` | `6E` |
| `0x1033` | `00` | `6E` |
| `0x1034` | `00` | `69` |
| `0x1035` | `00` | `76` |
| `0x1036` | `00` | `65` |
| `0x1037` | `00` | `72` |
| `0x1038` | `00` | `73` |
| `0x1039` | `00` | `61` |
| `0x103A` | `00` | `72` |
| `0x103B` | `00` | `79` |
| `0x103C` | `00` | `01` |
| `0x103D` | `00` | `01` |
| `0x103E` | `00` | `6E` |
| `0x103F` | `00` | `01` |
| `0x1040` | `00` | `02` |
| `0x1041` | `00` | `03` |
| `0x1428` | `00` | `04` |
| `0x142C` | `00` | `10` |


## Verification, evidence and next steps

Private evidence: DOSLAB `EXPERIMENTS/ADDRESSBOOK/A00_recon`, `A01_contact` and
`A02_longer_name`, plus recovery sprint status. Complete 126-file source/before/
after manifests and all 14 protected executable/profile/debugger hash-and-mtime
guards pass. Screenshots, actual upstream BIOS MCP replies, raw BIOS bytes,
working timestamp records, plans and immediate saved files remain private.
The source software and baseline database were never modified. The optional
case's long paused live interval is recorded rather than hidden.

Focused private regression assertions protect exact deltas/hashes, the no-edit
negative control, the measured four-byte growth and unchanged Calendar data.
They are observations against external fixtures, not an Address Book reader or
writer. No production Calendar, CI or dependency changes are made.

Next useful experiments: independently vary only Work Phone length, or populate
one previously empty optional field, to discriminate field framing and schema
positions. A two-contact experiment would then be needed for index ordering and
identifier behavior. Deletion, page allocation, non-ASCII, maximum lengths and
shared-engine internals remain untested. No further contacts or codec work were
performed during this initial phase.
