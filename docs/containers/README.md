# Observed container structures

Calendar's current profile has a .FIL magic, six candidate 1,024-byte pages, DBCOLS
schema rows, PERSONAL rows and page/offset/ID index triples. The parser validates
that exact profile; it is not a general .FIL reader. See the Calendar specification
for confirmed arithmetic, probable page roles and opaque values.

The [cross-application investigation](../research/cross-application-db.md) now
compares Calendar, native Address Book controls and two shipped Filer samples.
All four share a complete 152-byte self-schema region and the same index-header
and six-byte target arithmetic across 14 tables. Filer native creation/mutation
has not been performed; a common runtime engine remains an implementation hypothesis.
No generic parser, writer or engine API has been extracted. Preserve raw tokens
and unknown fields rather than assigning undocumented flag/checksum meanings.
