# Laboratory storage audit, November 23, 2026

This read-only campaign covers [issue #169](https://github.com/smartyhall/deskmate-formats/issues/169).
The standing housekeeping instructions were reviewed as proposed in
[PR #170](https://github.com/smartyhall/deskmate-formats/pull/170). It was
open at startup and merged during the audit. The operator's exact-path reclamation proposal,
file inventory, and lineage records are in the private lab evidence archive.

## Capacity and coverage

The Windows guest saw a 256 GiB VMware virtual disk. Its NTFS volume was
255.884 GiB with 133.655 GiB free near startup and 133.481 GiB free at the
end of scanning. This was 52% free at both observations. The guest's
partition allocation and file allocation are measurable. The outer VMware
datastore, backing disk allocation, snapshot chains, and free space require
host-side observation. The two guest storage providers reported different
disk sizes. The volume and partition results agree with the 256 GiB size
reported by `Get-Disk`. No capacity changes or intentional reclamation
occurred during this campaign.

**Operator clarification (November 23):** This Windows 10 guest runs on the
Dell server's VMware ESXi instance, not a Mac-local hypervisor. The operator
expanded its virtual disk from approximately 128 GiB to 256 GiB after observing
only about 6 GB free. The figures above are **post-expansion** measurements,
not space recovered by the audit or evidence that the original capacity was
comfortable. Free space on the ESXi datastore and the VMDK's actual host-side
allocation were not measured in this guest-only audit.

The catalog covers 20 scope shards across project directories, source
worktrees, ROM and emulator resources, and provisioned support tools. It
recorded 385,573 file entries, 955 image-like entries, and 17 scope boundaries
including directory exclusions used to avoid double-scanning and the audit's
own output directory. The sum of file lengths was 79.93 GiB. Observed file
allocations totaled 80.45 GiB before correcting for repeated hardlinks and
approximately 79.83 GiB after that correction. About 42.58 GiB of the
volume's used space is outside the resulting file-allocation total.
That residual also covers filesystem overhead, normal churn, and audit
outputs. Windows system data, unrelated profile contents, and hypervisor
storage were outside the inventory scope. [Inventory method](lab-storage-inventory.md)

| Consumer | Observed allocation before hardlink correction |
| --- | ---: |
| Win98 restore-test workspaces | 24.00 GiB |
| Win98 checkpoint family, including archives | 20.38 GiB |
| Private research evidence and working products | 15.58 GiB |
| Emulator machine workspaces, including the original Win98 install | 10.52 GiB |
| MSYS2 build environment | 3.89 GiB |
| Historical references and acquisitions | 2.30 GiB |
| Source worktrees, emulator source, and their build outputs | 0.98 GiB |
| Remaining measured roots, including tooling, ROMs, and installation media | 2.82 GiB |

The protected TVDog mirror accounted for 2.21 GiB within historical
references. The audit queried its file metadata and left its transfer,
content, and index state alone.

The project held three distinct 86Box executables by length, including the
main automation build and two instrumented audio research builds. Keep the
instrumented builds with their experiment receipts. Two files with a
`.snapshot` suffix were saved Git indexes in a recovery workspace.

## Win98 lineage and attachments

The 12 Win98 hard disks accounted for 48.00 GiB of independently allocated
NTFS storage. Each was 4,294,950,912 bytes in file length and in allocation,
consistent with the configured 8,322 cylinders, 16 heads, 63 sectors, and
512-byte sector size. The 86Box references, original copy receipts, and
bounded footer probes support direct raw disks. The ancestry is a copy
relationship. The scan found no recognized VHD, VHDX, VDI, VMDK, or known
VM snapshot artifacts in its roots. Host-side chains and hidden or
privileged attachments remain outside that finding.

- The retail stock installation has an original provisioning workspace, a
  sealed verified tree, and a round-trip extraction. All three hard disks
  matched sampled ranges. A current full SHA-256 of the extraction matched
  the recorded sealed stock digest. The verified archive also matched its
  recorded digest. The incomplete first archive remains historical evidence.
  [Stock restoration and archive verification](win98se-restoration-20261120.md)
- The Creative sound, February 2004 security update, and VB6/DM_Music results
  are distinct checkpoints from the shared Win98 installation. Each matched
  its likely donor working disk at sampled offsets. The donor for the
  VB6/DM_Music checkpoint started as a stock restoration. The retained
  screenshots, registry data, and audio results establish research value.
  [Win98 experiment and checkpoint history](win98se-restoration-20261120.md)
- The DM_Music continuation, MidiMapper, and later semantics working disks
  differed at sampled offsets. Preserve them with their associated workspace
  evidence. [Continuation](extended-resume-20261120.md)
  [MidiMapper](midimapper-win98-20261120.md)
  [Semantics](midimapper-semantics-20261120.md)
- Same-size DOS disks form a separate triage group. The shared geometry and
  documented baseline lineage describe their origins. Their current contents
  and the location of every generated result require per-experiment review.
  Keep the sealed DOS baselines and research workspaces.

Sampling used 18 MiB per Win98 disk across the prefix and dispersed offsets.
It confirmed differences where samples diverged. Matching samples leave
the rest of the disk unverified. The only full Win98 disk read was the
round-trip extraction.

Across the reviewed 86Box configs, 159 stored media references yielded five
unresolved literal paths. Those were relative CD paths in copied checkpoint
trees. They are **unresolved as literal stored paths**, not confirmed missing
CD images or evidence that a currently running emulator has a broken mount.
A copied configuration might require path resolution relative to its original
working directory; that behavior has not been independently verified for these
five entries. Before restoring any affected checkpoint, compare its original
configuration and working directory with the copy, resolve the referenced
media against the preserved source, and review the private exact-path inventory.
Do not rewrite or relink historical checkpoints merely to clear this audit
finding. No emulator process was observed during checks, and Windows
Restart Manager returned zero visible applications for each of the 12
Win98 hard-disk paths. The VM had one reported VMware SAS disk and a loaded
VMware optical drive. The guest could not identify the optical backing file
or obtain an elevated Windows virtual-disk listing. Recheck actual use and
all references immediately before any approved reclamation.
[Microsoft Restart Manager](https://learn.microsoft.com/windows/win32/api/restartmanager/nf-restartmanager-rmgetlist)

## Ranked reclamation proposals

| Rank | Target | Potential allocation freed on C: | Required decision |
| --- | --- | ---: | --- |
| 1 | Verified stock round-trip extraction, hard disk only | 4,294,950,912 bytes | Approve the exact path after confirming rollback and current references. Keep the verified archive and sealed stock. |
| 2–4 | Three donor working disks with checkpoint counterparts | Up to 12,884,852,736 bytes | For each, verify full current identity, account for unique workspace evidence, and approve separately. |
| 5 | A generated documentation preview | Up to 2,088,664 bytes | Verify byte coverage against a clean rebuild and approve the exact generated files. |

The 4 GiB extraction is the highest-confidence proposal. Its rollback uses
the already verified archive and member inventory. The working clone
proposals use the surviving checkpoint, rebased media, and recorded
hardware profile. The original provisioning workspace, distinct research
states, ROMs, historical media, archives, and the TVDog mirror are protected.
The MSYS2 package cache remains on hold pending independent restoration
sources for the pinned packages. Review the private report for each
candidate's exact paths and prerequisites.

For ongoing housekeeping, refresh the affected shard when an experiment
creates or seals a clone and put a retention review date beside its
provenance. Revisit candidates during already-authorized spare capacity.
Periodically record **two separate headroom measures**: free space inside the
Windows guest and free capacity on the Dell ESXi datastore, if host-side
read-only telemetry is available. The guest inventory tool cannot measure
ESXi datastore headroom or provide continuous monitoring on its own. Treat
future low-space observations as a reason for renewed review, **not** as
permission to perform reclamation without a new exact-path operator approval.
[Inventory tool and provenance fields](lab-storage-inventory.md)
