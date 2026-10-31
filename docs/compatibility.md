# Compatibility and supported versions

| Component | Current supported scope |
|---|---|
| Python | Local verification on 3.13/3.14 Windows; initial four hosted Windows/Ubuntu CI jobs passed (owner-reported) |
| DeskMate | Only the documented Tandy DeskMate 3.05 Calendar observed subset |
| Files | Exactly 6,144 bytes, single observed data/index page per table, validated schema, low IDs |
| Dates | 2026-10-23,2026-10-24,2026-11-01,2027-11-01 |
| Time values | 09:00,09:15,10:00,10:15,11:00,12:00; writer requires start<end |
| Text | Reader decodes printable ASCII; writer accepts 1..120 printable ASCII characters; 7/10-character historical descriptions and E15 60-character generated descriptions application-verified |
| Opaque values | Duration/Protected retained raw; writer accepts observed empty/31 profile; no alarm codec |
| Index ordering | Writer uses chronological date/start ordering, rejects ties; compatible with checked five-event sample |

Read-only parsing can preserve unsupported values as raw/null with warnings, but
rejects unknown structural layouts. Bounded append preserves existing physical row
bytes/IDs/addresses, may move index entries, and rejects extra pages. There is no
editing/deletion/compaction allocator, general text escaping or stable logical ID
promise. E11/E12 demonstrate IDs can change after application edits/deletions.

The private original 72 tests remain in DOSLAB. Their migrated counterparts use
the installed package and external fixtures; additional direct E07→E08/E09→E10
regressions are private as well. Synthetic success does not substitute for the
archival byte-perfect or application tests. The repository is privately hosted; the owner reports successful initial CI on
Windows/Ubuntu and Python 3.13/3.14. Historical local results remain in
verification.md; hosted CI uses only portable tests.

E15 observed a seven-page application-produced file after one allocation. It is
documented evidence, **not supported parser/writer input**; both reject it.
The accepted six-page near-capacity preflight remains supported. See
[the E15 report](experiments/e15-page-boundary.md).
