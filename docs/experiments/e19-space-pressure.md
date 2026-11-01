# E19: retained deleted storage under page-space pressure

## Result

At the first insufficient contiguous-space transition, DeskMate **allocated a new
data page instead of reclaiming the retired 24-byte BOUND12 span**. Twelve new
77-byte records fit on retained page6 after the retired row. The thirteenth went
to page7 at **0x1C00**, ID **0x2E**, and the file grew **7,168→8,192 bytes**.
The retired span and historical ID0x21 remain unchanged and unindexed. All29
previously indexed rows retain their raw bytes, IDs and addresses at the crossing.
No surviving record is compacted, relocated or reassigned in this transition.

This is one controlled pressure sequence, not a general free-list or allocation
policy. It demonstrates that this particular reclaimable span was not compacted
even when doing so could have avoided the next page. It does not prove that
reclamation never occurs under other conditions. Production reader/writer remain
unchanged and deliberately reject these unsupported layouts.

## Baseline and pre-mutation design

The original E16 post-delete installation, all126files and14protected original
executable/profile/debugger hash-and-mtime guards were verified. Starting
PERSONAL.CLN:7168bytes, SHA-256 `818c44af2f351cc764dfd48a82b3d8ae1dd0b5f733c8549dbdd902f67eed05ea`. Neither E17 nor E18 output was used.
The private written plan preceded all mutations and listed every event and stop
condition. The research branch starts at main272605367c620d38c80a1a66791605d48401e4e7.

Page6 starts1800; its24retired bytes precede03at1818. Reserving a new03 leaves
999contiguous append bytes. Prior observed60ASCII descriptions use77-byte rows
(17bytes overhead). Twelve require924bytes: predicted03at1BB4 and75bytes remain.
A thirteenth77-byte row exceeds that by2bytes. Reclaiming24retired bytes could
fit13live rows1001bytes plus03 and22zeros. The old24-byte hole alone cannot hold
a77-byte row. Compaction, another allocation, rearrangement or refusal were all
predeclared possibilities; no outcome was assumed.

The index supports163live6-byte entries with a full zero sentinel reserved;
current17 plus13 gives30, safely below that limit. Distinct dates November2–14,
2026 avoid existing user events and each other. Each new event is11AM–noon,
alarmvisiblyunchecked/off. Descriptions are P1901..P1913 plus the identical suffix
`A0123456789B0123456789C0123456789D0123456789E0123456789`: exactly60ASCII bytes.
This visually checkable suffix replaced55homogeneousXs in a documented amendment
**before any E19 mutation**, without changing the length or capacity calculation.

## Execution and clean checkpoints

Original DeskMate created all13events through its normal interface. The pinned
BIOS MCP server was called through the verified isolated local SDK fallback;
registered keyboard tools remained absent from this chat catalog. No host keyboard
simulation, AUTOTYPE, executable patch, debugger RAM write or database writer was
used. Explicit PID/creation/executable guards and serialized paced batches remain
in the private action record. No ambiguous batch was replayed.

For every event: observe Find Date's initial selection, directly type the verified
date, inspect Add's actual blank time fields/defaults, enter11AM/noon and select
PM explicitly, then type60characters in paced batches of at most14. Independent
description tail/head screenshots overlap to cover all60characters; date, times
and alarm are visible before the sole save. Each saved schedule was inspected.
Built-in Election Day/Veteran's Day displays were left untouched. No event was
edited, deleted, corrected by a second insertion, or submitted twice.

The first event was a separate clean gate: length77/address1818/ID22 and exact
description confirmed after normal Calendar/emulator exit. That full126-file
after snapshot became segment12's verified before copy. Events02..12 then ran
on that sequential copy; normal exits preceded the second full snapshot. It
confirmed marker1BB4/75zeros and all17original rows unchanged. A verified copy of
that clean checkpoint became segment13 for **one** crossing insertion. After
P1913 was verified, Calendar/emulator exited normally and all mutation stopped.
The authorization ceiling14 was not a target: only13events were added.

| Closed checkpoint | Bytes | Live rows including control | Next-ID candidate | Opaque token | SHA-256 |
|---|---:|---|---|---|---|
| E16 original |7168|00017|00034|001|`818c44af2f351cc764dfd48a82b3d8ae1dd0b5f733c8549dbdd902f67eed05ea`|
| first gate |7168|00018|00035|001|`843b6a6b7ac5d317c858454b6047b1c305dff852301dc7640b11afa8d0a32299`|
| after12 |7168|00029|00046|001|`f70406212f170065a5dec83f11d8a55e1ec05f58dda1d57b6c9973d5d6b9d0ed`|
| after13 |8192|00030|00047|001|`ad6683ae34d3367026e47aeddd91ca93502551c557f02f7762039ff2d82011a1`|

The final30indexed rows comprise29user appointments and the existing control
row. All16original user appointments survive byte-for-byte at their old addresses;
all12pre-boundary new events likewise survive unchanged at the crossing.

## Measured record and index locations

| Event | Date | ID | Address | Index slot | Bytes |
|---|---|---|---|---|---|
| P1901 | 2026-11-02 | `22` | `0x1818` | `0x1482` | 77 |
| P1902 | 2026-11-03 | `23` | `0x1865` | `0x1488` | 77 |
| P1903 | 2026-11-04 | `24` | `0x18B2` | `0x148E` | 77 |
| P1904 | 2026-11-05 | `25` | `0x18FF` | `0x1494` | 77 |
| P1905 | 2026-11-06 | `26` | `0x194C` | `0x149A` | 77 |
| P1906 | 2026-11-07 | `27` | `0x1999` | `0x14A0` | 77 |
| P1907 | 2026-11-08 | `28` | `0x19E6` | `0x14A6` | 77 |
| P1908 | 2026-11-09 | `29` | `0x1A33` | `0x14AC` | 77 |
| P1909 | 2026-11-10 | `2A` | `0x1A80` | `0x14B2` | 77 |
| P1910 | 2026-11-11 | `2B` | `0x1ACD` | `0x14B8` | 77 |
| P1911 | 2026-11-12 | `2C` | `0x1B1A` | `0x14BE` | 77 |
| P1912 | 2026-11-13 | `2D` | `0x1B67` | `0x14C4` | 77 |
| P1913 | 2026-11-14 | `2E` | `0x1C00` | `0x14CA` | 77 |


The crossing entry at14CA is bytes `07 00 00 00 2E 00`, resolving to `(7,0,0x2E)`.
LPHa124's triple moves14CA→14D0 and BETA456's14D0→14D6, without changing their
target values/IDs. All preceding27triples are unchanged at the crossing. The
sentinel begins14DC with804zero bytes to17FF; the index header remains unchanged.
New IDs22..2E match the observed next-ID candidate sequence34..46(decimal);
historical21is not reused. No universal max-live-ID rule is inferred.

Whole page6 is unchanged by the crossing: retired24bytes at1800..1817, prefix44,
oldID21/payload, the12rows1818..1BB3,03at1BB4 and75zeros. Page4 and its internal
row1000 are unchanged from E16. Schema blocks2/3 also remain identical. No
duplicate indexed row or abandoned replacement row is observed.

## Exhaustive crossing differences

OnlyPERSONAL.CLN changes among126files; no files are added/removed. From the
clean after12 checkpoint there are **16changed old-extent bytes and1024appended
bytes**,1040different/added positions. All16old-extent changes are listed below.
All unlisted old positions are identical. Changed1024-byte blocks:0(5positions),
1(3),5(8),7(1024appended); blocks2/3/4/6are unchanged at the crossing.

| Offset | Before | After |
|---|---|---|
| `0x0029` | `FF` | `00` |
| `0x002A` | `8F` | `7F` |
| `0x002B` | `FF` | `F8` |
| `0x002C` | `00` | `FF` |
| `0x002D` | `00` | `F0` |
| `0x0438` | `32` | `33` |
| `0x0439` | `39` | `30` |
| `0x0443` | `36` | `37` |
| `0x14CA` | `04` | `07` |
| `0x14CC` | `27` | `00` |
| `0x14CE` | `11` | `2E` |
| `0x14D2` | `3F` | `27` |
| `0x14D4` | `12` | `11` |
| `0x14D6` | `00` | `04` |
| `0x14D8` | `00` | `3F` |
| `0x14DA` | `00` | `12` |


Appended bytes are exhaustively specified: `0x1C00..0x1C4C` is the77-byte row
below; `0x1C4D` is03; `0x1C4E..0x1FFF` is946zero bytes. BeforeEOF all those
positions were absent, so the raw comparison records null→byte even for zeros.

```text
802e8f6c6f01680101ac01b00131015031393133413031323334353637383942303132333435363738394330313233343536373839443031323334353637383945303132333435363738390102
```

Raw seven fields:8F6C6F,68,empty,AC,B0,31,exactASCII description. Alarmoff is
visual evidence; no alarm codec is inferred. Header0026..0027 stays006F;
002A..002B changes8FFF→7FF8, accompanied by0029 FF→00,002C00→FF,002D00→F0.
Thus the previously noted four header bytes are **not** an exhaustive universal
allocation-update footprint. These five changed bytes are allocation-associated
observations, not decoded free-list/page-map/checksum semantics. Opaque001persists.

Complete fixed-offset comparisons also cover originalE16→after12
(979positions) and
originalE16→final(2010positions,
includingEOFextension). No heuristic insertion alignment or normalization was
used. Every byte, old/new/null value, block hash, counter and index/record table is
retained in private machine-readable reports.

## Preservation, tests and limits

Private root: DOSLAB `EXPERIMENTS/PHASE2/E19_space_pressure`. segment01,
segment12 and segment13 retain full before/run/after trees, SHA-256 manifests,
identity/configuration copies, screenshots, actual MCP replies/BIOS bytes and
raw observations. Root plan/action ledger/preboundary/allocation analyses and
three whole-sequence comparisons link the clean checkpoints. The recovery sprint
status records exact completed actions. No original software, database or image
is committed publicly. All126relevant source/final files and14original-file guards
are verified; working profiles remain separate copies of the established profile.

Focused external-fixture tests check the exact crossing delta/page, retained
deleted bytes, stable originals/index targets and conservative runtime rejection.
Executed checks are recorded in the private sprint handoff; hosted CI and unchanged
historical suites are not claimed. No production allocator, writer or multi-page
parser was introduced, and no further live experiment followed the first crossing.

A useful next controlled experiment would delete only P1913 from an independent
copy of this final state, checking whether the eighth page is retained, whether
the opaque001token becomes002, and whether header/index/ID behavior repeats E16.
That would discriminate candidate deletion-metadata interpretations with two
retired rows, without assuming a general algorithm. It was not performed here.
