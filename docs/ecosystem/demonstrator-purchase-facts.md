# Period purchase evidence for the Enthusiast's Edition

The [purchase facts](demonstrator-purchase-facts.json) record 31 advertised
U.S. prices and options from 19 documents in the November 19 TVDog snapshot.
They also record nine observations about compatibility, software bundles and
product availability, and ten acquisition leads. The files describe what
Tandy and other period sources told readers. They establish historically
plausible choices for the [demonstrator](demonstrator.md), with no fictional
buyers or transactions assigned.

## From DeskMate II to the RSX

| Period offer | Catalog number | Price | Evidence and context |
| --- | --- | ---: | --- |
| Tandy 1000 EX | `25-1050` | $799.00 | Announcement bundles Personal DeskMate, MS-DOS 2.11 and GW-BASIC. [Tandy release](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/1kexrel.txt) |
| Tandy 1000 SX | `25-1051` | $1,199.00 | Announcement bundles DeskMate II and MS-DOS 3.2. The CM-5 monitor was listed separately at $299.95. [Tandy release](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/1ksxrel.txt) |
| Tandy 1000 SL and 1000 TL | `25-1401` and `25-1601` | $899.00 and $1,299.00 | Both July 27, 1988 releases promise September availability with DeskMate and MS-DOS 3.3 in ROM. [SL release](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/1kslrel.txt), [TL release](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/1ktlrel.txt) |
| Tandy 1000 RL and RL HD | `25-1450` and `25-1451` | $599.95 and $999.95 | The HD model included the 20 MB SmartDrive and clock. The introductory mouse giveaway required buying an RL and monitor together. [RL article](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/rlpr2.txt) |
| Tandy 1000 RLX HD with color monitor | `25-1453` computer | $1,599.90 and $999.90 | The introductory article lists $1,599.90 in its comparison chart. The February 1992 newsletter reports $999.90 from the end of January for the 40 MB model with a VGA monitor. The later offer leaves the monitor model unspecified. `3367EB04.TXT`, `336806C4.TXT`. [CompuServe newsletter archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/cistanne.zip) |
| Tandy 1000 RSX HD with VGM-220 | `25-1454` and `25-4044` | $1,299.90 | The vendor article and August 1992 newsletter agree on the price. The computer alone cost $999.95 and included a 52 MB SmartDrive. `3367EABE.TXT`, `336805AD.TXT`. [CompuServe newsletter archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/cistanne.zip) |
| DMP 136 color dot-matrix printer | `26-2868` | $299.95 | The period article directs DeskMate users to the IBM Proprinter driver for monochrome printing, despite the printer's color capabilities. `3367FD02.TXT`. [CompuServe newsletter archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/cistanne.zip) |
| Getting the Most Out of DeskMate 3, second edition | `25-1254` | $21.95 | The Radio Shack release gives a suggested retail price and describes coverage of DeskMate 3.02, 3.03 and 3.5. [Book announcement](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/dmbook.txt) |
| Home Lawyer for DeskMate | | $69.95 | The vendor article advertises the DeskMate edition at this price and gives separate comparisons for the DOS edition. `336802A2.TXT`. [CompuServe newsletter archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/cistanne.zip) |

The RSX sources distinguish the `25-1455` floppy model from the `25-1454`
hard-drive model. They advertise 1 MB standard RAM, a 9 MB ceiling and
separate RAM and video-memory options. The `A` suffix matters for the
`25-1082A` RSX video kit. An order for an RL system RAM upgrade uses the
unsuffixed `25-1082`. The RSX HD's included DOS 5.0, DeskMate Home Organizer,
Print Companion and America Online should be recorded as bundled software
when modeling this purchase. `3367EABE.TXT`, `336805AD.TXT` and `rlpr2.txt`.
[RSX articles](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/cistanne.zip),
[RL article](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/rlpr2.txt)

The October 2, 1992 Factory Direct announcement describes a separate sales
channel. The October newsletter gives a $1,699 example for a custom OMNI
Profile 486SX/25 with 4 MB RAM, 120 MB disk and Super VGA display. The launch
announcement specifies shipping and handling separately and a $99 optional
service plan. These terms support an example custom order without extending
them to the RSX or its store bundle. `3367EA7A.TXT`, `3368055C.TXT`.
[CompuServe newsletter archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/cistanne.zip)

## Offers, dates and locators

- `price_usd_cents` is the period advertised amount in integer cents. `basis`
  records a launch price, suggested retail price, advertised price, option,
  bundle or conditional promotion. `requires` captures the purchase condition
  for the free mouse. A `catalog_number` on a bundle identifies its main
  product. Included items are described in `includes` where documented.
- `document_date` and `available_from` retain only the precision supported by
  the text. The 1997 CompuServe display timestamps are export metadata. For
  example, the RLX article states April 18 as introduction day but omits the
  year. The dated February 1992 newsletter supplies a separate firm reference
  point. The launch articles for the EX and SX also omit a date in these copies.
- `evidence` points to inclusive, one-based text lines via `source_id`.
  Standalone text sources identify the original URL, bytes and SHA-256.
  Container sources also identify the exact member name, zero-based ZIP
  ordinal, member bytes and SHA-256. Line numbers use decoded text and
  normalized line endings as in the local archive index.
- `observations` keep documented details and unresolved claims outside the
  price rows. The approximate Q&A Write price remembered in a Delphi thread
  is explicitly uncertain. `DEC91TAN.TXT`, lines 1534–1545.
  [Delphi Tandy forum archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/delfor91.zip)

The source and member hashes were independently checked against the acquired
bytes, and each price, catalog number and acquisition filename was checked at
its recorded line locator. The [mirror verification](tvdog-mirror-verification.md)
describes the original transfer snapshot.

## Catalog gaps relevant to later purchases

The captured directory description lists the 1987 and 1989–92 Radio Shack
annual catalog computer pages, the 1985 and 1987 Tandy computer catalogs, the
1988 Tandy Computer Catalog & Software Reference Guide, the Express Order
Software Buyer's Guide, and the 1992 Factory Direct price list. All ten
sources were in the pending queue at the dated snapshot. The research table
includes their exact URLs and listing locators for acquisition follow-up.
[TVDog directory description](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/00_index.txt)

One immediate catalog question is which additional scalable fonts Radio
Shack actually sold, under what numbers, and at what price. The RLX article
describes three supplied scalable Draw fonts and additional ones available
through Express Order. It identifies the feature with DeskMate 3.5 but leaves
the names and order numbers unspecified. `3367EB44.TXT`, lines 175–194.
[CompuServe newsletter archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/documents/cistanne.zip)
