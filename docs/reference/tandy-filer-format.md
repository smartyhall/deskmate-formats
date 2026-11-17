# Tandy Appendix A: Filer / Form Setup file-format reference

**Source:** *DeskMate Development System 03.05.00 Development Guide*, Appendix A Filer/Form Setup (printed A-11 onward; PDF pp. 483–485) and shared header (p. 476). **Status: manufacturer-documented, with selected native Filer corroboration in [PR #110](https://github.com/smartyhall/deskmate-formats/pull/110).** See [crosswalk](tandy-format-crosswalk.md).

## Table families and the counting caveat

Tandy describes **two or three application tables**, depending on graphics:

- `LAYOUTS`: record/report layout descriptions; static schema.
- `DATA`: user-defined data-field schema, up to 22 fields.
- `GRAPHICS`: optional binary picture information encoded for an ASCII-constrained database; static schema.

The native 3.05 database files additionally contain the common self-schema table **`DBCOLS`**. Therefore the documented “two or three” appears to refer to application-owned tables **excluding** `DBCOLS`. Do not report it as an actual physical table-count mismatch without clarifying that distinction. Native PR #110 includes a QRECORD file with DBCOLS/LAYOUTS/DATA and no GRAPHICS; shipped CARMAINT and INVNTORY also have GRAPHICS.

Appendix A says the layout and graphics definitions are fixed, but the DATA columns and sort are user-defined. `DATAINDEX` is the manufacturer's name for the DATA index. The guide says Filer can use a Database Manager `GET COLUMN NAMES` call to retrieve the dynamic schema; this does not establish an exact selector or API signature in our installed modules.

## LAYOUTS: documented 13-column semantics

Tandy says records describe both data-entry forms and report layouts, sorted by **START-ROW / START-COL**. The thirteen logical columns are:

| Column | Documented meaning |
| --- | --- |
| `ITEM#` | Item creation-order identifier, range 0–999 |
| `FIELD ID` | Field creation-order identifier, range 0–999; also references a source field for summaries or a report-section marker |
| `TYPE` | Item kind, numerical codes below |
| `FORMAT1` | Type-dependent presentation field: text attributes, field label/outline choices, or report-section leading blank lines |
| `FORMAT2` | Type-dependent field/summary subtype or report-section/trailing-blank-lines metadata |
| `FMT-CHARS` | Field or summary edit format string; literal content for static text |
| `DESCRIP` | User-supplied field or summary description |
| `START-COL` | Horizontal start position, documented 0–131, except report markers |
| `START-ROW` | Vertical start, documented 0–22; for report items, relative to the associated section; marker rows describe marker placement |
| `NUM-COLS` | Width in columns, documented 1–131 |
| `NUM-ROWS` | Height in rows, documented 1–22; for report markers, number of lines in section |
| `COL-OFFSET` | Marked unused by Tandy |
| `ROW-OFFSET` | For fields/report fields, decimal places to the right of the decimal point; otherwise unused |

**Important:** These are the logical field labels and semantics, *not* asserted byte offsets in the packed database rows. Physical row decoding depends on the DMDB schema, the DATA/LAYOUTS column declarations and the actual application-generated specimen. The guide's scanned field names include punctuation/spacing variations. Check native `DBCOLS` field spellings before using exact matches in code.

The guide describes report marker IDs/sections as **header 0, body 1, summary 2, footer 3**.

### Item type codes (`TYPE`)

| Code | Kind |
| ---: | --- |
| 101 | Static text |
| 102 | Data-entry field |
| 103 | Reserved/not used |
| 104 | Summary field |
| 105 | Date template |
| 106 | Page-number template |
| 107 | Report marker |
| 108 | Report static text |
| 109 | Report field |

### Context-sensitive formatting

`FORMAT1` supplies a text attribute for static text/report static text; label position and outline style for field/summary/report-field items; or leading blank lines for a report marker. `FORMAT2` supplies a field/summary subtype, report body/section identifier, or trailing blank lines, as appropriate. The guide names three text-attribute choices: normal, bold and underline, without giving their serialized numeric values here.

**Label and outline choices:**

| Code | Placement |
| ---: | --- |
| 100 | Label left of field, no outline |
| 101 | Label centered above field, no outline |
| 102 | No label, no outline |
| 103 | Label left, outlined field |
| 104 | Label centered above, outlined field |
| 105 | No label, outlined field |

**Field subtypes:** 201 single-line left aligned; 202 single-line right aligned; 203 numeric; 204 multiline; 205 internal use; 206 fixed-decimal numeric.

**Summary subtypes:** 401 sum; 402 average; 403 count.

These code sets are **documented values**, but their placement in actual DATA or LAYOUTS column bytes has not been uniformly verified. Create one native form variant per code or property before implementing a general writer.

## DATA and sorting

The guide describes a maximum of 22 user-defined DATA columns, each linked to a field item in LAYOUTS. Sort order is user-defined. In PR #110, native CARMAINT insertion showed index order independent of insertion order; deletion/length-changing edits sometimes compacted and reassigned record identifiers. That observation applies to the measured profile and does not establish a universal Filer maintenance policy. See the native Filer report on PR #110.

A controlled *new* form with one field, then two fields (including different field types), provides a better schema baseline than extrapolation from the shipped car/inventory examples.

## GRAPHICS: essential unresolved encoding

The guide says GRAPHICS stores **binary graphics data encoded in an “encrypted” format** because the database permits only ASCII data. It gives no transformation algorithm, graphics primitive grammar, or coordinate representation. **“Encrypted” is the manufacturer's word; this is not evidence of a cryptographic cipher.** The scanned section labels possible fields `RECORD` and `BITS` but gives no recoverable sizes or full semantics; treat their meaning and schema as unresolved until verified against native DBCOLS.

For graphics research:

1. Create an empty Form Setup database and confirm whether GRAPHICS is absent.
2. Add exactly one graphical element; track GRAPHICS table introduction, record bytes, index changes and LAYOUTS changes.
3. Move/resize/recolor the same graphic on independent clones; use controlled differentials.
4. Inspect allowed byte alphabet, per-record framing, encoded-length relationships, and candidate reversible transforms. Never assume raw binary Form Manager bytes occur verbatim inside a .FIL row.
5. Produce an equivalent graphic using Draw and paste it into Text; compare **normalized inner graphic payloads** when the Filer encoding becomes understood.
6. Repeat with disposable CARMAINT/INVNTORY copies. Their GRAPHICS row counts do not prove a one-to-one relationship to visual objects.

**Native context:** PR #110's CARMAINT sequence preserved unchanged metadata/graphics table pages through DATA mutations, but that is not direct evidence about their graphics payload encoding. The native QRECORD file lacks GRAPHICS, confirming optionality.
