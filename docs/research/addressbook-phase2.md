# Address Book Phase II: independent field controls

## Scope and baseline

This report records application-produced observations, not an Address Book codec.
A03 and A04 each start from a separate copy of the same original empty
126-file installation used in Phase I, not from a contact-bearing result.
Remote main was verified at
`6cdb0f29b02ca09110f61358ddae3759064ec9bd`; previous work was left intact.
The source PERSONAL.ADR is 10,240 bytes, SHA-256
`cb890e6d7ba96fafb5a5d3991e208f4de862bee485f6ce32696e989c97d3394c`.
The complete source and before manifests were verified before launch.

## A03: Work Phone length

Prediction, fixed before input: changing only Work Phone from `202-555-0142`
to `555-0142` would remove four stored bytes and shift the following fields
and terminator, retaining the candidate identifier and index.

Exactly one contact was entered in a fresh disposable installation: First Name
`TEST`, Last Name `USER A`, Work Phone `555-0142`; all optional user fields blank.
The actual inline form and status-bar field names established focus. All populated
values were screenshot-verified before saving. Escape displayed Save changes to
this record before quitting, with Yes selected. One Enter confirmed Yes and
returned to DOS. The immediate file and a complete saved installation snapshot
were preserved before read-only reopening. Reopen displayed Total entries: 1,
USER A, TEST and the exact phone. Escape returned to DOS without a save prompt;
the emulator then exited through DOS. No additional Add, edit or Save occurred.

**Result:** field 8 stores literal ASCII `555-0142`, eight bytes
(`35 35 35 2D 30 31 34 32`) at `0x1014–0x101B`. A01 held twelve bytes
`202-555-0142` at `0x1014–0x101F`. The measured framed span is now
`0x1000–0x1038`, **57 bytes**, versus A01's 61. It still begins `80 10`.
The closing `01 02` is at `0x1037–0x1038`, followed by `03` at `0x1039`
(A01: `01 02` at `0x103B–0x103C`, `03` at `0x103D`). File size remains 10,240.
The shortened phone's hyphen is stored literally; no normalization is observed
for these two tested values. This does not establish general telephone handling.

Removing only A01's four bytes `202-` at `0x1014–0x1017` makes its remaining
record and following marker byte-identical to A03, shifted four bytes earlier.
The four vacated bytes are zero. Every other field is byte-identical after
alignment, including Birthday, Anniversary and `n`; only field 8 differs.
All bytes outside the union of record/marker spans are identical between A01
and A03. Fixed-offset comparison has 41 differences between A01 and A03;
this is distinct from the four-byte logical removal.

There are still sixteen measured fields and sixteen `01` bytes, including the
final delimiter before `02`. The six-byte index at `0x1428` remains
`04 00 00 00 10 00`, consistent with `(page 4, offset 0, ID 0x10)` and address
`0x1000`. The count candidate `0x0431–0x0435` changes `00000` to `00001`;
next-ID candidate `0x043B–0x043F` changes `00016` to `00017`.
Opaque `000` at `0x0437–0x0439` remains unchanged. All are identical to A01.
Only blocks 1, 4 and 5 (grouped in 1,024 bytes) change from the empty baseline;
header block 0 remains identical. This does not establish general page semantics.

A03 after SHA-256:
`81b48761fce08c57cbe43a3bb0a23fc4f7d2faee0cdb800375c9175220787d5d`.
There are 62 changed positions against the empty baseline and no file growth.
All 126 complete saved/final files match byte-for-byte; only PERSONAL.ADR changes
from the original 126-file installation. In particular PERSONAL.CLN stays
`e48066b2b78fb73ec414271ae4404468529628c840dfac3f7c374621544bc243`.

## A04: populate City independently

Prediction, recorded after the pushed A03 checkpoint and before A04 input:
populating City with five ASCII characters would grow the record by five bytes
without changing delimiter order/count. A fresh original-baseline copy received
one contact: First TEST, Last USER A, City METRO, Work Phone 202-555-0142.
The status bar explicitly identified City before typing. The actual form showed
all four complete values before Escape; its verified Yes prompt was confirmed
once. A full saved snapshot and immediate ADR preceded read-only reopening.
Reopen showed exactly one correct contact, including METRO. Escape returned to
DOS without another save prompt; DOS exit closed the disposable emulator.

**Result:** formerly empty field **4** contains `METRO`, five literal bytes
`4D 45 54 52 4F` at `0x1010–0x1014`. The record is **66 bytes**,
`0x1000–0x1041`; closing `01 02` is at `0x1040–0x1041`, followed by `03` at
`0x1042`. Work Phone remains the same twelve literal bytes, shifted to
`0x1019–0x1024`. The sixteen fields/delimiters keep their order; all fifteen
other field values, both prefix bytes, defaults, counters and the entire index
match A01. Inserting only METRO before A01's `0x1010` delimiter reproduces the
new record/marker; all subsequent bytes move five positions, consuming five
zero bytes. Nothing outside the union `0x1000–0x1042` changes versus A01.
This confirms City for this specific field/value pair, not every optional field.

File size remains 10,240. There are 71 fixed-offset differences from baseline,
51 from A01. Only blocks 1, 4 and 5 change from baseline; header block 0 is stable.
All 126 saved/reopened file contents are identical, including immediate ADR.
The other 125 original installation files, including Calendar, are unchanged.
All fourteen original executable/profile/server hash-and-mtime guards pass.
A04 SHA-256: `2584874c957d74b0c1240ebc0d02a50ac4c886a53b977749cb912e1628cce46f`.
Complete private evidence mirrors A03 under DOSLAB
`EXPERIMENTS/ADDRESSBOOK/PHASE2/A04_city`.

## Input and preservation evidence

The keyboard catalog initially lacked doslab_keys; a later tool update exposed
its five registered tools before guest input. Attachment identified the intended
disposable PID and keyboard injection capability. **Actual input used the registered
BIOS keyboard MCP**, not the SDK fallback. Each subsequent A03 batch and every
A04 batch has raw replies
and before/after BIOS ring evidence, with an empty ring checked before input.
A local evidence-serialization error occurred after the launch command; the
application and BIOS ring were inspected, and that command was never replayed.
Its launch reply was not preserved privately. This logging gap does not affect
the contact-entry/save replies or independent before/after evidence.

The computer-use screenshot helper failed bounded recovery before entry. The
existing private read-only capture script was used instead; it validates process
creation identity and window bounds, captures without activation, and sends no
input. No host keyboard simulation, AUTOTYPE, rebuilding, database patching,
configuration changes or debugger replacement was used. The pinned upstream
checkout and original Codex configuration were verified unchanged.

Private evidence is under DOSLAB `EXPERIMENTS/ADDRESSBOOK/PHASE2/A03_work_phone`:
`before`, `saved`, `after`, `run`, complete manifests, `comparison.json`,
`baseline_fixed_offset_delta.json`, `A01_fixed_offset_delta.json`, `analysis.json`,
working timestamp inventories, identity, screenshots, immediate saved ADR and
registered MCP reply/BIOS records in `evidence`. Original source and all fourteen
executable/profile/server hash-and-mtime guards pass after clean exit.
The debugger ping reports no connected guest after normal emulator shutdown;
its executable and configuration are preserved. No private artifacts are published.

## A00–A04 comparison

Each baseline is 10,240 bytes; each final file is also 10,240. Counter values below
are the ASCII count/next-ID candidates, not established general semantics.
Lengths count stored ASCII characters. A00 contains no framed contact.

| Case | Baseline bytes | Final bytes | Contacts | Record bytes | First length | Work length | City length | Record address | Index location / ID | Count / next | Final SHA-256 |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| A00_recon | 10240 | 10240 | 0 | absent | 0 | 0 | 0 | absent | zero / absent | 00000 / 00016 | `cb890e6d7ba96fafb5a5d3991e208f4de862bee485f6ce32696e989c97d3394c` |
| A01_contact | 10240 | 10240 | 1 | 61 | 4 | 12 | 0 | 0x1000 | 0x1428 / 0x10 | 00001 / 00017 | `19215ea147c65b259eb963fd240e9931d96e77f92d1001f0f7edf89024076ac8` |
| A02_longer_name | 10240 | 10240 | 1 | 65 | 8 | 12 | 0 | 0x1000 | 0x1428 / 0x10 | 00001 / 00017 | `ae216968bce070f7a5d9619b844e20295428dac628984a05d22f203e032d76a6` |
| A03_work_phone | 10240 | 10240 | 1 | 57 | 4 | 8 | 0 | 0x1000 | 0x1428 / 0x10 | 00001 / 00017 | `81b48761fce08c57cbe43a3bb0a23fc4f7d2faee0cdb800375c9175220787d5d` |
| A04_city | 10240 | 10240 | 1 | 66 | 4 | 12 | 5 | 0x1000 | 0x1428 / 0x10 | 00001 / 00017 | `2584874c957d74b0c1240ebc0d02a50ac4c886a53b977749cb912e1628cce46f` |

## Confirmed, likely and unknown

**Confirmed:** independent one-contact files demonstrate variable-length storage
for First Name, Work Phone and the tested formerly empty City position. Work
Phone retains the tested punctuation literally. Fields 1, 2, 4 and 8 correspond
to First, Last, City and Work Phone in these contacts. All four contact cases
have sixteen `01` delimiters, prefix `80 10`, suffix `01 02`, a following `03`,
and the same six-byte index. Defaults Birthday/Anniversary and byte `6E` remain
stable. Every experiment used the same empty source; no result was an edit of
another experiment. No file-size growth occurred.

**Likely:** the ordered positions correspond to the inline form schema, with
count and next-ID candidates reflecting one insertion. Untested labels below
are candidates from observed UI traversal, not isolated payload demonstrations.
The following `03` may act as an end marker, but general framing/allocation
semantics require further controls.

| Zero-based position | Observed value or candidate role | Evidence status |
|---:|---|---|
| 0 | empty; candidate Title | likely label, unpopulated |
| 1 | TEST / TESTLONG; First Name | confirmed |
| 2 | USER A; Last Name | confirmed observed association; length not varied |
| 3 | empty; candidate Address | likely label, unpopulated |
| 4 | empty / METRO; City | confirmed A04 |
| 5 | empty; candidate State | likely label, unpopulated |
| 6 | empty; candidate Zip Code | likely label, unpopulated |
| 7 | empty; candidate Company Name | likely label, unpopulated |
| 8 | 202-555-0142 / 555-0142; Work Phone | confirmed A03 |
| 9 | empty; candidate Home Phone | likely label, unpopulated |
| 10 | empty | unknown |
| 11 | Birthday | confirmed application-written default text |
| 12 | empty | unknown |
| 13 | Anniversary | confirmed application-written default text |
| 14 | empty | unknown |
| 15 | n (`6E`) | confirmed byte, unknown meaning |

**Unknown:** general telephone normalization, non-ASCII encoding, delimiter
escaping, field limits, dates, `n`, lists/membership, two-contact IDs/index order,
deletions, allocation and general format rules. Similar Calendar structures do
not establish a shared database engine. No general parser/writer is implemented.

Best next discriminating Phase III experiment: from a fresh empty book, insert
two distinct synthetic contacts in reverse alphabetical last-name order, checking
and saving each once. Compare record placement/IDs with index order and displayed
order. This can distinguish insertion ordering from name ordering; it would not
by itself establish the full identifier allocator. It was not attempted here.

## Benchmark scope

This run produced two independent, fully saved/reopened field controls and two
public checkpoints. Phase I produced a no-edit control and two independent
contact files, including its first-name length control. Phase II therefore adds
two targeted field results with the same number of controlled contact insertions,
plus exhaustive comparisons and external-fixture regressions. This is a research
output comparison, not a measured efficiency or cost ratio. Credit balance and
monetary cost remain for the owner's external before/after observation; no account
billing operation or artificial resource consumption was performed.

## Exhaustive fixed-offset comparisons

All offsets are zero-based. These tables list every differing byte; all unlisted
positions and EOF are identical. No heuristic alignment or normalization is used.
Machine-readable complete deltas remain private.

### A03 versus baseline

| Offset | Before | A03 |
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
| `0x1014` | `00` | `35` |
| `0x1015` | `00` | `35` |
| `0x1016` | `00` | `35` |
| `0x1017` | `00` | `2D` |
| `0x1018` | `00` | `30` |
| `0x1019` | `00` | `31` |
| `0x101A` | `00` | `34` |
| `0x101B` | `00` | `32` |
| `0x101C` | `00` | `01` |
| `0x101D` | `00` | `01` |
| `0x101E` | `00` | `01` |
| `0x101F` | `00` | `42` |
| `0x1020` | `00` | `69` |
| `0x1021` | `00` | `72` |
| `0x1022` | `00` | `74` |
| `0x1023` | `00` | `68` |
| `0x1024` | `00` | `64` |
| `0x1025` | `00` | `61` |
| `0x1026` | `00` | `79` |
| `0x1027` | `00` | `01` |
| `0x1028` | `00` | `01` |
| `0x1029` | `00` | `41` |
| `0x102A` | `00` | `6E` |
| `0x102B` | `00` | `6E` |
| `0x102C` | `00` | `69` |
| `0x102D` | `00` | `76` |
| `0x102E` | `00` | `65` |
| `0x102F` | `00` | `72` |
| `0x1030` | `00` | `73` |
| `0x1031` | `00` | `61` |
| `0x1032` | `00` | `72` |
| `0x1033` | `00` | `79` |
| `0x1034` | `00` | `01` |
| `0x1035` | `00` | `01` |
| `0x1036` | `00` | `6E` |
| `0x1037` | `00` | `01` |
| `0x1038` | `00` | `02` |
| `0x1039` | `00` | `03` |
| `0x1428` | `00` | `04` |
| `0x142C` | `00` | `10` |

### A03 versus A01

| Offset | Before | A03 |
|---|---|---|
| `0x1014` | `32` | `35` |
| `0x1015` | `30` | `35` |
| `0x1016` | `32` | `35` |
| `0x1018` | `35` | `30` |
| `0x1019` | `35` | `31` |
| `0x101A` | `35` | `34` |
| `0x101B` | `2D` | `32` |
| `0x101C` | `30` | `01` |
| `0x101D` | `31` | `01` |
| `0x101E` | `34` | `01` |
| `0x101F` | `32` | `42` |
| `0x1020` | `01` | `69` |
| `0x1021` | `01` | `72` |
| `0x1022` | `01` | `74` |
| `0x1023` | `42` | `68` |
| `0x1024` | `69` | `64` |
| `0x1025` | `72` | `61` |
| `0x1026` | `74` | `79` |
| `0x1027` | `68` | `01` |
| `0x1028` | `64` | `01` |
| `0x1029` | `61` | `41` |
| `0x102A` | `79` | `6E` |
| `0x102B` | `01` | `6E` |
| `0x102C` | `01` | `69` |
| `0x102D` | `41` | `76` |
| `0x102E` | `6E` | `65` |
| `0x102F` | `6E` | `72` |
| `0x1030` | `69` | `73` |
| `0x1031` | `76` | `61` |
| `0x1032` | `65` | `72` |
| `0x1033` | `72` | `79` |
| `0x1034` | `73` | `01` |
| `0x1035` | `61` | `01` |
| `0x1036` | `72` | `6E` |
| `0x1037` | `79` | `01` |
| `0x1038` | `01` | `02` |
| `0x1039` | `01` | `03` |
| `0x103A` | `6E` | `00` |
| `0x103B` | `01` | `00` |
| `0x103C` | `02` | `00` |
| `0x103D` | `03` | `00` |

### A04 versus baseline

| Offset | Before | A04 |
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
| `0x1010` | `00` | `4D` |
| `0x1011` | `00` | `45` |
| `0x1012` | `00` | `54` |
| `0x1013` | `00` | `52` |
| `0x1014` | `00` | `4F` |
| `0x1015` | `00` | `01` |
| `0x1016` | `00` | `01` |
| `0x1017` | `00` | `01` |
| `0x1018` | `00` | `01` |
| `0x1019` | `00` | `32` |
| `0x101A` | `00` | `30` |
| `0x101B` | `00` | `32` |
| `0x101C` | `00` | `2D` |
| `0x101D` | `00` | `35` |
| `0x101E` | `00` | `35` |
| `0x101F` | `00` | `35` |
| `0x1020` | `00` | `2D` |
| `0x1021` | `00` | `30` |
| `0x1022` | `00` | `31` |
| `0x1023` | `00` | `34` |
| `0x1024` | `00` | `32` |
| `0x1025` | `00` | `01` |
| `0x1026` | `00` | `01` |
| `0x1027` | `00` | `01` |
| `0x1028` | `00` | `42` |
| `0x1029` | `00` | `69` |
| `0x102A` | `00` | `72` |
| `0x102B` | `00` | `74` |
| `0x102C` | `00` | `68` |
| `0x102D` | `00` | `64` |
| `0x102E` | `00` | `61` |
| `0x102F` | `00` | `79` |
| `0x1030` | `00` | `01` |
| `0x1031` | `00` | `01` |
| `0x1032` | `00` | `41` |
| `0x1033` | `00` | `6E` |
| `0x1034` | `00` | `6E` |
| `0x1035` | `00` | `69` |
| `0x1036` | `00` | `76` |
| `0x1037` | `00` | `65` |
| `0x1038` | `00` | `72` |
| `0x1039` | `00` | `73` |
| `0x103A` | `00` | `61` |
| `0x103B` | `00` | `72` |
| `0x103C` | `00` | `79` |
| `0x103D` | `00` | `01` |
| `0x103E` | `00` | `01` |
| `0x103F` | `00` | `6E` |
| `0x1040` | `00` | `01` |
| `0x1041` | `00` | `02` |
| `0x1042` | `00` | `03` |
| `0x1428` | `00` | `04` |
| `0x142C` | `00` | `10` |

### A04 versus A01

| Offset | Before | A04 |
|---|---|---|
| `0x1010` | `01` | `4D` |
| `0x1011` | `01` | `45` |
| `0x1012` | `01` | `54` |
| `0x1013` | `01` | `52` |
| `0x1014` | `32` | `4F` |
| `0x1015` | `30` | `01` |
| `0x1016` | `32` | `01` |
| `0x1017` | `2D` | `01` |
| `0x1018` | `35` | `01` |
| `0x1019` | `35` | `32` |
| `0x101A` | `35` | `30` |
| `0x101B` | `2D` | `32` |
| `0x101C` | `30` | `2D` |
| `0x101D` | `31` | `35` |
| `0x101E` | `34` | `35` |
| `0x101F` | `32` | `35` |
| `0x1020` | `01` | `2D` |
| `0x1021` | `01` | `30` |
| `0x1022` | `01` | `31` |
| `0x1023` | `42` | `34` |
| `0x1024` | `69` | `32` |
| `0x1025` | `72` | `01` |
| `0x1026` | `74` | `01` |
| `0x1027` | `68` | `01` |
| `0x1028` | `64` | `42` |
| `0x1029` | `61` | `69` |
| `0x102A` | `79` | `72` |
| `0x102B` | `01` | `74` |
| `0x102C` | `01` | `68` |
| `0x102D` | `41` | `64` |
| `0x102E` | `6E` | `61` |
| `0x102F` | `6E` | `79` |
| `0x1030` | `69` | `01` |
| `0x1031` | `76` | `01` |
| `0x1032` | `65` | `41` |
| `0x1033` | `72` | `6E` |
| `0x1034` | `73` | `6E` |
| `0x1035` | `61` | `69` |
| `0x1036` | `72` | `76` |
| `0x1037` | `79` | `65` |
| `0x1038` | `01` | `72` |
| `0x1039` | `01` | `73` |
| `0x103A` | `6E` | `61` |
| `0x103B` | `01` | `72` |
| `0x103C` | `02` | `79` |
| `0x103D` | `03` | `01` |
| `0x103E` | `00` | `01` |
| `0x103F` | `00` | `6E` |
| `0x1040` | `00` | `01` |
| `0x1041` | `00` | `02` |
| `0x1042` | `00` | `03` |

## Delimiter locations in measured contact spans

Positions below include the final `01` before `02`.

| Delimiter ordinal | A01 | A02 | A03 | A04 |
|---:|---|---|---|---|
| 0 | `0x1002` | `0x1002` | `0x1002` | `0x1002` |
| 1 | `0x1007` | `0x100B` | `0x1007` | `0x1007` |
| 2 | `0x100E` | `0x1012` | `0x100E` | `0x100E` |
| 3 | `0x100F` | `0x1013` | `0x100F` | `0x100F` |
| 4 | `0x1010` | `0x1014` | `0x1010` | `0x1015` |
| 5 | `0x1011` | `0x1015` | `0x1011` | `0x1016` |
| 6 | `0x1012` | `0x1016` | `0x1012` | `0x1017` |
| 7 | `0x1013` | `0x1017` | `0x1013` | `0x1018` |
| 8 | `0x1020` | `0x1024` | `0x101C` | `0x1025` |
| 9 | `0x1021` | `0x1025` | `0x101D` | `0x1026` |
| 10 | `0x1022` | `0x1026` | `0x101E` | `0x1027` |
| 11 | `0x102B` | `0x102F` | `0x1027` | `0x1030` |
| 12 | `0x102C` | `0x1030` | `0x1028` | `0x1031` |
| 13 | `0x1038` | `0x103C` | `0x1034` | `0x103D` |
| 14 | `0x1039` | `0x103D` | `0x1035` | `0x103E` |
| 15 | `0x103B` | `0x103F` | `0x1037` | `0x1040` |

## Checkpoint validation

A03 checkpoint: 3 new private tests and 3 Phase I tests passed against preserved
fixtures; 65 portable tests passed. Ruff passed for the new Python test file.
REUSE/SPDX lint passed (73/73 files); repository privacy audit passed (152 files).
All A00/A01/A02 sealed evidence was independently rehashed unchanged (443/508/451
files). Full A03 manifests and all fourteen guards passed. Tests and raw outputs
remain private alongside the evidence. No billing or credit balance was read;
the owner's external before/after readings are the monetary benchmark.


Final A04 checkpoint: **5 Phase II private tests and 3 Phase I private tests
passed, 0 failed**, against actual external fixtures, including complete
before/saved/after manifest checks for both new experiments. The 65 portable
tests passed at A03; they were not unnecessarily repeated after changes limited
to documentation and private fixture assertions. Ruff passed for the changed
Python file; REUSE passed (73/73); the final privacy audit passed (152 files).
The first final privacy attempt detected a document encoding error, corrected
before the successful rerun; both logs remain private. No test failure was hidden.

A03 was committed and remote-verified before A04 preparation:
`0905c6d4f7d574a5e73ecae5e40be1f1834176a8` on `research/addressbook-phase2`.
No pull request was created or merged. No production code, dependency, packaging,
old fixture or original installation was changed. Restart/handoff instructions
are private in `EXPERIMENTS/ADDRESSBOOK/PHASE2/SPRINT_STATUS.md`; no live guest
or unsaved contact remains. The completed branch is left for owner review.
