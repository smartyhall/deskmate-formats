# DeskMate installation atlas

This atlas records how each DeskMate release is installed and launched on
hardware, or on a reproducible emulated machine, and how far that work has
actually been carried. It separates four questions that are easy to blur:
which product a name refers to, which installation media exist, which
procedure reproduces an installation, and which release has been started
and identified on screen.

Start with a [version-specific guide](#installation-guides) if one exists for
your release. Use the [qualification table](#chronological-release-index) to
see what is proven, and read the [media inventory](#media-inventory-by-release)
only when you need source identities. The machine-readable
[installation registry](deskmate-installation-registry.json) holds the same
status data for tooling, and the
[laboratory installation recipe](deskmate-lab-installation-recipe.md) records
how the emulated environments are prepared.

The November 20, 2026 TVDog audit verified 9,973 originals. That establishes
what was retrieved, not what has been installed. [Mirror audit](../research/tvdog-second-pass-20261120.md)

## Evidence states

Each release carries the highest state reached, and a higher state assumes
the ones below it.

| State | Meaning |
| --- | --- |
| Listed | Named in a period source, archive index, or catalog. Media identity is not established. |
| Acquired | Original bytes are retained privately with a transfer receipt. |
| Verified | Archive size and SHA-256 match the recorded source receipt. |
| Inspected | Selected payloads, labels, or members were examined and described. |
| Installer inspected | The vendor installer ran and its prompts were observed, without a completed installation. |
| Installed | An observed installation completed on a stated environment and reached a working program. |
| Launched | A native first launch was observed and its version identity recorded. |
| Cold-launch qualified | The installation also survived a normal exit and a later cold restart. |

A verified archive can still lack disks, contain damaged files, or depend on
ROM components that the archive does not supply. An archive listing is never
evidence that a release has been recovered.

## Chronological release index

| Release | Lineage | Media basis | Highest state | Guide |
| --- | --- | --- | --- | --- |
| DeskMate 01.01.00 (Tandy 1000) | DeskMate 1 | Two 360 KiB documentation disks | Launched | — |
| DeskMate II 01.00.00 (Tandy 3000) | DeskMate II | Two file sets | Launched | — |
| DeskMate II 01.00.00 (Tandy 1000 SX) | DeskMate II | Four raw 360 KiB disks | Launched | — |
| Personal DeskMate 01.01.00 (1000 EX) | Personal DeskMate | Three raw 360 KiB disks | Inspected | — |
| Personal DeskMate 01.00.00 (1000 HX) | Personal DeskMate | ROM desktop plus file sets | Launched | — |
| Personal DeskMate 2 01.00.00 | Personal DeskMate | One 35-file set for four or five disks | Launched | — |
| Professional DeskMate | Professional | None identified | Listed | — |
| DeskMate 03.00.00 | DeskMate 3 | Five file sets | Installed | — |
| DeskMate 3.01 | DeskMate 3 | None found | Listed | — |
| DeskMate 03.02.00 | DeskMate 3 | Three file sets | Installed | — |
| DeskMate 3.02 (1000 TL) | DeskMate 3 OEM | Three raw 720 KiB disks | Inspected | — |
| DeskMate 03.03.01 | DeskMate 3 | Four file sets | Cold-launch qualified | [3.03.01 guide](deskmate-installation-303.md) |
| DeskMate 3.03 (1000 TL/2) | DeskMate 3 OEM | Four raw 720 KiB disks | Inspected | — |
| DeskMate (1000 SL/2) | DeskMate 3 OEM | ROM desktop plus program disks | Launched | — |
| DeskMate (1100 FD) | DeskMate 3 OEM | Four raw 720 KiB disks | Inspected | — |
| DeskMate 3.04 (1000 RL/RL-HD) | DeskMate 3 OEM | Six raw 720 KiB disks | Inspected | — |
| DeskMate 03.04.03 (1000 RLX-HD B) | DeskMate 3 OEM | Two compressed 1.44 MB disks | Inspected | — |
| DeskMate 03.04.04 (1000 RSX) | DeskMate 3 OEM | Six nested file sets | Cold-launch qualified | — |
| DeskMate 03.05.00 (nine TVDog sets) | DeskMate 3 | Nine file sets | Cold-launch qualified | [Nine-disk guide](deskmate-installation-305-ninedisk.md) |
| DeskMate 03.05.00 (`dm369` sets) | DeskMate 3 | Five file sets plus Thesaurus | Cold-launch qualified | [Comparison](../research/deskmate-305-variants-sl2-20261122.md#alternate-305-installation-media) |
| DeskMate 03.05.00 (five raw images) | DeskMate 3 | Five 720 KiB FAT12 images | Cold-launch qualified | [3.05 guide](deskmate-installation-305.md) |
| DeskMate for the Color Computer | Other lineage | None | Listed | — |
| DeskMate for OS-9 | Other lineage | None | Listed | — |
| WinMate (Windows-era companion) | Other lineage | None | Listed | — |

Four 03.05 packaging lineages now have separate records, and they are not
interchangeable. The nine TVDog sets and the five raw images install the
same launcher and Desktop program but differ in the installer's destination
default and the number of prompts. The `dm369` sets share application
modules with both but ship a different Desktop program, which reports 3.69
rather than 3.68.

## Installation guides

- [Install DeskMate 3.05 from the nine TVDog disk sets](deskmate-installation-305-ninedisk.md):
  new in this atlas, 140 installed files, Desktop 3.68, cold launch verified.
- [Install DeskMate 3.05 on a DOS PC](deskmate-installation-305.md): the
  five-disk retail lineage, including the printer and reset sequence.
- [Install DeskMate 3.03.01 on a DOS PC](deskmate-installation-303.md): the
  earliest generic release with a complete walkthrough, including the disk
  label rules that the installer enforces.
- [Five-numbered-set 3.05 and SL/2 ROM startup](../research/deskmate-305-variants-sl2-20261122.md):
  a dated comparison rather than a step-by-step guide.
- [RSX OEM 03.04.04 recovery](../research/deskmate-rsx-oem-recovery-20261122.md):
  the only completed OEM installer run, recorded as an experiment.

Three installed releases still lack their own guide: generic 3.00 and 3.02,
which have no vendor installer, and the RSX OEM 03.04.04, which does. They
are the next authoring tasks rather than open installation questions.
[Installation roadmap #153](https://github.com/smartyhall/deskmate-formats/issues/153)

## Hardware and operating-system compatibility

The tested work concentrates on Tandy's own machines, because that is where
the OEM distributions expect their ROM components.

| Platform | Documented or observed operating system | Notes from observed runs |
| --- | --- | --- |
| Tandy 1000 SX | Bundled DOS 03.20.02 | DeskMate 01.01.00, DeskMate II, and reconstructed Personal DeskMate 2 reached their desktops |
| Tandy 1000 EX | DOS 02.11.24 per bundled readme | Media inspected; the shipped installer has not been run |
| Tandy 1000 HX | ROM DOS and ROM desktop | ROM startup plus disk-loaded release observed |
| Tandy 1000 SL/2 | ROM DOS 3.30.22 | Requires a factory-initialized EEPROM for both ROM DOS and the ROM desktop |
| Tandy 1000 TL and TL/2 | DOS 3.30.20 and 3.30.22 | Media inspected only |
| Tandy 1100 FD | DOS 3.30.40 per notes | Media inspected only; EMS dependencies open |
| Tandy 1000 RL/RL-HD | DOS 3.30.22 | EEPROM-backed desktop storage; no lab profile yet |
| Tandy 1000 RLX-HD B | Separate DOS 5 media | Compressed 1.44 MB disks read on a related RSX |
| Tandy 1000 RSX | Tandy MS-DOS 5.00 | Generic 3.00, 3.02, 3.03.01, all three 3.05 lineages, and the OEM 03.04.04 were installed here |

Generic DeskMate 3 is described by the archive notes as PC-compatible with
at least 512 KiB RAM. Every completed generic installation in this atlas
used a VGA-capable Tandy 1000 RSX profile with 4 MiB RAM, a PS/2 mouse, and
one 1.44 MB floppy drive; that is a tested configuration, not a manufacturer
minimum. Earlier DOS versions, alternate displays, and physical drives
remain untested for the 03.05 lineages.
[TVDog DeskMate index](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/00_index.txt) ·
[3.05 tested configuration](deskmate-installation-305.md#requirements-and-preparation)

## Tandy Faxback correlation

The Faxback numbers below are cited because they bear on a release covered
here. They are support documents for a particular configuration, not general
compatibility claims, and their disk numbering follows the OEM sets they
describe. Publication of source documents and transcriptions follows the
[Faxback documentation task #154](https://github.com/smartyhall/deskmate-formats/issues/154),
which limits the first phase to material tied to completed research.

| Faxback | Applies to | What it contributes |
| --- | --- | --- |
| [1311](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01311.txt) | DeskMate 3.04 on the 1000 RL | EEPROM-backed desktop storage with a disk fallback |
| [1318](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01318.txt) | DeskMate 3 on the RSX | Printer-port setup, disk-backed `DESKTOP.CFG`, accessory conflicts |
| [1332](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01332.txt) | RSX hardware | Supplied PS/2-style mouse and OEM sound capabilities |
| [1342](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01342.txt) | 03.04.03 on the 1000 RLX | Two compressed high-density disks for the HD edition, five for the floppy edition |
| [1367](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01367.txt) | DeskMate 3.02 on the 1000 TL | ROM desktop and driver components |
| [1378](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01378.txt) | Personal DeskMate on the 1000 HX | ROM desktop and drivers with on-disk applications |

Where a Faxback describes a ROM component, the archive alone cannot complete
the installation; the ROM or EEPROM state is part of the prerequisite.

## Products sharing the name

DeskMate names appear on products outside the PC lineage. The Color Computer
and OS-9 titles are recorded here so they are not mistaken for PC
distributions, and WinMate is a separate Windows-era environment supplied on
Sensation CD media. None of them is covered by the installation procedures or
compatibility statements on this page. Professional DeskMate is a separate,
network-oriented PC edition named in period sources; no verified media or
build has been identified. [Ecosystem catalog](README.md) ·
[Release relationships](deskmate-evolution-atlas.md)

## Media inventory by release

**Reference** identifies an edition in a source. **Verified** means its archive size and SHA-256 match the mirror receipt. **Inspected** means we examined selected payloads, signatures, or filesystems. **Reproduced** means a documented clean installation reached a working program. A verified archive can lack disks, contain damaged files, or depend on hardware or ROM components that the archive does not supply.

The [media manifest](deskmate-installation-media.json) gives the original URLs, byte counts, SHA-256 hashes, exact member names, FAT labels, and selected internal file identities. Short paths in the table are relative to TVDog's [DeskMate directory](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/) unless prefixed with [`system/`](http://ftp.oldskool.org/pub/tvdog/tandy1000/system/). File-set ZIPs preserve the named files, while raw disk images also preserve disk layout. `DESKMATE.LBL` is an application resource, distinct from a FAT volume label.

| Release | Media and structure | Requirements and evidence |
| --- | --- | --- |
| DeskMate 01.01.00 | `system/d1000.zip`, unlabelled raw 360 KiB `MSDOS.DSK` and `DESKMATE.DSK`. `old/1kdisks.zip` supplies TeleDisk counterparts. | Original Tandy 1000 and DOS 02.11.22 per bundled notes. **Launched** with bundled DOS on a Tandy 1000 SX compatibility profile. [Native task screen and startup](../research/deskmate-evolution-native-20261121.md#original-010100-on-a-1000-sx-compatibility-profile) |
| DeskMate II for Tandy 3000 | `3kdm2dk1.zip` program set and `3kdm2dk2.zip` sample set. Launcher says 01.00.00. Companion manual in `3kdm2m.zip`. | **Launched** Desktop and Calendar on the RSX under DOS 5.00. Tandy 3000 and standard PCs according to the [archive index](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/00_index.txt). Minimum DOS and display requirements are open. |
| DeskMate II for Tandy 1000 SX | `system/d1000sx.zip`, four unlabelled raw 360 KiB disks. `DISK3.DSK` holds launcher 01.00.00. The older `sxdisk2.zip` and `sxdisk3.zip` have three and four TeleDisk images respectively. | **Launched** on the emulated 1000 SX with bundled DOS 03.20.02. Three TeleDisk payloads recur under different member names. Keep the SX and 3000 media distinct despite the shared version number. [TVDog system index](http://ftp.oldskool.org/pub/tvdog/tandy1000/system/00_index.txt) |
| Personal DeskMate for the 1000 EX | `system/d1000ex.zip`, three unlabelled raw 360 KiB images. `PDDISK1.DSK` contains `INSTALL.EXE` and launcher 01.01.00, and `PDDISK2.DSK` is the second DeskMate disk. `old/exdisks.zip` supplies TeleDisk counterparts. | 1000 EX and DOS 02.11.24 per readme. Three raw images inspected. The shipped installer has not been run. |
| Personal DeskMate for the 1000 HX | `system/hxdisks.zip` has nested `personal.zip` and `msdos.zip` file sets. Launcher 01.00.00. `old/hxdisks.zip` is byte-identical. `system/d1000hx.zip` holds a separate `HXORIG.IMD` dump. | The file-set readme specifies HX-only software, boot from ROM, and a nonbootable DOS utility disk. Tandy documents a ROM desktop and drivers plus on-disk applications. **Launched** ROM startup and disk-loaded DeskMate 2 on the HX profile. The separate ImageDisk utility disk remains untested. [Faxback 1378](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01378.txt) |
| Personal DeskMate 2 | `pdm2.zip`, 35 files with launcher 01.00.00, `MAINMENU.PDM`, and `DMCSR.MOD`. Archive recipe arranges files on four or five 360 KiB disks, with DOS utilities supplied separately. | TVDog lists Tandy 1000 video, 256 KiB RAM, and the TX bundle. **Launched** from reconstructed 360 KiB disks with DOS 03.20.02 on the SX, and saved a native Text control. Original labels and factory disk layout remain open. [Archive recipe](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/pdm2_360.txt) |
| Professional DeskMate | Period sources identify a separate, network-oriented edition and a Tandy 3000 HL bundle. | Reference only. No verified installer or exact build identified here. [1988 Radio Shack catalog](https://www.worldradiohistory.com/Archive-Catalogs/Radio-Shack/Radio-Shack-1988.pdf) · [*PC World*, May 1988, p. 13](https://vintageapple.org/pcworld/pdf/PC_World_8805_May_1988.pdf) |
| Generic DeskMate 3.00 | `dm300dk1.zip`–`dm300dk5.zip` contain startup/Desktop, office apps, Draw, Filer, and dictionary sets. Launcher 03.00.00. | **Reproduced** on the RSX with Tandy DOS 5.00, using manual DOS copy and `DMCONFIG`. [Native 3.00 procedure](../research/deskmate-evolution-native-20261121.md#generic-030000-on-the-rsx) [Archive instructions](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm300dsk.txt) |
| DeskMate 3.01 | A 1994 community program list associates this version with `SWITCH.EXE`. | Reference only. The filename search found no corresponding distribution in the inspected ZIP member listings. [Contemporary program list](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm_progs.txt) |
| Generic DeskMate 3.02 | `dm302dk1.zip`–`dm302dk3.zip` cover startup/video, Text/Calendar/Address Book, and remaining apps/help. Launcher 03.02.00. | **Reproduced** by DOS copy on the RSX. The archive instructions mistakenly name the `dm300dk*` files. [Tested procedure](../research/deskmate-303-305-comparison.md#deskmate-302-stretch-experiment) |
| DeskMate 3.02 for the 1000 TL | `system/d1000tl.zip`, three unlabelled raw 720 KiB images `TLDISK1.DSK`–`TLDISK3.DSK`, one DOS and two DeskMate. `old/tldisk2.zip` supplies TeleDisk images. | DOS 3.30.20. All three raw disks inspected. Calendar and `PERSONAL.CAL` on the second, Music and Sound on the third. The version is from the bundle notes. Tandy identifies the desktop and some drivers as ROM components. [Faxback 1367](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01367.txt) |
| Generic DeskMate 3.03 | `dm303dk1.zip`–`dm303dk4.zip`, four file sets for 720 KiB or larger disks. Startup has `INSTALL.EXE`, `INSTALL.PDM`, and launcher **03.03.01**. The remaining disks cover Desktop/Text, Address Book/Filer, and Draw/communications/Worksheet. | **Reproduced** on the RSX with Tandy MS-DOS 5.00. Use `DESKMATE_1` through `DESKMATE_4` as FAT labels. [Native installation guide](deskmate-installation-303.md) |
| DeskMate 3.03 for the 1000 TL/2 | `system/d1000tl2.zip`, four raw 720 KiB images. DOS first, then `DESKMATE_1`–`DESKMATE_3`. TeleDisk counterparts in `old/tl2disks.zip`. | DOS 3.30.22. `INSTALL.PDM` on DeskMate 1 and Music and Sound on DeskMate 3. Raw disks inspected. The bundle notes identify 3.03, with the exact build still open. |
| DeskMate for the 1000 SL/2 | `system/1000SL2D.zip`, DOS and three raw 720 KiB program disks. | **Launched** on the exact SL/2 profile. Restoring the factory EEPROM configuration enabled both ROM DOS 3.30.22 and the ROM DeskMate Desktop. Address Book, Calendar, Music, and Sound opened from their program disks. [EEPROM procedure and media controls](../research/deskmate-305-variants-sl2-20261122.md#sl2-rom-startup-on-a-factory-initialized-eeprom) |
| DeskMate for the 1100 FD | `system/d1100fd.zip`, raw 720 KiB `DOSGWB.DSK`, `DESK1.DSK`, `DESK2.DSK`, and `EMSDRV.DSK`. DeskMate labels `DESKMATE_1` and `DESKMATE_2`. `old/11fddisk.zip` has TeleDisk counterparts. | DOS 3.30.40. Calendar and `PERSONAL.CAL` on DeskMate 2. Raw disks inspected. Exact version and EMS dependencies remain open. |
| DeskMate 3.04 for the 1000 RL/RL-HD | `system/d1000rl.zip`, six raw 720 KiB images. DOS plus `DESKMATE_1`, `DESKMATE_2`, `KITCHEN`, `FINANCE`, and `PERSONAL`. `d1000rl_alternates.zip` adds alternate dumps and a `BACKUP`-labelled SmartDrive disk. `old/rldisks.zip` is TeleDisk. | DOS 3.30.22. Raw disks inspected. `INSTALL.PDM` and OEM Music and Sound are present. Tandy describes EEPROM-backed desktop storage with a disk fallback. [Faxback 1311](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01311.txt) |
| DeskMate 03.04.03 for the 1000 RLX-HD B | `system/dskrlxhd.zip`, raw 1.44 MB `DESK3431.IMG` and `DESK3432.IMG`, labeled `DESKMATE_1` and `DESKMATE_2`. Version from supplied notes and Tandy’s bulletin. `1000RLX_HD-B.zip` separately preserves a populated `DESKMATE/` tree. | Raw disks and populated tree inspected. DOS 5 is separate in `system/e1000rlx.zip`. Tandy specifies two compressed high-density disks for the HD edition and five uncompressed disks for the floppy-only RLX B. The five-disk variant remains reference-only here. The populated tree includes a truncated Cobb FF1. [Faxback 1342](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01342.txt) · [RLX resource analysis](tvdog-reference.md) Both compressed disks were readable on the related RSX after booting the RLX B DOS floppy. [Compatibility trial](../research/deskmate-305-variants-sl2-20261122.md#rlx-hd-b-dos-and-compressed-media-on-the-rsx) |
| DeskMate 03.04.04 for the 1000 RSX | `system/rsxdisks.zip` contains nested file sets `DISK1.ZIP`–`DISK6.ZIP` and `UTILS.ZIP`. The same bytes occur under `system/old/`. Startup launcher says 03.04.04 and separately carries a 04.03 runtime marker. | **Reproduced** on the RSX with separate Tandy MS-DOS 5.00 and six 1.44 MB working floppies. The native installer configured a printer, copied into `C:\DESKMATE`, updated `AUTOEXEC.BAT`, and reset to the hard disk, where `DESK` launched the OEM Desktop. [Reproduced RSX installation](../research/deskmate-rsx-oem-recovery-20261122.md) |
| Generic DeskMate 03.05.00, nine ZIPs | `dm305dk1.zip`–`dm305dk9.zip`: startup/installer, Desktop/Text, communications, Address Book/Calendar, Filer/Form Setup, accessories and printer data, clipboard and spelling, Draw and printer drivers, and video or font resources. | **Reproduced** on a disposable RSX DOS clone with Tandy MS-DOS 5.00. The installer reports 03.05.00, leaves the destination field empty, reads printer `.ACC` data from Disk 6, and installs 140 files. Desktop About reports 3.68. [Nine-disk installation guide](deskmate-installation-305-ninedisk.md) · [Campaign record](../research/release-installation-atlas-001.md) · [Instructions](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm305dsk.txt) |
| Generic DeskMate 03.05.00, `dm369dks*` | Five numbered file sets and a separate Thesaurus companion. | **Reproduced** on a Tandy 1000 RSX with Tandy MS-DOS 5.00. Installer reports 03.05.00, and Desktop About reports 3.69. Hangman takes the PC-Link shortcut position and the installed collection omits PC-Link. [Reconstructed media and native comparison](../research/deskmate-305-variants-sl2-20261122.md#alternate-305-installation-media) |
| Generic DeskMate 03.05.00, lab set | Five raw 720 KiB FAT12 images, labels `DESKMATE_1`–`DESKMATE_5`, from a separate preservation source. | **Reproduced** on a Tandy 1000 RSX with Tandy MS-DOS 5.00. [Observed procedure and exact image hashes](deskmate-installation-305.md) |

## Scope and compatibility

Read-only inspection used the settled transfer manifest, the central directories of 896 ZIPs, the existing searchable archive index, and source notes. The manifest records 83 ZIP originals rehashed against their transfer receipts, including alternate dumps, runtime sets, and DOS-only packages screened out of the table. Selected nested ZIP members were hashed after decompression. Raw images were listed with 7-Zip 26.05 and selected FAT members read with `7z x -so`. A null FAT label means the reader found no label. TeleDisk and ImageDisk inspection covered signatures and member hashes. Their sector contents and equivalence to named raw disks remain untested. The 1994 community register also names CoCo and Model IV versions and gives tentative ROM edition assignments. Unindexed or unsupported nested content can still conceal candidates. [Contemporary program list](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm_progs.txt)

Across the generic 3.00, 3.02, 3.03, and nine-disk 3.05 sets, the only filename repeated with different bytes within each set was `DESKTOPD.CFG`. Preserve the disk-specific copies, especially when testing a manual hard-disk install.

The Development System's three runtime disks, the Express Publisher standalone runtime, and the SAT Trainer package are application or development media. `dm302drv.zip`, `dm305drv.zip`, `drivers.zip`, and the `dmvid*` series supply device files. `dos5desk.zip` contains optional DOS batch helpers. `diskin.zip`, `f2ddos.zip`, and `macros.zip` install individual utilities or accessories. Sensation CD media supply the separate WinMate environment. [TVDog application matrix](tvdog-reference.md) · [DeskMate archive index](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/00_index.txt) · [Optical inventory](../research/tvdog-second-pass-20261120.md#optical-media)

## Native comparisons and open coverage

The 3.03.01 and 3.05 Calendar and Address Book tests used equivalent
synthetic records and disposable copies in both directions. Plain Text
saves also matched. A separate 3.02 trial reached the Desktop and wrote
Calendar and Address Book files. [Native comparison and remaining questions](../research/deskmate-303-305-comparison.md)

Open items are recorded in the [registry](deskmate-installation-registry.json)
so that a later session can pick them up without re-deriving this status.
The largest gaps are the unrun Personal DeskMate 1000 EX installer, the
absent 1000 RL machine profile, native version displays for several OEM
media, guides for the three installed releases that lack one, and any
verified Professional DeskMate media. [Installation roadmap #153](https://github.com/smartyhall/deskmate-formats/issues/153) ·
[Faxback documentation #154](https://github.com/smartyhall/deskmate-formats/issues/154)

Future version guides can follow the [installation guide template](deskmate-installation-template.md).
