# Programmatic Ghidra access: qualification (2026-11-26)

This note records what the campaign established about driving Ghidra
programmatically beyond a single import: the decompiler, function and
cross-reference enumeration, persistent annotations inside transactions, two
independent imports at once, interrupted imports, real historical executables
and resource cost.

Two categories are kept apart throughout:

* **observed** — a fact about the file (hash, bytes, offsets) or about a run
  (stage timings, exit status, a stored digest);
* **Ghidra-derived** — function boundaries, `FUN_*` names, decompiled source
  and the decompiler's variable model. These are the tool's conclusions about
  the bytes, not program metadata, and nothing here promotes them to original
  structure.

Tools: [`ghidra_dos_import.py`](../../tools/ghidra/ghidra_dos_import.py) and
[`ghidra_program_report.py`](../../tools/ghidra/ghidra_program_report.py).
Configuration: Ghidra 12.1.4 (build 2026-Sep-21, revision
`8b6bbb857accdfa20dc5b2f5dea471178c2e9fbc`), Temurin 21.0.13, PyGhidra 3.2.0,
`x86:LE:16:Real Mode`. The same surface was re-qualified under Ghidra 12.2 and
Temurin 25, with identical counts, fingerprints and decompiled text; see
[`ghidra-12.2-qualification-20261126.md`](ghidra-12.2-qualification-20261126.md).
The measurements below are the 12.1.4 baseline and are kept as such.

## Real historical executables

Each was imported with `--analyze`, saved, and reopened in a second process.

| Image | SHA-256 (prefix) | Instructions | Functions | Thunks | Blocks | Wall clock | Reopen |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `DESK.EXE` | `0f2a4024…` | 4,660 | 170 | 1 | 9 | 33 s | match |
| `CALENDAR.PDM` | `819df565…` | 24,154 | 508 | — | 6 | 70 s | match |
| `FIL2DBF.EXE` | `55bbb869…` | 4,405 | 161 | — | 9 | 27 s | match |
| `DBREPAIR.PDM` | `e1922f36…` | 4,596 | 139 | — | 5 | 29 s | match |

The four images differ by more than an order of magnitude in analysis work
(4.4k to 24.2k instructions) and in block structure (5 to 9 loader blocks),
which is what makes them useful as a sample rather than a single stub. All four
reopened with an identical content fingerprint, so persistence is not specific
to the smallest image.

`DESK.EXE`'s function-size distribution (170 functions) is 56 at 1–16 bytes,
70 at 17–64, 38 at 65–256 and 6 at 257–1,024. A 16-bit real-mode binary of this
kind is mostly small routines; a single average would hide that.

## Decompiler access

`ghidra_program_report.py --decompile NAME|ADDR` drives `DecompInterface`
directly. For `FUN_1000_0009` in `DESK.EXE`:

* completion: yes;
* signature: `void __cdecl16far FUN_1000_0009(void);`
* 21 lines, 380 characters, 141 ms;
* the source text was written to a private file, and the receipt carries only
  its SHA-256, character count and line count.

Decompiled source is proprietary output; it stays in the private lab. The
receipt records enough to prove a decompilation happened and to detect a change
between runs (the text digest) without publishing the text.

The decompiler's signature and `FUN_*` name are Ghidra's model. They are
reported as such and are not used to name anything in our own specifications.

## Functions and cross-references

`--functions` enumerates `FunctionManager.getFunctions(true)` with entry point,
name, body size, thunk flag, external flag and calling convention.
`--xrefs ADDR` enumerates `ReferenceManager.getReferencesTo`, with source
address, reference type and source kind, capped at 200 rows with an explicit
`truncated` flag.

On `DESK.EXE` the reference to `1000:0000` has two referrers. That is a small
number, and it is the reason the campaign does not treat xref counts as
coverage: a 16-bit real-mode program computes most of its targets through
segment registers and far pointers, which a static reference database does not
resolve. `--xrefs` is a navigation aid, not a reachability proof.

## Annotations and transactions in an owned project

The probe writes a plate comment, a bookmark and a `USER_DEFINED` label at the
image base inside one transaction, saves, closes, and then verifies from a
**separate process**:

```text
annotate        committed=True saved=True address=1000:0000
annotate-verify plate_comment="campaign annotation probe 2026-11-26"
                bookmarks=[Note/campaign-probe] symbols=[probe_label]
                persisted=True
```

Three things follow. Transactions and saves work on a program loaded through
`DomainFile.getDomainObject`; the annotation survives project close; and the
verification is meaningful only because it happens in a new JVM. An in-process
reopen would read Ghidra's cache and prove nothing, which is the same reason
reopen verification is a separate process in the import driver.

The probe never annotates a project it did not create for the purpose. Comments
and labels change stored state, and a research project that is also evidence
must not be mutated to demonstrate that mutation works.

**Later contract change, recorded rather than applied to the observation.** The
run above used the plate text `campaign annotation probe 2026-11-26` and judged
persistence from a nonempty plate plus the label. Since 2026-11-27 the tool
stamps the plate and bookmark comment with the annotate attempt identifier,
records the values it wrote, and requires `--verify-annotation` to be bound to
that receipt, comparing address, plate, bookmark category and content, and
label separately; see
[the procedure contracts](ghidra-procedure-contracts.md#annotation-verification-is-a-comparison-not-a-presence-test).
The paragraph above is the historical record of the earlier contract. It was not
re-run, and it is not evidence that the strengthened comparison was exercised
natively.

## Two independent imports at once

Two imports of different images into **different** projects in the same
directory completed successfully in 22 s wall clock, both with `status: ok`
and their own block structure (9 and 6 blocks).

Two imports of different images into the **same** project name raced: one
completed, the other exited `import_failed` with a worker exit code, and the
winner's program was intact (9 blocks, the `DESK.EXE` image). The refusal is
loud, but the message is generic because both workers passed the
"project exists" check before either created it.

The supported contract is therefore explicit: **one worker per project**. The
driver refuses an existing project by default, which closes the ordinary
mistake (importing over someone else's program); it cannot make two workers
that start at the same instant safe, and does not claim to.

No speedup is claimed for the concurrent case: a serial baseline was not
measured in the same window, so 22 s for two imports is a correctness result,
not a performance one.

## Interrupted imports

`--timeout 22` on `DESK.EXE` terminated the worker during autoanalysis and
produced `status: import_timeout`, exit 4, a lock file still present, and the
guidance that the project is in an unknown state and must be discarded.
`--timeout 5` terminated during JVM start with the same status and no lock.
Both receipts record `lock_after_failure`.

The driver does not attempt to repair an interrupted project. A half-written
Ghidra project is not evidence, and "recovered" bytes from one would be
indistinguishable from analysis state.

## Resource consumption

| Item | Measured |
| --- | --- |
| Cold first run of the day, `DESK.EXE` | 195 s (JVM start 79 s, import 13 s, analysis 34 s) |
| Warm `DESK.EXE` | 33 s (JVM start 10.5 s, import 3.4 s, analysis 11.9 s, save 0.4 s) |
| `CALENDAR.PDM` (24k instructions) | 70 s |
| Stored project, per image | 2–3 MB |
| Receipt | 4–5 KB |
| Decompile, one function | 141 ms |

JVM start dominates at this scale, so batching many images into one worker
would be the obvious optimisation; it is not implemented because it would make
one failure take down unrelated imports and would let one project's state leak
into another's run.

## Bounds

* Analysis output depends on the Ghidra version. Receipts record version,
  build date and revision so that a difference can be attributed rather than
  guessed.
* Autoanalysis is opt-in and is not required for byte-level probes; an
  unanalysed program has blocks but no instructions (the concurrent imports
  above show `instruction_count: 0`).
* Function boundaries are Ghidra's model. A missing function is not evidence
  that no code exists there.
* Nothing here validates runtime behaviour. Membership of a routine in a
  service call chain, a text buffer's runtime address or a file's on-disk
  meaning still needs native observation.

## Reproducing

```text
python tools/ghidra/ghidra_program_report.py --project-dir PRIVATE/projects \
  --project desk --program DESK.EXE --summary --functions --limit 25 \
  --decompile FUN_1000_0009 --text-output PRIVATE/exports/dec.txt \
  --output PRIVATE/exports/report.json
python tools/ghidra/ghidra_program_report.py --project-dir PRIVATE/projects \
  --project probe --program DESK.EXE --annotate "note" \
  --output PRIVATE/exports/annotate.json
python tools/ghidra/ghidra_program_report.py --project-dir PRIVATE/projects \
  --project probe --program DESK.EXE --verify-annotation \
  --annotation-receipt PRIVATE/exports/annotate.json
```

`--program` takes the project path without a leading slash; on Git Bash a
leading `/NAME` is rewritten into a Windows path before the script sees it.
