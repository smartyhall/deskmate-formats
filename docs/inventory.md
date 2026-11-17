# DeskMate format inventory

The [Tandy Appendix A format crosswalk](reference/tandy-format-crosswalk.md) contains manufacturer-documented common headers and application-specific technical references for Address Book, Calendar, Draw, Filer, Text and Worksheet. These are **documentation-derived leads**, not new native-verified capabilities; the inventory table below continues to distinguish research already integrated into the repository from open PR work.

| Application/family | Evidence status | Implemented capabilities |
|---|---|---|
| Calendar 3.05 PERSONAL.CLN | E00–E19, Phase III-A and SDK-derived ordinary time/date profile | Measured read/index/append, bounded additional-page reading, 29-event/14-day offline sample; no multipage writer |
| Address Book 3.05 PERSONAL.ADR | [Phase I](research/addressbook-phase1.md) and [Phase II](research/addressbook-phase2.md) native field differentials; [codec report](research/addressbook-codec.md) | Ten-page reader and one-contact writer (four exact native whole-file SHA matches); no multicontact insertion |
| Filer 3.05 | [Controlled native creation, edits, deletions and growth](research/filer-native-20261117.md) | Bounded read-only schema, index and DATA inspection |
| Text 3.05 | [Seventeen native documents](research/text-native-20261117.md) | Plain-text extraction from measured plain and default-header formatted streams |
| Worksheet | Not investigated | None |
| Draw | Not investigated | None |
| Supporting DeskMate database structures | DMDB components, common DBCOLS/index framing and code-backed service thunks studied | Bounded read-only [shared parser](../src/deskmate_formats/database.py); no universal allocator or runtime loader binding proved |

Names are scope categories, not claims about extensions or encodings. File signatures,
application versions and each application's storage model need independent evidence.
Related `.FIL` metadata, records and index structures have been observed in
Calendar, Address Book and Filer samples, but their complete storage semantics
and allocation policies are not interchangeable by assumption. See the
[dated project status](../PROJECT_STATUS.md).
