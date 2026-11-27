# Candidate deterministic procedures for archival operations

Campaign `freebuff/archive-qualification-2`. This is a handoff document for the
concurrent Supervisor campaign. Nothing here registers a procedure, starts a
worker or changes the Supervisor's worktree; the purpose is to describe what the
archival tools can already do deterministically, so the Supervisor's owners can
decide what is worth adopting.

## Why these are candidates rather than registrations

Each procedure below maps onto an existing entry point in `tools/archive`. Some
are read-only, some write derived artifacts into a caller-supplied directory, and
one proposes an index change that is explicitly not authorized. Registering any
of them for unattended execution needs the Supervisor's own review, because the
authorization profile differs between them and a single "archive" role would
hide that difference.

## Common contract

| Field | Requirement |
| --- | --- |
| Input identity | Absolute path plus expected SHA-256 and byte size. A procedure must refuse to run when the observed digest differs from the expected one. |
| Bounds | Input bytes, per-member bytes, aggregate bytes, member count, recursion depth and a wall-clock deadline. The defaults already exist in `intelligence_extract.Limits`. |
| Deadline | Enforced by the caller and by the tool's own `tool_seconds` for external decoders. |
| Result | JSON with `status`, `detail`, `members[]` (ordinal, name, size, sha256, status), and a `provenance` block naming tool version, bounds and observed digest. |
| Failure | A non-`ok` status is a result, not an exception. Unsupported and partial must never be reported as complete. |
| Provenance | Every derived artifact records its parent digest; no procedure may present a derivative as the acquired artifact. |

## Candidates

| Procedure | Read-only | Existing entry point | Notes for the Supervisor |
| --- | --- | --- | --- |
| `archive.identify` | yes | `intelligence_extract.identify` | Returns a kind token plus, since this campaign, the identity axes (`classify`). Cheap and safe to run on any path inside the workspace. |
| `archive.inspect` | yes | `intelligence_extract.extract` without persistence | Metadata and member listing only; no member bytes are returned if a `members=0` limit is used. |
| `archive.list` | yes | same | Member enumeration with per-member status, bounded by `members`. |
| `archive.validate` | yes | CRC/size checks inside `_arc`, `_lha0_entries`, `_fat` | The result carries the integrity statement; a mismatch is `read-error`, not a pass. |
| `archive.extract` | no: writes derived bytes | `intelligence_extract.extract` | Must be given an output directory it owns; the tool itself writes no member paths. |
| `image.normalise` | no: writes a derivative | `disk_images.to_lba` | Records missing and conflicting sectors; an incomplete image must stay `partial`. |
| `image.filesystem` | yes | `intelligence_extract._fat` through the container reader | Reports volume observations (divergent FAT copies, FSInfo, backup boot) separately from member results. |
| `capabilities.query` | yes | `tools/archive/capabilities.py` | Returns the registry record and whether the generated document is current; a stale document is a failure. |
| `index.missing-axis` | yes | `tools/archive/index_migration.py missing_axis` | Reads a database given by path; must only ever be pointed at a disposable copy. |
| `index.migrate` | no: mutates a database | `index_migration.migrate` | **Not authorized for unattended use.** Requires an operator-supplied copy and an explicit review. |
| `decoder.compare` | yes | two extractors over one digest | Compares member bytes and CRCs between an external decoder and the native one; a divergence is a finding, not a failure. |

## Authorization notes

- `archive.extract`, `image.normalise` and `decoder.compare` create files. They
  should declare an owned scratch or output directory, and their results should
  name it, so a later cleanup can be bounded.
- `index.migrate` changes durable state and is out of scope for this campaign.
- No candidate launches an emulator, reads a private specimen directory, or
  reaches the network. Corpora stay caller-supplied paths.
- The two external tool paths (`7z`, `lhasa`, and optionally `nomarch`) are
  supplied by the caller. A procedure should report which of them was actually
  used, and must never claim a native extraction when an adapter ran.

## What is missing before registration

1. A stable JSON schema for the result envelope, shared with the Supervisor's
   other procedures rather than invented per tool.
2. A conformance test that runs each read-only procedure against a committed
   synthetic fixture, so the Supervisor can detect a regression without corpus
   access.
3. A decision about whether `archive.validate` and `archive.extract` should be
   one procedure with a mode, since they share a code path but differ in
   authorization.
