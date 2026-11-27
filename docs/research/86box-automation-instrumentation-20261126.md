# Instrumented 86Box automation: queue, sequence and Corkboard verification

This is the implementation checkpoint that follows
[the instrumentation proposal](86box-automation-instrumentation-proposal.md). It
reports a working instrumented executable, native measurements from it, and the
Corkboard text-entry result the instrumentation made it possible to explain.
Proposals are labelled as proposals, synthetic results as synthetic, and native
results as measured.

The shared production emulator was not modified, replaced or rebuilt. The
instrumented executable is a separate build of a separate checkout, addressed by
its own path and hash throughout.

## Provenance

| Item | Value |
| --- | --- |
| Upstream revision | `855258da966f1594f568350be59e8e1eca082ed1` (same as the pinned production source) |
| Separate checkout | `C:/DeskMateLab/sources/86Box-input-idq`, produced with `git archive` from that revision, no git metadata |
| Build directory | `C:/DeskMateLab/builds/86box-automation-idq` (production build left untouched at `builds/86box-automation`) |
| Configuration | Ninja, `CMAKE_BUILD_TYPE=Release`, `AUTOMATION=ON`, `QT=ON`, Qt 5.15.19 static prefix |
| Compiler | `cc.exe (Rev6, Built by MSYS2 project) 16.2.0` |
| Executable | `builds/86box-automation-idq/src/86Box.exe`, SHA-256 `3e56b6e9b89ac95a555b88ba875614359d63cf432d17a3dd33d2ab5520035fe1` (second revision; the first was `23feae30…5845`) |
| Patch | 164 added lines across `src/automation.c`, `src/device/keyboard.c`, `src/include/86box/keyboard.h`; SHA-256 `213d668cb1862973a5397966f5bd00f751a8a2ebc2024d3aff1624b7c494a133` |
| Build note | `cc1.exe` needs MSYS2's `ucrt64/bin` on `PATH`; without it the compiler exits 1 with no diagnostic |
| Patch copy for review | [`tools/experimental/86box-instrumentation.patch`](../../tools/experimental/86box-instrumentation.patch) |

The patch applies to the pinned revision only and is not installed into the
production tree.

## Three queues, kept apart

The review asked not to conflate the automation queue with keyboard-controller
state, BIOS buffering or application consumption. Reading the source settled
what each layer actually is:

* **Automation queue** (`key_queue`, `KEY_QUEUE_MAX 64`, `KEY_GAP_MS 2` in
  `src/automation.c`): events this interface accepted and still owes to the
  keyboard device. It is the only per-keystroke FIFO in the emulator.
* **Keyboard device state** (`recv_key[768]` in `src/device/keyboard.c`): a
  pressed/not-pressed table, not a queue. `keyboard_held_count()` reports how
  many scancodes are currently held, which catches a stuck key.
* **BIOS ring** (`0040:001A/001C`, extents `0040:0080/0082`): translated
  keystroke words written by `INT 09h` and read by `INT 16h`. It is read from the
  guest side and is emptied by guest consumption.

No counter here claims that an application consumed a keystroke. Only the BIOS
ring observation, and the application-level evidence on top of it, do that.

## What was added

* `status` gains `caps` and an `input` block:
  `queue`, `capacity`, `seq`, `accepted`, `forwarded`, `dropped`, `held_keys`,
  `gap_ms`. A stock build has neither field.
* `key` replies gain `events`, `seq` and `queue` (0 at completion). The reply is
  produced by the timed completion path, so completion now means: every accepted
  event was handed to the keyboard device and the automation queue is empty.
* `wait queue <timeout_ms>` is a bounded observation of that drain, reporting
  `matched` and the remaining occupancy.
* `video` reports BIOS mode, text flag, geometry, BIOS cursor and frame size in
  either mode.
* `mouse state` reports cumulative motion and the last button mask the interface
  sent.

A defect was found while counting: the `key` handler reset `key_head`/`key_count`
on every request, so a second `key` issued while events of the previous one were
still pending silently discarded the remainder. It still does that - replacing
input mid-delivery is the caller's decision - but the discarded events are now
counted in `dropped` and reported as `replaced` in the new request's reply, so a
fresh `key` after `wait queue` cannot lose them unnoticed.

## Second revision, after the independent draft review

The review asked for an explicit accounting identity, a queue wait that can
actually drain an interrupted command, and a distinction between an empty queue
and complete delivery. The second revision adds:

* `accepted = forwarded + dropped + pending` as a reported identity
  (`accounting: true`) and as a client-side check. Every report also carries
  `pending` and `generation`.
* Per-request receipts: `key` replies carry `events`, `seq`, `replaced` and, at
  completion, the cumulative `accepted`, `forwarded`, `dropped`, `pending` and
  `generation`. The client compares consecutive replies, so a request that
  accepted *n* events must account for *n* forwards or discards. A reply ended by
  the debugger (`stopped`) is an interrupted delivery, not a completion.
* `wait queue` now **pumps** orphaned events at the normal emulated gap instead
  of only observing them. A key command can be ended by the debugger stop path
  with events still pending, and nothing else would ever forward them.
* `key cancel` discards pending events and counts them as `dropped`, which is the
  explicit-cancellation alternative to replacing them.
* A reset during delivery now discards and counts pending events and bumps
  `generation`, so a reboot cannot inherit keystrokes from before it.

The build announces `input_accounting`, `queue_pump` and `key_cancel` as
capabilities, so a client negotiates them rather than inferring them from a
version.

## Native results

Guest: disposable copy of the sealed RSX baseline, disk SHA-256
`3085c689…07fc1` before the run, `d16e3813000affb6cfc0a50dc78ec9e91c1c89454cf94782aa12f9896a0fdb03`
after. Visible window, exclusive port 8765, private raw evidence under
`private-evidence/input-delivery-20261126/idq/run-02`.

| Observation | Result |
| --- | --- |
| Capabilities | all six announced, none missing |
| DOS `VER` through `DosPrompt` | entry observed, output matched in new rows, new prompt at the bottom, `wait queue` matched |
| Event accounting for `VER` | `seq` 0 → 14, `accepted` 14, `forwarded` 14, `dropped` 0, `queue` 0 |
| BIOS ring during typing | head advanced by exactly 2 per keystroke, wrapping 60 → 30 with `end` 62 |
| Ring end offset | pointers wrap at 62 while `end` is 62, so the end offset is exclusive |
| Corkboard keystrokes | 30 characters, every one advanced both ring pointers and changed the frame |
| Live buffer (differential) | absent before typing, then the full note at `0x4DC78` (`318584`), stable across repeated reads, line 2 at `+12` |
| Saved document | `DESKMATE/DMCORKBD`, 2,864 bytes, header `1f000000` then `FF INPUT 01\rALPHA BRAVO CHARLIE`, SHA-256 `97747bf7…0c41` |
| Cold reopen | note rendered again; whole-frame diff 12 of 307,200 pixels, all inside `[600,16]-[606,21]` |
| Accounting, second revision | `accounting: true` at boot and at the end of every run; `accepted == forwarded + dropped + pending` |
| 21-character burst | 76 accepted, 76 forwarded, 0 dropped, ring peak 15 of 15, one character lost |
| Persisted header | offset 0 is the insertion position (12-byte text, word 7; 11-byte text after Backspace, word 3), restored as a caret on cold load |

The 12-pixel difference sits in the top-right corner, outside the note text.
Everything the note occupies is pixel-identical after a cold boot.

### Why the earlier run lost characters

The earlier campaign typed whole lines as one request
(`client.type_ascii('FF INPUT 01')`) and lost the first character and the tail of
line 2. A controlled burst run on a fresh clone now names the layer.

One line of 21 characters is one automation request of 76 events (each character
is a make and a break). The interface forwarded all 76; the guest BIOS ring
reached **peak occupancy 15**, which is its capacity, and the saved note lost
exactly one character at the end of that line:

| Observation | Value |
| --- | --- |
| Events accepted for the 21-character line | 76 |
| Events forwarded | 76 |
| Events dropped by the interface | 0 |
| Automation queue at completion | 0, `accounting: true`, `matched: true` |
| BIOS ring peak during the burst | **15 of 15** |
| Persisted text | `FF INPUT 01` CR `ALPHA BRAVO CHARLI` (30 bytes, expected 31) |

The 11-character first line reached a peak of 9 and lost nothing. The interface,
the socket and the automation queue are therefore not where the character went:
`accepted == forwarded == 76` and the queue drained. The loss is at **`INT 09h`
buffer-full**: the interface forwards one event every 2 emulated milliseconds,
the application polls `INT 16h` more slowly, the 15-word ring fills, and the BIOS
discards what does not fit. An empty ring afterwards is equally consistent with
this: the application consumed what it was given.

This is why the dependable recipe is per-character requests with a short settled
step, and why the facility's `chunk=1` with a settle step is the qualified path.
It also explains why the packet counters cannot predict the loss on their own:
they describe the interface, not the ring or the application.

### Controlled header experiment

The same instrumented build was used for a separate native experiment that
separates Corkboard's persisted insertion position from its text length. It is
reported in
[Corkboard's persisted header](deskmate-corkboard-header-20261127.md), and it
resolves the first word of the document header.

### Buffer location, and what it does not prove

The differential search does not assume an address. It searches conventional
memory for the typed marker, records that it was absent before typing, present
afterwards, stable across two reads, and that the second line sits at the
expected offset. That is a candidate live buffer, confirmed for this session by
the saved document holding the same text at offset 4. It is not a claim that
`0x4DC78` is the authoritative buffer for every build, configuration or
document size; the same differential method is what should be repeated before any
address is trusted.

The saved file's first four bytes (`1f 00 00 00` = 31) equal the text length
with CR delimiters, matching the earlier format finding that the document body
starts at offset 4.

## Questions for the static-analysis campaign

These are offered to the Ghidra work; nothing here was changed in its worktree.

1. Does `DMNOTEPD.ACC` write `DMCORKBD` through one routine? The native run now
   shows offset 0 is the insertion position, not a length (see the header
   experiment); the second word has not been explained.
2. What bound applies to the note text (offset 4, CR-delimited) and what happens
   at the limit - truncation, refusal, or a second block?
3. Which path copies the live buffer at `0x4DC78` (session-dependent) to the
   file, and does the application keep a second copy such as an undo buffer?
4. Under burst delivery, where does the keystroke get discarded: the
   application's `INT 16h` polling loop, its redraw path, or a fixed-size
   keyboard lookahead of its own?

## Limits

Several guests of one machine configuration, one compiler. The counters are
interface-side by construction: they show what the interface forwarded, not what
the BIOS or the application consumed, and the burst result depends on the guest
BIOS ring rather than on them. The buffer address is session-specific. Cold
reopen was compared by frame content, not by a second independent extraction
after the reopen.

The `wait queue` pump and `key cancel` are implemented and covered by portable
tests, but this build has no GDB stub compiled in, so the debugger-stop path that
leaves events pending cannot be induced from the automation socket. Native
`key cancel` was exercised only with an empty queue (a no-op); the non-empty case
is covered by the synthetic peer. The pump is therefore reviewed and portable-
tested, not natively exercised. `generation` was observed at 2 after two guest
resets and did not change within a run.
