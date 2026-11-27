# Ghidra procedure contracts (2026-11-27)

This note is the durable description of the deterministic procedures the
Ghidra campaign exposes to other workers. It exists so a Supervisor, an
emulator worker or a later agent can use a procedure without reconstructing
its semantics from source, and so nobody has to guess which procedures have
been exercised and which are only sketched.

**Status vocabulary.** Each procedure carries one of three labels, and the
label is a claim about evidence, not about ambition:

* **qualified** — implemented, covered by portable tests where the logic is
  portable, and exercised against a real installation on a recorded input.
* **experimental** — implemented and exercised at least once, with a named
  gap that prevents treating it as dependable.
* **proposed** — described only. No code, no measurements.

Nothing in this document registers a procedure for unattended execution. That
is a separate decision for the Supervisor campaign, and the campaign that owns
an implementation must make it.

## Shared contract

All procedures in this note are ordinary command-line tools:

* They take every input as an explicit argument. No procedure reads a selector
  from the environment silently; environment values are recorded in the receipt
  so a result can be attributed to them.
* They write one JSON receipt per invocation, published atomically, stamped
  with a schema identifier, the tool path, an attempt identifier and the start
  time in UTC.
* They exit with a distinct code per terminal outcome. A caller never has to
  parse prose to learn whether a run succeeded.
* They use no model service, no emulator and no network. Inference is never
  part of a measurement.
* Proprietary artifacts — decompiled source, program bytes, private project
  paths — go only to private files. Receipts carry digests, counts, addresses
  and structural facts.

## Read-only procedures

Read-only means: the procedure does not write to the analysis project, does not
change a program, and does not create a project when one is missing.

| Procedure | Tool and mode | Inputs | Output | Status |
| --- | --- | --- | --- | --- |
| Toolchain selection | `tools/ghidra/ghidra_toolchain.py` | optional install/Java/profile, requirement, search roots | selection record with every candidate and rejection reason | qualified |
| DOS structure identification | `tools/inspect_dosimage.py identify` | image file, optional digest, optional interpretation | format, header facts, overlay classification, header warnings | qualified |
| Loader block model | `tools/inspect_dosimage.py blocks` | image, load paragraph | block names, ranges, initialized extents | qualified |
| Coordinate mapping | `tools/inspect_dosimage.py map` | file offset, linear or segment:offset | all four coordinate forms | qualified |
| Far-pointer classification | `tools/inspect_dosimage.py far` | image, 4-byte offset | resolution class and out-of-image status | qualified |
| Bounded decode | `tools/inspect_dosimage.py disasm` | image, span, max instructions | instruction bytes and text from an independent decoder | qualified when Capstone is installed; refuses otherwise |
| Project reopen | `ghidra_dos_import.py --reopen-only` | project dir, project, program path, attempt id | program summary, project file listing | qualified |
| Program fingerprint | inside `--summary` | program | `content_sha256` over block geometry and bytes | qualified |
| Memory-block inventory | `ghidra_program_report.py --summary` | project, program | program path, content digest, block names, ranges, sizes, flags | qualified |
| Function enumeration | `--functions` | limit | entry, name, size, thunk/external flags, calling convention | qualified |
| Symbol inspection | `--symbols` | limit | address, name, type, namespace, primary, source | qualified (2026-11-27) |
| Cross-reference enumeration | `--xrefs` | target address | from-address, reference type, source | qualified |
| Bounded disassembly | `--disassemble` | function name or address, max instructions | address, bytes, mnemonic, operands, flow type | qualified (2026-11-27) |
| P-code extraction | `--pcode` | function name or address, max instructions | address, sequence, mnemonic, output and input varnodes | qualified (2026-11-27) |
| Bounded decompilation | `--decompile` | function name or address, private text path | digest, line and character counts, signature, elapsed ms | qualified |
| Annotation verification | `--verify-annotation` | project, program | plate comment, bookmarks, symbols, persisted flag | qualified |

### Measurement notes for the read-only set

The 2026-11-27 qualification ran against the owned 12.2 project
`deskmate122` (`/DESK.EXE`, image SHA-256
`0f2a40243c997276904d2555a117c60eedf0016dde073285e8d63c8345a2eba3`) under
Ghidra 12.2 (build `2026-Oct-16 1220 UTC`, revision `8ca9077…`) with Java
`25.0.5.1+2-LTS` and PyGhidra 3.2.0:

* `--summary` reported 4660 instructions, 170 functions, 196 symbols and 9
  blocks — the same counts recorded for the same image under 12.1.4, which is
  why the new procedures are treated as compatible rather than re-qualifying
  the whole image.
* `--symbols` returned `probe_label`, the label an earlier annotation probe
  created, from a project the probe did not create. That is independent
  evidence that annotation persistence survives a separate JVM.
* `--disassemble FUN_1000_0009` produced `DEC AL` / `JZ` / `DEC AL` / `JZ` /
  `JMP` from bytes `FEC8 7406 FEC8 740C EB15`.
* `--pcode FUN_1000_0009` produced, in order, `INT_SBORROW`, `INT_SUB`,
  `INT_SLESS`, `INT_EQUAL`, `INT_AND`, `POPCOUNT` for the first instruction.
  The varnodes name `register:0x0:1` (AL), `register:0x206:1` and
  `register:0x207:1` (the byte flags) and `register:0x20b:1` (carry), plus
  `unique` temporaries. P-code varnode identity therefore distinguishes
  operations that print identically, which is the point of extracting it.

**Correction recorded.** The first implementation reported `getHigh()` for
each varnode. Without a decompiler that is unset, so every operand printed as
`None` and two different operations could look the same. The procedure now
reports address space, offset and size of the raw varnode, and the note above
is the corrected measurement, not the original one.

## Procedures that write

Writing procedures operate only on projects this campaign owns. They take an
explicit project directory and never create a project implicitly.

| Procedure | Tool and mode | Effect | Status |
| --- | --- | --- | --- |
| Bounded executable import | `ghidra_dos_import.py` | creates or opens an owned project, imports one image, optionally analyses | qualified (2 images, 2 Ghidra releases) |
| Annotation creation | `ghidra_program_report.py --annotate` | one transaction writing a plate comment, a bookmark and a label; saves | qualified |

Both publish a receipt whose `persistence` section records `save` and `close`
separately. A committed but unsaved annotation is reported as
`not_persisted`, never as persisted; an import whose save failed is
`persistence_failed`, never `succeeded`.

## Differential procedures

| Procedure | Method | Status |
| --- | --- | --- |
| Same program, two Ghidra releases | import each release's project separately, compare receipts field by field, and compare instruction text, operand order, p-code and assembler output for named forms | qualified for 14 instruction forms and 5 long-mode forms; experimental for whole-program comparison |
| Same release, two program versions | import both, compare `--summary` structure, then symbol and function sets, then bounded disassembly at matched entry points | proposed |
| Same program, two implementations | compare p-code operation sequences per matched instruction | proposed |

The version-differential procedure is qualified only where it was measured:
the fourteen `MOV Sreg,/r` forms across 12.1.4 and 12.2, plus the five
long-mode forms, each with the bytes, the displayed text, the operand order and
the p-code. Asserting it for a whole program would claim much more than those
measurements support, because a whole-program comparison also depends on
analysis results that no form-level comparison covers.

## Resource requirements and concurrency

* Every procedure that starts a JVM costs a JVM. On this host a cold start is
  about 10 s and a whole analysed import is minutes; a read-only report is
  seconds. Times are recorded per receipt (`elapsed_seconds`, per-stage
  `seconds`) rather than assumed.
* One writer per project. Two concurrent writers would contend for a Ghidra
  lock, and this campaign has no positive ownership test, so it does not
  attempt concurrent writes at all.
* Read-only procedures open the project through the same lock as writers. They
  are therefore started one at a time against a given project; the retry with
  bounded backoff exists because a released lock can remain visible for a
  moment.
* All stages run under a timeout. A timed-out worker is terminated, and the
  project is reported as being in an unknown state rather than reused.

## Error semantics

| Condition | Reported as |
| --- | --- |
| Request refused before any JVM starts | `invalid_request`, exit 2 |
| Input digest differs from the expectation | `input_mismatch`, exit 2, no worker started |
| Project absent during a read or a reopen | `project_missing`, exit 3; the project is not created |
| Program absent from an opened project | `program_missing`, exit 3 |
| Import worker crashed or wrote no receipt | `import_failed`, exit 3, with the worker's stderr tail |
| Stage exceeded its timeout | `import_timeout` or `reopen_failed`/`timeout`, exit 4 |
| Autoanalysis raised | `analysis_failed`, exit 5 |
| Reopen could not open or identify the program | `reopen_failed`, exit 6 |
| Reopened program differs | `reopen_mismatch`, exit 7, with the differing field named |
| Reopened payload names no attempt, a foreign attempt or another project | `reopen_malformed`, reported as `receipt_malformed`, exit 8 |
| Reopened payload's `ok` is not the literal boolean true | `reopen_malformed`, as above |
| Reopened payload carries no program identity or fingerprint | `reopen_malformed`, as above |
| Reopened payload is unreadable | `reopen_failed`, reason `payload_unreadable` |
| Reopen worker reports failure but exits zero | `reopen_failed` with `worker_exit_disagrees: true` |
| Receipt failed validation, or claimed success with a nonzero exit | `receipt_malformed` / `receipt_inconsistent`, exit 8 |
| Analysis finished but was not stored | `persistence_failed`, exit 9 |
| Annotation committed but not saved | `not_persisted`, exit 6 |

## Evidence boundaries

* No procedure claims runtime semantics. A p-code sequence, a loader block
  boundary or an entry point is a statement about bytes and about Ghidra's
  reading of them.
* No procedure identifies a symbol's meaning. Symbol and function names come
  from the analysis; they are not evidence about what the code does.
* No procedure infers a compiler, a calling convention's use, or a data
  structure's layout from the presence of a pattern. Each needs its own
  evidence.
* Decompiled text is proprietary. Procedures never place it in a receipt; they
  place a digest, a line count, a character count and a signature.

## Relation to the Supervisor campaign

These descriptions are handoffs, not registrations. A Supervisor integration
should treat them as candidate task definitions and confirm, for each one, the
arguments, the expected receipt schema, the timeout and the resource
requirement before scheduling it unattended. Two properties make that
straightforward: every procedure is a separate process, and every procedure
answers with a terminal outcome and an exit code.
