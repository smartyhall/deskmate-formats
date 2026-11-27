# Historical conversion and repair utilities — static investigation

2026-11-26. Offline static work only. Neither utility was executed on the host;
no emulator was used. Inputs are the privately preserved TVDog extraction of
`dmrepair.exe` and `f2d01`/`f2ddos`. Original bytes, full string dumps and
bounded listings remain in the private lab.

Continues the [catalog review](../ecosystem/tvdog-directory-index-review.md)
that identified these titles, and the [database component
review](database-components.md) whose schema findings they corroborate.

## Identity

| File | Bytes | SHA-256 | Format | Entry | Relocations |
| --- | ---: | --- | --- | --- | ---: |
| `DBREPAIR.PDM` | 18,119 | `e1922f36dd470c0f78f8e3872dce055aa3fd088e2ac4d8ccd852b9d2cb2389c4` | MZ, `DM89` marker at file `0x28` | `02CD:000C` | 19 |
| `FIL2DBF.PDM` | 45,712 | `26d2ab728b7de3a4b1f8d82797b2225695a3810cff83176e844d0d1f73fd444c` | MZ, `DM89` marker at file `0x28` | `0000:2F80` | 33 |
| `FIL2DBF.EXE` | 16,168 | `55bbb869ad40316c029e63fd2e36c7912a9be1c5f748d2086cf5cca973f5f404` | MZ | `02DD:0002` | 45 |

Documented purpose, from the packages' own text files:

* `DBREPAIR.PDM` is Tandy's **DeskMate 3.0 or higher data file recovery
  program**. Its notes list the files it can access, and thereby name the data
  files DeskMate 3.0+ treats as databases: `PERSONAL.ADR`,
  `PERSONAL.CAL`/`PERSONAL.CLN`, `*.FIL`, `*.COL`, `*.DRY`, and the Home
  Organizer set `HOME.DB`, `TRAVEL.DB`, `INFOCNTR.DB`, `KITCHEN.DB`,
  `ACCOUNTS.DB` and `NOTEBOOK.DB`.
* `FIL2DBF.PDM` is **Fil2dbf 0.1**, © 1997 Jeffrey L. Hayes, converting
  DeskMate 3.0x databases "from Filer, Address Book, etc." to dBASE III/IV.
  It redistributes `DBREPAIR.PDM` and, as a fallback, the separate DeskMate
  runtime.
* `FIL2DBF.EXE` is that runtime's launcher: its embedded version string reads
  `03.03.01`.

The extension list is independent evidence for a shared on-disk container. Six
different suffixes, three application families and two Home Organizer products
are all offered to one repair program, which is consistent with the shared
DMDB/DBAL storage already established from the applications' call sites. It is
not proof that every one of those files has an identical schema; the repair
tool may dispatch per file.

## The service interface, as used by third-party code

Both `.PDM` modules contain 21 `INT E0` sites. The register construction
around them uses the same shape as the published application bindings, but
with a **wider selector vocabulary**:

| Module | Sequence before `INT E0` | Sites |
| --- | --- | --- |
| `DBREPAIR.PDM` | `PUSH DS` / `POP ES` / `MOV AX,0208` / `MOV DX,118C` / `MOV BX,1188` / `INT E0` | `0x129D`, `0x131D` |
| `DBREPAIR.PDM` | `… MOV AX,0206` … `INT E0`; `MOV AX,0207` after `PUSH DS`/`POP ES` | `0x12AB`, `0x12E2`, `0x12FF` |
| `FIL2DBF.PDM` | the same three sequences at `DX,18A0`/`BX,189C` and `DX,18AA` | `0x23FE`, `0x240C`, `0x2420`, `0x2443`, `0x2460`, `0x247E` |

So `ES = DS` is set first, then a name offset in `DX` and — depending on the
selector — a slot offset in `BX`, with selector `0206`, `0207` or `0208`.
Published bindings in Calendar, Filer and Address Book used `0206` or `020C`.
`0207` and `0208` are therefore additional observable request values, not new
semantics: the operative distinction between them, and the runtime handler, are
still **unresolved**.

`FIL2DBF.EXE` contains **no** `INT E0` site. The DOS runtime reaches DeskMate
services another way. That is a format-level distinction worth recording: the
`.PDM` module is bound into a running DeskMate, while the standalone `.EXE`
carries its own dispatch path. Neither the mechanism nor its equivalence is
established here.

## What the static text shows about the database contract

Both modules reference `DBCOLS`. `FIL2DBF.PDM` refuses to use it, with the
message "Access to DBCOLS is not permitted - internal DeskMate use only."

This is independent, contemporaneous corroboration of the project's reading of
`DBCOLS` in `DMDBRD.RES` as the engine's own column catalogue rather than an
application table. A 1997 third-party converter, written against the public
DeskMate 3 runtime, treats that name as reserved internal state; our schema
descriptors and `DBCOLS` sibling table sit in the same component. Neither fact
proves the record layout, but together they place `DBCOLS` on the engine side
of the boundary.

The converter's own vocabulary is a readable checklist of the operations it
expects: create a dBASE file, prompt for a dBASE field name and type, write the
dBASE header, handle an empty table, and fall back to repair with messages such
as "Error in table list.  Try to fix it with Dbrepair?" and "File or database
error retrieving column names." A write path exists — it produces a `.DBF` and
renames the original to `.OLD` — so the module is an independent, if
second-hand, witness to what a DeskMate database exposes: named columns, a
column type, and a table list.

Error strings in `DBREPAIR.PDM` name the recovery states it distinguishes:
"Error renaming file.", "Cannot open file.", "Cannot create file.", "The File
is empty or un-recoverable file." and a summary of the form "Recovered %lu
bytes, %lu bytes unrecovered." The last one implies a byte-granular salvage
count rather than record-granular repair, which is a hypothesis, not a decoded
behaviour.

## Format recognition

Neither module contains a table of the database extensions it accepts; the
`PERSONAL.ADR`/`.FIL`/`.DB` list appears only in the text documentation. The
recognizer is therefore more likely structural (through the DMDB service) than
name-based. This campaign did not locate a code path that validates a header
or magic number, so "structure-based recognition" remains an **inference from
absence** and should not be repeated as a finding.

## Shared service skeleton in the two `.PDM` modules

The two modules are not independent implementations of the same idea. The
instruction sequences around the `INT E0` calls match byte for byte while the
data offsets they load differ:

```text
DBREPAIR.PDM  0x12A8  06 53 1E 07 B8 08 02 BA 8C 11 BB 88 11 CD E0 0B C0 7E 16 C6 06 9C 11 01 B8 06 02 CD E0
FIL2DBF.PDM   0x2409  06 53 1E 07 B8 08 02 BA A0 18 BB 9C 18 CD E0 0B C0 7E 16 C6 06 B0 18 01 B8 06 02 CD E0
```

`PUSH DS` / `POP ES`, selector `0208`, a name in `DX`, a slot in `BX`, the same
`OR AX,AX` / `JLE` test, the same `MOV BYTE PTR [slot],1` and the same
follow-up with selector `0206` — with `DX,BX` pointing at `118Ch`/`1188h` in one
module and `18A0h`/`189Ch` in the other. A third site ends in a case-folding
loop (`CMP AL,61h` / `SUB AL,20h`) before the same selector call, so table
names are upper-cased before they are passed.

This is direct static corroboration of the documented claim that `FIL2DBF.PDM`
*redistributes* `DBREPAIR.PDM`: it carries a compiled copy of the same service
helper skeleton. It also explains why the two modules have identical selector
histograms below — the calls come from shared code, not from independent
authors converging on the same interface.

## DOS and service call profile

Counts are of immediate-adjacent call sites and are therefore a floor, not a
total: an `AH` loaded earlier and carried in a register through intervening
instructions escapes the scan (the large `unknown` bucket).

| Module | `INT 21h` functions seen | `INT E0` sites | `MOV AX,imm; INT E0` selectors |
| --- | --- | ---: | --- |
| `DBREPAIR.PDM` | `30h`, `3Eh`, `40h`, `42h`, `48h`, `4Ah`, `4Ch` | 21 | `0206`×5, `0207`×4, `020B`×2, `0208`×1, `020C`×1, `0600`×1, `0700`×1 |
| `FIL2DBF.PDM` | `25h`, `2Ah`, `2Ch`, `30h`, `40h`, `42h`, `48h`, `4Ah`, `4Ch` | 21 | identical |
| `FIL2DBF.EXE` | `01h`, `06h`, `09h`, `0Eh`, `19h`, `1Ah`, `25h`, `2Fh`, `30h`, `35h`, `3Bh`, `3Eh`, `3Fh`, `47h`, `48h`, `49h`, `4Ah`, `4Dh`, `4Eh`, `4Fh`, `50h`, `51h`, `52h`, `55h`, `59h` | 0 | none |

The profile separates the two worlds cleanly. The `.PDM` modules do their file
work through the DeskMate service (`INT E0`), with DOS used for memory and
standard-handle operations. The standalone `.EXE` carries a broad DOS surface —
read (`3Fh`), close (`3Eh`), seek (`42h`), DTA (`1Ah`/`2Fh`), disk (`0Eh`,
`19h`), memory (`48h`–`52h`), character output (`09h`) — and no DeskMate
dispatch at all. It is a DOS program that prepares an environment rather than a
module bound into one.

`FIL2DBF.EXE`'s `AH=4Bh` (EXEC) does not appear in the immediate-adjacent set,
so how it starts the DeskMate runtime remains unestablished; it may load a
module through a service in the runtime it starts, or build the call
indirectly.

## dBASE output: what static evidence can and cannot show

`FIL2DBF.PDM` holds the strings `dBASE` (12 occurrences), `DBF`/`dbf`, `Field`,
`field`, `record`, and its error text names the operations: create a dBASE
file, prompt for a field name and type, write the header, handle an empty
table. It also contains the four bytes `03 00 00 00` three times, and `03` is
the dBASE III version byte that begins a `.DBF` header.

That is **a candidate, not a finding**. A four-byte run in a 45 KB binary is
not a header construction; it could be a version number, a length or unrelated
data. What would settle it is a native run whose output file begins with `03`
and whose 32-byte field descriptors match the widths our parser derives from
the same table. Until then the claim stays at "the converter contains dBASE
vocabulary and a plausible version byte".

## Promising future experiments

These need native execution and therefore belong to an emulator campaign with
its own authorization. They are recorded because each one tests a claim this
campaign could only observe statically.

1. **Repair behaviour on a controlled defect.** Take a committed synthetic
   database fixture, corrupt one field or index entry in a copy, run
   `DBREPAIR.PDM` natively, and compare the recovered bytes with our parser's
   view. This tests the salvage granularity and whether `.OLD` is created
   before or after a successful repair.
2. **Converter acceptance as an independent oracle.** Point `FIL2DBF.PDM` at a
   synthetic native database and check whether it produces a dBASE III file
   whose header and field descriptors match our column widths and types. A
   third-party program's reading of the same table is stronger evidence than
   our own parser agreeing with itself.
3. **Selector mapping.** Observe, on a read-only debugger stop, which `INT E0`
   selector corresponds to open, to column enumeration and to row retrieval.
   The utility provides a compact exercise of `0206`/`0207`/`0208` without
   driving an application's UI.
4. **Runtime versus module dispatch.** Determine how `FIL2DBF.EXE` reaches the
   database service without `INT E0`, and whether the answer is the same
   service the `.PDM` path uses.

None of these were performed. No utility was executed, and no guest resource
was claimed by this campaign.

## Native qualification matrix

Every row needs native execution under the emulator campaign's authorization;
none was performed here, and no utility was run on the host. The point of the
matrix is that each row can **contradict** a current belief, not merely confirm
it, and that the outputs it must preserve are named in advance.

| # | Specimen | Hypothesis under test | Outputs to preserve | Corroborates if | Contradicts if |
| ---: | --- | --- | --- | --- | --- |
| U1 | committed valid `.FIL` fixture, unmodified | `DBREPAIR` repairs nothing and rewrites nothing when the file is intact | input and output hashes, `.OLD` presence, message text | hashes equal, no `.OLD`, success message | any byte change, or `.OLD` created |
| U2 | same fixture with one record's text byte changed | repair is record-granular | recovered record/byte counts, output hash, diff | the reported recovered count matches whole records | a byte-granular count, as the message wording implies |
| U3 | same fixture with a damaged index/row pointer | the repair path rebuilds an index from records rather than trusting it | output hash, table list, any index-shaped bytes | output readable by `FIL2DBF` afterwards | refusal, or an output our parser cannot read |
| U4 | zero-length file | an empty file is refused, not "recovered" | exact message, exit behaviour, file state | a refusal naming emptiness | a created or rewritten file |
| U5 | truncated file (header only, then half the records) | the utility salvages complete records and stops | recovered/unrecovered byte counts, output hash | counts consistent with the truncation offset | counts that exceed the surviving bytes |
| U6 | header with an unknown schema marker | recognition is structural and version-tolerant | message, whether the file is touched | a clear refusal | acceptance and rewrite |
| U7 | valid fixture, `FIL2DBF` conversion | the produced `.DBF` header matches our column types and widths | `.DBF` bytes (header, descriptors, records), `.OLD` name | descriptor widths equal our parser's | a width or type we do not predict |
| U8 | empty table, `FIL2DBF` conversion | an empty table yields a header with zero records, not an error | `.DBF` header bytes, record count | 32-byte header, zero records | an error message, or a missing file |
| U9 | fixture whose column name exceeds 10 characters | dBASE's 10-character name limit is enforced, truncated or refused | prompt text, `.DBF` descriptor name field | a deterministic, documented choice | silent corruption of the name field |
| U10 | selector trace during U7 | `0206` = open/load, `0207`/`0208` = table/column operations | selector, `DX`/`BX` arguments, return `AX` per call | the sequence matches the static call order | a selector used with a role we did not predict |
| U11 | `FIL2DBF.EXE` startup | the `.EXE` loads the DeskMate runtime and hands it the `.PDM` | every `EXEC`/module-load call, loaded file name | an `AH=4Bh` or service load of a runtime module | a self-contained implementation, no runtime load |

Reading of the columns: "corroborates" means the observation is consistent
with the current specification; "contradicts" means it falsifies a claim we
currently make, and the campaign must then change the claim rather than explain
the observation away.

Two practical rules for running the matrix:

* each specimen is generated by us, committed as a fixture, and copied into the
trial disk. The original is never the thing that gets damaged;
* the emulator disk is disposable and the input hash is recorded before the run,
so a surprising output can be attributed to the program rather than to a
drifted test image.

The most informative rows are U3, U5 and U7. U3 separates "repair" from
"index rebuild"; U5 tests the byte-granular salvage claim that the program's own
message wording suggests; U7 is the only row where a third-party program's
output is compared against our parser's independent prediction, which is
stronger evidence than either agreeing with itself.

## Publication boundary

All three files are third-party commercial binaries. Their bytes, listings and
full string dumps are not published. This report publishes identities, hashes,
offsets, structural counts and short quoted interface or error text as
research findings, consistent with existing project practice. The utilities'
own documentation files also remain private; facts drawn from them are cited
as package documentation rather than reproduced.
