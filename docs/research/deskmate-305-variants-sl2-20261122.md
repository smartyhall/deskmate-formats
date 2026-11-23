# Alternate DeskMate 3.05 and SL/2 ROM startup

November 22, 2026. Campaign based on `109c6e6ee5e4a2670b897456102622920ceaf984`, including the completed [Evolution Atlas](../ecosystem/deskmate-evolution-atlas.md) and [RSX OEM recovery](deskmate-rsx-oem-recovery-20261122.md). No emulator process was running at inventory. The previous RSX, Automatic House, and SL/2 experiment directories were kept as historical controls. All guest mutations in this follow-up use separate writable profiles and authenticated loopback automation in visible, held operation with seed 1.

## Alternate 3.05 installation media

This is the five-numbered-ZIP distribution at TVDog plus its separate sixth Thesaurus archive. All six original sizes and SHA-256 identities match the [archive index](../ecosystem/deskmate-installation-media.json). Read each numbered archive independently, preserve its member paths, bytes, timestamps, and order, and pass its regular members to `floppy(members, label, '720k')` in [the existing FAT12 builder](../../tools/experimental/deskmate_install_media.py). The working labels are `DESKMATE_1` through `DESKMATE_5` and `THESAURUS`, space-padded to 11 bytes. 7-Zip 26.05 independently extracted every reconstructed image. Every extracted path and payload agreed with its source ZIP.

| Archive | ZIP bytes | ZIP SHA-256 | Working image SHA-256 (737,280 bytes each) |
| --- | ---: | --- | --- |
| `dm369dks1.zip` | 402274 | `142e44bd220e5f2ae63b5cadb914396b7a56b8c7bf1bb35ed85fe4866f0f6622` | `771c739fbd093d9018a7c1e519b57ffb60dd9dd0c055f80c16ec0d8bb7a337a4` |
| `dm369dks2.zip` | 405492 | `815954bea80b0685a0ff2fcf2c4de558c016e525d1284f513ce4cf636651c140` | `dc0a47b9f31e10676095192cecbbc6a2c142059290ad6f7b5bf99eac35a3b976` |
| `dm369dks3.zip` | 342089 | `fa64d470630c4f13d830a72cab971be29fb77f8bae2444dbca97133a457d9c3c` | `c961d8452a9a6d8f80272027c1da6f2b43dffaca7197ca5b478275d6530cd7a6` |
| `dm369dks4.zip` | 178166 | `173e68395fd23380e3340d841002f966352e4855ec9fc9abf85fbd56b1a60e16` | `892b57626a1264a8592b6ef24bcd2b73d306c504c961347537b149775fa52a05` |
| `dm369dks5.zip` | 347417 | `a5e4e2b246952d51a26a885c71f5116bf6532d4d886a591159fd9473a510416a` | `3e3798fffc77215824857722c62529317bdcd4ffec06c22e98ddba350e94d615` |
| `dm369dks6.zip` | 300354 | `c8241c43ce908c544504f7396f06ca9003d4095710a73cdb606ea347fe0bad65` | `e63a8695c9df5c417e3661a2be181339426a17bd27634fd5ffce24a4345f915d` |

The installation uses a Tandy 1000 RSX, i386SX at 25 MHz, 4 MiB RAM, internal VGA, a PS/2 mouse, one 1.44 MB floppy drive, and a clone of the Tandy MS-DOS 5.00 FAT16 baseline (54,525,952 bytes, SHA-256 `6c146364c24000dbf46898eec1abd4940c3f8a3a666670bdda3aa30a01e681ec`). The raw-media comparison uses the separate clean E00 installed disk, SHA-256 `9afd080411c37a96cdce802cb129ffe7d6e1d84fb43314add7221dc71e141df0`, with the same hardware and video configuration. Build SHA-256 `e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d` matches the 86Box 7.0 lab build at source `855258da966f1594f568350be59e8e1eca082ed1` and ROM pin `908394b690f7da28f47727d9876774fd672c4ed3`. [RSX BIOS and machine controls](deskmate-303-305-comparison.md#installation-and-controls)


### Native installer

Boot to the clean C: prompt, mount the first alternate image in A:, change to `A:`, and run `INSTALL`. The launcher reported **03.05.00** at 32,210 emulated ms. The installer opened in VGA BIOS mode `0x12` (640 Ã— 480). Accept the default **C:\DESKMATE** directory, wait for each numbered prompt, then swap A: and press Enter once. The underscore FAT labels passed the installerâ€™s checks. The human-readable requests displayed spaces.

| Observed state | Cumulative emulated ms |
| --- | ---: |
| Installation Directory | 72,210 |
| Disk Needed for DeskMate 2 | 217,214 |
| Disk Needed for DeskMate 3 | 337,218 |
| Disk Needed for DeskMate 4 | 437,222 |
| Disk Needed for DeskMate 5 | 527,226 |
| Printer Settings on Disk 5 | 647,230 |
| IBM Graphic, 10 CPI | 657,034 |
| Install Printer, All or One | 663,038 |

IBM Graphic on LPT1 was preselected. No printer and line feed filter were clear. Enter accepted the default printer and 10 CPI. Select **All** in the driver copy dialog. These are sampling times and bound the observations, rather than identifying when each prompt first appeared.

At 748,042 ms the installer was updating `AUTOEXEC.BAT`. Its reset prompt was visible at 754,042 ms. Eject Disk 5 and confirm. The emulator recorded a soft reset and returned to C: by 778,046 ms, with no floppies mounted. DOS `VER` reported 5.00. The startup batch file ran `SET DMCONFIG=C:\DESKMATE`. Set the DOS date to October 23, 2026, and time to 12:00:00, then run `CD \DESKMATE` and `DESK`. The installed alternate Desktop was visible by 794,022 ms in mode `0x12`. No installation error appeared at the sampled checkpoints.

### Desktop program and configuration

On the matched Tandy RSX profiles at 640 × 480, both Desktops use a teal workspace, the same Text and Programs panels, Teach Me, a month calendar, and four shortcut positions. Address, Quick Load, and Calendar occupy the same positions. Hangman takes the fourth position in the alternate set; PC-Link occupies it in the raw-media control. File and Desktop menu command lists agreed at the sampled states. Open File → About by pressing F2, Up, and Enter. At 810,012 ms the alternate About dialog identified `DESKTOP.PDM` **3.69**. At 45,102 ms the raw control identified it as **3.68**. Both displayed `DESK.EXE` resource version 68.19, `DMCSR.RES` 3.111, `DMGUF.RES` 2.15, and `DMMDS.RES` 2.10. The launcher bytes match the raw 03.05.00 distribution. The alternate archive's stem is consistent with the Desktop module version; the packaging history is unknown. [Paired framebuffer receipts](../evidence/deskmate-305-sl2-20261122.json)

| Installed file | Alternate bytes and SHA-256 | Raw control bytes and SHA-256 |
| --- | --- | --- |
| `DESK.EXE` | 19,047 / `0f2a40243c997276904d2555a117c60eedf0016dde073285e8d63c8345a2eba3` | Same |
| `DESKTOP.PDM` | 72,617 / `c739a8359a7626454e63c08a41639e6d4ed80d4bada4ec76acb459769e3080f5` | 72,681 / `85e56146a4da122c6ac646ca76895dcd7375454d8d9e2067b5f25f160daa8c5d` |
| `DESKTOP.CFG` | 1,015 / `647570e042ab4c6bf62b1a6a83aa72cc2beb84da137742e8798858acdfc346e4` | 1,070 / `456412de789cfe1680e2be9ae7ae057b10f7afa81548cc1e34f0e33cffed1899` |
| `TEXT.PDM` | 75,185 / `44cc8632a2c655659bfe524b83e49bc27f85bd0107a5444590b1446398cc5ea7` | Same |
| `PC_LINK.PDM` | Absent | 72,087 / `3334347668812343e5deef2b6058b4e75f9dd6fe257868f994fee9215f49adbf` |

7-Zip extracted 131 installed DeskMate files after the alternate Desktop, Help, Teach Me, and unsaved Text trials. The preserved E00 control has 143. The 12 raw-only files comprise the PC-Link application, its Help and protocol resource, and nine `.PCL` files. The 21 differing common files are the Desktop executable, its shipped configuration, and Help or tutorial resources. The alternate and control each retained its media's shipped `DESKTOP.CFG` bytes. Both configurations contain a Hangman entry, while only the control's contains `PC_LINK.PDM`. The matched installer choices yielded byte-identical `DMCSR.CFG`, `DMPD.CFG`, `CONFIG.SYS`, and `AUTOEXEC.BAT`. This ties the application availability to the media and the visible shortcut to the shipped configuration. The comparison is between complete installations.

The stopped, pre-Thesaurus alternate disk is 54,525,952 bytes with SHA-256 `7e5b7078cca53b511366432ec502a828be681c1b5dc2cfb7761d6c6e009d2eb7`. The accompanying configuration and NVRAM hash to `35e7595a860f47e38301f602dbc6056c924c97d95bdf2a9271bc29ce88278e0f` and `a883930c6a8ed73bfbe238b7cdad519e63acea18b68f9ff1f367d6f02fd4aba2`. The DOS startup hashes match the raw control. [Raw-media install](../ecosystem/deskmate-installation-305.md#verify-the-installed-configuration)

### Help and Teach Me

On the alternate Desktop, F1 opened six question tiles. Tab moved among topics, Enter opened a yellow text pane for the selected topic, Escape returned to the tiles, and F1 advanced to six questions that covered files, directories, desktop views, disk formatting, backups, and common problems. The raw control also displayed the yellow context-help pane when invoked on the Text panel. Help depends on the focus and call path.

The existing Help database reader validates the changed fields without interpreting their coding. For example, `DESKTOP.HLP` has 167 active Rules rows on each variant (14 common record IDs with changed field bytes) and 150 versus 148 Text rows (52 changed shared IDs). `DESKMATE.HLP` has 229 versus 208 active Rules rows and 199 versus 191 Text rows. The row counts and changed bytes are evidence of different resources. They cannot supply a verbatim wording or unique topic count. [Help database reader and limits](deskmate-help-database-20261120.md)

Teach Me listed the same nine lessons on both installations. Enter began **DeskMate: An Introduction**. At 9,500 emulated ms after selecting it, both displayed the first instruction box with the same visible text and **C = continue**. The sample desktop behind it differed. The alternate tutorial showed a Telecom file panel at upper right, while the raw version showed a Hangman button there and retained PC-Link below. The observed first page is a staged lesson state and differs from the ordinary installed Desktop. The two `DMINTRO.TUT` files are 31,874 and 31,725 bytes and have different hashes. `DMPLAY.RES` is byte-identical. Escape displayed the quit-lesson prompt, and Enter returned to Teach Me.

### File operations and Thesaurus

File → Run opened the same Program and Data file fields in both releases. With the data field blank, the alternate ran Text and the raw control ran `PC_LINK.PDM` to its offline welcome screen. Escape cancelled registration, and a second Escape returned to Desktop. The links stayed disconnected and no registration or network action was attempted. File → Copy opened the same two pathname fields and the same visible F1 instructions in both installs. The 326 × 165 dialog body and the 318 × 164 Help pane matched by RGB pixels in the selected crops. Desktop → Display had the same placement controls. Its list of available menus differed, including Hangman in the raw control's visible list and Telecom in the alternate's list. The difference follows the installed desktop configuration. The trial cancelled both Display dialogs.

The clean alternate installation included a 1,704-byte `DMTHES.RES` stub. In Text, Edit → Thesaurus on the synthetic word `quick` prompted the user to obtain the program. For the hard-disk trial, mount Disk 6 and copy `DMTHES.RES`, `THES.RES`, and `DICT.SYN` from A: into `C:\DESKMATE`, replacing the stub. A batch typed more quickly than DOS returned to its prompt and left the second command incomplete. Ctrl+C cleared it. Issuing each binary copy from a confirmed DOS prompt succeeded. Eject A: and run `DESK TEXT` from the installation directory. The same Edit command opened grouped synonyms. At 185,478 emulated ms of the comparison session, the selected noun was **center**. Enter substituted it. The bundled README separately describes launching Text from companion media on floppy-only systems. Those floppy-only procedures were outside this test.

Select all in Text, apply Bold, and save as `THESDEMO.DOC`. DeskMate shows the document as Non-ASCII. Use Desktop File → Copy to create `THESCOPY.DOC` in the same directory. Both appeared in the Text panel by 220,226 ms. Native save and native copy produced byte-identical files, 32 bytes, SHA-256 `f815a81e10ba5470e0cf3a7fd7017bbb50e16da63fd45c72b73fd4135bd9b467`. An independent FAT16 reader and 7-Zip agreed on their bytes and on all three companion resources. The Text parser recovered `center ` with two format controls and zero pictures. The verified fixture is [305-alternate-thesaurus.doc](../../tests/fixtures/application-generated/text/305-alternate-thesaurus.doc).

The stopped add-on trial's disk hashes to `092cba3494c85c39b211416614b8e7d7f6e135feb3bc3bd450a4d9b4d934640d`. The earlier stopped disk remains the baseline for trials without the companion. The two profiles have no media mounted after shutdown.

## SL/2 ROM startup on a factory-initialized EEPROM

The same pinned 86Box build ran the exact `tandy1000sl2` profile, with an 8086 at 8 MHz, 640 KiB configured RAM, internal Tandy video, XT keyboard, no mouse, no hard disk, and two 720 KiB drives. Host clock sync and network links were off. BIOS displayed **01.04.04**. The previous configuration template was taken from the private pre-setup capture, whose NVR directory had no persistent EEPROM. Its configuration SHA-256 is `3caebcb8c0049a5ac745024ba498ffdb647f2ff4ab2da2bd3c96be3fd2c7de71`. Source `src/machine/m_tandy1k.c` at the pinned 86Box revision initializes a missing SL/2 EEPROM to 128 zero bytes.

| ROM or input | Bytes | SHA-256 |
| --- | ---: | --- |
| `8079047.hu1` | 262,144 | `7fe228566de37a2f06ca6703a9f1280fd75db2f2d0e0e635b7c3b1e214680866` |
| `8079048.hu2` | 262,144 | `160116f3ad6788af7faa7a5f12de636de58ea18e2021ddba242ac1e801a927af` |
| `1000SL2D.zip` | 3,969,557 | `516cb60ddad983cb1dd9d6ae1b496cdcd19b747d08c7566f52aa43a1e97c17ed` |
| `DOS33.IMG` | 737,280 | `a483df25609610be2dc4c4e129d9df0f55e60af08a1679630ddf310d009ff99a` |
| `DM1.IMG` | 737,280 | `ad7dd60348c5f734a4eaaacbc2906eff0087e208e5e9e6e987b0626d39af50bc` |
| `DM2.IMG` | 737,280 | `7d298875b22d0c4cd50d4a05a61492a505e9545a84595295727a8b26200fcc65` |
| `DM3.IMG` | 737,280 | `a3df72488b13f9bf7f59e3d95a00e5afdb596edfb8d5fca539262ae76e73dc4a` |

All four working images were extracted byte-for-byte from the reverified ZIP. Their SHA-1 values independently match the MAME 0.282 software entries for `msdos33sl2` and `deskmate3`. The MAME list identifies the DeskMate program disks as **03.03.01** and says they require the SL/2 ROM. The two firmware halves also match its SL/2 driver by SHA-1. The catalog version is a documentary identification of the exact disks. Startup and the sampled ROM Desktop File menu supplied no visible DeskMate suite version or About command. [MAME software list](https://github.com/mamedev/mame/blob/mame0282/hash/t1000.xml#L55-L115) · [MAME SL/2 ROM definitions](https://github.com/mamedev/mame/blob/mame0282/src/mame/pc/tandy1t.cpp#L891-L905)

### Initialize the EEPROM and change one setting

1. With no saved EEPROM, mount `DOS33.IMG` in A: at held startup. The floppy reached the DOS 3.30.22 date prompt by 45,000 ms in BIOS mode `0x03` (640 × 225). Press Enter at the date and time prompts and run `SETUPSL2`. It reported the two detected 3½-inch drives and an invalid EEPROM. The resulting initial menu showed DISK, DESKMATE, two buffers, and eight open files.
2. Press **F10**. This copy of the utility wrote the factory settings immediately and returned to DOS with “Original factory settings installed.” Run it again, accept the drive-type notice, and verify ROM, DESKMATE, ten buffers, and ten open files. Video was Color, speed Fast, drive designation Top, and both startup-file checks, date and time prompting, and memory diagnostics were set to No.
3. Select the Initial Start-up Program line with four Down arrows from Video Display. Left selects **MS-DOS**. Press F1, wait for **EEPROM updated**, then eject the floppy and quit. Preserve the resulting 128-byte EEPROM, SHA-256 `bc4b67bbc50a50f07b4de4031e80b71e1b7f865b2a939d1e740c3cc2fcff301b`, before cold-starting.
4. Cold-boot with both drives empty. ROM DOS reported **3.30.22** and reached `A>` by 10,000 ms in mode `0x03`. `VER` returned 3.30. `DIR C:\` showed the read-only ROM drive and its seven files, including a 9,904-byte `DESK.COM`. That is direct evidence for ROM DOS independent of DeskMate.
5. From working ROM DOS, mount `DOS33.IMG` in A:, run `SETUPSL2` again, and verify ROM and MS-DOS with the other settings intact. Right on the Initial Start-up Program line selects **DESKMATE**. Press F1, wait for **EEPROM updated**, eject, and quit. The resulting seed SHA-256 is `046e81e0948627f831179457fa51c9508f16589c4ac886d222f4fd39b3d25e2f`. The two new NVRAM files differ only at byte `0x08`. Cold-boot disposable copies of this seed for the two program-media conditions.

The Tandy manual documents the two startup selections, the distinction between ROM and floppy drives, and the F1 and F10 keys. The exact behavior of F10 and the chosen setup defaults above are native observations of the supplied utility. [Tandy SL/2 manual, changing drives](https://www.manualslib.com/manual/4261292/Tandy-1000-Sl-2.html?page=27) · [Setup instructions](https://www.manualslib.com/manual/4261292/Tandy-1000-Sl-2.html?page=40) · [Tandy Faxback 1283](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01283.txt)

### ROM DeskMate with and without program media

| Cold-start condition | Observed result |
| --- | --- |
| Both drives empty | Desktop rendered by 10,000 ms and remained visible at 35,000 ms. Text, Programs, and Autoconfig were empty. File → Run on `CALENDAR.PDM` opened Disk Needed for A: at 44,706 ms. |
| `DM1.IMG` in A:, `DM2.IMG` in B: | ROM DOS executed `C:DESK` by 2,500 ms. A busy icon was visible at 6,000 ms. By 14,000 ms the Desktop listed Address, Hangman, Install, and Mail Merge as the first four Programs. A Hangman shortcut occupied the former Autoconfig panel position. |

Both DeskMate boots rendered a 640 × 200 framebuffer on the internal video. The socket reported BIOS mode `0x03` during these frames. The early Desktop has a blue-purple workspace, a text-only Teach Me panel, and top-row Address, Calendar, and PC-Link shortcuts. It uses File, Directory, Disk, View, Sort by, and Desktop menus. The two media conditions demonstrate that the ROM can launch the shell without floppies. The program disks supply applications, associated resources, and a disk-specific desktop configuration. [Native image receipts](../evidence/deskmate-305-sl2-20261122.json)

### Application launches and reset control

From the populated Desktop, select File → Run with F2 and Down twice. Type a program name or drive-qualified path and leave Data file blank. The SL/2 Run File dialog offers **Normal** and **Fast** CPU speed controls, in addition to the program and data fields shared with 3.05. Address Book from A: opened an empty index (zero entries) at 27,894 ms. Switch to `B:\CALENDAR.PDM` with Disk 2 in B: to reach the January 1980 month view at 54,444 ms. Both applications returned to Desktop after Escape and loading time.

Replace Disk 2 in B: with Disk 3 and run `B:\MUSIC.PDM`. The busy state was visible at 77,576 and 92,576 ms, and the untitled score was visible at 110,576 ms. Escape began another busy transition. Input during that transition did not establish a Sound launch. After remounting Disk 2 in B:, an explicit socket hard reset at 163,708 ms returned to the populated ROM Desktop by 180,708 ms, 17,000 emulated ms later. From that freshly observed Desktop, swap B: to Disk 3 and run `B:\SOUND.PDM`. The blank Sound editor was visible at 231,136 ms. The test exercised the editors' launch path and left their untitled data unsaved. Recording and playback were outside the trial, and the emulator profile had no active sound device.

The original set also includes Draw, Filer, Form Setup, Hangman, Mail Merge, PC-Link, Telecom, Text, Worksheet, and an installer module. This inventory comes from the program disk bytes. Drive A held Disk 1 throughout these application tests. Disk 2 supplied Calendar and Disk 3 supplied Music and Sound. [Original disk inventory](../ecosystem/deskmate-installation-media.json) · [Native capture evidence](../evidence/deskmate-305-sl2-20261122.json)

### Earlier EEPROM control

The archived EEPROM from the prior blank-screen experiment has SHA-256 `8f90fccac308e2496957df0423ec2233fea761c7f16808f62c7f22d88da8a0ee`. Its 128 bytes differ from the working DeskMate seed at 65 positions. It contains only four nonzero bytes. Copy it into a disposable profile with the same configuration as the working cold-boot experiment. With separately extracted, SHA-256-matching Disk 1 and Disk 2 in A: and B: at held startup, the cold boot stayed blank in mode `0x03` at both 14,000 and 40,000 ms. The factory-initialized control had displayed the Desktop by the identical 14,000 ms sample. The CPU was executing at different offsets across the blank observations.

In another old-seed boot, the documented Ctrl+Alt+Shift+V monitor toggle switched the reported mode from `0x03` to `0x07` (640 × 225) and the framebuffer remained blank at 45,016 ms. This particular run used the post-application floppy copies. The matching-media cold-boot control used pristine floppies. Together with the successful hard reset on the factory seed, the cold-boot comparison isolates the EEPROM image as the relevant changed input. It establishes a recovery procedure and a reproducible failure case. Which altered fields are necessary for recovery remains open. [Earlier negative trial](deskmate-evolution-native-20261121.md#tandy-1000-sl2-startup-blocker) · [Tandy monitor-toggle instructions](https://www.manualslib.com/manual/4261292/Tandy-1000-Sl-2.html?page=40)

The active application-run copies of Disk 1 and Disk 2 changed only four bytes each, all in the FAT12 last-write timestamps for `PERSONAL.ADR` and `PERSONAL.CAL`, respectively. 7-Zip extraction confirmed identical file bytes and directory membership. The resulting full-image SHA-256 values are `b1f6332edb1bf0f9e7f98b5ceb05f6e3c0e8f6ba0fbbe008c7b3116f56294486` and `e4b54e3d997601a81e1daa26ba50ea9ec05e3b6e63a9c2b7f5e0a0e77faa328e`. DOS33 and Disk 3 rehashed unchanged. Keep the originals and freshly extracted boot controls for reproduction.
