# Bounded, verified guest input for 86Box automation

2026-11-26. Provider-independent improvement to the automation layer, with
portable tests and three authorized native sessions on a disposable clone.
Everything below was measured with the pinned automation build; nothing depends
on a model provider, an agent, or a hosted service.

The question was not "can we send keys". It was: after a key is sent, what can
the emulator, the guest BIOS, and the application each prove, and what should an
automation layer do when those proofs disagree?

## Four levels, not one

The protocol already distinguishes four things, and only the first is a fact
about the socket.

| Level | Evidence | What it proves | What it does not |
| --- | --- | --- | --- |
| Acknowledged | `{"ok": true}` reply | The emulator received the request | Nothing about the guest |
| Delivered | `key` reply after the last event's gap | The emulated keyboard device was handed every event | Nothing about the BIOS or an application |
| Accepted | BIOS keyboard ring drained (`0x40:001A` = `0x40:001C`) | The guest consumed the scan codes | That any program acted on them |
| Observed | A caller-supplied expectation is visible | The intended state change happened | Which code path caused it |

The delivery claim is source-verified, not inferred. `src/automation.c` treats
`key` as a timed command: it forwards the first event, emits the rest with
`KEY_GAP_MS` = 2 emulated milliseconds between them, and replies only from
`end_timed`, so the reply arrives after the final gap. The queue depth of 64
(`KEY_QUEUE_MAX`) is internal to that module and is not exposed, so the only
emulator-level acknowledgement available is that reply. There is no command that
reports how many events the guest keyboard device still holds.

Guest acceptance is readable, but weak. The BIOS extents at `0x40:0080`/`0x40:0082`
give a ring of `end - start` bytes holding one word per keystroke, and the
head/tail words at `0x40:001A`/`0x40:001C` give its fill. On this guest the ring
was already empty every time it was sampled: `COMMAND.COM` consumes typed
characters inside the same emulated millisecond. Acceptance is therefore a
negative test that can only fail loudly, never a positive proof that a program
ran.

## The facility

`src/deskmate_formats/automation/input.py` exposes `VerifiedInput` over the
existing client, with three operations and one recovery rule.

- `type_text(text, anchor=...)` splits the text into bounded bursts, sends each,
  drains the BIOS ring, then reads the characters after `anchor` on the anchored
  text row and compares them with the full intended string. `occurrence='last'`
  handles a scrolling terminal where the prompt recurs; `'only'` is the default
  and refuses to guess.
- `press(*codes, expect='change'|'restore', reference=...)` sends make/break
  events and compares a snapshot taken before and after. Restore is compared to
  a snapshot the caller kept, not to the state immediately before the press.
- `pointer(dx, dy, buttons, expect=...)` moves the configured mouse device and
  observes the frame.

Recovery is deliberately one case wide. After a burst, if what is on screen is a
strict prefix of the intended text, the missing suffix is sent again and the
whole string is re-verified. Anything else stops:

- an empty observation is reported `unchanged` and is **not** retried, because a
  swallowed keystroke and a keystroke delivered to the wrong focus look the same
  from the socket;
- an observation that diverges inside the intended text is reported `ambiguous`
  with the text from the first divergent character, because the missing input is
  then not a suffix and replaying would be guesswork;
- exceeding `max_attempts` is reported `ambiguous` rather than escalating.

Each attempt records the burst, the observed row, the BIOS ring depth and the
emulated time, so a report can be re-derived from the journal instead of trusted.

### Two snapshot bases

Graphics screens are compared by PNG digest, text screens by their character
rows. The distinction is not cosmetic: during the first native session, an F10
in DOS was reported as a screen change because the framebuffer changed. The cause
was the blinking cursor, which changes rendered pixels without changing any text.
Text-mode presses now hash the rows, where a blink does not appear, and the same
press correctly reports `unchanged` at the `delivered` level.

The second instrument lesson came from the same run. A settled frame is not a
drawn application: DeskMate clears to a perfectly stable black screen before it
paints the desktop, so "the picture stopped changing" was satisfied by an empty
screen. `await_render()` now requires at least one redraw after observation
starts, and the qualification run uses three of them before treating a frame as
the desktop. With that gate, the desktop digest is reproducible across runs.

## Synthetic qualification

`tests/portable/test_input_delivery.py` (19 tests, no emulator, no ROMs) runs an
authored peer over a real loopback socket, so the actual client transport, reply
validation and facility logic are exercised. The peer can drop a character,
substitute one, queue without echoing, keep the BIOS ring full, or never redraw.

| Test | Proves |
| --- | --- |
| full text in three bursts | one verification per burst, `observed` at the top level |
| last character dropped | only the proven-missing suffix is resent (`ABCDEFGHIJJ` received) |
| middle character dropped | `ambiguous` at `ABCDEFGHI`, no further input sent |
| every character swallowed | `unchanged`, level `delivered`, no replay |
| peer keeps dropping | the attempt bound stops the operation instead of looping |
| queued but not echoed | level stays `delivered`; a full ring never reads as acceptance |
| ring drained by stepping | depth 2 → 0, with extents and word accounting checked |
| menu open then restore | `observed` against a caller-supplied reference snapshot |
| blinking cursor in text mode | frame digests differ while the press reads `unchanged` |
| pointer motion | `mouse 5 -3 1` reached the wire and changed the frame |
| invalid arguments | no `key`, `mouse` or `tablet` command reaches the wire |

The suite also covers the `wait text` and `wait mem` primitives, the strict
repeated-anchor refusal, graphics-mode refusal of anchor verification, and the
JSON shape of a report.

## Native qualification

Disposable clone of the sealed RSX OEM install at
`C:/DeskMateLab/private-evidence/input-delivery-20261126/guest-01`; visible
window, port 8765, sole connection. The disk image was byte-identical
(`3085c689…07fc1`) to the sealed baseline before and after the sessions. Only the
local `86box.cfg` changed, because the launcher sets the two documented host
input preferences; the emulator rewrote it at exit.

| Stage | Emulated ms | Result |
| --- | --- | --- |
| Boot to prompt | 8,550 | Prompt read from the screen (`C:\>`), BIOS ring empty |
| `TYPE AUTOEXEC.BAT` | 8,828 | `observed` after three bursts; output matched |
| `VER` | 9,006 | `observed` in one burst; `MS-DOS Version 5.00` matched |
| F10 in DOS | 9,121 | `unchanged`, level `delivered`, basis `text` |
| `DIR` | 9,195 | `observed`; `Directory of` matched |
| `MOUSE` | 10,718 | `observed`; driver banner |
| DeskMate desktop | 18,884 | Digest `676d86f6…8c48`, three redraws seen |
| F10 Applications menu | 19,168 | `observed`, digest `88ad0f47…5710` |
| Escape | 19,412 | `observed` restore to `676d86f6…8c48` |
| Pointer +40 x | 19,612 | Frame changed; pointer redrawn |
| Left button | 19,772 | `unchanged` (desktop background) |

The F10-in-DOS row is the distinction the campaign existed to establish: the
socket acknowledged, the device was handed the event, the guest consumed it, and
no application state changed. Nothing in the lower-level instrumentation could
have told us which of "ignored" and "misrouted" had happened.

The Applications menu opened by F10 lists Spell Checker, Calculator, Phone List,
Corkboard, Month, Alarm, To Do List, Clipboard and Task Switch, which matches the
published accessory inventory, and Escape returned to a byte-identical desktop
frame.

## Limits

- Anchor verification needs a text mode; in graphics mode `type_text` refuses
  rather than pretending. Consumption of typed text inside DeskMate dialogs is
  therefore not claimed here.
- A frame digest proves "the picture differs", not which control responded. The
  pointer and menu rows above are evidence of redraw, not of hit-testing.
- The BIOS ring is a weak signal on this guest and would be a strong one on a
  guest whose application blocks on input; the facility treats it as
  corroboration only.
- `expect='restore'` needs a snapshot from the same basis, and a guest that
  animates continuously cannot be compared at all; `await_render` then reports a
  live guest and the caller must supply a content expectation instead.
- The report is journaled, not signed. Evidence stays in private storage because
  guest screens can contain private text.

## Reproduction

```powershell
$env:PYTHONPATH = 'src'
python -m unittest tests.portable.test_input_delivery -v
python tools/experimental/input_delivery_qualification.py `
  --machine C:/DeskMateLab/private-evidence/input-delivery-20261126/guest-01 `
  --port 8765 --out C:/DeskMateLab/private-evidence/input-delivery-20261126/run-03
```

The runner refuses to retry a stage whose result is unclear and stops the run
instead. Session transcripts, PNG captures and digests for the tables above are
in the private `run-01` to `run-03` directories; `run-01` and `run-02` are kept
because they contain the two instrument failures that motivated the snapshot
bases and the render gate.
