# Release Installation Atlas 001: the nine-disk generic DeskMate 3.05 installation

November 28, 2026. Campaign `release-installation-atlas-001`, branch
`freebuff/release-installation-atlas-001`, base
`5045901177b735c7f5aaaa3512e4d4741a9d7bb2`. This report records one new
native installation and the documentation work that surrounds it. It is a
dated experiment record, not a compatibility claim beyond the stated profile.

## Why this release

The [media inventory](../ecosystem/deskmate-installations.md) previously listed
the nine ZIP sets `dm305dk1.zip` through `dm305dk9.zip` as inspected but
without a clean installation record. Two other 3.05 lineages already had
records: the five raw 720 KiB images of the WinWorld retail set, and the
five-numbered `dm369dks*` repackaging. Installing the nine-set closes a
documented gap and tests whether its installer behaves like either existing
record. [Five-disk guide](../ecosystem/deskmate-installation-305.md) ·
[`dm369` comparison](deskmate-305-variants-sl2-20261122.md#alternate-305-installation-media)

## Controls and evidence limits

| Control | Value |
| --- | --- |
| Emulator | 86Box 7.0 automation build, visible window, authenticated loopback TCP, `--nohook`, seed 1 |
| Execution | Held at 0 ms, advanced in explicit 1,000 ms steps; no host keyboard or mouse injection |
| Machine | `tandy1000rsx`, i386SX at 25 MHz, 4 MiB RAM, internal VGA and sound, PS/2 mouse |
| Floppy | One 3½-inch 1.44 MB drive; 720 KiB working images; drive B absent |
| Hard disk | Primary IDE master, 1,024 × 4 × 26 sectors, FAT16, disposable copy of the verified DOS baseline |
| Operating system | Tandy MS-DOS 5.00, clean baseline disk SHA-256 `6c146364c24000dbf46898eec1abd4940c3f8a3a666670bdda3aa30a01e681ec` |
| Media source | Private TVDog mirror originals, `tandy1000/deskmate/dm305dk1.zip` through `dm305dk9.zip` |
| Configuration and NVRAM | `a96865de9b6df71cf27d9f8a67136f36185f02a3599659c97ef151da4031544f` and `76e47b742f2648d4b10fa81ba1f0a254018e72af5d3b4172248a9c82d74d6497` after the run |

Every emulated timestamp below is a sampled observation. A sampled time
bounds when a state had already appeared; it does not date its first
appearance. Host elapsed time, emulated guest time, and provider usage
telemetry are separate quantities and are not converted into each other.

## Reconstructed working media

`python tools/experimental/deskmate_install_media.py 305 <originals> <output>`
now accepts the nine-set and writes nine 737,280-byte FAT12 images with the
labels `DESKMATE_1` through `DESKMATE_9`. Each source ZIP was matched against
the [inventory manifest](../ecosystem/deskmate-installation-media.json) by
byte count, SHA-256, member count, and unpacked total before any image was
written. The images are reconstructed file sets: they are not factory disk
images, and their volume serial numbers are synthetic zeros.

| Image | Label | Working SHA-256 |
| --- | --- | --- |
| `dm305dk1.img` | `DESKMATE_1` | `31305d3404c43124f0efa0fd5a628d9e3488e136637db92a2a49595f01995c5e` |
| `dm305dk2.img` | `DESKMATE_2` | `d799bff522047be092004e493016756a3bbfc583e16cb597cb526554868914b0` |
| `dm305dk3.img` | `DESKMATE_3` | `a760db22f66df3045014cf741d2ef60352713f32f94ef19b8e5778b5f64558e0` |
| `dm305dk4.img` | `DESKMATE_4` | `9c413bdc3f95ebe94e23674f6eb443e7561f2dcf4f0fd64b6baf33625bcebe15` |
| `dm305dk5.img` | `DESKMATE_5` | `dbd4f2ed518d902c577620332885d84786e7cee6247a8db3c22bfec239ee5154` |
| `dm305dk6.img` | `DESKMATE_6` | `145f112ddf3d5f643ba6bbe5797b8cf3642e5a507587c31c91c6f88be9c58207` |
| `dm305dk7.img` | `DESKMATE_7` | `e0c5f4911187fc166fd26cb622aeb18edc005b4c7b69ef88b691145fb6716f94` |
| `dm305dk8.img` | `DESKMATE_8` | `7e32e26ac0bf1b76f848cc62208e599b81b93c1b4ad1b5837cdf1ed305e92c0a` |
| `dm305dk9.img` | `DESKMATE_9` | `2484a3536da18a6f2816a8c879d1fa779502ff1155ccd6ca7acab7bfff91d3f8` |

7-Zip 26.05 listed every image and read its directory entries independently.
Disk 6 carries the `.ACC` accessory data that the printer phase later needs;
disk 8 carries `DRAW.PDM` and its `DIXON.FF1` font.

## Installation sequence

The machine booted the clean DOS disk to `C:\>` with no floppy mounted.
Mounting Disk 1 in A:, changing to `A:`, and running `INSTALL` printed the
Tandy banner **DeskMate / Version: 03.05.00 / Copyright 1984,1990 Tandy
Corporation** in 80 × 25 text mode, then switched to 640 × 480 graphics for
the installer. The banner was sampled at 19,518 emulated ms.

| Observed state | Sampled emulated ms |
| --- | ---: |
| `C:\>` after boot | 11,682 |
| Installer banner | 19,518 |
| Installation Directory dialog | 37,522 |
| Searching files, Disk 1 | 51,514 |
| DeskMate 2 requested | 141,514 |
| DeskMate 3 requested | 241,518 |
| DeskMate 4 requested | 341,522 |
| DeskMate 5 requested | 441,526 |
| DeskMate 6 requested | 641,534 |
| DeskMate 7 requested | 741,538 |
| DeskMate 8 requested | 841,542 |
| Printer Settings, after the numbered copies | 941,546 |
| DeskMate 9 requested during printer phase | 1,115,578 |
| Updating `AUTOEXEC.BAT` | 1,195,582 |
| `C:\>` after reset | not sampled precisely; between 1,195,582 and 1,226,082 |
| Desktop visible | 1,226,082 |

### Destination default differs from the other 3.05 media

The **Installation Directory** pathname field opened empty. The five-disk
retail set prefilled `C:\DESKMATE`. Typing `C:\DESKMATE` and pressing Enter
was accepted; a first attempt typed during a lossy input burst produced a
truncated value and the installer reported a filename error. Re-entering the
complete value with paced keystrokes succeeded. This is an input-pacing
artifact of the experiment, not an installer property.

### The printer phase reads media in a second pass

After the numbered copies, **Printer Settings** opened and reported
*File Not Found: Please insert a disk containing the file DMPDIBMM.ACC*.
That file is on Disk 6. Supplying Disk 6 produced the printer list with
**IBM Graphic** selected on **LPT1** and **10 CPI** highlighted, then the
**Install Printer** question offering **ALL** or **ONE**. Choosing **ALL**
copied printer drivers from Disk 6, then requested **DESKMATE 7**.

Swapping media before a copy had finished produced the installer's
*Please insert a disk into drive A* prompt while copying `DRAW.PDM`, which
lives on Disk 8. Mounting Disk 8 and choosing **RETRY** resumed the copy.
The installer then requested **DESKMATE 9**, finished, and updated
`AUTOEXEC.BAT`. The rule the run supports is narrow: answer a numbered
request only after it appears, and treat a mid-copy swap as an insertable
error that RETRY can recover.

### Finish and first launch

Ejecting Disk 9 and confirming a reset returned the machine to `C:\>` with
`SET DMCONFIG=C:\DESKMATE` executed from the updated startup batch file.
`VER` reported **MS-DOS Version 5.00**. From `C:\DESKMATE`, `DESK` opened a
640 × 480 Desktop with Text, Teach Me, the Programs list, Address, Quick
Load, Calendar, and PC-Link shortcuts, and a November 2026 calendar.

**File → About** identified `DESKTOP.PDM` **Version 3.68**, with `DESK.EXE`
68.19, `DMCSR.RES` 3.111, `DMGUF.RES` 2.15, and `DMMDS.RES` 2.10, and the
notice *DeskMate Copyright 1984, 1990 Tandy Corporation*. Escape from the
Desktop opened the exit confirmation, **Press Enter to confirm exit**, and
confirming returned to DOS.

A hard reset from the stopped state was then performed. The machine booted
to `C:\>`, executed the startup batch file, and `DESK` again reached the
Desktop with the clock advanced, which is the cold-launch check for this
run.

## Installed identities

The stopped disk image is 54,525,952 bytes with SHA-256
`e8a2f15b95cfccdc5ddc3058d6678fbeb6ece60b9d3f34e5bfd13d3519144fd8`. It
contains 142 files: 140 under `C:\DESKMATE`, plus `AUTOEXEC.BAT` and
`CONFIG.SYS`.

| Installed file | Bytes | SHA-256 | Cross-media note |
| --- | ---: | --- | --- |
| `DESK.EXE` | 19,047 | `0f2a40243c997276904d2555a117c60eedf0016dde073285e8d63c8345a2eba3` | Same bytes as the five-disk set and the `dm369` set |
| `DESKTOP.PDM` | 72,681 | `85e56146a4da122c6ac646ca76895dcd7375454d8d9e2067b5f25f160daa8c5d` | Same bytes as the five-disk set, reporting 3.68 |
| `DESKTOP.CFG` | 1,070 | `456412de789cfe1680e2be9ae7ae057b10f7afa81548cc1e34f0e33cffed1899` | Same bytes and size as the five-disk set |
| `CALENDAR.PDM` | 72,593 | `819df5658b663aa69b15584abf805062679e97f587f3404738f6e82876e4bd23` | Same bytes as the `dm369` set |
| `TEXT.PDM` | 75,185 | `44cc8632a2c655659bfe524b83e49bc27f85bd0107a5444590b1446398cc5ea7` | Same bytes as the `dm369` set |
| `PC_LINK.PDM` | 72,087 | `3334347668812343e5deef2b6058b4e75f9dd6fe257868f994fee9215f49adbf` | Present; the `dm369` set omits it |
| `HANGMAN.PDM` | 27,027 | `21fc09b9328decbc6c4db1d9e7a7a90862b8b4f766ae84b2d72daccfb4b802d4` | Present with a Desktop shortcut position |
| `AUTOEXEC.BAT` | 93 | `81e3342527a29f11e043564a81af4a71709ced599d995f44632535ad295aa4b9` | Same bytes as the five-disk install |
| `CONFIG.SYS` | 71 | `0b1574c75cf4c4b0f5b25ffa1c14f307098e292002e2b7e10232e15e8080c7c6` | Unchanged from the DOS baseline |

The installation contains no `MUSIC.PDM` or `SOUND.PDM`; the generic
distribution omits the OEM sound modules, as the five-disk set does. The
file mix is 50 `.RES`, 18 `.ACC`, 13 `.PDM`, 12 `.HLP`, 9 `.TUT`, 9 `.PCL`,
6 `.RFD`, 4 `.CFG`, 3 `.FF1`, 3 `.R89`, 2 `.FIL`, and 2 `.EXE` files, plus
individual data and label files.

The result supports a specific reading of the packaging: the nine-ZIP
TVDog set carries the same launcher, Desktop program, shipped Desktop
configuration, and Printer data as the five-disk retail set, while the
`dm369` repackaging shares the application modules but not the Desktop
program or its configuration. Media identity and version identity are
therefore separate questions, which is why the registry records them apart.

## Screenshots

Five native frames were retained privately as a numbered sequence. Three
are published as documentary captures on the
[nine-disk guide](../ecosystem/deskmate-installation-305-ninedisk.md): the
installer banner, the empty destination dialog, and the About dialog. The
desktop frame is published on the same page. Raw frames, the installer
sequence, the disk images, and the installed tree remain outside Git.
[Visual publication policy](../site/visual-assets.md)

## Blockers, limits, and the next bounded trial

- Only one hardware profile was tested. Alternate displays, DOS versions,
  disk geometries, and physical drives remain untested for this media.
- The installer path search across multiple drives was not exercised; every
  swap used drive A.
- The printer phase's file-search behavior was observed on one printer
  choice. Whether choosing **ONE** avoids the Disk 6 lookup is untested.
- The nine-set has no documented factory label set beyond the shipped
  `DESKMATE.LBL` resource; the FAT labels used here are working labels.
- Version identity for the media as a product (catalog number and date
  code) is unconfirmed; the observed strings identify the build, not the
  retail package.

A single bounded follow-up is worthwhile: repeat the run with the **ONE**
printer option to determine whether the printer phase still reads Disk 6,
and record whether the resulting installed file count falls from 140. That
trial uses the same disposable disk and needs no new media.
[Installation roadmap #153](https://github.com/smartyhall/deskmate-formats/issues/153)
