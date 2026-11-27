# Successor checkpoint 3 — FAT32 and VFAT structural hardening

Campaign `freebuff/archive-qualification-2`. This checkpoint strengthens the
filesystem reader that the previous checkpoint added, and records what it still
does not claim.

## What changed

Three defects and three omissions were found by reading the existing reader
against the FAT specification rather than by a new specimen:

| Change | Before | After |
| --- | --- | --- |
| Bad-cluster marker | `0x0FFFFFF7` is below the FAT32 end-of-chain value, so a chain ending in a bad cluster was reported as a complete file. | A bad-cluster link is a distinct error; the member is refused. |
| Cluster ownership | Nothing tracked which file owned a cluster, so two directory entries pointing at one chain both read successfully. | The first file keeps its bytes and the second is reported as `read-error`. |
| Declared length | A chain shorter than the declared size already failed, but the failure was indistinguishable from a read fault. | Unchanged behaviour, now covered by a test rather than by inspection. |
| Active allocation table | Copy zero was always used. | `BPB_ExtFlags` is honoured: with mirroring disabled the low nibble selects the copy. |
| Mirrored copies | Never compared. | A divergence is reported as `fat-copy-N-differs` when mirroring is enabled; stale mirrors on a non-mirrored volume are not a defect. |
| FSInfo | Not read. | Signatures at offsets 0, 484 and 508 are checked, and implausible free-count or next-free values are reported. The hints are never used. |
| Backup boot sector | Not read. | Compared with the primary boot sector; `backup-boot-differs` and `backup-boot-outside-volume` are reported. |
| FAT media byte | The BPB media descriptor was validated, the allocation table's own copy was not. | A mismatch is reported as `fat-media-byte-differs`. |

Everything below the observation level stays conservative: an observation never
changes a member's bytes and never causes data to be invented. The volume-level
notes are prepended to the extraction detail, so they travel with the result
instead of being discarded.

## Coverage

`tests/portable/test_fat_volume.py` writes FAT32 volumes from the documented
on-disk structures, not from another filesystem implementation, and exercises
ten cases: a three-slot non-ASCII long name, a declared size beyond the chain, a
bad-cluster link, a cyclic chain, cross-linked files, active-copy selection with
mirroring disabled, divergent mirrored copies, FSInfo signature and value
checks, backup boot comparison, and a volume shorter than its declared total.

The multi-slot and Unicode case is new. The earlier reader assembled long names
but no fixture had ever exercised more than one slot, and the slots are stored
in reverse order with the `0x40` flag on the highest ordinal, which is exactly
where a hand-written fixture can silently be wrong. The test writes the slots in
the reverse order the format requires, and the checksum is computed by an
independent helper in the test module.

## What is still not qualified

The honest limitation is that every one of these volumes is written by the test,
from the specification. That proves the reader follows the structures as this
project reads them; it does not prove agreement with an established
implementation. A qualified next step is to format a volume with a real FAT
implementation and compare the reconstructed listing and bytes, but no such
implementation has been run here, and `7z` was not used because it lists healthy
volumes and hides exactly the damaged structures these tests are about.

Also unchanged: directory cluster chains are not cross-link checked, FSInfo
hints remain advisory, long names whose checksum does not cover the short name
fall back to the short name rather than being repaired, and there is
deliberately no write path.

## Verification for this checkpoint

- `tests/portable/test_fat_volume.py`: 10 tests pass.
- `tests/portable/test_intelligence_extract.py`: 16 tests pass, including the
  existing FAT32, VFAT and classification cases.
- `tests/portable/test_arc_crunch.py`: 12 tests pass.
- `tests/portable/test_archive_*.py`: 53 tests pass.
- `tests/portable/test_disk_images.py`: 28 tests pass.
- `tools/archive/capabilities.py` reports the generated document as current.

The full portable suite was not run locally; the supervisor and observer
subprocess tests exceed the local budget, and the CI matrix carries the rest.
