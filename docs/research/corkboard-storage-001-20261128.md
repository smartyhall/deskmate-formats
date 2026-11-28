# Corkboard note storage: header words, capacity, and character set (2026-11-28)

This campaign continued the [November 23 Corkboard work](deskmate-corkboard-20261123.md)
with new native experiments on the Tandy 1000 RSX OEM DeskMate **03.04.04**
installation. It separates the first header word from text length, constrains
what the second one is not, measures how much of the physical text area the
editor actually lets a user fill, and shows that the text area holds CP437 bytes
rather than ASCII.

Everything below is either a **native observation** in this campaign's own
emulator sessions or an explicitly labelled inference. Private raw captures,
socket journals, stopped disk images and guest memory dumps stay in the lab; the
repository receives the eligible synthetic fixtures, three documentary
screenshots, and a sanitized receipt.

Campaign metadata: owner **Freebuff** (native desktop agent), campaign
`corkboard-storage-001`, branch `freebuff/corkboard-storage-001`, base commit
`a49e72b3b967e6ed0b6097cb040114072a4970e7` (tag `research-origin-001`),
emulator 86Box **7.0** automation build with executable SHA-256
`e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d`.
Model identity and reasoning effort are not exposed to the agent and are
recorded as unknown.

## The control

Every session started from a byte-verified copy of the sealed RSX installation:
54,525,952-byte FAT16 disk `3085c689…6a107fc1`, configuration
`ccdfb129…d55b8b9`, NVRAM `e3ad097b…f84368ac`. The sealed directory was read
and hashed, never written. Four campaign-owned clones (`rsx-a` to `rsx-d`) were
used, one emulator instance at a time on loopback port 8765, each closed through
the socket before the next was prepared.

The stock `DESKMATE\DMCORKBD` on that installation is 2,864 zero bytes
(`35ea3bc0…bd3bb30`), so every non-zero byte in a specimen was written by the
program or by the declared input path.

## Method: three observation channels

The earlier campaigns read the note file only after stopping the emulator, which
makes every cursor experiment cost a full boot-and-extract cycle. Two cheaper
channels made this campaign possible, and both matter for judging the evidence.

**The live text array.** The accessory's working text lives in guest RAM. In this
profile it is at `0x4A0E8` (conventional memory), 2,860 bytes of CP437, with no
copy of the two header words adjacent to it. Reading it back turns graphical text
entry into a verified operation: after every burst the driver compares the array
with the intended bytes, and a short array is distinguishable from a refused
keystroke. This is a **runtime observation** for one edition and configuration,
not a static fact about the module; the earlier static study deliberately claimed
no guest address and this campaign's address is not a format property.

**DEBUG inside the guest.** Saved files were read in text mode with the guest's
own `DEBUG`: `D 100 L n` shows the header words and the first text bytes on the
CP437 text screen, which the automation client reads exactly. Because the row is
machine-readable, a mis-delivered keystroke appears as a malformed line rather
than as a plausible wrong number. The final check for each specimen was still a
stopped-image extraction by 7-Zip 26.05 and by the repository's independent FAT16
walker, which agreed on every file.

Two traps were found and are recorded because they cost trials: `DEBUG`'s `E`
command resets the write count, so a following `W` writes nothing until `R CX`
sets it; and the prompt after `AUTOEXEC.BAT` is `C:\`, not `C:\DESKMATE`, so an
`E`/`W` sequence run there edits a different file.

## Experiment 1: what the first word is

The earlier evidence left two readings alive, "insertion point" and "text length",
because most observations had the caret at the end of the text, where both
predictions coincide. The discriminating state is a caret strictly inside a note.

| Trial | Operation | Text bytes | Word at `0x0000` |
| --- | --- | ---: | ---: |
| T1 | Typed three lines, caret at end, closed with Escape | 61 | `0x003D` = 61 |
| T2 | Reopened a 61-byte note, pressed Home, closed | 61 | `0x003D` = 61 (unchanged) |
| T3 | Reopened, Home, typed one `X` at text index 51, closed | 62 | `0x0034` = 52 |
| T4 | Reopened, typed `AB` at 52 and 53, moved left three times, closed | 64 | `0x0033` = 51 |
| T5 | Reopened, Shift+Left seven times, closed | 64 | `0x0039` = 57 |
| T6 | Reopened a full note, Home, closed | 2,666 | `0x0A40` = 2,624 |
| T7 | Saved a 2,794-byte note with the caret at 42, cold-reopened | 2,794 | `0x002A` = 42 |

T3 is the decisive one: inserting one character left of the old end moved the word
from 61 to 52 while the text grew to 62. A length field cannot do that. T4 then
separated "value captured at the edit" from "value captured at close": the caret
ended at 51 and the stored word is 51, not the 54 it held when the text changed.
The word is the **caret's byte offset at the moment the note was written**, zero
based, counted in the text area that begins at file offset `0x0004`.

Byte offset and character position coincide here because the encoding is
single-byte. The measured constant is a **different kind of quantity** from text
length, visual column, row, and viewport position; it is none of those.

### Reconciling the T4, T5 and T6 sequences

The published T4, T5 and T6 entries describe several different sessions, and only
one of them left bytes that survive in the lab. The retained chain is:

| Trial | Retained evidence | Recorded sequence |
| --- | --- | --- |
| T4 | socket journal `state-edit-then-move`, captures `c01-ab-typed`, `c02-left3`; **no file copy** | Desktop started from the DOS prompt; F10 Corkboard; live-array read of the 62-byte text; `A` then `B` typed, landing at 52 and 53 as the second live-array read confirms; three Left presses; Escape; exit to DOS; guest `DEBUG` read of the saved file |
| T5 | socket journals `probe-select` and `sel-save`, captures `d01`–`d03`, `e01`, `e02`; **final file only** | Two reopen-and-select attempts, each started again from the DOS prompt later in the same boot. `probe-select`: reopen, live-array read, five Shift+Left, one Down, Escape. `sel-save`: reopen, live-array read, seven Shift+Left, Escape. Both journals contain modifier and arrow keys only — no character, CR, Delete or paste key |
| T6 | captures `b01-reopen`, `b02-home`; **final file only** | Reopen of the 2,666-byte note, Home, close |

The final rsx-a extract is `8cd0a2b8…` with 64 text bytes and words `(57, 0)`; the
final rsx-b extract is `b48eabde…` with 2,666 text bytes and words `(2624, 0)`.
Both clones overwrote their intermediate files, so no hash, image copy or
extraction exists for the file T4 left behind, nor for the rsx-b note before
Home. The values 51 and 2,666-before-Home come from the guest `DEBUG` screen read
during those sessions, which the driver consumed but did not store as a separate
artifact.

That gap matters. T5 sent no key that can change text, yet the file it left has a
word (57) that differs from the value T4 recorded (51). Either the close wrote the
file because the selection marked the buffer dirty, or the reopened note was
already treated as modified for a reason this campaign did not isolate — for
example a reopen, in the same boot, of a note an earlier session had edited. T6
has the same shape: Home moved the caret 42 bytes back from the end of a wrapped
row, and the saved word is that new position. Nothing retained distinguishes a
selection-triggered write from a dirty-on-reopen state, and this report does not
choose between them.

What the controls do support is narrower:

* **T2** reopened a 61-byte note, pressed Home and closed; the file was reported
  byte-identical with the word still 61. The before-image was not retained, so
  this rests on the comparison made at the time.
* **T7b** cold-reopened the maximum note, pressed Home and closed; whole-file
  hashes before and after the stop are equal (`8ebaa224…`), which is the
  strongest retained control.

A plain cursor-only close on a freshly opened note therefore left the file
unchanged in the two cases observed. The broader statements that cursor movement
never writes, and that a selection is inert, are **not established**: T5 is the
case that contradicts the stronger reading, and it cannot be adjudicated from
the retained evidence. The reader and the reference describe the stored word as
a write-time value and do not depend on a dirty-buffer rule.

One measured value lands on a line delimiter, and it must not be over-read. The
maximum specimen stores 42, and byte 42 of its text is the CR that ends the first
42-byte row; the following logical row begins at 43. The cold-reopen capture shows
the caret at the start of the row below, which is consistent with a caret left at
the end of the first row, but the trial did not isolate how the accessory draws
or restores a caret that sits on a CR. Read the stored 42 as the text-area byte
the caret was on at the write, and leave the row-boundary convention open: it is
not evidence for a conventional insertion offset (the position before which the
next character goes), and it must not be normalized to 43.

## Experiment 2: what the second word is not

The word at `0x0002` was zero in every file this project has measured, and it
stayed zero in every new state tried here: a blank note, notes of 2, 3, and 14
lines, a caret inside the text, an active seven-character selection, a 65-row
document scrolled to its end, a 2,794-byte document scrolled back to its first
row, a refused keystroke at the capacity boundary, and a CP437 note.

The experiment that matters is the scrolled one. After the 65-row note was filled,
six Page Up presses moved the viewport to the top while the caret stayed put; the
saved word at `0x0002` was still `0x0000`. That **excludes** the two most natural
guesses, a first-visible-row or a scroll offset, for the states exercised. It also
excludes a selection anchor, since a selection was active and the second word
stayed zero, and a line count, since documents of 2, 14, and 65 rows all stored
zero.

Reading the state back from the live array rather than the file narrows it
further: the 2,860-byte text array at `0x4A0E8` has no adjacent copy of either
word to read, so the second word is not maintained as part of a mirrored record
image next to the text. What remains is a reserved field, a flag that no tested
operation sets, or a value written only by an operation this campaign did not
reach. **Its meaning is unestablished** and the reader must not attribute one.

## Experiment 3: real editable capacity

The physical text area is 2,860 bytes. The editor does not let a user use all of
it, and the limit is not a simple byte count.

Two units have to be kept apart. A **logical line** is the run of bytes between CR
delimiters in the text area; its length is a property of the stored bytes. A
**visual row** is what the accessory draws: a logical line wider than the window
is wrapped across more than one drawn row, and the editor's row budget applies to
those drawn rows. The capacity trials composed short CR-delimited lines, so each
logical line was also one visual row; the 81-character trial is the one that
separates the two.

The first boundary appeared while filling a note with 40-character lines: at
2,666 text bytes the caret sat at the start of the 65th row, and the CR that would
have begun a 66th row was refused while following characters were appended to the
last row. A second composition with 20-character lines produced the same refusal
at the same structural point, 1,364 bytes and 65 rows, so the trigger is the row
count, not the byte count.

Isolating the two limits directly:

| Trial | Content | Result |
| --- | --- | --- |
| L1 | one logical line of single characters | 81 characters accepted; the trial stopped there rather than at a refusal, and the line was drawn across at least two visual rows, so 42 is a wrap width rather than a cap on a logical line |
| L2 | `A` + CR, repeatedly | the CR that would make a 66th row is refused once 65 rows exist |
| L3 | 65 lines, append to the last row | the last row grows to 42 characters, one full visual row, and then refuses further input |

So a drawn row holds **42 characters** and the note accepted **65 drawn rows** in
these compositions. The product is not the capacity, because rows can be shorter;
the largest composition demonstrated is 65 full rows: 65 × 42 = 2,730 characters
plus 64 delimiters = **2,794 bytes**. That is a demonstrated maximum, not a proven
universal one: it depends on every visual row being full and on each line ending in
a CR, and no trial drove a composition of wrapped logical lines to its refusal
boundary, so another arrangement of the same row budget was not measured. The 66
unused bytes are what this composition leaves; they are not proof that no
composition can reach them.

That number was then written in a single native note. A blank note was filled with
sixty-five 42-character rows in verified bursts, stopping exactly at 2,794. At that
length, with the caret at the end:

* Enter produced no new row and no new byte;
* a printable character produced no byte;
* a mid-row insertion at row 64 produced no byte.

The editor was not wedged: Home still moved the caret, and the close wrote
`0x0A40`-style values from it. The note saved, cold-reopened, and restored all
2,794 bytes exactly.

| Quantity | Measurement |
| --- | --- |
| Physical text area | 2,860 bytes (`0x0B2C`) |
| Measured maximum stored text | 2,794 bytes (65 rows of 42 + 64 CRs) |
| Unusable remainder | 66 bytes, never observed to hold text |
| Visual rows accepted | 65 (every trial composed CR-delimited lines) |
| Characters per drawn row | 42 |
| Behaviour at the limit | silent refusal of Enter, characters, and mid-row insertion; no dialog, no message |

Calling 2,860 the capacity would have overstated what a user can enter by 66
bytes, and calling it a byte limit would have been wrong about the mechanism: a
note of 65 short rows refuses earlier than a note of 65 full rows.

## Experiment 4: character set

The existing reader accepted only printable ASCII and CR. That was a limitation of
the profile, not a property of the format.

A disposable clone's note was seeded with a controlled CP437 sample through the
guest's `DEBUG` (`82 9B B0 B1 B2 C4 C9 CD DB E1 F1`, CR, `END`), and opened in
F10 Corkboard. The editor drew the corresponding CP437 glyphs: `é ¢ ░ ▒ ▓ ─ ╔ ═ █
ß ±`, then `END`. It then accepted numeric keypad entry, Alt+130 and Alt+225, and
stored `0x82` and `0xE1` at the end of the note, and the close wrote a file
containing both the loaded high bytes and the new ones (`63ec0dcf…024e700`).

| Layer | Observation |
| --- | --- |
| Intended input | Alt+130, Alt+225 on the numeric keypad |
| Stored byte | `0x82`, `0xE1` |
| Rendered glyph | `é`, `ß` in the note editor |
| Cold-reopened result | both bytes present, same glyphs |

The mapping was corroborated at two nonadjacent code points, not assumed from the
keyboard layout. The eleven seeded bytes prove display and preservation at those
code points rather than typed entry, and the campaign did not attempt 0x01–0x1F,
0x7F, or a full 256-code sweep. What is measured is therefore CP437 at two typed
code points and at eleven displayed ones; the rest of the high half is not
measured. The reader's acceptance of `0x20`–`0xFF` except `0x7F` is a
deliberately broader **policy** chosen from that display-and-preservation
evidence, not a measured range; it keeps rejecting other control bytes, decodes
as CP437, and preserves raw bytes.

## Clear, residual bytes, and one correction

This campaign did not repeat the Clear trial and adds no new Clear observation. It
did find an error in the earlier static note, which stated that Clear "zeroed
`0x0000`". The published cleared specimen
(`corkboard/rsx-cleared/DMCORKBD`, `29a77821…3348517a`) holds header words
`(20, 0)` and differs from its parent at exactly one byte, `0x0004`. Clear zeroed
the first text byte and left both header words as they were. The static note is
corrected accordingly; the reference page already described the operation
correctly.

The preservation consequence is unchanged and reinforced: the file keeps the prior
synthetic text after the first NUL, and the first word keeps the caret from the
last modified state. Neither is a secure erase, and this campaign did not build
one.

## Cross-edition interoperability: not measured here

The November 23 campaign established that matched synthetic notes were
byte-identical across Personal DeskMate 2 01.00.00, the SL/2 ROM Desktop with
03.03.01 program disks, generic 03.05.00, and the RSX. **This campaign did not
transfer a file between editions**, and nothing here should be read as a
migration test. What it adds is orthogonal: the first header word carries caret
state, the second word's meaning is unestablished, and the text is CP437, so a
transfer test would be checking the receiving edition's re-save behaviour rather
than a different layout.

The specific test to run next is one file, one direction: copy the published
2,794-byte specimen onto disposable media, open it under generic 03.05.00 and
under Personal DeskMate 2, and record the displayed text, the caret on open, the
re-save bytes, and whether the receiving edition preserves 2,794 bytes or
truncates it at its own row and byte limits.

## Failed trials and limitations

Recorded because they bound the claims:

* **Input loss in the graphics editor.** A 200-character burst produced a stray
  `0x0A`, a lost CR, and a `5`→`Q` substitution in one run. The live-array check
  caught it and the trial was discarded rather than published. Twenty-character
  bursts at 70–90 ms pacing with a settle were reliable for about 2,800
  keystrokes; this is a measurement technique, not a promoted automation facility.
* **One unreproduced capacity observation.** Before the row model was understood,
  a 2,666-byte note refused both Enter and a mid-row insertion. That state is
  consistent with "65 rows full at 40 characters plus two more on the last row",
  but the refusal of the mid-row insertion there was not re-derived after the row
  model was known, so the general claim "insertion is refused anywhere once the
  note is full" rests on that single trial plus the 2,794-byte confirmation.
* **The row limit is a boundary, not a specification.** 42 characters and 65 rows
  are what this 640 × 480 accessory in this edition accepted. Another video mode,
  window size, or edition could differ; nothing here establishes the constants
  for any other release.
* **No exhaustive code point coverage.** Two nonadjacent CP437 high bytes were
  entered natively. The rest of the high half is accepted by the reader on the
  strength of display and preservation, not of typed entry.
* **No scroll-position experiment for the second word beyond Page Up.** The
  viewport was moved with Page Up at a fixed caret. Mouse-wheel or scrollbar
  driven viewport changes were not exercised.

## Reproduction

The exact procedure needs the private sealed installation and the emulator build.
With those inputs, per trial:

```text
launch a campaign-owned clone of the sealed RSX install, held at 0 ms, port 8765
advance 20000 ms to C:\ ; CD \DESKMATE ; DESK ; F10 ; Down x5 ; Enter
type the intended text in verified bursts, reading 0x4A0E8 after each burst
close with Escape, then Escape and Enter to leave DeskMate
read the file with the guest's DEBUG (D 100 L 18), or stop and extract it
```

`tools/experimental/draw_disk.py` and 7-Zip 26.05 read the stopped image
independently and agreed on every published specimen.

## Local verification environment

The campaign's local checks ran on the shared system interpreter CPython
**3.13.17** (`<user>\AppData\Local\Programs\Python\Python313\python.exe`).
In that environment `import deskmate_formats` resolves to
`…\Lib\site-packages\deskmate_formats`. That copy is an older build of the
project: 42 files present under `src/deskmate_formats` are absent from it
(including `campaign_env/` and `automation/input.py`), and 11 modules differ,
among them most of `supervisor/` and `corkboard.py`. The campaign's own driver
scripts imported the worktree by inserting `src` on `sys.path` (`probe.py`), so
the native work used the worktree code even though the interpreter's installed
package did not.

The failing check was
`test_supervisor_driver.DriverTests.test_owner_termination_leaves_permanent_fence_and_read_only_restart`.
It starts its synthetic owner as `sys.executable -I -m
deskmate_formats.supervisor.driver_cli`; `-I` ignores `PYTHONPATH` and the
working directory, so with the system interpreter the child loaded the stale
site-packages copy while the parent loaded `src` (itself reachable only through
`PYTHONPATH=src`). Run that way the test failed at `owner never durably observed
acknowledgement` after 15.8 s: the child could not follow the parent's protocol.

Built from this branch and installed into a campaign-owned virtual environment in
the system temp directory (`--system-site-packages` only to supply `jsonschema`),
the same focused test passed in 2.3 s. That establishes the cause and verifies an
own environment; it is **not** a claim that the whole local suite passes, which
was not rerun. Hosted CI builds a wheel, installs it, and then runs the tests, so
its import identity matches by construction. The shared installation was not
modified.

## What this changes in the reader

`deskmate_formats.corkboard` now accepts a CP437 text range deliberately wider
than the two code points entered natively, exposes the visible text decoded as
CP437, and keeps the raw bytes, the raw header words, and the conservative
rejection of unmeasured control bytes. It still requires the
caller to identify the file: the buffer has no signature, and a 2,864-byte
all-zero file is equally plausible as a stock note or as unrelated data.

## Visual exemplars

Three native captures accompany this report. They are ordinary documentary
screenshots of synthetic campaign content under the operator's 2026-11-21
authorization, and they contain no private or third-party material beyond the
DeskMate interface itself.

* The maximum-length note, 65 rows of 42 characters, after the boundary was
  confirmed.
* The CP437 note after native Alt+130 and Alt+225 entry, showing `ENDéß`.
* The maximum-length note reopened on a cold boot, with the restored caret.

## Follow-up

1. Run the one-file cross-edition transfer described above.
2. Sweep CP437 code points natively, including the 0x01–0x1F and 0x7F range, to
   widen or confirm the reader's accepted set.
3. Test whether the second word is written by any operation at all, using
   selection, printing, and the Information Center dashboard as candidate
   writers.
4. Repeat the row and character limits on another edition and video mode before
   any of the three constants is treated as a format property.
