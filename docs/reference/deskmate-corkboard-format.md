# DeskMate Note Pad and Corkboard: read-only file format reference

**Status:** maintained, evidence-bounded reference for observed native files. This is **not** a complete vendor specification or a universal DeskMate database profile. Sources: [November 23 native write and cold-reopen campaign](../research/deskmate-corkboard-20261123.md#corkboard-storage); [November 28 header, capacity and encoding campaign](../research/corkboard-storage-001-20261128.md); [published fixture manifest](../../tests/fixtures/application-generated/manifest.json).

## Identification and editions

The observed Note Pad/Corkboard file has **no identifying magic signature**. The caller must supply provenance or an expected filename and edition. The native two-line Personal DeskMate 2 **01.00.00** `DMNOTEPD` was byte-identical to the RSX OEM DeskMate **03.04.04** `DMCORKBD` for matched synthetic text. The Tandy 1000 SL/2 ROM Desktop using **03.03.01** program disks produced the same bytes. Generic **03.05.00** also created a file of this size with a longer note; its fourteen-line save was measured separately. These tests do not establish universal interoperability for other editions, non-ASCII input, or larger notes.

The accessory module is named `DMNOTEPD.ACC` across several surveyed editions, but its displayed name and file naming conventions differ. On the RSX, Information Center **3.61** uses the same `DMCORKBD` text as the F10 Corkboard accessory. Its separate `INFOCNTR.DB` message records are **not** part of this format. [Edition matrix](../research/deskmate-corkboard-20261123.md#release-survey)

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

The second word stayed zero through every state tried, including a 65-row note scrolled to the top with the caret held in place, an active selection, and a refused keystroke at the capacity boundary. That excludes a first-visible-row or scroll offset, a selection anchor, and a line count for those states. **Do not assign a meaning to that second word** without an experiment that writes it.

## Clear, residual bytes, and recovery

In the measured RSX Clear operation, **only offset `0x0004` changed**: the first text character became NUL, and later text bytes remained on disk. The UI showed an empty note, but the old synthetic content remained recoverable after the terminator. A reader must therefore distinguish *visible text before the first NUL* from *raw buffer bytes*, and must not interpret residual bytes as currently displayed text. Both header words survived Clear unchanged; an earlier note that Clear zeroed the first word was wrong and is corrected. The repository's read-only `corkboard.parse_bytes()` reports the raw words, the visible CP437/CR text and the full snapshot. It does not sanitize residual data, and nothing here shows that Clear securely erases prior content. Treat files from real users as potentially containing deleted private content.

## Compatibility and limits

The demonstrated byte identity is confined to matched synthetic notes and named editions. A read-only inspection can recognize the measured size and CP437/CR/NUL profile, but **cannot reliably identify an arbitrary file by signature**: a stock all-zero note and unrelated zero-filled data are indistinguishable. Untested or unsupported cases include control characters other than CR, most of the CP437 high half by native entry, import/export, printing, any nonzero second-header-word meaning, and broader cross-edition migration. No write or in-place repair is promised.

For context on other storage, see [architecture](../architecture.md), [compatibility](../compatibility.md), and the [illustrated comparison](../history/note-pad-corkboard.md). Financial Notebook `NOTEBOOK.DB`, Collections `.COL`, Information Center `INFOCNTR.DB`, and Filer `.FIL` use independently measured DMDB-style database framing rather than this fixed text buffer.

## Editable capacity

The 2,860-byte text area is not the editable capacity. Two units matter: a **logical line** is the bytes between CR delimiters, and a **drawn row** is what the accessory displays, wrapping a longer logical line across more than one row.

In the measured RSX 03.04.04 accessory at 640 × 480, a drawn row holds **42 characters** and the note accepted **65 drawn rows**. The 42 is a wrap width, not a cap on one line: a single logical line of 81 characters was accepted (and drew as more than one row) before that trial stopped. The largest note actually written was 65 full rows of 42 characters plus the 64 carriage returns between them, **2,794 text bytes**, and at that length the editor silently refused Enter, a printable character, and a mid-row insertion, with no message, while the caret and the close still worked.

That 2,794 is the largest composition demonstrated rather than a proven universal maximum. The capacity trials used CR-delimited lines short enough to fill exactly one drawn row each, so they establish the row budget for that shape; no trial drove a composition of wrapped logical lines to its refusal boundary, and another arrangement of the same budget was not measured. A note of 65 short rows refuses earlier than a note of 65 full rows, so the limit is structural rather than a byte budget; 66 bytes were never observed to hold text, which is not proof that no composition can reach them. [November 28 capacity trials](../research/corkboard-storage-001-20261128.md#experiment-3-real-editable-capacity)

## Character set

The text area stores **CP437** bytes, and the accessory renders and preserves them. Native entry of Alt+130 and Alt+225 on the numeric keypad stored `0x82` and `0xE1`, which the editor drew as `é` and `ß` and preserved across a cold reopen; a seeded note containing eleven further box-drawing, shading, and accented bytes was displayed correctly and saved unchanged.

That is a sample, not a sweep: two code points were entered natively and eleven more were displayed. The reader accepts `0x20`–`0xFF` except `0x7F` as a **deliberately broader policy** chosen from that evidence, rejects other control bytes, decodes as CP437, and keeps the raw bytes regardless of decoding. It is not a measured claim that every high byte was exercised. [November 28 encoding trials](../research/corkboard-storage-001-20261128.md#experiment-4-character-set)
