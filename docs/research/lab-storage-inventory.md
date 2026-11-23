# Read-only laboratory storage inventory

Use [`tools/lab_storage.py`](../../tools/lab_storage.py) with Python 3.13 or
newer. Keep its JSON in a dedicated private directory outside source control.
The catalog contains absolute paths. Start with named project-owned roots,
prefer one shard per experiment or worktree, and leave unrelated profiles,
network shares, and external volumes out of scope.

```powershell
python tools/lab_storage.py $experiment $checkpoints --catalog $privateCatalog --resume
```

Each completed root has a timestamped JSON shard with file paths, file length,
observed allocation and method, hardlink count when known, modification time,
and scan gaps. Same suffix and length group potential duplicates within a
shard. Supply disjoint roots for totals. Use repeatable `--exclude` arguments for
known boundaries. Directory symlinks and Windows reparse points are skipped.
A shard is published atomically after its root finishes. `--resume` reuses
completed shards for the same scope, including historical gaps. Omit it to
refresh a changed root or retry gaps. An interrupted root restarts from its
beginning. Catalog timestamps let the reader distinguish aged and fresh
observations. For a live tree, treat the scan as a series of observations.

On Windows, regular file allocation comes from
[`FileStandardInfo`](https://learn.microsoft.com/windows/win32/api/winbase/ns-winbase-file_standard_info).
Sparse or compressed files use
[`GetCompressedFileSizeW`](https://learn.microsoft.com/windows/win32/api/fileapi/nf-fileapi-getcompressedfilesizew).
On POSIX, the tool uses `st_blocks × 512` where available. Unknown allocation
is JSON null. The file results concern the measured filesystem. Shares,
hardlinks, alternate streams, directory metadata, hypervisor snapshots, and
underlying datastore allocation are separate considerations. A hardlinked
path contributes no independently reclaimable allocation while another link
survives.

Request whole-file SHA-256 only for a specific comparison with decision
value. The byte budget covers the sum of logical lengths read on that
invocation. Identical receipts with unchanged path, file identity, length,
and modification time can be reused on resume. The hash is finalized only
after the apparent file signature still matches. Refresh it before a
consequential decision on mutable media. Each selected file checkpoints
individually. An interrupted file restarts from byte zero.

```powershell
python tools/lab_storage.py $experiment --catalog $privateCatalog --resume --hash-budget 104857600 --hash-file $knownCopy
```

For classic VHD investigation, the module's bounded footer helper can read
the advertised capacity, image ID, and a differencing disk's parent ID and
name. Treat those fields as declared metadata. Confirm the parent present
on disk, its identity, and all attach paths before counting any savings.
Other container formats need their own inspectors. For raw 86Box disks,
compare the logical length, configured IDE geometry, and checkpoint receipts.
Parentage through copying belongs in the research record even for a raw
disk that can boot independently.

At clone creation, add a private record with a stable asset ID, current
path, creation time, experiment or issue, copy source and source digest,
container type, and any runtime parent ID. Include the hardware profile,
config, NVRAM, ROM/build pins, external media, fixture and evidence locators,
observed attachment, and restore receipt. Assign a review date at creation
and refresh the affected catalog shard when a clone is sealed, forked, or
retired. At review, record the surviving restoration source, verification
status, and the operator decision. A review date triggers inspection.
