# DeskMate 3.03.01 and 3.05 native comparison

November 21, 2026. Generic DeskMate 03.03.01 completed its native four-disk
installer on a clean RSX/DOS clone. Calendar, Address Book, and Text ran in
both releases. Calendar and Address Book each read and saved the other
release's small test files. Opening and closing a foreign file without a
user edit could still change bytes. [3.03.01 procedure](../ecosystem/deskmate-installation-303.md) · [3.05 procedure](../ecosystem/deskmate-installation-305.md) · [Measured evidence](../evidence/deskmate-303-305-20261121.json)

## Installation and controls

| Control | Identity or result |
| --- | --- |
| Campaign base | `1c140eac8ebea99402930ce14d1f4130d7d6714c` |
| 86Box and build | Source `855258da966f1594f568350be59e8e1eca082ed1`, 7.0 UCRT64 Release, native automation enabled. EXE SHA-256 `e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d`, CMake cache SHA-256 `bdbc3adcd6f55928050039e008eebb2e0b789f7b52ef39377ee42186252602f5`. |
| ROM and POST | ROM pin `908394b690f7da28f47727d9876774fd672c4ed3`, RSX BIOS SHA-256 `17984fe7c31ab6b51c96272ba8ee89580eb139aab01399a1b865f6743f3334f2`. POST showed Phoenix 80386 ROM BIOS PLUS 1.10.00 and DeskTop VGA BIOS 1.00 (340-005-11-Rev1.00). |
| Machine | Tandy 1000 RSX, i386SX 25 MHz, 4 MiB, internal VGA and audio, PS/2 keyboard and mouse, no network links, no attached serial device, no CD-ROM. IDE geometry 1,024 × 4 × 26. |
| DOS and clock | Tandy MS-DOS 5.00, HIMEM 2.77, host clock sync disabled. Set guest date/time to October 23, 2026, at noon before the comparison. Test time advanced only through socket requests. |
| Common starting controls | Config SHA-256 `12bb7f7699f85c1eb094bd17da5994f5fc2a0c7bc74de27117b904ce5e5d1773`, NVRAM SHA-256 `a883930c6a8ed73bfbe238b7cdad519e63acea18b68f9ff1f367d6f02fd4aba2`. The launch helper backed up the copied profile and applied its socket input settings. |
| 3.03.01 boot disk | Writable clone of the 54,525,952-byte DOS baseline, SHA-256 `6c146364c24000dbf46898eec1abd4940c3f8a3a666670bdda3aa30a01e681ec`. First clean post-reset disk SHA-256 `65df42b5e7969e3504b8d01ff9c6848453c58842c5ae8876c254edd05dc68a03`. |
| 3.05 boot disk | Separate writable clone of the November 5 E00 clean installation, same geometry and length, SHA-256 `9afd080411c37a96cdce802cb129ffe7d6e1d84fb43314add7221dc71e141df0`. |

The emulator source and build hashes match the [lab's original build
and ROM provenance](sdk-dialog-portability.md#inputs-and-controls).
Each run used a single visible, held emulator and the existing authenticated
loopback socket, with seed 1 and no host keyboard or mouse injection.
Independent guest disk images and private journals preserve the original
archives, DOS base, and 3.05 installation. Observed construction, input, and
copy wait times are guest elapsed time. The screenshots show the latest
rendered frame at each held observation.

The 3.03 installer accepted the FAT label `DESKMATE_1` after rejecting
`DESKMATE 1` with the same files. It presented the destination, three
numbered disk prompts, and reset confirmation. The earlier 3.05 install
presented four disk prompts, then required printer, CPI, and driver-copy
choices. This comparison concerns the ZIP-derived 3.03 set and the tested
five-image retail 3.05 set. The 3.03 destination contained 96 files before
launch. The 3.05 clean install contained 143. In 3.03, the first line of
`AUTOEXEC.BAT` was the new `DMCONFIG` setting. Its 92 bytes hash to
`df5884463032042720a8e74d194da8b15c304b348743e4669228037efc970fc3`.
`CONFIG.SYS` remained 71 bytes with SHA-256
`0b1574c75cf4c4b0f5b25ffa1c14f307098e292002e2b7e10232e15e8080c7c6`.
[3.03 media and prompts](../ecosystem/deskmate-installation-303.md) · [3.05 install receipt](calendar-editor-observatory.md#media-and-disposable-installation)

Neither personal database was in the 3.03 hard-disk destination after
installation, though both were present in the ZIP sets. The installer
also omitted `DESKTOPD.CFG`. All 96 installed DeskMate files matched
the bytes of a same-name media member. By the first Calendar view, the
3.03 installation contained a new `DESKTOP.CFG` and `PERSONAL.CAL`.
First use of Address Book added `PERSONAL.ADR`. Later Calendar and
Address Book sessions sometimes changed `DESKTOP.CFG` as well.
The 3.05 control already had both shipped
personal databases before either application opened. The commercial
modules differed across releases:

| Module | 3.03.01 bytes / SHA-256 | 3.05 bytes / SHA-256 |
| --- | --- | --- |
| `DESK.EXE` | 16,384 / `702a5f6237695793a773a327b2b9bedc706cce3d16a52360aa90c4f13f67066a` | 19,047 / `0f2a40243c997276904d2555a117c60eedf0016dde073285e8d63c8345a2eba3` |
| `DMCSR.R89` | 79,983 / `b756c00bf3c9320819a8ae763bb6866cdaf4f2e902e1fd50aa0c17c2e44580a9` | 80,911 / `085edb2f2c67ae323343d9efedd7c731778f5fbb8dc59ed8bd6560006b45da75` |
| `DMDB.R89` | 1,117 / `5051e8d298e9a282430fa2bb21897880cc891d1d983847b5d28894d05c33e6a5` | 1,109 / `799444bb8c04632d261f61498ba269f9352e5528718f2e0a89512bf6ef7b808f` |
| `CALENDAR.PDM` | 72,211 / `53f780566d0966317db0693e6e0932052aa637a1146fe4999aefc25b905ce8ee` | 72,593 / `819df5658b663aa69b15584abf805062679e97f587f3404738f6e82876e4bd23` |
| `ADDRESS.PDM` | 53,923 / `127bf102fdd2371c0a020beb99e1a59f1122d83b8c4e1d47f7dff2ecbd324ff1` | 61,025 / `ef685b20e259f0932378668d9b120882468dc0da157a015e2df95d4ce61a60fb` |

The two experiments each used the release's own runtime and application
modules. Binary mixing and runtime ABI compatibility were outside the trial.
[3.05 binary identities](sdk-source-identities.md)

Both installed inventories include Draw, Filer, Form Setup, Hangman,
Mail Merge, PC-Link, Telecom, and Worksheet. The 3.03 destination also
contains `PC_DEMO.PDM`, which is absent from the 3.05 control. The 3.05
control includes separate `*.FF1` font files and `DMDRWPRT.ACC`.
These are installed-file facts. The campaign did not launch the PC-Link
demo, or exercise the changed Draw and printing resources.

## Desktop, menus, and dialogs

At the same date and VGA mode, 3.03.01's saturated blue desktop put
three shortcut buttons along the top with Programs on the right, a
text-panel Teach Me, and an empty Autoconfig panel. The teal 3.05
desktop arranged four shortcuts on the right, added Quick Load,
put Programs at lower left, and used a Teach Me icon. F7 opened
Desktop in both builds. The label **Createauto** appeared in 3.03
where 3.05 displayed **Create quick load**. The tests observed the
menu labels and default layout. They did not establish equivalent
behavior for creating a shortcut.

`DESK CALENDAR` and `DESK CALENDAR.PDM` at DOS reached Desktop
in the 3.03 configuration. Desktop File → Run accepted the full
`CALENDAR.PDM` name with a blank Data file, and Escape from Calendar
returned to Desktop. In 3.05, `DESK CALENDAR` at DOS ran Calendar
directly, and Escape returned to DOS. Desktop File → Run in 3.03
allowed entering a program, a data file, and a Normal/Fast CPU choice.

The populated Calendar day view and Change Event dialog had the same
control placement and labels in the matched October 23 states. In
3.03, Enter opened the day from the month grid but a subsequent Enter
on the highlighted appointment left the schedule in view in this
trial. Event → Change and Ctrl+C both reached the editor. In 3.05,
Enter opened Change Event directly from the highlighted schedule row.
The Address Book form used the same inline Title, First, Last, work
phone, dates, and membership fields in the measured states. Both
showed a save-before-quitting confirmation on a changed card. The
surrounding background was blue in 3.03 and teal in 3.05.
The matched Calendar editor frames differed only in the two-pixel-wide
caret region. The matched Text Open File and Save File frames were
pixel-identical.

## Calendar

The shipped 3.03 `PERSONAL.CAL` and 3.05 `PERSONAL.CLN` are the same
6,144 bytes (SHA-256 `c556b7f57102fc5432ce926317c8c0aa95cf8992d7fb64a72e2f270e4c517890`).
They start `03 46 49 4c`. The first 3.03 application-generated file
differed from the shipped file at `0x0015` only (`01 → 00`).
The 3.03 interface used the October 23 month cell, Event → Add, and
a 09:00–10:00 AM appointment with description `LPHa123` and alarm
clear, matching the historical 3.05 E01 test. Use Tab twice after
entering `0900` to reach End Time and twice after `1000` to reach
Description. Enter accepted the dialog. The edit replaced only
the final `3` with `4`. Ctrl+R then offered **This event only**,
which removed the selected entry on confirmation.
[Matched 3.05 E00–E02 experiment](calendar-editor-observatory.md#native-database-reproduction)

| 3.03 native stage | Held checkpoint | Byte evidence compared with 3.05 |
| --- | ---: | --- |
| First open before adding | 432,542 ms | Empty visible appointment set. One header byte differs from the shipped default. |
| Add, inspect day, exit | 436,754 ms | E01 differs at just `0x100d`: `65` in 3.03, `63` in the historical 3.05 save. |
| Edit, then exit | 446,220 ms | The sole change from 3.03 Add is `0x103c`, ASCII `3 → 4`. The resulting file is exactly the 3.05 E02 fixture. |
| Remove, then exit | 459,212 ms | Relative to the edit, 30 positions revert. Compared with the first-open 3.03 file, only `0x0015` remains different. 3.05 Ctrl+R and exit produced identical bytes. |

The inserted event is framed at `0x1027`, has ID 17 and a 24-byte
span before the `03` terminator at `0x103f`, and registers
`(4,39,17)` at `0x142e` as three little-endian words. Removal
restores the marker at `0x1027`, clears that index triple, and
reverts the measured counts at `0x0439` and `0x0443`. The
description survives as literal mixed-case ASCII and the packed
date and time bytes agree with the 3.05 sample. The one configuration
byte at `0x100d` is distinct from the appointment payload. The
historical 3.05 E01 trial exited from month view, whereas this 3.03
trial exited from day view. The comparison therefore does not
attribute that byte to release alone. [Calendar format notes](../formats/calendar/CALENDAR_FORMAT.md)

## Address Book

The shipped 3.03 and 3.05 `PERSONAL.ADR` are byte-identical
10,240-byte files, with leading `03 00 00 00` and SHA-256
`cb890e6d7ba96fafb5a5d3991e208f4de862bee485f6ce32696e989c97d3394c`.
The first 3.03 application-generated empty book differs at 64 bytes
`0x2009–0x2048`. At that offset the short `Me`/ `All`
configuration row ends with `01 02 03` followed by padding.
The shipped form has an additional comma-and-number field before
the row terminators.

The test reproduced the 3.05 A01 contact with blank Title, First
`TEST`, Last `USER A`, and Work Phone `202-555-0142`. Select
Address → Add, then Tab through the fields. A fast input burst
lost part of the telephone number in the 3.03 run. After inspecting
the visible prefix `202`, the missing suffix was typed with
160 emulated ms between characters. Escape prompted to save, and
Yes saved once. On reopening, Tab from Index reached Title and
Tab again reached First Name. End and `LONG` grew First Name to
`TESTLONG`; Escape and Yes saved. Ctrl+D from the Index and OK
removed the contact. [3.05 A01 and A02 controls](addressbook-phase1.md)

| 3.03 native stage | Held checkpoint | Byte evidence compared with 3.05 |
| --- | ---: | --- |
| Empty, before typing | 465,668 ms | A newly created database with the shorter configuration row. |
| Add and save | 474,862 ms | 66 bytes change relative to the empty file. The sole difference from 3.05 A01 is the same 64 configuration bytes. |
| Grow First Name and save | 485,198 ms | The contact grows from 61 to 65 bytes. The full configuration row appears. All 10,240 bytes match the independently saved 3.05 A02 digest. |
| Delete and exit | 494,946 ms | The row, index entry, and count revert. Both releases returned all bytes to the shipped empty database, including its longer configuration row. |

In both releases the one-contact row occupies `0x1000` with ID 16,
preserves the sixteen delimiter-separated fields and literal ASCII
name and phone, and uses index entry `(4,0,16)` at `0x1428`.
The inserted row follows the 3.05 A01 field layout, including
its Birthday, Anniversary, and final `n` defaults. The test
separates behavior of the first generated configuration from the
shared contact representation. It does not establish the meaning of
the extra configuration field or the supported maximum field widths.
[Address Book format and codec](addressbook-codec.md)

## Cross-version opening and saving

Both native apps opened byte-verified disposable copies under their
target release's expected basename and extension. In particular,
copying between `PERSONAL.CAL` and `PERSONAL.CLN` only changed the
filename before the target app ran. The test observed the appointment
and contact data before quitting without an edit, took a second disk
snapshot, then reopened and saved the specified changes. It did not
test opening unrenamed foreign extensions through a pick list.

| Direction and input | Open and close without editing | Explicit native edit and save |
| --- | --- | --- |
| 3.05 → 3.03 Calendar, E01 | `LPHa123` and its times displayed. Only `0x100d` changed, `63 → 65`; the result matched the native 3.03 Add file. | Description `LPHa124`; exact match to 3.05 E02. |
| 3.03 → 3.05 Calendar, 3.03 Add | Opened in day view and displayed the correct appointment. Opening, opening/canceling Change Event, and closing left the database byte-identical. | Description `LPHa124`; exact match to 3.05 E02. |
| 3.05 → 3.03 Address Book, native two-contact fixture | Displayed both synthetic contacts and their phone numbers. Selection with Down and Up worked. The book remained byte-identical after exit. | Changed `ZULU` to `ZULUX`. 38 byte positions changed in the page containing the second physical row; the index bytes and first physical row were unaffected. |
| 3.03 → 3.05 Address Book, 3.03 Add | Displayed `TEST USER A` and `202-555-0142`. Exit without a user edit produced the exact 3.05 A01 bytes, changing only the 64 configuration bytes. | Changed `TEST` to `TESTLONG`; exact match to the independent 3.05 A02 result. |

These are bidirectional acceptance results for the tested states.
A no-edit session can change configuration while leaving application
data intact. The experiment did not isolate whether the 3.03
Calendar rewrite and the 3.05 Address Book rewrite occur on load,
navigation, or exit.
[3.05 two-contact fixture and index](addressbook-two-contact-native-20261117.md)

## Text and file dialogs

Both editors started with an untitled ASCII buffer and the same
File, Edit, Text, Search, Layout, and Picture menus. Typing `ALPHA`,
Enter, and `BETA` showed the same nonprinting line-end indicator.
File → Save as opened the same compact filename dialog, and entering
`MATCH` created `MATCH.DOC` in both releases. File → Open
showed the `DOC` extension field, the document list, drive entries,
and OK and Cancel. The saved files are identical, 13 bytes
`41 4c 50 48 41 0d 0a 42 45 54 41 20 1a`. This exercised the
plain-text profile. Formatted inline codes, embedded pictures, and
native File → Open across versions need separate controls.
[3.05 Text byte profiles](text-native-20261117.md)

## DeskMate 3.02 stretch experiment

A separate clean RSX DOS clone ran the generic 03.02.00 set after a
manual hard-disk copy. The archive instructions mistakenly list
`dm300dk*` filenames. The verified inputs are `dm302dk1.zip` through
`dm302dk3.zip`. The reconstruction tool generated three 720 KiB FAT12
images with member counts 25, 17, and 38. [TVDog 3.02 instructions](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm302dsk.txt) · [Archive identities](../ecosystem/deskmate-installation-media.json) · [Image hashes and native receipt](../evidence/deskmate-303-305-20261121.json)

Create `C:\DESKMATE` and use `COPY A:\*.* C:\DESKMATE` for each
disk in order, waiting for DOS to report the copy count before each
swap. This produced 78 unique installed files. Disk 3's `DESKTOPD.CFG`
overwrote Disk 2's different copy. The repeated `DMDB.RES` was
identical. Eject the last disk, append `SET DMCONFIG=C:\DESKMATE` to
`AUTOEXEC.BAT`, boot DOS again, verify the value with `SET`, change
to the installation directory, and run `DESK`. The launcher displayed
03.02.00, SHA-256
`ceafb18e3949f4b3f44a2ab2565e9450ff3ff025a3cfd8055eaf908834dfa61b`.

The socket acknowledged a Ctrl+Alt+Del request on the first run.
The reset counters and console showed no reboot, and the two apps
created their personal databases at the C: root. A second, cold launch
verified that DOS applied `DMCONFIG` and that both apps initialized
separate defaults in `C:\DESKMATE`. The saved root files retained
their hashes. First run elapsed 272,469 emulated ms, and cold
verification elapsed 35,786 emulated ms.

The 3.02 Desktop uses a patterned background, five file panels across
the top, and a calculator at lower left. Help appears at upper right,
with date and time grouped on the left. Desktop File → Run required one
Down press because it skipped disabled Get Info. The 3.03 two-Down
sequence selected Copy and produced a same-filename error. The
Calendar month grid and Add Event controls were already present.
Address Book showed the same card and index structure, with shorter
Work and Home labels and without the later dotted field guides.

Calendar wrote the same `LPHa123` appointment. The 3.02 first-open
and one-appointment files each differ from their 3.03 counterpart
only at `0x0018`, `43` in 3.02 versus `57` in 3.03. The Calendar
reader extracts the same appointment. The 3.02 Address Book wrote the
same contact and index bytes as 3.03. Its declared DATA widths are
**5 versus 10** for Title and **38 versus 43** for Address. The other
DATA column definitions match. The common container reader extracts
the 3.02 rows. The schema-specific Address Book reader rejects the
older DATA schema. Native interchange with 3.02 remains to be tested.

## Published samples and visual provenance

The [fixture manifest](../../tests/fixtures/application-generated/manifest.json)
records actual application output recovered independently by FAT16
traversal and 7-Zip, with size, SHA-256, and expected synthetic values.
The deleted Address Book bytes are identical to the shipped empty file
and are represented by its digest in the evidence. The two plain Text
saves share one published specimen.

The [image manifest](https://github.com/smartyhall/deskmate-formats/blob/main/website/reference-images.json) records the
captions, alt text, original frame hashes, and derivative hashes.
Every illustration is a native guest capture. The release banner,
destination, and reset crops keep original pixel scale. Full views
were re-encoded without altering visible pixels. The evidence receipt
ties each published frame to its emulator mode and emulated time.
Raw screenshots, disks, and socket receipts are preserved privately.

## Outstanding tests

1. Hold and extract the working file immediately after entry, then
   after each action and after exit, to locate each configuration rewrite.
2. Cross-open Calendar at allocator and index boundaries, then check
   recurring events, multiple calendars, alarms, and non-ASCII text.
3. Measure Address Book maximum field length, ordering ties, and
   named-list data before and after cross-version saves.
4. Compare matched Filer record insert/delete, Worksheet formula
   save/reopen, and Draw primitive and text saves. The 3.05 baselines
   are already published. [Filer](filer-native-20261117.md) · [Worksheet](worksheet-native-20261117.md) · [Draw](draw-native-ui-20261119.md)
5. Qualify 3.02 interchange with short and maximum-width fields on disposable
   copies. Observe whether the newer app updates the narrower schema and how
   the older app handles fields beyond its declared widths.
