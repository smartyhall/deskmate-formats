# Archival format capability inventory and first qualification packages

Campaign: `freebuff/archival-format-coverage-research-campaign`.
Base commit: `3d3f784`. Branch: `freebuff/archival-format-coverage-research-campaign`.
Observed 2026-11-26. Provider-neutral usage receipt:
`docs/evidence/agent-usage/freebuff-archival-format-coverage-20261126.json`.

This report records what the archive tooling could already do at the start of
the campaign, what was newly implemented and qualified, what the existing
private holdings actually contain, and what remains blocked. It is a dated
evidence record, not a standing specification.

## Method

Three sources were used in this order:

1. the implementation itself (`tools/archive/intelligence_extract.py`,
   `archive_intelligence.py`, `verify_mirror.py`, `optical_inventory.py`), read
   rather than assumed;
2. public primary specifications for each container under study, retrieved
   before any parser was written;
3. bounded, read-only analysis of the private TVDog mirror.

The accompanying machine-readable registry is
[`docs/archive-capabilities.json`](../archive-capabilities.json), with generated
prose in [`docs/archive-capabilities.md`](../archive-capabilities.md). The
registry is deliberately separate from the
[format backlog](../archive-format-backlog.json): a backlog entry is a
candidate, a registry record is a claim that a test can check.

The backlog's own warning — that it is "not a support matrix" — was taken
literally. Several packages listed as `needs-audit` turned out to be fully or
partly implemented, and one (`DCF`) turned out to be unimplementable from
public sources at all.

## Capability audit at campaign start

The implementation already covered more than the backlog implied, but with an
important qualification: most "archive" support is a bounded adapter around
7-Zip rather than an independent implementation.

Native, independently implemented: ZIP (stored and deflated), TAR, GZIP, ARC
methods 1 and 2, FAT12 and FAT16 with directory traversal, plus structural
recognition of ISO 9660, UDF, 2352-byte raw sector candidates, MZ executables
and the project's own DeskMate formats.

Adapter-mediated: ARJ, CAB, RAR, 7z, ISO and UDF listing and extraction through
7-Zip, LHA level-0 extraction through `lhasa`, ARC methods 8 and 9 through
`nomarch`, PDF text through `pdftotext` or `pypdf`.

Absent: every compression family in the priority-one package, every PC sector
container, FAT32, VFAT and XDF, and all Tandy, Commodore, Apple and Amiga
families.

Two audit findings are worth recording because they change how the remaining
work should be scheduled:

- **Identification was already structural in places but not consistently.**
  The extension table and the header sniffer overlapped, so a correctly named
  file and a misnamed file could reach different extractors. The registry now
  separates `identify` from `extract` so this cannot be reported as one number.
- **No capability registry existed.** `docs/ecosystem/tvdog-extraction-capabilities.json`
  covers only four optical/executable observations from an earlier campaign, so
  there was no single place to record what is qualified and what is not.

## New packages

### Standalone compression streams

`tools/archive/compression.py` decodes three families, each into one bounded
payload:

- **Unix `compress(1)` LZW (`.Z`)** — a native decoder following the published
  algorithm: least-significant-bit-first variable-width codes starting at nine
  bits, a dictionary reset on code 256 in block mode, and the "KwKwK" immediate
  code case. Output is bounded in bytes and in decoded codes, so a hostile
  stream cannot expand without limit.
- **bzip2 (`.bz2`)** and **xz (`.xz`)** — driven through the CPython standard
  library decompressors, but fed incrementally with a `max_length` room limit so
  the bound applies before expansion rather than after it.

The `.Z` decoder is the only part of this package that is a genuine independent
implementation, so it received the strongest verification. A separate encoder
in the test suite (authored from the algorithm description, not from the
decoder) produces streams that the decoder reproduces exactly at maximum code
widths 9, 10, 12 and 16. Those same streams were then extracted by **7-Zip
26.05**, which reproduced all three test payloads byte-for-byte:

| Payload | Encoder output | 7-Zip 26.05 extraction |
| --- | --- | --- |
| 1,120 B repetitive text | valid `.Z` | byte-identical |
| 1,536 B all byte values | valid `.Z` | byte-identical |
| 9,000 B single-value run | valid `.Z` | byte-identical |

That cross-check matters because it caught a real error: a first attempt widened
the code width before writing the triggering code, which round-tripped against
its own decoder but disagreed with the format. The 7-Zip agreement is what
establishes that the width-bump ordering is now correct.

An early regression risk was also closed: the compression sniffer reads only
magic bytes, and a `.z`-named text file is still classified as text. Extensions
alone never promote a file into a decoder.

### PC sector-image containers

`tools/archive/disk_images.py` decodes three containers into explicit
`Sector` records and an optional normalised logical-block derivative.

Research before implementation corrected two assumptions that would otherwise
have produced wrong parsers:

- **IMD is not a text format.** There is no `cyl: head sectormap mode sectorsize`
  track line. Each track is a five-byte binary header (mode, cylinder, head,
  sector count, sector size code), followed by a sector numbering map, optional
  per-sector cylinder and head maps, an optional `0xFF` per-sector size table,
  and then one status byte per sector. Even status bytes mean a single fill byte
  repeated to the sector size; odd bytes mean raw data; zero means no data.
  The parser implements exactly that, including the deleted-data-address-mark
  and read-error statuses rather than collapsing them into "ok".
- **TeleDisk has no per-sector "method 4".** The sector data header is a
  separate 16-bit block size and a separate encoding byte, with methods 0
  (raw), 1 (repeated 16-bit pattern) and 2 (RLE). "Advanced" TD0 is a different
  thing: the entire post-header stream is LZSS/Huffman compressed.

CopyQM was implemented from the LibDsk appendix and cross-checked against the
fdimg reader: a 133-byte header whose bytes must sum to zero, an embedded BIOS
parameter block, and per-track run-length encoding with *signed* 16-bit lengths.
The zero-sum header check is used as the structural identification invariant,
which is much stronger than a three-byte magic.

Normalisation never hides damage. `to_lba()` returns the derivative together
with `missing` and `conflicts` tuples, and the extractor demotes a clean
filesystem read of an incomplete volume to `partial`, because the container —
not the filesystem — decides completeness. This is the concrete implementation
of the rule that missing data must never be silently zero-filled and presented
as verified.

Two integration paths are proven end to end rather than asserted: a FAT12
volume embedded in an IMD file and the same volume embedded in a CopyQM file
both reach the existing FAT reader through the normaliser and yield the
contained member.

## Blocked: Disk Copy Fast (`.DCF`)

No published byte-level specification for Disk Copy Fast was found, and its
distributed documentation is marketing text only. Contemporary secondary
sources agree only that a `.DCF` holds a raw floppy image behind some header.
Its signature, header length and geometry fields are therefore unknown.

Implementing it from file size, extension, or the assumption that it is "just
raw plus a header" would be guessing. The record is registered as `blocked`
with the precise reason. Two things would unblock it: a real specimen, and
controlled comparison of several images from the same tool version to identify
the geometry fields. A naming trap is recorded in the registry: Aaru's "CisCopy
`.DCF`" is a different program and must not be used as a substitute.

## TeleDisk advanced compression

The `td` variant is recognised from the header and its metadata (version, data
rate, drive type, side count, comment) is reported. Its payload is not decoded,
and the record says so. The distinction is deliberate: header metadata is
evidence about the disk, not recovery of the disk's contents.

## Application to existing holdings

A bounded read-only pass over the private TVDog mirror read at most 4 KiB of
each file and classified 10,037 inputs by content. No file was modified, and
the live downloader and index writer were not touched.

| Classified kind | Files |
| --- | --- |
| DOS text | 6,485 |
| PDF | 2,480 |
| ZIP | 986 |
| HTML | 62 |
| MZ executable | 16 |
| ARC | 2 |
| 7z | 2 |
| ARJ | 2 |
| OLE compound document | 1 |
| Unclassified binary | 1 |

Three results matter for scheduling:

1. **The new handlers add zero coverage to this corpus.** No `.Z`, bzip2, xz,
   IMD, TD0 or CopyQM file exists in the mirror. Sector-image and compression
   work is therefore justified by future media preservation, not by this
   corpus, and must not be prioritised on corpus-demand grounds.
2. **Structural identification changes the numbers.** 986 files are ZIP by
   content against 895 carrying a `.zip` extension. Of the 106 `.exe` files,
   exactly 90 are identified as ZIP containers and 16 as plain MZ executables,
   so the executables are predominantly self-extracting or installer payloads
   that an extension-based inventory would have binned as opaque binaries. One
   further ZIP is carried under an unrelated name.
3. **Both ARJ archives are named `.apm`.** An extension-based inventory would
   have missed them entirely. They are identified structurally and list two
   members each — but only when the optional 7-Zip adapter is present; without
   it the same inputs report `unsupported` with `7zip-unavailable`.

The ARC result is the clearest actionable gap. Both ARC archives contain five
members between them, and four use **method 8**:

| Archive | Member | Method | Packed | Unpacked | Native result |
| --- | --- | --- | --- | --- | --- |
| `t1kbootf.arc` | `BOOTFIX.DOC` | 8 | 3,306 | 6,195 | unsupported |
| `t1kbootf.arc` | `BOOTFIX.SYS` | 8 | 411 | 726 | unsupported |
| `t1kbootf.arc` | `INT19.COM` | 2 | 2 | 2 | ok, CRC verified |
| `tandykey.arc` | `TANDY.ASM` | 8 | 2,925 | 5,366 | unsupported |
| `tandykey.arc` | `TANDY.COM` | 8 | 118 | 128 | unsupported |

So 80% of the corpus's ARC content is currently unreachable without `nomarch`.
7-Zip 26.05 was tested as a possible substitute oracle and returns exit status 2
for ARC extraction: it has no ARC handler. A native method-8 decoder is
therefore the highest-value next package, and it will need a constructed test
vector corpus rather than an external oracle.

## Architectural notes

The layering the standing workstream asks for is now partially explicit in
code rather than only in prose:

- acquisition and provenance stay in `archive_mirror.py` and are untouched;
- identification is a pure function of a bounded header sample;
- compression decoding produces one opaque payload and knows nothing about
  containers;
- sector containers produce sectors and geometry and know nothing about
  filesystems;
- filesystem interpretation is the existing FAT reader, unchanged;
- the normaliser is the only component allowed to convert between geometry and
  logical blocks, and it is the only component that reports gaps.

The new modules have no dependency on DeskMate, 86Box or any agent runtime, so
they remain extractable under the [roadmap](../preservation-roadmap.md).

One deliberate non-change: no attempt was made to support FAT32 or VFAT in the
existing reader during this campaign. Both require changes to the layout
detection and directory enumeration that would have mixed an unqualified
feature into a package that is otherwise fully tested.

## Candidate deterministic procedures

These are proposed interfaces for later review by the Supervisor campaign. No
integration was attempted and no other campaign's worktree was touched.

| Procedure | Proposed interface | Exit states |
| --- | --- | --- |
| `archive.identify` | `--input PATH` → JSON `{kind, structural_evidence}` | 0 identified, 3 unclassified |
| `archive.inspect` | `--input PATH` → JSON members/geometry without payloads | 0 ok, 4 unsupported format |
| `archive.extract` | `--input PATH --output DIR --limit-bytes N` | 0 complete, 5 partial |
| `archive.verify` | `--input PATH` → JSON per-member integrity outcomes | 0 all verified, 6 mismatch |
| `archive.capabilities` | `--registry PATH --check` | 0 current, 1 stale |

All five are already deterministic and offline. `archive.capabilities` exists
today as `tools/archive/capabilities.py --check`. Each proposed task should
carry its registry record id as provenance so a Supervisor run can cite exactly
which qualification it relied on.

## Remaining questions

- Which ARC methods appear in the wider historical corpus? Method 8 is dominant
  in these two archives, but two files are not a distribution.
- Does the documented TeleDisk header CRC use the stated polynomial with
  MSB-first or LSB-first bit ordering? The current code implements MSB-first
  with preset 0 and reports a mismatch as a warning rather than a failure,
  because no specimen was available to confirm it.
- For TeleDisk RLE, one independent source reads the block length as
  `1 << flag` while the primary notes give `flag * 2`. The two disagree at
  flag ≥ 3. The implementation follows the primary notes; both are recorded so
  a future specimen can settle it.
- CopyQM's documented disk-data CRC excludes the top two bits of every byte
  before accumulation. That claim is recorded but unverified here.

## Limitations of this campaign

- Every new sector-image parser was qualified against hand-authored fixtures
  built from published structure, not against a genuine image produced by
  ImageDisk, TeleDisk or CopyQM. Coverage of real-world quirks is therefore
  unproven, and the registry says so in each record.
- The 7-Zip cross-check applies to `.Z` only. bzip2 and xz rest on CPython's
  implementations, which are independent of this project but not independent of
  each other in the sense of a second written parser.
- The corpus pass classified 10,037 files by header only. It did not extract
  members, and it did not validate any of the PDFs, ZIPs or text files against
  their contents.
- No Tandy, Commodore, Apple, Amiga, cassette or flux family was started. They
  remain `planned`, which the registry renders as an explicit gap rather than a
  coverage statistic.

## Resumable record: next packages

In the order this campaign would take them, with the reason attached:

1. **ARC method 8 and 9 native decoder** — 4 of 5 corpus ARC members depend on
   it and no external oracle exists. Needs a constructed CRC-bearing vector set.
2. **FAT32 and VFAT long file names** — the largest remaining gap in a family
   already partly qualified; requires 32-bit FAT chains, a cluster-based root
   directory, and LFN checksum validation.
3. **TeleDisk advanced (LZSS/Huffman) decompression** — recognised but opaque;
   would convert a whole class of TD0 images from metadata-only to recoverable.
4. **ZOO, SQZ, HA, UC2 and DWC readers** — nothing implemented and nothing
   identifiable; each needs its header layout transcribed from a primary source
   before any claim.
5. **IBM XDF geometry** — belongs on a geometry layer that does not yet exist;
   the current normaliser assumes fixed sectors per track.
6. **Tandy JV1/JV3/DMK/VDK/JVC** — the natural next consumer of the sector
   abstraction added here, and the first step toward the Tandy file systems.

`DCF` is deliberately last and remains blocked on a specimen rather than on
effort.
---

# Successor checkpoint: genuine-specimen qualification

This section supersedes two claims made above. The first campaign could not
qualify any sector-image parser against a genuine image, and it recorded the
TeleDisk header CRC and RLE block length as unconfirmed. Genuine specimens were
then obtained, and they both settled the CRC question and exposed a defect in
the identification rule that hand-authored fixtures had not caught.

## Specimens

Six genuine images were acquired and kept privately outside this repository;
their bytes are not committed, and only derived structural facts appear here.

| Image | Family | Source position |
| --- | --- | --- |
| `copwrcpm.td0` | TeleDisk, advanced (`td`) | third-party mirror, not redistributable |
| `cpm86sys.td0` | TeleDisk, ordinary (`TD`) | third-party mirror, not redistributable |
| `dos211-1.td0` | TeleDisk, ordinary (`TD`) | third-party mirror, not redistributable |
| `DIAG_2.04.IMD` | ImageDisk | Osborne archival mirror |
| `DRIVE_C.IMD` | ImageDisk | Osborne archival mirror |
| `OCC1_HARDDISK.IMD` | ImageDisk | Osborne archival mirror |

Acquisition respected the standing rule that acquired historical binaries are
never executed on the host: every file was read as bytes only.

## TeleDisk header CRC: resolved

The header CRC is CRC-16 with polynomial `0xA097`, preset `0`, applied
most-significant bit first over the first ten header bytes, and stored
little-endian at offset 10. All three genuine images agree:

| Image | Stored | Computed |
| --- | --- | --- |
| `copwrcpm.td0` | `0x0A52` | `0x0A52` |
| `cpm86sys.td0` | `0x609C` | `0x609C` |
| `dos211-1.td0` | `0x17FB` | `0x17FB` |

Three distinct stored values matching one computation closes the bit-order and
preset alternatives the previous checkpoint left open. The reader therefore no
longer reports a mismatch as an unconfirmed observation: a mismatch is now
reported as `header-crc-mismatch`, which is a statement about the file rather
than about our uncertainty. The three 12-byte headers are embedded in the
portable tests as structural vectors, so the convention is regression-tested
without shipping any specimen.

## TeleDisk RLE and repeat-pattern conventions: resolved

The previous checkpoint also listed the RLE block length as unconfirmed. The
genuine specimens settle it, because both compressed sector methods are used by
real data rather than only by fixtures: 359 sectors use the RLE method and 426
use the repeated-pattern method across the two ordinary images.

Two independent facts support the convention. First, every one of those 785
sectors decodes to exactly its declared sector size, and the decoder rejects
both undershoot and overshoot, so a wrong block length would have to overshoot
or fall short. Second, the very first RLE block of the DOS 2.11 image is
`00 1b` followed by 27 literal bytes beginning `E9 83 00 5A 44 53`, which is
the boot record at the offset the disk layout predicts. A zero flag therefore
introduces a literal block whose length is the following byte, and a non-zero
flag introduces a block of `flag * 2` bytes repeated the number of times given
by the next byte. The repeat-pattern method is confirmed the same way: a block
of `00 01 f6 f6` fills an entire 512-byte sector with `0xF6`.

Exact length is necessary rather than sufficient, and disk data is highly
repetitive, so a coincidence is not formally excluded. What can be said is
that the reading of both methods is consistent with 785 genuine sectors and
with a known boot record recovered at its expected offset, which is far
stronger than the published notes alone.

## Identification defect found by the specimens

The previous rule required `data[3] == (data[0] + data[1] + data[2]) & 0xFF`,
reading byte 3 as a checksum of the signature. Every genuine image violated it,
carrying `0x42`, `0x43` and `0x2E` respectively, so all three files were
rejected as `unhandled`. Byte 3 is a volume-set identifier, not a checksum.

Identification now requires the `TD`/`td` signature and a plausible version
byte, and reports the header CRC separately as `header_crc_verified`. This
keeps a genuinely damaged image identifiable and its damage visible, instead of
conflating "not a TeleDisk file" with "a TeleDisk file with a bad header".

Consequence: the two ordinary images now parse (800 and 640 sector records, no
unknown sector status), and the advanced image is recognised and still refused
rather than silently mis-parsed.

## Content-level placement evidence

`dos211-1.td0` normalises to a complete 640-sector image whose first sector is
`E9 83 00` followed by `ZDS 2.0`, a DOS 2.11 boot record reached through
TeleDisk's per-track sector map. That corroborates sector placement from file
content rather than from internal consistency alone.

`cpm86sys.td0` is the interesting negative. It declares 40 cylinders, 2 heads
and 10 sectors per track, but holds 800 sector records across only 40
track-head pairings, i.e. 20 records per track. Half of them therefore cannot
occupy distinct logical sectors: the normaliser writes 400 and reports the
other 400 missing instead of inventing a head mapping. Its comment block is
preserved (`CP/M 86 Version 1.1 ... Modified for the Telecon Zorba`), and the
header carries `stepping = 0` even though a comment is present, which
disproves the assumption that a comment is announced only by bit 7 of the
stepping byte.

## ImageDisk against genuine media

All three genuine IMD files parse with zero unknown sector statuses, and both
the raw and fill paths are exercised by real data.

| Image | Geometry | Records | Result |
| --- | --- | --- | --- |
| `DIAG_2.04.IMD` | 40c / 2h / 10spt / 256 B | 440 | 40 conflicts, 400 unwritten |
| `DRIVE_C.IMD` | 40c / 2h / 10spt / 512 B | 400 | complete 400/400 |
| `OCC1_HARDDISK.IMD` | 40c / 2h / 10spt / 512 B | 400 | complete 400/400 |

`DIAG_2.04.IMD` repeats one sector ID on every head-1 track. The reader keeps
all 40 records and reports 40 conflicts plus 400 logical sectors it cannot
write, which is the accurate description of a diagnostic disk that stores
per-head content under a shared ID. Sector placement is confirmed by content:
a normalised image begins `C3 5C D2 C3 58 D2 7F 00`, a Z80 `JP`/`JP`/`LD A,0`
boot sequence followed by the text `COPYRIGH`.

## ARC method 8: a documented negative result

A native method-8 decoder was written and tested against the four CRC-bearing
method-8 members of the corpus (`BOOTFIX.DOC`, `BOOTFIX.SYS`, `TANDY.ASM`,
`TANDY.COM`). It decodes the LZW layer without error on the smallest member and
reproduces the exact unpacked length after the RLE90 pass, but no member
reproduces its CRC.

The variants actually tried, each against all four members:

- bit order within the code stream: least-significant first and
  most-significant first;
- dictionary insertion rule: `previous + first(entry)` and
  `entry + first(previous)`;
- RLE90 repeat count: `n`, `n - 1`, `n + 1`, `n + 2`, and both readings of the
  `0x90 0x00` escape;
- discarding the remainder of the current bit block at a CLEAR code, and not
  discarding it.

No combination matches a single member's CRC, and the larger members fail with
a code above the next free table slot while reporting zero CLEAR codes, so the
error precedes any table reset. Two candidate explanations remain untested: a
different first-code-after-reset convention, and an RLE90 pass applied to the
input rather than to the output of the LZW stage.

The registry consequently still claims no method-8 extraction. `nomarch`
remains the only qualified path for methods 8 and 9, and no independent oracle
is available locally: 7-Zip 26.05 has no ARC handler, and no C toolchain is
present to build `nomarch` from source as a second implementation.

## FAT32 and VFAT

The filesystem reader now accepts a cluster count at or above the FAT32
threshold, reads a 32-bit allocation table, follows the root directory as a
cluster chain, merges the high and low halves of a 32-bit first-cluster field,
and reconstructs VFAT long names from their UTF-16 code units.

Qualification uses a sparse volume large enough to cross the real FAT32
threshold rather than a small FAT16 layout relabelled as FAT32. A file placed
at cluster `0x10003` is read back byte for byte, so the high cluster word is
proven in use. A single-slot long name is reported in place of its 8.3 alias,
and a long-name chain whose checksum does not cover its short name is rejected
in favour of the short name, because an unverified fragment must not be
trusted.

## Identification axes in the registry

Every capability record now carries an `identification` block separating seven
things that were previously entangled:

- `extensions`: the filename hints, which are never evidence on their own;
- `structural`: what the bytes are;
- `carrier`: an executable wrapper, when present;
- `embedded`: an archive found inside that wrapper;
- `completeness`: the strongest completeness claim available
  (`verified-sizes`, `structural`, `unverified`, `not-applicable`);
- `methods`: the extraction methods actually implemented;
- `unsupported_variants`: named gaps rather than silence.

The validator enforces the vocabulary, and the generated document renders all
seven for every record plus a table of dual-identity formats. At run time
`intelligence_extract.classify()` returns the same axes: a self-extracting
executable reports structural kind `zip`, carrier `pe` and embedded `zip`
together, while a ZIP merely named `.exe` reports no carrier at all. That keeps
a genuine dual identity distinguishable from a misleading filename.

## Verification for this checkpoint

- `tests/portable/test_disk_images.py`: 28 tests pass, including the three
  genuine header vectors and a damaged-CRC case.
- `tests/portable/test_intelligence_extract.py`: 16 tests pass, including the
  FAT32 cluster-root volume, the VFAT checksum fallback and three
  carrier/embedded classification cases.
- `tests/portable/test_archive_capabilities.py`: passes, including new
  rejection tests for a missing identification block and unknown completeness,
  method or carrier values.
- `tests/portable/test_archive_compression.py`: 14 tests pass.
- `tools/archive/capabilities.py` reports the generated document as current.

The full portable suite was not run locally: its supervisor and observer
subprocess tests exceed the local time budget, so this checkpoint relies on the
focused suites above plus the independently executed CI matrix for the rest.
That distinction is deliberate and is not a claim that the whole suite passed.

## Revised resumable record

1. **ARC method 8 and 9 native decoder**: still open, now narrowed. The LZW
   stage decodes cleanly, so the remaining unknowns are the reset convention
   and the direction of the RLE90 pass. A CRC-bearing vector set built by an
   independent implementation remains the missing instrument.
2. **TeleDisk advanced (LZSS/Huffman) payload**: recognised and refused; one
   genuine advanced specimen is now held for future validation.
3. **ZOO, SQZ, HA, UC2 and DWC readers**: unchanged, still needing primary
   header layouts.
4. **IBM XDF geometry**: unchanged, still needing a geometry layer.
5. **Tandy JV1/JV3/DMK/VDK/JVC and the Tandy filesystems**: unchanged, and the
   natural next consumer of the sector abstraction.
6. **CopyQM against a genuine specimen**: the handler is still qualified only
   against hand-authored fixtures; no genuine `.QM` image has been obtained.
