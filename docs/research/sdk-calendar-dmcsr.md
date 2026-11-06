# Calendar and DMCSR through the DeskMate SDK

The public dialog ABI explains Calendar's descriptor, frame and component
table. The tested runtimes also use the byte named `help_level` as focus
bookkeeping, and their private allocator disagrees with the manuals' window
size examples. An observer can use SDK names for the public objects and
separately qualify private state by build, allocation and capture.
[Source and binary identities](sdk-source-identities.md)

## Evidence and method

**D** means documented in the SDK, **S** means verified statically against
a hashed binary, **R** means measured in prior 86Box experiments, and **H**
means a hypothesis. High confidence applies to the particular layout or
path supported by the cited evidence. A medium-confidence correspondence
still needs an independent check of the object, scope or interpretation.
All code positions are absolute hexadecimal file offsets. `DS:` and
`ES:` denote offsets in the named guest segment. No new runtime observation
was made. See the [focus](calendar-editor-observatory.md),
[activation](calendar-dialog-activation.md) and
[geometry](calendar-dialog-identity.md) reports for the controls and pins.

The Development Guide, programming environment (PDF p. 173), specifies
byte-packed C structures. Sum the explicit byte, word and nested record
widths in the SDK assembler definitions and compare with C member order.
Use little-endian 16-bit words, two-byte near data offsets relative to the
owning data segment, and four-byte far callback pointers (offset then
segment). An odd word offset is expected. The libraries provide small- and
medium-model bindings, with the medium model changing code distance.
Host compiler alignment and host pointer sizes would give incorrect layouts.

For reproducibility, read OMF library member records (`THEADR`, `PUBDEF`,
`LEDATA`, `MODEND`) using 16-byte library pages, then disassemble the
code data and retain the distinction between prelink operands and fixups.
For MZ modules, read the header and relocation directory, resolve direct
near calls by adding the signed displacement to the next IP and translate
table entries using the `0x200` header. Use GNU Binutils
`2.47.20260726` with `objdump -D -b binary -m i8086 -M intel
--start-address=<file-offset> --stop-address=<exclusive-end> <module>`.
Capstone 5.0.9 in x86 16-bit mode independently located and decoded the
bounded paths. The private probe scripts and listings accompany the
identity report in the lab archive.

## Public objects and Calendar's descriptors

The packed SDK `DIALOG_BOX` is `0x15` bytes. Compare
`CSRCMPS.H/.INC` (Dialog Box and Component Manager) and Technical Reference
8-3 through 8-6 (PDF pp. 294–297). The file-backed Calendar DGROUP data
starts at `0xEA70`. For these initialized objects add the DS-relative
offset to that file base. The live data base is separately measured.

| Offset / bytes | SDK role | 3.05 Calendar or DMCSR correspondence | Evidence and confidence |
| --- | --- | --- | --- |
| `+00 / 1` | `bStatRedraw` | `0x5C9C` checks for 1 before drawing static items. | D+S high |
| `+01 / 2` | `return_value`, component result | `0x5E53` stores a word. The command returned in AX comes from a distinct path at `0x5CDC` and `0x5CE7`. | D+S high |
| `+03 / 1` | `focus_index`, zero-based index reused on the next run | `0x5E7C..0x5E8E` indexes `pCmps`, and `0x6004` writes a navigation result. The archived editor samples read 5 for Description and 1 for Start Time. | D+S+R high for both observed controls |
| `+04 / 1` | `help_level` in the public declaration | Low seven bits are reused for the last focus index or a first-run sentinel. Bit 7 carries the application-event return request. See below. | D+S+R high for the focus copy, D+S high for the event flag |
| `+05 / 2` | `pFrame` | Editor `DS:22C6` points to `DS:211C`. Find Date `DS:1AA0` points to `DS:1A2C`. `0x5B18` and `0x5C8B` follow the pointer. | D+S high |
| `+07 / 1`, `+08 / 2` | Static string count and base | Editor has nine entries. `0x5B89..0x5BB5` iterates packed 8-byte records. | D+S high |
| `+0A / 1`, `+0B / 2` | Static box count and base | `0x5BB8..0x5BC7` uses a 10-byte stride. The editor's count is zero. | D+S high |
| `+0D / 1`, `+0E / 2` | Static icon count and base | `0x5BCA..0x5BE7` uses a 10-byte stride. The editor's count is zero. | D+S high |
| `+10 / 1` | `nCmps` | Nine for Add/Change, three for Find Date. The run handler iterates it at `0x5D39`. | D+S high. Prior R corroborates allocations |
| `+11 / 2` | `pRFlags`, one redraw byte per component | Editor points to `DS:22AA`. `0x5CAB` loads it and `0x5BFD..0x5C19` checks and clears individual redraw bytes on selective redraw. | D+S high |
| `+13 / 2` | `pCmps`, array of near component pointers | Editor table at `DS:22B4`, Find Date table at `DS:1A9A`. Run advances by two bytes per pointer. | D+S high |

`MAPRECT` is four packed signed words at `+0/+2/+4/+6` for world
origin X/Y and extents X/Y. `FRAME` embeds it at `+0` and has a near
title-string offset at `+8`, for a total of ten bytes. DMCSR follows that
title pointer at `0x63E6` and scans for NUL at `0x63F4..0x63FA`. Calendar
writes the pointer at `DS:2124`, precisely editor frame `+8`, with
`0x0536` for Add and `0x0540` for Change before their shared editor
call. Find Date uses its own frame and title. The Change title pointer
survived Cancel in prior RAM. The Add assignment is statically verified
and the Add title was seen on screen. A subsequent
[live comparison](calendar-live-dialog-identity.md) measured both held
editor pointers and their retention after Cancel.
The frame sizes `1194/0B2C` and `0AF0/044C` match the prior allocated
outer-window measurements for Change and Find Date. Those are world-unit
extents. Screen pixels depend on the window and video mapping.

A packed `CMP_HEADER` is 15 bytes. Its type word is at `+0`, flags at
`+2`, `MAPRECT` at `+3`, accelerator at `+0B`, and command code at
`+0D`. In the editor table, Date, Start Time, End Time and Description
have type `F805` (edit fields), the AM/PM controls have `F801` (radio
groups), Alarm has `F804` (checkbox), and OK/Cancel have `F800` (push
buttons). For example, the file-backed OK record at `0x10B96` contains
`000D` in both command fields. DMCSR compares a pushbutton's accelerator at
`0x5D77` and loads a command at `0x5E9C`. `CMP_ROUTINES` separately
describes five far entries (20 bytes) for open/draw/run/close/help. The
routine table concept explains distinct stages. The internal registration
table, every component-specific tail and every focus index's live behavior
remain separate verification tasks.

### The byte named `help_level`

Technical Reference 8-4 (PDF p. 295) specifies a null help level as the
valid value. The same chapter's constants (PDF p. 297) and both SDK
headers also document OR-ing the application-event request into that byte.
The initialized 3.05 editor and Find Date bytes are already `04` and
`03`, respectively. The observed nonzero settled values therefore do
not identify help topics. The verified implementation sequence is:

1. Draw ORs `0x7F` into `+4` at `0x5B1F`.
2. Run saves bit 7 and clears it from `+4` at `0x5CB9..0x5CC2`.
3. `0x5E5A..0x5E77` compares `+3` to the low part of `+4`, copies the
   index when different, and uses the former `0x7F` sentinel to skip
   setting the selected component's new-session flag on that path.
4. With an application message (event type 6), `0x5F21..0x5F3B` checks the
   saved bit and can return command `0xFA01`. Run restores the bit at
   `0x5CCA..0x5CCD`.

The corresponding draw/split/copy offsets are
`5C88/5E22/5FC3` in the SDK runtime and `5BE9/5D83/5F24` in retail 3.03.
This contradicts a help-only or always-zero runtime interpretation across
all three checked images. The high bit agrees with the SDK flag. The
comparison does not identify the full intelligent-help subsystem or prove
how every caller initializes the byte. A settled copy is a consistency
check with correlated provenance. It cannot independently prove focus or
activation. Keep the existing replay's exact settled-value gate until a
broader sampling contract is verified.

## Service names, events and window ownership

The library symbol-to-selector mapping resolves the unnamed app calls.
`DM.LIB` and `DMMED.LIB` expose the same relevant low ordinals, with
`0x10xx` selector words. Retail 3.03 Calendar uses `10E3/10E4` at
file `D732/D738`. Retail 3.05 uses `20E3/20E4` at `D647/D64D`.
The DMCSR low-ordinal table entries for `E3/E4` are at
`12986/12988` (SDK runtime), `1291E/12920` (retail 3.03) and
`12AF7/12AF9` (retail 3.05), leading to the verified draw/run bodies
after adding the MZ header. The first two builds have distinct code
positions even where the instructions agree.

| Public services | Low ordinals | Independent anchors |
| --- | --- | --- |
| `dlg_draw`, `dlg_run`, `dlg_draw_frame` | `E3/E4/28` | DM.LIB LEDATA records `12920/129EF/9834`, plus Calendar `D647/D64D` for draw/run |
| `event_read`, `event_purge` | `13/16` | DM.LIB LEDATA `88B0/8B21`. Calendar `D4F7/D509`. The post-Escape cleanup is the public purge operation |
| `cmp_open/draw/run/close` | `1B/1C/1D/1E` | DM.LIB LEDATA `8F2E/8FFE/90CD/919F` |
| `win_group_init/end`, `win_open/activate/get_active/close` | `2B/2C`, `2D/2E/2F/30` | DM.LIB LEDATA `99D4/9AA3/9B6E/9C42/9D14/9DDF`. Calendar `D52D..D544` for the last four |

For Calendar's two near wrappers the caller pushes one two-byte descriptor
offset and cleans it off the stack. The dispatch thunk makes BP point at the
argument and transfers through the named far DMCSR slot. DMCSR loads the
word into SI at `0x5B05` or `0x5C24`. The header declares a void draw
and integer run result. The packed word at descriptor `+1` carries the
component outcome while run's returned command is separately interpreted.
`DMDECL.H` and the library symbols establish the public signatures.
The high selector bits and complete dispatcher ABI remain version-specific.
`DESK.MAP` and `RUNTIME.MAP` label executive builds (for example, distinct
`RES_GETBIND` offsets `2484` and `24B2`). Neither map supplies DMCSR
private structure symbols or verified retail 3.05 addresses.

Technical Reference Dialog Box Manager (PDF pp. 298–301) describes drawing,
then calling run to obtain updates, with separate static/component redraw
state and a returned command. The Development Guide's dialog example
(PDF p. 209) initializes the focus index separately. The two phases explain
why a drawn form and an input context have different lifetimes. The 3.05
draw path pops its temporary context. Run creates a group, draws requested
items, opens components, selects a child for input and unwinds before
returning. Calendar handles Escape after the return and bypasses packing
and database mutation. A selected child handle, a retained descriptor, or
a queued command can each outlive or lag a particular visual transition.

`CSRBASE.H/.INC` and the Technical Reference Event Manager (PDF
pp. 315–316 and following) describe a seven-byte `EVENT` with message byte
`+0`, parameter word `+1`, and world X/Y at `+3/+5`. The packed size
agrees with the two seven-byte copies at `0x3025/0x303A`. The dialog input
path reads a stack event at `BP+6` and treats `BP+7` as its parameter.
Character, mouse, command, outside and application events are different
cases. Hot spots belong to a window and can turn keyboard or pointer input
into a command. The manuals describe at most two stored events. The
tested code has two seven-byte copies in task context, with flags at
`ES:0FC2/0FCA` and payload starts `0FC3/0FCB` on the path through
`0x2C34` and `0x2D9E`. This is static correspondence. A complete queue
ordering model and live interpretation are open. Event history alone
cannot recover current modal identity.

### Window Manager compatibility

Technical Reference 26-1 (PDF p. 904) describes a shared 2 KiB pool and a
window as a saved video context. The public input to `win_open` is
`MAPRECT *` per `DMDECL.H` and the prose on PDF p. 913. The printed
prototype on that page uses `WINDOW *`; the structure page (PDF p. 906)
shows `MAPRECT` and provides no allocator-record definition. The 03.05
replacement index (PDF pp. 1–2) lists revisions for Component Manager,
Dialog Box Manager 8-1/2 and 8-7/8, Event Manager 10-11 through 10-14, and
Window Manager 26-1/2. The scan's 26-1 and Event Manager general notes
still combine `0x40/0x12` byte prose with a 52/16 decimal example and
68-byte group overhead. Treat those numbers as conflicting documentation.

| Private field or relationship | Evidence and confidence |
| --- | --- |
| `ES:0F9C` upward boundary and `ES:0F9E` downward boundary | D documents a shared pool. S initializes boundaries to `079C/0F9C` at `27EF/27F6`, exactly 2,048 bytes apart. R measured reversible deltas and a matched idle. High for the pinned task context. |
| `ES:0FA0` selected window handle | D identifies the active-window concept. S saves/restores the handle and uses `FFFF` on the empty path. R observed a selection change. High for selection, insufficient for parent identity. |
| Window stride `0x3C`, small record stride `0x10` | S at `28A2` and `2A2E`. The group allocator requires `0x4C` bytes, copies a `0x3C` marker, and reserves `0x10` on the small side. The SDK and retail 3.03 equivalents at `2B2B` and `2A8C` use the same sizes. R confirms the strides through growth/restoration. High. The 16-byte small record matches the decimal hot-spot example. Neither printed window size matches. |
| Small record ownership | S at `261F..262F` stores the selected window at record `+2` and copies 12 input bytes from `+4`; `2631..` transforms rectangle-related words. Medium for the full hot-spot record, high for owner and stride. A small marker consumes the same space. |
| Outer window extents at record `+18/+1A` | S at `2505..2517` copies the public frame's extents here and again at `+1C/+1E`. R confirms the first pair for two forms. High for the first pair in the verified 3.05 allocation. Other private window fields remain open. |
| Task context lookup | `CSRBASE.H/.INC` reserves `0000:0384/0386` for shared and task segment words. S at `0865..0876` writes DS and ES to those locations in 3.05. High as a candidate lookup contract. The recorded runtime context was mapped from registers. No held capture verified the pointer words or task switching. |

At the settled repeat, the outer record is one stride above the day-view
top (`0850 + 003C = 088C`) and precedes the child at `08C8`. The
settled top is `0904`. The prior 1,236 ms open and 604 ms unwind controls
showed `+3/+10` records for Change and `+3/+4` for Find Date, with
identical A and C context and a matched idle. These are signatures of the
tested paths and baselines. A menu, nested dialog, different component
mix or a sample between run calls can yield different boundaries. Counts
can also collide. Replaying the three archived triplets at C's archived
wall timestamp with a 60,000 ms age limit returned Change Event-style
and Find Date-style with geometry corroborated, and no tested modal
context for idle. No address was re-read from a guest.

## Address Book and Filer portability

The following is a bounded 3.05 static check on the exact modules in the
[identity table](sdk-source-identities.md). For each app, follow the
named `DMCSR` bind (`INT E0`, AX `0206`), then the two selector
wrappers and one caller pair. Locate the initialized data base by subtracting
the bind name's DS operand from the corresponding file-backed string
position. Verify that the descriptor, title, counts and pointer targets
resolve coherently in that same file-backed region. The base is a file
mapping for these initialized objects.

| App | Dispatch and calls | One verified descriptor |
| --- | --- | --- |
| Address Book | Bind `9582..958B`, slot `DS:2814`, far call `95D0`, wrappers `971F/9725`. Callers `4F4B/4F69` push `1948`. | File data base `BDD0`, descriptor `D718`, frame `D6A4`. Add List Name has extents 3500×1540, three pointers, and edit/pushbutton/pushbutton types. At `4F42` the caller zeroes `DS:194B` (`+3`), whose file initializer is `14h`, outside the table. |
| Filer | Bind `69A5..69AE`, slot `DS:0E7A`, far call `69F3`, wrappers `6B18/6B1E`. Callers `40C1/40CE` push `0CD2`. | File data base `8770`, descriptor `9442`, frame `942E`. Print Form has extents 3000×1430 and radio-group/pushbutton/pushbutton types. The run loop checks commands `F533/F534`. |

This confirms that the app-side decoder shape and service names transfer to
one example in each application. The Address Book initializer demonstrates
why even a valid static descriptor needs an active context and runtime
field checks. No live binding, geometry, count signature, focus, disk
mutation or application-wide mapping was inferred. Retail 3.03 app hashes
differ and these app addresses remain scoped to 3.05.
