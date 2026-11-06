# Independent requirements for Supervisor S2–S5

Baseline for [issue 62](https://github.com/smartyhall/deskmate-formats/issues/62),
derived from DeskMate Formats commit `ce2db0a2eebd3c69883ddbc4961245d4be25815c`
before examining external orchestrators. The shipped offline S0/S1 behavior
governs where the design proposal sketches a broader contract.

## Hard constraints

| ID | Requirement and acceptance boundary | Basis |
| --- | --- | --- |
| R1 | Separate observation, dispatch, approval and native control authorities. Browser GET/HEAD consumes immutable owner-published projections only. Refresh, replay and extra viewers cause zero native requests and zero guest-time advancement. No privileged browser routes, including approvals. | [Observatory](observatory-v2-spec.md), [supervisor](codex-supervisor-design.md) |
| R2 | Discover only exact Git objects under the configured local source, ref and ancestry policy. Review the exact bytes and referenced material. Discovery grants no queue authority, and accepting a revision grants no dispatch authority. Re-delivery preserves the original decision. Changed bytes or reused keys fail closed. Operator-maintained Git trust and private queue custody are explicit assumptions. | [S1](codex-supervisor-s1.md) |
| R3 | Only control owned, version-checked app-server sessions. Persist a stable operation identity before writing to the wire. Never automatically replay a mutation that may have been sent. Use exact saved thread/turn identities and authoritative read-only evidence where available. Keep unacknowledged starts and ambiguous results unresolved. A transport ID alone supplies no cross-session idempotency. | [S0](codex-supervisor-s0.md), [supervisor](codex-supervisor-design.md) |
| R4 | Queue follow-ups by default. Steer only with deliberate authorization and the exact active turn ID. Approval authority stays local and separate, bound to the exact generation, request, thread, turn, item and permitted decision. Reject stale, duplicate and mismatched decisions. | [S0](codex-supervisor-s0.md), [supervisor](codex-supervisor-design.md) |
| R5 | A held experiment has one authenticated native controller per clone and port. Restart, expired ownership, worker replacement and workspace cleanup must never reset, resume or mutate a held guest or transfer custody implicitly. Stale or ambiguous custody requires operator reconciliation. Bound native reads and scope RAM/display approvals to verified identity and checkpoint per the applicable publication policy. | [MCP](86box-readonly-mcp.md), [supervisor](codex-supervisor-design.md), [appliance roadmap](headless-research-appliance-roadmap.md) |
| R6 | Keep durable receipts, raw prompts/tool output, secrets, private evidence and original commercial inputs outside public Git. Publish only approved reduced telemetry. Record artifact identities and provenance. Git checkpoints cover source, while guest evidence has its own private archive. Checkpoints need stable eligible files, audit and branch-specific authorization. Preserve a local commit through push failure and keep merging under operator review. | [S0](codex-supervisor-s0.md), [S1](codex-supervisor-s1.md), [supervisor](codex-supervisor-design.md), [licensing](../../LICENSING.md) |
| R7 | Keep Windows 10 the operational target and use portable synthetic validation first. Live recovery, unattended operation and actual guest/control isolation must be demonstrated on Windows before an authorized Linux feasibility probe. Linux, containers and Nix are deferred. | [appliance roadmap](headless-research-appliance-roadmap.md), [S0](codex-supervisor-s0.md), [Observatory](observatory-v2-spec.md) |

S0 has an offline send gate and bounded reconciliation, with no production
approval sender. S1 records reviewed queue decisions, with no dispatcher.
Neither establishes real child-tree recovery, live turn custody or emulator
lease recovery. The next phase must preserve these limits explicitly.

## Desirable capabilities and rollout

- **S2** — One owned worker with queue, exact-ID steering and independently
  authorized approvals. Prefer a small, inspectable local coordinator.
- **S3** — Reviewable milestone commits, resumable publication and draft PRs.
  Keep a checkpoint barrier and a private publication receipt.
- **S4** — Bounded concurrency with dedicated worktrees and branches,
  named shared-resource leases and independent read-only workers.
- **S5** — Durable queue/operation/process recovery across worker, service and
  host failures, plus a way for the operator to stop dispatch and reconcile.
  Preserve the no-replay and held-state invariants from the first live turn.
- **S6 and later** — Extend the existing normalized Observatory feed. Report
  process liveness, transport health, real agent activity and pending approvals
  separately. Supported desktop handoff, issue intake and a headless appliance
  are optional and independently gated.
