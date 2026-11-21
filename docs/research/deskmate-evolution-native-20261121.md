# DeskMate Evolution Atlas native trials

## Shared controls

The base was `1540ea6` on main. The held, visible trials used the
authenticated loopback socket, seed 1, no keyboard hook, and no host
input injection. The 86Box build reports 7.0, source
`855258da966f1594f568350be59e8e1eca082ed1`, executable SHA-256
`e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d`,
and ROM checkout `908394b690f7da28f47727d9876774fd672c4ed3`.
Raw frames, disk images, exact socket journals, and launch receipts
remain in the private lab. [Media ledger](../ecosystem/deskmate-evolution-releases.json) · [86Box controls](86box-client.md) · [Prior RSX configuration](deskmate-303-305-comparison.md#installation-and-controls)

## Generic 03.00.00 on the RSX

The five verified TVDog ZIPs were reconstructed separately using
`python tools/experimental/deskmate_install_media.py 300 <originals> <output>`.
The tool creates 720 KiB FAT12 media with `DESKMATE_1` through
`DESKMATE_5` and preserves extracted member bytes and DOS timestamps.
TVDog describes 360 KiB or larger media. The reconstructed FAT labels
identify the working media in this trial. [TVDog copy procedure](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm300dsk.txt)

| Image | Working SHA-256 | Copy completed by emulated ms |
| --- | --- | ---: |
| Disk 1 | `f3894c3ea7303a749f0174331e361d439c67e253eb9d237cb4196fdb59b7456a` | 125,976 |
| Disk 2 | `d80c160b776fd0ae1ce82161849691abaf43d96b5122a66bb8b9bc8ed8c337f7` | 142,808 |
| Disk 3 | `b2ca1157a2fdde1d6980d978ea4e0e6e573ea514ec7531cfe966d203f2e03dbc` | 167,640 |
| Disk 4 | `c47e509e62c35240e85ce5fae0c4603747be4225f13743f17a7284d22faa765d` | 188,472 |
| Disk 5 | `0959359e07f439ef2eece5e8ee235aac5cfae128c87b7c77bd625a941119d20f` | 213,304 |

The sealed DOS 5.00 disk, configuration, and NVRAM were copied from
the RSX baseline. The machine used a 25 MHz i386SX, 4 MiB RAM,
internal Cirrus VGA, PS/2 input, and one 1.44 MB drive. The source
disk SHA-256 was `6c146364c24000dbf46898eec1abd4940c3f8a3a666670bdda3aa30a01e681ec`.
Create the destination with `MD DESKMATE` at the C: root. Mount
each image in A: in numerical order, run `COPY A:\*.* C:\DESKMATE`,
and wait for the DOS prompt. The first copy completed despite the
automation's initial failure to match DOS's indented count. The count
reader was corrected without replaying the copy. Copy order retains
the last encountered `DESKTOPD.CFG` where the per-disk bytes differ.

After ejecting Disk 5, append `SET DMCONFIG=C:\DESKMATE` to
`C:\AUTOEXEC.BAT`, run that batch file from DOS, and verify the
value with `SET`. This activates the setting in the current DOS
session. Set `DATE 10-23-2026` and `TIME 12:00:00`, switch to the
installation directory, and run `DESK`. The installed `DESK.EXE`
contains the media's 03.00.00 string and matches SHA-256
`27df5c7e26312e88f7a7075613a93a871ac71f72ad0a9ccf4ca69e0b508e9a2e`.
The first documented desktop was at 225,418 emulated ms. A separate
cold-boot control was outside this run.

The 640 × 480 VGA desktop in BIOS mode `0x12` displays Text,
Calendar, Hangman, Address, and PC-Link panels, plus Programs and a
calculator. On the same date, 3.02 uses Draw in the panel occupied by
Hangman in 3.00. Both display the date and time at top left and Help
at top right. F2 opens File. One Down selects Run because Get Info is
disabled. The Run File dialog accepts a program and separate data
filename, with Normal and Fast CPU options. Enter `CALENDAR.PDM`
to reach the month grid. Escape returns to Desktop.

Run `TEXT.PDM`, type ALPHA, Enter, and BETA, and choose File → Save as.
The enabled-item menu scan skipped disabled Save, so four Down
presses selected Merge. Escape canceled it, and three Down presses
selected Save as. The basename `ATLAS` created `ATLAS.DOC`. It
matched the existing 13-byte 3.03 and 3.05 synthetic fixture exactly.
The independently recovered [3.00 save](../../tests/fixtures/application-generated/text/300-native-atlas.doc)
has SHA-256 `5b891ce9954b0fb4b859921e8670d758a25572d4e153f0609ba055f8f347d582`.
`Escape` from Text returned to Desktop, and `Escape` from Desktop
returned to DOS in this trial. The run ended at 249,076 emulated ms.
[Matched later Text fixture](../../tests/fixtures/application-generated/text/303-native-match.doc) · [3.02 Desktop and exit evidence](deskmate-303-305-comparison.md#deskmate-302-stretch-experiment)

The stopped disk SHA-256 is
`676fa9f8a6d9a1974967979d1000db78edd8216c6aa078cce4ff0c6a9ee042dd`.
It has 80 files in the DeskMate directory after the native observations,
including the synthetic Text save. `AUTOEXEC.BAT` hashes to
`c75372306273d0cbab6ba2ddbb75acec2368eb3d430d98040d3a7af107a5ed89`.
The original `CONFIG.SYS` digest remained
`0b1574c75cf4c4b0f5b25ffa1c14f307098e292002e2b7e10232e15e8080c7c6`.

## Original 01.01.00 on a 1000 SX compatibility profile

The pinned 86Box build provides a Tandy 1000 SX profile. This trial used
that profile for the original 1000 distribution. The emulated machine
had an 8088 at 4.77 MHz, 640 KiB RAM, internal video, and two 360 KiB
drives. BIOS POST reported 01.02.00. The SX ROM SHA-256 was
`f68a569f71fc090cec61bc5f699d0553dca7c5d012166709e74fc6c72568fdc2`.
There was no hard disk.

Extract byte-identical working copies from the verified `system/d1000.zip`:

| Raw image | Role | SHA-256 |
| --- | --- | --- |
| `MSDOS.DSK` | Boot DOS from A: | `14287d75a5581270af4e055a2697f07e6ab845f2c2097b516086398c7205e7fd` |
| `DESKMATE.DSK` | Program/data disk in B: | `801f65a5f50abe9cd4b26faccbf82d60739285788e0389a035c1adcba60ff2be` |

Both are unlabelled 368,640-byte images. Mount both before advancing
guest time. At 48,000 emulated ms, Tandy DOS 02.11.22 requested the date.
Enter `10-23-2026` and `12:00:00` at its date and time prompts.
Switch to `B:` and enter `DESK`. The version banner showed 01.01.00
and a 1984 copyright at 58,714 ms. The native task screen was visible
by 71,714 ms in BIOS text mode 3 at 640 × 225 pixels.

The screen put a month calendar and today's events above the Text,
Worksheet, Filer, Telecom, Calendar, and Mail document panels. The
footer exposed F1–F10 commands including Alarm, Host, Select, and
Swap. Right Arrow moved focus from Text to Worksheet. Escape left
that screen in view at the measured checkpoint. The emulator quit
at 72,872 ms. Application editing, save, the program's own exit
command, and operation on original Tandy 1000 hardware remain open.
[Image and capture receipt](../evidence/deskmate-evolution-20261121.json)

## DeskMate II 01.00.00 on the Tandy 1000 SX

This carried forward the already booted SX process after the session
interruption. Its authenticated status confirmed held time at 47,000 ms
and matched the mounted disk identities. The profile used the SX ROM,
8088 at 4.77 MHz, 640 KiB, internal video, and two 360 KiB drives.

Extract the four unlabelled 368,640-byte images from verified
`system/d1000sx.zip`. Mount Disk 1 (DOS) in A: and Disk 3 (DeskMate II)
in B:. Disk 2 holds supplemental DOS software, and Disk 4 holds samples.
The boot dialog identified Tandy DOS 03.20.02 and BIOS 01.02.00.
Enter `10-23-2026` and `12:00:00` at the DOS prompts, switch to B:,
and run `DESK`. The program disk's exact launcher has SHA-256
`d0a00742f352538ad0de880d28c03bbd3c00f008a80a08a83657c4364662201d`
and contains version 01.00.00. [Archive and member identities](../ecosystem/deskmate-installation-media.json)

At 69,214 ms, the 640 × 225 mode-3 task screen had the original
layout of six application panels, a month calendar, today's events,
and F1–F10 commands. F2 Name replaced the bottom commands with
Old filename and New filename prompts. Escape, F7, and a blank Enter
left the prompt visible at subsequent checkpoints. The run ended by
socket quit at 71,230 ms. No rename or other document change was
submitted. The sample disk and the program's own exit remain open.

## DeskMate II Tandy 3000 file sets on an RSX compatibility profile

TVDog identifies the program set as DeskMate II for the 3000 and
standard PCs. A separate Tandy DOS 5.00 RSX clone used two
720 KiB FAT12 working images from the two verified `3kdm2dk*.zip`
archives. The respective working SHA-256 digests were
`24b9030dbe775f7ab13b4b90436dec3e0fbc07c1912a776dc9716d67a7321ef8` and
`dc9bc0856474a6c4447aa5a750c3e129241c0c3c1b8917df1af7aeb5d1e22ad6`.
Image 1 contains 27 program and help files, and image 2 contains
nine sample and tutorial files. [TVDog index](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/00_index.txt)

Boot DOS, create `C:\DMII`, and copy `A:\*.*` from each work image
to that directory in numerical order. DOS reported the two copy
counts at 37,468 and 46,164 ms. Eject the media, set the same date
and time as the SX trial, and run `DESK` from `C:\DMII`. This
procedure changed neither DOS startup file nor disk geometry.
The version 01.00.00 string is present in the launcher with SHA-256
`c3c8ae6409707ad78503b22ce4a9d9f35aa998cb96efa5a600fd061b2180e09f`.

The program reached its task screen by 48,918 ms. Layout and footer
commands parallel the native SX view. This run used BIOS mode 3 at
720 × 400 with a green frame, blue panels, and red focus. The SX
run used different video hardware and displayed gray and black,
so this trial does not isolate which factor determined the palette.
Right Arrow moved across the application panels. Four presses from
Text reached Calendar, and Enter opened Calendar's separate
text-mode weekly schedule. The program showed a filename prompt
and a function-key bar with Date, Events, and Add. Typing `ATLAS`
left a zero-byte placeholder on the disposable disk. No event was
entered, and Escape left the schedule in view. The stopped run
ended at 70,104 ms with disk SHA-256
`b39a1c182722bd9b9d21d335d36a6bc855f569e68f74b754f695751a09a35630`.

The same-name program comparison against SX Disk 3 found 15 exact
matches and 10 differences. All nine `TW*.EXE` programs matched
byte-for-byte. `DESK.EXE`, `DMPLUS.COM`, `ALARM.ARM`, and seven
help files differed. This directly establishes shared applications
alongside different launcher and support bytes. Operation on an
emulated or physical Tandy 3000 and a whole-suite DOS compatibility
claim remain open.

## Personal DeskMate EX 01.01.00 on a 1000 SX compatibility profile

The verified `system/d1000ex.zip` supplies three unlabelled 360 KiB
raw disks. Boot `MSDOS.DSK` in A: and put `PDDISK1.DSK` in B: on
the same floppy-only SX profile used above. Their respective
SHA-256 digests are
`b1ec150fea5d6caf2d2aa72a392b13a3332534ce974514808d274b2623e52bca` and
`d13f0c1b9b80986f35650cda9d6ecde576dc85e28be15f6f0cc375005a72b45d`.
`PDDISK2.DSK`, SHA-256
`57e5061a84b31006f5be69fac76aafc88c82163d6adf29bfabe7541fc9293567`,
holds Text, Paint, Telecom, Filer, and Worksheet. Disk 1 holds Calendar,
the desktop, accessories, and `INSTALL.EXE`.
[EX media and bundled DOS](../ecosystem/deskmate-installation-media.json)

Bundled Tandy DOS 02.11.24 asked for date at 47,000 ms. Enter
`10-23-2026` and `12:00:00` at its prompts, switch to B:, and run
`DESK`. The program reports 01.01.00 and a 1986 copyright on the
graphical startup screen. The Desktop was visible by 83,834 ms in
mode `0x0A` at 640 × 200. A calendar, Note Pad, and calculator
sit beside seven file panels. The focus outline moves as Tab
cycles through the panels. F2 alone did not open File in the
measured state. Alt+F displayed Get Info, Copy, Delete, Rename,
and Quit DeskMate. Up selected Quit DeskMate, and Enter switched
back to mode 3. The run ended at 88,974 ms before a DOS prompt
was verified. Exact EX hardware, the installer, and use of Disk 2
remain open.

## Personal DeskMate HX media and ROM startup

Use a fresh 86Box Tandy 1000 HX profile with internal video, an 8088
at 4.77 MHz, 640 KiB RAM, and 720 KiB floppy drives. The ROM
`v020000.u12` has SHA-256
`c7d7cb0cdec5178898001cdde05442a9d2f64b56bfdf94003ee5e814f98f6bce`.
The HX startup menu appeared with both drives empty at 47,000 ms
and showed Tandy DOS 02.11.26. Its options include Run Personal
DeskMate, Set System Date and Time, View Programs on Drive A:, and
Startup from Internal Drive. F1 with an empty A: showed a
DeskMate-not-found message. Tandy's Faxback separately documents
the original ROM desktop, drivers, and EEPROM startup choices.
[Faxback 1378](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01378.txt)

Extract nested `personal.zip` from verified `system/hxdisks.zip`.
Use the atlas FAT12 writer's default 720 KiB geometry with the label
`HX PERSONAL`. The working image SHA-256 is
`2fc5ad0b196be404e424448ad29174b9dd2179437271f1c8c9257d3baefef5e9`.
Mount it in A: and press F1 again. The disk launcher has version
01.00.00, SHA-256
`1bfa0cf19c46f5e99a6fd6d689c3daff483c2787bd8038d74c583244d5a6f3f6`.
The Desktop at 77,008 ms says **DeskMate 2 - A:\** in 640 × 200
mode `0x0A`, with Text, Worksheet, Filer, Music, Paint, Calendar,
and Telecom panels. The observed boot used the default January 1980
date. The nested `msdos.zip` and distinct `HXORIG.IMD` utility disk
were outside the boot path.

Alt+F opened File. Down selected Run, and Enter opened fields for
Program and Data file and controls for Normal/Fast CPU speed.
Run `CALENDAR.PDM` with Data file blank for the graphical month
view. Enter opened January 1's day view. Escape left that view in
place. The trial ended by socket quit at 98,592 ms. No appointment
or save was submitted. Exact ROM service usage and the ImageDisk
utility original remain open.

The HX nested program set and standalone Personal DeskMate 2 ZIP
share 34 names with 31 exact byte matches. Their launchers and
`MAINMENU.PDM` match. `DMCSR.MOD`, `ART.PNT`, and `XMAS.SNG`
differ. The HX runtime is 28,595 bytes and the standalone copy
is 57,203 bytes. HX adds `MENUDATA.TAN`, while the standalone
ZIP adds `DMNOTEPD`. These file identities distinguish the
acquisitions despite their shared program title and launcher version.

## Standalone Personal DeskMate 2 on the Tandy 1000 SX

Use the five-disk option in the [TVDog recipe](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/pdm2_360.txt)
with verified `pdm2.zip`. Take `COMMAND.COM`, `DISKCOPY.COM`, and
`FORMAT.COM` from the SX DOS Disk 1, with working timestamps set to
1987-06-29 00:00:00 for those three copies. Keep program member bytes,
archive timestamps, and recipe order on each disk. Use the actual
`DMPDASCI.MOD` member for the recipe's `DMPDACSI.MOD`. Assemble
360 KiB FAT12 images with `floppy(members, label, '360k')` in
the [reconstruction tool](../../tools/experimental/deskmate_install_media.py);
use `PDM2 DISK1 ` through `PDM2 DISK5 ` as eleven-byte labels.
The [media receipt](../evidence/deskmate-evolution-20261121.json)
lists the exact reconstructed image hashes.

Boot the separate Tandy DOS 03.20.02 copy in A: on a fresh 1000 SX
profile with two 360 KiB drives. Put the startup image in B:, set the
shared October 23, 2026 date and noon time, switch to B:, and run
`DESK`. The launcher banner at 58,684 ms reported Personal
DeskMate 2 01.00.00 and a 1987 copyright. The Desktop was
visible at 81,684 ms in 640 × 200 mode `0x0A`.

File → Run rejected `A:\TEXT.PDM` with Invalid program name
while B: was the desktop drive. Put Text/Worksheet Disk 2 in B:
and choose Disk → Swap (Alt+S). The Text and Worksheet panels
then showed the corresponding files. Keep DOS Disk 1 in A:,
use File → Run, enter `TEXT.PDM` in the Program field, leave
Data file blank, and press Enter. The untitled editor opened
with **Non-ASCII** in its status bar. Alt+F and three Down presses
selected Save as because Save was disabled. Type ALPHA, Enter,
and BETA as two lines, and save using basename `HIST`. The
title became `HIST.DOC` by 159,476 ms. Ctrl+Q left a blue
frame before the trial ended by socket quit at 164,184 ms.

The actual [35-byte Text save](../../tests/fixtures/application-generated/text/pdm2-native-hist.doc)
has SHA-256 `89444e6419f4fc936ff2da8eed8fce570986b2800c8778499f901f77fec5e9e4`.
7-Zip and independent FAT12 extraction agree. A 22-byte formatted
envelope precedes a 13-byte body identical to the 3.00 ASCII save.
This establishes the default mode and bytes for this synthetic case.
Cross-release read and write compatibility and operation on a TX
proper remain open.

## Tandy 1000 SL/2 startup blocker

On the emulated SL/2, boot unmodified `DOS33.IMG` in A: with
`DM1.IMG` in B:. The verified source is `system/1000SL2D.zip`.
The 720 KiB DOS image SHA-256 is
`a483df25609610be2dc4c4e129d9df0f55e60af08a1679630ddf310d009ff99a`.
The 8086 profile ran at 8 MHz with 640 KiB, internal video,
and two 720 KiB drives. POST reported BIOS 01.04.04, and DOS
3.30.22 reached its date prompt by 45,000 ms. The two ROM
halves match SHA-256
`7fe228566de37a2f06ca6703a9f1280fd75db2f2d0e0e635b7c3b1e214680866`
and
`160116f3ad6788af7faa7a5f12de636de58ea18e2021ddba242ac1e801a927af`.

After setting the date and time, run `SETUPSL2`. The program
reported changed drive types, then warned about an invalid EEPROM
record. Its menu showed DISK as the primary startup device and
DESKMATE as the initial program. From Video Display, three Down
presses reached Primary Start-up Device. Left selected ROM, and
F1 wrote the disposable profile's EEPROM. The utility reported
completion. This follows the documented ROM and initial-program
choices. [Tandy Faxback 1283](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01283.txt)

After switching A: to DeskMate Disk 1 and B: to Disk 2, a hard reset
left the screen blank for the full 85,000 ms of observation.
A second hard reset with both floppies ejected also stayed blank
for 45,000 ms. Socket quit ended the run at 193,192 ms. The modified
disposable EEPROM was preserved. The test established the supplied
DOS boot, setup menus, and failure of this ROM startup attempt.
Version identification and application launch remain open. A fresh
control should compare ROM startup in **MS-DOS** mode before retrying
ROM DeskMate.

## Tandy 1000 RSX OEM 03.04.04

Use a pristine RSX DOS 5.00 clone and verify `system/rsxdisks.zip`
against the media manifest. Extract the six `DISK*.ZIP` members
separately. Follow the archive notes' 1.44 MB geometry and keep
all member bytes and directory names. The atlas FAT12 writer uses
`'1440k'` and eleven-byte labels `DESKMATE_1 ` through
`DESKMATE_6 `. Disk 4 contains nested Print Companion files
under `DOCUMENT`, and Disk 5 contains `HOMEAUTO`. `UTILS.ZIP`
is a separate utility set. Independent FAT12 extraction of all six
reconstructed disks matched all 509 ZIP member byte strings.
[RSX archive identity](../ecosystem/deskmate-installation-media.json)

| Disk | Files | SHA-256 of working image |
| --- | ---: | --- |
| 1 | 28 | `7bb8e4a7e8d66e1271d2639e59414dea2cce1d82c8fdfabd04cba05764bee940` |
| 2 | 62 | `d6af4f46430245b3b98fe740d45b083363464af368e96a07c54b676c52198e15` |
| 3 | 57 | `9d8c8c2f66bbc6d177799c8a4b987aaa6037bb37d9c5f8d86f818006f0da37a7` |
| 4 | 236 | `be132ea042027ff03d9d888d8162c0bd3a145d49ab7b864cb4ead2a7fdd57b9d` |
| 5 | 56 | `c717d1ce81b326240f5b21fbe4d8a5a884847a56351d3ebf13588b0d76b2534c` |
| 6 | 70 | `6afd2695ccb76f64a246aa1fce2647b4def65dbfa02477303b474ad971cd3b42` |

Boot DOS, mount Disk 1 in A:, use `A:`, and confirm the FAT
label with `VOL`. The tested `DESK INSTALL` command showed the
**03.04.04** banner at 21,784 ms. It requested Disk 1 while that
disk was mounted. Enter accepted it and reached the floppy
Desktop at 36,788 ms. The interface has an Applications menu,
Teach Me, Home Organizer, Information Center, Print Companion,
and Automatic House, plus AOL and Letter Invaders shortcuts.
The experiment identifies the applications from the menus and
media. It does not establish network or accessory operation.

Open File with F2, press Down twice to reach Run, and submit
`INSTALL.PDM` with no data filename. This opened the hard-disk
installer at 47,452 ms. The installer selected `C:\DESKMATE`
as its default destination. The first copy stage reached the
DeskMate 2 disk prompt at 216,456 ms.

Disk 2 was mounted in A: and accepted. Its copy was still progressing
at 448,460 ms, with `RECORD.COL` visible. The installer requested
**DeskMate 3** at the 536,460 ms checkpoint. The emulator remains
held at that prompt with Disk 2 still mounted. The partial
hard-disk copy, current configuration, screenshots, and command
journal are archived privately. The partial disk has SHA-256
`9b4eaa045d826d6d68026ffcfe7d38820a48dfe34afd963a96c0a45c41b2ceba`.
This digest anchors the partial installation. Continuing that
exact run requires the held process. Verify its time and prompt,
mount the verified Disk 3 image, and confirm once. Disks 3–6,
post-install configuration, the installer exit, and first
hard-disk launch remain open.

## Alternate 3.05 media comparison

Rehashed each numbered ZIP and each original 720 KiB raw disk.
Extracted actual member bytes and grouped them by uppercase filename
across each entire set. A match requires at least one identical
byte instance under that filename. Only `DESKTOPD.CFG` has
different copies under the same name within each set. Disk order
is a separate test. [Verified raw media](../ecosystem/deskmate-installation-305.md#identify-the-five-disk-set) · [ZIP originals](../ecosystem/deskmate-installation-media.json)

| Pair | Common names | Byte match anywhere in set | No matching bytes | Names exclusive to first / second |
| --- | ---: | ---: | ---: | ---: |
| Nine ZIP / five raw | 146 | 145 | 1 | 0 / 2 |
| Five ZIP / five raw | 136 | 113 | 23 | 0 / 12 |
| Nine ZIP / five ZIP | 134 | 112 | 22 | 12 / 2 |

The nine-ZIP and raw sets differ on `DESKMATE.LBL`; the raw set
also has `INSTALL.HLP` and `USERDICT.SPL`. In the five-ZIP
set, the desktop program, desktop configuration, and numerous
help and tutorial files have different bytes. PC-Link's program,
help, protocol resource, and nine `.PCL` files are missing
from that layout. The launcher, installer, Calendar, Address
Book, Text, Draw, Filer, Worksheet, and principal runtime
binaries match across the three layouts. The separate sixth
five-ZIP companion contains Thesaurus files. These are static
findings. A five-ZIP native install would test changes to the
Desktop, program collection, and help. A nine-ZIP run would
mostly test its alternate disk layout.
