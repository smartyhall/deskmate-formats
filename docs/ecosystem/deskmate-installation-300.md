# Install generic DeskMate 3.00 on a DOS PC

DeskMate 3.00 ships as five file sets with no vendor installer. TVDog's own
instructions describe copying the files to a directory and setting
`DMCONFIG`, and that is the procedure the project tested on November 21,
2026. The run installed the five reconstructed 720 KiB images on an emulated
Tandy 1000 RSX, launched the Desktop, and saved a Text document that matched
the project's synthetic fixture byte for byte. [Native run](../research/deskmate-evolution-native-20261121.md#generic-030000-on-the-rsx) ·
[Archive instructions](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm300dsk.txt)

This is the earliest generic DeskMate 3 release with a recorded installation.
It has no Setup program, so the steps below are a file copy plus one
environment setting; there are no installer prompts to answer. The later
[3.03.01](deskmate-installation-303.md) and [3.05](deskmate-installation-305.md)
releases do have installers, and their guides describe them.

## Requirements and preparation

| Component | Observed working configuration |
| --- | --- |
| Computer | Tandy 1000 RSX, 386SX at 25 MHz, 4 MiB RAM |
| Display and input | Internal Cirrus GD5402 VGA, PS/2 keyboard and mouse. The Desktop runs at 640 × 480 in BIOS mode `0x12`. |
| Boot and floppy | Tandy MS-DOS 5.00 on C:, one 3½-inch 1.44 MB drive used with 720 KiB media, drive B absent |
| Storage | Primary IDE master, 52 MiB raw disk, 1,024 × 4 × 26 sectors, FAT16 |
| Emulator | 86Box 7.0 automation build, visible, held, seed 1, no dynamic recompilation |

The run started from a copy of the verified DOS baseline whose disk SHA-256
is `6c146364c24000dbf46898eec1abd4940c3f8a3a666670bdda3aa30a01e681ec`. TVDog
describes 360 KiB or larger media; the laboratory used 720 KiB images. The
archive notes describe generic DeskMate 3 as PC-compatible with at least
512 KiB RAM, which the tested configuration exceeds. Minimum hardware and
earlier DOS versions were not tested. [Verified DOS setup](../research/rsx-dos5-baseline.md#installation-procedure)

## Identify the five file sets

The five ZIPs contain file sets rather than disk images. Reconstruct them
from the private mirror's `originals` directory:

```text
python tools/experimental/deskmate_install_media.py 300 <originals> <output>
```

The tool verifies each archive against the [media manifest](deskmate-installation-media.json),
writes uppercase DOS filenames with their original timestamps, and labels the
images `DESKMATE_1` through `DESKMATE_5`. Disk 1 holds the launcher and
Desktop, and the later disks add the office applications, Draw, Filer, and
dictionary resources.

| Disk | Working image SHA-256 |
| --- | --- |
| `DESKMATE_1` | `f3894c3ea7303a749f0174331e361d439c67e253eb9d237cb4196fdb59b7456a` |
| `DESKMATE_2` | `d80c160b776fd0ae1ce82161849691abaf43d96b5122a66bb8b9bc8ed8c337f7` |
| `DESKMATE_3` | `b2ca1157a2fdde1d6980d978ea4e0e6e573ea514ec7531cfe966d203f2e03dbc` |
| `DESKMATE_4` | `c47e509e62c35240e85ce5fae0c4603747be4225f13743f17a7284d22faa765d` |
| `DESKMATE_5` | `0959359e07f439ef2eece5e8ee235aac5cfae128c87b7c77bd625a941119d20f` |

These are working media with synthetic volume serials, not factory disks.
Keep each disk's `DESKTOPD.CFG`: the copies differ between disks, and a plain
copy in ascending order leaves the last one encountered.

## Copy the files

Boot to `C:\>` with no floppy mounted and create the destination, then copy
each disk in numerical order. Wait for the DOS prompt after each `COPY`
before changing disks.

```dos
C:
MD \DESKMATE
A:
COPY A:\*.* C:\DESKMATE
```

Repeat the `COPY` for Disks 2 through 5, ejecting and mounting each image
between copies. The run completed each copy in roughly 15 to 25 seconds of
emulated time, with Disk 5 finishing at about 213,304 emulated ms.

## Set the environment and start

DeskMate 3.00 finds its resources through `DMCONFIG`. Append the setting to
the startup batch file, then run that file so the value also applies to the
current session:

```dos
C:
ECHO SET DMCONFIG=C:\DESKMATE>> AUTOEXEC.BAT
AUTOEXEC.BAT
SET DMCONFIG
```

`SET` should print `DMCONFIG=C:\DESKMATE`. Then set the clock and start the
Desktop from the installation directory:

```dos
DATE 10-23-2026
TIME 12:00:00
CD \DESKMATE
DESK
```

## Verify the installation

The first Desktop appeared at 225,418 emulated ms. It shows Text, Calendar,
Hangman, Address, and PC-Link panels, the Programs list, and a calculator at
640 × 480. The title bar carries the date and time at the left and Help at
the right. F2 opens File; because Get Info is disabled in this state, one
Down selects Run, whose dialog accepts a program name and a separate data
filename with Normal and Fast CPU options.

To confirm the build, note the launcher rather than an About dialog: the
installed `DESK.EXE` is 15,826 bytes with SHA-256
`27df5c7e26312e88f7a7075613a93a871ac71f72ad0a9ccf4ca69e0b508e9a2e` and
contains the string `Version: 03.00.00`. The media's `DESKTOP.PDM` is 64,847
bytes with SHA-256 `b3021773cb0726689cc7d465f5689f9267963275f4725e3416b3eb9664c9e810`.

One native application check: open `TEXT.PDM` through Run, type `ALPHA` then
`BETA`, and use **File → Save as** with the basename `ATLAS`. The resulting
`ATLAS.DOC` matched the project's 13-byte 3.03 and 3.05 synthetic fixture
exactly, with SHA-256
`5b891ce9954b0fb4b859921e8670d758a25572d4e153f0609ba055f8f347d582`.
Escape from Text returned to the Desktop, and Escape from the Desktop
returned to DOS.

The stopped disk is 54,525,952 bytes with SHA-256
`676fa9f8a6d9a1974967979d1000db78edd8216c6aa078cce4ff0c6a9ee042dd` and
holds 80 files in `C:\DESKMATE` after the Text save. Its `AUTOEXEC.BAT` hashes
to `c75372306273d0cbab6ba2ddbb75acec2368eb3d430d98040d3a7af107a5ed89`, and
`CONFIG.SYS` remained unchanged at
`0b1574c75cf4c4b0f5b25ffa1c14f307098e292002e2b7e10232e15e8080c7c6`. Fresh
installations may produce different disk hashes.

## Troubleshooting and evidence limits

- There is no installer, so a missing file after the copy means the wrong
  disk was mounted or a copy was interrupted. Re-copy that disk and check
  the DOS count before continuing.
- If the Desktop cannot find its resources, confirm that `DMCONFIG` is set
  in the current session, not only in `AUTOEXEC.BAT`.
- Only one disk order, one destination, and one hardware profile were
  tested. The per-disk `DESKTOPD.CFG` difference means an alternate copy
  order can change the shipped Desktop configuration.
- The run ended at the Desktop exit with no cold-boot control, so this
  release is recorded as installed and launched rather than cold-launch
  qualified.

Media, disk images, and the complete installed tree remain in private
preservation. [Installation atlas](deskmate-installations.md) ·
[Installation roadmap #153](https://github.com/smartyhall/deskmate-formats/issues/153)
