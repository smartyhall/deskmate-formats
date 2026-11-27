# Native procedure handoff for the Supervisor and Observatory

2026-11-27. Durable description of the native emulator procedures this campaign
qualified, written so the deterministic-execution campaign can decide whether to
register them. Nothing here registers a procedure, changes the Supervisor or
authorizes unattended operation; it records what a caller would have to supply
and what the procedure would have to prove.

The two procedures are deliberately different in kind:

* `deskmate.dos.command/1` is read-only from the guest's point of view: it types
  and submits one command line at a DOS prompt.
* `deskmate.note.write/1` mutates persistent guest state: it replaces the text of
  the shared Corkboard/Note Pad store.

## Common requirements

| Field | Requirement |
| --- | --- |
| Execution mode | One exclusively owned emulator process, visible window, authenticated loopback socket |
| Emulator capabilities | Stock builds: none. Instrumented builds: `input_queue`, `event_seq`, `wait_queue`, `input_accounting` for queue evidence; absence is reported, never assumed |
| Guest profile | Text-mode DOS prompt at a known anchor (`C:\>`-shaped), 80×25 text mode, BIOS keyboard ring readable through `memr` |
| Application profile | For the note: DeskMate desktop rendered, Corkboard reachable through the F10 Accessories menu |
| Typed arguments | Command string (ASCII, validated before any input); note text (ASCII + CR, validated) |
| Input identity | Caller-supplied anchor/occurrence; the procedure refuses an ambiguous anchor |
| Authorization | Operator authorization for live emulator work; exclusive reservation of machine, socket and guest image |
| Resource ownership | The procedure owns the process, the socket and the guest image for its duration and releases them at the end |
| Persistent mutation | `dos.command` none; `note.write` writes `DESKMATE/DMCORKBD` |
| Expected duration | Boot to prompt ≈ 9 s emulated; one command ≈ 0.2–0.5 s; a 31-character note ≈ 1 s plus accessory open/close |
| Artifacts | JSON report with per-burst evidence, ring and queue samples, cursor readings, frame digests; the caller keeps raw captures privately |

## `deskmate.dos.command/1`

Progress observations: command line observed at the anchor with the cursor at
its end, Enter submitted, a new prompt at the bottom row with the cursor at its
end, expected output matched only in rows the pre-Enter screen cannot explain.

Terminal outcomes: `observed` (entry, prompt and output), `output_missing`
(entered and prompt returned, output absent), `unknown` (Enter sent, no new
prompt, or the guest left text mode), `withheld` (entry not verified, nothing
submitted), `pending` (input still queued).

Cancellation: safe before Enter. After Enter, cancellation means observing and
reporting, never replaying: the command's execution state is unknown.

Timeout: per-command prompt budget (default 30 s emulated), then `unknown`.

Trustworthy automatic recovery: only the entry stage may be resumed, and only
when the observation is a strict prefix, the ring is empty, the automation queue
is drained, the anchor is still at its original row and column, and the cursor is
at the end of that prefix. Execution is never retried.

## `deskmate.note.write/1`

Progress observations: Corkboard open (frame digest captured in the session),
per-keystroke ring advancement, the cursor at the end of the typed text, and the
persisted document extracted after the accessory is closed.

Terminal outcomes: `observed` (text verified on screen and in the extracted
document), `screen_only` (text verified, document not yet extracted),
`ambiguous` (text differs, or the anchor moved), `partial` (a verified prefix only).

Cancellation: safe while the note is unmodified; after input, the procedure
reports the verified prefix and leaves the note open rather than pressing keys to
undo it.

Timeout: per-character settle budget plus an accessory open/close budget.

Trustworthy automatic recovery: **not qualified.** Recovery of a partial note
needs the same ring/queue/cursor gate as text entry, plus a way to prove the
application has stopped consuming earlier keystrokes. Burst delivery can overflow
the guest BIOS ring (peak 15 of 15 measured), so the procedure must use
`chunk=1` with a settle step and must not be run unattended until a partial note
can be reconciled with the persisted document.

Evidence requirements: the persisted record's SHA-256, its header words, the
text bytes, the exact typed text and the per-character evidence. A screen
digest alone is not acceptance.

## Uncertainty semantics

| Situation | Reported as | Not reported as |
| --- | --- | --- |
| Socket reply only | `acknowledged` | delivery |
| Interface forwarded every event | `delivered` + accounting identity | guest consumption |
| Ring observed holding then empty | `translated` | application acceptance |
| Ring unreadable | `withheld` | success with a null observation |
| Screen matches, ring still holds input | `pending` | observed |
| Guest leaves text mode | `unknown` (left text screen) | prompt returned |
| Document differs from screen | `ambiguous` | success |

## Status

Both procedures exist as experiment drivers
([`input_delivery_qualification.py`](../../tools/experimental/input_delivery_qualification.py),
[`corkboard_header_probe.py`](../../tools/experimental/corkboard_header_probe.py)),
not as registered Supervisor procedures. Registering them would need a reviewed
adapter, a durable recipe format, and the partial-note reconciliation above.
