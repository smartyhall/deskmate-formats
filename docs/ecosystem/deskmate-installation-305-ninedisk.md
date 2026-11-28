# Install generic DeskMate 3.05 from the nine TVDog disk sets

This guide follows the November 28, 2026 clean installation of the nine
numbered TVDog file sets, `dm305dk1.zip` through `dm305dk9.zip`, on an
emulated Tandy 1000 RSX. The installer reported **03.05.00**, copied 140
files into `C:\DESKMATE`, reset the machine, and reached a Desktop whose
About dialog identifies `DESKTOP.PDM` as **3.68**. A hard reset then
reproduced the launch. The [campaign record](../research/release-installation-atlas-001.md)
holds the sampled timings and hashes behind each step.

This is a third 3.05 lineage. The [five-disk retail guide](deskmate-installation-305.md)
covers raw 720 KiB images with a different installer default, and the
[`dm369` comparison](../research/deskmate-305-variants-sl2-20261122.md#alternate-305-installation-media)
covers a five-file-set repackaging whose Desktop reports 3.69. Disk order,
prompts, and installed bytes differ, so media from one lineage is not a
substitute for another.

## Requirements and preparation

| Component | Observed working configuration |
| --- | --- |
| Computer | Tandy 1000 RSX, 386SX at 25 MHz, 4 MiB RAM |
| Display and input | Internal Cirrus GD5402 VGA, PS/2 keyboard and mouse. The banner is 80 × 25 text; the installer and Desktop use 640 × 480 in BIOS mode `0x12`. |
| Boot and floppy | Tandy MS-DOS 5.00 on C:, drive A: configured as 3½-inch 1.44 MB and used with 720 KiB media, drive B: absent |
| Storage | Primary IDE master, 52 MiB raw disk, 1,024 cylinders × 4 heads × 26 sectors, FAT16, BIOS drive C set to AUTO |
| Sound and printer | Internal audio configured. IBM Graphic on LPT1 with 10 CPI was accepted; physical printing was outside the run. |
| Emulator | 86Box 7.0 automation build, visible window, held execution advanced in explicit 1,000 ms steps, seed 1, no dynamic recompilation, host clock synchronization disabled |

Start from a clean DOS installation rather than an existing DeskMate
directory. TVDog describes 360 KiB or larger media for this distribution;
the laboratory used 720 KiB working images. Minimum RAM, earlier DOS
versions, and physical hardware were outside the run. [Verified DOS setup](../research/rsx-dos5-baseline.md#installation-procedure) ·
[TVDog 3.05 instructions](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm305dsk.txt)

## Identify the nine file sets

The nine archives are file sets, not disk images. Their bytes were matched
against the [media manifest](deskmate-installation-media.json) before
reconstruction, and the resulting images are working media with synthetic
volume serial numbers. Report the image hashes, not the factory layout, when
reproducing this run.

| Disk | ZIP and ZIP SHA-256 | Working image SHA-256 | Contents worth knowing |
| --- | --- | --- | --- |
| 1 | `dm305dk1.zip`, `5fdd7fe79032860274bd0e679b94ce14eb175ea6dde9296d9cf105cbe1186bec` | `31305d3404c43124f0efa0fd5a628d9e3488e136637db92a2a49595f01995c5e` | Launcher, installer, runtime |
| 2 | `dm305dk2.zip`, `188e8bd58eb9b46b3707014d0e955fb9f2d9f2d49169520606a01714a409a8fa` | `d799bff522047be092004e493016756a3bbfc583e16cb597cb526554868914b0` | Desktop, tutorials, dictionary |
| 3 | `dm305dk3.zip`, `53b2a8bfd45b5c16d4103a65109317288aefbef02d4133da717c9c013b8bfeed` | `a760db22f66df3045014cf741d2ef60352713f32f94ef19b8e5778b5f64558e0` | Communications protocol files |
| 4 | `dm305dk4.zip`, `07fd75ecc80499c17260dd9e2c8889e13a889efc4c73ad686853396c39ff6066` | `9c413bdc3f95ebe94e23674f6eb443e7561f2dcf4f0fd64b6baf33625bcebe15` | Calendar, Address, Filer support |
| 5 | `dm305dk5.zip`, `8d5b2843e8b9de9d69ed6d1f2fb08ade76527bea3f5f5cf5a219c44774ec677c` | `dbd4f2ed518d902c577620332885d84786e7cee6247a8db3c22bfec239ee5154` | Database reader and update resources |
| 6 | `dm305dk6.zip`, `d6395d8bc3d21ed1bf66d49f53161287af89d9b338487004898a778ed5118d3b` | `145f112ddf3d5f643ba6bbe5797b8cf3642e5a507587c31c91c6f88be9c58207` | Accessories and the `.ACC` printer data |
| 7 | `dm305dk7.zip`, `b7d34274cb95797691f997daed53721c57b8d7c1c31e98d93febaaf27d3c3d02` | `e0c5f4911187fc166fd26cb622aeb18edc005b4c7b69ef88b691145fb6716f94` | Clipboard and spelling resources |
| 8 | `dm305dk8.zip`, `d32d6c3fe6692112c8bd3f7c689649cf20222de6de8ae94ec28ee7e7c7c5e3e4` | `7e32e26ac0bf1b76f848cc62208e599b81b93c1b4ad1b5837cdf1ed305e92c0a` | Draw and printer driver files |
| 9 | `dm305dk9.zip`, `52befdd828e7065fc2e1fde60c010693d946ca5e4c477703f9c43564086cd883` | `2484a3536da18a6f2816a8c879d1fa779502ff1155ccd6ca7acab7bfff91d3f8` | Video and font resources |

From the repository root, reconstruct the working images from the private
mirror's `originals` directory into an existing empty private directory:

```text
python tools/experimental/deskmate_install_media.py 305 <originals> <output>
```

The tool verifies each ZIP against the manifest, writes uppercase DOS
filenames with their original timestamps, and labels the images
`DESKMATE_1` through `DESKMATE_9`. Keep the ZIPs, the images, and the
resulting installed tree outside Git.

## Start the installer

Boot to `C:\>` with no floppy mounted, insert Disk 1 in A:, and change to A:
before running the installer. The run sampled the banner **DeskMate /
Version: 03.05.00 / Copyright 1984,1990 Tandy Corporation** at 19,518
emulated ms, before the graphics installer appeared.

```dos
A:
INSTALL
```

Plain `INSTALL` from `C:` was not tried in this run. In the five-disk run,
the same command from `C:` asked for the drive containing DeskMate 1.

## Set the destination

The **Installation Directory** field opened empty in this lineage; the
five-disk set prefilled `C:\DESKMATE`. Type `C:\DESKMATE` and press Enter.
Pace the keystrokes if you drive the guest through the automation socket:
an unpaced burst in this run delivered a truncated path and the installer
reported a filename error until the value was re-entered.

## Change disks and answer the printer prompts

Wait for each **Disk Needed** prompt, mount the named image in A:, and press
Enter once. The observed order was Disk 2 through Disk 9, with no skips.
The dialogs show human-readable names with spaces while the working FAT
labels use underscores.

After the numbered copies, **Printer Settings** reports *File Not Found* for
`DMPDIBMM.ACC` and asks for a disk containing it. That file is on Disk 6.
Supply Disk 6, keep **IBM Graphic** on **LPT1**, keep **10 CPI**, and choose
**ALL** when asked whether to copy all printer drivers or only the selected
one. The installer then copies drivers from Disk 6 and requests
**DESKMATE 7**, and later **DESKMATE 9**.

Do not swap media while a copy is in progress. A premature swap during the
driver phase produced *Please insert a disk into drive A* while copying
`DRAW.PDM`, which is on Disk 8. Mounting Disk 8 and choosing **RETRY**
resumed the copy.

## Finish and restart

When the installer reports that it is updating `AUTOEXEC.BAT` and will
reset, eject Disk 9 and confirm. The machine returns to `C:\>` with
`SET DMCONFIG=C:\DESKMATE` executed from the startup batch file. `VER`
should report **MS-DOS Version 5.00**. The installer does not launch
DeskMate automatically.

## Launch and verify

```dos
C:
CD \DESKMATE
DESK
```

The first Desktop showed Text, Teach Me, the Programs list, Address, Quick
Load, Calendar, and PC-Link shortcuts, and a month calendar. Open
**File → About** to identify the build: this lineage reports `DESKTOP.PDM`
**Version 3.68**, `DESK.EXE` 68.19, `DMCSR.RES` 3.111, `DMGUF.RES` 2.15,
and `DMMDS.RES` 2.10. Escape opens the exit confirmation, **Press Enter to
confirm exit**.

After confirming the exit, a hard reset reproduced the same Desktop from
the installed disk, which is the cold-launch check for this run.

| Installed file | Bytes | SHA-256 |
| --- | ---: | --- |
| `DESK.EXE` | 19,047 | `0f2a40243c997276904d2555a117c60eedf0016dde073285e8d63c8345a2eba3` |
| `DESKTOP.PDM` | 72,681 | `85e56146a4da122c6ac646ca76895dcd7375454d8d9e2067b5f25f160daa8c5d` |
| `CALENDAR.PDM` | 72,593 | `819df5658b663aa69b15584abf805062679e97f587f3404738f6e82876e4bd23` |
| `PC_LINK.PDM` | 72,087 | `3334347668812343e5deef2b6058b4e75f9dd6fe257868f994fee9215f49adbf` |
| `AUTOEXEC.BAT` | 93 | `81e3342527a29f11e043564a81af4a71709ced599d995f44632535ad295aa4b9` |

The stopped disk image is 54,525,952 bytes with SHA-256
`e8a2f15b95cfccdc5ddc3058d6678fbeb6ece60b9d3f34e5bfd13d3519144fd8`. Fresh
installations may produce different disk hashes.

## Troubleshooting and evidence limits

- If the installer reports a filename error at the destination dialog,
  clear the field and re-enter a complete `C:\DESKMATE` path. A truncated
  value is an input-pacing artifact, not a rejected directory.
- If a numbered disk is requested repeatedly, check that the mounted image
  matches the requested number and that A: is the current drive.
- A mid-copy media swap can leave the installer asking for a disk while a
  file such as `DRAW.PDM` is missing. Mount the disk that contains the named
  file and choose **RETRY**.
- The generic distribution ships no Music or Sound modules; their absence
  after installation is expected and does not indicate a failed copy.
- One hardware profile, one floppy drive, default destination, and the
  **ALL** printer option were tested. The **ONE** option, alternate displays,
  earlier DOS versions, and physical drives remain untested.

The published illustrations are native guest frames. Original ZIPs, disk
images, complete installed files, and raw frame sequences are held
privately. [Visual publication policy](../site/visual-assets.md) ·
[Installation atlas](deskmate-installations.md) · [Installation roadmap #153](https://github.com/smartyhall/deskmate-formats/issues/153)
