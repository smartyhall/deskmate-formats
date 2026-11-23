# TVDog descriptive directory index review

The preserved November 20, 2026 snapshot contains 62 directory listings and
9,973 file URLs. The November 23 offline verification reconciled the saved
listings, manifest, transfer database, and local bytes. All 9,973 originals
matched their recorded sizes and SHA-256 hashes. Every searchable-archive
source row agreed with the mirror manifest by URL, size, SHA-256, and
indexed status. This covers the
discovered snapshot. The [initial mirror verification](tvdog-mirror-verification.md)
describes an earlier, partial transfer.

TVDog's Tandy readme directs readers to its descriptive indexes. The saved
tree contains 14 files named `00_index.txt`. Six readmes and the
top-level Tandy directory guide supplement them, covering 19 distinct
directories in all. For the other 43 directories, the saved server listings
provide discovery coverage. Many commercial release subdirectories list
disk archives with no separate descriptive text file. [Tandy archive readme](http://ftp.oldskool.org/pub/tvdog/tandy1000/readme.txt) · [Tandy directory guide](http://ftp.oldskool.org/pub/tvdog/tandy1000/dirlist.txt)

The review joined each parsed entry to the named file in the same directory,
retaining wrapped descriptions, line ranges, listed sizes and dates, and
unmatched rows. It then compared selected entries with the searchable
database, readmes and manuals inside packages, nested archive members,
executable metadata, historical catalogs, and acquisition records. The
original descriptions, per-directory inventory, member identities, and
reconciliation receipts remain in the private lab. Index dates describe
archive entries. Product versions below come from the stated evidence.
[Offline archive index](../../tools/archive/intelligence.md) · [Acquisition records](acquisitions.md)

Two documentation-index filenames, `3l4101.zip` and `3kdocm.zip`, have
no exact sibling in the saved server listing. Their index entries describe
Tandy 3000 DOS manuals. Both discrepancies are retained in the private
reconciliation. [Documentation index, lines 177–185](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/00_index.txt)

## New catalog entries

The source column gives the original index line or file. Package
documentation supplies stated requirements, which remain untested unless
the evidence column cites an existing native observation.

| Software and archive | TVDog source | Evidence and verification limits |
| --- | --- | --- |
| DeskHelp demo · `deskhe.zip` | DeskMate 118–120 | `DH-DEMO.EXE` identifies demo 1.00.00, credits Bobby Ballard, and names Atmospheres. TVDog names DeskMate 1 and II and excludes Personal DeskMate and DeskMate 3. The full release remains open. |
| Disk Info · `diskin.zip` | DeskMate 136–138 | `DISKINFO.PDM` identifies Disk Info 3.01 and Bob Jack Software. TVDog describes a boot-sector viewer and excludes RAM disks. |
| Kaleidocubes · `kubes.zip` | DeskMate 343 | `KUBES.PDM` matches the member in RSX Disk 6 and the RLX HD-B bundle by SHA-256. The ZIP includes `KUBES.HLP` and `.KUB` files. Publisher and product version remain open. |
| Letter Invaders · `li.zip` | DeskMate 344 | `LI.PDM` matches RSX Disk 1 and the RLX HD-B bundle. The prior RSX About dialog identifies Kriya Systems and version 1.0. Udut also associates it with Typing Tutor IV, whose distribution and relationship to this build remain open. [RSX native record](../research/deskmate-rsx-oem-recovery-20261122.md#other-rsx-applications) · [Udut's list](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm_progs.txt) |
| Pocket Watch · `pocket.zip` | DeskMate 410–411 | `POCKET.PDM` names Bob Jack Software and version 3.1. `POCKET.DOC` describes DeskMate 3 and standalone modes. The nested `POCKET.EXE` identifies runtime 03.03.01. |
| Recipe Sharing · `rcpshare.zip` | DeskMate 440–441 | TVDog specifies Home Organizer. The ZIP's `RCPSHARE.PDM` differs by SHA-256 from the member shared by RSX Disk 3 and the RLX HD-B bundle. Udut's Recipe Importer mention is an adjacent lead with equivalence open. [Udut's list](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm_progs.txt) |
| Fil2dbf · `f2d01.zip`, `f2ddos.zip` | DeskMate 300–304 | `FIL2DBF.TXT` identifies Jeffrey L. Hayes, version 0.1, and export from DeskMate 3 databases to dBASE III/IV. The second ZIP contains the standalone runtime. |
| DBrepair · `dmrepair.exe` | DeskMate 251–254 | The indexed self-extracting archive contains a `DBREPAIR.PDM` byte match to the copy inside Fil2dbf. Its documentation specifies DeskMate 3.0 or later. |
| Filer ASCII conversion utility · `filer.zip` | DeskMate 312–314 | `FILER.BAS` and `FILER.DOC` describe two-way conversion between early Filer and delimited text. TVDog excludes DeskMate 3. Exact earlier versions remain open. |
| Hmw2txt · `hmw2txt.zip` | DeskMate 330–331 | The readme identifies 0.1. The package includes C source and a DOS command-line converter for Sierra HomeWord `.HMW` files. HomeWord edition coverage remains open. |
| Prn2file · `prn2fil2.zip` | DeskMate 416–419 | The readme identifies version 2 and Jeffrey L. Hayes. The package includes the DOS filter and C source for cleaning up print-to-file output. |
| BackupDM · `backupdm.zip` | DeskMate 39–40 | `BACKUPDM.BAT` and its menu helper identify a DOS batch backup workflow for DeskMate data using floppy drives. Backup Pro has a separate catalog identity. |
| Dmgif · `dmgif09.zip`, `dmgif12a.zip`–`dmgif12c.zip` | Graphics 10–27 | The 0.9 ZIP contains `DMGIF.PDM`. The 1.2 installer set and docs identify Jeffrey L. Hayes and both DOS and DeskMate 3.0x installation paths. The 1.2 manual specifies a PC-compatible with 512 KiB RAM. [1.2 installation instructions](http://ftp.oldskool.org/pub/tvdog/tandy1000/graphics/dmgif12.txt) |
| Dmsound · `dmsnd07.zip`, `dmsnddos.zip` | Sound 28–34 | `DMSOUND.DOC` identifies Jeffrey L. Hayes and version 0.7. It specifies DeskMate 3.00+ or DOS 2.11+ with the additional runtime. Hardware support varies by driver. The overview specifies a 286 minimum for its speaker, parallel-port DAC, and Tandy/PCjr three-voice drivers. [Dmsound overview](http://ftp.oldskool.org/pub/tvdog/tandy1000/sound/dmsound.txt) |
| Mavis Beacon Teaches Typing for DeskMate · `installed_version.zip` | Mavis Beacon readme | `MAVIS.PDM` names The Software Toolworks and version 1.31T. `MAVIS.EXE` displays runtime 03.03.01. TVDog describes copy-protected distribution disks and TransCopy hardware for recreating them. The installed copy supplies the measured application metadata. [Media readme](http://ftp.oldskool.org/pub/tvdog/tandy1000/wares/Mavis-Beacon-for-DeskMate/readme.txt) |
| Convert · `conver.zip` | Sound 15–17 | `CONVERT.DOC` describes rewriting a Mac sound header for DeskMate Sound. The ZIP includes `CONVERT.EXE`. |
| Conv2snd · `c2snd202.zip` | Sound 7–10 | `CONV2SND.DOC` identifies version 2.02 and credits Kenneth Udut and Jeffrey L. Hayes. The ZIP includes Pascal source, the DOS converter, and `SND2WAV.EXE`. |
| Prtsnd · `prtsnd.zip` | DeskMate 420–424 | `PRTSND.COM` and its assembly source support the identification of a waveform-printing utility. TVDog specifies uncompressed Tandy SND and IBM- or Epson-compatible dot-matrix printing. |

Original indexes for the line references above. [DeskMate](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/00_index.txt) · [Graphics](http://ftp.oldskool.org/pub/tvdog/tandy1000/graphics/00_index.txt) · [Sound](http://ftp.oldskool.org/pub/tvdog/tandy1000/sound/00_index.txt)

## Existing entries and open questions

- The DeskMate index links Workgroup Companion, Macro Companion, Outliner,
  Personal Financial Assistant, and Thesaurus to `deskwork.zip`,
  `macros.zip`, `outliner.zip`, `pfa.zip`, and `thes.zip` respectively.
  Member inventories substantiate the package matches. The 1988 buyer's
  guide supplies the Workgroup product identity, while the archived notes
  specify DeskMate 3.02+, MS-DOS 3.2+, and serial or network configurations.
  [Period buyer's guide evidence](demonstrator-purchase-facts.md) · [Workgroup notes](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/deskwork.txt)
- The index identifies a Pocket Watch runtime pairing with Q&A Write demo
  `gwd1.exe`. The archive database has the demo file but no decoded members,
  so the pairing remains an index claim. Likewise, the Print Magic readme's
  3.00–3.02 limit remains a distribution note pending a controlled compatibility
  check. [DeskMate index, lines 323–325 and 410–411](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/00_index.txt) · [Print Magic readme](http://ftp.oldskool.org/pub/tvdog/tandy1000/wares/DeskMate-Print-Magic/readme.txt)
- TVDog points to Tandy's May 1988 announcement and a separate four-page
  brochure. They describe developer and product relationships. Udut's product
  list and the project’s acquisition notes provide further search terms for
  cases such as ESPER, where a matching package has yet to be established in
  this review. [Tandy announcement](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/deskmor.txt) · [Brochure archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/3rdparty.zip) · [Udut's list](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm_progs.txt)
