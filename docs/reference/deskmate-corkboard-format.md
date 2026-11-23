# DeskMate Note Pad and Corkboard: read-only file format reference

**Status:** maintained, evidence-bounded reference for observed native files. This is **not** a complete vendor specification or a universal DeskMate database profile. Source: [November 23 native write and cold-reopen campaign](../research/deskmate-corkboard-20261123.md#corkboard-storage); [published fixture manifest](../../tests/fixtures/application-generated/manifest.json).

## Identification and editions

The observed Note Pad/Corkboard file has **no identifying magic signature**. The caller must supply provenance or an expected filename and edition. The native two-line Personal DeskMate 2 **01.00.00** `DMNOTEPD` was byte-identical to the RSX OEM DeskMate **03.04.04** `DMCORKBD` for matched synthetic text. The Tandy 1000 SL/2 ROM Desktop using **03.03.01** program disks produced the same bytes. Generic **03.05.00** also created a file of this size with a longer note; its fourteen-line save was measured separately. These tests do not establish universal interoperability for other editions, non-ASCII input, or larger notes.

The accessory module is named `DMNOTEPD.ACC` across several surveyed editions, but its displayed name and file naming conventions differ. On the RSX, Information Center **3.61** uses the same `DMCORKBD` text as the F10 Corkboard accessory. Its separate `INFOCNTR.DB` message records are **not** part of this format. [Edition matrix](../research/deskmate-corkboard-20261123.md#release-survey)

## Measured binary layout

| Offset | Size | Observed interpretation |
| --- | ---: | --- |
| `0x0000` | 2 bytes | Little-endian unsigned 16-bit word matching the **insertion/cursor position** in three nonempty observed write states; not the total text length |
| `0x0002` | 2 bytes | Little-endian 16-bit word, **zero in the measured specimens**; purpose unknown |
| `0x0004` | 2,860 bytes (`0x0B2C`) | Fixed-size text area; observed ASCII characters separated by carriage returns (`0x0D`), visible text ending at first NUL (`0x00`) |

Total measured size: **2,864 bytes (`0x0B30`)**. The RSX accessory and Information Center binaries independently show two 2-byte transfers and a `0x0B2C`-byte transfer on the same file handle. These static observations corroborate the layout; they do not prove a general parser or allocator. [Binary transfer offsets](../research/deskmate-corkboard-20261123.md#corkboard-storage)

In the RSX two-line specimen, editing the final `T` of `TEST` to `X` left the text length unchanged but changed the first word from `0x0029` to `0x0014`, supporting an insertion-position interpretation rather than a length field. The generic 3.05 fourteen-line specimen had a 377-byte text and first word `0x0179` (377 decimal). The second word remained zero even in the scrolled view. Do not assign a meaning to that second word without further differential tests.

## Clear, residual bytes, and recovery

In the measured RSX Clear operation, **only offset `0x0004` changed**: the first text character became NUL, and later text bytes remained on disk. The UI showed an empty note, but the old synthetic content remained recoverable after the terminator. A reader must therefore distinguish *visible text before the first NUL* from *raw buffer bytes*, and must not interpret residual bytes as currently displayed text. The repository's read-only `corkboard.parse_bytes()` reports both the raw words and visible ASCII/CR text while preserving the full snapshot. It does not sanitize residual data. Treat files from real users as potentially containing deleted private content.

## Compatibility and limits

The demonstrated byte identity is confined to matched synthetic notes and named editions. A read-only inspection can recognize the measured size and ASCII/CR/NUL profile, but **cannot reliably identify an arbitrary file by signature**. Untested or unsupported cases include maximum editable capacity, full-buffer behavior, CP437 and other encodings, control characters beyond observed CR/NUL, import/export, printing, nonzero second-header-word meanings, and broader cross-edition migration. No write or in-place repair is promised.

For context on other storage, see [architecture](../architecture.md), [compatibility](../compatibility.md), and the [illustrated comparison](../history/note-pad-corkboard.md). Financial Notebook `NOTEBOOK.DB`, Collections `.COL`, Information Center `INFOCNTR.DB`, and Filer `.FIL` use independently measured DMDB-style database framing rather than this fixed text buffer.
