# Standing secondary workstream: archival format coverage

Operator approved 2026-11-20. See [backlog](archive-format-backlog.json)
and the [preservation ecosystem roadmap](preservation-roadmap.md).

## Scheduling

During an already authorized Codex campaign, after primary deliverables and
required checks are complete, choose independent work packages from the
backlog while quota remains. Do not wait for a format to appear in the
corpus. Favor complete, independently reviewable increments; record usage
receipts and checkpoint early near exhaustion. Do not redeem resets, start
extra turns or unattended dispatch, or launch emulators solely under this
workstream. Existing priorities, authorization and publication rules apply.
Rank work by relevance, prerequisites, effort and remaining capacity; split
larger families as needed. Preserve resumable records of unfinished work.

## Architecture

Separate acquisition from offline intelligence. Keep original bytes,
receipts and provenance immutable. Introduce composable handlers for
identification, decompression, track/flux decoding, sector access, partitions,
filesystem interpretation and recursive ingestion. Do not conflate a capture
format, recording encoding, geometry and filesystem. Preserve existing
interfaces and avoid a premature physical repository split or large refactor.
Use structural evidence rather than extensions alone.

Prefer straightforward native implementations where independently testable;
use optional external CLI adapters for complex mature implementations.
Candidate tools, not qualified dependencies, include Greaseweazle,
FluxEngine, Aaru, Disk Utilities, libarchive, Ancient, CiderPress II, VICE
c1541 and libyal. Evaluate licensing before incorporating source or
redistributing tools or fixtures. Do not combine GPL-2.0-only code with
GPL-3.0-or-later code as if compatible. Evaluate independent executable
integration separately. Record helper versions, configuration and commands.

## Recording and recovery

Retain original captures, individual track hashes, timing and revolutions;
recognize grouped multi-file captures. Distinguish capture, decoded bitstream,
recovered sectors, normalized image, filesystem member and reconstructed
derivative. Record competing geometry/encoding hypotheses, CRC validity,
missing/conflicting sectors, weak bits and deleted-data marks when observable.
Never silently zero-fill missing sectors and represent them as verified.
Multi-source recovery must record contributing captures and sector-level
decisions. Derivatives never replace originals.

## Qualification

For each format/variant, cite specifications, define supported operations,
use synthetic or suitably licensed specimens and compare extracted bytes
and metadata with independent implementations where practical. Test malformed,
truncated and ambiguous data, unsafe names, duplicate members, decompression
bombs, recursion limits, helper timeouts and cancellation. Keep original
executables inert. Bound and isolate external helpers, including output paths,
resource use and network access. Preserve partial, unsupported and error
states with recursive provenance.

Maintain a machine-readable capability registry separate from the backlog:
format/variant, identify/decode/list/extract/validate, dependencies, versions,
specifications, fixtures, limitations and evidence. Generate documentation
from qualified capabilities, not plans. Integrate selective cached-analysis
invalidation/requeue so newly supported formats can be revisited without
rebuilding the entire index.

Use separate test databases, read-only inputs and isolated working directories.
Do not interrupt the live downloader or contend with the production index
writer. Keep acquired media, original recordings and private indexed evidence
outside Git. Publish only eligible reviewed code, metadata and test specimens.
Run applicable regression, audit, REUSE and packaging checks. Commit each
coherent package on a review branch; do not self-merge. Continue selecting
packages while authorized capacity remains and stop at a durable checkpoint.
