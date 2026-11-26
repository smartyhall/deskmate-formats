# Supervisor and Observatory current state — 2026-11-26

**Scope:** implementation-oriented audit of the Supervisor and Observatory as
they exist on `main` at `3d3f784` (merge of PR #185), plus the changes delivered
by the
[heterogeneous worker infrastructure campaign](heterogeneous-worker-infrastructure-20261126.md)
on `freebuff/supervisor-and-observatory-infrastructure`.

**Purpose:** replace contradictory descriptions in earlier planning prose. The
[Supervisor design](codex-supervisor-design.md) and the dated `PROJECT_STATUS.md`
snapshots remain historically accurate for their own checkpoints. Where they
conflict with this document, this document reflects the source, tests and
receipts inspected here.

**Method.** Read every module in `src/deskmate_formats/supervisor/` and
`src/deskmate_formats/observer/`; read the S0–S3 reports and their evidence
receipts; ran the portable Supervisor suite and the focused driver, ledger and
task tests on Windows 10 / CPython 3.13.17; inspected the pinned app-server
schema profile. No model turn, emulator or network service was started.

Evidence vocabulary follows `PROJECT_STATUS.md`: **implemented** means checked-in
source with the stated test scope, **offline tested** means verified without a
native application, **native observed** means verified in a controlled emulator
experiment, and **proposed** means neither.

## 1. Capability matrix

| Area | Implemented | Tested | Live-proven | Notes |
| --- | --- | --- | --- | --- |
| Pinned app-server protocol client | Yes | Yes, synthetic peer | Yes, one S0 canary (2026-11-16) | `protocol.py`; Codex CLI `0.166.0`, schema hash pinned |
| Durable operation receipts | Yes | Yes | Yes | `ledger.py`; unknown outcomes become `needs-reconciliation` |
| Single-use dispatch fence | Yes | Yes | Yes | `attempt.json` written before the first RPC |
| Trusted Git task intake | Yes | Yes | No | `task_git.py`; exact branch tip plus trust anchor |
| Manual accept/reject decision queue | Yes | Yes | No | `task_queue.py`; atomic unresolved-intent recovery |
| Text-analysis task dispatch (S2) | Yes | Yes, synthetic only | No | `bridge.py`; live dispatch explicitly disabled without separate grants |
| Source-edit task dispatch (S3) | Yes | Yes, synthetic only | No | `editing.py`, `workspace.py`; native editing unverified |
| Deterministic (no-model) execution | **Added** | Yes, real subprocesses | Yes, local development procedures | `procedures.py`, `deterministic.py`; see §7 |
| Common worker abstraction | **Added** | Yes | n/a | `workers.py`; capability negotiation, no pretend parity |
| Campaign registry and resource leases | **Added** | Yes | Yes, local coordination | `campaigns.py`; no blind takeover. Schema 2: leases carry owner identity, session and scope, and path resources resolve to canonical identities |
| Execution integrity binding | **Added** | Yes, including hostile cases | Yes, local runs | `deterministic.py`; plan binds working-tree content, implementation digest, module origins, interpreter and acceptance; `run` refuses on any drift |
| Process-tree inspection and recovery | **Added** | Yes, real parent/child processes | Yes, Windows and Linux | `process_tree.py`; owner status and descendant status are separate, recovery refuses while anything may run |
| Snapshot collector | **Added** | Yes | Yes, from real attempts and registry | `supervisor/snapshot.py` plus `deskmate-observer-snapshot`; unreachable sources are listed, unstated values stay unknown |
| Allowance-aware worker selection | **Added** | Yes, synthetic | No | `scheduling.py`; explicit unknowns, no unit conversion |
| Heterogeneous campaign projection | **Added** | Yes | Yes, synthetic concurrent workers | `observer/campaigns.py` plus read-only HTTP routes |
| Unattended Supervisor service / daemon | No | n/a | No | No service loop, scheduler daemon or auto-approval exists |
| Automatic PR creation or merge | No | n/a | No | Checkpoints are local refs only |
| Multi-worker concurrent dispatch | No (as a service) | n/a | No | Manual per-campaign operation only |

## 2. Task schemas and lifecycle

`task_manifest.py` is data-only. It validates strict UTF-8 JSON, at most 8 KiB,
with exact member sets.

| Version | Class | Resources | Purpose |
| --- | --- | --- | --- |
| 1 | `text-analysis-v1` | `source-read`, `synthetic-fixtures`, `portable-tests` | Read-only analysis task |
| 2 | `source-edit-v1` | `source-read`, `source-edit`, `portable-tests` | Adds `development` with exact source commit, file scopes, acceptance criteria, test profiles |
| 3 | `deterministic-v1` | procedure-declared subset | Adds `deterministic: {procedure, arguments}` validated against the reviewed procedure registry |

Version 2 requires `resources` to equal exactly `{source-read, source-edit}` plus
`portable-tests` when test profiles are requested. Version 3 requires
`resources` to equal exactly the procedure's declared resource set, so a task
cannot ask for less supervision than the reviewed procedure needs.

Queue lifecycle: `discovered → (accepted | rejected)` with `abandoned` available
only for an interrupted decision intent. A task revision is accepted once; the
next revision must increment by exactly one; the idempotency key is unique
across revisions; an accepted revision must be dependency-clean and unexpired.

**Correction to earlier prose:** the design document's `discovered → validated →
queued → leased → dispatched → running → waiting-approval → completed` ledger is
still a design sketch. The queue stores only the *decision*; it does not model a
full dispatch lifecycle. Execution lifecycle lives in separate private stores:
the Codex operation ledger (S0–S3) and, new in this campaign, deterministic
attempt records.

## 3. Approval, acceptance, dispatch and checkpoint

These are four distinct gates and are not interchangeable:

1. **Review token** — `sha256` over the exact source provenance tuple
   (repository, branch, commit, path, blob, sha256). Accepting a revision
   requires the token from that exact discovery.
2. **Acceptance** — durable, one-shot, in the private queue. Acceptance never
   launches a worker.
3. **Dispatch grant / model authorization** — the exact `plan.json` digest. In
   `bridge.py` a live S2 dispatch additionally requires a separate
   `model_authorization` and an experimental-lab risk acknowledgment, both equal
   to the same plan digest.
4. **Checkpoint authorization** — a further exact-plan digest required by
   `workspace.checkpoint`, which is also single-attempt and refuses to retry a
   failed validation.

Deterministic tasks (new) use the same review-token and acceptance gates, and a
plan-digest authorization for `run`. They do not require a model authorization
because they cannot invoke a model.

## 4. Process ownership and termination

- `AppServer` owns exactly one child and one generation, with a single owning
  thread; calls from another thread raise. Stdio writes are bounded by a
  timeout; a timed-out writer sets the session broken rather than retrying.
- Child identity is recorded as `(pid, process_identity)` from
  `process_health.process_claim`, using creation time on Windows and
  boot-id plus start time on Linux. `verify_process` distinguishes `alive`,
  `stopped`, `not-found` and `identity-mismatch`.
- Exit is verified after teardown. An unverified child exit forces the driver
  outcome to `blocked` (`child-exit-not-verified`).
- Saved process claims never authorize killing a PID. `driver.close()` only
  kills the child it created.
- The deterministic runner (new) spawns one process group and terminates the
  whole tree (`taskkill /F /T` on Windows, `killpg` elsewhere) on timeout or
  cancellation, then waits for the exit.

## 5. Restart recovery and uncertain execution

- Codex operations: `sent-unknown`, `acknowledged` and `running` move to
  `needs-reconciliation` when the connection is lost or the generation changes.
  `Operations.reconcile` performs read-only history RPCs and never resends a
  mutation.
- An interrupted queue decision leaves exactly one `unresolved` intent, which
  blocks further decisions until the operator `abandon`s it or the original
  decision is observed to have committed.
- `driver.reconcile_synthetic` is an explicit operator action limited to
  synthetic plans; it refuses uncertain child exits and writes an immutable
  restart receipt so a failed restart cannot implicitly retry.
- Deterministic attempts (new): an attempt fence without a terminal outcome is
  reported as `uncertain`. `recover` closes it as `uncertain` and never
  respawns; it refuses while the recorded child identity is still alive.

**Correction:** there is no automatic restart, resume or replay anywhere. Every
`uncertain` state requires an operator action.

## 6. Worktree and emulator resource coordination

Before this campaign, coordination was entirely convention: a prose
recommendation in the design document plus the operator's private notes. The
only enforced exclusion was the S3 disposable clone, which is per task and
indexes no cross-campaign resource.

The new private registry (`campaigns.py`) adds machine-readable campaigns and
exclusive leases with these properties:

- Registration requires an absolute private worktree locator, branch, provider
  and purpose; the public summary omits the locator and process identity.
- `acquire` refuses a resource held by another campaign **even when the lease
  has expired**. Expiry alone is not evidence the owner stopped.
- `reclaim` requires the lease to have expired, an explicit operator reason and
  a *positively dead* owner (`stopped` or `not-found`). `alive`, `unknown` and
  `identity-mismatch` are refused, and the takeover is recorded durably.
- `reserve` acquires all requested resources or none.
- The registry is a coordination promise between cooperating agents. It is not
  an operating-system sandbox, and it does not prevent a process ignoring it.

Emulator names appear only as opaque resource identifiers (`emulator:rsx-02`).
The registry does not contact, start or inspect an emulator.

## 7. Event journal and Observatory projection

`events.py` defines schema version 1 with an event-type allowlist, bounded
detail trees, strict UTC timestamps and a `visibility` field. `journal.py`
appends LF-committed records under an exclusive lock with non-decreasing
cursors and per-origin monotonic source sequences.

Projections are pure functions over committed records:

- `agents.py` builds `AgentView` objects with the distinct states
  `active-reporting`, `alive-no-new-events`, `approval-needed`, `disconnected`
  and terminal turn states. It never reports "thinking".
- `presentation.py` renders the read-only dashboard, the classic HTML 2.0 legacy
  page and an ASCII `status.txt`.
- `http.py` serves IPv4 loopback only, `GET`/`HEAD` only, with strict `Host` and
  `Origin` checks, no-store caching, `nosniff`, `DENY` framing and a
  `default-src 'none'` CSP. There is no mutation route.
- New: `observer/campaigns.py` and the optional `/campaigns`, `/campaigns.txt`
  and `/api/campaigns` routes project frozen campaign snapshots. They are
  read-only, fail closed when no snapshot is configured, and never dispatch,
  steer or cancel.

**Correction:** the Observatory is not a single service combining emulator and
agent views. The emulator frame registry (`publication.py`) and the agent feed
are separate publications served by the same read-only listener; campaign
projection is a third, newly added, optional publication.

## 8. Usage collection and allowance-aware scheduling

- The Codex ledger (`docs/evidence/codex-usage/`) contains reviewed, sanitized
  historical receipts with a collector. Its fields are Codex-specific.
- The provider-neutral contract (`docs/evidence/agent-usage/README.md`) is
  documentation only. It states plainly that a schema, validator and collector
  are follow-up work.
- There is **no** live quota feed. The design's
  `account/rateLimits/read` investigation remains a candidate, unverified
  against the pinned schema.
- New: `scheduling.py` models *allowance hours*, *tokens*, *context percent* and
  *counts* as separate units with separate scopes and semantics. It refuses to
  total unlike units or unlike semantics, treats a missing or stale allowance as
  ineligible (never zero, never unlimited), and prefers a deterministic worker
  for a task that requires no inference.

## 9. Hard-coded limitations and gates

- `LIVE_BLOCKERS` in `driver.py` names three unverified boundaries (OS
  confinement, inherited configuration/built-in tools, effective Windows
  sandbox/authentication). The `experimental-lab` profile accepts VM-local risk;
  it does not satisfy those blockers.
- `verify_native` pins the Codex executable SHA-256 and `--version` output, and
  `Schema` pins the app-server profile hash. Upgrading either is a review event.
- `bridge.dispatch` refuses live S2 without a model authorization; the driver
  refuses live launch without the experimental-lab profile.
- S3 is limited to Python source, portable tests and Markdown documentation,
  at most 16 modify plus 16 create paths, with `portable-full` or
  `synthetic-unit` validation only.
- Observation windows: 60 s for S0/S2, 300 s for S3.
- No network, MCP server, subagent or shell tool is enabled in generated Codex
  configuration; `sandbox_mode` is `read-only` except S3 `workspace-write`.

## 10. Codex-specific versus already reusable

| Module | Classification |
| --- | --- |
| `protocol.py`, `operations.py`, `synthetic_peer.py`, `telemetry.py` | Codex app-server specific |
| `ledger.py` | Codex-specific semantics; the *state machine* pattern is reusable |
| `driver.py` | Codex launch/policy specific; the plan/fence/outcome discipline is reusable |
| `task_manifest.py`, `task_git.py`, `task_queue.py`, `task_cli.py`, `task_publication.py` | Provider-neutral already |
| `workspace.py`, `editing.py` | Git-portable; validation command set is project specific |
| `procedures.py`, `deterministic.py`, `workers.py`, `campaigns.py`, `scheduling.py` | Provider-neutral, no model dependency |

The reusable part is the *discipline*: strict validated input, immutable frozen
plan, exact-digest authorization, write-ahead fence, terminal or uncertain
outcome, and never replay an uncertain mutation. The app-server protocol itself
is not generalizable and was left untouched.

## 11. The reported Windows owner-termination failure

PR #186 reported an intermittent failure of
`test_owner_termination_leaves_permanent_fence_and_read_only_restart`
(`test_supervisor_driver.py`).

**Cause: a test synchronization defect, not an implementation defect.** The
wait loop read:

~~~python
while monotonic() < deadline and owner.poll() is None:
    ... scan evidence for a durable turn-result ...
    if observed:
        break
    sleep(0.02)
self.assertTrue(observed, "owner never durably observed acknowledgement")
~~~

The loop condition consults the owner's liveness *before* the body runs. A fast
owner — this scenario finishes quickly with a synthetic peer — can exit between
iterations, and the loop then terminates without a final scan. The durable
acknowledgement may already be on disk; the test simply never reads it. Under
full-suite CPU contention the owner is more likely to win that race, which is why
the failure looked timing-dependent and did not reproduce in isolation: eight
consecutive focused runs passed here.

The fix replaces the loop with `await_evidence()`, which scans until the record
appears or a deadline expires and does not consult process liveness at all, plus
a regression test
`test_durable_record_is_observed_after_its_writer_exits` that writes the record
from a short-lived child which exits before the first scan. Assertions were not
weakened: a genuinely missing record still fails after the deadline.

No implementation change was required, and no timeout was increased to mask a
product defect.

## 12. Superseded statements

- "S0/S1 implemented, S2/S3 unverified" — S2 synthetic dispatch and S3 synthetic
  editing are implemented and tested; only *live* S2 and *native* S3 remain
  unproven.
- "S4 parallelism and S5 recovery are proposals" — partially delivered here as a
  library (registry, leases, attempt recovery) without an unattended service.
- "The Observatory observes Codex and emulators" — it can also project
  deterministic attempts, heterogeneous campaigns and explicit unknowns.
- "Freebuff has no integration path" — no adapter exists, but the installed
  client does expose documented API paths and an SDK package; see the
  [integration discovery](freebuff-integration-discovery-20261126.md).

## 13. What remains genuinely unproven

**Revision 2026-11-26 (integrity pass).** The independent review of PR #191
found nineteen defects; `docs/research/execution-integrity-20261126.md` records
each one with its evidence and correction. What changed in this audit's terms:

- A deterministic plan now binds the *content* of the inputs it will read, not
  only the Git revision. Matching HEAD is no longer offered as proof that the
  executed source is the reviewed source.
- Path-like leases are keyed by canonical identity, so two campaign names for
  one worktree collide instead of both obtaining exclusivity.
- Recovery distinguishes an owner from its descendants, and refuses while
  either may still be running.
- The Observatory reads a snapshot assembled from real records by a collector
  that reports unreachable sources and never invents a status.

Still unproven, unchanged in kind: no operating-system confinement boundary, no
network isolation, no unattended service, and no live model dispatch.

- Any live S2 or S3 model dispatch beyond the 2026-11-16 S0 canary.
- Native S3 editing under the Windows sandbox.
- Emulator lease enforcement against a non-cooperating process.
- Any programmatic Freebuff dispatch, event stream or usage feed.
- Exchange rates between allowance hours and tokens; none is assumed here.
- An unattended Supervisor service that survives reboot and resumes a queue.
