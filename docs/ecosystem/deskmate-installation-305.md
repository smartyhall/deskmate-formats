# Install DeskMate 3.05 on a DOS PC

For the earlier generic release, see the [tested 3.03.01 installation
guide](deskmate-installation-303.md) and the [native interface and format
comparison](../research/deskmate-303-305-comparison.md). The [alternate
five-ZIP installation](../research/deskmate-305-variants-sl2-20261122.md#alternate-305-installation-media)
uses a different Desktop build and has its own matched RSX record.

This guide follows the November 5, 2026 clean installation of generic DeskMate **03.05.00** on an emulated Tandy 1000 RSX. The installer ran from five 720 KiB images, wrote a new hard-disk installation, and restarted DOS. Calendar then opened and reproduced the expected test files. The steps below come from that run and its preserved screens and installed files. [Native installation report](../research/calendar-editor-observatory.md#media-and-disposable-installation)

## Requirements and preparation

| Component | Observed working configuration |
| --- | --- |
| Computer | Tandy 1000 RSX, 386SX at 25 MHz, 4 MiB RAM |
| Display and input | Internal Cirrus GD5402 VGA, PS/2 keyboard and mouse. Installer and Calendar graphics at 640 × 480, BIOS mode `0x12`. |
| Sound and printer | Internal audio configured. IBM Graphic on LPT1 selected by default. Physical printing was outside the experiment. |
| Boot and floppy | Tandy MS-DOS 5.00 on C:, drive A: configured as 3½-inch 1.44 MB and used with 720 KiB DeskMate media, drive B: absent. |
| Hard disk | Primary IDE master, 52 MiB raw disk, 1,024 cylinders × 4 heads × 26 sectors, FAT16. BIOS drive C set to AUTO. |
| Emulator | 86Box 7.0 experimental build, source `855258da966f1594f568350be59e8e1eca082ed1`, ROM revision `908394b690f7da28f47727d9876774fd672c4ed3`. Dynamic recompilation and host clock sync disabled. |

The [verified DOS setup](../research/rsx-dos5-baseline.md#installation-procedure) covers a fresh DOS installation and the explicit BIOS and floppy settings. The 3.05 run started from a writable copy of that verified DOS disk and a separate copy of its configuration and NVRAM. On physical hardware, start from a backed-up DOS disk and use floppies that match the drive and controller. The table records the tested configuration. Minimum hardware, earlier DOS versions, and original hardware were outside the run. [Baseline and hashes](../research/rsx-dos5-baseline.md#preservation-hashes-and-restore) · [86Box and BIOS pins](../research/sdk-dialog-portability.md#inputs-and-controls)

Tandy’s hardware bulletin describes the RSX’s supplied PS/2-style mouse and its OEM sound capabilities. TVDog’s archive notes describe generic DeskMate 3 as PC-compatible with 512 KiB RAM. The lab used the configuration in the table above. A manufacturer-specified minimum for the exact standalone five-disk edition remains unconfirmed. [Tandy Faxback 1332](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01332.txt) · [TVDog DeskMate index](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/00_index.txt)

## Identify the five-disk set

The [WinWorld 3½-inch listing](https://winworldpc.com/download/c2bbc2ad-0279-c2ae-c281-11c3a4c2ac5a) gives a SHA-512 that matches the preserved laboratory archive. The 7-Zip original is 1,075,628 bytes, SHA-256 `bb1a74f787cfbdbda813e34a6a912a8533e0f9449ef0edbcb65353bedc9e323c`. The five members are under `Tandy DeskMate 3.05  (3.5)/`. Each image is 737,280 bytes. Use write-protected originals and working copies. The [TVDog inventory](deskmate-installations.md#version-and-installation-media-comparison) describes a separate nine-ZIP layout and a five-file-set repackaging with differences. Their disk order and member bytes cannot be substituted for this image set.

| Image | FAT12 label | Selected contents | SHA-256 |
| --- | --- | --- | --- |
| `DISK1.IMG` | `DESKMATE_1` | Installer, runtime, and Calendar | `2f6bb36af31d2996d01c9dcf159ae79ff30009d2a9fb9894798989fe2dda1487` |
| `DISK2.IMG` | `DESKMATE_2` | Desktop, Text, and Hangman | `6aa634f5e7516ef13d57d94c27040732c9aa17ea8d15ba8d816cee80d7610ce5` |
| `DISK3.IMG` | `DESKMATE_3` | Address Book, Filer, and Form Setup | `48d8c47807b14853faf14d774259fa8809cb1e189fdeb0852810ee577c9f9a30` |
| `DISK4.IMG` | `DESKMATE_4` | PC-Link, Telecom, and Worksheet | `f79d1344c02c4d8709b7b9bb4b52c197959bb6322b37a6a63717237eae5cafb4` |
| `DISK5.IMG` | `DESKMATE_5` | Draw, fonts, and printer resources | `9fdb5559ab34914f24b22aa23c0a5c3f7d3c0c668fbb57240a69cd9ecc47627b` |

## Start the installer

Boot to the DOS prompt and insert DeskMate 1 in A:. Switch to A: before running the installer. In the lab, running `A:\INSTALL` from C: produced a message asking the user to change to the drive containing DeskMate 1. Running the following commands displayed the 03.05.00 banner and opened DeskMate Hard Disk Installation. [Observed launch](../research/calendar-editor-observatory.md#media-and-disposable-installation)

```dos
A:
INSTALL
```

## Set the destination and change disks

Accept the **Installation Directory** field's default, `C:\DESKMATE`. Wait for each numbered **Disk Needed** prompt before changing the disk. Swap the working copies in order from DeskMate 2 through DeskMate 5, then press Enter to continue each time. The original run used drive A: for all swaps. The prompts display human-readable disk names with spaces, while the preserved FAT labels are represented with underscores. How the installer searches multiple drives was not tested. [Observed media changes](../research/calendar-editor-observatory.md#media-and-disposable-installation)

## Choose the printer and finish

When **Printer Settings** appears, keep **IBM Graphic** on **LPT1**. Confirm **10 CPI** and choose **All** when asked whether to copy all printer drivers or only the selected driver. This reproduces the driver set in the 143-file lab installation. When the installer reports that it will reset, remove DeskMate 5 from A: and confirm. In the recorded held execution the reset dialog was visible at 462,928 emulated ms and DOS had returned by 482,932 ms. [Observed printer and reset sequence](../research/calendar-editor-observatory.md#media-and-disposable-installation)

## Verify the installed configuration

The installer wrote `SET DMCONFIG=C:\DESKMATE` and prepended `C:\DESKMATE` to `PATH` in `AUTOEXEC.BAT`. It left `TEMP=C:\DOS`, and the installed `CONFIG.SYS` still contained the SETVER and HIMEM device lines, `DOS=HIGH`, and `FILES=10`. DeskMate did not launch automatically. These values were read from the preserved post-install FAT volume. The [DOS baseline report](../research/rsx-dos5-baseline.md#installed-baseline-observations) identifies the original startup settings.

| Installed files | What to check |
| --- | --- |
| `DESK.EXE`, `DESKTOP.PDM`, `DMCSR.R89`, `DMGUF.R89`, `DMDB.R89` | Launcher, desktop application, and shared runtime and database components. The exact `DESK.EXE` SHA-256 is `0f2a40243c997276904d2555a117c60eedf0016dde073285e8d63c8345a2eba3`. |
| `DESKTOP.CFG`, `DMCSR.CFG`, and `DMPD.CFG` | Desktop, runtime, and printer configuration files in the preserved installation. The installer run did not isolate what each runtime setting changes. |
| `DMVSVGA.RES`, `DMVEVGA.RES`, `DMFONT.RES`, and `*.FF1` | VGA and font resources. The included `DMVID.DOC` describes setting a video driver through `DMVID.EXE` and updating `DMCSR.CFG` at an explicit path. No video override was needed in this run. |
| `CALENDAR.PDM` and `PERSONAL.CLN` | The shipped calendar opened in the installed environment. The E00 database digest matched the media, and two subsequent native saves matched earlier research outputs. |

The preserved 54,525,952-byte E00-installed disk has SHA-256 `9afd080411c37a96cdce802cb129ffe7d6e1d84fb43314add7221dc71e141df0`. The 93-byte `AUTOEXEC.BAT` hashes to `81e3342527a29f11e043564a81af4a71709ced599d995f44632535ad295aa4b9`, and the 71-byte `CONFIG.SYS` hashes to `0b1574c75cf4c4b0f5b25ffa1c14f307098e292002e2b7e10232e15e8080c7c6`. These hashes identify the preserved files. Fresh installations may produce different disk hashes.

[Installed binary hashes](../research/sdk-source-identities.md) · [Native Calendar checks](../research/calendar-editor-observatory.md#native-database-reproduction)

## Launch and verify

Start in the installation directory. The installation experiment's first documented application launch was `DESK CALENDAR`. Plain `DESK` opens the Desktop in the project's 3.05 application collection. The installer banner and the installed launcher hash above distinguish this build from other DeskMate releases. The Calendar screen records the first documented application launch from this install, after the guest date was set for the test. The published Desktop captures are from a separate native session. [Native application inventory and Desktop images](../inventory.md#desktop-and-launcher) · [Calendar launch record](../research/calendar-editor-observatory.md#native-database-reproduction)

```dos
C:
CD \DESKMATE
DESK
```

To repeat the Calendar check, exit Desktop to DOS and run `DESK CALENDAR` in the same directory.

## Troubleshooting and evidence limits

- A POST configuration error was reproduced when the emulator's floppy settings disagreed with saved BIOS settings. The DOS baseline report shows the correction and records a separate Disk 2 label workaround for **DOS Setup**. The DeskMate images already had their labels. [BIOS and DOS media evidence](../research/rsx-dos5-baseline.md#bios-diagnosis-and-corrective-procedure)
- If the installer asks for Disk 1 immediately, ensure A: is the current drive, the image is the correct first disk, and each later request is matched to the actual media label. The rejected cross-drive command was observed. Other installer recovery paths were outside the run. [Install report](../research/calendar-editor-observatory.md#media-and-disposable-installation)
- Generic 3.05 lacks the OEM Music and Sound modules. A separate experiment launched selected OEM modules with 3.05 on the RSX. That combination has its own dependencies and evidence. [Native Sound and Music study](../research/sound-native-20261118.md)
- Tandy's RSX troubleshooting note documents printer-port setup, disk-backed `DESKTOP.CFG` on its own DeskMate configuration, and accessory conflicts with some add-on applications. Its disk numbers apply to the OEM set it describes. Contemporary coverage describes the general DeskMate 3 environment and its bundled applications. [Tandy Faxback 1318](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01318.txt) · [1989 *Los Angeles Times* review](https://www.latimes.com/archives/la-xpm-1989-11-16-fi-2234-story.html)
- The original media, raw framebuffers, and installed disk remain in private preservation. The illustrations are native captures, with installer dialogs cropped at original pixel scale where indicated. There is no verified first-desktop capture from this specific clean installation, and alternate settings and physical devices were outside this raw-media run. [Visual publication policy](../site/visual-assets.md) · [Installation roadmap #153](https://github.com/smartyhall/deskmate-formats/issues/153) · [Faxback documentation #154](https://github.com/smartyhall/deskmate-formats/issues/154)
