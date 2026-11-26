# Bounded, verified guest input for 86Box automation

2026-11-26, revised after independent review of PR #187. Provider-independent
improvement to the automation layer, qualified with portable tests and six
authorized native sessions on disposable clones.

The question was not "can we send keys". It was: after a key is sent, what can
the emulator, the guest BIOS, and the application each prove, and what should an
automation layer do when those proofs disagree?

## Review findings and their disposition

| Finding | Disposition | Basis |
| --- | --- | --- |
| An empty BIOS ring does not establish that a keystroke was accepted | Confirmed | The ring holds *translated keystroke words*; a bare modifier never enters it, and a program that hooks `INT 09h` or polls the controller bypasses it entirely |
| Ring depth calculation appears reversed | Confirmed, corrected | `INT 09h` writes at TAIL, `INT 16h` reads at HEAD; occupancy is `(tail - head) mod size`. Native: head 36, tail 42, depth 3 |
| Do not retry while input may still be queued | Confirmed, implemented | The facility sends nothing while the ring is non-empty and reports `pending` |
| Chunk and attempt limits restrict ordinary input to 24 characters | Confirmed, corrected | Bursts and recoveries are separate budgets; a 40-character entry uses five bursts and no recovery |
| A matching prefix does not prove the insertion point | Confirmed, implemented | The BIOS cursor must sit exactly at the end of the prefix, and stale characters after it refuse the observation |
| Trailing whitespace is stripped | Confirmed, corrected | Rows are read raw; the cursor decides how much of the row is typed input |
| A changed framebuffer does not prove the operation succeeded | Confirmed, implemented | Evidence is recorded per layer; a press without an expectation can never report success |

One proposal was not adopted as stated. The review suggested that the synthetic
peer "appears to reproduce the same assumption" about the ring. It did: the peer
advanced HEAD on insert, so it agreed with the bug instead of exposing it. The
peer now models the documented producer/consumer split, wraps at the extents,
and refuses overflow the way the BIOS does, which is why the reversed arithmetic
is now caught by the tests rather than confirmed by them.

## Four evidence layers

| Layer | Evidence | Proves | Does not prove |
| --- | --- | --- | --- |
| Acknowledged | socket reply | the emulator received the request | anything about the guest |
| Delivered | `key` reply after the last event's `KEY_GAP_MS` gap | the emulated keyboard device was handed every event | BIOS translation, queueing or application action |
| Accepted | BIOS ring head/tail, read through `memr` | translated keystrokes were consumed as of that sample | which program consumed them, or that any did |
| Observed | caller-supplied expectation met | the intended state is now visible | which code path produced it |

These are separate attributes on every report
(`acknowledged`, `delivered`, `accepted`, `observed`), not a single level. A
press has `accepted: null` because scan codes may never become keystroke words; a
text entry on an unreadable ring has `accepted: null` and cannot recover.

The delivery claim remains source-verified: `src/automation.c` treats `key` as a
timed command, forwards the first event, emits the rest two emulated milliseconds
apart, and replies from `end_timed` after the last gap. `KEY_QUEUE_MAX` (64) is
internal and not exposed, so no command reports how many events the device still
holds; that gap motivates the instrumentation proposal.

## Cursor-authoritative verification

Text-mode verification no longer infers the typed region from screen cells. The
protocol's `text` reply already carries the BIOS cursor, so the facility reads it
and treats everything between the anchor and the cursor as typed input:

- a typed space is a character like any other, so `VER   ` is verified as six
  characters and its cursor lands at column 10;
- unused cells after the cursor must be blank, so a longer previous line that
  leaves stale characters there refuses the observation instead of reading them
  as input;
- the insertion point is checked before any suffix is resent, and a cursor that
  lags behind the echoed text blocks recovery rather than duplicating it.

A guest that trims trailing spaces cannot be verified this way, and is reported
`ambiguous` after the recovery budget is spent rather than being retried blindly.

## Recovery and its bounds

Recovery happens only when the observation is a strict prefix that stopped
growing, the ring is provably empty, and the cursor sits at the end of that
prefix. Bursts that keep making progress are normal operation and do not consume
the recovery budget; a burst that produces nothing new does. If the ring is
non-empty the facility sends nothing and reports `pending`, because queued input
can still arrive and a quiet screen proves nothing yet.

## Profiles

`profiles.py` keeps application knowledge out of the generic layer.

- `DosPrompt.submit` separates entry from execution: it types the command,
  refuses to press Enter unless the line and cursor are verified, then reports
  `prompt_returned` and `output_matched` independently. It never replays a
  command whose execution is unknown.
- `ScreenStates` recognises named graphics states by frame digest captured in the
  same session, and reports a transition as ambiguous when the screen lands on
  neither the expected nor the starting state. Digests are guest-specific, so
  they live in experiment recipes, not in the module.

## Synthetic verification

`tests/portable/test_input_delivery.py` (41 tests) and
`tests/portable/test_draw_disk_names.py` (3 tests) run without an emulator. The
peer speaks the real authenticated protocol over loopback and models a 25x80
screen, a BIOS cursor, and the ring.

| Case | Result |
| --- | --- |
| 40 characters in five bursts | observed, zero recoveries |
| last character dropped | suffix resumed; one resend |
| first or middle character dropped | ambiguous, no resend |
| substituted or duplicated character | ambiguous, no resend |
| every character swallowed | unchanged at level delivered |
| queued input before or after a burst | pending, nothing sent |
| delayed echo inside the budget | observed, no duplicate |
| echo slower than the budget | unchanged, no resend |
| trailing and repeated spaces | verified through the cursor |
| guest trims trailing spaces | ambiguous after the budget |
| cursor lagging or leading | unchanged or ambiguous, no resend |
| stale characters after the cursor | refused |
| ring wrapped, malformed, full | depth 3, invalid, 15 with overflow refused |
| menu open/restore, blink, render gate | observed, unchanged, false |

## Native qualification

Disposable clones of the sealed RSX OEM install, visible window, port 8765,
sole connection. Runs 04-06 are the corrected-facility sessions; the earlier
runs 01-03 are retained because they exposed the cursor-blink and pre-paint
failures.

| Stage | Emulated ms | Result |
| --- | --- | --- |
| Boot to prompt | 8,550 | prompt read from screen, ring empty, cursor [21,4] |
| `VER` entry and execution | 8,829 | entered, submitted, output matched, prompt returned |
| `VER   ` with trailing spaces | 9,119 | observed, cursor at column 10 |
| pacing: unverified | +128 | matched |
| pacing: fixed 25 ms per key | +203 | matched |
| pacing: bounded bursts | +278 | observed, one burst |
| pacing: verified submit | +278 | entry, prompt and output all verified |
| type-ahead during `TYPE COMMAND.COM` | 10,652 | ring head 36, tail 42, depth 3 — producer leads |
| type-ahead consumed | 11,652 | arrived once, ring empty, no duplicate |
| DeskMate desktop | 23,696 | digest `ca6a32f1…18c4`, three redraws |
| F10 Applications menu | 24,060 | observed, digest `f307d0bb…6863` |
| Escape | 24,304 | observed restore to the desktop digest |
| Corkboard note typed | 29,792 | captured, no text-level verification possible |
| Reopen | 76,984 | blank editor; 236 differing pixels from the typed frame |

The type-ahead row is the decisive correction: the ring held three translated
keystrokes while the guest was busy writing, TAIL led HEAD by six bytes, and the
queued `XYZ` appeared exactly once at the next prompt. With the previous
arithmetic the same state would have read as empty.

The pacing rows show what each approach costs and what it buys. Unpaced input was
fastest and happened to work for a three-character command on an idle guest; the
verified path cost 150 ms more and produced entry, output and prompt evidence.

## The Corkboard result, and why it matters

Two synthetic lines were typed into Corkboard, captured, and closed. Reopening
the accessory showed a blank editor, and the native file differed from the stock
all-zero document only by:

```
b'\x00F INPUT 01\rALPHA BRA'
```

The first character was lost and the second line was truncated, yet every
framebuffer observation along the way looked like success. Nothing in graphics
mode could have detected either loss: the editor has no text-mode row to read, no
cursor to compare, and the pixel change was real. This is the concrete cost of
unverified graphical text entry, and it is the argument for the field-level
instrumentation in the proposal rather than for more retries.

The staged note is not published as a fixture: it is the output of an
unverified, partially failed interaction, not a candidate fixture.

## Pointer

Motion was delivered and redrawn. A 200-pixel move produced four separate changed
regions, so frame differencing cannot localise the pointer reliably in this
application, and no click was claimed as hit-testing. `pointer` therefore records
`delivered` and a frame change, never a control activation. Aiming at a control
needs a position source; the proposal asks for one.

## Limits

- Anchor verification is text-mode only. Graphics text entry is unverified, as
  the Corkboard result shows.
- A frame digest proves the picture changed, not which control responded.
- The BIOS ring is a corroborating signal: it was empty at almost every sample on
  this guest and cannot be attributed to a specific keystroke.
- Frame digests are valid only within one session and configuration; the desktop
  digest differed between run-05 and run-06 because the clock and the previous
  application state differed.
- A guest that animates continuously defeats frame comparison; `await_render`
  reports that condition instead of hiding it.

## Reproduction

```powershell
$env:PYTHONPATH = 'src'
python -m unittest tests.portable.test_input_delivery tests.portable.test_draw_disk_names -v
python tools/experimental/input_delivery_qualification.py `
  --machine C:/DeskMateLab/private-evidence/input-delivery-20261126/guest-03 `
  --port 8765 --out C:/DeskMateLab/private-evidence/input-delivery-20261126/run-06
```

Captures, transcripts and digests are in the private `run-01` to `run-06`
directories.
