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

Every media entry in this table is privately preserved and hash-verified.
Hardware requirements and compatibility are attributed to the index or
package documentation. Letter Invaders has a separate native observation.

| Product or utility | Publisher or credited author | Product version | DeskMate relationship | Verified private media | Source evidence |
| --- | --- | --- | --- | --- | --- |
| DeskHelp demo | Atmospheres | 1.00.00 demo | Early DeskMate add-on | `deskhe.zip` | DeskMate 118–120. `DH-DEMO.EXE` credits Bobby Ballard and names Atmospheres. TVDog specifies DeskMate 1 and II and excludes Personal DeskMate and 3. |
| Disk Info | Bob Jack Software | 3.01 | Native utility | `diskin.zip` | DeskMate 136–138. `DISKINFO.PDM` identifies publisher and version. TVDog excludes RAM disks. |
| Kaleidocubes | Unknown | Unknown | Native game | `kubes.zip` | DeskMate 343. `KUBES.PDM` matches RSX Disk 6 and RLX HD-B by SHA-256. The ZIP has `.KUB` files and help. |
| Letter Invaders | Kriya Systems | 1.0 | Native typing game | `li.zip` | DeskMate 344. `LI.PDM` matches RSX Disk 1 and RLX HD-B. The prior RSX About dialog names Kriya Systems and 1.0. [RSX native record](../research/deskmate-rsx-oem-recovery-20261122.md#other-rsx-applications) |
| Pocket Watch | Bob Jack Software | 3.1 | Native and standalone runtime | `pocket.zip` | DeskMate 410–411. `POCKET.PDM` identifies version 3.1. `POCKET.DOC` describes both modes. `POCKET.EXE` identifies runtime 03.03.01. |
| Recipe Sharing | Unknown | Unknown | Home Organizer companion | `rcpshare.zip` | DeskMate 440–441. TVDog specifies Home Organizer. The member differs from the common RSX Disk 3 and RLX HD-B `RCPSHARE.PDM`. |
| Fil2dbf | Jeffrey L. Hayes | 0.1 | Native converter and standalone runtime | `f2d01.zip`, `f2ddos.zip` | DeskMate 300–304. `FIL2DBF.TXT` documents DeskMate 3 database export to dBASE III/IV. The second ZIP has the DOS runtime. |
| DBrepair | Tandy (package documentation) | Unknown | DeskMate database repair utility | `dmrepair.exe` | DeskMate 251–254. Its `DBREPAIR.PDM` matches Fil2dbf's copy. The package notes specify DeskMate 3.0 or later. |
| Filer ASCII conversion utility | Unknown | Unknown | External BASIC converter | `filer.zip` | DeskMate 312–314. `FILER.BAS` and `FILER.DOC` document two-way conversion. TVDog excludes DeskMate 3. |
| Hmw2txt | Unknown | 0.1 | External HomeWord converter | `hmw2txt.zip` | DeskMate 330–331. The readme identifies 0.1. C source and the command-line `.HMW` converter are present. |
| Prn2file | Jeffrey L. Hayes | 2 | External DeskMate report filter | `prn2fil2.zip` | DeskMate 416–419. Readme identifies version and author. DOS filter and C source are present. |
| BackupDM | Unknown | Unknown | DOS batch companion | `backupdm.zip` | DeskMate 39–40. `BACKUPDM.BAT` and a menu helper provide floppy backup for DeskMate data. |
| Dmgif | Jeffrey L. Hayes | 0.9, 1.2 | Native viewer and standalone runtime | `dmgif09.zip`, `dmgif12a.zip`–`dmgif12c.zip` | Graphics 10–27. The sets contain `DMGIF.PDM`. The 1.2 docs describe both modes and specify a PC-compatible with 512 KiB RAM. [1.2 instructions](http://ftp.oldskool.org/pub/tvdog/tandy1000/graphics/dmgif12.txt) |
| Dmsound | Jeffrey L. Hayes | 0.7 | Native player and standalone runtime | `dmsnd07.zip`, `dmsnddos.zip` | Sound 28–34. `DMSOUND.DOC` specifies DeskMate 3.00+ or DOS 2.11+ with the additional runtime. The overview specifies a 286 for some drivers. [Overview](http://ftp.oldskool.org/pub/tvdog/tandy1000/sound/dmsound.txt) |
| Mavis Beacon Teaches Typing | The Software Toolworks | 1.31T | DeskMate application with launcher | `installed_version.zip` | Mavis Beacon readme. `MAVIS.PDM` identifies 1.31T and the publisher. `MAVIS.EXE` identifies runtime 03.03.01. TVDog describes copy protection and TransCopy hardware for separate distribution images. [Media readme](http://ftp.oldskool.org/pub/tvdog/tandy1000/wares/Mavis-Beacon-for-DeskMate/readme.txt) |
| Convert | Unknown | Unknown | External Mac sound converter | `conver.zip` | Sound 15–17. `CONVERT.DOC` describes rewriting a Mac sound header for DeskMate Sound. `CONVERT.EXE` is present. |
| Conv2snd | Kenneth Udut and Jeffrey L. Hayes | 2.02 | External audio converter | `c2snd202.zip` | Sound 7–10. `CONV2SND.DOC` gives both credits and version. Pascal source, the DOS converter, and `SND2WAV.EXE` are present. |
| Prtsnd | Unknown | Unknown | External waveform printer | `prtsnd.zip` | DeskMate 420–424. `PRTSND.COM` and assembly source are present. TVDog specifies uncompressed Tandy SND and compatible dot-matrix printing. |

Original indexes for the line references above. [DeskMate](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/00_index.txt) · [Graphics](http://ftp.oldskool.org/pub/tvdog/tandy1000/graphics/00_index.txt) · [Sound](http://ftp.oldskool.org/pub/tvdog/tandy1000/sound/00_index.txt)

## Five companion media confirmations

All five archives match their transfer hashes. The member inventories
establish that the corresponding packages are already in the private
archive. Release identities, retail SKU equivalence where applicable,
and native behavior remain open.

| Existing companion | TVDog DeskMate index | What the archive establishes |
| --- | --- | --- |
| Workgroup Companion | `deskwork.zip`, lines 129–131 | `WGSETUP.PDM`, `WRKGROUP.EXE`, `3PLUS.PDM`, and networking modules substantiate the package identity. The archived notes specify DeskMate 3.02+, MS-DOS 3.2+, and serial or network configurations. The 1988 guide documents SKU 25-1251. [Buyer’s guide evidence](demonstrator-purchase-facts.md) · [Workgroup notes](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/deskwork.txt) |
| Macro Companion | `macros.zip`, lines 347–348 | The set has `DMMACRO.ACC`, `DMMACRO.RES`, `DMMACRO.HLP`, and installer components. Macro storage and recording behavior remain untested. |
| Outliner | `outliner.zip`, `outlndoc.zip`, lines 380–384 | The installer ZIP contains `OUTLIN88.SML`, `OUTLIN89.SML`, and `OUTLINER.SML`. The separate ZIP contains a notes PDF. The runtime roles of those SML variants remain open. |
| Personal Financial Assistant | `pfa.zip`, lines 402–404 | The installer ZIP contains `PFA.SML`, `PFADAT.SML`, and `PFAHLP.SML`. The link to the printed SKU 25-1366 remains open. |
| Thesaurus Companion | `thes.zip`, `thesman.zip`, lines 491–494 | The program ZIP has `DICT.SYN`, `DMTHES.RES`, and `THES.RES`. The second ZIP contains the manual PDF. Integration with DeskMate Text awaits testing. |

## Open verification questions

- Udut associates Letter Invaders with Typing Tutor IV and mentions a
  Recipe Importer for Home Organizer. The Typing Tutor IV distribution and
  the connection between Recipe Importer and Recipe Sharing remain open.
  [Udut’s list](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dm_progs.txt)
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

The [acquisition gaps](acquisition-gaps.md) record the bounded publication
review of additional commercial packages already in the preserved shelf.

## Validation record

The original Windows portable run executed 749 tests with one failure
and two skips. The failure was
`test_owner_termination_leaves_permanent_fence_and_read_only_restart`
in `test_supervisor_driver.py`. Its isolated Python subprocess exited
before the test observed a durable acknowledgement. Repeating the test
with the shared Python installation reproduced the failure. The
subprocess uses `python -I` and therefore imported the shared installed
package even when the parent had the checkout on `PYTHONPATH`.

The same test passed in an isolated virtual environment configured to
put the staged source on its site path. An explicit `python -I` import
confirmed the staged-source path before the rerun. The isolated result
applies to this one test. The original full-suite result retains the
failure and skips. No supervisor code or tests changed.
