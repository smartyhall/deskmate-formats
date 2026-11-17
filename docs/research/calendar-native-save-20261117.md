# Controlled 30-day Calendar edit/save and reopen — 2026-11-17

**Observed:** original DeskMate 03.05.00 saved one declared description edit
in the exact published 61-appointment month Calendar. A read-only reopen showed
the saved description, times and unchecked Alarm. The reopened Calendar bytes
equal the after-save bytes. Offline checks preserve all other 60 appointments,
the configuration row, all logical locators, IDs, row addresses and row lengths.

This campaign was directly authorized through the existing interactive Codex
session, including one bounded guest edit/save and a read-only reopen. It did
not accept or dispatch the S3 revision-2 task, invoke another model, investigate
Windows sandbox attempt 05, or establish native S3 editing compatibility.
Base repository: `93e164f4827f2f08685ada512f65924280a756aa`.

## Exact bytes and independent oracles

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Published tool-generated input | 8192 | `d35b10c8e8f0b04e41cd6d16a27b9825531353b00ab503e94b7abd3a11499106` |
| [Exact native saved fixture](../../tests/fixtures/application-generated/calendar/native-30-day-edit-save-20261117.cln) | 8192 | `4b59c4f30ba21260df8159ac8758077858f1f516efbfc95365c7a5096ccab970` |
| After read-only reopen | 8192 | `4b59c4f30ba21260df8159ac8758077858f1f516efbfc95365c7a5096ccab970` |

The new file is **application-saved synthetic content**, derived from the
tool-generated input. It is not a generated replica. The actual independently
checked binary is committed with its REUSE sidecar and manifest entry. The
original candidate and native two-calendar specimens are unchanged.

The independent whole-file oracle uses only prior published specimens: copy
the input, replace its index page 5 with page 5 of native empty-SECOND specimen
`338487558d9992452db15858de1ba9cf790c26abf990ba70b47bbc9dc8d011f5`, and
replace the unique `Plan 01 / allocator trial` with `Plan 01 / allocator saved`.
The resulting bytes equal the complete saved fixture. This does not use the
production parser, writer, value codecs or saved-file bytes to construct the
expected result.

## Disposable environment and preservation

The operator-confirmed ESXi snapshot **Lab Provisioned** was the accepted lab
rollback. No networking, Windows accounts, antivirus or existing S3 custody
records were changed. No 86Box process was present at preflight. Original disk,
installed tree, configuration, NVRAM, emulator build and ROMs were opened only
for reading and hashing. The complete original 143-file DeskMate tree was
extracted privately before preparation.

The new disposable machine `rsx-calendar-campaign-20261117` used a copy of the
previously verified E02 closed disk. An offline FAT16 installation extended only
PERSONAL.CLN's three-cluster chain by one FAT-free cluster (1178), updated both
FAT copies and the directory size, and wrote the published input. No disk was
formatted. Independent FAT traversal and 7-Zip 26.05 extraction agreed on all
8192 installed bytes. The 143-file installed-tree comparison showed only
PERSONAL.CLN changed. Whole-disk snapshots and full manifests were retained
before open, after save and after reopen. Original source pins were preserved.

| Pin | Identity |
| --- | --- |
| Original E02 disk | `c013712c0cda7628a5a3138047a7d0e9b631098c5c72d41d5b8f717a6f90a281` |
| Before-open disposable disk | `4c835a9acd5734ffac89cc1878cbb11afc8fdbf4b5d83c37ae010c711459c5e8` |
| After-save disk | `37b3cd4ec3ab6d482273998f66abb0bda04d009e3afc2bf2984651161fb9b003` |
| After-reopen disk | `924d2ce64c553e45aa2de7607de763f7329eb033a81f3d3e09bc4abbd1884f31` |
| 86Box source | `855258da966f1594f568350be59e8e1eca082ed1`, clean |
| 86Box executable | `e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d` |
| Build cache | `bdbc3adcd6f55928050039e008eebb2e0b789f7b52ef39377ee42186252602f5` |
| ROM checkout | `908394b690f7da28f47727d9876774fd672c4ed3`, clean |
| RSX BIOS | `17984fe7c31ab6b51c96272ba8ee89580eb139aab01399a1b865f6743f3334f2` |
| CALENDAR.PDM | `819df5658b663aa69b15584abf805062679e97f587f3404738f6e82876e4bd23` |

Configuration: Tandy 1000 RSX, i386SX 25 MHz, 4096 KiB RAM, no dynarec,
internal video/sound, PS/2 input, disabled RTC host sync, IDE 1024/4/26 image,
no mounted floppy/CD, inherited disconnected guest network profile. Config and
NVRAM originals and before/after hashes are private. A preparation encoding
error was corrected only in the new clone: two launcher calls failed in config
parsing before child creation. Both failures and the correction are retained;
neither delivered any guest input. The successful launch was visible and held
at 0 ms, with `--automation-seed 1 --nohook`.

## Input and observation ledger

Only the authenticated loopback native socket controlled the guest. No Computer
Use, display clicks, host keyboard/mouse injection, RAM reads, debugger or
competing controller was used. Each action group checked one expected listener
and one owned connection, held status, clock/frame continuity and reset identity.
Receipts bracket native framebuffer captures. No uncertain mutation was replayed.

Save PID **12108**, loopback port **8897**; after its verified exit, the read-only
reopen used PID **1240**, port **8898**, on a separate copy of the saved disk,
config and NVRAM. At most one emulator process was running. Both processes and
their listeners exited before offline collection.

| Checkpoint | Action | Elapsed emulated ms / frame |
| --- | --- | --- |
| Boot | Step 12000; `VER` + Enter; step 300. DOS 5.00 observed. | 12328 / 846 |
| Calendar | Set `DATE 10-23-2026`, `TIME 08:00:00.00`; query TIME; `CD \DESKMATE`; `DESK CALENDAR`. Step 300 after each command group, 6000 after launch. | 19936 / 1321 |
| Initial detail, cancelled | A nonextended keypad Down (`0x50`) did not advance selection; Enter opened LPHa124. No edit/save; Escape returned to day view. | 21376 / 1408 |
| Target selected | Extended Down (`0x150`), step 200; verified Plan 01 selected. | 21884 / 1438 |
| Original target detail | Enter (`0x1C`), step 1232. Verified all declared original fields. | 23120 / 1512 |
| Before save | Type `Plan 01 / allocator saved` into selected Description, step 300. Verified full form, unchanged date/times/alarm. | 23524 / 1536 |
| **Only save** | Enter once, step 800. Day view displays the new description. | 24328 / 1585 |
| Close | Escape, step 1000. DOS prompt observed; native quit, disconnect and verified process exit. | 25332 / 1649 |
| Reopen | Fresh sequential process: step 12000; `VER`, step 300; `CD \DESKMATE`, step 300; `DESK CALENDAR`, step 6000. Saved schedule visible. | 18824 / 1243 |
| Reopened detail | Extended Down, step 200; Enter, step 1232. Saved description, original times and alarm off visible. | 20264 / 1330 |
| Cancel/close | Escape, step 300; Escape, step 1000. DOS prompt; native quit and verified exit. **No second save.** | 21572 / 1417 |

Exact selected record: PERSONAL ID 77 (`0x4D`), Friday 2026-10-23,
09:30–10:15, `Plan 01 / allocator trial`, alarm off; empty Duration,
Protected `31`. Forty-two-byte row at `0x1E28` (page 7, offset 552).
The predeclared same-length replacement is `Plan 01 / allocator saved`.
Total measured elapsed emulated time: **46904 ms**, across two sequential
processes: 46096 ms explicitly requested as steps and 808 ms recorded around
input commands. Guest wall-clock delta was not independently measured; timestamps,
requested steps, all socket responses and captures remain in the private ledger.

## Byte-level results and evidence limits

Exactly **242 byte positions** change: **237** on index page 5, and the five
ASCII bytes `trial` → `saved` at `0x1E4B..0x1E4F` on page 7. All other bytes
match the original candidate. Header, allocation map, directory/schema, counts,
next ID, data-chain ownership and file size remain unchanged. There are no new,
deleted or retired rows. All 62 logical `(page, offset, ID)` locators remain
identical and in order, though their physical index slots move.

The index repartitions `[41,21,0,0]` → `[20,21,21,0]` and writes first finite
route `8f6b80016801b901bd01`, exactly matching the pre-existing native
empty-SECOND fixture's index page. **Calendar creation is not necessary for
this rewrite:** no calendar was created in this trial. This does not isolate
whether opening, editing or saving caused it; no pre-edit closed-file snapshot
was taken. General split selection/propagation and K collation remain unresolved.

A bounded static follow-up rehashed original **DMDBUPD.RES** (13740 bytes,
SHA-256 `9e77a2081ebb3a9549903f5d337580c65d6e0a3f603185064d4c82e16327cf4f`)
and decoded explicit entry/call windows with the existing Python 3.13.17 /
Capstone 5.0.7 environment. Offsets are hexadecimal absolute file offsets:
selector 19 (`UPDATE_ROW` in the SDK) branches at `023F/0242` to `0270`, which
calls `0BB1`; the update handler calls `1426` at `0CD7`. Within that helper,
`14A0/14AC` call the length callback thunk `33EF` (selector `0x32`). The equal
length comparison at `14E8/14EB` takes the existing-row copy branch and rejoins
at `1537` through `150F`. That path still reaches index insertion `1F8E` at
`1568`. This is source corroboration that a same-length row update can perform
index maintenance while preserving the row's address. It is **not** a trace of
the actual loaded target or proof of the repartition trigger. Private probe,
asserted branch/call anchors and disassembly hashes are retained separately
from the frozen native capture index; no executable bytes/listings are published.

All 61 appointments' decoded values/alarms were checked offline against the
source with the one declared substitution. Sixty unmodified appointment rows
and the configuration row are byte-exact at their original addresses. Only
PERSONAL.CLN changed among the 143 installed files after save. The read-only
reopen preserved the entire Calendar; whole-disk differences include DOS file
timestamps, and config/NVRAM snapshots are retained separately.

**Native visual scope:** the October 23 schedule, cancelled LPHa124 detail,
declared target detail before edit, updated schedule and reopened target detail.
This is selected-event native read/edit/save/reopen evidence, not an all-30-date
UI review, alarm-firing test, general allocator qualification, or arbitrary
multicalendar writing/selection/rename/delete support.

## Diagnostics, tests and reproduction

The old trial diagnostic rejected the saved file's finite route as `index
header`. Its independent scanner now validates all four dense subdivisions,
count, gaps, finite endpoint prefixes, target framing and existing row coverage.
It retains its documented bounded trial scope and imports no production reader
or writer. Existing Address Book and growth controls continue to pass. New
adversaries cover routing bytes, subdivision holes/tails, wrong targets and count.

Use a dedicated Python environment with the project development dependencies.
Build and install this worktree's wheel before full validation. The supervisor
tests launch `-I` children from the installed package and bind hashes of every
project Python file; `PYTHONPATH=src` alone cannot select their implementation.
An initial run used another worktree's wheel and failed its isolated-owner test.
The mismatching `calendar/personal.py` hashes, failed logs and matching-wheel
rerun are preserved privately. No supervisor code or custody record was changed.
These portable commands need no commercial inputs:

```powershell
python -m build
python tools/install_wheel.py
python tools/check_install.py
$env:PYTHONPATH='src'
python -m unittest discover -s tests/portable -p test_database_trial_report.py -v
python -c "import json; from pathlib import Path; from tools.experimental.database_trial_report import compare; p=Path('tests/fixtures/application-generated/calendar'); print(json.dumps(compare((p/'sdk-30-days-allocator-tool-generated.cln').read_bytes(),(p/'native-30-day-edit-save-20261117.cln').read_bytes(),'PERSONAL'),indent=2))"
python -m deskmate_formats.calendar.cli tests/fixtures/application-generated/calendar/native-30-day-edit-save-20261117.cln --profile sdk --json
python -m unittest discover -s tests/portable -v
python -m ruff check src tests/portable tools
python -m reuse lint
python tools/audit_repository.py
```

The fixture remains excluded from wheel/sdist. Native reproduction requires a
separately authorized new disposable clone; the ledger above is a reproducible
sequence, not authorization for a second edit. The highest-value discriminating
follow-up is an untouched candidate open/close control, with no edit/save.

Final local validation: **438 full portable tests passed in 912.079 seconds**
with a matching wheel in the private `validation/native-venv` environment;
ten focused diagnostic tests and 73 Calendar tests passed. Deployment checks:
31 run, two platform skips. Ruff, REUSE, wheel/sdist build, installed-wheel
imports/CLIs, repository/package audit and staged diff checks passed. The initial
437-test run's one source-binding failure and the superseded mismatched-wheel
retry remain archived; the corrected isolated-owner focused check also passed.

[Sanitized evidence receipt](../evidence/calendar-native-save-20261117.json).
Private archive: `calendar-campaign-20261117`; frozen native evidence index
SHA-256 `cb09ada9a6970863950ecf32a40c0c1e430d72940014533e98bd09de1cc14005`.
It indexes 641 files: exact disks/trees, setup scripts/pins, config/NVRAM backups,
action journals, native PNGs, parsed snapshots and independent diagnostics.
Private screenshots, complete installed trees, media, ROMs and credentials are
not published. Source originals remain unchanged.
