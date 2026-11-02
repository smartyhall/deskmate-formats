# Calendar INT E0 binding: recovery and static boundary

2026-11-02; [issue 25](https://github.com/smartyhall/deskmate-formats/issues/25).
Continues [the selected request](lookup-trace-22.md) and
[the database call review](database-call-review.md). No native execution.

## Recovery checkpoint

The interrupted investigation created `research/calendar-binding-25` from
main `391c0ca` in one separate worktree. Recovery reused it. The worktree was
clean; earlier research worktree heads matched the recorded baseline. Private
scripts, vector scan, source hashes and the 11,392-file preservation baseline
survived under DOSLAB `EXPERIMENTS/RESEARCH/calendar_binding_25`.

The baseline exception is one temporary Ghidra database page already absent
when the baseline was taken. This is not evidence of a change by this task.
Historical manifests remain unchanged. Both new Ghidra imports stopped before
the probe script ran: the normal launcher exceeded its bound and its owned
Java process was terminated; the direct-Java attempt terminated at its
300-second bound during import. Neither produced a verified instruction
listing. Their incomplete projects and logs are retained privately. Recovery
found no surviving process from either attempt. Existing MCP services were
left alone. No GUI, emulator, VM, configuration or original database was used.

## Evidence standard and current conclusion

**H** means original bytes and explicit MZ/address arithmetic; **M** means a
functional interpretation; **U** means unresolved. File offsets are absolute
hexadecimal. A byte scan identifies candidates, not instruction boundaries.

Calendar's slot remains unresolved. The raw binding sequence supplies
`ES=DS`, `BX=2A62`, `DX=2944` and selects `AX=0206` or `020C` before the
interrupt at file `D800`. The old trace's call at `DEAD` still reads the
four-byte slot at file `114D2`; its segment word has no MZ relocation.
No callback/export selection or forwarding into DMDBRD has been established.

DESK.EXE contains vector get/set candidates and a possible AH=02 dispatch
table. These are **provisional** at this checkpoint: failed Ghidra imports
must not be counted as validation. In particular, an on-disk installation
path does not identify the actual runtime interrupt vector. That distinction
is required even if the candidate path is subsequently validated.

| Original image | SHA-256 |
|---|---|
| CALENDAR.PDM | `819df5658b663aa69b15584abf805062679e97f587f3404738f6e82876e4bd23` |
| DESK.EXE | `0f2a40243c997276904d2555a117c60eedf0016dde073285e8d63c8345a2eba3` |
| DMDB.R89 | `799444bb8c04632d261f61498ba269f9352e5528718f2e0a89512bf6ef7b808f` |

The originals are the preserved F00 before installation. Recovery rehashed
them; no binary or proprietary listing is included here.

## Verified continuation after recovery

A private copy of the MZ payload, starting at file `0200`, was imported with
the explicit `x86:LE:16:Real Mode` processor and synthetic base `1000:0000`.
The bounded [Ghidra script](../../tools/ghidra/CalendarBinding25.java) uses
pseudo-instructions, follows no branch graph, runs no autoanalysis/decompiler
and changes no program instructions. Original MZ relocations are checked
separately with `tools/inspect_structure.py`. Existing projects were not used
as writable query targets. Results and proprietary output stay private.

The first successful payload query included a straight-line window across the
bootstrap's inline signature. That interval is data and was rejected as code.
The reviewed script explicitly skips `42A1–42B9`, retaining only the entry jump
and the separately targeted handler body. No claim depends on decoding that
signature as instructions. Ghidra's known segment-MOV display anomaly is
handled by checking original opcodes, as in the prior review.

| Observation | Evidence / confidence |
|---|---|
| Calendar preserves a helper result, then chooses 020C for signed AX > 0; otherwise 0206 | `D7E5–D802`; helper semantics U; branch and register construction H |
| Binding interrupt and return synchronization points | `D800` INT E0, `D802` RET; H |
| DESK gets the existing E0 vector and records its ES:BX words | `37B0–37C1`; H instructions, no runtime value known |
| A nonzero old vector is checked for the nine-byte DESKMATE signature at old ES:BX+3 | `37C7–37D9`; literal `42A2–42AA`; H comparison, not proof of image identity |
| Signature equality takes a path around the set-vector instruction | `37DA–37E1 → 383A`; H; old-vector retention interpretation M |
| Alternative installation sets INT E0 to the bootstrap offset 004F | `37E2–37E9`; H; actual execution U |
| Bootstrap code entry corresponding to that offset | image-relative `0405:004F`, file `429F`; entry jump skips the signature; H arithmetic |
| Non-AH=4D bootstrap path loads DS and writes a core-call offset before a far call | `42CF–42F8`; CS:000E has MZ-relocated word 0456; slot segment at file `4774` has relocated word 0000; H conditional relationship |
| Conditional core AH=02 routing | `5C7–5CB → 618 → 65F`; H instructions, conditional on entry into this image's core |
| Selectors 06 and 0C share a **near-code** table entry | table file `686`, entries `693` and `69F`, both image offset `0505` → file `705`; H; not an export table |
| Shared entry preserves the selector | `705 → 2D65`, which stores AL at DS:0305 before replacing AX with DX; H; identical selector semantics **not** established |

The `65F` dispatcher takes the saved AL, caps it using the table's first byte
(`0D`), indexes the following near-offset words, stores the chosen word at
DS:0410, restores registers, and jumps through DS:0410. For 06 and 0C no cap
changes the index. This establishes a conditional dispatch relationship in
DESK.EXE, not Calendar's actual runtime destination.

## First unresolved edge and stopping rule

**The first unresolved edge in the actual Calendar chain is the INT E0 vector
at the instant file D800 executes.** In real mode its four bytes reside at
physical `000380–000383`. Neither the saved installation bytes nor the current
corpus supplies that runtime value or proves the absence of an incumbent or
later handler. The signature comparison does not authenticate a handler's
bytes. Stop the asserted request chain here.

The conditional DESK path above is a separately labelled static candidate.
Its module lookup also depends on mutable module state: the inspected slice
uses eight-byte name comparison (`2DC2`) and pointer-bearing entries, including
the table scan at `2D9D–2DAE` (DS:0180, stride 0B, up to 20hex entries).
At `2DB7`, a near call enters `2C61`: POP AX and MOV BX,AX retain the
continuation at `2DBA` as an internal iteration callback; CALL BX at `2C78`
can invoke that comparator. This is an internal name-comparison continuation,
**not a DMDB export**. The first unvalued pointer in this conditional lookup
is the LES SI,[DI+2] at `2C6F`, with DI starting at 0180 and stride 0B.
The values and history of these entries at Calendar binding time are unknown.
Do not choose an occupied/free entry, loaded module, export or callback from
those facts. No loader API name, DMDB.R89 callback selection or forwarding to
DMDBRD is asserted. The older descriptor pointers remain candidates only.

This is an evidential static stopping point, not proof that a fuller loader
reconstruction is impossible. Chasing reader code would not resolve the missing
runtime state. The report does not close issue 25 as a successful binding.

## Minimal future read-only observation plan

This plan was **not executed**. Use a validated disposable emulator and the
same input hashes. No software breakpoints, guest patches, API calls, database
writes or speculative physical addresses. Instruction synchronization needs a
separately validated debugger facility; millisecond automation stepping cannot
guarantee these boundaries.

1. Establish the module load paragraph and code identity from the loader/debugger
   before arming non-writing execution breakpoints. Validate both the relevant
   instruction bytes and the loaded-image mapping; a four-byte sentinel alone
   is insufficient. In ordinary real mode, image file offset `f` maps to
   `16*L + f - H`, where `L` is the **observed** load paragraph and `H` the
   MZ header size. A segment address is `(L+s):o`; its physical candidate is
   `16*(L+s)+o`, subject to the validated CPU mode/A20 mapping. A file offset
   is never itself a physical address. Calendar's conditional DS paragraph is
   `L+0E87`, with `H=0200`; verify actual DS rather than assume it.
2. Halt immediately before Calendar's binding INT at file `D800`. Capture
   CS:IP, FLAGS, AX/BX/CX/DX, SI/DI/BP, DS/ES/SS:SP, mode/segment bases,
   the four bytes at original Calendar DS:2A62, five bytes at ES:DX, and the
   four-byte IVT E0 vector. Require BX=2A62, DX=2944, ES=DS and DMDB+NUL;
   record whether AX is 0206 or 020C. Save a bounded stack window privately
   if needed to verify the return boundary.
3. Stop at the first instruction of the IVT-selected handler, before it runs.
   Capture CS:IP and at most 32 code bytes, plus the same vector. Compare the
   bytes with the candidate bootstrap **accounting for MZ relocation**. A
   different address/byte identity establishes a different handler or hook;
   stop and identify it before using the DESK candidate route.
4. Stop on return to the instruction at Calendar file `D802`, before RET.
   Capture registers/FLAGS and the four slot bytes using the **saved Calendar
   DS**, even if the handler changed DS. A changed pointer identifies a
   candidate binding; unchanged sentinel plus failure flags/result distinguishes
   a failed or deferred operation. Do not guess the return-code convention.
5. Stop before the first selected thunk CALLF at file `DEAD`, capture current
   registers, saved-DS slot and current-DS slot, and ES:BX transport context.
   Then stop at the selected far target before its first instruction. Compare
   the pointer and target bytes with the loaded-module map and both relocated
   DMDB descriptor candidates. A third address distinguishes a trampoline or
   another export. Only this target observation establishes which callback was
   selected; no downstream reader behavior follows from it alone.

Each stop must have one identity/epoch, reset counters and a consistent held
state. Capture registers and memory without resuming between them. Abort on
reset, reconnect, lost identity, mode change or inability to stop exactly. Keep
all guest bytes/screenshots/paths private; publish only authored conclusions.

## Validation and preservation

Six focused private tests constrain original hashes, signed branch targets,
vector installation alternatives, MZ segment relocations and the conditional
near-code dispatch. They do not simulate a loader or establish a runtime API.
Run with explicit DOSLAB_ROOT and PYTHONPATH=src:

```text
python -B -m unittest discover -s tests/private -p test_calendar_service_binding.py -v
```

Recovery's preservation comparison matched 11,390 of 11,392 watched files and
all 125 inherited guards. Two pre-existing DeskMateCodex metadata files (lock
and project properties) differed across the interruption; an existing MCP
launcher was present at recovery. Their cause is unproved. No restoration or
edit was attempted, and original database/binary/project-database evidence
matched the watched baseline. This exception must accompany any preservation
claim; the historical baseline is retained unchanged.
