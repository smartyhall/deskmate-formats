# Observed container structures

Calendar's current profile has a .FIL magic, six candidate 1,024-byte pages, DBCOLS
schema rows, PERSONAL rows and page/offset/ID index triples. The parser validates
that exact profile; it is not a general .FIL reader. See the Calendar specification
for confirmed arithmetic, probable page roles and opaque values.

No second application/container has been characterized. Shared database-engine
code is intentionally not extracted until a practical cross-application use and
compatible evidence exist. Preserve raw tokens/unknown fields rather than assigning
meanings to undocumented engine flags or checksums.
