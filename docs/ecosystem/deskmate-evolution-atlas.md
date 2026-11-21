# DeskMate Evolution Atlas

DeskMate changed from a screen of numbered or named tasks to a graphical
environment of menus, file panels, and application shortcuts. Tandy also
distributed machine-specific editions whose desktop, drivers, or startup
programs depended on the computer's firmware. This atlas follows surviving
distributions and native observations. [Historical introduction](../history/introduction.md) · [Installation-media index](deskmate-installations.md)

## Reading the atlas

The [release matrix](deskmate-evolution-releases.json) assigns stable
identifiers to the verified distributions, acquisition variants, and
documentary leads. Media identities include the original archive SHA-256,
length, and provenance. The [installation manifest](deskmate-installation-media.json)
retains image and member identities where measured. An entry can advance
from documented to verified, inspected, launched, and reproduced. A
successful launch on related hardware is evidence for that profile.

The early Tandy 1000 association is dated to the **1984 product era**.
The **1988** catalog and trade coverage document distinct later editions,
including Professional DeskMate. The **1994** community listing is the
date of that listing, and supports the DeskMate 3.01 lead. These dates
describe different events. The release matrix leaves exact release
dates open where the sources do. [Tandy 1000 context](../history/introduction.md#from-the-first-tandy-1000-to-deskmate-3) · [1988 Radio Shack catalog](https://www.worldradiohistory.com/Archive-Catalogs/Radio-Shack/Radio-Shack-1988.pdf) · [1988 *PC World* coverage](https://vintageapple.org/pcworld/pdf/PC_World_8805_May_1988.pdf) · [1994 program list](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm_progs.txt)

## Original DeskMate and DeskMate II

The original Tandy 1000 disk set contains separate DOS and DeskMate
floppies. Its launcher says 01.01.00. The Tandy 3000 and Tandy 1000 SX
DeskMate II copies both report 01.00.00. The 3000 program and sample
sets and the SX four-image bundle each have independent media
identities. [Early media evidence](deskmate-installations.md#version-and-installation-media-comparison)

On the 1000 SX compatibility profile, the original 01.01.00 launched
from its own DOS 2.11 and program floppies. Its text-mode screen has
six task panels, a calendar, today's events, and visible function-key
commands. The original 1000 target remains to be qualified.
[Native startup and navigation record](../research/deskmate-evolution-native-20261121.md#original-010100-on-a-1000-sx-compatibility-profile)

## Personal DeskMate

The 1000 EX bundle has DOS and two Personal DeskMate disks, with
`INSTALL.EXE` on the first program disk. The 1000 HX combines ROM
startup, a ROM desktop, and floppy-loaded applications. Its nested ZIP
and ImageDisk material establish different media representations. The
TX-associated Personal DeskMate 2 material survives as a downloadable
file set with a manual disk reconstruction recipe. [Tandy Faxback 1378](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01378.txt) · [Personal DeskMate 2 recipe](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/pdm2_360.txt)

## Generic DeskMate 3

The 3.00 and 3.02 archive instructions specify manual DOS copying and
`DMCONFIG`. The reproduced 3.03.01 and 3.05 installations instead use
numbered floppy prompts, configure DOS startup, and reset. DeskMate
3.05's verified five-image installer adds printer and driver-copy
choices. [3.00 archive instructions](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm300dsk.txt) · [3.02 native record](../research/deskmate-303-305-comparison.md#deskmate-302-stretch-experiment) · [3.03.01 installation](deskmate-installation-303.md) · [3.05 installation](deskmate-installation-305.md)

The 3.00 five-disk copy also worked on the RSX. It opens a graphical
file-panel Desktop with Hangman in the slot that 3.02 uses for Draw.
Calendar opened from the Run dialog, and Text saved a synthetic
two-line document matching the 3.03.01 and 3.05 controls.
[Native 3.00 installation and Text save](../research/deskmate-evolution-native-20261121.md#generic-030000-on-the-rsx)

On the matched RSX profile, 3.02 shows five file panels and a calculator,
3.03.01 uses a blue workspace with three shortcut buttons, and 3.05
uses a teal workspace with four. The 3.03.01 and 3.05 Calendar and
Text comparisons retain closely matching dialog layouts. Navigation
can differ even where screens look similar. [Native desktop, menu, and application comparisons](../research/deskmate-303-305-comparison.md#desktop-menus-and-dialogs)

The nine-ZIP, alternate five-ZIP, and verified five-image 3.05 layouts
share a launcher identity. The alternate five-ZIP layout has 132
matching same-name files across the corresponding raw disks, as well
as differing or absent files. Its sixth archive adds Thesaurus
material. [3.05 media comparison](deskmate-installations.md#version-and-installation-media-comparison)

## Machine-specific DeskMate 3

The TL, TL/2, SL/2, 1100 FD, RL and RL-HD, RLX-HD B, and RSX media
remain separate entries. Tandy documents a ROM desktop on the TL,
EEPROM setup with a disk fallback on the RL, and a compressed
two-disk procedure on the RLX-HD B. Surviving TL, TL/2, and SL/2
program disks contain Music and Sound. The earlier RSX audio trial
used selected OEM modules under generic 3.05. [Tandy Faxbacks 1367](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01367.txt), [1311](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01311.txt), and [1342](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01342.txt) · [RSX audio trial](../research/sound-native-20261118.md)

## Native observation procedure

1. Match the archive size and hash, identify boot and program media,
   and clone or prepare an isolated writable profile with saved
   configuration and firmware state.
2. Capture POST and DOS or ROM startup, then record the exact launcher
   path, version evidence, first desktop, graphics mode, and native
   dimensions. Use authenticated socket input with held checkpoints.
3. Sweep the menu and record the active controls, keyboard navigation,
   program launch, a basic application screen, file dialog, and exit
   path. Record field values and whether a save actually occurred.
4. Where the release accepts it, use October 23, 2026, noon, and
   synthetic text `ALPHA` and `BETA`. Note clock or hardware
   differences, and capture before and after states where they matter.
5. Preserve elapsed emulated time, screenshots, and disk receipts.
   End an unsuccessful trial at an observable condition, and name
   the next dependency or control. [86Box procedure](../research/86box-client.md) · [Visual-evidence policy](../site/visual-assets.md)

## Continuation

Use the matrix's evidence level and uncertainties to select the next
trial. Keep the 3.02, 3.03.01, and 3.05 controls available for comparison.
For Professional DeskMate, 3.01, and the RLX B floppy-only edition,
seek identifiable installation media. A negative inventory result
records the limits of the currently checked collection.
