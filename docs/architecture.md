# Architecture and scope boundaries

The application-format implementation currently lives under
`src/deskmate_formats/calendar`: `personal.py` is the reader,
`writer.py` the experimental append writer and writer CLI, and `cli.py` the
read/list/export CLI. This is the **only implemented application codec** on
this baseline. Other package namespaces implement emulator automation,
read-only observation and offline-tested supervisor components; they are not
general DeskMate format codecs. See the [project status](../PROJECT_STATUS.md)
for their respective maturity and remaining live gates.

Conceptual layers guide later work:

| Layer | Current state / extraction rule |
|---|---|
| Binary reading and encoding utilities | Bounded reads/field rules remain in Calendar; extract a common helper only for a real second use |
| Database containers | Calendar profile plus [cross-application structural evidence](research/cross-application-db.md); no generic engine or cross-application API |
| Application formats | Calendar only; future siblings can be added after evidence establishes their structures |
| Conversion/interchange | Calendar JSON export exists; no general importer, iCalendar conversion or roundtrip guarantee |
| CLIs | Two installed Calendar commands; public Python API remains separate from listing presentation |
| Tests | Independent synthetic portable checks plus explicitly opted-in private archival regressions |
| Specifications/evidence | docs/formats, containers, experiments, evidence; original archive stays external |

There are deliberately no empty Address Book/Filer/Text/Worksheet/Draw modules,
common-engine base classes or conversion frameworks. A shared abstraction must have
experimental support and reduce real duplication, not encode an assumed .FIL family.

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
