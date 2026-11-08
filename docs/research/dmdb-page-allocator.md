# DMDB 3.05 data-page allocator continuation

Offline continuation from fetched `origin/main`
`8c1e7aa6f6aac04c3167d141f981e10f1d3b860e`, branch
`codex/dmdb-page-allocator`, started 2026-11-07 America/New_York.
[Draft PR #75](https://github.com/smartyhall/deskmate-formats/pull/75).
Original branches, worktrees, media and private archives were preserved.

## New static findings

The header contains **MSB-first packed 12-bit page-chain entries**, not a bitmap.
This conclusion comes from mutually consistent executable writer/reader paths,
the pinned E02 fixture, and both published allocation transitions. Original
E15/E19 bytes remain unavailable: no new measurement of those files is claimed.
SDK interface declarations supply selector names, not this storage encoding.

All addresses below are **absolute file offsets**, hexadecimal. Each MZ header
is 0x200 bytes. CS-relative operands in the selected single code segment therefore
need +0x200; these are not guest addresses or original function names.

| Pinned input | Bytes | SHA-256 |
| --- | ---: | --- |
| SDK 3.03 DMDB.H | 14093 | `47c2ff4638d8ab1bcc12aeab3e2dd5b51ccfeef9bbddb1a014912c831df4d5aa` |
| SDK 3.03 DMDB.INC | 13275 | `2ea33422d68ab2402ca2b83a1c1f5d7fee80db9c36000a8609d42712ce299a29` |
| 3.05 DMDB.R89 | 1109 | `799444bb8c04632d261f61498ba269f9352e5528718f2e0a89512bf6ef7b808f` |
| 3.05 DMDBRD.RES | 21955 | `c4bc9f5699bfaf1ac5adb57a011b04dcec00a2ae75edb2baf603c8001fa99cee` |
| 3.05 DMDBUPD.RES | 13740 | `9e77a2081ebb3a9549903f5d337580c65d6e0a3f603185064d4c82e16327cf4f` |
| 3.05 DMDBBLD.RES, corroborating input | 11858 | `91ada27c026de823aef6a9aae541bafcb6a312552cc5bd612ec8b0e90e53aeed` |

Paths are the previously documented `references/oldskool/extracted`: SDK headers
under `sdk-3.03/Development-Disk-1`, retail inputs under `deskmate/dm305dk4`
(DMDBBLD under `dm305dk5`). No substituted binary or guessed source path.
The existing SDK crosswalk's private Python 3.13.17 / Capstone environment was
reused for headless x86 16-bit decoding. Full listings, scripts, identities and
instruction-boundary corrections stay in the new private archive
`dmdb-allocator-20261107`; old projects were not opened or changed. Linear sweeps
were used only for locating candidates; selected routines were decoded again
from explicit entry/call targets. Padding and data tables can misalign a sweep.

| Location | Decoded semantics | Evidence boundary |
| --- | --- | --- |
| UPD 0200–02AE, 0235/025E | Selector 7 (`ADD_ROW`) calls 02B0; 0340 calls 1277. Selector 39 also uses 02B0. | Direct static branches/calls; actual runtime dispatch not observed. |
| UPD 1277–140B | Gets last data page via callback 0x17; checks contiguous tail space, calls 18E5 on shortage; writes high ID byte OR 0x80, low ID byte, payload and marker 03; forms location `(page << 10) + offset`; calls index insertion 1F8E and page write 3001. | Static implementation agrees with measured low-ID rows; broad index splitting not qualified. |
| UPD 12DB–12F6, 140C–1425; RD 43E3–43F8 | Payload length through inclusive 02 plus 4 is compared with `1023 - marker_offset`. A low-ID row has two ID bytes, so this guard requires **row length + 2** free bytes excluding the marker. | Two extra bytes of headroom are source-derived; their rationale and equality behavior have no new native observation. The existing six-page writer's guard is unchanged. |
| UPD 18E5–1977 | Obtain page N from 1A96, set map[N]=0xFF8, find prior chain tail with callback 0x17 when a starting page exists, then set map[tail]=N. | Establishes append linkage. The >=0x154 special branch is outside the proposed small profile. |
| UPD 1978–19FD | Entry address is `map_base + n + floor(n/2)`. For even n write value bits 11..4 then bits 3..0 in next byte's high nibble, preserving its low nibble. Odd n preserves current high nibble and writes value bits 11..8 in low nibble plus bits 7..0 in next byte. Flushes map through 2F8B. | Exact bit operations and neighbor preservation. No checksum operation on this path. |
| UPD 1A96–1B14 | Scan entries from 1. Zero is an available slot. On 0xFFF, check disk free space for 1024 bytes, set next entry to 0xFFF and current to zero; return current page. Limit 0x294 is encoded. | Static free-slot/extent-marker policy, not proof of all reuse/reclamation behavior. |
| RD 4058–40A9; 40AA–40D1 | Matching packed-12 decoder; chain walker follows values until 0xFF8 and returns the last page. | Independent executable corroboration of the writer interpretation. |
| RD 20D4–20F6; 360C–3673 | Allocate 0x3E0 map bytes at object +4; read those bytes from file offset 0x20. | Establishes the map's disk base, not merely a fitted header offset. |
| UPD 2F8B–3000; 3001–3075 | Seek to 0x20 and write 0x3E0 map bytes; page write seeks to `page << 10` and writes 0x400 bytes. DOS write at 31C6 uses AH=40h. | File extension follows the new page write; no separate file-length field update found on this path. Unknown first 32 header bytes preserved. |
| RD callback table 482B; dispatcher 48AD–48C2 | Entries 0x16/0x17/0x19/0x32/0x35 resolve to 4058/40AA/45AB/43E3/4575. UPD thunks 3347/334D/3359/33EF/3401 select those callback numbers and jump through DS:011C at 3449. | Conditional intercomponent continuation; external service binding is still not a runtime-proven edge. |
| RD 3D1D→3B0E, 3C32–3C4F | The cache request 0x4E used by UPD 1310 creates a zero-filled 1024-byte page with initial marker 03. | Explains the new-page row offset and zero tail without inventing page-local linkage. |
| UPD 30A8–3161; 2F0A–2F4B | Table-descriptor update locates the count token, uses width 5, and selects the next-ID token with ordinal 7; recursive division by 10 emits ASCII digits. | Corroborates the measured count/next-ID changes. The descriptor data-page start stays unchanged. |

DMDB.R89 remains the previously identified small name-binding/forwarding stub;
the allocation arithmetic is in the update resource, with reader callbacks.
The names/DS-slot facts in [call review](database-call-review.md) remain valid;
this investigation does not claim to close the loader observation gap in #25.
The corroborating BLD path at 272D–275F sets data/index chain tails to 0xFF8;
it is not used to justify a general create-schema writer.

## Independent crosschecks against historical transitions

For page n, bit position is `12*n` within the map at 0x20. E02's verified map
starts with six 0xFF8 entries (pages 0–5), then 0xFFF at entry 6, then zeros.
The following **source-derived updates** reproduce the published deltas exactly:

| Transition | Entry updates | Predicted changed header bytes |
| --- | --- | --- |
| E15, 6→7 pages | [4]=6, [6]=0xFF8, [7]=0xFFF | 0026 FF→00; 0027 8F→6F; 002A F0→8F; 002B 00→FF |
| E19, 7→8 pages | [6]=7, [7]=0xFF8, [8]=0xFFF | 0029 FF→00; 002A 8F→7F; 002B FF→F8; 002C 00→FF; 002D 00→F0 |

All unlisted header bytes remain identical, including the neighboring nibbles.
E19's prior deletion did not change this chain. Neither test authenticates or
reconstructs the missing native files. The known DOSLAB root is unset; only the
documented inventory/archive roots were consulted, with no unrelated private scan.
Use the existing Phase II diagnostic if the exact original files become available.

## Scope decision

The evidence justifies only an explicitly experimental, **new-file builder from
the exact E02 baseline**, with fresh pages 6 and 7 appended as necessary, one
unchanged PERSONAL index page, ordinary SDK events, low IDs and no tied starts.
Preserve all source bytes except the proven map entries, existing count/next-ID
tokens, chronological index, and previously unused data tail. No general bitmap,
native-file multipage append, reuse, deletion, pack, schema creation, index growth,
tie/collation or >=0x154-page support is implied. Existing six-page profiles stay
unchanged. Generated output requires a separately authorized native open/save.

## Implemented experiment and reproducibility

`calendar.experimental_new.build_new(source, events, experimental=True)` requires
the exact 6,144-byte E02 SHA-256
`0af0896163c24c992fa515ddca8c45a31496250d6ba84c9f08e28020a07fe0d9`.
It rejects its own output as a subsequent source, an omitted/non-boolean opt-in,
empty or >100 additions, unsupported values, ties and a ninth page. It builds
everything in memory; the CLI publishes through a flushed same-directory
temporary file and atomic hard-link creation, with no overwrite fallback.
The existing six-page writer source is unchanged.

From the repository root, with `PYTHONPATH=src`, use fresh destination paths:

```powershell
python tools/experimental/generate_calendar_month.py tests/fixtures/application-generated/calendar/e02-86box-historical-match.cln NEW-MONTH.cln --experimental-new-pages > NEW-MONTH.json
python tools/experimental/check_calendar_multipage.py tests/fixtures/application-generated/calendar/e02-86box-historical-match.cln NEW-MONTH.cln NEW-MONTH.json
python -m unittest discover -s tests/portable -p test_calendar_multipage.py -v
```

The candidate is **tool-generated, not application-generated or native-accepted**:
61 appointments / 30 dates (October 23–November 21, 2026), including unchanged
original LPHa124, with 60 additions in reverse chronological physical insertion
order. Descriptions append ` / allocator trial` to the existing sample schedule;
all date/time/alarm values are in the receipt. It is 8,192 bytes, SHA-256
`d35b10c8e8f0b04e41cd6d16a27b9825531353b00ab503e94b7abd3a11499106`.
The complete file, expected additions, independent report, source snapshots and
test logs are retained in the new durable private archive. No generated binary
was added to the application-generated fixture directory.

The independent checker imports no production parser, writer, map setter or
date/time codec. It compares a bitstream model with all 992 map bytes; scans all
data pages independently of index targets; checks every raw field against the
receipt using separate SDK arithmetic; checks chronological unique LE16 triples,
original row addresses/bytes, ASCII counters, marker/zero tails and all unchanged
header/directory/schema/index-header bytes. Production SDK parsing is an additional
check, not the independent oracle. No native success follows from either check.
Portable tests cover published deltas, adjacent-nibble preservation, both sides
and equality of the source space guard, input/size/tie/opaque-value limits, reverse
insertion across both new pages, corrupted bytes and no-overwrite/source-mtime.

Four opt-in private tests hash-verify SDK/modules and assert selected instruction
operands and callback-table words. Run with `DESKMATE_REFERENCE_EXTRACTED`
explicitly set to the preserved extraction root:

```powershell
python -m unittest discover -s tests/private -p test_dmdb_allocator_source.py -v
```

## Native gates and remaining uncertainty

No emulator was launched, connected or controlled; no guest media/config/NVRAM
or native save changed. Requested emulated execution **0 ms**; actual guest-clock
delta **not measured**. This establishes static code semantics and offline
consistency, not live loader binding, a full allocator specification, or native
acceptance. Unknown header bytes, schema, descriptor tokens and original indexing
rules remain preserved. No Address Book specimen arrived and no multicontact
writer was enabled; its prepared A01→two-contact trial is unchanged.

The highest-value next experiment is a **separately authorized native trial of
the pinned month candidate** on an identified disposable installation and owned
emulator epoch: verify the installed candidate hash, inspect appointments whose
receipt/index targets lie on pages 4, 6 and 7 and all 30 dates, then perform one
predeclared edit/save on a copied candidate and retain complete before/after files
and installed-tree manifests. The exact edit, input, save and reopen scope must
be authorized first. This distinguishes offline consistency from native traversal
and persistence. The A01→two-contact trial remains the smallest Address Book gate.

Validation/preservation totals and artifact identities are in the successor
[receipt](../evidence/dmdb-page-allocator.json). Historical reports stay unchanged.

Final portable run: **330 passed (138.855 s)**; nine focused allocator tests
passed (1.491 s), and four hash-pinned private source tests passed (0.003 s).
Ruff, REUSE (290/290 authored files), repository audit (587 files, four database
fixtures/four synthetic JSONL fixtures), wheel/sdist build, package privacy checks
and isolated wheel-only generation passed. The wheel-only builder reproduced
the exact month hash. An initial host-interpreter probe lacked Capstone; using
the existing crosswalk venv resolved it without installing dependencies.

All six input contents **and mtimes**, all four committed database fixtures,
106 prior campaign archive members and 46 prior Phase II archive members were
rehash-verified unchanged. The new candidate has 62 index entries including the
control row, IDs 0x10–0x4D, next-ID 78 decimal and 101 free index slots. Data-page
row counts are 24/24/14 on pages 4/6/7, with 30/7/429 zero bytes after their 03
markers. These are raw offline measurements of the generated candidate.
