# Deterministic DOS import receipts (2026-11-26)

The Ghidra import driver in [`tools/ghidra/ghidra_dos_import.py`](../../tools/ghidra/ghidra_dos_import.py)
turns one stored DOS image into one analysed Ghidra program and writes a
receipt that says what happened. This document states what the receipt now
promises, records the evidence for each promise, and bounds the claim: it
qualifies the procedure as reproducible on a measured configuration, not as
correct on every image.

The loader model and the qualification runs behind it are in
[the DOS binary analysis note](ghidra-dos-binary-analysis.md).

## Result states

A run ends in exactly one terminal outcome, recorded in `outcome`, and each
outcome maps to its own process exit code. Failure is never folded into a
success record.

| Outcome | Exit | Meaning |
| --- | --- | --- |
| `succeeded` | 0 | Import, optional analysis and optional reopen verification all passed |
| `invalid_request` | 2 | The request itself was refused before any JVM started |
| `input_mismatch` | 2 | The input digest did not match `--expect-sha256`; no worker was started |
| `import_failed` | 3 | The program was not loaded, or the worker produced no readable receipt |
| `import_timeout` | 4 | A worker stage exceeded its timeout and was terminated |
| `analysis_failed` | 5 | The program imported, but Ghidra autoanalysis raised |
| `reopen_failed` | 6 | The stored program could not be reopened or identified |
| `reopen_mismatch` | 7 | The reopened program differs from the imported one |
| `receipt_malformed` | 8 | The worker's receipt failed schema or identity validation |
| `receipt_inconsistent` | 8 | The receipt claimed success while the worker process exited nonzero |
| `persistence_failed` | 9 | Analysis finished but the program was not durably stored |

`reopen_mismatch` is deliberately separate from `reopen_failed`: "I could not
check" and "I checked and it is different" are different facts about the
artifact. `receipt_malformed` and `receipt_inconsistent` are separate from
`import_failed` for the same reason: a receipt that cannot be trusted is not
an import that failed, and the two need different investigation.

## What the receipt records

* The **attempt**: a 32-hex identifier chosen per invocation, the start time in
  UTC, the worker PID, and the attempt's private working directory. A receipt
  that does not carry this attempt's identifier is rejected, so a file left by
  an earlier run cannot stand in for this one.
* Input name, size and SHA-256, the requested digest and whether it matched.
* The request as received (language, analyze, project name and directory) and
  the **resolved** language read back from the imported program, with processor
  and compiler spec plus whether it matched the request.
* The toolchain as requested and as resolved: Ghidra install directory,
  application version, build date, revision, minimum Java, Java runtime, Java
  VM and PyGhidra version, read from the installation rather than assumed.
* Project identity (name, directory, and whether it existed before this
  attempt) and program identity (project path and content fingerprint).
* Persistence: `save` and `close` recorded separately, each `ok` or `failed`
  with the error text.
* The worker record: exit code, receipt path and the SHA-256 of the receipt
  bytes as published.
* Per-stage wall-clock timings.
* Block geometry, instruction and function counts, and a content fingerprint.
* For reopen: every attempt, the originating attempt identifier, the reopened
  summary, the comparison, and the project file listing.
* Lock samples (`lock_after_exit`, `lock_after_failure`, `reopen.lock_after`),
  each stating that presence alone establishes no ownership and that no action
  was taken.

The **content fingerprint** is a SHA-256 over each memory block's name, range,
size, initialization flag, and its bytes (or the literal `uninitialized`).
Summaries can agree while bytes differ; the fingerprint is what makes the
reopen check an identity check.

## Review findings and their resolutions

### 1. Lock removal relied on "this invocation created the project"

The earlier driver deleted `NAME.lock` when its own `created_project` flag was
set. That flag says nothing about ownership at the moment of deletion, and
Ghidra may still be releasing the lock in its shutdown sequence.

Measured behaviour on the qualification host (Ghidra 12.1.4 and 12.2, Windows):

* a clean import worker exit leaves `desk3.lock` visible for a moment —
  `lock_after_exit.present` was `true` in the run recorded at
  `receipts/desk-reopen-v4.json`;
* the next JVM that opens the project closes it cleanly and the lock is gone —
  `reopen.lock_after.present` was `false` in the same receipt;
* reopen succeeded on its **first** attempt in both full runs, with no lock
  file touched;
* the same held under 12.2: `DESK.EXE` and `CALENDAR.PDM` each imported with
  `--analyze` and reopened on the first attempt (`receipts-122/desk.json`,
  `receipts-122/cal.json`, both exit 0).

So no deletion is needed for the normal lifecycle, and deletion would be
actively harmful: if another worker did own the project, removing the lock
would disable the only protection against concurrent writers.

**The quarantine flag is gone.** A follow-up review observed that
`--quarantine-stale-lock` renamed a lock on *presence*, which an explicit flag
does not turn into proof of staleness: the owner could be a live worker whose
run this sample merely raced, and moving its lock would corrupt its project.
Nothing in the reference temperature, timestamp or owner record of a lock file
establishes that no process holds the project, so the driver now offers no
reclamation at all. It samples lock state as a diagnostic
(`lock_after_exit`, `lock_after_failure`, `reopen.lock_after`) with
`ownership_established: false` and `action_taken: "none"`, and retries a locked
reopen with bounded backoff. A test asserts both that the function is absent
and that the flag is rejected by the parser.

Recovery, if it is ever wanted, has to be a separately reviewed operation whose
prerequisites positively establish that the project is unowned — for example a
recorded owning PID that no longer exists plus an operator assertion about the
same host — and it must not share a code path with ordinary import or reopen.

An existing project is still refused unless `--allow-existing-project` is
passed, because opening someone else's project may adopt their program or their
lock. A **reopen-only operation never creates a project**: `_open_existing`
raises `project_missing` instead of falling through to `createProject`, so a
verification cannot report success about a project that did not exist.

One real lock outlives its JVM in the campaign's own evidence:
`private-evidence/ghidra-integration-20261126/projects-122/` still holds
`segforms122.lock` and `segforms122.lock~`. It is left exactly where it is. Its
presence is consistent with an interrupted or terminated probe, and nothing in
it proves the probe's process is gone; treating it as reclaimable would be the
same unfounded inference the review objected to.

### 2. Failed autoanalysis became a successful receipt

`pyghidra.analyze()` previously ran inside a `try` that recorded the exception
in `analysis` while leaving the receipt `ok`. Autoanalysis failure now sets
`analysis_failed`, keeps the failure text, and exits 5. `tests/portable/test_ghidra_driver.py`
asserts the status is not `ok` and that analysis is marked unsuccessful.

### 3. Reopen verification recorded two summaries without comparing them

`reopen_only()` returned a summary and the driver copied it into the receipt.
The driver now compares language, compiler spec, image base, minimum and
maximum address, block count and the content fingerprint, and reports each
differing field with its before and after values. Any difference is
`reopen_mismatch` with exit 7. Tests cover a byte difference behind an
otherwise identical summary, a different program identity, a missing program
and a reopen timeout.

### 4. Timeouts were not enforced for ordinary imports

Only the reopen stage ran as a bounded child; the import itself ran in the
driver process, so `--timeout` did not bound it. The import now **always** runs
in a worker process under `subprocess.run(timeout=…)`, and the driver kills the
worker when the timeout expires. Measured: `--timeout 22` on `DESK.EXE`
terminated mid-analysis with status `import_timeout` and exit 4; `--timeout 5`
terminated during JVM start. Both receipts carry guidance that the project is
in an unknown state and must be discarded rather than reused as evidence.

The timeout bounds the worker process, not arbitrary grandchildren. Ghidra runs
in one JVM here, so that is the whole job; the limit is stated rather than
implied.

### 5. Arbitrary bytes were reported as a COM executable

A COM program has no header, magic number or length field, so *every* byte
sequence is a valid COM load image. Reporting `format: com` from structure was
therefore not an observation at all.

`dosimage.identify(data)` now returns `format: unknown` with `com_candidate:
true`, no entry point, and a scope note that the COM reading is an assumption.
Passing `interpretation="com"` — or `--interpretation com` on the CLI — adopts
IP=0100h explicitly and marks the result `interpretation: explicit`. The
`blocks`, `map` and `disasm` commands refuse a headerless input without it.

### 6. The far-pointer CLI mapped targets outside the image

`command_far` called `image_to_file()` on any resolved pointer. For a pair that
resolves past the stored image, that raised and aborted the whole report.
`far_pointer_file_offset()` now returns `None` outside the image, and the CLI
reports `resolved_inside_image: false`, `resolved_file_offset: null` and a note
saying the target is in another segment, an overlay or unrelated data. The
synthetic specimen's relocated pair resolves to image offset `C100h` in a
`200h`-byte image and is covered by a regression test.

### 7. Loader-block arithmetic could go negative

The far-return adjustment moved bytes from one block's head to the previous
block's tail and then did `previous["uninitialized_size"] -= moved`. Because a
stored MZ image has no uninitialized bytes, that count started at zero and went
negative — the defective receipt recorded `-1`.

Moved bytes are file bytes, so the previous block's initialized size grows and
its uninitialized size does not change. The driver's model now recomputes
`uninitialized_size = size - initialized_size` after every adjustment and
raises if any size is negative. A test asserts the identity
`initialized + uninitialized == size` for every block and that the adjusted
block keeps an uninitialized size of zero.

### 8. Addresses, segments, identity and expected hashes were unchecked

* Project names must match `[A-Za-z0-9][A-Za-z0-9 ._-]{0,63}` and may not
  contain a path separator.
* Languages must be explicit identifiers with at least three parts.
* Timeouts must be positive and at most one day.
* `--expect-sha256` must be 64 hex characters and must match the input before
  the JVM starts.
* Inputs must exist, be regular files and be non-empty.
* The CLI rejects `--load-paragraph` and `--segment` outside `0000h`–`FFFFh`,
  segment offsets beyond `FFFFh`, negative file offsets, non-positive lengths
  and `--max-instructions`, spans past the input, and a far-pointer offset that
  does not address four bytes.

Each of these is covered by a portable test.

### 9. Regression coverage

`tests/portable/test_ghidra_driver.py` exercises the supervisor without a JVM:
usage refusal, digest mismatch, worker crash without a receipt, timeout and its
guidance, failed analysis, failed reopen, reopen timeout, locked-project retry,
mismatched identity, byte drift, missing program and lock reporting.
`tests/portable/test_dosimage.py` adds the headerless-input, far-pointer,
block-size and range-validation cases.

### 10. A predictable intermediate receipt could be inherited

The supervisor wrote its worker receipt to `<output>.import.json`, or to
`receipt.json.import.json` in the current directory when `--output` was absent.
Both names are fixed, so a worker that crashed before writing left the previous
invocation's successful receipt in place, and the supervisor read it as this
run's result. Nothing in the code proved the file had been written by *this*
worker.

Each invocation is now an attempt with a 32-hex identifier and its own private
working directory:

```text
<output>.attempts/<attempt-id>/import-worker.json
```

The directory is created with `exist_ok=False`, the identifier is passed to the
worker and echoed in the receipt, and the supervisor rejects a receipt whose
`attempt.id` differs. It also rejects a receipt whose `input.sha256` is not the
digest it computed itself, whose `requested.project` or `requested.project_dir`
is another project (compared with `realpath` and `normcase`, because Windows
can report one directory as either its long or its 8.3 short spelling),
and any receipt missing a field its outcome requires. Attempt directories are
left in place after failure, timeout and interruption: the partial receipt is
recorded as `partial_worker_receipt` with `used_as_result: false`, so the
evidence survives without being mistaken for an outcome. Nothing is deleted.

`--output` is now **required** in supervisor mode. A default name in the
working directory is shared state between invocations, which is exactly the
failure being removed.

### 11. Malformed receipts, and empties that compared equal

`compare_programs` compared whatever it was given. Two summaries that both
lacked the required fields agreed on nothing and reported `match: true`, so an
incomplete reopen payload could corroborate an incomplete import.

Validation is now explicit and per outcome (`REQUIRED_FIELDS`,
`validate_receipt`), and the comparison reports missing fields separately:
`complete` is false and `match` is false when any compared field is absent on
either side. A test asserts that `compare_programs({}, {})` is not a match.

### 12. Exit status, persistence and reopen identity are reconciled

Three separate gaps, all about a claim outranking the evidence for it:

* **Worker exit.** A receipt saying `succeeded` was accepted even when the
  worker exited nonzero. Success now requires both, and disagreement between a
  success claim and a nonzero exit is `receipt_inconsistent` (exit 8). The
  reverse direction is handled conservatively: a nonzero claim with a zero exit
  keeps its failure outcome and records `worker_exit_disagrees: true`. A test
  covers each direction.
* **Persistence.** `project.save()` and `project.close()` ran in a `finally`
  that recorded a `close_error` while leaving the outcome `ok`. Each stage is
  now recorded separately, and a failed save or close turns a successful import
  into `persistence_failed` (exit 9) whose receipt still says exactly what was
  and was not stored. A successful analysis followed by a failed save is not a
  stored analysis.
* **Reopen identity.** The reopen worker now receives the originating attempt
  identifier and the expected content digest, and echoes the identifier. A
  payload from another attempt, or a success payload from a worker that exited
  nonzero, is rejected rather than accepted as a restart of the comparison.
  The first version of this check still let a *missing* identifier through;
  finding 13 corrects it.

Receipts are published with `os.replace` after writing sibling temporary bytes,
so a reader sees either the previous complete file or this complete one. The
digest is computed over the published **bytes**: `write_text` would translate
newlines on Windows and the recorded digest would not describe the file.

### 13. A missing reopen identity was read as agreement

Follow-up review, 2026-11-27. `_run_reopen` compared
`payload.get("attempt_id") in (None, attempt["id"])`, so a payload that named no
attempt at all satisfied the check, and a zero worker exit plus `ok: true` then
established success. Two more weaknesses sat in the same few lines: `ok` was
tested for truthiness, so `"yes"` and `1` counted as success, and nothing
checked that the payload described *this* project or carried a program identity
at all.

* **Identity by absence.** Exact equality is required. A missing or null
  attempt identifier is a payload that does not belong to this attempt.
* **Literal booleans.** Success requires `ok is true`. Any other value,
  including a truthy one, is malformed. `validate_receipt` applies the same
  rule to the `match` and `complete` fields of a published reopen comparison.
* **A payload schema.** `validate_reopen_payload` now requires the schema and
  mode, this attempt's exact identifier, this project's name and directory,
  and — for a success claim — the literal `ok`, `program.project_path`, a
  well-formed `program.content_sha256` and `program.block_count`.

The reopen result vocabulary gained `reopen_malformed`, which the driver
reports as `receipt_malformed` (exit 8): the worker's own document could not be
trusted, so nothing this attempt produced may be presented as verified. A
well-formed payload describing *different* bytes is not malformed — it is
`reopen_mismatch` (exit 7), because the difference is the finding and the
comparison names the field. An unreadable payload is `reopen_failed` with
`reason: payload_unreadable`, and a failure payload from a worker that exited
zero keeps its failure outcome with `worker_exit_disagrees: true`.

`_run_reopen_single` no longer exists. The corresponding code is the
attempt-scoped worker `reopen_only`, which now also echoes the project identity,
the digest it was asked to corroborate, and whether it closed the project, so a
reopen that leaves the project open is visible in the receipt rather than
inferred.

Nine negative tests cover a zero-exit success payload with no attempt id, a
null attempt id, a foreign attempt id, truthy non-boolean `ok` values, a success
payload with no fingerprint, drifted bytes, another project, an unreadable
payload, and a failure payload from a zero-exit worker. Five more assert that a
published receipt whose `reopen` section claims `ok` without this attempt's
identifier, or without a literal `match`/`complete`, is rejected.

## Qualification as a deterministic procedure

Determinism here means: the same stored bytes and the same declared
configuration produce the same program facts and the same content fingerprint,
independent of when and how often the import runs.

Three separate imports of `DESK.EXE`
(SHA-256 `0f2a40243c997276904d2555a117c60eedf0016dde073285e8d63c8345a2eba3`)
with `x86:LE:16:Real Mode` and autoanalysis produced:

| Run | Instructions | Functions | Blocks | Content SHA-256 |
| --- | --- | --- | --- | --- |
| cold JVM | 4660 | 170 | 9 | `1ad71b7a57780048…` |
| warm JVM | 4660 | 170 | 9 | `1ad71b7a57780048…` |
| warm JVM, no reopen | 4660 | 170 | 9 | `1ad71b7a57780048…` |

The reopen check then compares a program written by one process with a program
read by another, so the fingerprint also covers persistence, not only analysis.

Cost on this host: 33 s warm, 195 s for the first run of the day, of which
JVM start was 10.5 s and 78.9 s respectively. Those numbers are properties of
the host and the image, not guarantees.

### What this does not establish

* Byte-for-byte reproducibility across **different** Ghidra versions. A
  version change may alter analysis results; the receipt records the version
  precisely so a comparison can be attributed.
* Correctness of Ghidra's interpretation. Disassembly text is the tool's
  reading; the original bytes and an independent decoder remain the evidence.
* Safety of a project left behind by a terminated worker. The receipt says so
  instead of implying the project is usable.

## Reproducing the checks

```text
python -m unittest tests.portable.test_ghidra_driver tests.portable.test_dosimage
# Toolchain selection and the program-report driver have their own suites:
# tests.portable.test_ghidra_toolchain and tests.portable.test_ghidra_report.

# Pick the toolchain from evidence, then run the import with it.
python tools/ghidra/ghidra_toolchain.py --profile ops/toolchains/ghidra-12.2.json
python tools/ghidra/ghidra_dos_import.py --project-dir PRIVATE/projects \
  --project cal --input CALENDAR.PDM --expect-sha256 <digest> --analyze \
  --reopen-check --timeout 600 --python <venv-python> \
  --output PRIVATE/receipts/cal.json
```

`--python` names the interpreter for worker stages and defaults to the current
one, so a run is reproducible from a single environment unless PyGhidra lives
in a dedicated one. On this host the lab interpreter has no PyGhidra and the
campaign venv reports `pyghidra 3.2.0`, so `--python` was pointed at the venv
for every measured run; both facts are recorded in the toolchain selection
record rather than inferred.
