# Tandy Appendix A: DeskMate Text format

**Source:** *DeskMate Development System 03.05.00 Development Guide*, Appendix A Text (printed A-15 onward; PDF pp. 486–491), with common header on p. 476. **Status: Tandy-documented.** The [native Text campaign in PR #110](https://github.com/smartyhall/deskmate-formats/pull/110) independently confirms only a measured subset. See [crosswalk](tandy-format-crosswalk.md).

## Two stream profiles

- **Plain/ASCII:** Contains printable/IBM extended characters, CRLF (`0x0D 0x0A`) for explicit line or paragraph breaks, and `0x1A` for DOS EOF. It does not carry a Page Setup header and uses default settings. On ingest, unrecognized bytes below `0x20` in a non-Text-origin plain file may be converted to spaces; this is described editor behavior, not a parser permission to rewrite source bytes.
- **Formatted (“non-ASCII”):** Byte 0–3 is `0D 44 4F 43` (the `CR DOC` identifier); bytes 4–21 hold PGSETUP; stream/control content begins at byte **22 (`0x16`)**. Formatted documents can be triggered by changed page setup, bold or underline, paragraph alignment/indent, headers/footers, fields, merging formatted content, or pasting a Draw picture. The editor's “To ASCII” operation discards non-ASCII features; actual native conversion behavior must be measured for each case.

The format name **“non-ASCII” does not mean the text itself is an opaque binary encoding**: literal text is interspersed with controls. In PR #110, T07–T11 supported CP437 decoding and exact 22-byte formatted prefixes. The observed extra trailing space in some plain documents is a *native observation*, not a rule supplied by this guide.

## Documented controls

| Byte | Interpretation | Scope |
| --- | --- | --- |
| `0x10` | underline off | Character attributes |
| `0x11` | underline on | Character attributes |
| `0x12` | bold off | Character attributes |
| `0x13` | bold on | Character attributes |
| `0x01` | start embedded Draw picture | Picture paragraph |
| `0x02` | end embedded Draw picture | Picture paragraph |
| `0x03` | start paragraph-margin definition | Paragraph layout |
| `0x04` | end paragraph-margin definition | Paragraph layout |
| `0x05` | start dynamic field | Field substitution |
| `0x06` | end dynamic field | Field substitution |
| `0x07` / `0x08` | date-field subtype when inside `0x05…0x06` | Field payload |
| `0x09` | page-number subtype when inside `0x05…0x06` | Field payload |
| `0x0D 0x0A` | explicit paragraph/line end | Text |
| `0x1A` | end of a text section / file | Text outside opaque substructures |

**Important:** Bytes inside picture payloads or margin data may collide with these codes. Decode controls **contextually**; a global byte replacement or naive scan to the first `0x1A` will corrupt valid documents. The guide's original scanning example is illustrative and its OCR is unreliable; prefer length-bounded state machines.

## Embedded Draw picture (documented framing, native verification pending)

A picture is a paragraph preceded by CRLF or another picture end. The manufacturer gives this envelope, where `n` is the clipboard-picture length and `col` is the display column:

```text
01 | n:2 bytes | col:2 bytes | picture data (n bytes) | n:2 bytes | 02
```

The first picture-content byte follows the four metadata bytes. The final two-byte length mirrors the first. **A native experiment must establish byte order and whether the documented length excludes all padding/metadata**; 16-bit little-endian is plausible in the DOS C environment but must not be silently asserted from the diagram. The guide points to rendering picture data via `vid-draw-form` and states that length-aware traversal is necessary when encountering embedded control-like bytes (including EOF).

The picture's storage position is independent of its display column. Changing only the column should be a discriminating test of the metadata bytes. Compare the embedded picture content with native Draw's **graphics-form payload**, not only its complete file, because Draw files include a Page Setup header and palette.

## Paragraph margins

A margin record uses `03` (begin), three **one-byte** values, and `04` (end). The three interior values represent first-line indentation, later-line left indentation, and right indentation. Margin data precedes the first printable character of the paragraph. Native Text T08 already measured a distinct five-byte centering control; investigate whether it is this envelope and which positions vary. The manual does not provide all enum meanings or numeric bounds.

## Dynamic fields

The field envelope is `05 … 06`. Tandy describes three families:

| Inner content | Meaning |
| --- | --- |
| `*` + Address Book field name + `*` | Address Book mail-merge substitution |
| `07` or `08`, then a date-format rendering string | Current date, in one of two printable formats |
| `09` followed by the page-number placeholder | Current page number |

A field is edited as an indivisible unit in Text. Address Book merge values are substituted **when printing**, not necessarily written into the saved document. The appendix says fifteen Address Book fields are available, plus two date formats and one page-number field. The precise field spellings, printed formats and alternate variants should be confirmed natively.

## Headers and footers

Tandy supplies separate sample structures for document headers/footers. The formatted PGSETUP is followed by optional **section markers**:

- `H` or `h`: header, with the lowercase variant meaning an exception for the first page.
- `F` or `f`: footer, with the lowercase variant meaning an exception for the first page.
- Marker-associated `0D 0D` separates the section's control prefix from its text; `1A` ends that text section. Another pair of `0D 0D` precedes main document content.
- The main body terminates with its own `1A`.

Tandy's guide includes examples for no section, header-only, footer-only, and both. This summary intentionally avoids copying the raw sample dumps. **Native verification is outstanding**, especially when picture payloads contain internal `1A`; the source states such bytes must be skipped. Do not implement a generic first-/second-EOF splitter without recognizing nested constructs.

## Reader development and minimum regression corpus

The existing `deskmate_formats.text` extractor in PR #110 intentionally accepts only measured plain/default-header formats, attributes and two measured layout controls. Keep that fail-closed behavior until additional native evidence arrives.

Suggested tests, each preserving exact application-produced before/after files:

1. Same text with only changed PGSETUP.
2. One indent and one centering change, with paragraph boundaries.
3. Header and footer variants with different first-page choices.
4. One each of page number, date and Address Book field.
5. One native Draw picture pasted into Text, then a second picture at a changed display column.
6. A picture with embedded `0x1A`/`0x02` or analogous opaque bytes, testing length-bounded parser behavior.
7. To ASCII conversion of picture/field/header versions; check what is discarded, replaced, or preserved.

**Success criterion:** safely identify and preserve unparsed spans while extracting textual content; do not claim complete rendering, format coverage, or lossless rewriting from a text-only extractor.
