# Database service call review

2026-11-01. Static review of the preserved DeskMate 3.05 installation.
No native application, GUI, keyboard service, OCR or database mutation was used.

## Result and confidence

**All three application images contain code-backed calls through a named DMDB
service interface.** Each has a name-bearing binding sequence and a far-indirect
call thunk using the same pointer slot. Direct callers of those thunks were
recovered and checked against original bytes. DMDB.R89, in turn, contains a
DMDBRD-name binding sequence and calls through its reader slot. DMDBRD contains
corresponding sequences naming DMDBUPD and DMDBBLD.

This is stronger than matching strings or file conventions. It is direct static
evidence for a common callable service interface. **It does not yet establish
the runtime binding contract, the loaded image identity, or which record-storage
operations pass through that interface.** In particular, a common setup/resource
interface alone cannot prove that every application's record codec or allocator
is shared. The shared on-disk structures remain independently established.

Confidence: H = instruction/data relationship checked against original bytes and
MZ arithmetic; M = functional interpretation of that relationship; U = unresolved.
No source-level function names or inferred C signatures are assigned.

## Reproducible corpus

Use the same primary installation and SHA-256 identities as
[cross-application-evidence.json](cross-application-evidence.json).
Private new evidence is DOSLAB EXPERIMENTS/RESEARCH/database_call_review.
The original cross_application_db evidence, projects and manifests remain intact.

The new [call map](database-call-map.json) contains file identities, offsets,
typed edges and confidence. Absolute file offsets below are hexadecimal; they
are independent of Ghidra's synthetic load base. Original bytes, selected
instruction listings and project databases remain private. Reproduce MZ facts
with the existing inspection helper's new mz and mz-far commands; run the
opt-in test_database_bindings.py for fixed original-byte assertions.

Private ReviewApps.java selected name-operand candidates in four images.
ReviewThunks.java queries only the identified binding/thunk routines and reader
callback candidates. Scalar matches are candidates until instruction context is
checked: for example, SUB SP,60 is not a schema-table reference merely because
the descriptor table has relative offset60.

## Bounded call/reference map

The application DS-relative coordinates below are conditional on their observed
relocated DS-initialization sequences. They are not a universal DS model.

| Image | Image-relative DS paragraph / file base | DMDB name offset | Binding routine / pointer slot | Indirect-call thunk / call instruction |
|---|---|---|---|---|
| FILER.PDM |0857 /8770|0E88 →95F8|6C67 / DS:0FA6|740D /741B|
| ADDRESS.PDM |0BBD /BDD0|28A6 →E676|A1E5 / DS:29C4|A9B9 /A9C7|
| CALENDAR.PDM |0E87 /EA70|2944 →113B4|D7E5 / DS:2A62|DE9F /DEAD|

Each binding routine sets ES from DS, supplies the DMDB name in DX and the
pointer-slot offset in BX, selects AX0206 or020C, then executes INT E0.
Each thunk marshals a stack-argument address into ES:BX and calls far through
the corresponding DS slot. These are H-confidence register/instruction facts.
“Bind/open service” is an M-confidence functional description: INT E0's actual
implementation has not been traced. The segment MOV display caveat below matters.

| Observed code/data edge | Evidence | Classification |
|---|---|---|
| Filer6C16 →6B54 →740D | Direct near calls; final helper call at6B7B; thunk calls slot0FA6 at741B | H, application wrapper → shared interface |
| AddressA194 →9A3E →A9B9 | Direct near calls; final helper call at9A99; slot29C4 atA9C7 | H, application wrapper → shared interface |
| CalendarD794 →D684 →DE9F | Direct near calls; final helper call atD6AB; slot2A62 atDEAD | H, application wrapper → shared interface |
| Application slot → DMDB.R89 callback | Name-bearing binding sequence plus matching DMDB descriptor | M, actual name-to-image dispatch edge unresolved |
| DMDB.R890301–0310 | ES:DX names DMDBRD at0425; BX0048; AX0206; INT E0 at030E | H, named reader binding sequence |
| DMDB.R8902E9 and03B8 | Far-indirect calls through DS:0048; image DS paragraph001F gives file base03F0 | H bytes/control candidates; no storage-operation name assigned |
| DMDB.R890404 /0408 | MZ-relocated descriptor pointers target02DD /0393 | H data references; descriptor/API roles remain M |
| DMDBRD.RES52EA /52EE | MZ-relocated pointers following DMDBRD name target4EDB /4E92 | H data references; runtime export selection remains U |
| DMDBRD.RES1AD8 /1B29 | Name arguments0134/013C resolve to DMDBUPD at51B4 and DMDBBLD at51BC; slots0128/0130; shared helper1B64 executes INT E0 with AX0206 | H named component binding; M functional loader interpretation |
| DMDBRD.RES19EC,1B20,481E | Far-call byte candidates through slot0128;1B20 also queried as an instruction | H bytes; unqueried code boundaries and operation semantics U |
| DMDBRD.RES2110 | Constructs value0096 associated arithmetically with DBCOLS at5116 | H constant/construction; M schema-name association, not a proven schema-builder entry |

The intermediate application wrappers differ. Address Book's9A3E includes
additional branches and state handling absent from CalendarD684 and Filer6B54.
That is direct application-specific code evidence, without assigning meanings to
its untested parameters or returns. The common thunk does not imply identical
application logic.

| Requested architectural area | Established | Still unresolved |
|---|---|---|
| Shared entry interfaces | Three named DMDB binding/call pairs; stub reader binding; relocated reader callback candidates | Runtime INT E0 binding and export selection |
| Schema/field descriptions | DMDBRD's six name/width/type descriptors still match all four databases; DBCOLS-associated constant construction | Routine-level creation/validation API and omitted-field defaults |
| Record lookup/indexing | Shared on-disk six-byte target arithmetic; callable interface present | Which selector/routine consumes the index |
| Allocation/deletion | Native Calendar evidence and static Filer retirement candidates survive review | Shared allocation/deletion routine or cross-application policy |
| Application interfaces | Distinct wrappers feed a common stack-marshalling thunk shape | Source signatures, operation selector meanings, UI-to-storage mappings |

## Ghidra conclusions that survived review

MZ sizes, relocations, entry arithmetic and the six schema descriptor
correspondences survived independent original-byte checks. The earlier negative
reference queries accurately describe those queries, not the absence of code
references throughout the program. Name-operand/dataflow probes now recover
relationships the original string-reference query missed.

The earlier report correctly withheld a common-engine claim and correctly
rejected short shared-code matches as decisive: TEXT.PDM was a negative control
for that technique. New evidence concerns actual callers and pointer-slot use,
not those nondiscriminating window matches. No new claim about TEXT's storage
behavior is made.

MZ contains initial CS:IP and SS:SP, **not an initial DS field**.
Ghidra-created CODE/DATA block names are not DS assignments or original symbols.
DS arithmetic is supported only where explicit relocated register-load code or
a stated conditional base is supplied. An unrelocated four-byte value is not
automatically a far pointer into the image.

FUN_* names, function boundaries and entry labels produced by autoanalysis are
not original DeskMate symbols. In the tiny stub, autoanalysis boundaries do not
coincide cleanly with all descriptor-pointed callback starts. No decompiler
signature, guessed parameter count or auto-generated routine name is published
as an established API. The reviewed scripts did not use decompilation output
to identify database functions.

The selected reader callback addresses4E92/4EDB produced no instruction listing
under the query's default segmented alias. Their MZ-relocated data references
remain valid; no decoded callback routine or negative proof of use is claimed.

## Verified segment-MOV display anomaly

In the installed Ghidra12.1.4 x86 language source, ia.sinc lines4013–4014 display
the register form of opcode8E with the general register first, while the semantic
assignment writes the segment register. For example, stub file0203 contains
8E D8, whose effect is DS := AX; the listing prints MOV AX,DS. At a thunk,
8E C3 writes ES from BX while displaying the opposite order.

This is a **display-versus-semantics distinction**, not evidence that Ghidra's
p-code performs the reversed move. The installed source hash and relevant
artifact references are in the machine map. No language files were patched.
It does not, by itself, explain the earlier missing cross-references.

## Limits, failures and next investigation

The small-stub launcher exceeded its420-second parent timeout; its Java child
later completed analysis and the script. Both events are recorded, rather than
claiming a successful bounded launcher receipt. The four-image batch completed
normally. The first no-analysis follow-up looked only at the project root and
found no programs because imports were nested below inputs; that failure was
retained and the follow-up was corrected to recurse. A fixed-byte test initially
placed the first stub call one byte early; its failed log was retained before
correcting02E8 to02E9. No database bytes or old evidence were changed.

**Best next task: trace one record-lookup request through the common interface.**
Choose one application call to its thunk, retain the numeric request selector,
resolve its DMDB/DMDBRD dispatch edge, and follow only that request to the
six-byte index lookup and returned row payload. Stop at the first unresolved
indirect edge and document it. The distinguishing outcomes are:

* A single shared reader path consumes the same index/row structures for all
  three application schemas: strong evidence for shared storage implementation.
* The common path ends at setup/metadata and each application performs its own
  record lookup: supports shared infrastructure with application-specific storage.
* The name binding cannot be established statically: prepare a later read-only
  native binding trace; do not infer the missing edge from filenames.

This remains a bounded offline task. Native F00–F02 are still unperformed and
are not prerequisites for the next static lookup trace. No native operation is
authorized or executed by this review.
