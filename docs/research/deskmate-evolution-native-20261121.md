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
