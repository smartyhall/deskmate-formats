# Tandy Appendix A: common Page Setup header

**Source:** Tandy *DeskMate Development System 03.05.00 Development Guide*, Appendix A introduction (printed A-1, PDF p. 476). **Status: documented; byte interpretations require profile-specific native verification.** See [crosswalk](tandy-format-crosswalk.md).

Tandy describes a 22-byte Page Setup prefix for application data formats. **Exception:** plain ASCII Text documents have no such prefix; formatted Text documents begin with their separate `0D 44 4F 43` identifier and then the 18-byte Page Setup structure. The installed Filer/Calendar/Draw/Worksheet variants should be tested separately rather than generalized from one header.

## Header layout (zero-based file offsets)

| Offset | Size | Meaning from guide |
| ---: | ---: | --- |
| 0 | 1 | Application type identifier |
| 1–3 | 3 | Default filename extension, normally an ASCII three-character extension |
| 4–21 | 18 | PGSETUP byte structure |

**Application identifier values documented by Tandy:**

| Decimal | Hex | Application |
| ---: | ---: | --- |
| 3 | `0x03` | Filer |
| 13 | `0x0D` | Office Text (formatted stream) |
| 14 | `0x0E` | Worksheet |
| 16 | `0x10` | Draw |
| 17 | `0x11` | Calendar |
| 20 | `0x14` | Draw88 |

These values come from the manufacturer appendix. They are not a universal file signature detector, and absence of this header does not imply that a file is invalid.

## PGSETUP layout (18 one-byte members)

The guide's C structure consists of a mode byte, three four-byte margin groups, and five Boolean/option bytes. Mapping the ordered members onto the prefix yields this **document-derived offset interpretation**:

| File offset | Member | Meaning |
| ---: | --- | --- |
| 4 | `mode` | Notebook, landscape or portrait selection |
| 5–8 | `mNotebk` | Notebook margins |
| 9–12 | `mLandscp` | Landscape margins |
| 13–16 | `mPortrait` | Portrait margins |
| 17 | `bDspace` | Double-spacing option |
| 18 | `bPgpause` | Pause between pages |
| 19 | `bScontrol` | Emit control sequences |
| 20 | `bGraphic` | Graphic mode option |
| 21 | `bText` | Text mode option; Calendar also documents use as a last-selected-calendar index |

Each four-byte margin group contains, in order, **left**, **line width**, **total lines per page**, **printed lines per page**. C `char` fields imply byte-sized values; signedness, enum values, and exact print-device units are not specified here. Do not replace opaque bytes with assumed defaults in a writer.

## Validation questions

1. Check the type/extension bytes of multiple independently native-created files in every application.
2. Change one Page Setup option at a time and compare all 18 PGSETUP bytes.
3. Specifically test Calendar `bText` selection behavior against a genuine multi-calendar save, rather than assuming its nominal graphic/text semantics.
4. For Draw and formatted Text, test whether equal Page Setup choices produce equal header fields.
5. Report any nonheader plain Text format and other extension/version exceptions without trying to “repair” them to the generic 22-byte layout.

**Native context:** The [Text native study in PR #110](https://github.com/smartyhall/deskmate-formats/pull/110) independently observed a 22-byte formatted-document prefix and headerless ASCII streams. Do not infer completion of the entire PGSETUP decoder from a matching prefix.
