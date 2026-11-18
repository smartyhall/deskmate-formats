# Tandy Appendix A: DeskMate Worksheet format

**Source:** *DeskMate Development System 03.05.00 Development Guide*, Appendix A Worksheet (printed A-21 onward, PDF pp. 492–493), plus common file header (p. 476). The tables below summarize the manufacturer account. The [native Worksheet campaign](../research/worksheet-native-20261117.md) supplies experimental qualifications. See the [crosswalk](tandy-format-crosswalk.md).

The installed `0E WKS` profile has the documented outer boundaries. Native
controls identify byte 124 as a little-endian pad-size word, show usable
coordinates starting at 1, and establish record sizes of 6 for labels,
14 for numbers/formulas/inputs and 8 for text blocks. Each descriptor is
five little-endian words and its count includes the dummy. A pointer
rebase followed by native Save As established that the stored addresses
can be reconstructed. See the native report for offsets, text-block
padding, and the stale-cache and error controls.

Unlike the database-backed Calendar, Address Book and Filer files, Worksheet is described as a serialized **pad**, five cell lists, cell records and a string pool. It uses GUF high-level file I/O, according to the manual. This should be investigated as its own format, not forced into the shared DMDB page parser.

## Documented outer structure

| Zero-based range | Documented role |
| --- | --- |
| 0–21 | Common 22-byte file and Page Setup header |
| 22–121 | 100 column widths, one byte for each column 0–99; stated width range 4–77 |
| 122 | Extreme used row index, 0–99 |
| 123 | Extreme used column index, 0–99 |
| 124–125 | Reserved/ignored |
| 126–175 | Five `TOPLIST` descriptors, 10 bytes each in the documented 16-bit layout |
| 176 onward | Cell structures, one list after another |
| Following last cell structure | NUL-terminated ASCII strings for cell contents |

The five lists are **labels**, **numbers**, **formulas**, **inputs**, **text blocks**, in that order. The 10-byte TOPLIST layout is inferred from Tandy's listed members and the fixed 50-byte five-list region. It must still be checked on native saved bytes.

## TOPLIST member semantics

For each list, Tandy describes `start` and `end` pointers, `size`, `status`, and `num`. The pointer values are **in-memory addresses from the last application session**, not durable absolute on-disk offsets to trust when parsing. The author says to ignore/resolve them on load rather than blindly dereference their stored numbers. The other fields describe cell size, state, and number of entries. The exact status bits and pointer representation are not fully defined by Appendix A.

The `num` count **includes a trailing dummy cell**. Each list exists even when logically empty: its dummy entry is described as being at **row 100, column 100** (outside normal user grid 0–99). This supplies a strong native sanity check.

## Cell record layouts

Two named record shapes are described:

| Structure | Members and meaning |
| --- | --- |
| `TEXT-CELL` | Row byte, column byte, status integer, string offset/pointer, row count, column count |
| `CELL` | Row byte, column byte, status integer, string offset/pointer, numeric `double` value |

The guide explicitly assigns `CELL` to numeric, input and formula entries. It does not make every list-to-C-structure association completely explicit in this scanned excerpt; determine remaining mapping from `TOPLIST.size` and controlled native specimens.

**Potential 16-bit DOS C sizes:** with two-byte `int` and near-pointer/offset members, a TEXT-CELL may occupy **8 bytes** and a CELL may occupy **14 bytes** (assuming an eight-byte `double`). Those are **architectural hypotheses**, not measured constants; `TOPLIST.size`, compiler packing, pointer representation and actual saved files are the authorities.

## String pool

Tandy describes stored text as ASCII representations of label text, number entries, formulas, input names and multiline text blocks. Each stored string is **NUL-terminated**. The string offset within a cell is measured **from the start of the TOPLIST array (file offset 126)**, not necessarily from the start of the overall file.

The guide says the cell region's end is found by summing each list's entry count multiplied by its cell size; the strings follow immediately. Preserve a distinction between **logical cell count** and the extra dummy entry included in `num`.

The manual contains one example hex dump of a small worksheet; this reference intentionally does not reproduce it. Use the appendix as a comparison source, not as a substitute for native-created fixtures.

## Original validation questions

1. Create empty Worksheet and save/reopen; verify `0E WKS` identifier/extension and stable header.
2. Add exactly one label; compare the label TOPLIST count, dummy cell and NUL string.
3. Add one number, formula, input and text block independently on clean parents.
4. Change only cell row/column, length of a string, and width of a column; isolate each changed location.
5. Test two cells of the same type to identify list packing and string-offset rebasing.
6. Save an unchanged file twice and compare pointer-looking fields and timestamps; if addresses differ between sessions, do not interpret them as stable file links.
7. Implement a small bounds-checked read-only inspector only after confirming the actual `TOPLIST.size`, dummy rules and cell/string boundaries.

**Parsing safety:** do not trust stored in-memory pointers, do not read past verified list/string bounds, and reject invalid counts or offsets instead of attempting repairs.
