# Independent review corrections — archival format coverage

2026-11-27. Campaign: `freebuff/archival-format-coverage-research-campaign`
(PR #194) and its successor `freebuff/archive-qualification-2` (PR #195).

Two independent reviews were read at their exact heads and answered here:

- PR #194, review `pullrequestreview-6078744944`, at `cca20c2`;
- PR #195, review `pullrequestreview-6078745158`, at `4343b9b`.

A follow-up exact-head review of PR #194,
`pullrequestreview-6085087858`, confirmed the geometry, logical-image, CHS,
degraded-sector and xz `memlimit` corrections and named one remaining defect in
the concatenated-stream lifecycle. It is answered in the follow-up section
below.

Both reviews are integration holds, not experiment repeats: the earlier genuine
specimen work (TeleDisk, ImageDisk, ARC methods 8/9) is retained unchanged and
was not rerun.

## Disposition

| Finding | Resolution | Evidence |
| --- | --- | --- |
| `disk_images.to_lba()` allocated `total * sector_size` from container geometry without an aggregate bound | `Bounds` gained `total_bytes`, `geometry_sectors`, `lba_bytes`, `track_bytes` and `track_sectors`; `to_lba` validates geometry and refuses the allocation before it happens | `test_sector_image_bounds.LbaImageTests` |
| CopyQM track size and inner sector loops could exceed the sector cap before the next outer check | Track length, sectors per track and total geometry are checked before a track is expanded; the sector cap is applied to the whole track before the inner loop | `test_the_sector_cap_is_enforced_for_the_whole_track`, `test_a_copyqm_geometry_bomb_is_refused_before_expanding_a_track` |
| `read()` permitted a stat/read race and `struct.error` on a truncated header | The bound is enforced by a single bounded read; an explicit kind on a short file returns `truncated-header` | `test_the_input_bound_is_enforced_by_the_read_itself`, `test_an_explicit_kind_on_a_short_file_is_a_truncated_header` |
| Malformed geometry could alias invalid CHS onto legitimate blocks | Out-of-range cylinder/head/number is counted in `rejected` instead of being wrapped or dropped silently | `test_out_of_geometry_coordinates_are_counted_not_aliased` |
| A filled read-error sector could establish a verified image | Normalisation reports `degraded` separately from `missing` and `conflicts`; only an all-good image is `complete` | `test_a_read_error_sector_does_not_complete_a_verified_image` |
| `LZMADecompressor` needed a decoder-memory limit independent of output | `Bounds.decoder_bytes` feeds `memlimit`; bzip2 checks its declared block size; concatenated streams are counted | `test_decoder_memory_is_bounded_independently_of_output` |
| compress(1) width changes cleared without old-width group alignment | The decoder now mirrors `ncompress`'s eight-code group padding at every width change and CLEAR, re-basing the group origin after each jump | matrix below |
| Only output-direction comparison existed for `.Z` | gzip 1.15's independent `unlzw` decoder reproduced every generated payload from the 10–16 bit streams | `test_gzip_reproduces_every_generated_stream` |
| Partial/unknown integrity was not reported honestly | `partial` + `truncated-final-code`, `dictionary-saturated`, `block-clears-N`, `reserved-header-flags`, `trailing-data`, `concatenated-streams-N` | `test_a_stream_ending_inside_a_code_is_partial` and peers |
| VFAT fragments accepted without slot validation | Each slot is validated (reserved order bit, reserved byte, zero first cluster, repeated checksum, descending ordinals, unique 0x40, contiguous 1..N, UTF-16 pairing and FFFF padding, following short entry) | `VFatSlotTests` |
| Ownership tracked by filename, directory chains unclaimed | Ownership is per directory entry; directory chains and the FAT32 root are claimed before they are walked | `FatOwnershipTests` |
| FSInfo/backup placement and damage-vs-advice were conflated | FSInfo and the backup boot must sit inside the reserved region; observations are split into `damage:` (partial status) and `advisory:` | `test_fsinfo_signature_and_values_are_checked`, `test_backup_boot_sector_is_compared_with_the_primary` |
| `.COM` mapped to MZ, `.Z` to `compress`, extension discrepancies suppressed by an embedded archive | One identifier per format on every axis; `unexpected_extension` evaluates all identities and is never suppressed | `test_archive_classification.py` |
| ARC implementation provenance was undocumented | Provenance is recorded in `_arc_crunch` and in the registry: conventions learned from nomarch 1.4, implementation written independently, verified against genuine member CRCs | registry `arc` record |
| Version-2 migration predated the corrected contracts | Identity axes vocabulary, confidence semantics, evidence keys, transactional restart and idempotent re-run | `test_archive_index_migration.py` |

## compress(1): what changed and how it was checked

The decoder previously assumed that a width change simply continues at the new
width. compress(1) instead packs codes into groups of eight and pads the current
group at the old width before a width change or a CLEAR, and the decoder must
make the same jump from the *start of the current group*, not from the start of
the stream. The corrected state machine also:

- re-bases the group origin after every alignment;
- resumes after a CLEAR without resetting the previous code, matching
  `ncompress`'s decoder (the table stays one entry behind the encoder, and the
  KwKwK path covers the gap);
- freezes a full table instead of widening past `maxbits`;
- treats fewer than eight trailing zero bits as clean padding and anything else
  as `truncated-final-code`.

### Independent generation matrix

Streams were produced by a test encoder authored from the published
eight-code convention (`ncompress` 5.0 `output()` and `decompress()`), then
decoded by **gzip 1.15** (`unlzw`, an independent implementation) and by this
module. Codepoints 10–16 bits, block and non-block mode, four payload shapes
(pseudo-random 70 kB, repetitive text, full byte range, long runs), plus a
dictated CLEAR and a saturated table: gzip reproduced every payload byte for
byte, and this decoder reproduced the same bytes and termination.

The reverse direction is retained from the earlier checkpoint: 7-Zip 26.05
extracted streams produced by this project's encoder byte-identically.

### Recorded divergence

Nine-bit streams round-trip through this decoder but are **not** cross-validated:
gzip 1.15 reports corrupt input once a nine-bit table fills. The decoder follows
`ncompress`'s published state machine here (which freezes the table at
`maxbits`), so the difference is recorded as an open question rather than
smoothed over. It does not affect the 12–16 bit streams real compress(1) writes.

## bzip2 and xz boundaries

- Concatenated streams are joined and counted (`concatenated-streams-N`); the
  count is bounded separately from output so stacked streams cannot allocate
  decoders without limit.
- Trailing non-stream bytes are reported as `trailing-data` without discarding
  the payload; truncation and corruption fail with a named detail.
- xz decoding passes `memlimit` from `Bounds.decoder_bytes`, so a small stream
  declaring a 16 MiB dictionary is refused under a 64 KiB bound rather than
  allocated. bzip2's block size is declared in its header and checked the same
  way, per member. This is the point the review made: bounding output does not
  bound memory, and one member's header cannot speak for the next.

## Follow-up review: concatenated-stream decoder budgets

The follow-up review found that `decode_bzip2` validated the declared block size
of the **first** member only, while `_bounded_streams` constructed a fresh
decoder for every later member. A `BZh1` member followed by a `BZh9` member
therefore decoded under a budget only the first member satisfied. The same
lifecycle questions applied to the input bound in `_compressed`.

| Finding | Resolution | Guard |
| --- | --- | --- |
| Later bzip2 members bypassed `decoder_bytes` | `_bzip2_member` validates every member's header before that member's decoder is constructed; the budget is the caller's for every member | `test_a_later_member_cannot_raise_the_decoder_memory_budget` |
| Four block bytes understated the decoder | The comparison uses bzip2(1)'s documented decompression requirement per block size, which covers libbzip2's `tt` allocation and its fixed tables | `test_the_documented_bzip2_requirement_is_the_budget_unit` |
| A later xz member could raise the dictionary budget | Every member is a new `LZMADecompressor` with the same `memlimit` | `test_a_later_member_cannot_raise_the_xz_dictionary_budget` |
| A damaged later member discarded members that had already verified | `_stream_stop` returns the verified members as `partial` and names the member that stopped the join; damage in the first member still yields no payload | `test_a_damaged_later_member_keeps_the_members_that_verified`, `test_a_damaged_first_member_yields_no_payload` |
| `_compressed` bounded input by a separate `stat` | The bound is enforced by the read that feeds the decoder, one byte past the limit | `test_the_compression_input_bound_is_enforced_by_the_read_itself` |
| A partial payload was recorded as an `ok` member | The member carries the extraction's qualifier | `test_a_partial_stream_is_not_reported_as_a_complete_member` |

Every member is now classified before it is decoded: a member too short for its
header is `truncated-member-header`, a digit outside `1`–`9` is
`unsupported-block-size`, a member whose documented requirement exceeds the
budget is `limited`/`decoder-memory-limit`, and a decoder error is
`bzip2-integrity-or-structure` or `xz-integrity-or-structure`. Truncation inside
a member stays `truncated-stream`. Only one decoder is live at a time: the
previous member's is released before the next is constructed, so the working
set is the largest member's requirement rather than the sum.

### Documented bzip2 memory, per block size

| `-1` | `-2` | `-3` | `-4` | `-5` | `-6` | `-7` | `-8` | `-9` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 500 KiB | 900 KiB | 1300 KiB | 1700 KiB | 2100 KiB | 2500 KiB | 2900 KiB | 3300 KiB | 3700 KiB |

bzip2(1)'s MEMORY MANAGEMENT table gives these figures, and libbzip2's
`decompress.c` allocates `tt` as `blockSize100k * 100000 * sizeof(Int32)` as
soon as it reads the header, with fixed tables besides; the table's value — not
four block bytes — is the documented bound a caller's budget is compared
against. The standard library never selects the 2.5-bytes-per-block-byte `-s`
decoder, so the normal figures apply. These are vendor estimates, not
measurements taken here.

## Resource bounds, layer by layer

`disk_images.Bounds` now carries one limit per layer and every one is enforced
before allocation:

| Layer | Bound | Where enforced |
| --- | --- | --- |
| Input file | `input_bytes` | the read itself, one byte past the limit |
| One sector | `sector_bytes` | IMD/TD0/CopyQM sector and size tables |
| One track | `track_sectors`, `track_bytes` | track header, before expansion |
| All decoded sectors | `total_bytes` | every appended payload |
| Declared geometry | `geometry_sectors` | before any coordinate is used |
| Logical image | `lba_bytes` | before `bytearray(total * size)` |
| Decoder memory | `decoder_bytes` | xz `memlimit` per member, bzip2 documented requirement per member |

`intelligence_extract._sector_image` derives each of these from the caller's
`Limits`, so a container header cannot enlarge a caller's bound. The tests use
deliberately tiny limits (1 KiB, 4 sectors, 2 tracks) and never allocate the
memory the checks exist to prevent.

## FAT32 and VFAT

Long names are now assembled by a chain state machine rather than by collecting
fragments: a stale, duplicated, out-of-order, interleaved, wrongly-checksummed
or malformed slot cannot supply a name the short entry does not describe, and a
malformed chain always leaves the short name visible.

Ownership moved from file name to directory entry, which fixes two real defects:
two entries with the same name were treated as one object, and a file pointing
at a directory's clusters was not detected. Directory chains and the FAT32 root
chain are claimed before they are walked, so aliasing a directory, the root or
another entry is refused while the earlier owner keeps its bytes.

Observations are now classified: a divergent mirrored FAT, an invalid FSInfo
signature, and a backup boot sector that differs or sits outside the reserved
region are damage (the listing becomes `partial`); an implausible free-cluster
hint is advice only.

FAT12 chains are exercised directly for the first time: a two-cluster extent, a
bad-cluster marker and a self-referencing chain, read through the fixed root
region.

## Identification axes

- `dos-com` is its own identifier: a headerless COM program is never labelled
  `mz`, and an MZ file named `.COM` is reported as a genuine discrepancy.
- `.Z` implies `unix-compress`, the identifier the decoder and the registry use.
- `identities` is an ordered set of the structural kind, the executable carrier
  and any embedded payload; `unexpected_extension` compares the suffix against
  all of them. A PE carrier accepts `.exe` because PE is an MZ carrier; nothing
  is suppressed merely because a second identity exists.
- `evidence` records which axis decided the kind and `confidence` derives from
  it, so a name-only classification is `probable` and can never be mistaken for
  a structural finding.

## ARC provenance

The ARC method-8 conventions (eight-code group padding, 256 as a width reset
rather than a table clear) were learned by reading nomarch 1.4, which is
GPL-2.0-or-later. The implementation in `intelligence_extract._arc_crunch` is
written independently from that format knowledge; no nomarch expression was
copied, and the authority for the result is the stored CRC-16 of four genuine
members (`BOOTFIX.DOC A963`, `BOOTFIX.SYS F1C8`, `TANDY.ASM 6ADD`,
`TANDY.COM 79BB`), not nomarch's output. nomarch remains an optional backend for
methods 5 and 6 and is never the oracle for 8 and 9. This is recorded in the
registry `arc` record as well as in the function.

## Migration readiness

Schema version 2 is reconciled with the corrected contracts: the identity axes
are `structural`, `extension`, `carrier` and `embedded`; confidences are
`certain`, `probable` and `unknown`; evidence keys cover completeness,
integrity, unpacked size, unsupported methods, recovery and classification. The
backfill no longer claims certainty version 1 never stored — it writes
`unknown` with `backfilled-from-schema-v1-kind-only`, and a classified pass
refines the row in place.

Rehearsal now covers interruption (explicit transaction, rollback to version 1),
restart (a completed migration is a no-op), malformed identity rows, two
different structural kinds for one analysis (`duplicate_kinds`), and selective
reprocessing by axis.

**Not adopted.** `archive_intelligence.open_index` still rejects version 2, the
live database was not opened for writing, and no downloader or index-writer
change is proposed here.

## Remaining limitations

- ARC methods 3, 4, 5, 6 and 7 remain unsupported; method 9 still has no genuine
  specimen.
- TeleDisk advanced (LZSS/Huffman) is recognised but not decoded.
- No CopyQM, TeleDisk, ImageDisk, DMK, JV3 or XDF specimens were found in the
  accessible mirror, so those cases stay unresolved.
- No volume formatted by an independent FAT implementation (dosfstools, mtools,
  Windows) has been qualified; the FAT tests qualify the reader against the
  on-disk specification. This is the largest outstanding evidence gap.
- Nine-bit compress(1) streams are decoded but not cross-validated against an
  independent decoder.
- bzip2's working-memory figures come from its published table; peak allocation
  was not measured on this machine, and a caller's budget is compared against
  the documented requirement rather than an observed high-water mark.
- DCF remains blocked on a byte-level specification; no unrelated format was
  substituted.

## Observed test costs

Recorded for the separate performance campaign, measured on this workstation
while it was running its normal background load: the 27 FAT-volume tests take
8–9 s (sparse 32 MB fixtures, no long scans); the 26 compression tests 7–8 s,
of which roughly 60 % is the gzip cross-check spawning one process per matrix
case; the 14 sector-bound tests 1.6–1.9 s; the 28 disk-image tests 5–10 s, with
the spread tracking unrelated load rather than the change. The nine
archive-focused suites together take roughly 35–40 s, so they stay cheap enough
to run at every checkpoint rather than deferring them to CI.
