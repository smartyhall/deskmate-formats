# DeskMate Help databases in the TVDog archive

The 109 files previously rejected at directory offset `0x0464` are
DeskMate Help resources stored in the common database engine. Every
byte-distinct candidate in this group is archived as an HLP file and
contains `DBCOLS`, `Rules` and `Text` descriptors at pages 2:3, 4:5 and 6:7
(data:index). The Filer and Address Book help viewers consumed exact
matching members of the cluster in DeskMate 3.05. Filer itself refused the
same Help resource when passed as a Filer document.

## Corpus differential

The [previous sweep](extended-resume-20261120.md) recorded 157 distinct
DMDB-format candidates across the private TVDog library, with 17 accepted
by existing preservation readers. On the same 364 occurrences, the archive
inventory now accepts 125 distinct candidates, including 108 Help databases.
It identifies a Help directory for all 109 and retains a structural
rejection for one. The existing Filer, Calendar and Address Book readers
retain their original validation.

| Bytes immediately after the directory marker, hex | Distinct |
| --- | ---: |
| `36 01 37 01 02 03` | 76 |
| `02 03 37 01 31 01 02 03` | 25 |
| `35 01 02 03 37 01 34 01 31 01 02 03` | 8 |

The first marker ends the descriptor list. The post-marker bytes are
retained as opaque evidence. Their resemblance to older descriptor
suffixes is a hypothesis. The reader recognizes the measured table roles,
column counts, directory position and exact tails. The bounded Help parser
validates the row and index data separately.

A first in-memory diagnostic that zeroed the directory tail accepted 70
specimens in the shared storage reader. The first remaining failures were
25 chained indexes, 13 row IDs outside the shared profile, and one data
page whose last indexed record fills its extent. Inspection of the original
bytes resolved the first two:

- Across the 109 files, 32 table indexes span two packed-12-linked pages.
  Each nonterminal index page contains four full 41-entry subdivisions.
  The number of occupied slots across both pages matches its table's
  declared record count. Index targets and IDs are unique across the
  whole chain of each accepted table.
- The index holds the little-endian row ID. Across 3,763 indexed IDs at
  or above 128, the target row starts with the big-endian word
  `0x8000 + id`. This covers 3,707 IDs in the range 128–255 and 56 in
  the range 256–302. The remainder of the row uses the existing field
  separators and terminator. The new rule applies to live rows in the
  Help profile. Retired-row framing and general allocation are unchanged.
- `DMSETUP.HLP` (SHA-256
  `9fb468108d09136a72c594a52ceb383310d1b95684bc1e7b751bc289ea01a053`)
  has a single indexed Text row (ID 16) starting at page 10 offset zero
  and ending exactly at its last byte. The first reported error at
  `0x2C00` names the following page boundary, where ID 17 starts. Page 11
  contains five structurally framed indexed rows, with no missing prefix.
  An isolated in-memory reader probe allowing the fully occupied page
  then reached a finite Text index route without declared sort ordinals.
  Its directory is recognized and both additional checks remain in force.

The read API is `database.inspect_help_directory(source)` for descriptors
and `database.parse_help_bytes(source)` for validated rows with exact
source retention. It returns opaque field bytes. Help rule execution and
the control or dictionary coding in the Text field remain open. No writer
or automatic Filer conversion is provided.

## Native attribution and controls

DeskMate 3.05 ran from a disposable clone of the previous
[Filer baseline](filer-native-20261117.md), on an RSX i386SX at 25 MHz
with 4 MiB RAM and network links down. Its starting disk SHA-256 was
`c013712c0cda7628a5a3138047a7d0e9b631098c5c72d41d5b8f717a6f90a281`.
The 86Box 7.0 build and RSX ROM origins are pinned in the
[RSX baseline](rsx-dos5-baseline.md). All input and captures used the
authenticated loopback socket. Times are the held emulated clock.

| Resource and matched source | SHA-256 | Native observation |
| --- | --- | --- |
| FILER.HLP, 22,528 bytes, DeskMate 3.05 disk 5 | `433f8a5724fffeff242605c36465825f4ad42dd7a1856c5fc6c5a03c81f0a5a5` | F1 in the Filer Open dialog showed context help at 23,171 ms. After renaming only this HLP on the clone, the same action gave a missing-data-file message at 32,127 ms. With the name restored, `DESK FILER FILER.HLP` displayed a Filer rejection at 106,506 ms. |
| ADDRESS.HLP, 36,864 bytes, DeskMate 3.05 disk 4 | `3fcca9a3fb219910c2df78447d9794709c8b3a3a910a576c56fdce71b3f23a9c` | F1 in Address Book showed help for the focused index at 51,154 ms. After renaming its HLP, F1 gave a missing-data-file message at 62,255 ms. |
| DESKMATE.HLP, 53,248 bytes, retained RSX install | `d1736cd15bfd70aab57b60bb2efa468dc421a73323469d0fab14a5164bb085c5` | The 12-byte-tail representative parses independently as 19 schema, 208 Rules and 191 Text rows. Removing it did not affect the tested desktop exit-dialog help. Its specific native binding remains unverified. |

Static inspection of the installed `DMHELP.ACC` (SHA-256
`0b32213a0cde0d0aae62eeedcbb6843c9b64a62c7090cdaeb09cd3143b8a5976`)
found a reference and missing-file diagnostic for `DESKMATE.HLP`. The
desktop exit-dialog control isolates that screen from the general resource
but does not rule out other call paths.

The native Help viewer exposed read-only navigation in the tested contexts.
The earlier native schema, insert, delete, compaction and sort trials in
Filer remain Filer evidence. They were not repeated as Help authoring or
Save As trials. An incidental edit to a bundled Text document on the clone
was discarded. Stopped-disk extraction verified exact original bytes for
all three renamed resources and that document. Socket quit was
acknowledged at 125,809 ms. The stopped clone SHA-256 is
`bbfa166ced0fbe3acbba3d62bc9a98e11a7755e8e6b70b8ec8832789601356cf`.

## Reproduction

Run the inventory from an installed checkout against a read-only open of
the private TVDog SQLite index, as documented in the
[archive workflow](../archive-format-coverage.md):

```powershell
python tools/archive/desk_native_inventory.py $db
```

The private `semantics-20261120` evidence directory retains the
`native-population-help.json` inventory and archive member paths,
`database-profile.json`, `help-coverage.json`, the byte-verified private
specimens, the socket journal, and the native screenshots. The portable
database tests independently assemble synthetic tables and exercise
cross-page indexes, IDs above 255, unknown tails and mismatched index targets.

The next format experiment is to trace the native read of one address
Help topic from its indexed Rules row to Text, then compare the compressed
bytes against the matching framebuffer. Use a setup guest with the exact
DMSETUP.HLP to verify fully occupied Text pages and the finite index-route keys.
