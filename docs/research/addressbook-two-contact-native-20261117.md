# Native Address Book second contact — 2026-11-17

Base `67572e4eae2a69eba419c3f8fad9d1bb1b0cfa33`; branch
`codex/addressbook-two-contact-native`. The operator's extended campaign grant
explicitly authorized this one insertion/save and a separate read-only reopen,
disposable installation copies, development and eligible fixture publication.
No supervisor dispatch, model call, host input injection or Computer Use.

## Exact starting identity

Original A01 archival bytes remain unavailable. This trial deliberately uses
the documented **tool-generated A01 reconstruction**, not a claimed recovered
native original. From the preserved empty native database, `create_contact(empty,
Contact('TEST', 'USER A', work_phone='202-555-0142'))` produces the exact historical
A01 complete-file SHA-256. It contains only the existing synthetic contact.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Preserved empty database | 10240 | `cb890e6d7ba96fafb5a5d3991e208f4de862bee485f6ce32696e989c97d3394c` |
| [Published tool A01 source](../../tests/fixtures/application-generated/addressbook/a01-historical-match-tool-generated.adr) | 10240 | `19215ea147c65b259eb963fd240e9931d96e77f92d1001f0f7edf89024076ac8` |
| [Actual native saved pair](../../tests/fixtures/application-generated/addressbook/native-two-contact-20261117.adr) | 10240 | `c37c62bf2fb16963f910c4d4c80e395d3a42305b55e954435d30ca0f9d3cdf40` |
| Independent saved-installation reopen | 10240 | `c37c62bf2fb16963f910c4d4c80e395d3a42305b55e954435d30ca0f9d3cdf40` |
| [Tool-generated reproduction](../../tests/fixtures/application-generated/addressbook/second-alpha-tool-generated.adr) | 10240 | `c37c62bf2fb16963f910c4d4c80e395d3a42305b55e954435d30ca0f9d3cdf40` |

The native fixture is the actual unchanged extracted application output. The
equal generated fixture remains **tool-generated**, with no separate native
run of that duplicate. All three public binaries have reviewed synthetic
contents, manifest entries and REUSE sidecars; commercial inputs/screenshots
remain private. Fixtures remain Git-only, excluded from wheel/sdist.

## Preparation and serialized action ledger

The preserved Address Book installation disk is SHA-256
`d7f117f2521acc1aac2676126d61abf933df5c710ab8ba8446ad9bfd59342ba4`.
A fresh clone replaces only the existing five ADR clusters with A01; no FAT
allocation, disk formatting or original modification. Independent FAT16
traversal and 7-Zip extraction agree before launch and after termination.
All **143** installed files are hashed before/after; the older runbook's 126-file
count does not describe this actual installation. Before-open disposable disk:
`fd2e3a97f63655f55e72893a246cf176e63c95291ebfd64fe889392dad405c6a`.

An initial preparation stopped before launch because config/NVRAM backups were
beside, not inside, the archived closed-disk folder. Its partial clone was
retained unchanged. Corrected trial **insert1** used a new independently named
clone. The failed preparation sent no guest input and performed no native save.

The emulator/hardware pins match the controlled Calendar campaign: 86Box source
`855258da966f1594f568350be59e8e1eca082ed1`, executable
`e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d`,
ROM checkout `908394b690f7da28f47727d9876774fd672c4ed3`, Tandy 1000 RSX,
i386SX 25 MHz, 4096 KiB, no dynarec, disabled host RTC sync, disconnected guest
network profile, no mounted floppy/CD. Original ADDRESS.PDM hash is
`ef685b20e259f0932378668d9b120882468dc0da157a015e2df95d4ce61a60fb`.
Visible held-at-zero launches, seed 1, `--nohook`, authenticated loopback **8902**,
exclusive connection/listener checks, reset and clock/frame continuity guards.

| Checkpoint | Native action/observation | Emulated ms / frame |
| --- | --- | --- |
| Open, PID 5404 | Boot 12000; VER +300; CD DESKMATE +300; DESK ADDRESS +6000; original TEST USER A and phone visible, total 1 | 18816 / 1243 |
| Menu | F5 +300; Enter +500 did not activate an unselected menu item; extended Down +200 selects Add; Enter +500 activates it once | 20332 / 1334 |
| First | Tab, verify First Name; type ZULU; Tab, verify Last Name | 20972 / 1372 |
| Last/City | Type ALPHA; Tab to blank Address; Tab to blank City; Tab to blank State | 21824 / 1423 |
| Work | Three Tabs through blank ZIP and Company to verified Work Phone; type 555-0100; inspect complete card | 22768 / 1480 |
| **Only save** | Escape +300; inspect “Save changes to this record before quitting?” with YES selected; Enter once +1000; DOS prompt | 24076 / 1565 |
| Collect | Native socket quit; Windows process-handle termination verified; copy/extract whole disk | 24076 / 1565 |
| Reopen, PID 11196 | Exact stopped saved disk/config/NVRAM copy; same boot/VER/CD/launch | 18816 / 1243 |
| Read both | Extended Down +500 selects USER A, original fields/phone visible; extended Up +500 selects ALPHA, ZULU/ALPHA/555-0100 and blank City visible | 19824 / 1303 |
| Close | Escape +1000 directly to DOS without save prompt; native quit, verified termination, offline extraction | 20828 / 1372 |

The initial reopen framebuffer showed ALPHA selected and its new phone while
the name fields still displayed TEST/USER A. After the two read-only selection
changes both cards displayed correctly. This is a **native initial repaint
anomaly**, not a reason to silently claim the first framebuffer was consistent.
No corrective edit/save was performed. Whole ADR bytes remained unchanged.
Total measured elapsed emulated time: **44904 ms**; guest wall-clock delta not
independently measured. No uncertain mutation replay.

## Native byte findings

Exactly **63 byte positions** change; page deltas 0–9 are
`[0,2,0,0,57,4,0,0,0,0]`. All predeclared
[Phase II trial](database-phase-ii.md) predicates pass in the independent raw
diagnostic; `unrelated_changed_offsets` is empty:

* Old ID 16 remains at `0x1000`, all 61 bytes unchanged.
* New ID 17 is physically appended at `0x103D`, exactly **56 bytes**, with
  sixteen fields and the predicted Birthday/Anniversary/`n` defaults; marker
  `03` is at `0x1075`.
* Index triples at `0x1428` are **`(4,61,17),(4,0,16)`**: ALPHA before USER A,
  opposite physical insertion order. All four routing keys remain sentinel.
* DATA count becomes `00002`, next ID `00018`; opaque token `000`, sort
  ordinals `3,2`, header, schema, NAMES, CONFIG and all unrelated bytes stay exact.
* Only PERSONAL.ADR changes among 143 installed files; the separate reopen
  changes no installed-file bytes. Config/NVRAM and disk timestamp changes are
  retained separately in the [sanitized receipt](../evidence/addressbook-two-contact-native-20261117.json).

This native pair supports the source-predicted LastName ordering and append
allocation. It contradicts first-name-only or insertion-order indexing for this
pair, but does not establish secondary FirstName ordering, ties, punctuation,
case equivalence, DOS collation-table contents, split behavior or larger books.
The [previous static trace](addressbook-insertion-trace.md) supplies separate
conditional source evidence for full LastName/FirstName comparison.

## Small supported writer

`addressbook.experimental_second.append_second_contact(source, contact,
experimental=True)` requires the **exact A01 hash**, LastName **ALPHA**, blank
City, and `Contact`'s existing printable-ASCII first-name/phone width constraints.
It appends ID 17, indexes it before USER A, updates only the two counters and
preserves all other bytes. The original empty-to-one API still rejects nonempty
input; arbitrary last names, ties, third insertion and page growth remain closed.
First-name/phone variations are offline demonstrations only; the native trial
is exactly ZULU/ALPHA/555-0100.

```powershell
$env:PYTHONPATH='src'
python tools/experimental/append_addressbook_second.py `
  tests/fixtures/application-generated/addressbook/a01-historical-match-tool-generated.adr `
  NEW-second.adr --experimental
```

This command reproduces every byte of the actual native saved fixture without
loading it. `write_second_contact` atomically creates a new destination and
refuses overwrite. Portable tests use the actual public source/native pair,
fixed-offset independent serialization/index prediction, the earlier independent
trial diagnostic, width extremes, malformed source routes/locators/counts/schema,
explicit opt-in, immutable sources and no-overwrite checks.

Private complete disks/trees, setup failure, source pins, action/capture receipts,
config/NVRAM and independent reports are preserved under
`C:/DeskMateLab/private-evidence/addressbook-two-contact-20261117`.
The next useful native trial is a separately identified equal-last-name pair
with long shared FirstName prefix, to test secondary comparison beyond the
ten-byte routing prefix. General multicontact writing is not inferred here.

The frozen private native evidence index covers **658 files**, SHA-256
`1be76444e5a360adfe54f1c5cf1918fa467dd324a81539e25734674aca5db2ae`.
It includes the failed preparation, complete before/after disk and installed
trees, config/NVRAM, all guest action/capture and launch receipts, plus the
independent raw diagnostic and private experiment scripts. Validation logs and
the worktree-specific installed-wheel environment are preserved separately.

## Validation

With this worktree's wheel installed in its own private Python 3.13.17
environment, **448 full portable tests passed in 908.781 seconds**. All **14
Address Book tests** passed separately, including six new native/independent
writer tests. Deployment: **31 run, two platform skips**. Ruff, REUSE,
wheel/sdist builds, installed-wheel import/CLI checks and repository/package
audits passed. An isolated import confirmed the installed second-contact module
belongs to this environment and is byte-identical to this worktree's source.
Direct archive inspection verifies no `.adr`/`.cln` binaries ship in wheel/sdist.
GitHub CI is reported separately after push; these are local results.
