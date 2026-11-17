# DeskMate 3.05 Text native documents

DeskMate Text 03.05.00 saved two document streams under the same default
`.DOC` extension. The editor labeled the plain stream **ASCII**, including a
measured CP437 character. Bold and underline switched the status to
**Non-ASCII** and produced a header followed by inline controls and literal
text. The read-only extractor covers the measured profiles, including a
mixed-format, 2,527-byte document. [Executable and run evidence](../evidence/filer-text-native-20261117.json)

## Native corpus

Each row points to the actual bytes written by Text. The experiment archive
retains the stopped disk, independent FAT16 and 7-Zip extractions, exact
socket actions and framebuffer captures. File identities, synthetic contents
and save provenance also appear in the [fixture manifest](../../tests/fixtures/application-generated/manifest.json).

| Specimen | Native operation and content | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| [T00](../../tests/fixtures/application-generated/text/t00.doc) | File → Save as from untitled with an empty buffer | 2 | `5cbce9f3c747dbf42c733cf41b4da6a2c44b5355f5a8e58619721f451bb8221a` |
| [T01](../../tests/fixtures/application-generated/text/t01.doc) | Type A | 3 | `6111af099f17cb1b9b3dc92e4f99e7f36e515bfb7f83f4558dc432f939d7f42e` |
| [T02](../../tests/fixtures/application-generated/text/t02.doc) | Append B to T01 | 4 | `0bb2a2860490eb0ac79536a8e78f8d99c790a5fadf029c4f58a87118392b3b7b` |
| [T03](../../tests/fixtures/application-generated/text/t03.doc) | Append C to T02 | 5 | `0ec12ceb3b74de337088c6ce3595a6105ab0d0336661c1665d7e287f753cdb6b` |
| [T04](../../tests/fixtures/application-generated/text/t04.doc) | Enter, then Q7 | 9 | `96ecde54d57611ea8d0b7f7b59750644f8686256699afaf19c9449d2e23e9344` |
| [T05](../../tests/fixtures/application-generated/text/t05.doc) | Enter twice, then R9 | 15 | `486dc3f76afc37f4eaa1ca2ee92521b42f628b411366af8e4d8cc1f81db89791` |
| [T06](../../tests/fixtures/application-generated/text/t06.doc) | Backspace and type 8 in place of 9 | 15 | `a840cc4f5f7759c92265194871e9a3a674fa20f4a8422f624d7f299b52e3d45e` |
| [T07](../../tests/fixtures/application-generated/text/t07.doc) | Select R8 with Shift+Home and apply Text → Bold | 39 | `b05158822f36a393f87e719a814e3b1719f52f68db74d8d4551ffaa45f9b340f` |
| [T08](../../tests/fixtures/application-generated/text/t08.doc) | Ctrl+C centers R8 and creates a new final line | 51 | `28184d70a6f746f2029e859e9b4b9dce5aad56c343d924ee1f1d130fdde1d598` |
| [T09](../../tests/fixtures/application-generated/text/t09.doc) | T11, Enter, and 48 distinctly numbered 50-character lines, each followed by Enter | 2,527 | `0f2a2d128b28e7a262cbec4961baaff136d185c55a5c421dedeafe5f6abefec4` |
| [T10](../../tests/fixtures/application-generated/text/t10.txt) | File → To ASCII on T08, then Save as T10.TXT | 17 | `7ac80c0581b0f6124cf838117d796dfca4d26c3c300aecde0d7ff142285eb088` |
| [T11](../../tests/fixtures/application-generated/text/t11.doc) | New ABC, Shift+Left selects C, then Text → Underline | 29 | `2bfe5c5b3f90c139c6a3945423d393c2305db0bd96e67a01f89dbce8e99a4683` |
| [T12](../../tests/fixtures/application-generated/text/t12.doc) | New K, Alt+numpad 130, Z, Tab, W | 6 | `4f17ded7d16c6fa88124398f5de6f20e2a2a22e1c14926d31e16af0ab70e14a7` |
| [T13](../../tests/fixtures/application-generated/text/t13.doc) | New single logical line of ten 10-character words separated by spaces | 111 | `6848c83a7508b2b25cecbf8af2a2876be3f702fa0e7ae70fc24eba0ff5e5b0fb` |
| [T14](../../tests/fixtures/application-generated/text/t14.doc) | New X and one typed space | 4 | `8e178c25aa4fd8f0fd2d5087bab4639b94ceb6b573a93b38d932e898f1a62f8f` |
| [T15](../../tests/fixtures/application-generated/text/t15.doc) | Append a second space to T14 | 5 | `4847e683afa1bca5a6cab4b6f78aafad1ff4701a8ecb6c58e526e108ae9d4c33` |
| [T16](../../tests/fixtures/application-generated/text/t16.doc) | Remove the two typed spaces with Backspace | 3 | `c9769b23bcf3481594b10bea4df338f336ec39e48dd91450cd452c3a17fb2213` |

`DESK TEXT` launched an untitled empty editor. File → New also opened an
untitled buffer. A basename entered in Save as acquired `.DOC`. Save as
accepted an explicit `.TXT` for the converted buffer. To ASCII operated on the
current document in memory, followed here by Save as to a separate file. The
empty save returned to an Untitled title, yet the stopped disk contained
T00.DOC. Across the four Text trials the installed-file manifests showed just
the 17 listed additions by content, with no auxiliary file additions.

On a new clone, T08 displayed the centered bold R8 and accepted an explicit
File → Save. The file's bytes before and after matched exactly while its DOS
write time advanced from 21:05:26 to 21:06:02 on the emulated clock. Only T09
and T11 were added on that clone. On the next clone, a read-only T09 reopen and
Ctrl+End showed the final numbered line, with exact bytes preserved on exit.
The first direct filename entry into the T08 Open picker instead selected the
first listed document, the shipped DMVID.DOC. The trial observed its title,
then used the verified list selection for T08. A rapid first attempt to enter
the large corpus produced visibly corrupted input, and its attempted Save As
did not produce a specimen. File → New → No discarded the buffer. The paced
retry used at most six characters per burst and verified all 2,496 numbered-line
bytes independently against the input recipe.

## Measured byte structure

Offsets are zero-based. `0x1A` terminates all 17 captured files.

| Comparison | Observation |
| --- | --- |
| T00–T03 | `20 1A` is the two-byte empty file. A, AB and ABC are literal characters before that suffix, with growth of one byte per character. |
| T03–T06 | Enter becomes `0D 0A`. A blank line adds a second CRLF with no paragraph record. T05 → T06 is exactly `39 → 38` at `0x0C`. |
| T06–T08 | All formatted examples use the same 22-byte prefix beginning `0D 44 4F 43 00`. The first body character is at `0x16`. In T07, `13` and `12` bracket the bold run. T08 inserts `03 21 00 00 04` before R8, then adds a CRLF and `03 00 00 00 04` before EOF. |
| T03 vs. T11 | The same ABC body has `11` immediately before C and `10` immediately after it when C alone is underlined. This isolates character attributes within one line. |
| T08 → T10 | The plain conversion removes the header and formatting controls. T10 includes the space before the final CRLF. |
| T11 → T09 | After the existing ABC body and its stored space, each numbered line occupies exactly 52 bytes including CRLF. The file crosses 1,024 and 2,048 bytes without any inserted record headers or page padding. FAT16 uses two clusters for the file. |
| T12 | The six bytes are `4B 82 5A 20 57 1A`. The editor displayed é for `82`. Tab inserted one space in this position. This file has no space immediately before EOF. |
| T13 | The window wraps after the sixth word. The saved body has all ten words separated by spaces and zero CRLF pairs. |
| T14–T16 | One, two and zero explicitly typed spaces yield two, three and one spaces before EOF respectively. This isolates the extra stored space from user input for these printable ASCII cases. |

The first 22 bytes of the formatted profile are
`0d 44 4f 43 00 01 2b 2d 2d 05 64 2d 2d 05 46 42 3c 00 00 00 00 01`.
The observed five-byte sequences are sufficient for this centering experiment.
The operands' units and bit meanings remain hypotheses. The stable T08 save
establishes byte repeatability for that profile and operation. T05/T06 locate
an edit in the saved bytes. These stopped-disk comparisons leave the native
I/O write granularity and behavior across changed page settings unresolved.

The shared DMDB parser requires a page-aligned database and indexed tables.
The measured Text variants are streams. T07 and the new Form Setup database
have an exact match at offsets `0x0D–0x15`, even though their signature and
body framing differ. Shared page or print settings are a plausible explanation.
The bytes alone do not assign that region's fields. An MZ probe of TEXT.PDM
confirmed a 512-byte executable header and `DM89` at `0x1C`. The exact
`0D 44 4F 43 00` signature did not occur as a contiguous static string in
the pinned module. [Prior Text static comparison](database-components.md)

## Read independently

```powershell
python -m deskmate_formats.text tests/fixtures/application-generated/text/t07.doc
```

`extract_bytes` and `extract_file` render the measured text stream via CP437
with LF line endings, suppressing one space immediately before DOS EOF.
Spaces before a hard line break are preserved. The reader requires the
measured formatted header and recognizes the two isolated attribute pairs and
two exact layout controls. Coverage ends at changed headers and other controls
such as pictures, page features and indentation. An otherwise identical
pair with a single page or indentation setting changed is the shortest
path to extending the reader's layout coverage.
