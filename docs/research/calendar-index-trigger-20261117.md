# Calendar index open/close controls — 2026-11-17

Base `67572e4eae2a69eba419c3f8fad9d1bb1b0cfa33`; branch
`codex/calendar-native-index-campaign`. This extended campaign was explicitly
authorized by the operator, including sequential disposable native experiments,
source development and publication of checked synthetic files. No additional
model session or supervisor dispatch was used.

## Native observations

| Control | Actions after verified boot | Calendar result | Elapsed emulated ms |
| --- | --- | --- | ---: |
| A | `VER`, no DeskMate launch; native quit | Whole disk and all 143 installed files unchanged | 12328 |
| B | Set date/time, open Calendar, observe October 23 schedule, Escape to DOS, native quit | Only 237 bytes on index page 5 change; `[41,21,0,0]` becomes `[20,21,21,0]` | 20940 |
| F59 | Same no-dialog open/close, separate 59-appointment forward-insertion candidate | Only 226 bytes on index page 5 change; `[41,19,0,0]` becomes `[20,21,19,0]` | 20940 |
| I | Original month input; stop emulator while initial schedule remains open, no Escape | Whole disk and installed files unchanged | 19936 |
| J | Same as I, plus 1004 ms idle time to match B's total elapsed time, no Escape | Whole disk and installed files unchanged | 20940 |

**An event edit, change dialog, explicit save and second-calendar creation are
unnecessary for the observed rewrite.** Control B does not separate opening,
initial schedule display and closing internally. Calling it an observed
open-time rewrite alone would overstate the sampling. Controls C/D/E were
conditional on B leaving the index unchanged and were therefore unnecessary.
Total measured emulated time for these five processes: **95084 ms**. This
includes time advanced around socket keyboard commands; guest wall-clock
delta was not independently measured.

Both open/close trials displayed the expected October 23 synthetic schedule:
LPHa124 09:00–10:00, Plan 01 09:30–10:15, Review 01 14:15–15:15.
Neither trial entered an event dialog or submitted a save. After Escape, the
DOS prompt was observed before native socket quit. Each owned PID's termination
was verified with a Windows process handle before copying or extracting disks.
PIDs were A **8200**, B **12848**, F59 **13132**, I **8196**, J **10200**,
serialized on loopback **8901**. I/J deliberately use native emulator quit
while Calendar remains open instead of a DOS exit; these are disposable
power-off timing controls, not clean application closes. Their last captures
show the expected schedule. Their stopped disks remain byte-identical to the
input disk, including J at **20940 ms**, matching B's total elapsed time.
Thus initial open/display and matched idle time do not produce a **durable**
rewrite in these controls. This does not exclude a dirty in-memory rebuilt
index that is only flushed during close.
No Computer Use, host input injection, RAM capture or uncertain-operation replay.

## Exact published bytes

All four files below are 8,192 bytes. Native outputs are **actual unmodified
application-written synthetic bytes**, extracted after emulator termination,
not generated replicas. Tool input provenance remains distinct.

| Calendar | SHA-256 |
| --- | --- |
| Existing 61-appointment tool input | `d35b10c8e8f0b04e41cd6d16a27b9825531353b00ab503e94b7abd3a11499106` |
| [B native open/close](../../tests/fixtures/application-generated/calendar/native-30-day-open-close-20261117.cln) | `8ba8a9b45fe2da1f0c685a4b1b0e3a8ad0c1672bc8429390d2e456f5acc99b8d` |
| [F59 tool input](../../tests/fixtures/application-generated/calendar/sdk-29-days-forward-tool-generated.cln) | `74ef8274793da77faf3cca6afe15cf4631f3ae4fa025b579a019a514e73e852f` |
| [F59 native open/close](../../tests/fixtures/application-generated/calendar/native-29-day-open-close-20261117.cln) | `90fb11730967dc3957c6f8a33313073a20de0fc9916efd94164e661046ccf2e7` |

F59 generation from exact published E02 (`0af0896163c24c992fa515ddca8c45a31496250d6ba84c9f08e28020a07fe0d9`):

```python
from dataclasses import replace
from deskmate_formats.calendar.experimental_new import build_new
from deskmate_formats.calendar.samples import schedule
events = tuple(replace(e, description=e.description + ' / allocator trial')
               for e in schedule(days=29))
candidate = build_new(e02_bytes, events, experimental=True)
```

This preserves original LPHa124 and adds 58 ordinary occurrences. Unlike the
61-appointment input, the additions are inserted in forward order. Count and
physical order both differ, so the trial does not independently isolate their
effects; it shows the same split transformation on this second exact profile.

## Environment and custody

A and B each start with a byte-exact copy of the prior campaign's preserved
before-open disk SHA-256
`4c835a9acd5734ffac89cc1878cbb11afc8fdbf4b5d83c37ae010c711459c5e8`.
F59 replaces only the existing four Calendar clusters on another copy; no FAT
allocation, formatting or original-media mutation. Before every launch, offline
FAT16 traversal and independent 7-Zip extraction agree on the installed Calendar.
All 143 installed files are hashed. After every process exit both extraction
methods agree again. Full disks, installed trees, configs/NVRAM, native captures,
commands and per-action millisecond/frame receipts remain private under
`C:/DeskMateLab/private-evidence/native-index-campaign-20261117`.

Build/ROM/hardware pins are the same as the
[previous controlled save](calendar-native-save-20261117.md): 86Box source
`855258da966f1594f568350be59e8e1eca082ed1`, executable
`e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d`,
ROM checkout `908394b690f7da28f47727d9876774fd672c4ed3`, Tandy 1000 RSX,
i386SX 25 MHz, 4096 KiB, no dynarec, disabled host RTC sync, disconnected guest
network profile, no mounted floppy/CD. Each visible launch starts held at 0 ms
with seed 1 and `--nohook`; exclusive socket ownership, reset identity and
clock/frame continuity are checked. Config/NVRAM are copied separately for
every trial and their exact before/launch/after hashes are in the
[sanitized receipt](../evidence/calendar-index-trigger-20261117.json).
NVRAM and emulator-written config bytes changed; no claim of byte-invariant
machine state is made. Original evidence/media remain unchanged.

## Independent byte explanation

A raw oracle, independent of the production reader, writer and prefix helper,
predicts both complete output files from input bytes alone:

1. Preserve all bytes outside index page 5.
2. Split the first 41 locators into the first 20 and remaining 21.
3. Shift the prior second subdivision unchanged into subdivision three.
4. Zero each subdivision's unused tail; leave subdivision four empty.
5. Replace only route zero with the ten-byte sort-field prefix of locator 19's
   target row; retain the three `FF`×9/`00` sentinel routes.

Both native outputs equal this oracle byte for byte. All logical locator
triples, IDs, row addresses, payloads, counters, schemas and allocation bytes
are unchanged. B's index page also equals the prior native empty-SECOND and
native description-save index pages exactly. Route zero is
`8f6b80016801b901bd01` in both new trials, despite different endpoint IDs and
physical addresses. It is derived from endpoint **fields**, not ID/address:
encoded date, day-of-week, start and end fill the ten bytes before Description.

The pinned static findings in the
[multicalendar study](calendar-multicalendar-reader-writer.md) explain a 41-slot
split at byte 120 with a 126-byte suffix, and route construction from the new
left group's last row. They support the measured transformation, not a general
rebalance algorithm or proof of loaded runtime call targets. The earlier
UPDATE_ROW path remains relevant even without a user edit. Reverification of
the existing [SDK crosswalk](sdk-calendar-database.md) pins Calendar's table-close
path: `A101` calls the three-column config updater `9F6D`; `9FBF/9FC3` submit
selector 19 through wrapper `CDF8`, with a null old values pointer (`9F93`) and
verify 0 (`9FB3`), before selector 9 table close at `A12C`. This is separate from
the six-column user event update at `B22F..B2C1`.

The pinned UPD code checks the last locator at subdivision offset 240 (`2A59`),
calls that full-slot guard at `2197`, reaches split helper `2A72` at `21B3` and
route rebuild `284A` at `21D2`. Existing half-copy anchors explain the 20/21
split and whole-subdivision shift. Six opt-in private source tests now pin these
source relationships, including new close/guard checks. Original resources and
selected disassemblies stay private. These are conditional static paths, not
observed loaded runtime targets.

The best-supported explanation is **a native index-maintenance split of a full
first subdivision associated with clean Calendar close**, rather than equal
three-way balancing or a required event edit. The close-path configuration-row
update is the strongest source-supported explanation: it can invoke index
maintenance while leaving the configuration payload unchanged. I/J narrow the
durable-write boundary but do not distinguish earlier in-memory rebuilding from
close-time writeback. General split selection, multiple full groups, cascading
splits, K collation and loaded runtime call tracing remain open.
