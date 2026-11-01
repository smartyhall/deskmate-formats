# Bounded static examination of database components

2026-11-01. All files were read from the preserved F00 before installation.
Identities and sizes are recorded in
[cross-application-evidence.json](cross-application-evidence.json).
Raw headers, strings, relocation tables, code probes and Ghidra project remain
private under DOSLAB EXPERIMENTS/RESEARCH/cross_application_db.

## What the files contain

| File | Bytes | Direct observation | Functional inference / limit |
|---|---:|---|---|
| DMDB.R89 |1109|Valid MZ header,11 relocation entries,512-byte header, entry at file0200; embedded DMDB at03FC, DMDBRD at0425 and DMDBUPD.RES at042C|Executable component with module-name data; loader/dispatch role plausible, not established merely by name |
| DMDBBLD.RES |11858|Valid MZ,4 relocations, entry2DBC; self-name at2E22|Contains executable material, not just a text resource; “build” behavior not recovered |
| DMDBRD.RES |21955|Valid MZ,21 relocations, entry4FAC; metadata names and repeated descriptors below|Direct database-schema connection; general read/query API and all call sites unresolved |
| DMDBUPD.RES |13740|Valid MZ,4 relocations, entry3516; self-name at357C|Executable material; update/allocator behavior not assigned from filename |
| FILER.PDM |40081|Valid MZ,25 relocations, entry83D0; DM89 header marker; structured header contains dmguf, dmform, dmdb|Plausible module/import relationships; dispatch semantics unverified |
| FORMSET.PDM |60163|Valid MZ,25 relocations, entryD072; same header-name pattern|Plausible relation to Filer and common components; actual schema UI still requires observation |
| DB01–DB09.PCL |2017–12385|Non-MZ resource directory, all offsets/lengths bounded and payloads contiguous to EOF|Embedded text points to PC-Link; no evidence that DB prefix denotes the DeskMate database engine |

All six MZ candidates' encoded file sizes exactly match their actual lengths;
their header size is0200. Calendar and Address Book PDMs were included as
comparison modules: both are also MZ images with DM89 markers. The .RES and .R89
extensions do not identify a standalone data-only resource format.

This determination uses existing lab dumps/strings plus the standard MZ header,
relocation and entry arithmetic, not guessed native execution. No proprietary
binary or substantial disassembly is included in source.

## Metadata data references

DMDBRD contains the exact NUL-separated sequence cname, owner, pos, len, type,
uniq at50C2–50DF. At50E0–5115 are six consecutive9-byte candidate descriptors:

| Descriptor start | Name address | Relative name value | Width | Type literal |
|---|---|---|---:|---|
|50E0|50C2 cname|0042|80|C|
|50E9|50C8 owner|0048|80|C|
|50F2|50CE pos|004E|4|N|
|50FB|50D2 len|0052|4|N|
|5104|50D6 type|0056|1|C|
|510D|50DB uniq|005B|1|N|

Each nine-byte entry has a little-endian32-bit candidate relative name value,
a little-endian16-bit width, a type byte, and two ASCII0 bytes retained as opaque.
Adding file base5080 to each name value resolves all six strings exactly.
That base is the loaded data-segment candidate identified by the MZ analysis
(segment04E8 before Ghidra's1000 relocation base). This is a recoverable
**data-address relationship**, not a guess based only on filenames.
Widths/types match all four files' on-disk DBCOLS self-schema rows exactly.
DBCOLS itself is present at5116.

The opaque trailing00 text is not assigned uniqueness/default semantics.
The first arithmetic probe placed this table two bytes late and failed; correcting
the start to50E0 resolved every pointer/name/width/type consistently.
The corrected result is retained in reader_schema_correspondence.json.
A startup/version/registration interpretation for surrounding executable bytes
does not establish the database API or storage algorithm.

## Module relationships: observation versus call evidence

FILER and FORMSET contain dmdb at0056; ADDRESS.PDM contains it at004C.
These names occur in structured MZ-header extensions before their relocation
tables, alongside other short module-like names. This is stronger than a random
body-string match, but the extension's import/dispatch semantics have not been
fully decoded. CALENDAR.PDM has no lowercase dmdb in its header.

FILER contains DMDB/DMDBRD at95F8/95FD; FORMSET atE6A0/E6A5;
ADDRESS atE676/E67B; CALENDAR at113B4/113B9.
DMDBRD itself embeds DMDBUPD at51B4 and DMDBBLD at51BC.
These are **embedded data relationships**, not established caller→callee edges.

A negative control matters: TEXT.PDM also contains DMDB/DMDBRD names and shares
the strongest exact96-byte-window code matches with DMDBRD that were found in
Calendar, Filer and Address Book. Common runtime/library material is therefore
a competing explanation. These matches do not identify database-specific code.
The probe excludes MZ headers and low-diversity windows; its raw region matches
remain private in module_relations.json.

Ghidra12.1.4 headless successfully imported DMDBRD as an old-style DOS MZ,
x86 little-endian16-bit real mode, completed bounded analysis and saved a new
private project. Existing Ghidra projects were not opened or altered.
The first script located the metadata but recovered no direct references using
the returned segmented aliases. A second bounded reference enumeration checks
physical-address equivalence and the candidate descriptor region. Results and
their limits are recorded in the verification checkpoint. This is not a
complete call graph or proof of cross-application runtime service use.

## PCL resource directories: a useful negative result

All nine start with51, a file-number byte and common22 08 bytes. Under the tested
layout, bytes5–6 hold an LE16 entry count, bytes7–10 an LE32 total length.
Entries start000B and are eight bytes: LE16 ID, LE32 file offset, LE16 length.
No semantic label is assigned to the remaining header byte at0004.

| File | Entries | First payload | Last payload end / file bytes |
|---|---:|---|---:|
|DB01.PCL|16|008B|2017|
|DB02.PCL|40|014B|3008|
|DB03.PCL|36|012B|3559|
|DB04.PCL|33|0113|2532|
|DB05.PCL|28|00EB|2076|
|DB06.PCL|10|005B|8135|
|DB07.PCL|117|03B3|4376|
|DB08.PCL|9|0053|12385|
|DB09.PCL|16|008B|11754|

Every first payload is exactly000B+8×entry_count. All305 entries are in bounds;
successive payloads meet without gaps/overlap and the final one ends exactly at
EOF in each file. Header total lengths also match the actual file sizes.
This is substantial evidence of a resource container, not a1024-byte database.

For precise text anchors: DB02 at02BA contains PC-Link, DB07 at03B5 contains an
exit-related PC-Link label, DB09 at0093 begins a PC-Link registration title.
Full text is retained privately, not reproduced here. These observations point
to PC-Link resources. They do not prove no database use anywhere inside PC-Link,
nor establish meaning for the DB filename prefix or all payload record types.

## Evidence boundary

Directly supported: MZ/executable organization, a structured schema-descriptor
table in DMDBRD matching on-disk DBCOLS, candidate module-name relationships,
and independently consistent PCL resource directories. Plausible: a shared
database service used through DeskMate's module machinery. Unverified: entry
ordinals, import binding, read/update/build division of work, record allocation,
locking behavior, file ownership and shared runtime use by each application.

The next code investigation should resolve one import/dispatch table and one
call path, with real-mode segment aliases accounted for. The next native
investigation should use F00–F02. Neither a broad speculative disassembly nor
a database-engine implementation is justified by these results.
