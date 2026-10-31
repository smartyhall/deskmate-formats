# E16: deletion on the first allocated data page — 2026-10-31

## Result

Deleting only BOUND12 through Calendar's normal interface **did not truncate or
erase page 6**. The file remains 7,168 bytes. The active index entry disappears,
but the retired record's leading byte changes from 80 to 44 (ASCII D), with every
remaining byte on page 6 unchanged. BOUND12 remains present as unindexed raw text.
The result does **not** restore the six-page E15 preflight database.

There are exactly 11 changed bytes relative to E15 post-insertion, all listed
below. The complete original data page 4 and all surviving row IDs/locations/raw
bytes are unchanged. The four allocation-associated header bytes retain their
E15 values. The live count decreases, an opaque metadata token increases, and
the next-ID candidate does not decrease. No general reclamation algorithm or
production multi-page support was implemented. No further GUI experiment was
attempted after this unexpected retained-row result.

## Git and verified baseline

Local worktree was clean on experiment/e15-page-boundary at d2b8268. Fetched
origin, switched to main and fast-forwarded only to the owner-specified merge
27c1f9097ae226979f7d83fec543b4239894e869. Its ancestry was verified; E15 branch
history was retained. E16 starts on experiment/e16-page-reclamation from updated
main. PR #1 and its four passing CI jobs are owner-reported completed work, not
recreated here. Dependabot/workflow configuration is untouched.

The complete E15 477-entry artifact inventory and SHA-256 manifest verified,
as did all three 126-file installed snapshots. The original E15 artifact manifest
hash is 855939c401567a1e59ddd730bce14f65b5f83ae7f76347780a545209aba9e845.
The source database is exactly 7,168 bytes, SHA-256
42517ab1f90f9e7b6c5cf184219bc301254db33adf3f875a36347237743f1380.
The page-6 BOUND12 row and index entry at 1482 were checked before use. A complete
disposable copy was verified against the E15 post-insertion manifest; the previous
RUN was retained. Original E15 evidence was never edited.

## Application procedure and visual evidence

The existing SDL1/software-rendering emulator was visibly at a clean DOS prompt
before copying. The established foreground-checked Windows keyboard/native-paste
and independent full-desktop screenshot workflow was used. No native Computer Use
diagnostics, installation or emulator changes occurred.

Calendar opened the seven-page copy. Find Date showed November 1, 2026 with
BOUND12 at 11:00 AM–12:00 PM alongside FILL009, FILL010, MID2026 and FILL011.
Only BOUND12 was selected. Event → Remove displayed **This event only** selected;
one OK confirmed deletion. The day schedule then showed the same four surviving
events without BOUND12. All other schedules were inspected: October 23 had
EARLY26/FILL001–004, October 24 had FILL005–008/LATEOCT, and November 1, 2027 had
LPHa124/BETA456, all at their established times. Thus all 16 survivors were
visually present. Escape returned cleanly to DOS before collection.

Twenty numbered screenshots (00–19), the action record, helper sources, complete
before/after installed trees and their SHA-256 manifests are retained privately.
These observations describe only the single selected deletion.

## Exhaustive E15 post-insertion → E16 comparison

Both trees contain 126 files, with no added/removed files. Only PERSONAL.CLN
changed; the other 125 file contents are identical. Both databases are 7,168 bytes.

| Absolute byte | Before | After | Observed context |
|---|---|---|---|
| 0439 | 38 | 37 | ASCII live count 00018 → 00017 |
| 043D | 30 | 31 | Opaque token 000 → 001 at 043B..043D |
| 1482 | 06 | 04 | First shifted index entry: page |
| 1484 | 00 | 27 | First shifted index entry: offset |
| 1486 | 21 | 11 | First shifted index entry: ID |
| 148A | 27 | 3F | Second shifted index entry: offset |
| 148C | 11 | 12 | Second shifted index entry: ID |
| 148E | 04 | 00 | Cleared trailing index slot: page |
| 1490 | 3F | 00 | Cleared trailing index slot: offset |
| 1492 | 12 | 00 | Cleared trailing index slot: ID |
| 1800 | 80 | 44 | Retired row's leading byte |

The count 00017 equals 16 user appointments plus the internal row. The candidate
next-ID at 043F..0443 remains **00034 decimal**, while max live ID is 0x20 (32).
The prior max-live-ID+1 relation is therefore not universal. The token at
043B..043D is descriptor token index 5 (zero-based); its 000→001 transition is
deletion-associated evidence, **not proof that it counts deleted rows/free pages**.
No other metadata-page byte changes. The production parser also requires that
opaque token to be 000; no support is inferred for 001.

The (6,0,0x21) index triple disappears. LPHa124's (4,0027,0011) shifts from
1488 to1482; BETA456's (4,003F,0012) shifts from148E to1488. The six-byte former
last slot 148E..1493 is all zero. Seventeen live entries remain, followed by
882 zero bytes through17FF. The entire index page is byte-identical to the E15
preflight index page. No live index entry references page6 or ID21.

The entire header page and pages2/3/4 are unchanged from E15 post-insertion.
Every surviving row occurs exactly once at its original address, including the
internal row at1000. There is no survivor relocation or ID reassignment.

Page6 remains physically present, not empty. Its first 25 bytes now are:

```text
44 21 8F 6C 62 01 62 01 01 AC 01 B0 01 31 01 42 4F 55 4E 44 31 32 01 02 03
```

Bytes1801..1BFF exactly match E15, including the old ID, date/time/description,
01 02 row ending, 03 at1818 and999 trailing zeros. No erased payload, new
free-page linkage or changed padding was observed. The 44 prefix is consistent
with a deleted-row marker (ASCII D), but broader marker and reuse semantics
remain hypotheses. On-disk retention is confirmed; logically allocated versus
free/reusable status cannot be established from this one deletion.

## Independent E15 preflight → E16 comparison

All 125 non-database files are also identical to preflight. PERSONAL.CLN is
1,024 bytes longer, and even its first 6,144 bytes differ at exactly six positions:

| Range | Preflight | E16 |
|---|---|---|
| 0026..0027 | FF 8F | 00 6F |
| 002A..002B | F0 00 | 8F FF |
| 043D | 30 | 31 |
| 0443 | 33 | 34 |
| 1800..1BFF | Absent | Retained page6 described above |

This is six changed old-extent bytes plus1,024 additional bytes, or1,030
differing/added positions in five runs. Count/index/live data match preflight;
header, opaque token, next-ID and extra page do not. In particular, the four
header bytes did **not** reverse on deletion; they correlate with persistent
file/page state rather than simply the presence of a live BOUND12 row. Their
actual encoding, bit meanings, ownership and any free-list role remain unknown.

E16 database SHA-256:
`818c44af2f351cc764dfd48a82b3d8ae1dd0b5f733c8549dbdd902f67eed05ea`.
The six-page preflight SHA remains:
`ed43356dac2b6351429f785e4b868b4458f6bc1a68f05f447477da30021862a4`.

## Scope, evidence and next experiment

Production parser and writer still reject E16 with unsupported_layout; they do
not discard retained pages, decode inactive rows, interpret001 or normalize ID
counters. Live enumeration in this report uses the observed raw index triples
and exact comparison to known preflight rows, not a new multi-page parser.
Portable tests use independently generated synthetic data to check safe rejection
and read-only evidence preservation. Private tests assert the entire11-byte
delta, retained payload, survivor/index identities, six baseline-prefix differences
and unchanged runtime rejection.

Private evidence is under E16_page_reclamation in the laboratory: baseline and
copy verification, full before/after snapshots, exact per-byte/per-file JSON
comparisons against both E15 references, raw structural analysis, action record,
screenshots, reproduction sources, test logs and final manifest. No real database,
installed tree or screenshot is transferred to the repository.

Recommend a separately authorized E17: add one seven-character **REUSE17** event
at the now-vacant November1,2026 11:00–12:00 key. Examine whether DeskMate reuses
page6 and the retired storage/ID, appends within that page or allocates elsewhere,
and whether001/next-ID/header values change. This directly tests reuse without
assuming 44 means a reusable slot. E17 was not performed.
