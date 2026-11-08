# DeskMate 3.05 multicalendar reader and bounded writers

2026-11-08, America/New_York. Branch `codex/calendar-multicalendar`.
Fetched main `7f47ef744d7fe02b4385f77e93e20fb2b64c5568`; inspected PR #82,
issue #81 and the separate Address Book draft PR #80 before changes. The latter
remains untouched. During this run the operator supplied the published original
B URL at commit `59e601200641232bf67207c3b4ab7a2f0a9f36e0`. That existing
fixture/provenance commit was incorporated intact; neither original was recreated.

## Results and evidence boundaries

| Snapshot | Bytes | PERSONAL appointments | SECOND appointments | Separate configs |
| --- | ---: | ---: | ---: | ---: |
| Native A, empty SECOND | 10,240 | 61 | 0 | 2 |
| Native B, first SECOND appointment | 10,240 | 61 | 1 | 2 |

Both contain three database tables: `DBCOLS`, `PERSONAL`, `SECOND`. Production
common parsing and Calendar `profile='sdk'` now accept both. All 61 PERSONAL
appointments, alarms, raw payloads, physical locations and 62 logical locators
are checked against the unchanged eight-page source and its existing expected
listing. Configuration ID 16 and appointment ID 17 are scoped by calendar.

The first-SECOND writer reproduces **all original B bytes**. The separate
exact-month-source SECOND creation profile reproduces **all original A bytes**.
Their composition reproduces B. These are offline byte comparisons and synthetic
adversarial tests. The native originals' creation/save actions remain
**operator-reported**, with no complete independently captured guest ledger,
installation manifest or separate reopen evidence. Generated files retain their
distinct provenance even when they equal those originals.

No emulator launch, connection, input, reset, media replacement, save, host input,
RAM capture or configuration/NVRAM change occurred. Requested emulated execution
**0 ms**; actual elapsed guest-clock time **not measured**. No native acceptance
of the newly generated files is claimed.

## Index subdivisions and routing

The old reader treated the index as a 40-byte constant followed by one flat list.
Each 1,024-byte index page instead contains:

- Four ten-byte routing keys at offsets 0, 10, 20 and 30.
- Four **246-byte** locator subdivisions, beginning at offsets **40, 286, 532,
  778**. Each has **41** six-byte little-endian `(data page, offset, ID)` slots.
- Within a subdivision, live locators precede zero padding. A full subdivision
  needs no extra zero locator. An empty subdivision cannot precede a populated
  later one in the supported profile.

The original month source fills these as `[41,21,0,0]`. A and B use
`[20,21,21,0]` for PERSONAL and respectively `[1,0,0,0]` / `[2,0,0,0]` for SECOND.
Logical concatenation across subdivisions preserves all PERSONAL locator values
and their order; physical index offsets change.

A finite routing key is the native ten-byte prefix of the subdivision's **last**
indexed row, using descriptor sort ordinals (up to five fields): append field
bytes and separator `01`, reserve the tenth byte for a final separator when
truncating, and zero-pad short prefixes. PERSONAL's first key is
`8f 6b 80 01 68 01 b9 01 bd 01`; it matches locator `(6,848,60)` and its row.
The remaining keys stay at the original `FF×9/00` sentinel, including two
populated subdivisions. Thus **a sentinel is not an empty-subdivision flag**.
On a routing-prefix tie the native insertion path compares full row fields.

The common reader validates dense individual subdivisions, count, unique
table-local IDs/targets, exact row-boundary/ID correspondence, and every finite
key against its endpoint. SDK Calendar additionally checks ordering of the first
four C sort fields using the source-backed ASCII fold. Description K collation
and ordering among equal first-four-field keys remain opaque; no DOS collation
table is invented. The generic reader does not assert a universal collation.

Packed-12 data chains are now traversed explicitly. Cycles, free/extent markers
inside chains, out-of-file links, metadata/index aliases, shared table data
pages, cross-table locators, interior-row targets, unindexed live rows, dirty
tails and malformed record boundaries are rejected. The one-index-page limit
is retained. The header/directory chains and extent marker are checked. Other
unreferenced pages/map entries remain opaque, retained in `Database.data` and
`CalendarDatabase.data`, not claimed as free space.

## Source corroboration

Offsets here are hexadecimal **absolute file offsets**, not guest addresses.
The original resources have 0x200-byte MZ headers. Reused the existing private
Python 3.13.17 / Capstone 5.0.7 x86-16 environment; selected routines were decoded
from entry/call targets. Private listings are not redistributed.

| Pinned original | Bytes | SHA-256 |
| --- | ---: | --- |
| dm305dk4/DMDBRD.RES | 21,955 | `c4bc9f5699bfaf1ac5adb57a011b04dcec00a2ae75edb2baf603c8001fa99cee` |
| dm305dk4/DMDBUPD.RES | 13,740 | `9e77a2081ebb3a9549903f5d337580c65d6e0a3f603185064d4c82e16327cf4f` |
| dm305dk5/DMDBBLD.RES | 11,858 | `91ada27c026de823aef6a9aae541bafcb6a312552cc5bd612ec8b0e90e53aeed` |
| dm305dk4/CALENDAR.PDM, contextual study | 72,593 | `819df5658b663aa69b15584abf805062679e97f587f3404738f6e82876e4bd23` |

Paths are under the preserved `references/oldskool/extracted/deskmate` root.
These are static executable findings, not observations of loaded runtime targets:

| Location | Corroboration |
| --- | --- |
| RD 5120 | Numeric table `(40,286,532,778)` establishes the four locator starts. |
| UPD 3076–30A7 | Scans backward from subdivision offset 240 in six-byte steps to find the last live locator. |
| UPD 284A–28CA | Calls that endpoint helper, loads its row via 23C6, calls prefix builder 11C8, and writes the ten-byte group route; empty group uses the sentinel. |
| UPD 11C8–1276 | At most five sort ordinals; ten-byte field-prefix construction, separator and zero-padding. |
| UPD 20F4 / 213C | Prefix comparison through 16C5, then full-field fallback through 1BFC on a tie. |
| RD 434A–437A | C comparison folds ASCII a–z and subtracts unsigned byte values. K has a separate DOS-table path. |
| UPD 1C46, 1C8C–1CA8, 2CD9–2CEB | The 126-byte half-copy branch copies from byte 120 (slot 20), explaining a full 41-slot group split into 20 and 21. This is not qualification of general split selection/propagation. |
| BLD 0218 / 0239 | CREATE_TABLE selector 4 reaches 0286. Its complete general name/schema/selection lifecycle is not claimed. |

Row append, headroom, map and decimal-counter rules reuse the hash-pinned
[allocator study](dmdb-page-allocator.md). Four new opt-in private tests pin the
above index/source anchors; four existing allocator tests pin those older rules.

## Reader API and compatibility

```python
from deskmate_formats.calendar import parse_file

db = parse_file("two-calendars.cln", profile="sdk")  # rb only, bounded input
names = [c.name for c in db.calendars]
personal = db.calendar("PERSONAL").appointments
second = db.calendar("SECOND").appointments
configs = db.calendar("SECOND").internal_records
original_bytes = db.data
```

`db.records`, `appointments` and `internal_records` aggregate all calendars.
Every record carries `calendar_name`; use `(calendar_name, record_id)` as a
snapshot key. JSON includes a `calendars` array and names on flat records. Text
output identifies each calendar, including an empty one. Original descriptors,
tokens, raw fields/records, routing keys and header metadata remain available.

`python -m deskmate_formats.calendar.cli FILE.cln --profile sdk --json`
enumerates both. The default observed profile remains six-page. Existing ordinary
six-page writer entry points retain their limits. The common/SDK reader now
requires valid packed-12 chains, so synthetic common-reader fixtures explicitly
construct them. The historical observed corpus is generated with its original
opaque header, preserving its exact fingerprint and historical reports.

## Bounded SECOND append

`calendar.experimental_second.append_first_second(source, event,
experimental=True)` requires exact native A:
`338487558d9992452db15858de1ba9cf790c26abf990ba70b47bbc9dc8d011f5`.
The owning calendar must be exactly SECOND, with only its existing config,
one data/index page, low next ID, known descriptor and available row/index space.
It validates ordinary SDK date/time/ASCII/alarm encodings, appends a serialized
row at the physical marker, inserts its six-byte table-local locator and updates
the two five-digit counters. It reserves the native source-derived two bytes of
headroom, checks preservation, and reparses. Its output is rejected as a later
source. No splitting, allocation, deletion, packing, recurrence or unsupported
record types are enabled.

For `SECOND ONLY 001`, 2026-10-24, 11:00–12:00, alarm off, its output equals B
SHA-256 `b9c9a4cae3cffac1bc337f7b378ea25df74efd3b6771e117c6e0fc3f81b77084`.
Exactly 38 positions change: two counter bytes at 0464/046E, the 32-byte row
and relocated marker at 2027–2047, and three nonzero bytes of the new locator
at 242E/2430/2432. Record ID 17 is independent of PERSONAL's ID 17.
Other supported event values have only independent offline controls, not native
qualification. The direct new-file API `write_first_second` never overwrites.

## Exact-source SECOND creation profile

`calendar.experimental_create.create_second(source, experimental=True)` accepts
only the exact 8,192-byte month source
`d35b10c8e8f0b04e41cd6d16a27b9825531353b00ab503e94b7abd3a11499106`
and exact uppercase name SECOND. It derives seven schema rows/IDs from PERSONAL's
schema, appends a descriptor with separate data/index pages 8/9, copies the
source-derived configuration into its own row, updates DBCOLS counters and the
calendar count, and writes the three packed-12 links/extent marker. It preserves
the PERSONAL descriptor and all appointment data pages/locators.

The PERSONAL repartition is explicitly the single measured `[41,21,0,0]` →
`[20,21,21,0]` profile, with the source-backed slot-20 half copy and endpoint
prefix. **It is not a general balancing algorithm or a claim that creation
caused that split.** Other source bytes, calendar names/case, subsequent creations,
rename/delete, selection and general split propagation are rejected/unimplemented.
`write_second` publishes only to a new destination. Complete output equals A.

The exact-name restriction avoids inventing normalization rules. Active-calendar
selection may involve `PGSETUP.bText` as described in the SDK; this builder does
not inspect or set that external application state. Exact CLN reproduction does
not resolve that separate question.

## Actual generated binaries and independent checks

Both complete files are committed with per-file REUSE sidecars and detailed
manifest entries, and remain excluded from wheel/sdist:

| Tool-generated file | Bytes | SHA-256 / exact byte oracle |
| --- | ---: | --- |
| [second-empty-calendar-tool-generated.cln](../../tests/fixtures/application-generated/calendar/second-empty-calendar-tool-generated.cln) | 10,240 | `338487558d9992452db15858de1ba9cf790c26abf990ba70b47bbc9dc8d011f5` / A |
| [second-first-event-tool-generated.cln](../../tests/fixtures/application-generated/calendar/second-first-event-tool-generated.cln) | 10,240 | `b9c9a4cae3cffac1bc337f7b378ea25df74efd3b6771e117c6e0fc3f81b77084` / B |

**Tool-generated, not application-produced or native-accepted.** Original A/B
bytes and their provenance are preserved separately and unchanged.

From the repository root, set `PYTHONPATH=src` and use fresh destinations:

```powershell
python tools/experimental/generate_calendar_second_table.py tests/fixtures/application-generated/calendar/sdk-30-days-allocator-tool-generated.cln tests/fixtures/application-generated/calendar/sdk-30-days-allocator-tool-generated.expected.json NEW-SECOND.cln --experimental-create-second
python tools/experimental/generate_calendar_second.py tests/fixtures/application-generated/calendar/native-second-empty-calendar-operator.cln NEW-FIRST-EVENT.cln --experimental-first-second
python tools/experimental/check_calendar_multicalendar.py tests/fixtures/application-generated/calendar/sdk-30-days-allocator-tool-generated.cln tests/fixtures/application-generated/calendar/native-second-empty-calendar-operator.cln tests/fixtures/application-generated/calendar/sdk-30-days-allocator-tool-generated.expected.json --first-second tests/fixtures/application-generated/calendar/native-second-first-event-operator.cln
python -m unittest discover -s tests/portable -p test_calendar_multicalendar.py -v
```

The checker imports no production reader, writer, page-map or value codecs. It
decodes map bits as a bitstream, scans physical rows separately from locators,
checks schema/ownership/routes/counts/ordinary fields, all 61 expected PERSONAL
appointments and alarms, and the complete A/B differential. Its structural
`inspect` path has no input-hash gate, so adversarial tests exercise actual
validation. The CLI additionally pins the original identities. Generated append
outputs use a distinct expected-event/preservation check without reading B.
Both generators independently validate **before** atomic new-file publication.

Validation, command log hashes, machine configuration, source/code identities and
durable private archive receipt are in [the evidence record](../evidence/calendar-multicalendar-reader-writer.json).

## Smallest remaining native experiments

First, on a separately authorized disposable installation, identify and reopen
the published generated first-event candidate and verify SECOND's event plus
PERSONAL isolation, retaining full CLN and installed-tree hashes. Byte equality
is already established; an independently captured reopen/selection ledger is not.

For the creation trigger, the smallest discriminating control is to open/close
an untouched copy of the original eight-page month source **without creating a
calendar**, retaining complete before/after CLN bytes. If its full first group
also splits, creation was not necessary for that rewrite. Arbitrary names and
active selection need their own declared experiment. These are proposed future
actions, not authority to operate the guest in this campaign.
