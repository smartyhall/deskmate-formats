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

A run ends in exactly one state, and each state maps to its own process exit
code. Failure is never folded into a success record.

| Status | Exit | Meaning |
| --- | --- | --- |
| `ok` | 0 | Import, optional analysis and optional reopen verification all passed |
| `usage_error` | 2 | The request itself was refused before any JVM started |
| `import_failed` | 3 | The program was not loaded, or did not match its expected digest |
| `import_timeout` | 4 | A worker stage exceeded its timeout and was terminated |
| `analysis_failed` | 5 | The program imported, but Ghidra autoanalysis raised |
| `reopen_failed` | 6 | The stored program could not be reopened or identified |
| `reopen_mismatch` | 7 | The reopened program differs from the imported one |

`reopen_mismatch` is deliberately separate from `reopen_failed`: "I could not
check" and "I checked and it is different" are different facts about the
artifact.

## What the receipt records

* Input name, size and SHA-256, the requested digest and whether it matched.
* Requested language and the **resolved** language read back from the imported
  program, with processor and compiler spec.
* Ghidra application version, build date, revision, Java runtime and PyGhidra
  version, read from the installation rather than assumed.
* Per-stage wall-clock timings.
* Block geometry, instruction and function counts, and a content fingerprint.
* For reopen: every attempt, the reopened summary, the comparison, and the
  project file listing.

The **content fingerprint** is a SHA-256 over each memory block's name, range,
size, initialization flag, and its bytes (or the literal `uninitialized`).
Summaries can agree while bytes differ; the fingerprint is what makes the
reopen check an identity check.

## Review findings and their resolutions

### 1. Lock removal relied on "this invocation created the project"

The earlier driver deleted `NAME.lock` when its own `created_project` flag was
set. That flag says nothing about ownership at the moment of deletion, and
Ghidra may still be releasing the lock in its shutdown sequence.

Measured behaviour on the qualification host (Ghidra 12.1.4, Windows):

* a clean import worker exit leaves `desk3.lock` visible for a moment —
  `lock_after_exit.present` was `true` in the run recorded at
  `receipts/desk-reopen-v4.json`;
* the next JVM that opens the project closes it cleanly and the lock is gone —
  `reopen.lock_after.present` was `false` in the same receipt;
* reopen succeeded on its **first** attempt in both full runs, with no lock
  file touched.

So no deletion is needed for the normal lifecycle, and deletion would be
actively harmful: if another worker did own the project, removing the lock
would disable the only protection against concurrent writers.

The driver now never deletes a lock. It samples lock state as a diagnostic
(`lock_after_exit`, `reopen.lock_after`), retries a locked reopen with bounded
backoff, and offers `--quarantine-stale-lock`, which **renames** a lock aside
for the operator who has independently established that no process owns it.
An existing project is refused unless `--allow-existing-project` is passed,
because opening someone else's project may adopt their program or their lock.

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
mismatched identity, byte drift, missing program, lock reporting and
quarantine. `tests/portable/test_dosimage.py` adds the headerless-input,
far-pointer, block-size and range-validation cases.

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
python tools/ghidra/ghidra_dos_import.py --project-dir PRIVATE/projects \
  --project cal --input CALENDAR.PDM --expect-sha256 <digest> --analyze \
  --reopen-check --timeout 600 --python <venv-python> \
  --output PRIVATE/receipts/cal.json
```

`--python` names the interpreter for worker stages and defaults to the current
one, so a run is reproducible from a single environment unless PyGhidra lives
in a dedicated one.
