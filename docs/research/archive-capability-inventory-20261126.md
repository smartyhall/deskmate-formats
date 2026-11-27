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

`tools/archive/compression_streams.py` decodes three families, each into one bounded
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
