# Proposed Codex laboratory supervisor — design and integration plan

**Status:** Architectural proposal, not implemented.
**Companion:** [DeskMate Observatory v2 functional specification](observatory-v2-spec.md).
**Deferred successor:** [Headless and reproducible research appliance roadmap](headless-research-appliance-roadmap.md) (only after validated Windows observer/supervisor).
**Scope:** Local Windows 10 research workstation and multiple isolated Codex/86Box
experiments. This note records proposed behavior; it does not authorize any
currently running Codex process or emulator to be controlled.

## 1. Why add a supervisor?

The observatory answers *what happened* and *what is visible*. A supervisor
would answer *what should run next*, route authorized instructions to an agent,
preserve work at safe checkpoints, and coordinate independent workers.

The operator's goal is to stop manually relaying instructions and answers
between ChatGPT and a running desktop Codex conversation. High-level plans
would live in Git, with a small always-on service accepting queued tasks and
reporting reviewable results. The operator can continue to discuss objectives
with ChatGPT; a task or approved steering message submitted through a known
source can be picked up without logging into the VM or opening RDP.

Design for a single user and a trusted laboratory LAN. Distinguish read-only
browser viewing from privileged orchestration; do not create emulator control
routes in the observer, even in trusted-LAN mode.

## 2. What Codex actually exposes

- `codex exec --json` emits structured events for **that CLI invocation**.
  Do not assume an existing desktop-app turn emits the same separately
  attachable stream.
- Codex app-server exposes bidirectional thread/turn lifecycle and notifications.
  On a session the supervisor owns, `thread/start`, `thread/resume`, `turn/start`
  and `turn/steer` can create, continue and steer turns; approvals and tool
  notifications can be handled using the documented protocol.
- The Codex SDK is a simpler option for single-task or scripted execution;
  app-server is a better fit for a durable multi-thread client with approvals.
- The terminal `/app` command can continue a CLI session in the desktop app,
  but does not prove that a separate supervisor can subscribe to or steer an
  arbitrary active desktop conversation. Treat desktop-session attachment as
  an experiment, never as a required dependency.
- Do not scrape private thinking or claim to know reasoning progress merely
  because a process exists. Record transport health, last actual activity,
  and explicitly reported approvals separately.

Official integration references:
[App server](https://learn.chatgpt.com/docs/app-server),
[Codex SDK](https://learn.chatgpt.com/docs/codex-sdk),
[Non-interactive execution](https://learn.chatgpt.com/docs/non-interactive-mode),
[Codex developer commands](https://learn.chatgpt.com/docs/developer-commands).

## 3. Process boundaries

~~~mermaid
flowchart LR
    G[Git instructions and review PRs] --> Q[Supervisor inbox]
    Q --> S[Durable scheduler and policy gate]
    S <-->|thread/turn events and approvals| A[Supervisor-owned Codex app-server]
    S --> X[CLI exec worker for bounded batch jobs]
    A --> W[Per-job Git worktree]
    X --> W
    A -->|authorized native controller| E[Disposable 86Box clone]
    S --> J[(Private event journal and job ledger)]
    A --> J
    X --> J
    E -->|owner-approved observations| O[Observer publication]
    J -->|read-only normalized feed| O
    O --> B[LAN browser viewers]
~~~

**The browser must never send input through this diagram.** Supervisor RPC,
task approvals, and cancellation are outside the observer HTTP listener,
preferably limited to the local host and the authenticated operator.
Emulator native socket authority stays with its exclusive controller.

## 4. Trusted task inbox

Start with a repo-backed manifest under a documented path such as
`ops/tasks/*.yaml` (exact schema/version to be chosen), consumed only from a
configured trusted branch, normally protected `main`. An optional GitHub Issue
or PR-comment adapter can translate a user-approved instruction into the same
schema. A private local spool provides a fast path when waiting for a push is
unnecessary. A plain repository README, arbitrary diff or PR comment is not
automatically an executable instruction.

Example of *data*, not a command to run:

~~~yaml
schema_version: 1
id: calendar-e20-geometry
type: start
title: Inspect dialog geometry
source_ref: docs/research/calendar-dialog-activation.md
working_branch: research/calendar-e20-geometry
profile: research
resources:
  - "emulator:rsx-experiment-02"
depends_on:
  - calendar-dialog-activation-merged
max_parallelism: 1
checkpoint_policy: milestone
status: ready
~~~

A task may request: `start` a new thread, `queue` a follow-up, `steer` an
already active supervised turn, `cancel` that turn, or `respond_to_approval`
using an explicitly identified pending request. Treat these as separate,
versioned operations. Each submitted operation has a unique ID, source
commit or issue revision, intended thread/turn ID, optional expiry and
idempotency key.

**Never execute arbitrary shell text merely because it appears in Git.**
The structured task is an instruction to a supervised agent subject to its
configured sandbox, explicit resource leases, and authorization policy.
Restricted emulator memory reads, destructive guest operations, and new
network exposure still need the operator's approval. Replying to a pending
approval must match the exact request ID and authorized scope; the supervisor
does not click blanket "yes" by default.

## 5. Durable scheduler and conversation control

Persist a ledger outside Git before dispatching anything:
`discovered → validated → queued → leased → dispatched → running →
waiting-approval → completed/failed/cancelled`. Record the task ID, source
revision, run ID, app-server endpoint/owner PID and creation time, thread ID,
active turn ID, worktree, lease(s), timestamps, output commit IDs and error
state. Recovery after restart must not replay already accepted instructions.

Use one **supervisor-owned** app-server connection or carefully coordinated
client process per agent group. Keep saved thread IDs. Use `turn/start` for
new or idle work, `turn/steer` only with the exact active `expectedTurnId`
for deliberate mid-turn changes, and queue a future turn by default. On
disconnect, read the saved thread history/state before deciding whether to
retry; deduplicate operations by task ID and source revision.

Existing desktop-app conversations are not seized or modified. Initial
adoption should allow current desktop work to finish naturally, then
transition a new task to a supervisor-owned thread. Investigate handoff with
a disposable test thread before promising desktop/CLI interoperability.

Keep the operator's higher-level conversation with ChatGPT separate from
Codex's experiment details. Task manifests and completion summaries are the
handoff boundary; the supervisor should not automatically make ChatGPT
messages or approvals on the operator's behalf.

## 6. Checkpoint commits and remote preservation

A checkpoint manager may commit and push **on each job's own branch** when
a meaningful milestone completes, and optionally at a conservative elapsed
interval when the worktree contains coherent, publishable changes. It should
never rewrite or force-push `main` or automatically merge PRs.

Suggested checkpoint sequence:

1. Acquire the per-worktree Git lease and identify the exact starting commit.
2. Snapshot `git status` and identify private/proprietary paths; use explicit
   project allowlists and existing audit rules before staging.
3. Capture the agent's claimed milestone and actual test/audit results;
   distinguish tests not run from tests passed.
4. Stage only eligible files, record staged file hashes and verify the audit.
5. Commit with a task/milestone identifier, parent SHA and an honest WIP or
   tested label. Do not claim successful validation if the checks failed.
6. Push to the job's remote feature branch, preserving a local commit and
   retryable pending-push state if the network fails.
7. Publish `git.checkpoint` / `git.push` events. Open or update a draft PR
   when a coherent milestone is reviewable, but leave final merge to review.

Avoid commits while a file is being written: coordinate a checkpoint barrier
with the agent if possible, or require a verified stable Git snapshot.
Do not indiscriminately stage all files or include lab disks, ROMs, raw RAM,
tokens, private environment files, or original DeskMate executables.

Important distinction: frequent commits preserve **source progress**, not
the complete emulator state. Preserve guest disk/config/NVRAM and native
evidence through the separate private experiment manifest and hash discipline.
Checkpoint publication must not reset or release a held emulator.

## 7. Parallel workers and exclusive resources

Use a dedicated Git worktree and branch for each independent worker. The
scheduler may run multiple read-only/static-analysis or independent fixture
tasks concurrently. Avoid same-file editing collisions by assigning module
or directory ownership, and reconcile through PRs rather than shared writes.

A per-emulator lease is stronger: only one authenticated native controller
may own a given clone and port. Other agents can read already-published
observer data, but cannot obtain another native control connection just
because they started in parallel. Reserve additional locks for Ghidra
project writes, source checkout changes, private evidence paths, and shared
test installations as necessary.

Dispatch classes:
- **Cheap deterministic work:** use ordinary scripts to manufacture synthetic
  fixtures and verify hashes; Codex is needed to design/test the generator,
  not to manually repeat known mechanical steps.
- **Short independent reasoning:** parallel Codex threads for documentation,
  code review and isolated static targets.
- **Live emulator research:** serialized under a named emulator lease, with
  provenance and exact-memory authorizations.
- **Integration:** one worker consolidates results and opens a reviewable PR.

Use bounded concurrency, optional model/effort budgets and measured throughput
rather than assuming many parallel agents are always faster. Remember that
several workers may share the same plan usage quota and hardware resources.

## 8. Observer feed integration

Publish structured events into the private journal specified by Observatory v2.
Include task discovery, acceptance/rejection, queue depth, leases, starts,
real Codex item/tool/plan notifications, approval requests, quiet periods,
tests, experiment checkpoints, Git commits/pushes/PRs, retries and final status.

Expose source heartbeat, process liveness, and agent-reported activity as
independent timestamps. When there are no new Codex notifications, display
"process alive; no new agent event for N minutes", not "thinking".
The operator can view approval-required information from the LAN browser,
but the observer remains read-only. An approval is supplied through a
separate authorized channel, never through the display endpoint.

## 9. Minimal rollout and validation

| Phase | Priority | Functional result | Test |
| --- | --- | --- | --- |
| S0 — Architecture probe | P0 | Verify app-server protocol and own-thread telemetry on actual Windows VM; document existing desktop-session attachment limits | Start a disposable thread, observe events, resume after restart; no live emulator |
| S1 — Task intake | P0 | Versioned Git task manifests, append-only queue ledger, manual dispatch | Same task revision seen twice produces one run; malformed/untrusted tasks rejected |
| S2 — Managed turns | P0 | One supervised app-server Codex thread, new turns, queued prompts and exact-ID steering | Queue and steer observed under test; approval only when explicitly authorized |
| S3 — Checkpoints | P1 | Milestone commits, remote branch push and draft PR updates | Induced connection failure leaves local commit; retry never duplicates/moves unrelated branches |
| S4 — Parallelism | P1 | Independent worktrees, per-resource leases and bounded concurrent workers | Two synthetic workers run independently; one emulator lease blocks a second controller |
| S5 — Recovery | P1 | Supervisor service, journal replay, crash/reboot recovery, process identity audit | Kill/restart service during queued/running/approval states without duplicated dispatch |
| S6 — Console integration | P1 | Supervisor feed linked into Observatory v2 LAN view | Five viewers, no guest time or socket activity from browser refresh |
| S7 — Optional adapters | P2 | Existing desktop-log observer, GitHub Issues adapter, push notifications | Capability-gated adapters never assume unauthorized attach; replayed events deduplicated |

Prefer S0/S1 as the first independent PR, then S2, then S3. The observatory's
M0/M1 event journal can be built in parallel using agreed event envelopes.
Keep the implementation small, inspectable and restartable rather than
creating a second full-featured distributed workflow engine.

## 10. Operational limits and open questions

- Desktop app events may share the Codex harness, but the desktop process is
  not assumed to expose a supported public subscription endpoint for unrelated
  controllers. Validate with a disposable session, not the live research chat.
- The Codex app-server transport and protocol details may vary by installed
  version. Generate its version-specific JSON schema for integration tests.
- Supervisor and task-inbox credentials are local secrets, separate from the
  read-only LAN viewer. Never put a Codex control endpoint on the LAN by
  accident. Where remote control is later desired, use explicit authentication
  and an independently reviewed interface.
- Incoming Git tasks should be trusted operator instructions; do not treat
  arbitrary third-party PR text as authority. Protect against task-file
  rewrites or replay, branch confusion, invalid resource names, and
  instructions trying to override sandbox/approval policy.
- Git can checkpoint source but not held guest RAM, unsaved UI state, or private
  media. The experiment archive remains the source for those artifacts.
- Do not silently resume, reset, or quit existing emulators while restoring
  the supervisor. A stale lease becomes "needs operator reconciliation".
- A manual operator must be able to stop dispatch, recover worktrees, and
  continue a task in the usual desktop or CLI client.

**Success criterion:** After initial setup, an approved task can be committed
to the trusted Git inbox, start a supervised Codex thread, publish honest
progress to the read-only LAN observatory, preserve code at safe checkpoints,
and produce a PR for the operator to discuss/review without using RDP.
