# DeskMate Note Pad and Corkboard: measured file format reference

**Status:** maintained, evidence-bounded reference for observed native files. This is **not** a complete vendor specification or a universal DeskMate database profile. Sources: [November 23 native write and cold-reopen campaign](../research/deskmate-corkboard-20261123.md#corkboard-storage); [November 28 header, capacity and encoding campaign](../research/corkboard-storage-001-20261128.md); [November 28 cross-edition, boundary and control-byte campaign](../research/corkboard-interoperability-002-20261128.md); [published fixture manifest](../../tests/fixtures/application-generated/manifest.json).

## Identification and editions

The observed Note Pad/Corkboard file has **no identifying magic signature**. The caller must supply provenance or an expected filename and edition. The native two-line Personal DeskMate 2 **01.00.00** `DMNOTEPD` was byte-identical to the RSX OEM DeskMate **03.04.04** `DMCORKBD` for matched synthetic text. The Tandy 1000 SL/2 ROM Desktop using **03.03.01** program disks produced the same bytes. Generic **03.05.00** also created a file of this size with a longer note; its fourteen-line save was measured separately. These tests do not establish universal interoperability for other editions, non-ASCII input, or larger notes.

The accessory module is named `DMNOTEPD.ACC` across several surveyed editions, but its displayed name and file naming conventions differ. On the RSX, Information Center **3.61** uses the same `DMCORKBD` text as the F10 Corkboard accessory. Its separate `INFOCNTR.DB` message records are **not** part of this format. [Edition matrix](../research/deskmate-corkboard-20261123.md#release-survey)

## Cross-edition transfer, as observed

Two hard-disk editions were exercised in both directions with exact injected
bytes rather than retyped text: the RSX OEM **03.04.04** accessory and the
alternate generic **03.05.00** installation. The observed behaviour is not
treated as a shared rule; it is a matrix of what each receiver did.

| Receiver | Input | Reopen and close without edit | Edit and save |
| --- | --- | --- | --- |
| 03.04.04 | 03.05.00 fourteen-line note (377 bytes) | whole file byte-identical | appended two characters: 379 bytes, first word 379, only the header word and the two appended bytes changed |
| 03.05.00 | 03.04.04 two-line note (41 bytes) | whole file byte-identical | not exercised |
| 03.05.00 | 03.04.04 CP437 note (17 bytes) | CP437 glyphs drawn | appended two characters: 19 bytes, first word 19, every CP437 byte preserved |
| 03.05.00 | 03.04.04 cleared note, word 20, residual text | whole file byte-identical, word and residual kept | not exercised |
| 03.05.00 | 03.04.04 maximum note (2,794 bytes) | all 65 rows loaded, first 13 drawn | a typed character was refused silently; close left the file byte-identical |
| 03.05.00 | all-zero buffer | empty note, no create dialog | typed two characters: 2-byte text, first word 2, new file closed |

Byte-preserving interoperability is therefore demonstrated for these measured
shapes in both directions, and a foreign edit is written by the receiving
edition in its own right. It is **not** a claim about every edition or every
shape: 03.03.01 and Personal DeskMate 2 01.00.00 were not transferred in the
campaign that produced this matrix. [Cross-edition report](../research/corkboard-interoperability-002-20261128.md#phase-1-cross-edition-transfer-matrix)

## Measured binary layout

| Offset | Size | Observed interpretation |
| --- | ---: | --- |
| `0x0000` | 2 bytes | Little-endian unsigned 16-bit word: the **caret's byte offset** in the text area at the moment the note was written, zero based. Recorded at the close; see the note on rewrites below. Not the text length |
| `0x0002` | 2 bytes | Little-endian 16-bit word, **zero in every measured specimen**, including scrolled and selected states; purpose unestablished |
| `0x0004` | 2,860 bytes (`0x0B2C`) | Fixed-size text area holding **CP437** bytes separated by carriage returns (`0x0D`), visible text ending at the first NUL (`0x00`) |

Total measured size: **2,864 bytes (`0x0B30`)**. The RSX accessory and Information Center binaries independently show two 2-byte transfers and a `0x0B2C`-byte transfer on the same file handle. These static observations corroborate the layout; they do not prove a general parser or allocator. [Binary transfer offsets](../research/deskmate-corkboard-20261123.md#corkboard-storage)

In the RSX two-line specimen, editing the final `T` of `TEST` to `X` left the text length unchanged but changed the first word from `0x0029` to `0x0014`, supporting an insertion-position interpretation rather than a length field. The generic 3.05 fourteen-line specimen had a 377-byte text and first word `0x0179` (377 decimal).

The November 28 campaign separated the remaining readings. A caret inside a note is the discriminating state, because a caret at the end makes position and length coincide. Inserting one character at text index 51 of a 61-byte note produced a 62-byte text with word `0x0034` (52): position, not length. Moving the caret afterward without editing gave a word equal to the caret's final offset, so the value is captured at the write, not at the edit. Byte offsets and character positions coincide here because the encoding is single-byte.

Whether a close rewrites the file is narrower than it first appeared. A cold reopen, Home and Escape left the file byte-identical with whole-file hashes compared across the stop, and an earlier reopen-and-Home trial was reported identical without keeping its before-image. Two other trials did not behave as a plain no-write case: one reopened a 64-byte note, sent only Shift+Left and left a changed first word (57, where the previous session recorded 51), and one reopened a 2,666-byte note, pressed Home and left 2,624. The retained records cannot say whether the selection, or a reopen in the same boot after an edit, marked the buffer dirty, so **a general rule that cursor movement never writes is not established**; the conclusion is limited to the controlled cases. [Reconciliation](../research/corkboard-storage-001-20261128.md#reconciling-the-t4-t5-and-t6-sequences)

When the stored value lands on a line boundary it must not be over-read. The maximum specimen stores 42, and its text byte 42 is the CR that ends the first 42-byte row; the next row begins at byte 43. The cold-reopen capture draws the caret at the start of that next row, which is consistent with a caret left at the end of the first row, but the accessory's convention for a caret that sits on a CR was not isolated. Treat the field as the text-area byte the caret was on at the write; do not normalize 42 to 43, and do not assume a conventional insertion offset at that boundary.

Later trials pinned the drawing rather than the storage convention. A seeded
word of **20** in a 41-byte note reopened with the caret drawn inside the first
row at the named character, and a seeded word of **43** - past the end of that
41-byte text - opened with the file unchanged and the caret drawn at
end-of-text. The field is not validated on load; an out-of-range value degrades
to end-of-text instead of being rejected. Words of 29 (the CR ending the first
row) and 30 (the first byte of the second row) also reopened byte-identical, but
their drawn positions were not distinguished at pixel level, so the CR-boundary
convention stays open. [Caret trials](../research/corkboard-interoperability-002-20261128.md#where-the-caret-is-drawn)

Home and End are **row-scoped** motions in this editor, not logical-line
motions. On a note that was one logical line of 2,730 bytes drawn as 65 wrapped
rows, End stored 42 - the end of the first drawn row - and changed nothing else.

The second word stayed zero through every state tried, including a 65-row note scrolled to the top with the caret held in place, an active selection, and a refused keystroke at the capacity boundary. That excludes a first-visible-row or scroll offset, a selection anchor, and a line count for those states. **Do not assign a meaning to that second word** without an experiment that writes it.

## Clear, residual bytes, and recovery

In the measured RSX Clear operation, **only offset `0x0004` changed**: the first text character became NUL, and later text bytes remained on disk. The UI showed an empty note, but the old synthetic content remained recoverable after the terminator. A reader must therefore distinguish *visible text before the first NUL* from *raw buffer bytes*, and must not interpret residual bytes as currently displayed text. Both header words survived Clear unchanged; an earlier note that Clear zeroed the first word was wrong and is corrected. The repository's read-only `corkboard.parse_bytes()` reports the raw words, the visible CP437/CR text and the full snapshot. It does not sanitize residual data, and nothing here shows that Clear securely erases prior content. Treat files from real users as potentially containing deleted private content.

## Compatibility and limits

The demonstrated byte identity is confined to matched synthetic notes and named editions. A read-only inspection can recognize the measured size and CP437/CR/NUL profile, but **cannot reliably identify an arbitrary file by signature**: a stock all-zero note and unrelated zero-filled data are indistinguishable. Untested or unsupported cases include control characters other than CR, most of the CP437 high half by native entry, import/export, printing, any nonzero second-header-word meaning, and broader cross-edition migration.

A construction API now exists (below), but there is no in-place repair of an arbitrary file and no provenance check. `update_note` and `clear_note` trust the exact-size buffer they are handed: size alone does not establish that the bytes are a DeskMate note, which edition wrote them, or that they are structurally valid. The reader's signature limitation applies to the writer's input as well.

## Construction API and its policies

`deskmate_formats.corkboard` keeps its read-only surface (`parse_bytes`,
`parse_file`, the `Corkboard` snapshot with raw words, visible text and residual
bytes) and adds a writer: `create_note`, `update_note`, `clear_note` and
`text_bytes`, refusing unsupported requests with `PolicyError`. Its byte oracle
is native rather than self-referential: `create_note` reproduces five published
application-created files byte for byte from their own text and stored caret
word, and `clear_note` reproduces the published cleared file from its parent.

Every policy is a documented choice, not a measured universal:

* the first word defaults to the end of the new text and accepts any offset in
  `0..len(text)`; no insertion-boundary normalisation is applied, and the
  convention for a caret sitting on a CR was never isolated;
* the second word is zero for a new note and preserved by `update_note`, because
  no operation was observed to set it;
* `update_note` preserves bytes after the terminator unless the caller asks for
  them to be zeroed, and `clear_note` defaults to the measured one-byte Clear.
  Residual bytes are prior content: the reader does not report them as visible
  text, and the writer does not interpret them;
* `update_note` and `clear_note` accept any caller-supplied 2,864-byte buffer.
  Size is the only check, so a supplied buffer proves nothing about its
  identity, provenance or structural validity;
* 2,794 bytes is a default refusal point with an explicit override up to the
  last byte that still leaves a terminator. That ceiling is a **construction
  policy, not a capacity guarantee**: it is the largest composition demonstrated
  in a native editor, and logical lines and wrapped visual rows impose further
  constraints this module does not model, so a shorter text can still be
  refused by the original accessory;
* NUL, control bytes other than CR, DEL and non-CP437 strings are refused. That
  restriction is deliberate even though a seeded native note displayed and
  preserved the control range: the bytes were injected rather than typed, so
  this is a smaller profile for the normal path, not a limit derived from the
  seeded evidence;
* `sanitize=True` zeroes the buffer `clear_note` returns. It is not a secure
  erase of physical storage, of earlier copies, or of backups.

## Related storage

For context on other storage, see [architecture](../architecture.md), [compatibility](../compatibility.md), and the [illustrated comparison](../history/note-pad-corkboard.md). Financial Notebook `NOTEBOOK.DB`, Collections `.COL`, Information Center `INFOCNTR.DB`, and Filer `.FIL` use independently measured DMDB-style database framing rather than this fixed text buffer.

## Editable capacity

The 2,860-byte text area is not the editable capacity. Two units matter: a **logical line** is the bytes between CR delimiters, and a **drawn row** is what the accessory displays, wrapping a longer logical line across more than one row.

In the measured RSX 03.04.04 accessory at 640 × 480, a drawn row holds **42 characters** and the note accepted **65 drawn rows**. The 42 is a wrap width, not a cap on one line: a single logical line of 81 characters was accepted (and drew as more than one row) before that trial stopped. The largest note actually written was 65 full rows of 42 characters plus the 64 carriage returns between them, **2,794 text bytes**, and at that length the editor silently refused Enter, a printable character, and a mid-row insertion, with no message, while the caret and the close still worked.

That 2,794 is the largest composition demonstrated rather than a proven universal maximum. The capacity trials used CR-delimited lines short enough to fill exactly one drawn row each, so they establish the row budget for that shape; no trial drove a composition of wrapped logical lines to its refusal boundary, and another arrangement of the same budget was not measured. A note of 65 short rows refuses earlier than a note of 65 full rows, so the limit is structural rather than a byte budget; 66 bytes were never observed to hold text, which is not proof that no composition can reach them. [November 28 capacity trials](../research/corkboard-storage-001-20261128.md#experiment-3-real-editable-capacity)

These are three separate observations, not one model. A file holding **one**
logical line of 2,730 bytes - the same 65 drawn rows of 42 characters with no CR
at all - **loaded** completely, was drawn wrapped, and was saved unchanged. A
65-row composition at 2,794 bytes **refused further input** silently. Two edits
near a boundary left **residual bytes** after the terminator. The results are
consistent with a budget on drawn rows, and no load-time byte limit was reached
at 2,730 bytes, so the measured refusal is input-side. They do not establish the
complete capacity model: the refusal boundary for a wrapped or mixed composition
was not measured. [Wrapped-line trial](../research/corkboard-interoperability-002-20261128.md#phase-3-loading-input-refusal-and-residual-writes)

An edit near a soft-wrap boundary, or one whose stored caret lies past the
loaded text, can leave bytes **after** the terminator while the visible text stays
unchanged. Two such writes are published as native fixtures: one left a shifted
fragment of the note's own characters with a stray `0x0A`, and one left the two
typed characters behind the terminator. Neither damaged the visible text and
neither mechanism is established. [Residual writes](../research/corkboard-interoperability-002-20261128.md#an-unexplained-write-after-the-terminator)

## Character set

The text area stores **CP437** bytes, and the accessory renders and preserves them. Native entry of Alt+130 and Alt+225 on the numeric keypad stored `0x82` and `0xE1`, which the editor drew as `é` and `ß` and preserved across a cold reopen. A seeded note also carried eleven high bytes; two of them repeated those same natively entered values, so **nine further code points** - box-drawing, shading and accented bytes - were displayed correctly and saved unchanged.

That is a sample, not a sweep: two code points were entered natively and nine further code points were displayed from a seeded buffer. The reader accepts `0x20`–`0xFF` except `0x7F` as a **deliberately broader policy** chosen from that evidence, rejects other control bytes, decodes as CP437, and keeps the raw bytes regardless of decoding. It is not a measured claim that every high byte was exercised. [November 28 encoding trials](../research/corkboard-storage-001-20261128.md#experiment-4-character-set)

### The control range, seeded

A later seeded trial put `0x01`–`0x1F` and `0x7F` into the text, each byte
preceded by its own textual tag, and opened it in the 03.04.04 accessory.

| Byte class | Drawn | Stored on save |
| --- | --- | --- |
| `0x01`–`0x09`, `0x0B`–`0x1F` | each acted as a line break: one tag per drawn row | preserved byte for byte |
| `0x0A` (LF) | acted as a line break | **dropped when the note loaded**; the 159-byte visible text was then saved as-is (the only substitution observed) |
| `0x7F` (DEL) | drawn as a glyph, not as a row break | preserved |
| `0x0D` (CR) | line break | preserved |

These bytes were **seeded by an injector, not typed**, so they are
display-and-preservation evidence only: no trial typed one, and nothing here
establishes how the keyboard behaves for them. The reader and the writer still
reject them, because a typed note cannot be shown to contain them and a file that
does is outside the measured normal path; the evidence now exists to relax that
deliberately, with `0x0A` singled out. [Control-range trial](../research/corkboard-interoperability-002-20261128.md#phase-4-the-control-range)
