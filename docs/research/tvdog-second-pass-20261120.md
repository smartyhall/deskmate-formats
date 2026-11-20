# TVDog Faxback and optical media, second pass

## Faxback catalog

The read-only transfer snapshot started at 04:27:34 Eastern on November
20, 2026. It held 9,570 verified files, one partial and 402 pending across
the mirror. The Faxback subtree held 8,249 verified files, one partial and
four pending. Its most recent verified receipt was recorded at
04:27:33.674964 Eastern.

The private SQLite catalog rehashed and indexed 8,247 numbered objects
with 8,247 unique SHA-256 identities. There are 5,774 TXT bodies in FTS
and 2,473 PDF records searchable through the archive's title index or
their filenames. The PDF bodies were outside the specialized Faxback
pass. The general archive index handles extractable PDF text separately.
The archive's title index has SHA-256
`73534bb87771d605f29abdafc15786cdb54765acda77940018fa2c38b6085666`.

There are 5,735 matching document numbers from body headers, 2,507
archive-index title records and five number conflicts. Conflicting pairs
of filename and body identifiers are 2620/2621, 3138/9996, 5082/5072,
5533/5531 and 5780/5777. The index retains both values. It found 18,924
catalog number references, 593 document references and 44 texts with
candidate date lines. The catalog edges distinguish title and body
evidence and keep unrelated product mentions visible as separate hits.
Dates are candidates for review. File numbers and source checksums are
the join keys for relating this index to the existing library.

| Reference | Confirmed scope |
| --- | --- |
| [Faxback 4347](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/04347.txt) | DeskMate color driver for the DMP-240, catalog 260-2839 |
| [Faxback 5390](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/05390.txt) | FaxMate usage from DeskMate, catalog 250-3063 |
| [Faxback 1209](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01209.txt) and [1229](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01229.txt) | Separate Music references for 1000 TL and TL/2 |
| [Faxback 2611](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/02611.txt) and [2636](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/02636.txt) | WinMate and its options on Sensation! 250-1650 |
| [Faxback 2862](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/02862.txt), [2875](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/02875.txt) and [2876](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/02876.txt) | Screen options, door replacement and program icon creation on 250-1651 |

## Optical media

Four large ZIP originals independently matched their transfer receipts.
Each has a single cooked 2048-byte-sector ISO 9660 image. The table
counts directory and file records together. Volume creation stamps and
authoring applications describe the available image editions. Three
Sensation images contain Nero fields dated 2005. The Radio Shack disc
image has a 2004 Roxio creation stamp and a January 1995 title.

| Archive | ISO volume label | Bytes | Listed records |
| --- | --- | ---: | ---: |
| Sensation-CDs/Bookshelf.zip | BOOKSHELF92 | 641,003,520 | 1,381 |
| Sensation-CDs/DataDisc.zip | DATADISC1 | 508,876,800 | 4,652 |
| Sensation-CDs/SystemDisc.zip | TANDYDEMO3 | 397,795,328 | 2,995 |
| Retail-Services-CD.zip | RSPSC_JANUARY_95 | 577,579,008 | 13,473 |

The DataDisc has an original WinMate tree with its desktop, calendar,
multimedia and application binaries. The SystemDisc has the MMTANDY
demo program tree, DataFax and DOS disk content. On the Retail Services
CD, extracted readmes in `MODS/ZBAVIS1` and `MODS/ZBAVIS2` identify
Discis compatibility software for the Tandy Sensation and other supported
multimedia PCs, and Multicom compatibility software for the Sensation.
The first distribution includes VDISCIS and VINSTALL. The second
includes SETUP and references specific Multicom titles. These are
affirmative VIS-related finds with internal disc provenance. The available
evidence establishes PC compatibility packages. The presence of native
VIS titles or a Modular Windows runtime remains unconfirmed.

## Tools and repeatability

- `faxback_index.py MIRROR PRIVATE.sqlite` takes a short read-only
  transfer snapshot and updates a private metadata/FTS index. Its JSON
  summary keeps acquisition and ingestion coverage separate.
- `optical_inventory.py MIRROR PRIVATE_OUTPUT --seven-zip EXE --select
  '*/Sensation-CDs/*.zip' --select '*/Retail-Services-CD.zip'` hashes
  the verified ZIPs and streams out bounded image candidates to a private
  temporary directory. Supply repeated `--member-select` globs to hash
  and inspect up to 40 selected file records per disc. The result preserves
  the outer URL and hash, image member path and hash, descriptor and
  nested member labels. Read-only extraction never uses media paths as
  host output names.
- `archive_intelligence.py requeue` accepts kind and path filters.
  Requeue existing nested candidates by source path when a new structural
  recognizer lands. Existing bulk extraction limits still
  apply to large ZIP-wrapped discs, which have a dedicated path above.

The independent ISO and UDF controls were written with PyCdlib 1.22.0
and extracted with 7-Zip 26.05. In each case the recovered member matched
the original 16 bytes. The 7-Zip adapter uses explicit `-tIso` or
`-tUdf` list and stdout extraction, with bounded duration and output.
7-Zip is an external executable with its own licensing. The repository
does not redistribute it or any image and member bytes from this pass.

- [Sensation CD archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/wares/Sensation-CDs/)
- [Retail Services CD accession](http://ftp.oldskool.org/pub/tvdog/tandy1000/wares/Retail-Services-CD.zip)
- [ECMA-119 CD-ROM volume structure](https://ecma-international.org/publications-and-standards/standards/ecma-119/)
- [ECMA-167 volume recognition and file structure](https://ecma-international.org/publications-and-standards/standards/ecma-167/)
- [7-Zip capabilities and license](https://www.7-zip.org/)
