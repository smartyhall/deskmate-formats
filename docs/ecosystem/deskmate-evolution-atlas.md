# DeskMate Evolution Atlas

DeskMate changed from text-mode task panels to a graphical
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
The [capture receipt](../evidence/deskmate-evolution-20261121.json)
records native dimensions, emulated times, and source-image hashes.

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

DeskMate II retained the six task panels in both native runs. On the
SX, F2 exposed old and new filename prompts. The 3000 file sets
launched on an RSX compatibility profile, where Calendar used a
text-mode weekly grid and a separate filename prompt. Nine application
executables match across the SX and 3000 sets, while the launchers
and several support files differ. [SX startup](../research/deskmate-evolution-native-20261121.md#deskmate-ii-010000-on-the-tandy-1000-sx) · [3000 compatibility trial](../research/deskmate-evolution-native-20261121.md#deskmate-ii-tandy-3000-file-sets-on-an-rsx-compatibility-profile)

## Personal DeskMate

The 1000 EX bundle has DOS and two Personal DeskMate disks, with
`INSTALL.EXE` on the first program disk. The 1000 HX combines ROM
startup, a ROM desktop, and floppy-loaded applications. Its nested ZIP
and ImageDisk material establish different media representations. The
TX-associated Personal DeskMate 2 material survives as a downloadable
file set with a manual disk reconstruction recipe. [Tandy Faxback 1378](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01378.txt) · [Personal DeskMate 2 recipe](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/pdm2_360.txt)

The EX disks launched graphically on the SX compatibility profile.
Alt+F opened File, and Tab moved among file panels. On the native HX
profile, the ROM boot menu required a program disk in A: for the
surviving archival copy. The Desktop calls itself DeskMate 2 and
adds Music and a Run dialog. Calendar has a graphical month grid and
buttons for moving through dates. The HX and standalone Personal
DeskMate 2 sets share their launcher and desktop, with differing
runtime bytes. [EX startup](../research/deskmate-evolution-native-20261121.md#personal-deskmate-ex-010100-on-a-1000-sx-compatibility-profile) · [HX startup and file comparison](../research/deskmate-evolution-native-20261121.md#personal-deskmate-hx-media-and-rom-startup)

The standalone Personal DeskMate 2 file set also launched from
reconstructed 360 KiB disks on the SX. Its Disk → Swap command
refreshed the file panels after a floppy change. Text started in
Non-ASCII mode and saved a 35-byte document for the same two lines
that generic 3.00 saved as 13 bytes. [Standalone startup and Text save](../research/deskmate-evolution-native-20261121.md#standalone-personal-deskmate-2-on-the-tandy-1000-sx)

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

Across each entire set, the nine-ZIP layout agrees with the raw
five-disk set on 145 of its 146 unique filenames. The five-ZIP
layout has a different Desktop program and omits PC-Link. Both
alternate layouts preserve the core application binaries.
[Member-by-member summary and scope](../research/deskmate-evolution-native-20261121.md#alternate-305-media-comparison)

### Comparing the two 3.05 desktops

Both installations use a teal desktop with the Text and Programs
panels, the illustrated Teach Me icon, four shortcut buttons, and a
calendar. The alternate five-ZIP installation puts **Hangman** in
the lower-right shortcut where the five raw disks put **PC-Link**.
The installed alternate files omit the PC-Link program and supporting
resources. Both distributions include Hangman and Telecom.
[Matched RSX comparison](../research/deskmate-305-variants-sl2-20261122.md#desktop-program-and-configuration)

### About dialog

Both installations identify the suite as **03.05.00**. The Desktop's
File → About dialog identifies its own module as **3.69** on the
alternate installation and **3.68** on the raw-media control. This
documents two Desktop builds within the same reported suite release.
[Module identities and native captures](../research/deskmate-305-variants-sl2-20261122.md#desktop-program-and-configuration)

### Thesaurus in Text

The alternate distribution's separate Thesaurus archive supplied the
synonym data for Text. With its three resources installed on the hard
disk, the Edit menu looked up a test word and substituted a selected
synonym. Teach Me listed the same nine lessons on both layouts, though
the first introduction screen showed a different sample workspace.
[Thesaurus procedure and lesson comparison](../research/deskmate-305-variants-sl2-20261122.md#file-operations-and-thesaurus)

## Machine-specific DeskMate 3

The TL, TL/2, SL/2, 1100 FD, RL and RL-HD, RLX-HD B, and RSX media
remain separate entries. Tandy documents a ROM desktop on the TL,
EEPROM setup with a disk fallback on the RL, and a compressed
two-disk procedure on the RLX-HD B. Surviving TL, TL/2, and SL/2
program disks contain Music and Sound. The earlier RSX audio trial
used selected OEM modules under generic 3.05. [Tandy Faxbacks 1367](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01367.txt), [1311](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01311.txt), and [1342](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01342.txt) · [RSX audio trial](../research/sound-native-20261118.md)

The SL/2 booted its DOS floppy, and `SETUPSL2` saved the ROM
startup selection. Two reboot controls then left a blank display.
This edition remains an inspected distribution with an observed
startup blocker. [Native SL/2 trial](../research/deskmate-evolution-native-20261121.md#tandy-1000-sl2-startup-blocker)

The RSX OEM 03.04.04 Desktop adds an Applications menu, five
illustrated task tiles, and shortcuts to AOL and Letter Invaders.
The recovered installer copied all six floppies, configured the
printer driver, updated DOS startup, and reset. The hard-disk
launch reproduced the OEM Desktop under Tandy MS-DOS 5.00.
[Reproduced RSX installation and comparison](../research/deskmate-rsx-oem-recovery-20261122.md)

Automatic House 01.08 opens a navigator for Floor Plan, Routine Maker,
and Scheduler. Information Center 3.61 opens a household dashboard
with an agenda, telephone shortcuts, a notepad, and messages. Both
were launched from the installed RSX desktop.
[Automatic House and CP290](../research/deskmate-automatic-house-x10.md) · [Information Center](../research/deskmate-rsx-oem-recovery-20261122.md#information-center)

### RSX household applications

Home Organizer groups household and finance programs by task. Print
Companion opens its own navigator for stationery and graphics, and
Teach Me lists lessons that can start from the installed desktop.
[Native application survey](../research/deskmate-rsx-oem-recovery-20261122.md#other-rsx-applications)

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

1. Test the nine-ZIP 3.05 layout as a disk-order control. Compare more
   Help topics and later tutorial pages with the matched installed
   five-ZIP and five-image controls.
2. Reproduce SL/2 ROM **MS-DOS** startup on a fresh EEPROM
   baseline, then qualify DeskMate startup. Preserve the successful
   floppy-DOS profile for comparison.
3. Locate exact profiles or qualified configurations for the TL,
   TL/2, 1100 FD, RL/RL-HD, and RLX-HD B. The pinned 86Box machine
   table lacks exact profiles for those targets. Confirm the original
   1000, EX, TX, and 3000 on matching hardware when available.
4. Seek identifiable media for Professional DeskMate, generic 3.01,
   and the RLX B floppy-only edition. The current scope is the
   verified collection and the references listed in the matrix.
