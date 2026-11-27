# Corkboard: static investigation and a handoff (2026-11-26)

This note examines the accessory that hosts Corkboard and Note Pad —
`DMNOTEPD.ACC` — statically, and states what the native emulator campaign can
test. It continues the
[release survey and native trials](deskmate-corkboard-20261123.md), whose
observations it uses as ground truth for the note file's bytes.

Nothing here was executed. No emulator was started, no guest memory was read,
and no worktree or reserved resource of the concurrent campaign was touched.

## The measured facts this starts from

From the earlier native trials (not repeated here):

* the note file `DMCORKBD` is 2,864 bytes, identical byte-for-byte to the
  standalone Note Pad's `DMNOTEPD` file;
* typing two lines changed file offset `0x0000` and the bytes
  `0x0004`–`0x002C`, which is exactly the 41-byte text
  `CORKBOARD ATLAS TEST 20261123` + CR + `SECOND LINE` starting at `0x0004`;
* typing fourteen 27-character lines wrote a 377-byte text and left the first
  two bytes `01 79`, i.e. `0x0179` = 377;
* an edit that replaced one character mid-text left the text length unchanged
  and changed `0x0000` from `0x29` to `0x14` (= 20), with the changed character
  at `0x0017` (= 23, the twentieth text byte);
* **Clear** zeroed `0x0000` and wrote a NUL at `0x0004`, while every later text
  byte stayed in the file.

The stock file from the 03.05.00 media is 2,864 zero bytes
(SHA-256 `35ea3bc020cf509336e438b06974ec7aea3736f4d0fd3db23a741fa98bd3bb30`),
so the initial state is blank and every non-zero byte in a used file is written
by the program.

## Identity of the module

| Property | Value |
| --- | --- |
| File | `DMNOTEPD.ACC` (identical bytes in `dm303dk3` and `dm305dk2`) |
| Size | 14,295 bytes |
| SHA-256 (prefix) | `74fc7073cb1680fa…` |
| Format | MZ, header `0x200`, load image `0x35D7`, 13 relocations |
| Loader blocks | `1000:0000` / `0x1B20`, `11B2:0000` / `0xB0`, `11BD:0000` / `0x1A07` |

Strings relevant to this investigation, as **file** offsets (image offset =
file offset − `0x200`):

| Text | File offset | Image offset |
| --- | ---: | ---: |
| `CANCEL`, `CLEAR`, `PRINT` (button labels) | `0x3406`–`0x3420` | `0x3206`–`0x3220` |
| `The corkboard file was not found. Insert the disk containing DMCORKBD…` | `0x3422` | `0x3222` |
| `Do you want to create a file DMCORKBD on drive …?` | `0x34A3` | `0x32A3` |
| `Corkboard` (window/accessory title) | `0x3530` | `0x3330` |
| `CORKBOARD` (upper-case, help/error text) | `0x36B5`, `0x36F4` | `0x34B5`, `0x34F4` |

The second `DMCORKBD` occurrence is a *message*, not a second file name: the
accessory refers to one file, and the two strings differ only in the sentence
around the name.

## How the note is read and written

The accessory contains **no DOS open or read call**. Twelve `INT 21h` sites
exist and their functions are version query (`AH=30h`, two sites), vector
get/set (`AH=35h`/`25h`, four sites), `IOCTL` (`AH=44h`), close (`AH=3Eh`),
write to handle 2, memory resize (`AH=4Ah`, three sites) and exit (`AH=4Ch`).
There is no `AH=3Dh` and no `AH=3Fh` anywhere in the image.

Persistence therefore reaches the note file through the Desktop, not through
DOS in this module. The calls that carry it are far calls:

* a direct far call to `BBDA:8C18` at file `0x1332` — a segment far outside the
  module, and therefore a host-provided entry point;
* ten indirect far calls through memory (`FF 1E`), at `0x1324`, `0x133A`,
  `0x1415`, `0x15A7`, `0x15E4`, `0x171E`, `0x1908`, `0x1969`, `0x19A0` and
  `0x1A21`, i.e. through a table of service vectors the Desktop fills in;
* four relocated far calls to offsets `0x10D1`, `0x10D5`, `0x10CD`, `0x10B2`,
  `0x10D9` in the module's own segment, which are its internal entry stubs.

Two data descriptors carry a relocated segment word `0x01BD` at file `0x3542`
and `0x35D6`, next to the title string and a run of tagged data that includes
the markers `PRGUF` and `DMGUF` and the signature `DCBAABCD`. These look like
module/resource descriptors; their meaning is not established here.

**Inference, not observation:** the accessory asks a Desktop service to open,
read and write `DMCORKBD`, and the service — not the accessory — performs the
DOS work. This is supported by the absence of open/read in the module and the
presence of host far calls, but the service's identity and its file mechanism
are unverified.

## The note buffer

The file layout is observed; the buffer layout is inferred from it.

Observed, for a 2,864-byte file whose text begins at `0x0004`:

| Written content | Word at `0x0000` | Bytes after `0x0004` |
| --- | ---: | --- |
| 41-byte two-line note, cursor at end | `0x0029` = 41 | 41 text bytes, then zeros |
| 377-byte fourteen-line note, cursor at end | `0x0179` = 377 | 377 text bytes, then zeros |
| same note, one character replaced at text index 19, cursor there | `0x0014` = 20 | 41 bytes, one changed |
| after **Clear** | `0x0000` = 0 | `0x0004` = NUL, later bytes retained |

Candidate structure:

```text
offset  size  candidate meaning                      confidence
0x0000   2    insertion position / cursor offset     strong (mid-text case)
0x0002   2    unknown; zero in every observed file    none
0x0004  2860  text bytes, NUL-terminated or delimited by a length elsewhere
```

Why the cursor reading wins over "length": both end-of-text cases agree with
either reading, and only the mid-text edit separates them. That edit left the
text length at 41 while the word became 20, which is the character position the
edit ended at. The earlier report's note that "the unchanged text length with a
smaller byte at offset zero rules out interpreting that byte as the total
length" is the same observation, stated as an exclusion.

Why `0x0002` is unknown: it is zero in the stock file, in the two-line note and
in the fourteen-line note. A field that is zero in every observed state could
be a scroll offset, a selection anchor, a flag word or reserved space. Guessing
would be worse than leaving it open.

Where the **live** buffer is remains unresolved. The 2,864-byte file is what
the Desktop writes; the editor's working copy may be that file's image in
memory, a separate allocation, or a structure the Desktop owns and the
accessory draws from. The file's shape (a 4-byte header then a flat text area)
is consistent with a memory image written verbatim, but consistency is not
evidence.

## What is static, relocated, or runtime

These are different things and are kept apart:

* **static file offset** — e.g. the `DMCORKBD` string at file `0x3468`;
* **image offset** — the same byte at `0x3268`, after subtracting the `0x200`
  header;
* **analysis address** — `1000:3268` under the synthetic load paragraph used
  for disassembly; a labelling, not a guest address;
* **relocated address** — a word the MZ loader adds the load segment to; the
  module has 13 such sites, and their runtime values depend on where DOS loads
  it;
* **observed guest address** — a segment:offset actually seen in the emulator.
  None is claimed here.

A candidate static location is never an authoritative runtime text buffer. The
handoff below is written so that only the last category can settle it.

## Handoff to the native emulator campaign

The structured list is in
[`deskmate-corkboard-handoff-20261126.json`](deskmate-corkboard-handoff-20261126.json).
Each entry states the hypothesis, the smallest controlled edit, the expected
observation, and what would refute it.

The three highest-value experiments:

1. **Locate the live buffer, not the file.** After typing a distinctive string
   and saving, scan guest memory for that string. If it appears in the
   accessory's own segment or PSP allocation, the accessory owns the buffer; if
   it appears only inside the Desktop's data, the buffer is shared and the
   accessory is a view. This single result decides most of the rest.
2. **Calibrate `0x0000` against the cursor.** With a known text, press Home,
   End, and move one character at a time, recording the word at file `0x0000`
   after each save. Expect 0 at Home, the text length at End, and the position
   after each move. Any other value refutes the cursor reading.
3. **Distinguish "buffer cleared" from "file cleared".** Clear, then Escape
   without saving, then re-open. If the note returns, Clear only cleared the
   live buffer and the file write is what makes it permanent; if it does not,
   Clear wrote through. The earlier trial showed the file changed, so this
   separates the two mechanisms rather than repeating the observation.

Expected memory changes for controlled edits, to be confirmed or refuted:

| Edit | Expected file/memory change |
| --- | --- |
| type `A` at start of empty note | byte `+0x0004` = `41`, word `+0x0000` = 1 |
| type ten characters | bytes `+0x0004…+0x000D`, word = 10 |
| Home, then type | word = 1, previous text shifted one byte |
| Backspace at position *k* | byte *k−1* removed, tail shifted, word = *k−1* |
| Clear | word = 0, byte `+0x0004` = 0, later bytes unchanged |
| fill beyond 2,860 bytes | a refusal or truncation at the capacity boundary |

Two cautions for the worker:

* the earlier corrupted-note result came from a run that observed the
  framebuffer but not the store. Framebuffer agreement is not persistence
  agreement; the file and the live buffer must both be checked;
* the note file is shared between Corkboard, Note Pad and Information Center.
  An edit made through one application is evidence about the *store*, not
  necessarily about the other application's view of it.

## Publication boundary

`DMNOTEPD.ACC`, `DMCORKBD` and the reference media are third-party commercial
artifacts and are not published. This note publishes hashes, sizes, offsets,
string text that is interface or error copy, structural counts and hypotheses,
consistent with existing project practice. Guest-memory dumps and full listings
stay in the private lab.
