# E18: record-size controls after deletion

## Result

Both independent insertions **append at 0x1818 with fresh ID 0x22**, rather than
reuse the retired BOUND12 span at 0x1800 or its ID 0x21. This holds for a record
smaller than that span and one larger than it. Neither allocates a page: both
files remain 7,168 bytes. These two observations do not establish a general
allocator or prove that retired space can never be reclaimed under pressure.

## Controlled design and execution

The plan was recorded privately before either trial. Each starts from a separate
complete, byte-verified copy of the same original E16 post-deletion installation:
126 files; PERSONAL.CLN SHA-256
`818c44af2f351cc764dfd48a82b3d8ae1dd0b5f733c8549dbdd902f67eed05ea`.
No E17 or first-variant output served as another experiment's input.
The branch starts independently at main 0697693021f1d465b984e3197ac3afe85a6491f5.
The [separate E17 checkpoint](https://github.com/smartyhall/deskmate-formats/commit/43c890c95c1569b8e788439d65f8f000031a1481)
provides the equal-length 24-byte control.

Both events use November 1, 2026, 11:00 AM–12:00 PM and visibly unchecked alarm.
S18 has three characters and a 20-byte record; LONG18 followed by fourteen literal
X characters has twenty characters and a 37-byte record. Both exceed the original
page's 17 available bytes; only the shorter fits the retired 24-byte span. This
avoids confounding hole reuse with a record that fits the original data page.
The long description is below the previously observed 60-character input limit.

The pinned BIOS-keyboard server/local SDK operated each fresh emulator by explicit
PID, with short paced batches and queue checks. Find Date used direct replacement
of its observed initial selection. Event → Add opened with the correct date,
blank times, AM defaults and alarm unchecked. Start 1100 entered 11 AM; End 1200
was followed by explicit PM selection (Right focuses; Space selects). Complete
descriptions, date, times and alarm were independently screenshot-verified before
each **single Enter submission**. Each resulting day screen showed the new event
once alongside the same four original events. No correction, editing or deletion
occurred. Both applications and emulators exited normally before after snapshots.

## Evidence matrix

| Case / description | Characters | Record bytes | New address / ID | New 03 marker | Changed positions |
|---|---:|---:|---|---|---:|
| E16 deleted baseline | — | retired 24 | no new live record | 0x1818 | — |
| E17 REUSE17 | 7 | 24 | 0x1818 / 0x22 | 0x1830 | 35 |
| S18 | 3 | 20 | 0x1818 / 0x22 | 0x182C | 31 |
| LONG18XXXXXXXXXXXXXX | 20 | 37 | 0x1818 / 0x22 | 0x183D | 48 |

Short after SHA-256:
`cda46df771e8214b0a3484123da57359ff3143d7c947423e93f1e5f853725a2d`.
Long after SHA-256:
`736a9441eb8b691c58b7fa0deb1b181e408646c893d9f3cd9df11059e3d8662f`.

## Common measured structures

Only PERSONAL.CLN changes; all other 125 files remain byte-identical, with no
files added or removed. All 17 original indexed rows (16 user appointments plus
the control row) keep their IDs, addresses and exact raw bytes. Entire page 4,
the control row at 0x1000, header page 0 and schema pages 2/3 are unchanged.
The entire retired 24-byte span, including prefix 44 and old ID 21, is unchanged
and unindexed. No live row resolves to 0x1800.

Both counters change identically: 00017→00018 and next-ID candidate 00034→00035
(decimal); opaque 001 remains unchanged. The original marker at 0x1818 becomes
80, beginning the new row. The index at 0x1482 becomes `(6,0x18,0x22)`; the last
two original triples shift six bytes right, retaining their target values.
All earlier index slots remain unchanged and unused index space remains zero.
Only 1,024-byte blocks 1, 5 and 6 change. Header bytes 0x26–0x27 remain 006F and
0x2A–0x2B remain 8FFF; their semantics remain unknown. There is no new page or
observed page-reference change. Zero bytes after the new 03 marker number 979
(short) and 962 (long).

The seven raw fields are date 8F6C62, weekday 62, empty Duration, start AC, end B0,
Protected 31, and the exact ASCII description. Alarm was visibly off; this does
not independently identify an alarm encoding. Unknown fields remain unknown.

## Exhaustive fixed-offset comparisons

No file-size differences exist. These tables cover every changed position;
all unlisted positions are identical. No heuristic insertion alignment is used.

### E18_short3: every changed byte

| Offset | E16 | After |
|---|---|---|
| `0x0439` | `37` | `38` |
| `0x0443` | `34` | `35` |
| `0x1482` | `04` | `06` |
| `0x1484` | `27` | `18` |
| `0x1486` | `11` | `22` |
| `0x148A` | `3F` | `27` |
| `0x148C` | `12` | `11` |
| `0x148E` | `00` | `04` |
| `0x1490` | `00` | `3F` |
| `0x1492` | `00` | `12` |
| `0x1818` | `03` | `80` |
| `0x1819` | `00` | `22` |
| `0x181A` | `00` | `8F` |
| `0x181B` | `00` | `6C` |
| `0x181C` | `00` | `62` |
| `0x181D` | `00` | `01` |
| `0x181E` | `00` | `62` |
| `0x181F` | `00` | `01` |
| `0x1820` | `00` | `01` |
| `0x1821` | `00` | `AC` |
| `0x1822` | `00` | `01` |
| `0x1823` | `00` | `B0` |
| `0x1824` | `00` | `01` |
| `0x1825` | `00` | `31` |
| `0x1826` | `00` | `01` |
| `0x1827` | `00` | `53` |
| `0x1828` | `00` | `31` |
| `0x1829` | `00` | `38` |
| `0x182A` | `00` | `01` |
| `0x182B` | `00` | `02` |
| `0x182C` | `00` | `03` |


### E18_long20: every changed byte

| Offset | E16 | After |
|---|---|---|
| `0x0439` | `37` | `38` |
| `0x0443` | `34` | `35` |
| `0x1482` | `04` | `06` |
| `0x1484` | `27` | `18` |
| `0x1486` | `11` | `22` |
| `0x148A` | `3F` | `27` |
| `0x148C` | `12` | `11` |
| `0x148E` | `00` | `04` |
| `0x1490` | `00` | `3F` |
| `0x1492` | `00` | `12` |
| `0x1818` | `03` | `80` |
| `0x1819` | `00` | `22` |
| `0x181A` | `00` | `8F` |
| `0x181B` | `00` | `6C` |
| `0x181C` | `00` | `62` |
| `0x181D` | `00` | `01` |
| `0x181E` | `00` | `62` |
| `0x181F` | `00` | `01` |
| `0x1820` | `00` | `01` |
| `0x1821` | `00` | `AC` |
| `0x1822` | `00` | `01` |
| `0x1823` | `00` | `B0` |
| `0x1824` | `00` | `01` |
| `0x1825` | `00` | `31` |
| `0x1826` | `00` | `01` |
| `0x1827` | `00` | `4C` |
| `0x1828` | `00` | `4F` |
| `0x1829` | `00` | `4E` |
| `0x182A` | `00` | `47` |
| `0x182B` | `00` | `31` |
| `0x182C` | `00` | `38` |
| `0x182D` | `00` | `58` |
| `0x182E` | `00` | `58` |
| `0x182F` | `00` | `58` |
| `0x1830` | `00` | `58` |
| `0x1831` | `00` | `58` |
| `0x1832` | `00` | `58` |
| `0x1833` | `00` | `58` |
| `0x1834` | `00` | `58` |
| `0x1835` | `00` | `58` |
| `0x1836` | `00` | `58` |
| `0x1837` | `00` | `58` |
| `0x1838` | `00` | `58` |
| `0x1839` | `00` | `58` |
| `0x183A` | `00` | `58` |
| `0x183B` | `00` | `01` |
| `0x183C` | `00` | `02` |
| `0x183D` | `00` | `03` |


## Preservation, regression and limits

Private evidence remains under DOSLAB `EXPERIMENTS/PHASE2/E18_short3` and
`EXPERIMENTS/PHASE2/E18_long20`: full before/run/after trees and manifests,
all byte deltas and block hashes, raw observations, MCP replies/BIOS bytes,
action records and independent screenshots. Both original source manifests,
all 126 final installation files and 14 protected emulator/profile/debugger
hash-and-mtime guards pass. Source software, databases and screenshots are not
distributed. The private evidence matrix also records E16 and E17 hashes.

Focused external-fixture tests assert both complete deltas, exact hashes,
unchanged originals/index targets, and continued seven-page production rejection.
No production parsing, writing, allocation, CI or dependencies are changed.
Executed checks are recorded in the private sprint checkpoint; no hosted CI or
unexecuted historical test results are claimed.

These controls weaken a simple "reuse any sufficiently large retired slot"
explanation for this baseline. Append-after-marker is consistent across 20-, 24-
and 37-byte records. Alternatives include deferred reclamation under pressure,
an explicit packing operation, or a page/record state not yet understood.
The most useful future controlled experiment would create page-6 space pressure
from an independent verified baseline and ask whether retired storage is reclaimed
before another allocation. It requires a separately reviewed bounded procedure;
no such experiment or generalized allocator was implemented in this sprint.
