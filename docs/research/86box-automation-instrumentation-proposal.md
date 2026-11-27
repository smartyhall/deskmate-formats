# Instrumentation proposal: emulator evidence for input delivery

2026-11-26. Proposal only, prepared from the pinned automation source at
`C:/DeskMateLab/sources/86Box` (revision `855258da9`). No shared production
executable was modified; any trial build must live in its own directory with its
own provenance.

The verified input facility can prove four different things, but only one of them
comes from the emulator: that the `key` reply arrives after the last event's gap.
Everything after that is inference from guest memory or pixels. Three concrete
gaps are worth closing in the automation interface, and one is not closable
there at all.

## What the interface has today

- `key down|up <scan>...` is a timed command: it forwards the first event,
  emits the rest `KEY_GAP_MS` (2) emulated milliseconds apart, and replies from
  `end_timed` after the last event. The reply carries `ms`, `frames` and `held`.
- `KEY_QUEUE_MAX` (64) bounds an internal event queue that is not reported.
- `status` reports `ms`, `frames`, `held`, `paused`, `ff`, `w`, `h`, `bios_mode`
  and `quantum_ms`; there is no keyboard or pointer state.
- `text` already returns the BIOS cursor as `[row, col]`, which this campaign uses
  for insertion-point verification.
- `mouse <dx> <dy> <buttons>` applies relative motion; the emulator does not
  track where the guest drew the pointer.

## Proposal 1: report the delivery queue

Add to the `key` reply and to `status`:

```json
{"ok":true,"ms":1234,"frames":56,"held":true,
 "events":8,"queue":0,"capacity":64,"seq":17}
```

- `events` counts events accepted by this request.
- `queue` is the occupancy of the automation key queue after dispatch.
- `seq` is a monotonic counter over accepted input requests.

This turns "we sent it" into "the device queue accepted it and here is the
backlog", without pretending anything about the guest. It is also the only way
for a client to distinguish a slow emulated device from a slow guest.

Suggested edit points: the queue declaration near `src/automation.c:184`, the
`key` handler near `:2109`, and the quantum dispatch near `:2597`; the status
reply is assembled where `bios_mode` and `quantum_ms` are written.

## Proposal 2: a `wait queue` completion event

```
wait queue <timeout_ms>
```

Run until the automation key queue is empty, then reply with `drained`, `ms`,
`frames` and the number of events retired. A client that sends a burst and waits
for this knows the device has consumed it, which is a stronger statement than a
timed reply and a weaker one than guest acceptance. Today the only way to wait is
to poll `status` and hope the reply cadence does not change.

## Proposal 3: delivery counters and drops

Count events passed to `keyboard_input()` and events refused because the queue
was full, and expose both in `status`. A refused event is currently invisible: the
`key` command returns `ok` after the queue accepts it, so an overflow in a long
burst would be a silent loss. This is the counter that would let a client prove
"no event was dropped in the emulator" rather than assume it.

## Proposal 4: pointer position, or an explicit refusal

Relative `mouse` input cannot tell a client where the pointer is, and the
campaign measured why that matters: a 200-pixel move produced four separate
changed regions in DeskMate, so frame differencing could not localise the pointer.
Two honest options:

1. Report the accumulated relative motion and the configured scale
   (`mouse state` → `dx`, `dy`, `scale`, `buttons`). This lets a client that
   starts from a known homed position aim, and admits the emulator does not know
   the guest's drawing position.
2. Report nothing and document that pointer targeting needs a device with
   absolute coordinates (a tablet or touch screen already has `tablet <x> <y>`).

Option 1 is cheap and sufficient for aiming from a homed corner; option 2 is
honest but leaves the capability out. The facility records pointer events as
`delivered` plus a frame change either way.

## Proposal 5: video state for observation

A `video` command returning mode, page, cursor and the active text/graphics
dimensions would let a client decide how to observe without a `text` call that
fails in graphics modes. `text` already returns most of this in text modes; a
standalone `cursor` command would be useful when only the insertion point is
wanted and the full screen is expensive to transfer.

## What the emulator cannot provide

- Application semantics. No emulator can know that a dialog's field received the
  intended text; that needs a profile with field-level evidence.
- Guest acceptance attribution. The BIOS ring records translated keystrokes, not
  which program read them, and a program that hooks `INT 09h` bypasses it.
- Pointer hit-testing. Position plus a click still does not prove a control was
  activated; only an observed state change does.

## Qualification plan for any trial build

1. Build separately (`builds/86box-automation-<tag>`), record the source
   revision, compiler and executable hash, and keep the production executable
   untouched.
2. Replay the existing portable client tests against the new replies; absent
   fields must stay absent rather than defaulting to zero.
3. Measure the same native sequence as this campaign: type-ahead during a long
   write, a burst that fills the queue, and a held machine with an empty queue.
4. Verify that `events`, `queue` and `seq` agree with the guest ring
   (proposal 1) but never claim acceptance for them.

## Integration with the Supervisor and the Observatory

A separate campaign owns those systems; this is an interface proposal only.

- Supervisor dispatch could require a structured receipt per input operation:

  ```json
  {"operation":"type_text","profile":"dos-prompt","target":"C:\\>",
   "evidence":{"acknowledged":true,"delivered":true,"accepted":true,"observed":true},
   "observed":"VER","bursts":1,"recoveries":0,"emulated_ms":278,
   "status":"observed"}
  ```

  A gate can then demand `evidence.observed` for steps whose failure would
  corrupt evidence, and stop on `pending` or `ambiguous` rather than retrying.
- The Observatory journal could record `status` transitions with the profile name
  and frame digest, so a later review can re-derive why a step was accepted.
- Both should treat the four evidence fields as independent: a `pending` result
  with `accepted: null` must not be recorded as a delivery failure, and an
  `observed` frame with `accepted: null` must not be recorded as guest
  acceptance.

The facility already emits this shape from `Report.as_dict()`; no provider-specific
data is involved.
