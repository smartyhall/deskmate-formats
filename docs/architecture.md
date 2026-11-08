# Architecture and scope boundaries

The package has **two bounded application codecs**, not a complete generic
DeskMate database implementation:

- `calendar/personal.py` and `calendar/writer.py`: the measured read/append
  profile plus opt-in SDK-derived date/time parsing and writing.
- `addressbook/personal.py` and `addressbook/writer.py`: the ten-page Address
  Book reader and experimentally verified **empty-to-one** contact writer.
- `database.py`: a read-only, evidence-bounded common table/schema/index/row
  parser used for overlapping structures; it does **not** allocate pages,
  resolve every DMDB loader call or impose universal ID semantics.
- `interchange.py`: strict version-1 **semantic** Python/JSON envelopes and
  explicit loss reporting, not lossless native reconstruction or network sync.

The application CLIs remain distinct from the storage/format APIs. Original
commercial archives and private evidence are external to source control.
See [project status](../PROJECT_STATUS.md), [compatibility](compatibility.md)
and [database implementation report](research/database-campaign.md).

| Layer | Implemented boundary / remaining limit |
| --- | --- |
| Binary framing and schema | Shared validated page/directory/index/DBCOLS reader, with opaque-byte preservation and bounded unsupported cases |
| Application interpretation | Calendar ordinary records and four independently populated Address Book fields; unsupported semantics stay raw |
| File writes | Calendar append in the six-page profile; Address Book empty-to-one; no general page growth/edit/delete |
| Interchange | Calendar/Address Book semantic JSON with explicit loss accounting; no CalDAV/CardDAV transport |
| Verification | Portable adversarial tests, historical native fixtures and four whole-file Address Book hash oracles; newer generated files still need native application acceptance |

The shared on-disk structures and three applications' DMDB call thunks are
observed evidence, **not** proof of identical allocation, deletion, sorting or
universal serialization behavior. Further common utilities should follow
validated cross-application behavior, not precede it.

## Emulator observation

`automation.readonly` owns one lazy, serialized native socket per configured
86Box instance. `automation.mcp_server` exposes the owner's read-only calls
through the MCP stdio SDK. Coherent held observations require operator control
of execution before handing off the socket.

`automation.observer_bridge` projects only approved status and display onto
immutable `observer.publication` streams. The owner tracks sequence and
continuity per instance and prepares browser images outside its native lock.
The optional loopback HTTP listener reads the registry, which has no reference
to a native socket or guest control. See the [observatory architecture and
operator boundaries](research/86box-observer-design.md#native-mcp-integration-and-security).

## Agent activity and task authority

`observer` implements bounded private event storage and an explicitly read-only
HTTP projection; optional Codex CLI telemetry reports only observable activity.
The offline-tested `supervisor` S0 app-server protocol/ledger and S1 Git task
queue are separate from that observer. S1 acceptance cannot launch a model turn.
The real S0 canary, automatic dispatch, worktree/resource leases and unattended
restart are not implemented or validated on this baseline. See the
[supervisor design](research/codex-supervisor-design.md), [S0](research/codex-supervisor-s0.md),
[S1](research/codex-supervisor-s1.md) and the [reuse assessment](research/agent-orchestrator-reuse-assessment.md).
