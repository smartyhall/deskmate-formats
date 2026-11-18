# Tandy Appendix A: format-evidence crosswalk

This index summarizes the technical content of the operator-provided **DeskMate Development System 03.05.00 Development Guide**, Appendix A, *DeskMate 3 File Formats*. It is a **manufacturer-documentation reference**, not a claim that every described feature has been reproduced in the project's DeskMate 3.05 laboratory.

**Source identity:** Operator-supplied `DeskMate-Development-Guide.pdf`, 493 PDF pages, SHA-256 `8081d5cd34305982844ab3598ebfbdf8887e7e369d1174a88a7631cba08439e0`. The source is not redistributed in this repository. Refer to PDF page numbers below (1-based) and printed Appendix labels. Recheck unclear scans against the page image, not OCR alone.

**How to read evidence labels**

- **Documented:** stated in the Tandy guide; not necessarily native-tested in our installed version.
- **Native-confirmed:** independently observed in actual application-saved files, with test/report links.
- **Inferred:** an interpretation or proposed link not directly demonstrated.
- **Discrepancy/unresolved:** a version difference, ambiguous terminology, incompatible observation, or untested boundary. Preserve both claims rather than silently choosing one.

This is an original, concise technical paraphrase with numerical interface facts, not a transcription of the copyrighted guide. Do not publish the source PDF, verbatim sample dumps, substantial code from it, or proprietary application files.

## Guide map

| Topic | Appendix label / PDF page(s) | Our reference | Immediate validation target |
| --- | --- | --- | --- |
| Overview / 22-byte Page Setup header | A-1 / 476 | [Common headers](tandy-common-headers.md) | Match identifiers and profile fields against native files |
| Address Book / Phone List | A-3 / 477 | [Address Book](tandy-addressbook-format.md) | CONFIG/NAMES, 15 fixed fields, user lists |
| Calendar | A-5 / 478–481 | [Calendar](tandy-calendar-format.md) | Special configuration row, alarms, reminders and anniversaries |
| Draw | A-9 / 482 | [Draw](tandy-draw-format.md) | Form header, size buffer, form payload, trailing palette |
| Filer / Form Setup | A-11 / 483–485 | [Filer](tandy-filer-format.md) | Layout columns/types, encoded GRAPHICS, dynamic DATA |
| Text | A-15 / 486–491 | [Text](tandy-text-format.md) | Formatting, headers/footers, length-delimited embedded Draw pictures, fields |
| Worksheet | A-21 / 492–493 | [Worksheet](tandy-worksheet-format.md) | [Native TOPLIST, typed cells, string pool and formula-cache controls](../research/worksheet-native-20261117.md) |

## Cross-application interfaces

The introduction explicitly associates **Address Book, Calendar and Filer** with a Database Resource and **Draw** with the Core Services Form Manager. These are Tandy's architecture descriptions; they do **not** prove any particular runtime selector or common updater. See [database call study](../research/database-call-review.md).

The highest-priority three-way comparison is **native Draw picture → clipboard picture embedded in Text → comparable Form Setup/Filer graphic**. Draw has a documented graphics-form section; embedded Text pictures carry native Draw picture data; Filer says its GRAPHICS table stores encoded binary data in an ASCII-restricted database. Distinguish shared *graphics payload* from different *outer file/container or encoding* layers. See [graphical research campaign](../research/graphics-cross-application-plan-20261117.md).

## Important discrepancies and boundaries

- **Text plain files:** The guide's generic 22-byte header statement has an explicit ASCII Text exception. Native T00–T16 experiments include headerless plain files and 22-byte-header formatted files. See [PR #110](https://github.com/smartyhall/deskmate-formats/pull/110) and [merged Text campaign](../research/text-native-20261117.md).
- **Calendar filename:** The guide spells the illustrative data file `PERSONAL.CAL`; our native corpus uses `PERSONAL.CLN`. Do not alter measured extensions based on the guide.
- **Database table counts:** Tandy describes three Address Book tables and two-or-three Filer user tables. Actual shared databases also contain `DBCOLS`; in the controlled new QRECORD file, the physical table names were DBCOLS/LAYOUTS/DATA. Count the self-schema table explicitly when comparing.
- **Filer GRAPHICS:** The guide uses the word “encrypted” because database fields can contain only ASCII. No encoding algorithm is specified; do not interpret this as proof of cryptographic encryption.
- **Unspecified structures:** Appendix A refers readers to the *DeskMate Technical Reference* for graphics-form definitions and lower-level interfaces. FORM HEADER, primitive records, binary-to-ASCII conversion, allocator policy and complete storage semantics are **not** resolved by Appendix A alone.
- **Version context:** This appendix calls itself a description of the basic DeskMate 3.0 applications even though the kit is labeled 03.05.00; later releases and installed configurations may differ. The Address Book section explicitly identifies field width changes in DeskMate 3.3.
- **Scanned ambiguities:** Source is scanned; some C identifiers, numeric offsets and examples are unreliable as extracted text. Preserve exact byte values only where the printed page is legible; treat inferred arithmetic as a hypothesis.

## Operating procedure for Codex

Read this crosswalk, then the **one or two application references relevant to the current experiment**, then the corresponding native research report. Treat documented layouts as *testable predictions*. Save a native artifact first, compute its hash, test field offsets and lengths, and record agreement or conflict in the native report. Do not make a writer accept an untested profile merely because Tandy documented it.

If a document contains embedded graphics, use **length-delimited** traversal; never search indiscriminately for EOF/control codes inside an opaque picture.
