# DeskMate installation atlas

This atlas records how each DeskMate release is installed and launched on
hardware, or on a reproducible emulated machine, and how far that work has
actually been carried. It separates four questions that are easy to blur:
which product a name refers to, which installation media exist, which
procedure reproduces an installation, and which release has been started
and identified on screen.

Start with a [version-specific guide](#installation-guides) if one exists for
your release. Use the [qualification table](#chronological-release-index) to
see what is proven, and read the [media inventory](deskmate-installation-media-by-release.md#media-inventory-by-release)
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
| DeskMate 03.00.00 | DeskMate 3 | Five file sets | Installed | [3.00 guide](deskmate-installation-300.md) |
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
- [Install generic DeskMate 3.00 on a DOS PC](deskmate-installation-300.md):
  the earliest generic release with a walkthrough, which has no vendor
  installer and is copied by hand before `DMCONFIG` is set.
- [Install DeskMate 3.03.01 on a DOS PC](deskmate-installation-303.md): the
  earliest generic release with a vendor installer walkthrough, including
  the disk label rules that the installer enforces.
- [Five-numbered-set 3.05 and SL/2 ROM startup](../research/deskmate-305-variants-sl2-20261122.md):
  a dated comparison rather than a step-by-step guide.
- [RSX OEM 03.04.04 recovery](../research/deskmate-rsx-oem-recovery-20261122.md):
  the only completed OEM installer run, recorded as an experiment.

Two installed releases still lack their own guide: generic 3.02, which has
no vendor installer, and the RSX OEM 03.04.04, which does. They are the next
authoring tasks rather than open installation questions.
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

## DeskMate installation media by release

Release identity and media identity are separate findings. One version number
can ship as several disk sets, assembled from different source archives, with
different installer defaults and different program builds. The
[installation media inventory](deskmate-installation-media-by-release.md#media-inventory-by-release)
records the archive names, sizes, hashes, members, FAT labels, and internal file
identities behind every release below, and distinguishes a media reference from
a verified archive and from a reproduced installation.

| Media family | Releases covered | Shape |
| --- | --- | --- |
| Original and DeskMate II | 01.01.00, II 01.00.00 | Raw 360 KiB disks and file sets |
| Personal DeskMate | 01.01.00, 01.00.00, 2 01.00.00 | Raw 360 KiB disks, ROM desktops, one 35-file set |
| Generic DeskMate 3 | 03.00.00 through 03.05.00 | Three to nine file sets, or five raw 720 KiB images |
| Tandy 1000 OEM | SL/2, TL, TL/2, 1100 FD, RL, RLX-HD B, RSX | ROM components plus labelled 720 KiB or 1.44 MB disks |
| Other lineages | Color Computer, OS-9, WinMate, Professional | No verified PC installation media |

[Installation media inventory](deskmate-installation-media-by-release.md) ·
[Media manifest](deskmate-installation-media.json)

## Version and installation media comparison

The 03.05 packaging lineages show why version and media are separate questions.
All four report 03.05.00 and none is a substitute for another.

| Lineage | Media | Installer destination | Desktop About |
| --- | --- | --- | --- |
| Nine TVDog sets | `dm305dk1.zip` through `dm305dk9.zip`, rebuilt as nine 720 KiB images | Empty field | `DESKTOP.PDM` 3.68 |
| Five raw images | Five 720 KiB FAT12 images, `DESKMATE_1` through `DESKMATE_5` | Prefilled `C:\DESKMATE` | `DESKTOP.PDM` 3.68 |
| `dm369` sets | Five numbered file sets plus Thesaurus | Prefilled `C:\DESKMATE` | `DESKTOP.PDM` 3.69 |
| Retained nine-set installation | Installed tree from the nine-set run | Not applicable | `DESKTOP.PDM` 3.68 |

The installed `DESK.EXE`, `DESKTOP.PDM`, and `DESKTOP.CFG` from the nine-set run
match the five-disk retail lineage, while `CALENDAR.PDM` and `TEXT.PDM` match the
`dm369` set. A shared launcher does not make two collections interchangeable.
Across the generic 3.00, 3.02, 3.03, and nine-disk 3.05 sets, the only filename
repeated with different bytes within one set was `DESKTOPD.CFG`; keep the
disk-specific copies.
[Nine-disk guide](deskmate-installation-305-ninedisk.md) ·
[Media inventory](deskmate-installation-media-by-release.md)

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
media, guides for the two installed releases that lack one, and any
verified Professional DeskMate media. [Installation roadmap #153](https://github.com/smartyhall/deskmate-formats/issues/153) ·
[Faxback documentation #154](https://github.com/smartyhall/deskmate-formats/issues/154)

Future version guides can follow the [installation guide template](deskmate-installation-template.md).
