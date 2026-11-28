# DeskMate installation media by release

This page is the detailed companion to the [installation atlas](deskmate-installations.md).
It records which archives and disk images carry each release, how those
identities were established, and why a shared version number does not imply
shared media. The atlas keeps the qualification state and the procedures;
this page keeps the source identities behind them. The machine-readable
[media manifest](deskmate-installation-media.json) holds the same data for
tooling.

**Reference** identifies an edition in a source. **Verified** means its archive
size and SHA-256 match the mirror receipt. **Inspected** means we examined
selected payloads, signatures, or filesystems. **Reproduced** means a
documented clean installation reached a working program. A verified archive
can lack disks, contain damaged files, or depend on hardware or ROM components
that the archive does not supply.

## Media inventory by release

The manifest gives the original URLs, byte counts, SHA-256 hashes, exact
member names, FAT labels, and selected internal file identities. Short paths
in the table are relative to TVDog's
[DeskMate directory](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/)
unless prefixed with [`system/`](http://ftp.oldskool.org/pub/tvdog/tandy1000/system/).
File-set ZIPs preserve the named files, while raw disk images also preserve
disk layout. `DESKMATE.LBL` is an application resource, distinct from a FAT
volume label.

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

## Related records

- [Installation atlas](deskmate-installations.md): qualification state, guides,
  compatibility, and Faxback correlation.
- [Installation registry](deskmate-installation-registry.json): the same status
  data as structured records.
- [DeskMate evolution atlas](deskmate-evolution-atlas.md): what each observed
  Desktop build looked like at runtime.
