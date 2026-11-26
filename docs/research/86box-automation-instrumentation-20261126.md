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
| Executable | `builds/86box-automation-idq/src/86Box.exe`, SHA-256 `23feae30018f97c341adb41ff64969c9aa54e3204d8c3fa290bbaf23979f5845` |
| Patch | 99 added lines across `src/automation.c`, `src/device/keyboard.c`, `src/include/86box/keyboard.h`; SHA-256 `9f75ad0e1162352d3ec0ed511e3120c683b407a32fa21a83d53a02c12a38ba0b` |
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
counted in `dropped`, and a fresh `key` after `wait queue` cannot lose them
unnoticed.

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

The 12-pixel difference sits in the top-right corner, outside the note text.
Everything the note occupies is pixel-identical after a cold boot.

### Why the earlier run lost characters

The failed campaign typed whole lines as one request
(`client.type_ascii('FF INPUT 01')`) and lost the first character and the tail of
line 2. With instrumentation:

* Every accepted event was forwarded (`accepted == forwarded`, `dropped == 0`),
  so nothing was lost inside the automation interface.
* The BIOS ring advanced by 2 for every keystroke and drained, so the BIOS saw
  and consumed every one.
* The application's buffer holds the complete note when each character is its
  own request followed by a 30-40 ms step.

The loss therefore happened between the device and the application, under burst
delivery, not in the transport, the ring, or the application's buffer handling.
The dependable recipe is per-character requests with a short settled step, which
is exactly what the verified facility now does when `chunk` is 1 and a settle
step is used.

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

1. Does `DMNOTEPD.ACC` write `DMCORKBD` through one routine, and is the
   4-byte header at offset 0 a length or a flags/version pair plus length?
2. What bound applies to the note text (offset 4, CR-delimited) and what happens
   at the limit - truncation, refusal, or a second block?
3. Which path copies the live buffer at `0x4DC78` (session-dependent) to the
   file, and does the application keep a second copy such as an undo buffer?
4. Under burst delivery, where does the keystroke get discarded: the
   application's `INT 16h` polling loop, its redraw path, or a fixed-size
   keyboard lookahead of its own?

## Limits

One guest, one machine configuration, one compiler, two runs of the same
scenario. The counters are interface-side by construction. The buffer address is
session-specific. Cold reopen was compared by frame content, not by a second
independent extraction after the reopen.
