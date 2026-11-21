# Install DeskMate 3.03.01 on a DOS PC

On November 21, 2026, the generic DeskMate **03.03.01** installer copied a
four-disk distribution to a clean Tandy MS-DOS 5.00 disk, restarted DOS,
and reached the Desktop on an emulated Tandy 1000 RSX. Calendar, Address
Book, and Text then ran from the installed directory. [Native experiment and comparison](../research/deskmate-303-305-comparison.md)

## Requirements and preparation

| Component | Observed working configuration |
| --- | --- |
| Computer | Tandy 1000 RSX, 386SX at 25 MHz, 4 MiB RAM |
| Display and input | Internal Cirrus GD5402 VGA, PS/2 keyboard and mouse. Installer and applications ran at 640 × 480 in BIOS mode `0x12`. |
| Boot and floppy | Tandy MS-DOS 5.00 on C:. Drive A: configured as 3½-inch 1.44 MB and used with 720 KiB media. Drive B: absent. |
| Storage | Primary IDE master, 52 MiB raw disk, 1,024 cylinders × 4 heads × 26 sectors, FAT16, BIOS drive C set to AUTO. |
| Audio and printing | Internal audio configured. The installer reached its reset dialog without asking for a printer choice. Audio playback and physical printing were outside the trial. |
| Emulator | 86Box 7.0 experimental UCRT64 Release build, held execution, seed 1, no dynamic recompilation, host clock synchronization disabled. |

The test used writable copies of the [verified RSX DOS disk, configuration,
and NVRAM](../research/rsx-dos5-baseline.md). TVDog specifies 720 KiB or larger
floppies for this set. The original factory disk geometry and the minimum
DOS, RAM, and display requirements for this exact release remain open.
[TVDog 3.03 instructions](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm303dsk.txt) · [Tandy Faxback 1332, RSX hardware](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01332.txt)

## Prepare the four installation disks

Use the four independent ZIPs from the November 20 verified TVDog mirror.
The hashes below distinguish the ZIP originals from the reconstructed 737,280-byte
FAT12 images. The ZIPs contain file sets. The working images do not establish
the original factory layout, physical disc labels, or volume serial numbers.
[Verified media inventory](deskmate-installation-media.json) · [Mirror audit](../research/tvdog-second-pass-20261120.md)

| ZIP and working FAT label | ZIP bytes / files | ZIP SHA-256 | Working image SHA-256 |
| --- | ---: | --- | --- |
| [dm303dk1.zip](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm303dk1.zip), `DESKMATE_1` | 411,531 / 42 | `a9897beaaddd29c47ec3ad4046d57ea2e28872399afea0731c12f2e8a259ebfe` | `6f6ec96cb231c9f94d5578c1db469772e3aa446e889fda7f32f343733802ae22` |
| [dm303dk2.zip](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm303dk2.zip), `DESKMATE_2` | 419,320 / 30 | `edb617433344c50361c23c582bccefd63441fa1dd5205d64905981c6f995638b` | `fc382d320f5a50d7e64b0fb36f3812852e81823fb6d8ada0b7647aaae774ebdf` |
| [dm303dk3.zip](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm303dk3.zip), `DESKMATE_3` | 325,771 / 32 | `e4c9fbada6cbcd158df1c488afbcb79b7b3fae9b28c4dff13bb87108ade8a18f` | `48c48524b23c571cf9d18250889e32b8d0fdb613dc4289c7c638b460e1bb272e` |
| [dm303dk4.zip](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm303dk4.zip), `DESKMATE_4` | 367,667 / 39 | `b164799dbf99511eda5e562ca3423622fa0452c591b6d548ea6783a58607055a` | `17cafd6656d443a0a6ce13dbfd1e2d3482d32df6f7a6168310d653a3965eede5` |

From the repository root, use the [media reconstruction tool](../../tools/experimental/deskmate_install_media.py).
Pass the mirror's private `originals` directory and an existing empty private
output directory:

```text
python tools/experimental/deskmate_install_media.py 303 <originals> <output>
```

The tool checks each ZIP against the manifest, preserves each member's content
and DOS timestamp, and writes uppercase DOS filenames to that disk only. Keep
each disk's `DESKTOPD.CFG` with its original set. Disks 2, 3, and 4 have
different copies. The `DESKMATE.LBL` file stays intact on every disk.

## Start the installer

Boot to the DOS prompt with no floppy inserted. Mount Disk 1 in A:, make A:
the current drive, and check the label with `VOL`. The failed control
used `DESKMATE 1` with a space. DOS recognized that label, but the installer
asked for the drive containing Disk 1. The same member bytes with
`DESKMATE_1` opened the **03.03.01** banner and the graphical installer.
Keep the underscore even though the installer calls the disk **DESKMATE 1**.

```dos
A:
VOL
INSTALL
```

## Set the destination and change disks

Keep `C:\DESKMATE` in **Installation Directory** and press Enter. Wait
for **Disk Needed** to name each next disk. The observed order was Disk 2
after `CALENDAR.TUT`, Disk 3 after `DICT.SPL`, and Disk 4 after
`DMVID.DOC`. Insert each image in A: and press Enter once. The dialogs
allow insertion into any drive. This run used A: throughout.

## Finish and verify the reboot

The installer displayed **Updating AUTOEXEC.BAT on drive C** and asked to
remove the diskette. Eject Disk 4 and confirm with Enter. The recorded run
showed the reset prompt at 387,144 emulated ms and DOS at 400,148 ms.
There was no interactive printer selection between accepting Disk 4 and the
reset prompt.

The clean destination contained 96 files, including `DESK.EXE`,
`DESKTOP.PDM`, `DMCSR.CFG`, `DMCSR.R89`, `DMGUF.R89`, `DMDB.R89`,
and the application modules. The installed launcher is 16,384 bytes with
SHA-256 `702a5f6237695793a773a327b2b9bedc706cce3d16a52360aa90c4f13f67066a`.
The installer set `DMCONFIG=C:\DESKMATE` at the top of `AUTOEXEC.BAT` and
prepended `C:\DESKMATE` to `PATH`, retaining `TEMP=C:\DOS`. The
`CONFIG.SYS` bytes matched the DOS baseline. Startup returned to the DOS
prompt. The installed directory had neither `PERSONAL.CAL` nor
`PERSONAL.ADR` before their applications first ran.

## Launch and verify

```dos
C:
CD \DESKMATE
DESK
```

The first Desktop displayed Address, Calendar, and PC-Link shortcuts.
For the keyboard-only verification, open **File** with F2, press Down
twice to highlight **Run**, and press Enter. Replace the selected Program
value with `CALENDAR.PDM`, leave Data file blank, and press Enter.
Calendar should display the current month. Escape returns to Desktop.
The experiment also ran `ADDRESS.PDM` and `TEXT.PDM` this way. In this
configuration, both tested DOS commands `DESK CALENDAR` and
`DESK CALENDAR.PDM` reached the Desktop. [Launch and application evidence](../research/deskmate-303-305-comparison.md)

## Troubleshooting and evidence limits

- Verify the mounted ZIP-derived image and its FAT label with `VOL` if
  the installer asks for Disk 1 again. A separately downloaded video update
  was unnecessary on the RSX.
- The guide covers one clean DOS profile, default destination, and one
  floppy drive. Driver overrides, alternate DOS versions, installation
  over an existing release, and physical hardware remain untested.
- The images on this page depict native guest frames. Disk images, original
  ZIPs, and complete installed files are held privately. [Visual policy](../site/visual-assets.md) · [Installation roadmap #153](https://github.com/smartyhall/deskmate-formats/issues/153) · [Faxback documentation #154](https://github.com/smartyhall/deskmate-formats/issues/154)
