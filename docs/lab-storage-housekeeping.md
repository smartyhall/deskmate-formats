# Standing secondary workstream: laboratory storage inventory

Operator direction 2026-11-23. Immediate dedicated campaign:
[issue #169](https://github.com/smartyhall/deskmate-formats/issues/169).
This complements [archival format coverage](archive-format-coverage.md),
[visual evidence curation](visual-evidence-curation.md), and
[experimental laboratory posture](research/experimental-lab-operating-posture.md).

## Objectives and scheduling

The recoverable Windows 10 DeskMate lab has accumulated multiple Windows 98
VM/installations, emulated disk images, experimental clones, snapshots,
software acquisitions and research outputs. Distinguish essential preserved
evidence from truly disposable derivatives, report storage pressure, and
provide an operator-reviewable plan for restoring free space.

After the primary campaign is complete, use remaining *already-authorized*
Codex capacity for **bounded, low-impact, read-only** inventory work. Choose
small, independently reviewable portions; checkpoint before usage exhaustion.
This workstream does not authorize extra model turns, unscheduled dispatch,
new emulator launches, site publication, purchases or host/guest disk
resizing. Do not compete with active experiments, image transfers, indexing,
the TVDog mirror or an active emulator. If storage is critically low, report
the blocker instead of creating large derivative files.

The next focused campaign may perform a broad assessment under issue #169.
Subsequent filler passes should maintain or improve the resulting catalog,
especially when new native experiments create disk images, and not repeatedly
rescan everything.

## Scope and asset classification

Start with the known project-controlled lab and research worktrees. Discover
related project-owned evidence archives, emulator profiles, virtual media,
Win 98 installations, snapshots/differencing files, downloaded installers,
captures and temporary outputs using existing receipts and configuration
pointers. Identify volume ownership and space limits before scanning.
Do not crawl unrelated user folders, other repositories, network shares or
host storage without explicit scope. Treat junctions, symlinks, mounts and
reparse points as boundaries rather than silently crossing them.

Each recorded item or image family should be classified as:

- **Original / acquired:** historical distribution media and other immutable
  source bytes; keep the original and provenance.
- **Sealed baseline:** hash-pinned installation and its required emulator
  ROM/configuration/NVRAM/dependencies; protect the full reproducible unit.
- **Research evidence:** native-generated documents, before/after disks,
  source-capture screenshots, logs and experiment receipts; preserve evidence
  and distinguish the canonical copy from derivatives.
- **Active / attached:** media currently opened by a running emulator, worker,
  filesystem driver, mirror/index process or referenced snapshot; no cleanup.
- **Reusable working environment:** known useful clone with documented
  relationship to a baseline; retain pending review.
- **Candidate disposable derivative:** genuinely rebuildable intermediate
  whose exact lineage, active use, dependencies and recreation steps have been
  independently verified.
- **Unknown:** provenance, ownership or dependencies unresolved; **retain**.

Record *logical* file size versus *allocated* on-disk size where available.
Dynamic, sparse, compressed and differencing formats can make these diverge.
A reported file length, guest disk capacity, VirtualBox image capacity,
Windows guest partition size and available host physical space are different
measurements. Distinguish them clearly and never promise reclaimed space from
logical-size totals alone.

## Private inventory and duplicates

Keep the detailed catalog **private**, ideally in a recoverable location
separate from high-churn scratch media. Suitable fields include private stable
asset ID, discovered and source paths, volume, filename, extension,
format/container if reliably known, logical and allocated size (with method),
SHA-256 when actually calculated, modification time, VM/profile and
configuration identifiers, parent/child and differencing relationships,
attachment/active state, creator experiment, provenance references, PR/issue
receipts, evidence class, rebuildability, protection status, and last verified
time. Mark unavailable fields *unknown*, not zero or no.

Use cheap metadata, filename, size and type triage first; group likely
duplicate candidates. Hash large files selectively, incrementally and
resumably with bounded I/O. Recheck changing files before treating a hash
as stable. A matching SHA-256 proves byte identity for the examined
snapshots, **not** that either copy is unneeded. Two visually similar
screenshots, duplicate-format archives or apparently identical Win 98
installations may have distinct provenance. Preserve occurrence-level
locators even after identity grouping; never replace originals with
inferred equivalents.

For VM images, explicitly assess linked/differencing disks, snapshots,
boot configurations and runtime attachments. Never delete an apparent
parent, move one part of a chain, deduplicate writable images using
hardlinks, or compact an image merely because it appears redundant.

## Reclamation proposal only

Build an operator-reviewed candidate table showing:

1. Exact private path or stable asset ID and its intended disposition.
2. Measured allocatable/physical savings, with assumptions and bounds.
3. Original/base dependency, provenance and last known experiment use.
4. Rebuild/restore procedure and needed surviving artifacts.
5. Confidence, risk and whether the asset is currently attached.
6. Prerequisite backup/snapshot and an explicit **approval pending** state.

The default action is **no modification**. This workstream does **not**
authorize deletion (even to Recycle Bin), moving, overwriting, unmounting,
snapshot cleanup/merge, image compaction, hardlink/reflink deduplication,
filesystem optimization, guest or host partition resizing, or changing
canonical filenames. Any later destructive cleanup must have a separately
reviewed, specific-path authorization and a measured rollback plan. Current
Codex workers must not infer approval from the existence of a task or PR.

If a space emergency prevents ordinary research, report critical consumers
and ask for an exact operator decision instead of attempting automated
recovery. The operator may independently expand the underlying VM disk;
that is separate from this inventory and from extending guest partitions.

## Reusable software and reviewable outputs

Prefer small, read-only, scope-bounded tools that work on Windows 10 and can
produce resumable private JSON/CSV/SQLite manifests and human-readable
summaries. Test against synthetic directory trees, fake sparse media and
simulated parent chains. Cover inaccessible files, symlink/reparse loops,
changed-under-scan files, incomplete hashing, duplicate names, interrupted
runs and known-empty directories. Scope and access must remain explicit.

Publish to the repository only authored guidance, general-purpose code,
synthetic tests, and sanitized aggregate statistics. Keep private path
inventories, commercial binaries, ROMs, media images, original personal
documents, credentials and raw evidence out of Git. A public PR may
describe where a *private* operator report lives without publishing its
contents. Follow `AGENTS.md`, `LICENSING.md`, REUSE, normal tests and review.

## Campaign completion / filler receipt

Report measured before/after space with filesystem and measurement method;
count and bytes of classified asset families; coverage and skipped locations;
high-impact consumers; duplicate candidates versus confirmed equivalences;
evidence/baseline dependencies; potential *allocated-byte* savings and
uncertainties; outstanding operator decisions; and next bounded work items.
If the run was inventory-only, state **zero bytes intentionally reclaimed**.
Checkpoint the private catalog, provide an eligible review PR for any code
or documentation changes, and record available Codex usage telemetry.

This workstream complements rather than outranks current native research
or the other secondary workstreams. It must not silently change the
emulator's visible-window preference. Future Observatory and dispatcher
improvements are independently tracked under issues #31 and #86.
