# DeskMate 3.05 native Worksheet format

The installed Worksheet saves `0E WKS` files with a Page Setup prefix,
100 width bytes, five packed cell lists and a trailing string pool. The
campaign reproduced all five cell categories. The reader recovers typed
cells, text blocks and numeric caches directly from the application-written
bytes. [Evidence receipt](../evidence/worksheet-native-20261117.json)

## Reproduction

The branch started at `a5d3a713e808fd0e73fbc6ae6c09104a90020260`, the
merge of PR #112. The disposable guest was DOS 5 on a Tandy 1000 RSX,
386SX at 25 MHz, 4 MiB RAM and internal VGA. The evidence receipt pins
the disk lineage, machine configuration, NVRAM, ROM and 86Box identities,
and hashes of DESK.EXE, WRKSHEET.PDM and DMGUF.R89.

| Session | Held emulated time (ms) | Frames | Scope |
| --- | ---: | ---: | --- |
| initial | 77,964 | 4,799 | Empty, label, numbers, formula, input and single-cell text |
| edits | 130,283 | 8,054 | Multiline block, disjoint label edits, reopen, formula copy and mixed sheet |
| formats | 163,808 | 10,087 | Width and number formats, insertion, absolute references, far cell, Text clipboard and nested reopen |
| reopen | 74,230 | 4,664 | Pointer rebase, stale reopen, error, input recalculation and row deletion |
| growth | 52,994 | 3,315 | Fresh large block, paced soft-wrap control and large-file reopen |

The total was 499,279 ms of emulated time. All guest input and observations
used the authenticated loopback socket. The formats and reopen clones used
the serial-mouse setting established for the previous graphics campaign.
All sessions returned to DOS before shutdown. Independent FAT16
directory/cluster extraction agreed with 7-Zip for every published file.
Complete action transitions, PNGs, inventories, images and stopped-disk
comparisons remain under
`C:/DeskMateLab/private-evidence/worksheet-native-20261117`. The receipt
names the individual captures and includes the byte differences relative to
the recorded parent, or to W00 as a comparison for independent File New runs.

## Native controls

`DESK WRKSHEET` in the installation directory opens an untitled pad.
`DESK WRKSHEET W06.WKS` opens a named file. File (F2) offered New, Open,
Save, Save As, Merge, Page Setup, Print, Exit and Run. File → Save As from
the initial empty screen created W00, and a basename acquired `.WKS`.

The viewport labels the first row and column 1. Arrows move the current
cell, Shift+arrows extend selection, and Search (F5) → Find Cell accepts
a row and column. Edit (F3) offers Cut, Copy, Paste, Clear and Select All.
Ctrl+Insert copies, Shift+Insert pastes and Delete clears. Pad (F4) offers
column width, row/column insertion and deletion, and Calculate (Ctrl+C).

The status bar distinguishes Label, Text, Number, Input and Formula.
Ordinary text typed into a cell and committed by Enter produces a label.
Typing an integer, fraction or negative number produces a number.
Cells (F6) → Formula or Ctrl+F opens a formula dialog. Cells → Input
opens a field name and value dialog. To create a block, select an extent,
use Start Text (Ctrl+T), enter text, then use End Text (Ctrl+Q).
The block editor uses Enter for a hard break when its selection has room.
Cells → Format offers alignment, number type and decimal precision
controls. Current Column Width was operated with a native serial-mouse
click after a keyboard-only attempt left All selected.

## Native corpus

Each name below identifies one archived file. The 38 public files appear
under [worksheet fixtures](../../tests/fixtures/application-generated/worksheet/)
with size, SHA-256, parent provenance and expected contents in the
[manifest](../../tests/fixtures/application-generated/manifest.json).
Aliases with identical bytes preserve separate native save histories.

| Specimen | Native observation |
| --- | --- |
| W00, W01 | Empty save and subsequent `ALPHA7` at R1C1. |
| W02, W03, W04 | Independent numbers 123, 12.5 and −7. |
| WBASE, W05, W05C | Baseline 2 and 3, add `R1C1+R1C2`, then separately calculate to 5. |
| W06, W06C, WRECALC | Replace 3 with 9, save with stale cache 5, and calculate to 11. A cold reopen reproduced the stale display and the same recalculated bytes. |
| W07 | Uncalculated named input RATE7 with stored value 6.25. |
| W08M, WSOFT | Explicit two-line block and automatic word-wrap control. |
| W09, W10 | Duplicate label at R3C4, then native clipboard copy to R5C2. |
| W11 | Current column 1 width increased from 10 to 16. Only file byte 23 changes from W01. |
| W12, W13 | Independent replacements with `BETA77` of the same length and `ALPHA7LONG` of greater length. |
| W14, W15, WEMPTY | Clear the second label, independently reopen/resave the one-label file, then clear its only label. W14 and W15 equal W01. WEMPTY equals W00. |
| WNUM | Zero, one and 123456789. The last value overflows its display column and remains intact in storage. |
| WINT, WLEFT | Integer choice and separate Left choice on 12.5. The status words become `0040` and `004A`; the latter dialog retained its selected type. Stored double and numeric string remain intact. |
| WFCOPY, WABS, WABSC | Relative formula copy and side-by-side relative/absolute reference controls. |
| WMIX, WMIX2 | All five cell categories together. Changing RATE7 during Calculate raises its dependent formula result from 40.5 to 67.5. |
| WROW, WCOL, WBACK | Independent insertion before row 1 and column 1, then deletion of the inserted row on a reopened copy. |
| WSPARSE | Find Cell to R99C99 and type `FAR99`. Both extent bytes are 99. |
| WCTX, WFIX | No-edit resaves under a nested Text launch and after a private memory-pointer rebase. |
| WERR | Division by zero visibly yields `*ERROR`. The expression and error-state word persist. |
| WGRW | 63-row by seven-column block with GROWTH and CONTROL. Saved file is 5,094 bytes across three 2,048-byte FAT clusters. Both lines remained visible on reopen. |

W08, WLARGE and WWRAP are archived privately because their dummy records
contain unresolved heap residue. Rapid text input lost some characters in
the first growth and wrap probes. WGRW used short bursts on a fresh install
and WSOFT used individual paced keys. Their bytes contain the intended text.

## File layout

All offsets below are zero-based and ends are exclusive. The outer layout
substantially matches the [manufacturer's reference](../reference/tandy-worksheet-format.md).
The interpreted pad size, one-based grid and six-byte label records refine
that reference.

| Offset | Native interpretation |
| --- | --- |
| 0–22 | Page Setup. Identifier and extension bytes are `0E 57 4B 53`. |
| 22–122 | 100 width bytes. Column 1 uses array index 1. W11 changed byte 23 and preserved byte 22. |
| 122–124 | Extreme used row and column. Empty is `00 00`, R1C1 produces `01 01`, and WSPARSE reaches R99C99. A block includes its full selected extent. |
| 124–126 | Little-endian pad size. It equals file size minus 22 in every measured file, including both shipped comparators. |
| 126–176 | Five 10-byte TOPLIST descriptors, in label, number, formula, input, text-block order. |
| 176 onward | Five consecutive cell arrays. Compute each bound from the preceding array and this list's count and record size. |
| After arrays | Packed NUL-terminated strings. W00 ends immediately after the five dummy cells at 232. |

Each TOPLIST is five little-endian 16-bit words. Relative to its descriptor,
the start pointer is at 0, end pointer at 2, cell size at 4, status at 6
and entry count at 8. The end-minus-start difference tracks count times
record size. The address words never locate file bytes in the reader.
On the measured controlled launches the five list statuses were
`000A, 0002, 0002, 0002, 0000`.

In W00 the first start pointer is `71E0` and the five actual array starts
are 176, 182, 196, 210 and 224. Adding cells shifts pointers to following
arrays. W15 (a separate boot) and WCTX (Worksheet launched by Text)
reproduced W01 byte-for-byte. The shipped samples have a different
first start pointer, `6CE0`. To test this independently, only the ten
pointer words in a disposable copy of W15 were reduced by 1,280, retaining
their span differences. The candidate was opened from DOS and displayed
`ALPHA7`. Native Save As to WFIX regenerated the original `71E0` base and
matched W01 exactly. The tool-generated input stays in the private archive.

## Cell records and strings

Each count includes a trailing dummy with row and column bytes `64 64`
in hexadecimal. Cells in a list sort by column, then row. The same
worksheet coordinate does not appear as a real cell in multiple lists
in the measured files.

| Record offset | Field |
| --- | --- |
| 0, 1 | One-byte row and column |
| 2–4 | Little-endian status word |
| 4–6 | Little-endian string offset relative to the start of TOPLIST at file byte 126 |
| 6–14 | IEEE-754 binary64, little-endian, for number, formula and input |
| 6, 7 | Row and column extent minus one, for text blocks |

Labels end at byte 6. Numbers, formulas and inputs use 14-byte records.
Text blocks use eight bytes. The dummy records have these same sizes and
the reader preserves their contents verbatim. Some dummy data contains
residue from earlier cell allocations. For example, the number dummy in
W07 retains the final bytes of the previously stored synthetic 9.0.
The dummy coordinate identifies the terminator independently of that data.

The pool entries are reached by their exact start offsets. The order
varies with edit history. W05 stores the most recently added expression
before the two number strings. Replacing a referenced number in W06
moves that number's string to the front and changes the expression's
offset. WBACK restores the same cell coordinates, formula and value as
W06C with a different pool order. W09 and W10 store a separate copy for
each identical label. W14 compacts the pool back to W01, and clearing the
sole label in W15 returns to a byte-identical W00. The measured profile
has one referenced string per real cell and no unreferenced pool tail.

W08M contains two rows by two columns and
`FIRST\rSECOND` followed by 33 `01` pad bytes, an `02` and the NUL.
WSOFT stores an automatic wrap as LF within its text. WGRW demonstrates
extent-dependent in-string capacity in the 63-row block. The stored
byte sequence is preserved alongside the reader's newline-normalized text.
Worksheet → Text clipboard paste was unavailable for the tested W08M
range. Worksheet block padding and line controls differ from the measured
Text DOC stream's CRLF and DOS EOF framing. The shared-file-I/O claim
does not establish a common document serialization.

## Numbers, formulas and inputs

Native byte comparisons match little-endian binary64 for zero, one,
123, 12.5, −7, 123456789 and calculated results. Plain number strings
carry the default fixed-decimal text, for example `12.50`. A formula
string carries the editable expression verbatim. Inputs store the field
name and put the value in the numeric field. The measured records have
no separate compiled expression or reference index. Worksheet displays
formula and input fields after Calculate, which prompts for named inputs.

| File | R1C2 | R1C3 expression | R1C3 stored double | Status |
| --- | ---: | --- | ---: | --- |
| W05 | 3 | `R1C1+R1C2` | 0 | `0002` |
| W05C | 3 | `R1C1+R1C2` | 5 | `0092` |
| W06 | 9 | `R1C1+R1C2` | 5 | `0092` |
| W06C / WRECALC | 9 | `R1C1+R1C2` | 11 | `0092` |
| WERR | 3 | `R1C1/0` | 0 | `0192` |

The observed `0080` bit accompanies displayed result or error state. It
does not indicate freshness. The error control sets `0100` along with
it. Other bits remain available raw. W06 visibly reopened with the stale
5, and recalculation changes a single binary64 byte at file offset 236.
For the mixed sheet, raising RATE7 from 4.5 to 7.5 during the Calculate
prompt changes the numeric value and its dependent cache, with just three
file bytes changing.

Copying `R1C1+R1C2` down a row produced `R2C1+R2C2`. In WABSC the
relative expression calculates to 10, and the copied absolute
`#R1C1+#R1C2` remains unchanged and calculates to 11. Inserting a row or
column ahead of the original coordinates also rewrites relative references.

## Inspect a worksheet

```powershell
python -m deskmate_formats.worksheet tests/fixtures/application-generated/worksheet/wmix.wks
python -m deskmate_formats.worksheet --list tests/fixtures/application-generated/worksheet/wabsc.wks
```

The JSON reader emits identity, Page Setup bytes, column widths, extents,
TOPLIST descriptors and exclusive cell bounds, original records and
strings, and numeric caches with measured flags. The compact listing keeps
each expression visible beside its stored number. Structural checks reject
truncation, inconsistent pad size, invalid counts or dummies, overlapping
cell coordinates, misaligned pool references and invalid text-block extents.
The same reader checked the shipped LOAN and TVM files privately, recovering
355 and 34 real cells respectively. Their bytes are commercial comparators
and remain in the lab.

High-value follow-up controls include copy or move of ranges containing a
mix of labels and all reference forms, status-word mapping for decimal
and currency formats, non-ASCII entry, and the upper limit of the native
pad allocator. A writer would need native acceptance tests for reconstructed
pool order, dimensions, error caches and dummy initialization.
