# TVDog archive research references

The [reference catalog](tvdog-reference.json) records 28 annotated references and 12 prioritized questions. Each record has a stable ID and original source URL. When an archive was acquired, the record includes its byte size and SHA-256 plus selected exact member paths and identities. Member paths run from the outer archive inward. A locator names a section, message or byte offset. The [ecosystem catalog](catalog.json) tracks product and installation status independently of the reference records. See the [mirror verification](tvdog-mirror-verification.md) for the boundary between snapshot results and selective follow-up acquisitions.

## Express Publisher and FF1

All four ZIPs from the [Express Publisher archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/wares/Express-Publisher-for-DeskMate/) passed CRC verification. Three are disk file sets with 12, 6 and 5 files totaling 699,763, 544,806 and 705,171 uncompressed bytes. Preserved ZIP timestamps cluster on December 6, 1991. The separate manual ZIP contains a 7,585,927-byte PDF. The timestamps describe the media files and scanned manual, with product release date still open.

The 14 EPB members are standard LHA archives using the historical `-lh1-` codec. 7-Zip 26.05 and Windows tar recognized the containers, and the tested Windows builds did not extract that method. The pinned [Lhasa 0.6.0 Windows release](https://github.com/fragglet/lhasa/releases/tag/v0.6.0) ZIP, SHA-256 `5925e6a7b615d784e381e18240a1537d55a42cddad91d21e13c604a40974fe28`, extracted the vetted flat member lists into separate private directories using `lha xf <archive>`. Lengths and independently computed CRC-16 values matched the 7-Zip listings for all 261 occurrences, totaling 4,496,075 bytes and 250 distinct SHA-256 identities. On Windows, file extraction was necessary because this Lhasa build translated line feeds when printing binary data to stdout.

Disk 1 contains the application PDM, resources, font install support and four `EPT` templates under `DOCS.EPB`. Each measured template starts with `00 04 4A 4F 52 47 45 00`. Disk 2 has the extra outline fonts, help and matching collections of 49 TIFF names at two advertised resolutions. Disk 3 contains a standalone runtime, resource and printer packages, and a separate `DMFONT.RES` upgrade. The installer references shared DeskMate and standalone installation modes. Both copies of the 39,949-byte Express Publisher `DMFONT.RES` are byte-identical, and the project already has a distinct build pinned in the [typography laboratory](../research/typography-lab-20261119.md). The bundled `EPDM.EXE` names DeskMate Runtime 03.05.00 and carries the literal marker `DESKMATE$05.00 901001$`. The application PDM and companion help identify the product version as 1.00 and 1.0 respectively.

| FF1 family | Bytes | Directory IDs | Glyphs | Candidate pair entries | Comparison |
| --- | ---: | --- | ---: | ---: | --- |
| Cobb | 61,503 | See pinned directory | 224 | 0 | Matches stock SHA-256 |
| Dixon | 42,049 | See pinned directory | 224 | 89 | Matches stock SHA-256 |
| Marin | 55,782 | See pinned directory | 224 | 147 | Matches stock SHA-256 |
| Dingbat2 | 105,653 | 185–194 | 224 | 0 | Additional family from `XTRAFONT.EPB` |
| Springer | 68,611 | 144–149, 53, 105, 167, 196 | 224 | 3 | Additional family from `XTRAFONT.EPB` |

The additional families each have ten descriptors and an outer marker `BD 7A 01 01 01` paired with an inner marker `1E F3 00 01`. The stock families instead pair `BD 7A 00 01 01` with `1E F3 01 01`. The updated independent parser validates both marker pairs and reproduces the exact bytes from all five decoded resources. It retains opaque auxiliary data, whose lengths are multiples of six in all five samples. Observed nominal advance ranges are 97–3,913 for Dingbat2 and 106–920 for Springer at 1,000 units per em. Springer's trailing 22-byte block starts at offset 68,589 and has the same ten-byte header and four-byte entry geometry as the Dixon and Marin pair candidates. Runtime application of these pair records and new font compatibility depend on native testing. The two extra outlines do not identify themselves as Rockwell. [Pinned outline evidence](../research/draw-fonts-20261119.md)

The [1000 RLX HD-B bundle](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/1000RLX_HD-B.zip) contains three more FF1 hashes and a distinct 39,965-byte DMFONT.RES. Its Dixon and Marin files reproduce all 224 outlines, advances and per-glyph auxiliary byte sequences from the pinned resources. Its Dixon pair block has 5 entries versus 89, with one shared key and zero shared adjustments. Marin has 18 entries versus 147 and 11 shared keys with zero shared adjustments. Marin AV is −132 in the RLX candidate table and −244 in the pinned one. This gives a native test with identical outlines and controlled pair differences. The RLX Cobb member is 25,087 bytes and declares that the glyph data ends at 61,402. It differs from the stock file at 5,143 positions within the recovered extent, so the strict reader rejects it and the archive is insufficient to reconstruct the missing byte range.

The Express Publisher manual identifies compatible faces as Atech FastFonts and lists Cobb, Dixon, Marin and Dingbat2 among available families on printed pp. 181–182 (PDF pp. 197–198). Its font installation section is on PDF p. 155. These page locators come from the searchable text layer. [Manual archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/wares/Express-Publisher-for-DeskMate/EPMan.zip)

Delphi's September 1992 archive ties the historical Atech identification to two specific additional packages, MicroLogic MoreType and Atech AllType, at message 21444. Together with the FastFonts list, these are leads for original FF1s, including possible Rockwell evidence. Message 21446 describes Tandy's ClipArt Editor beta. The [recovered beta](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dmclip.zip) independently corroborates the Draw Object-to-CLP workflow and supplies a native test target. [Delphi 1992 archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/delfor92.zip)

## Software and native format coverage

Here, acquired means the inspected release archive passed file/member checks. Identity evidence may establish a title, product version or embedded runtime marker. Installation and format status describe the evidence currently available to this campaign.

| Product or release | Acquired | Identity evidence | Installation evidence | Native format evidence |
| --- | --- | --- | --- | --- |
| Express Publisher 1.00 | Three disk file sets and manual | App and help agree on 1.00, launcher banner 03.05.00 | Standalone install and launch on disposable RSX | Native EPD save, four EPT templates, five FF1 identities, 47 PRS members |
| First Publisher 2.01 | Three FAT12 disks from earlier campaign | FP.EXE runtime 03.02.00 | Previously launched on disposable RSX | PUB samples and independently read FNT maps |
| Q&A Write 1.00 | QWD.ZIP | Symantec, documented version 1.00 and launcher banner 03.03.01 | Install PDM inspected statically | Six printer FNTs plus DMTOQWD.PDM |
| Print Magic 1.1 | PM.ZIP and compatibility readme | Epyx, 1988, application version 1.1 | Install PDM inspected statically | PMP page, PMG graphic and PMF font corpus |
| Instant Pages 1.0 | INSTANT.ZIP | IP.PDM gives 1.0, Robert P. Plummer copyright in launcher | Install scripts inspected | 125 IPD members |
| Backup Pro 1.0 | BP-720K.ZIP | Application 1.0, 1989 Software Toolworks timer | Install executables inspected statically | Backup data layout open |
| Solitaire and Poker | SOL.ZIP | Two PDM/EXE pairs with launcher banner 03.05.00 | Launch paths in help | Game data layout open |
| StudyWare for Chemistry, Economics and the ACT | Three installer sets | Cliffs StudyWare 4.5 revision B in all three | Installers inspected statically, DeskMate runtime unresolved | Opaque RED assets |
| Tandy ClipArt Editor beta | DMCLIP.ZIP | Tandy attribution and beta wording in CLIPART.DOC | Workflow documented | Draw object conversion to CLP, color CLP examples |
| UnDesk | UNDESK.ZIP | COM converter and usage documentation | DOS utility unrun here | DOC-to-text conversion documented |
| DM_Music 1.04 | DM_MUSIC.ZIP | PE file/product version 1.04 | GUI and VB6 dependency statically identified | HDS text output documented |
| DeskMate SDK 3.03 | Two manual ZIPs, Development Disk 1, Samples and two toolkits | Both PDFs and selected DMDB headers match project pins | Tools inventoried statically | DMDB interfaces and SND research candidates |

The table reflects the original media review. The
[descriptive index review](tvdog-directory-index-review.md) extends the
[ecosystem catalog](catalog.json) using TVDog's directory descriptions,
nested member inventories, and executable metadata.
The [current acquisition gaps](acquisition-gaps.md) incorporate the later
review of the completed private mirror.

### Two historical document controls

- `VIDEOMEM.DOC` is a 2,102-byte formatted Text file from the archive's documentation shelf. It has six margin controls at absolute offsets 26, 84, 460, 476, 552 and 568. All follow the documented five-byte envelope. The recovered projection is 2,016 characters over 34 lines. The reader preserves raw records and offsets for export while the browser preview reports that unmeasured layouts are omitted. [Original ZIP](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/videomem.zip) · [Tandy DOC format crosswalk](../reference/tandy-text-format.md)
- `PRNTRINF.PMP` and `RS232INF.PMP` are 24,061 and 24,139 bytes and share the `PMPAGE` plus NUL page marker. The two third-party documents and separate Print Magic binaries give a concrete starting point for independent native save controls and printer selection tests. [Original ZIP](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/cblmgc.zip)

## Music and development

The selectively retrieved DM_Music ZIP independently matches the earlier archived copy byte for byte. Its new archive-index identity includes the exact original URL and CRC-checked two-member inventory. The PE file and product version both read 1.04. The archived readme describes instrument changes and six dynamics labels, output tempo changes with a default `Pace=100`, and edits needed by the companion player to interpret certain historical repeats. It lists PDM2/1000HX slot 5 as Cello and a later profile's slot 5 as Baritone and slot 6 as Banjo, with slot 6 and later reassignable. These are historical claims to verify against original hardware and observed scores. The package has no source, examples or companion player. The native differential with raw HDS remains open. [Original ZIP](http://ftp.oldskool.org/pub/tvdog/tandy1000/sound/dm_music.zip) · [Earlier private corpus report](../research/audio-historical-corpus-20261118.md) · [Author's Usenet discussion](https://groups.google.com/g/comp.sys.tandy/c/fq1OO44yLtI)

Both SDK manuals retrieved from the 3.03 shelf match local PDF hashes. `DMDB.H` and `DMDB.INC` from Development Disk 1 match the prior allocator study's pins. The 50-member Tandy Sound Toolkit includes DeskMate audio examples and a joystick interface. Those original assets remain private, with exact archive and selected member identities in the reference catalog. [3.03 shelf](http://ftp.oldskool.org/pub/tvdog/tandy1000/wares/DeskMate-Development-System-3.03/) · [Allocator evidence](../research/dmdb-page-allocator.md)

Frank Durda IV's independent **PSSJ Digital Sound Toolkit 0.9** dates to October 18, 1994 and has 157 files. Its disk-format documentation and assembly declarations identify the linked SND header's word at byte 92 as a hardware skew value. Both bundled recordings independently pass the current SND parser. Each has that word set to 4, a nominal rate of 11,000 Hz, one descriptor at 114, and uncompressed payload at 2,048. Their sample counts are 48,700 and 39,323. The document associates playback-rate correction with recordings made on early 1000 SL and TL hardware. These two files corroborate the field's location, with the relationship between value 4 and physical rate still open. The toolkit documentation also describes DeskMate 88-compatible compression, providing a separate reference for the existing decoder and future native comparisons. [PSSJ toolkit archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/wares/DeskMate-Development-System-3.03/PSSJ-Toolkit.zip)

## Community collections

| Collection | Measured coverage | Starting locations |
| --- | --- | --- |
| America Online DeskMate | 1 export, 383,833 bytes | Look for Express Publisher, Q&A Write trial, Worksheet, clipboard and SDK threads |
| CompuServe Tandy Professional | 238 members | ACDB.TXT and ACDA.TXT mention the DeskMate SDK. AC8E.TXT has printer discussion |
| CompuServe Tandy Newsletter | 182 members | 336802FD.TXT describes Worksheet functions and names three upgrade paths |
| Delphi Tandy | 7 years, 84 monthly members | September 1992 messages 21444 and 21446 cover outlines and CLP. July 1992 message 21177 describes the SDK. October 1994 message 23212 mentions runtime media |
| Tandy Users Are People Too | 2 issues | Contemporary product and utility commentary |

The CompuServe newsletter's Worksheet list gives specific function names to check against the independent evaluator, and its interoperability paragraph identifies Q&A Write, Lotus Spreadsheet and filePro as migration targets. Confirm those routes in native products before describing preserved data types. Delphi's July 1992 report of a $250 SDK price is an attributed community observation, suitable as a lead for a printed price list. [Newsletter archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/cistanne.zip) · [Delphi archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/delfor92.zip)

## Using the catalog

Use record IDs for cross-links and cite the original source URL and ordered member chain. The [schema](tvdog-reference.schema.json) describes public records and the lead register. The full archive index and extracted historical files remain private. For offline querying, use the [archive tools](../../tools/archive/README.md).

The [second-pass TVDog report](../research/tvdog-second-pass-20261120.md)
cross-references Faxback technical documents, Sensation/WinMate media
and the VIS compatibility packages independently identified on the
Radio Shack Retail Services CD. See the machine-readable
[extraction capabilities](tvdog-extraction-capabilities.json) for
measured optical media coverage.
