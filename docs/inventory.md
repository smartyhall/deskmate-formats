# DeskMate format inventory

| Application/family | Evidence status | Implemented capabilities |
|---|---|---|
| Calendar 3.05 PERSONAL.CLN | E00–E19 and Phase III-A observed subsets | Read/index enumeration, JSON export, bounded append |
| Address Book 3.05 PERSONAL.ADR | [Phase I](research/addressbook-phase1.md) and [Phase II](research/addressbook-phase2.md): no-edit and single-contact field differentials | No reader or writer; measured layout only |
| Filer 3.05 and shipped samples | [Static structure](research/cross-application-db.md), [DMDB call review](research/database-call-review.md), and [CARMAINT native observation](https://github.com/smartyhall/deskmate-formats/issues/54) | No parser/writer; staged F00–F02 schema/record experiments outstanding |
| Text | Not investigated | None |
| Worksheet | Not investigated | None |
| Draw | Not investigated | None |
| Supporting DeskMate files | DMDB components, schema descriptors, code-backed service thunks and selected cross-application structures studied | No universal database engine or loader binding proved |

Names are scope categories, not claims about extensions or encodings. File signatures,
application versions and each application's storage model need independent evidence.
Related `.FIL` metadata, records and index structures have been observed in
Calendar, Address Book and Filer samples, but their complete storage semantics
and allocation policies are not interchangeable by assumption. See the
[dated project status](../PROJECT_STATUS.md).
