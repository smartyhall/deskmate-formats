# DeskMate 3.05 Filer native records

Native Filer writes the same indexed, page-based row framing already measured
in Calendar and Address Book. The two-record CARMAINT sequence also shows
when application-visible operations change the physical representation. A
terminal field growth keeps its locator. A nonterminal growth and two deletion
controls close with dense DATA and reassigned locators or IDs. A separate
five-insertion pressure test extends the packed page chain.
[Run evidence and byte differences](../evidence/filer-text-native-20261117.json)

## Baselines and menu availability

The private original disk and independent, hash-verified read-only copies of
both shipped files anchor the controls. F00 ran `DESK FILER`, selected
CARMAINT, observed the File, Edit and Records menus, then exited normally
with Escape. All 242 extracted files and the whole disk matched the input.
This replicates the earlier no-edit evidence using the campaign's own clone.

| Shipped sample | Bytes | SHA-256 | Counts in DBCOLS / LAYOUTS / GRAPHICS / DATA | Data : starting index pages in the same order |
| --- | ---: | --- | --- | --- |
| CARMAINT.FIL | 14,336 | `ca5ea9d77dc7545e761457ddc9d40c0b5aca427d7f787a19038d61495f4c67e7` | 28 / 22 / 4 / 0 | 2:3, 4:5, 6:7, 8:9 |
| INVNTORY.FIL | 12,288 | `62316203c555e42cddc47b118f4a34ef1c60362e684d2b90a978fb3675d9c6fe` | 26 / 20 / 3 / 3 | 2:3, 4:5, 6:7, 10:11 |

CARMAINT DATA columns in schema order are Date K/10, Cost K/10,
Car K/22, Serviced by: K/41, Comments K/229, Mileage K/10 and
Next Scheduled : N/10. The starting DATA marker is `03` at `0x2000`,
and the first index slot at `0x2428` is zero. INVNTORY DATA columns
are Label C/27, Field 1 C/27, Field 2 C/20, Comments C/581 and Field 3
C/12. Its indexed DATA starts at `0x2800`, `0x291E` and `0x29D2` with IDs
16–18. The fixed-offset schema index probe confirmed five stored fields in
INVNTORY's non-self DBCOLS rows. The common reader requires six there and
rejects it at `0x0898`. INVNTORY was inspected offline in this campaign.
[Earlier private baseline and schema study](cross-application-db.md)

At zero records, Add was enabled along with Open, Copy layouts, Page setup
and Form setup. Delete, Copy record, navigation, Find, Sort, Count and both
Print commands were disabled. After the first insertion and reopen, Print
record/report, Delete, Copy, Find, Sort and Count were enabled. Navigation
still required another record. With two records, Ctrl+N traversed from ALFA2
to ZULU7Q9. At the last row, Previous and First were enabled and Next and
Last were disabled. Records → Count displayed two selected out of two.

## Native CARMAINT mutation sequence

Every row represents a separate stopped-disk specimen. Its clone was made
from the exact parent disk. Only CARMAINT.FIL changed by content in each
mutation. Add used Ctrl+A. Existing fields were reached by Tab navigation.
Escape returned to DOS and persisted each edit. Delete used Ctrl+D and one
confirmed OK. Values not mentioned in the table were left blank.

| Trial / parent | Native operation and observed state | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| F00 / original | Empty open/menu/exit control | 14,336 | `ca5ea9d77dc7545e761457ddc9d40c0b5aca427d7f787a19038d61495f4c67e7` |
| F01 / F00 | Car ZULU7Q9, Serviced by SHOP7Q9, close; displayed on F02 reopen | 14,336 | `a53aea56bbf31d292995dcf6835988a07ba82922171acb55a341ced96001f109` |
| F02 / F01 | Add Car ALFA2, Serviced by BAY2, close; both displayed in index order on F03 reopen/navigation | 14,336 | `b84081c1d77acc272ea5a36bca92615219f293d03ee673fa628ec6629cf98db1` |
| F03 / F02 | Replace BAY2 with BAY3, same length | 14,336 | `77ad216b7e26abf90908b381132d472634016af50b8a0a99f84aac9a1be59b63` |
| F04 / F03 | Replace BAY3 with BAY3-LONG7, extending the last physical row | 14,336 | `5e0aa12b3fad0413984d416eabc8ab87e775531b707788d14427394aaca0f9eb` |
| F05 / F04 | Delete ALFA2, last physical row | 14,336 | `a53aea56bbf31d292995dcf6835988a07ba82922171acb55a341ced96001f109` |
| F06 / F04 | Delete ZULU7Q9, first physical row | 14,336 | `5444b2fcdb0eaf1cca78ac193019cdf3dfbc31ff17d9ca0f57b8975a77d90925` |
| F07 / F04 | Replace SHOP7Q9 with SHOP7Q9-PLUS, extending the first physical row | 14,336 | `ec8fec09987f57fac00aac93cc0f95d7578fbc1078ff7f8bf4fc6d7c650af78d` |
| Pressure / F04 | Add P01–P05 with five independently verified 197-byte Comments values | 15,360 | `bd9f18633fb1585477450e6d9a2bbcb67bc7fa21e736f070fa93f3490054c880` |
| Sort / F02 | Records → Sort; Clear; add Serviced by as sole key; confirm | 14,336 | `6c10a8cb5a0fcc715ace2ea51be087935426c1462187295565db1debdfa7e55b` |
| Find / F02 | Open Find Records and select Car; operator stayed None; cancel, then close | 14,336 | `b84081c1d77acc272ea5a36bca92615219f293d03ee673fa628ec6629cf98db1` |

These versions retain the shipped car artwork and form. The archived files
and diffs are private. The two application-authored QRECORD fixtures below
provide a public native regression without the shipped material.

### Storage behavior

- **Insert.** F01 changes 29 byte positions. DATA count rises to 1 and the
  next-ID-like token to 17. Index tuple `(8,0,16)` points to a 24-byte row
  at `0x2000`. The prefix is `80 10`, seven fields are separated by `01`,
  the row ends in `01 02`, and the list ends in `03`.
- **Index order.** F02 appends ID 17 at `0x2018`, leaving ID 16's bytes exact.
  The first two little-endian index tuples are `(8,24,17),(8,0,16)`.
  The native order and Sort dialog agree with directory ordinals `3,1`
  (Car, Date). This pair distinguishes Car ordering from insertion order.
  It leaves equal-Car/date comparison unresolved. Changing to Serviced by
  replaces the directory key with `4`. The three changed offsets are
  `0x48C`, `0x48E` and `0x48F`. The original index order also sorts
  BAY2 before SHOP7Q9, so the unchanged index does not distinguish ordering
  by the two keys. The shorter descriptor leaves stale `02 03` after the
  new directory marker. The strict shared parser rejects this native variant.
- **Edits.** F03 changes exactly `0x2025`. F04 adds six field bytes,
  changes 12 physical byte positions at `0x2026–0x2031`, and preserves
  both indexed IDs and locators. F07 grows the first physical record by five
  bytes and closes with ALFA2 at `0x2000`/16 and edited ZULU7Q9 at
  `0x2019`/17. DATA and its index change, while the count and next-ID-like
  token stay at 2 and 18. Both record IDs differ from the parent.
- **Delete.** F05 is byte-identical to F01. F06 moves ALFA2 from
  `0x2018`/17 to `0x2000`/16. Both closes leave a zero-filled data tail,
  no `44` retired row in DATA, and tokens `00001/000/00017` for
  count/opaque/next-ID-like. This contrasts with a retained Calendar row in
  E16 and with the two static retired LAYOUTS rows in INVNTORY. Data compaction
  and ID reassignment are demonstrated for these Filer operations and this
  size; their trigger before or during close remains unmeasured.
- **Pressure.** P01–P04 are 210-byte rows at `0x2031`, `0x2103`,
  `0x21D5`, `0x22A7`. The fifth starts at `0x3800` on appended page 14,
  ID 22. DATA's page chain is `8 → 14`; the original index remains on page 9
  and resolves all seven live rows. The two pre-existing rows retain their
  complete physical bytes and IDs. Header changes are at `0x2C–0x2D` and
  `0x36–0x37`. This is one distinct page allocation under observed pressure.
- **Metadata scope.** DBCOLS, LAYOUTS and GRAPHICS index/data pages in
  CARMAINT are byte-identical through the recorded row edits, deletions,
  order change and growth. The conditional Find operator could not be set by
  the observed keyboard sequence, so this experiment establishes dialog
  availability and cancellation only. Print and Copy were observed in menus.

## Independent native schema and reader

`DESK FORMSET` offered to create a file. Accepting and entering QRECORD
created `QRECORD.FIL`. Field → Add, two Down and five Right presses, then
Enter opened Data Field Definition for a six-column by three-row rectangle.
Naming it FTXT_A with the default text, no outline and top-label settings
created a width-22 K column. Escape to DOS persisted the empty file. On a
separate clone Filer opened that form, displayed the field, accepted F7Q9
via Ctrl+A, and persisted it at clean exit.

| Published specimen | Bytes | SHA-256 |
| --- | ---: | --- |
| [QRECORD empty](../../tests/fixtures/application-generated/filer/qrecord-empty.fil) | 8,192 | `c8da80395059f2b9d981bd7a1bae2a161a85670c781f479404c1a7a1ad4a37f6` |
| [QRECORD one](../../tests/fixtures/application-generated/filer/qrecord-one.fil) | 8,192 | `8d9ed82cf8526fb833f4df8689184905905d40cd8b8c3c5925cbf10336ff1476` |

The new form has DBCOLS, LAYOUTS and DATA, with no GRAPHICS table. Form Setup
created the FTXT_A layout and four default report sections. Filer changed
13 byte positions on insertion. The raw row at `0x1800` is
`80 10 46 37 51 39 01 02`, followed by `03`. The first index triple at
`0x1C28` is `(6,0,16)`. This confirms the same framing in a fresh native
schema, with other metadata pages preserved byte-for-byte on insertion.

```powershell
python -m deskmate_formats.filer tests/fixtures/application-generated/filer/qrecord-one.fil
```

The read-only `filer.parse_file` returns the common database snapshot.
The CLI lists table definitions, counts, DATA index entries and live/retired
fields in hex, with a printable ASCII view where applicable. The reader
accepts QRECORD, the CARMAINT row-edit family and the measured extra-page
profile. It inherits the common parser's explicit limits, including low IDs,
one index page per table, six-field DBCOLS rows and a zero directory tail.
The next discriminating Filer experiments are a pre-close observation of
nonterminal growth, a distinct-key sort that reverses order, and valid
conditional Find on a two-record clone.
