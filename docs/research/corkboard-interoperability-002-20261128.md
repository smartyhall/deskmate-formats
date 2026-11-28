# Corkboard and Note Pad interoperability, capacity and control bytes (2026-11-28)

This campaign continued the [November 28 storage work](corkboard-storage-001-20261128.md)
with a different question: what happens when a note file crosses between DeskMate
editions, and what the editor really does at its boundaries. It transferred
published specimens into two hard-disk editions through exact bytes rather than
retyping, separated plain reopening from editing, drove a wrapped logical line to
its boundary, seeded the control range the reader had only ever rejected, and
implemented a writer that reproduces published native files byte for byte.

Campaign metadata: owner **Freebuff** (native desktop agent), campaign
`corkboard-interoperability-002`, branch `freebuff/corkboard-interoperability-002`,
base commit `5045901177b735c7f5aaaa3512e4d4741a9d7bb2`, emulator 86Box **7.0**
automation build with executable SHA-256
`e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d`, automation
port 8765. Model identity and reasoning effort are not exposed to the agent and
are recorded as unknown.

Everything below is either a **native observation** in this campaign's own
emulator sessions or an explicitly labelled inference. Private raw captures,
socket journals, injected media, stopped images and extracted files stay in the
lab; the repository receives the eligible synthetic fixtures, documentary
screenshots, authored specification changes and regression tests.

## Environment and method

The campaign ran in its own checkout with its own qualified environment
(`deskmate_formats.campaign_env` provision → preflight `qualified`, all eleven
checks passing, receipt kept with the run). The parent, the isolated `-I` child
and the checkout all resolved to this campaign's installation of base commit
`50459011`; the shared system interpreter and the older shared site-packages copy
were not used or modified.

Three campaign-owned machines were cloned by verified file copy, never written in
place:

| Machine | Source | State |
| --- | --- | --- |
| `rsx-a` | sealed RSX 03.04.04 install, image `3085c689…6a107fc1` | 54,525,952-byte FAT16 volume, 2,048-byte clusters, `DESKMATE\DMCORKBD` 2,864 zero bytes |
| `alt305-a` | alternate generic 03.05.00 installation | same layout; its stock note held the published fourteen-line note |
| `pdm2-a` | Personal DeskMate 2 profile | read-only copies of the reconstructed 360 KiB DOS and PDM2 media |

The new instrument is a **private in-place FAT injector** (`local-results/cb2/fat.py`
in the checkout; the tool itself is campaign-private). It parses the volume's
partition table and BPB, finds one existing file, requires the payload to fit the
clusters already allocated to it, rewrites only that file's data and its directory
size word, and reads the file back before reporting. It never creates files,
never changes allocation, and never touches a FAT copy or the boot sector. Every
injection receipt records the volume's whole-image SHA-256 before and after, so a
reviewer can see that the only difference is one file.

That mattered for more than convenience: it is what makes an *exact* transfer
test possible. Typing a specimen into a guest proves that the guest can be typed
into, not that these bytes arrived; injecting the published file and reading it
back through the independent walker proves the bytes.

Guest control used the packaged authenticated client only: held stepping, verified
input, the live note array in RAM, PNG captures at every state change, and a
stopped-image extraction for every result. No host input injection and no
emulator-display clicks were used.

## Phase 1: cross-edition transfer matrix

Two hard-disk editions were exercised in both directions. `03.04.04` is the RSX
OEM Corkboard accessory; `03.05.00` is the alternate generic installation, whose
accessory is the same `DMNOTEPD.ACC` family under the Corkboard name.

| Trial | Receiver | Input (source edition) | Open and display | Close without edit | Edit and save | Result |
| --- | --- | --- | --- | --- | --- | --- |
| T01 | 03.04.04 | 377-byte fourteen-line note (03.05.00) | full text, scrolled to lines 2–14, caret at end | whole file byte-identical | — | preserves |
| T02 | 03.04.04 | same note | as T01 | — | `Z9` appended: 379 bytes, word 0 → 379, only offsets `0x0000`, `0x017D`, `0x017E` changed | edits |
| T03 | 03.05.00 | 41-byte two-line note (03.04.04) | both lines, caret after `SECOND LINE` | whole file byte-identical | — | preserves |
| T04 | 03.05.00 | 17-byte CP437 note (03.04.04) | CP437 glyphs drawn | — | `Z9` appended: 19 bytes, word 0 → 19, offsets `0x0000`, `0x0015`, `0x0016` | preserves CP437 |
| T05 | 03.05.00 | 2,794-byte maximum note (03.04.04) | all 65 rows loaded, viewport shows 13 | whole file byte-identical | `Z9` refused silently | preserves, refuses input |
| T06 | 03.05.00 | cleared note, word 20, residual text (03.04.04) | empty note | whole file byte-identical, word 20 kept, residual kept | — | preserves |
| T07 | 03.05.00 | all-zero 2,864-byte buffer | empty note, no create dialog | — | `Z9` typed: 2-byte text, word 2, closed | creates |

What this establishes, and what it does not:

* **Byte-preserving interoperability is real in both directions** for the
  measured note shapes: reopening a foreign note and closing it without an edit
  changed no byte in every trial across the two editions (T01, T03, T06, T08,
  T09, T12, T13, T14; T05 also closed byte-identically after a refused
  keystroke), including a cleared note with residual content and a note at the
  demonstrated maximum.
* **Editing across editions works** at ordinary lengths, and the receiving
  edition writes the first header word as the new caret position in its own
  right (`379`, `19`), not as a preserved length.
* **CP437 survives a foreign edit**: the 3.05 accessory drew the seeded high
  bytes and appended ASCII after them without substituting any.
* **The 2,794-byte composition is readable by both editions**, and 3.05 refused
  further input at that size exactly as the RSX did. That is a *shared refusal
  boundary for this composition*, not proof of a shared capacity rule; a wrapped
  or shorter-row composition was not driven to refusal in 3.05.
* **The editions are not independent implementations of one tested path**:
  03.05.00's live text array sits at a different guest address (`0x47B48`) than
  03.04.04's (`0x4A0E8`), which is a runtime observation about different builds,
  not a format property.

The 03.03.01 (SL/2 ROM Desktop with program disks) and Personal DeskMate 2
01.00.00 legs were **not completed in this campaign**. The PDM2 media exist as
reconstructed 360 KiB images with `DMNOTEPD` present and the injector handles
that FAT12 volume, but no PDM2 or SL/2 session was run before the campaign's
evidence budget was reached, so no cross-edition claim is made for them here.
That is a recorded limitation, not a negative result.

## Phase 2: what a close writes, and where the caret is

Campaign 001 left T4/T5/T6 ambiguous: one selection trial left a changed first
word, and nothing retained distinguished a selection-triggered write from a
dirty-on-reopen state.

This campaign approached it from the other end: seed a known file, boot cold, do
exactly one thing, close, and compare the whole file.

| Trial | Seeded state | Operation | Stored word after | Whole file |
| --- | --- | --- | --- | --- |
| T08 | 41-byte two-line note, word **20** (interior) | open, close | 20 | byte-identical |
| T09 | same text, word **43** (past the 41-byte text) | open, close | 43 | byte-identical |
| T13 | same text, word **29** (on the CR) | open, close | 29 | byte-identical |
| T14 | same text, word **30** (immediately after the CR) | open, close | 30 | byte-identical |
| T12 | same text, word 41 | open, five Shift+Left, close | 41 | byte-identical |
| T06 | cleared note, word 20 | open, close (03.05.00) | 20 | byte-identical |

**A cold open followed by a close with no text change wrote nothing in every one
of the eight trials listed above**, including an active selection. The stored word is therefore not
recomputed on open or on close by itself. Campaign 001's T5 changed the word after
a selection *within a boot in which the note had already been edited*; T12
reproduces its key gesture on a clean, unedited open and leaves the file alone.
The retained evidence still cannot say whether that earlier write came from the
selection or from the earlier edit in the same session, but it does exclude
"a selection alone always marks the note dirty" for this clean state.

### Where the caret is drawn

The stored word is a byte offset in the text area, and the accessory draws the
caret there:

* word **20** of a 41-byte note put the caret inside the first row, at the
  character the offset names, not at the row end or the text end;
* word **43** of a 41-byte note - a value **past** the visible text - was drawn
  at the end of the text. The field is not validated on load, and an out-of-range
  value degrades to end-of-text instead of being rejected;
* word **29** (the CR that ends the first row) and word **30** (the first byte of
  the second row) both reopened with the file unchanged; their drawn positions
  were not distinguished at pixel level in this campaign, so the row-boundary
  convention stays open exactly as campaign 001 left it.

### End moves to a drawn-row boundary, not the logical line end

In T10 the note was one logical line of 2,730 bytes, drawn as 65 wrapped rows.
Pressing **End** left the stored word at **42** - the end of the first drawn row -
and the text unchanged. So End is not "end of logical line" in this editor; it is
a row-scoped motion. Read with campaign 001's T6 (Home from a wrapped row moved
the caret back 42 bytes), the editor's Home/End work in drawn rows.

## Phase 3: the capacity model, from the load side

The 2,794-byte composition of campaign 001 is 65 CR-delimited rows of 42
characters. This campaign asked whether the *same* row budget expressed as one
wrapped logical line is also accepted.

T10 seeded a single logical line of **2,730 bytes** - 65 drawn rows of 42
characters with no CR at all - and opened it. The accessory loaded **all 2,730
bytes**; the live array matched, the display showed the wrapped rows, and the
saved file kept the visible text byte-for-byte. So:

* the editor's limit is on **drawn rows**, and it is not a limit on logical
  lines or on stored bytes at load time;
* a 65-row wrapped line is inside the budget, which is consistent with the row
  model rather than with a byte budget, since 2,730 bytes alone is 64 short of
  the demonstrated maximum.

The refusal itself is an **input-side** rule: in T10 the typed character did not
reach the visible text at all, and in T05 (2,794 bytes, CR-delimited) the same
silent refusal appeared. This campaign did not drive a wrapped composition to its
refusal boundary, so the boundary value for that shape remains unmeasured; what
is established is that 65 wrapped rows load, and that the composition's limit is
not a byte limit.

### An unexplained write after the terminator

T10 also produced the campaign's most surprising byte pattern. After End (word
42) and one typed `X`, the visible text was **unchanged** (2,730 bytes, still
terminated) but 63 non-zero bytes appeared **after** the terminator: a shifted
fragment of the note's own character pattern (`89AB…V`) containing one `0x0A`,
which the note format otherwise never stores.

T11 produced a related pattern. Its seeded note kept a `0x0A` control byte; on
load the editor dropped that byte from the visible text (160 → 159 bytes) but the
stored caret stayed beyond the remaining text. The typed `Z9` then appeared on
screen on its own row, while the saved file kept the 159-byte visible text, stored
a first word of **161** (not the 159-byte text length, and not the 160-byte caret
this campaign had seen before that byte was dropped) and wrote `Z`, then `Z9`
(with intervening NULs) **after** the terminator.

Neither write damaged the visible text. Both are recorded as **observed
anomalies with an unestablished mechanism**: an edit near a soft-wrap boundary, or
an edit whose stored caret is beyond the loaded text, can leave bytes outside the
visible text. The practical consequences are already in the reference: the reader
must not interpret residual bytes as visible text, and a writer must not assume
the area after the terminator is zero or meaningless.

## Phase 4: the control range

The reader had always rejected control bytes other than CR because nothing had
exercised them. A seeded note (`<01>` `0x01` … `<1F>` `0x1F`, `<7F>` `0x7F`,
each byte preceded by its own tag) was opened, inspected, edited and saved on
03.04.04.

| Byte class | Displayed | Preserved on save | Notes |
| --- | --- | --- | --- |
| `0x01`–`0x09`, `0x0B`–`0x1F` | each ended the drawn row: one tag per row | yes, byte for byte | the editor acts on them as line breaks but stores the original bytes |
| `0x0A` (LF) | acted on as a line break | **no** - removed from the visible text | the only substitution observed |
| `0x7F` (DEL) | drawn (with a glyph) | yes | stored unchanged |
| CR (`0x0D`) | line break | yes | as measured before |

Two qualifications matter here. The file was **seeded**, not typed - a user
cannot enter these through the keyboard - so this is *display and
preservation* evidence, not key-entry evidence. And the editor's treatment of
control bytes as row breaks means the on-screen layout of such a note is not its
stored layout.

This does not change the reader's policy: it still rejects control bytes other
than CR, because a *typed* note cannot contain them and a file that does is
outside the measured normal path. The evidence now exists to relax that policy
deliberately in a later change, with `0x0A` singled out as the one value a native
save rewrites.

## Phase 6: a writer that reproduces native files

`deskmate_formats.corkboard` now has a construction API beside the unchanged
read-only one: `create_note`, `update_note`, `clear_note`, `text_bytes`, and a
`PolicyError` for refusals. The read-only `parse_bytes`/`parse_file` and the
`Corkboard` snapshot are unchanged.

The byte oracle is strong because it does not involve the writer at all: the
writer reproduces **five published application-created files byte for byte** -
`rsx-two-lines`, `305-alternate`, `rsx-cp437-20261128`,
`rsx-maximum-2794-20261128`, `rsx-caret-selection-20261128` - and
`clear_note` reproduces the published cleared file from its parent. Those are
native files from other campaigns, selected only by their measured caret word.

The policies are written down in the module and in the
[format reference](../reference/deskmate-corkboard-format.md), and each is a
choice rather than a measured universal:

* the first word defaults to the end of the new text, and a caller may set any
  offset in `0..len(text)`; nothing is normalised to an "insertion boundary";
* the second word is zero for a new note and **preserved** on update, because no
  operation was ever observed to set it;
* bytes after the terminator are preserved on update unless the caller asks for
  them to be zeroed, and `clear_note` reproduces the measured one-byte Clear;
* 2,794 bytes is the default refusal point with an explicit
  `allow_above_demonstrated=True` override up to the last byte that still leaves
  a terminator, because it is a demonstrated maximum, not a proven capacity;
* NUL, control bytes other than CR, DEL and non-CP437 strings are refused.

### Native qualification

The writer was then qualified against the applications themselves, on both
editions, with a tool-built note (four synthetic lines including CP437
characters, caret at the end):

| Trial | Edition | Displayed | Edit and save | Result |
| --- | --- | --- | --- | --- |
| T15 | 03.04.04 | four lines, CP437 glyphs drawn, caret after the last line | `Q` typed at the restored caret | 53-byte text, word 0 → 53, **only** the header word and offset `0x0038` (the `Q`) differ from the tool-built file |
| T16 | 03.05.00 | same | same | same differential: word 53, only the header word and the `Q` |

That is the qualification the earlier report asked for: the note was generated
by the modern implementation, opened in the original accessory, its content read
from the screen, edited and saved by the application, extracted, and compared
with the writer's own bytes. The application did not rewrite a single byte the
writer had chosen; it appended the typed character and updated the caret word.

Two limits stay attached. The qualification covers one text shape on two
editions, not every construction the API can produce - an empty note, a note with
residual bytes, and a note above 2,794 bytes were not opened natively. And the
second header word was never exercised, because no operation sets it.

## Phase 5: Information Center on the same buffer

Information Center **3.61** was opened on a cold boot with the same tool-built
note in place (T17). Its dashboard's yellow notepad drew all four lines,
including the CP437 characters, without opening the accessory first, and the note
file was **byte-identical** after the visit - as were `INFOCNTR.DB` and the rest
of the installation apart from desktop state.

That is one direction of the interaction only. This campaign opened the dashboard
and closed it without editing. It did not edit the note through the dashboard,
so the earlier campaign's dashboard-edit observation
([T4 in the November 23 report](deskmate-corkboard-20261123.md#rsx-write-and-cold-reopen-trial))
remains the only measured write through that path, and this campaign adds nothing
about in-memory state that separates the two applications.

## Failures, limits and what was not done

* **The SL/2 03.03.01 and Personal DeskMate 2 legs were not run.** Media exist
  (PDM2 as reconstructed 360 KiB images, and the injector parses that FAT12
  volume), but the campaign reached its evidence budget first. No cross-edition
  claim is made for either edition. The runner for that leg is written and its
  first PDM2 boot was not attempted.
* **Information Center was exercised read-only.** No dashboard edit, so the
  question of distinct in-memory state between the accessory and the dashboard
  stays open.
* **One input scan bug cost a session.** An empty visible text made the RAM
  search treat an empty needle as matching at every offset; it was fixed
  (empty needle returns nothing, hits are capped) and the interrupted leg was
  re-run from a fresh injection.
* **A sync command was killed at its timeout mid-session.** The killed session's
  emulator exited with it, a stale automation token was removed after confirming
  no listener, and every later session ran as a background job.
* **Two writes recorded but not explained** (T10, T11) - see above. They are
  published as fixtures; the mechanism is not claimed.
* **The second header word remains unexplained.** This campaign did not add a
  state that sets it; it stayed zero in every file it produced. It is preserved by
  the writer and never attributed a meaning.
* **No pixel-level caret measurement.** Caret positions are reported from what
  the captures show at the character cell, not from a renderer measurement, so
  the CR-boundary convention stays open.

## Reproduction

Private inputs are the campaign clones, the emulator build and the injected
specimens. With those:

```text
inject the published specimen into DESKMATE\DMCORKBD of a campaign clone
launch visibly, held at 0 ms, on loopback 8765
advance 20000 ms, type "CD \DESKMATE", ENTER, "DESK", ENTER, advance 12000 ms
F10, Down x5, ENTER; capture; run the scripted steps; ESC; ESC; ENTER
quit through the socket, then extract DMCORKBD and compare whole files
```

`tools/experimental/draw_disk.py` and 7-Zip 26.05 both read the stopped image;
this campaign's injector read-back is a third, independent check of the same file.

## Timing checkpoints (host wall clock, not guest time)

| Checkpoint | Time (local) |
| --- | --- |
| Campaign environment ready, preflight `qualified` | 23:53 |
| First emulator launch (held, 0 ms) | 23:58 |
| First verified native interaction | 00:00 |
| First useful cross-edition specimen (T01, byte-identical) | 00:04 |

Guest time is recorded per session in the private receipts; it is not mixed with
host elapsed time here.

## Visual exemplars

Ordinary documentary screenshots of synthetic campaign content under the
operator's 2026-11-21 authorization: the 03.05.00 accessory showing a foreign
CP437 note, the 03.05.00 accessory showing the 2,794-byte note scrolled to its
first rows, and the 03.04.04 accessory showing the seeded control-range note.
