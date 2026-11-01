# Address Book Phase II: independent field controls

## Scope and baseline

This report records application-produced observations, not an Address Book codec.
A03 starts from the same original empty 126-file installation used in Phase I,
not from a contact-bearing result. Remote main was verified at
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

## Input and preservation evidence

The keyboard catalog initially lacked doslab_keys; a later tool update exposed
its five registered tools before guest input. Attachment identified the intended
disposable PID and keyboard injection capability. **Actual input used the registered
BIOS keyboard MCP**, not the SDK fallback. Each subsequent batch has raw replies
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

## Interpretation at the A03 checkpoint

Confirmed: for these ASCII values, First Name (Phase I) and Work Phone have
variable-length storage; the measured delimiters, identifier/index and defaults
survive the phone-length change. The complete file remains fixed at 10,240 bytes.
Likely: these sixteen positions form an ordered contact schema, with count/next-ID
candidates as described. Unknown: meanings of unpopulated positions, `n`, general
phone normalization, date encoding, encoding outside tested ASCII, limits,
index ordering, identifier assignment across multiple contacts, deletion and allocation.
Similar Calendar structures do not establish a shared database engine.

A04 is not yet performed at this checkpoint. Its authorized independent test
will populate City with METRO, leaving the A01 phone and names unchanged.
A later Phase III two-contact test could insert distinct last names in reverse
alphabetical order and inspect insertion IDs versus index order. No general
parser, writer or production packaging change is included here.

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

## Checkpoint validation

A03 checkpoint: 3 new private tests and 3 Phase I tests passed against preserved
fixtures; 65 portable tests passed. Ruff passed for the new Python test file.
REUSE/SPDX lint passed (73/73 files); repository privacy audit passed (152 files).
All A00/A01/A02 sealed evidence was independently rehashed unchanged (443/508/451
files). Full A03 manifests and all fourteen guards passed. Tests and raw outputs
remain private alongside the evidence. No billing or credit balance was read;
the owner's external before/after readings are the monetary benchmark.
