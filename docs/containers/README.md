# Observed container structures

Calendar's default profile has a .FIL magic, six candidate 1,024-byte pages, DBCOLS
schema rows, PERSONAL rows and page/offset/ID index triples. The parser validates
that exact profile; it is not a general .FIL reader. See the Calendar specification
for confirmed arithmetic, probable page roles and opaque values.

The [cross-application investigation](../research/cross-application-db.md) now
compares Calendar, native Address Book controls and two shipped Filer samples.
All four share a complete 152-byte self-schema region and the same index-header
and six-byte target arithmetic across 14 tables. Filer native creation/mutation
has not been performed; a common runtime engine remains an implementation hypothesis.
The [campaign structural reader](../research/database-campaign.md) now extracts
the bounded common directory/schema/index/framing layer, preserving raw tokens,
unknown fields and the full source. It reads the local CARMAINT sample but rejects
INVNTORY's schema row with an omitted sixth value. It is not a general engine or
allocator and assigns no undocumented flag/checksum meanings. The default
Calendar profile retains its earlier bounds; an explicit SDK profile adds bounded
additional-page reading.
