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

## Publication boundary

All three files are third-party commercial binaries. Their bytes, listings and
full string dumps are not published. This report publishes identities, hashes,
offsets, structural counts and short quoted interface or error text as
research findings, consistent with existing project practice. The utilities'
own documentation files also remain private; facts drawn from them are cited
as package documentation rather than reproduced.
