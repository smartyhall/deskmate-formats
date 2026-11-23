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
