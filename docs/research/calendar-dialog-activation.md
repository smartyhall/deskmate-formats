# DeskMate Calendar dialog activation

DMCSR keeps window allocation boundaries and a selected window identifier
separately from Calendar's control index. Its Change Event input handler
pushes window records, temporarily selects the window for the focused control,
then unwinds and restores the parent window. On a separate E02 clone, the
approved six-byte comparison showed a reversible increase of three window
records for both Change Event and Find Date. The small-record count
distinguished the two dialogs. Moving between Description and Start Time
left all six bytes unchanged. The result establishes an activation indicator
for the tested views and clone. Other dialogs can share the same counts.
[Completed focus experiment and archived evidence](https://github.com/smartyhall/deskmate-formats/pull/44)

## Static call path

The pinned inputs were `CALENDAR.PDM` SHA-256
`819df5658b663aa69b15584abf805062679e97f587f3404738f6e82876e4bd23`
and `DMCSR.R89` SHA-256
`085edb2f2c67ae323343d9efedd7c731778f5fbb8dc59ed8bd6560006b45da75`.
Both use a `0x200`-byte MZ header. Worked on copies of the existing
Ghidra 12.1.4 projects at synthetic `1000:0000` with autoanalysis disabled.
Bounded pseudo-disassembly and selected function decompilations were
cross-checked with GNU i8086 objdump, relocation entries, little-endian
reference words and direct-call arithmetic. File offsets below refer to
the original modules. Segment overrides, indirect calls and carry branches
are taken from the instructions. Decompiler output is supporting evidence
where it agrees. Original bytes and listings remain private.

| Module and file offsets | Verified static relationship |
| --- | --- |
| Calendar `0xC775`, `0xC789` | Writes the Change Event title pointer to `DS:0x2124`, then enters the shared editor at `0xC363`. The Add path writes a different title pointer at `0xC6FE` before calling the same editor. |
| Calendar `0xC4D4`, `0xC4E7`, `0xD647`, `0xD64D` | Passes the same descriptor `DS:0x22C6` to DMCSR selectors `0x20E3` and `0x20E4`. The named DMCSR dispatch slot was verified in the previous run. |
| DMCSR table `0x12AF7`, `0x12AF9` | Original low-selector table entries point to `0x5B05` and `0x5C24`. The first builds and draws controls, then pops its temporary context before returning. The second establishes the input context, dispatches to the selected control and retains its parent context until it returns an event. |
| DMCSR `0x2442..0x246F`, `0x2496..0x2534`, `0x2569..0x2583` | Saves the previous selected handle, adds a marked context via `0x27FE` and `0x2A2E`, creates the dialog window, and selects it. The public selector table also exposes distinct entries for creating, selecting and retrieving a window (`0x2D`, `0x2E`, `0x2F`). |
| DMCSR `0x5E7C..0x5EA6`, `0x6B3F..0x6C15` | Uses Calendar's descriptor byte `+3` and pointer table `+0x13` to choose the control. The input handler saves the parent handle, installs a child window for the enabled control, invokes its handler, then removes the child and restores the parent. The selected handle can therefore differ while the same modal dialog is open. |
| DMCSR `0x5CE2`, `0x5D0F`, `0x2470`, `0x2821` | Both normal and error return paths call the context pop. It scans backwards through `0x3C`-byte window records to the marked frame, restores the stack boundary, and restores the saved handle or the empty sentinel. It also unwinds the small-record area. |
| Calendar `0xC539`, `0xC678`, `0xC67F`, `0xC682` | The returned `0x001B` takes the cancel path, sets a stack-local flag, and bypasses the record copy, which is gated on `0x000D`. The cleanup call at `0xC67F` resolves to selector `0x2016`, whose original table entry clears per-context input state at DMCSR `0x2DD5`. The window pop is in the input handler's own return path. |

### Distinguishing focus, activation and dialog identity

The Change Event descriptor stores the control count `9` at `+0x10` and the
table pointer `DS:0x22B4` at `+0x13`. The instructions at `0x5FCC..0x6008`
cycle through this table on Tab or Shift+Tab and write the resulting index.
The draw path at `0x5E5A..0x5E66` copies the current index to `+4` when it
changes. These are editor-local control fields.

| Index | Calendar descriptor | Control | Basis |
| ---: | --- | --- | --- |
| 0 | `DS:0x2196` | Event date | First edit buffer and form order |
| 1 | `DS:0x21C6` | Start Time | Static descriptor and prior live focus control |
| 2 | `DS:0x2260` | Start AM/PM | Two-choice descriptor and form order |
| 3 | `DS:0x21F6` | End Time | Time buffer and second Shift+Tab visual checkpoint |
| 4 | `DS:0x2282` | End AM/PM | Two-choice descriptor and form order |
| 5 | `DS:0x2226` | Description | Description buffer cross-reference and prior live focus control |
| 6 | `DS:0x229A` | Alarm | Single checkbox and form order |
| 7 | `DS:0x2126` | OK | Label pointer and `0x000D` command word |
| 8 | `DS:0x213A` | Cancel | Label pointer and `0x001B` command word |

The earlier RAM captures reproduce the same focus results after reopening
and cancelling. The title pointer and text persist in day view. The old
approved spans contain none of the DMCSR window bookkeeping.

Find Date uses a different descriptor, `DS:0x1AA0`, and the same two DMCSR
selectors. Calendar file `0x5404` draws it, `0x5411` runs its input loop,
and `0x541E` tests for Escape. Descriptor `+5` points to layout `DS:0x1A2C`.
The Change Event layout is `DS:0x211C`. DMCSR `0x2505..0x2517` copies the
layout size words into the allocated window record. The two layouts differ
in those words, so the outer window's geometry is a possible second-stage
discriminator for Change Event versus Find Date. The actual record offset
depends on the parent stack boundary. Add Event shares the Change Event
layout. Separating Add from Change would also need the title-pointer
comparison, gated on independent activation evidence.

## Candidate window-context words

| DMCSR operand | Static evidence | Interpretation to test |
| --- | --- | --- |
| `ES:0x0F9C`, 2 bytes | Initialized to `0x079C` at `0x27EF`. A large allocation advances it by `0x3C` at `0x28A2..0x28CE`. The marked-frame allocator advances it by a further `0x3C` and commits it at `0x2A7F`. The unwind writes the restored boundary at `0x283D`. | Upward boundary of the window records. Primary focus-independent candidate. |
| `ES:0x0F9E`, 2 bytes | Initialized to `0x0F9C` at `0x27F6`. The allocation path uses `0x10`-byte records growing in the other direction. `0x2ABF` moves the boundary down for a marker and `0x286F` or `0x288E` restores it. | Lower boundary of small records. Corroborates a nested context and can vary with control setup. |
| `ES:0x0FA0`, 2 bytes | Saved to the marked record by `0x2451..0x2455`, set on selection at `0x2579`, retrieved by `0x2584` and restored at `0x2489` or set to `0xFFFF` on the empty path. `0x2985` accepts handles through `0x07FF` and compares the low 11 bits of record words. | Selected window handle. It can name a child control window or be reused. Interpret changes alongside the boundaries. |

The static prediction for settled Change Event was an increase in the
upward boundary in both focus variants, followed by restoration to A at C.
The marked context and the dialog window explain two `0x3C` increments.
The selected control path can add a third. Exact depth is a measurement,
including whether the sample lands in the child input path. Find Date
should exercise the same general push and pop mechanism. An unchanged
boundary with a changed handle would support window selection without
modal growth. Comparable boundary growth in idle would undermine the
proposed discriminator at this sample cadence. A failed restoration or
different focus depths would require resolving nesting and sampling before
assigning a modal predicate.

## Register-only repeat and approved read boundary

The original Calendar clone stayed held with its observer owner. A separate
RSX/DOS clone booted a byte-verified copy of the archived E02 disk, using
independent config, NVRAM, machine identity and authenticated endpoint. The
source E02 database SHA-256 was
`0af0896163c24c992fa515ddca8c45a31496250d6ba84c9f08e28020a07fe0d9`.
The held final disk matched the complete source disk byte-for-byte. The
repeat sampled registers at one-ms steps during opening and closing. No
new guest-memory spans were read in this repeat.

| Held checkpoint | Guest ms | Frame | Visual label |
| --- | ---: | ---: | --- |
| A | 18,992 | 1,253 | October 23 day schedule with the E02 row selected |
| B Description | 19,596 | 1,289 | Change Event, Description selected |
| B Start Time | 20,148 | 1,322 | Same dialog and values after four Shift+Tabs, Start Time selected |
| C | 20,752 | 1,358 | Escape restored the day and row |
| Find Date | 21,892 | 1,427 | Distinct modal opened through Search, date unchanged |
| Final day | 22,496 | 1,463 | Escape restored the day and row |

DMCSR ran with code segment `0x0D76` and context `ES=0x1DB7` in both the
archived original run and the repeat. The repeat stopped at DMCSR file
`0x25B5` at 19,136 ms, immediately after the `ES:0x0FA0` load into BX.
It also reached file `0x282D` at 20,292 ms on the unwind. These stops
corroborate code base `0x0D760` and context base `0x1DB70` from the register
caches and the file offsets. A later transition from Find Date also reached
`0x25B5` with the same selected handle in BX as the Change Event transition.
This is an intermediate-register observation. It leaves the settled B
handle and activation words unknown and illustrates why a handle alone
cannot serve as a dialog name.

| Stage | Physical range on the repeat clone | Length | Mapping |
| --- | --- | ---: | --- |
| Code anchor | `0x0F9A4..0x0F9CC` | 41 | `0x0D760 + (file 0x2444..0x246C − 0x200)`, context creation and selection |
| Code anchor | `0x0F9D7..0x0F9EF` | 25 | `0x0D760 + (file 0x2477..0x248F − 0x200)`, empty handling and restoration |
| Data | `0x1EB0C..0x1EB11` | 6 | `0x1DB70 + (0x0F9C..0x0FA1)`, the three adjacent words above |

Both code windows have no MZ relocation entries. The code-only gate at
22,496 ms matched the pinned module, and both anchors matched again at each
of the 13 data checkpoints. Each MCP owner held one authenticated connection.
The host socket table verified closure at the handoffs. Grouped reads
matched the independent native registers, held clock and reset counters.
The two samples of the six-byte `normal`, width-one read matched at every
checkpoint with **0 ms** of guest advancement between samples. The raw
records, byte diffs and image labels are private.

## Approved comparison results

Each A→B interval was 1,236 guest ms. Each B→C interval was 604 guest ms.
For the Start Time run an additional held sample at 26,780 ms, frame
1,720, recorded Description focus before four Shift+Tabs. The frame
comparator stopped before reading Start Time because of a caret blink.
Independent visual inspection confirmed the same selected field and form
values, and the only pixel difference was the 2 × 19 caret. The code and
data reads then used that same held checkpoint, with no repeated input.

| Run | A guest ms / frame | B guest ms / frame | C guest ms / frame | A→B window records | A→B small records | A→B / B→C / A→C changed bytes |
| --- | --- | --- | --- | ---: | ---: | --- |
| Description | 22,496 / 1,463 | 23,732 / 1,537 | 24,336 / 1,573 | +3 | +10 | 5 / 5 / 0 |
| Matched idle | 24,336 / 1,573 | 25,572 / 1,647 | 26,176 / 1,684 | 0 | 0 | 0 / 0 / 0 |
| Start Time | 26,176 / 1,684 | 27,412 / 1,758 | 28,016 / 1,794 | +3 | +10 | 5 / 5 / 0 |
| Find Date | 28,016 / 1,794 | 29,252 / 1,868 | 29,856 / 1,904 | +3 | +4 | 4 / 4 / 0 |

The six bytes agreed across the two matched Change Event B samples and
across the Description→Start Time focus move within one opening. At each
modal B, the upward boundary advanced `0xB4` and the selected handle
changed. Find Date's B differed from Change Event's B in three bytes.
The downward boundary moved by `0xA0` for Change Event and `0x40` for
Find Date. This fits one small marker plus the descriptor's nine or three
control entries. DMCSR `0x5D31` iterates the control count, and `0x69BA`
allocates a small record for each entry through `0x2613`. These results
support interpreting the two words as allocation boundaries. The dialog's
focus and name come from separate evidence. The selected handle adds
context, and its value is subject to allocation and reuse.

The tested detector can use the increase in window records relative to
the selected day-view baseline, then use the small-record increase to
distinguish the two tested dialogs. This measures the live input context
at held checkpoints. Other DMCSR calls can allocate windows temporarily,
and the same counts may occur in other forms. Additional controls would
be needed to generalize across menus, nested dialogs or other applications.

For a code-backed identity cross-check, the parent A boundary was `0x0850`.
If a later authorized sample verifies the same parent and mapping, the
marked frame consumes `0x3C` and the outer dialog record begins at context
offset `0x088C`. The two size words written by `0x2508` and `0x2513` lie
at record `+0x18..+0x1B`, giving the conditional physical range
`0x1E414..0x1E417` on this clone. Change Event's original layout supplies
`0x1194` and `0x0B2C`, while Find Date supplies `0x0AF0` and `0x044C`.
These are layout units. Reading this range would require separate approval.
Add Event shares the Change Event layout and control count. Testing it
would also require an approved title-pointer comparison while the
independent context is active.

All captured states retained one hard and one soft reset, last reset at
613 ms. The final held disk matched the archived E02 disk byte-for-byte.
The repeat clone was left on the selected day view at 29,856 ms.

The offline comparator accepts three already-extracted six-byte files. It
checks lengths, static boundaries, allocation alignment and handle bounds,
then reports the record deltas and restoration. Its synthetic cases cover
growth and restoration, handle-only changes, failed restoration, and malformed
samples. It produces measurements for this candidate layout. The visible
state labels and experiment controls supply the meaning.

```text
python tools/experimental/calendar_window_context.py A.bin B.bin C.bin
```

## Observer operation

The embedded live MCP observer served a status-only modern and classic view
for the original Calendar clone. Status JSON matched the allowed schema,
and both image routes refused unpublished content. Across 290 HTTP samples
over 120.136 host seconds the same authenticated owner measured **0 ms**
of guest advancement and **zero** new native connection attempts. An
independent synthetic demo served three fictional stations with changing
timelines and PNG and GIF frames. Both listeners were IPv4 loopback only.
The Windows browser launch was rejected by the tool policy. The HTTP checks
therefore measure scripted requests. No screen artifact was published.
