# Corkboard's persisted header: the first word is the insertion position

2026-11-27. Controlled native experiment on a disposable clone of the sealed RSX
baseline, using the experimental instrumented 86Box build. It answers the first question in
the Ghidra campaign's handoff (`deskmate-corkboard-handoff-20261126.json`, in the
static-analysis PR) and leaves the second one open, with the evidence for both.

Nothing here starts from an address. The live buffer is not needed to read the
persisted document, and the runtime copy is a separate question.

## Why the earlier evidence could not settle it

Every note observed before this run was saved with the cursor at the end of the
text, so a header word equal to the text length and one equal to the insertion
position produced the same number. The static analysis called the insertion
reading "strong" from one mid-text edit, but that edit also kept the text length
at 41 while the word became 20; a single case distinguishes "length" from "not
length" without showing what the word tracks.

## What was done

Each row is one cold boot on the same guest image:

1. boot DOS, run `MOUSE`, then `DESK`, and wait for the desktop to render;
2. open Corkboard through the documented F10 applications menu;
3. apply the cursor moves and text in the row;
4. press Escape, which is the close-and-save path, and quit the emulator;
5. extract `DESKMATE/DMCORKBD` from the stopped image with the repository FAT16
   reader and record the header words, the text and every hash.

The steps are cumulative: each one begins from the document the previous step
saved. All text was typed one character per automation request.

| Step | Before saving | word0 | word1 | Persisted text (CR shown) | Text bytes |
| --- | --- | ---: | ---: | --- | ---: |
| s0 | empty note, no edit | 0 | 0 | *(empty)* | 0 |
| s1 | typed `ABCDEFGHIJ` | 10 | 0 | `ABCDEFGHIJ` | 10 |
| s2 | Home, no edit | 10 | 0 | `ABCDEFGHIJ` | 10 |
| s6 | Home, Right×5, typed `XY` | **7** | 0 | `ABCDEXYFGHIJ` | 12 |
| s7 | Home, Right×4, Backspace | **3** | 0 | `ABCEXYFGHIJ` | 11 |
| s8 | End, Enter, `ZZ` | 14 | 0 | `ABCEXYFGHIJ` CR `ZZ` | 14 |
| s10 | reopen, type `Q` without moving | **15** | 0 | `ABCEXYFGHIJ` CR `ZZQ` | 15 |
| s11 | End, 22×Enter, `ZZ` | 39 | 0 | 25 lines | 39 |

The decisive rows are s6, s7 and s10:

* s6 inserts two characters at text index 5. The text is 12 bytes long and the
  word is 7, the character offset just past the insertion.
* s7 deletes the character before offset 4. The text is 11 bytes and the word is
  3, the new caret offset.
* s10 types nothing but `Q` after a cold reopen, and `Q` lands at the end of the
  stored text: the caret was restored to the persisted offset 14. The word is a
  position the application reads back, not a save-time echo of the text length.

## What the first word is

`word0` is a zero-based **character offset into the text area**, counted in bytes
with each CR as one byte. It is written when the note is saved and is used to
place the caret when the note is loaded.

It is not the text length: s6 stores 12 bytes with a word of 7, and s7 stores 11
with a word of 3. It is not a line number: s8 is on line 2 with a word of 14. It
is not a byte count into the 2,864-byte record: the record size never changes.

## What the first word is not

An unmodified note is not rewritten. In s2, Home moved the visible caret (76
changed pixels in the text row) and Escape closed the accessory, but the document
and the whole disk image were byte-identical to s1's. So closing an unchanged
note neither saves the new caret position nor touches the file. That is why the
test needed an insertion to force a write: a pure cursor move cannot be observed
in the persisted document, and a design that assumed "save always writes" would
have recorded a false negative.

## The second word

`word1` is `0` in every observed state: the stock file, the empty note, a
one-line note, a two-line note, a 25-line note longer than the visible area, and
notes saved after mid-text insertion and deletion. The scroll-offset hypothesis
in the handoff is therefore **not supported** by any observation here. It cannot
be excluded either: the editor may not persist a scroll position at all, so a
zero would look the same.

Remaining candidates are reserved space, a version or flags word, or a field
written only by a path this experiment did not take (capacity, an error state, a
different accessory editing the same store). It should stay unresolved until an
experiment discriminates them.

## Capacity was not tested

The text area is 2,860 bytes by record arithmetic, but this run did not approach
it. Typing to the boundary needs a delivery method that does not overflow the
guest BIOS ring (see the instrumentation report), and the experiment is better
run with a bulk path than with thousands of key events. Capacity, truncation and
refusal behaviour remain untested.

## Runtime buffer

This experiment says nothing about the live buffer. It is consistent with a
working copy shaped like the record (a 4-byte header then flat text), because the
persisted record is exactly what the editor reloads, but no runtime address is
claimed or needed here. The differential search used in the earlier campaign
remains the method for that question.

## Provenance and limits

| Item | Value |
| --- | --- |
| Guest | disposable clone of the sealed RSX baseline, disk `3085c689…07fc1` before the run |
| Instrumented executable | SHA-256 `3e56b6e9b89ac95a555b88ba875614359d63cf432d17a3dd33d2ab5520035fe1` |
| Driver | [`corkboard_header_probe.py`](../../tools/experimental/corkboard_header_probe.py), one emulator launch per step |
| Raw captures and images | private lab, `private-evidence/input-delivery-20261126/corkboard-header-01` |
| Guest after the run | disk `0dfbf2fcda8712fef161571115db21ee01df04794d30ee77afb675a29a5a68de` |

One guest, one configuration, one DeskMate release. The rows are cumulative, so
each header reading depends on the text the previous row saved; the text column is
the independently extracted content, not an assumption. Screenshots are private
because they are raw captures of a commercial interface, but the persisted
document bytes and the header words are reported here.

## Cross-campaign note

This is consistent with the static finding in the Ghidra campaign's report
(`deskmate-corkboard-static-20261126.md`) that `0x0000` is the insertion
position, and it adds the two results static analysis could not give: the field
survives a cold load as a caret position, and it is not written when a note
closes without an edit.
