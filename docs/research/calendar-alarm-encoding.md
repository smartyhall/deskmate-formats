# DeskMate 3.05 Calendar Alarm encoding

Enabling Alarm for an ordinary timed appointment changed Protected from
`0x31` to `0x71`, a one-bit change (`0x40`). This was the only
difference between the closed Alarm trial and the closed no-op save,
even at whole-disk level. Cancellation and no-op save both preserved
the original database byte for byte.

## Source and setup

The prediction came from the Development Guide Appendix A, printed
page A-7, and the 3.05 Calendar editor code at `C6A3..C6C3`. The
Technical Reference chapter 6 and `DMDB.H` identify the update API.
The source hashes and static offsets are recorded in the SDK crosswalk.
[Calendar database crosswalk](sdk-calendar-database.md) · [SDK source identities](sdk-source-identities.md)

The November 6, 2026 run started from repository commit
`ad10303a97bdcf248ade3b6281b4f5cc19b3318c`. The common input was
`calendar-editor-20261105/disk-E02-closed/disk.img` in the private
archive. Independently extracted `DESKMATE/PERSONAL.CLN` with
7-Zip 26.05 and verified it against the archived E02 extraction. All
three disk copies were hashed independently before launch. Each clone
had its own UUID, configuration, NVRAM copy and launch credential.

| Input | Identity |
| --- | --- |
| E02 disk and each starting copy (54,525,952 bytes) | `c013712c0cda7628a5a3138047a7d0e9b631098c5c72d41d5b8f717a6f90a281` |
| E02 `PERSONAL.CLN` (6,144 bytes) | `0af0896163c24c992fa515ddca8c45a31496250d6ba84c9f08e28020a07fe0d9` |
| `CALENDAR.PDM` | `819df5658b663aa69b15584abf805062679e97f587f3404738f6e82876e4bd23` |
| `DESK.EXE` | `0f2a40243c997276904d2555a117c60eedf0016dde073285e8d63c8345a2eba3` |
| `DMCSR.R89` | `085edb2f2c67ae323343d9efedd7c731778f5fbb8dc59ed8bd6560006b45da75` |
| `DMDB.R89` | `799444bb8c04632d261f61498ba269f9352e5528718f2e0a89512bf6ef7b808f` |
| 86Box source | `855258da966f1594f568350be59e8e1eca082ed1`, clean |
| 86Box 7.0 UCRT64 Release executable | `e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d` |
| Build cache, automation enabled and GDB stub disabled | `bdbc3adcd6f55928050039e008eebb2e0b789f7b52ef39377ee42186252602f5` |
| ROM checkout and RSX BIOS `tandy-1000rsx-1-10.00.bin` | `908394b690f7da28f47727d9876774fd672c4ed3` (clean), SHA-256 `17984fe7c31ab6b51c96272ba8ee89580eb139aab01399a1b865f6743f3334f2` |
| Original profile from the prior dialog experiment | `12bb7f7699f85c1eb094bd17da5994f5fc2a0c7bc74de27117b904ce5e5d1773` |
| Starting NVRAM, backed up per clone | `a883930c6a8ed73bfbe238b7cdad519e63acea18b68f9ff1f367d6f02fd4aba2` |
| Launcher global config, all three | `ed46df650d08c87667b68731a3c8588e6d10a93a9a1393772f3972c01cd128b6` |

Native `info` reported a Tandy 1000 RSX with a 25 MHz i386SX, 4 MiB RAM,
internal video and sound, and an IDE hard disk with 1,024 cylinders,
four heads and 26 sectors. No floppy or CD was mounted. The profiles
used PS/2 input, no dynarec and disabled RTC host synchronization.
The effective clone profiles matched each other after removing the
UUID line. The following PIDs and ports identify this run.

| Trial | PID / port | Prelaunch config SHA-256 | Effective config SHA-256 |
| --- | --- | --- | --- |
| A | 9432 / 8891 | `fa9dd220bcc66355e008ae28e07d6e8c346ccb97a78c295bcd2fac10a487e08d` | `7971c16cd4c207e56ee878d287677e7b2460e7bb75aa0288d3d03279785b6322` |
| B | 7432 / 8892 | `e860fa862e3a672faae6519ac2ed8aede812aefd4801c52b964f473c811cc482` | `b3cb0e69480eb645bce4bbd1f55e073cd3fced38aa4bf36fbabe760f403ffb4d` |
| C | 1696 / 8893 | `1b681c57a6931dfac4adcecac9be9b27bfe9644d0b85ea723c7403344628c1d9` | `442ebc7fb076084688a432cdeaf980bf5574314c0f235e820f9d0159675615a3` |

## Trial sequence

Start a fresh clone per trial with the repository launcher, changing
the machine suffix and port for B and C. The launcher uses
`--automation-hold`, seed 1 and `--nohook`. It verifies a visible window
and an authenticated held clock at 0 ms.
[Native launcher and input constraints](86box-visible-operation.md)

```powershell
python tools/86box_launch.py --machine C:/DeskMateLab/machines/rsx-calendar-alarm-20261106-A --port 8891 --seed 1
```

Use the [native client](86box-client.md) to run the sequence below.
Split longer steps into requests of at most 1,000 ms. Deliver Set-1
scancodes using socket key down/up. Before and after each action
group, the Windows socket table verified listener ownership and
exclusive access. Captures bracketed the native framebuffer with held
status and reset identity checks. The latest rendered frame may
predate the held CPU. No guest RAM requests or MCP watches were used.

| Action and check | Guest ms / frame after action |
| --- | --- |
| Step 12,000 ms, type `VER` + Enter, step 300 ms. DOS reports 5.00. One hard and one soft reset, last at 613 ms. | 12,328 / 846 |
| Type `DATE 10-23-2026`, `TIME 08:00:00.00`, then `TIME` with a blank response. Step 300 ms after each command group. The query reports 08:00:00.34. | 13,440 / 924 |
| Type `CD \DESKMATE` + Enter, step 300 ms, then `DESK CALENDAR` + Enter and step 6,000 ms. Verify Friday October 23, 2026, 08:00 AM and the selected `LPHa124` appointment at 09:00–10:00 AM. Mode `0x12`, 640 × 480. | 19,936 / 1,321 |
| Enter (`0x1C`), step 1,232 ms. Verify Change Event, the complete date, both AM times, description and unchecked Alarm. | 21,172 / 1,395 |
| Tab (`0x0F`) from Description to Alarm, step 200 ms. | 21,376 / 1,408 |
| A/B wait 204 ms. C taps Space (`0x39`) and steps 200 ms. | 21,580 / 1,420 |
| Shift+Tab (`0x2A` + `0x0F`), step 200 ms. Review the complete form. C is checked, A/B unchecked. | 21,788 / 1,432 |
| A presses Escape (`0x01`). B/C press Enter. Step 600 ms. A/B return to the same day view. C shows an **Alarm Is Off** warning about the global Alarm accessory. | 22,392 / 1,469 |
| C acknowledges the warning with Enter, then steps 200 ms. The accessory setting stays off and Calendar returns to the same day view. | C 22,596 / 1,481 |
| Escape from day view, step 1,000 ms and verify `C:\DESKMATE>`. Send native `quit` while held and wait for process exit before imaging. | A/B 23,396 / 1,538 · C 23,600 / 1,546 |

Day and initial editor PNGs matched across the three siblings. The
pre-save C frame differed from the controls by 44 pixels inside the
checkbox, with identical date, times, description and focus display.
The global warning added 204 guest ms to C after the matched save
input. The exit procedure, DOS prompt framebuffer and on-disk DOS
timestamp matched across the three trials. A acknowledged native
`quit` at 23,396 ms but the first host-side process wait timed out
with the client still connected. Process and listener exit were verified
after disconnect. B and C closed their sockets before the process wait.

## Closed-image differentials

Read-only extraction on each final disk copied all 143 files in
`DESKMATE`. A separate FAT16 walk followed the directory entry and
cluster chain for `PERSONAL.CLN` and agreed byte for byte with 7-Zip.
Compared all disk bytes and all database bytes at equal length. Parsed
the indexed record with the complete date, weekday, times, description
and empty Duration as the logical key, then compared physical placement.

| Comparison | Database differences | Whole-disk differences |
| --- | --- | --- |
| E02 → A (Cancel) | 0 | `0x26EA36..0x26EA37`, `99 A9 → 04 40` |
| E02 → B (no-op save) | 0 | Same two timestamp bytes |
| E02 → C (Alarm on) | `0x1034`, `31 → 71` | Same two timestamp bytes and `0x30EE34`, `31 → 71` |
| A → B | 0 | 0 |
| B → C | `0x1034`, `31 → 71` | `0x30EE34`, `31 → 71` |

The FAT changes are the write-time word at directory entry
`0x26EA20 + 0x16`. It moved from 21:12:50 to 08:00:08 on the same
guest date, October 23, 2026. The attributes, file size, start cluster,
chain (1499–1501), both FAT copies and other directory bytes matched. All
143 file contents matched E02 in A/B. In C only the database differed.
All three closed NVRAM copies had SHA-256
`164d15b851396febc29aafca772b1c0671bad85e1cd8c9d86713f22ff4037c95`.

```text
ID 0x11 at 0x1027, length 24
E02/A/B: 80 11 8F 6B 78 01 67 01 01 A4 01 A8 01 31 01 4C 50 48 61 31 32 34 01 02
C:       80 11 8F 6B 78 01 67 01 01 A4 01 A8 01 71 01 4C 50 48 61 31 32 34 01 02
```

The configuration row at `0x1000..0x1026`, including day mode
`0x65` at `0x100D`, is byte-identical in all four files. Its index
entry at `0x1428` is `04 00 00 00 10 00`. The appointment entry
at `0x142E` is `04 00 27 00 11 00`. Both entries, both index pages,
all table descriptors and the header matched. The PERSONAL count is
2 and the next-ID candidate is 18 decimal. The DBCOLS count and
next-ID candidate stay 13 and 29. There are six pages. The PERSONAL
list marker stays at `0x103F` with 960 zero bytes after it on the page.

| Closed trial | `PERSONAL.CLN` SHA-256 | Whole disk SHA-256 |
| --- | --- | --- |
| A | `0af0896163c24c992fa515ddca8c45a31496250d6ba84c9f08e28020a07fe0d9` | `d8dc6d74768fcb2a4046fdc07c35d48db2751bc817df3b89d647517dc7500efb` |
| B | `0af0896163c24c992fa515ddca8c45a31496250d6ba84c9f08e28020a07fe0d9` | `d8dc6d74768fcb2a4046fdc07c35d48db2751bc817df3b89d647517dc7500efb` |
| C | `9233f9dee8473df2a3522386a907d262371d71b4ce1e0f71bd4c9e7764b361cf` | `9619c9e8e848f315899bcfbe431d1f47747405554f8bb13a06a6ae5adf0c373d` |

The lab's `private-evidence/calendar-alarm-20261106` directory contains
the trial driver, journals, PNGs, launch receipts, backed-up profiles
and NVRAM, closed disks, all extracted-file manifests and the two
offline verification scripts. Its `evidence-index.json` covers 680
files and has SHA-256
`f6cfbfe878f3495f81822c8b3fa54a6055e2a109f7aa29c2bf5b1949c9171ded`.
The detailed comparison has SHA-256
`40cd6d7dd1d14e3b8050bff12fd0719ec9b9d1a8d1c01a7af2d7d8eee7b51959`.

## Supported interpretation

The two literals are confirmed for this 3.05 ordinary timed appointment.
The snapshots establish persistence and stable final placement. The
experiment did not sample intermediate writes or advance to alarm
delivery time. The parser exposes the stored appointment setting for
the observed timed profile and retains the full Protected byte.
The portable regression uses a byte-exact copy of the original trial C
database, verified against the evidence index, closed-disk manifest
and disk bytes. The file has the same schema and configuration as E02
and contains one synthetic appointment. Independently assembled cases
exercise both states and unsupported values.
[Application-generated fixture manifest](../../tests/fixtures/application-generated/manifest.json)

The append writer continues to require empty Duration and Protected
`0x31` in its inputs and output. Other Protected patterns, bit 7, global alarm delivery,
and reminder, annual occasion, midnight and blank-time variants require
separate validation. Their SDK-defined signatures can serve as
predictions for later application-generated comparisons.
