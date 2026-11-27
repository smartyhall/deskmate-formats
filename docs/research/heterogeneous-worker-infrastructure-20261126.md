# Heterogeneous worker infrastructure — 2026-11-26

**Campaign:** `freebuff-supervisor-observatory-20261126`
**Branch:** `freebuff/supervisor-and-observatory-infrastructure`
**Base:** `3d3f78471ec8832f944baa4d12102fe1ed508305` (merge of PR #185)
**Direction:** the
[revisit roadmap](https://github.com/smartyhall/deskmate-formats/pull/183)
(PR #183, endorsed by the operator for this assignment; not merged at the time
of writing). Its document was read from the PR branch, not from `main`.

This report describes what was implemented and verified. The
[current-state audit](supervisor-observatory-state-audit-20261126.md) replaces
contradictory descriptions in older planning prose. The
[Freebuff integration discovery](freebuff-integration-discovery-20261126.md)
records the provider investigation separately.

## 1. Summary

The campaign delivered a working no-model execution backend, a capability-based
worker interface, a private campaign registry with exclusive leases, an
allowance-aware selector that keeps measurements separate and honest, and a
read-only campaign projection for the Observatory. The proven Codex protocol,
ledger and gates were not rewritten.

Nothing in this campaign created a model session, contacted a provider,
operated an emulator, dispatched another agent, or published a binary artifact.

## 2. Deterministic execution backend

### 2.1 Reviewed procedures

`src/deskmate_formats/supervisor/procedures.py` is data and validation only. It
never spawns. A procedure is selected by name from a closed registry:

| Procedure | Purpose | Resources | Timeout |
| --- | --- | --- | --- |
| `portable-tests` | Run one reviewed unittest discovery scope (`supervisor`, `observer`, `all`) | `portable-tests` | 1800 s |
| `repository-audit` | Run the existing repository content audit | `source-read` | 600 s |
| `reuse-lint` | Run the SPDX/REUSE declaration check | `source-read` | 600 s |
| `hash-files` | Hash named files, print a structured receipt | `source-read` | 300 s |
| `fixture-compare` | Byte-compare two files, print a structured receipt | `source-read` | 300 s |
| `package-build` | Build a wheel into the attempt artifact directory | `portable-tests` | 900 s |

The executable is always the resolved running interpreter. The argument vector
is assembled from constants plus validated arguments, so a caller cannot supply
an executable, a shell, or a raw argument vector. Repository paths reject
absolute paths, traversal, Windows device names, empty segments, trailing dots,
backslashes and duplicates. Adding a procedure is a code review event, not a
task-authoring right.

### 2.2 Attempt lifecycle

`src/deskmate_formats/supervisor/deterministic.py` owns one attempt directory
containing:

- `plan.json` — immutable: attempt id, campaign, procedure, normalized
  arguments, exact `argv`, interpreter digest, working directory, observed
  source revision, resource declaration, timeout, supervisor implementation
  digests, runtime versions.
- `attempt.json` — the single-use fence, written before the child starts.
- `child.json` — the owned `(pid, process_identity)` claim.
- `progress.jsonl` — bounded start, running and finish samples.
- `stdout.bin`, `stderr.bin` — bounded captured prefixes with size, digest and
  truncation flag.
- `artifacts/` — the only directory a procedure may write, hashed afterwards.
- `outcome.json` — terminal or `uncertain` record, immutable.
- `cancel.json` — optional one-shot cancellation request.

States are `prepared`, `completed`, `failed`, `cancelled`, `timed-out` and
`uncertain`. A nonzero exit is `failed`, never `completed`. A timeout and a
cancellation are distinct states, not generic failures.

Ordering guarantees: the plan digest is the only dispatch authorization; the
attempt fence is written before any process exists; the working-directory
revision and the supervisor implementation digests are re-checked at dispatch;
`outcome.json` is written even when teardown or artifact hashing fails; and a
second dispatch is always refused.

Timeout and cancellation terminate the whole process group (`taskkill /F /T` on
Windows, `killpg` elsewhere) and then wait for exit. Output capture stops storing
after 256 KiB per stream but keeps draining, so a chatty child cannot deadlock on
a full pipe.

Recovery: an attempt fence without a terminal record is reported `uncertain`.
`recover` closes it as `uncertain` with reason `attempt-without-terminal-record`,
never respawns, and refuses while the recorded child identity is still alive.

### 2.3 Trusted intake integration

Task schema version 3 adds a `deterministic` block to the existing versioned
manifest. Intake validates the procedure name, the normalized arguments and the
declared resources, so a malformed deterministic task is rejected at discovery
rather than at dispatch. The queue reports its class as `deterministic-v1`, which
the Codex text-analysis and source-edit paths refuse; a deterministic task cannot
be routed to a model worker.

`deterministic.accepted()` re-reads the existing immutable acceptance and refuses
an unaccepted, superseded, unresolved-blocked, wrong-token or expired revision.
It deliberately repeats those conditions instead of importing the Codex protocol
stack into a no-model backend.

### 2.4 Demonstration

`tools/experimental/heterogeneous_workers_demo.py` registers two campaigns, runs
two different real procedures concurrently in owned attempt directories, leases
each campaign's worktree, then projects the receipts plus an explicitly synthetic
agent campaign through the Observatory renderer and runs two scheduler decisions.
Observed result from the qualification run:

- `hash-files` over `README.md` and `AGENTS.md` completed, exit 0, about 0.43 s.
- `fixture-compare` over `pyproject.toml` against itself completed, exit 0, about
  0.44 s, reporting `same: true`.
- Both campaigns reported `Activity: measured` from attempt receipts.
- The synthetic agent campaign reported `allowance_remaining_hours = unknown` and
  `thread_input_tokens = unknown`, with a known context value, exactly as
  intended.
- The deterministic task selected `deterministic-local`; the inference task
  selected nothing because its allowance was unknown.

## 3. Worker abstraction

`src/deskmate_formats/supervisor/workers.py` defines a capability vocabulary
(`prepare`, `dispatch`, `progress`, `cancellation`, `recovery`, `artifacts`,
`session`, `continuation`, `steering`, `usage`) and three descriptors:

| Worker | Advertised capabilities | Status |
| --- | --- | --- |
| `deterministic` | prepare, dispatch, progress, cancellation, recovery, artifacts | Real execution |
| `codex` | prepare, dispatch, progress, cancellation, recovery, session, continuation, steering | Protocol implemented; live dispatch gated. `health()` reports `unavailable` with the actual blockers |
| `freebuff` | none | No verified programmatic interface; every operation raises |

`require()` raises on an unsupported capability, so a caller cannot silently
assume parity. Capability is separated from availability: the Codex worker
advertises `steering` because the protocol implements it, while `health()`
reports the gates that currently forbid a live turn.

`SyntheticWorker` is a scripted double for multi-worker tests and demonstrations.

## 4. Campaign ownership and leases

`campaigns.py` is a private, operator-owned registry outside Git. It stores
campaigns and exclusive leases in one JSON document guarded by the existing
private-storage lock, with bounded size and record counts.

- Resources use `kind:name` identifiers (`worktree:audit-worker`,
  `emulator:rsx-02`, `socket:86box-01`, `account:codex`). Names are opaque; the
  registry never contacts an emulator or a provider.
- `acquire` refuses a resource held by another campaign even when the lease has
  expired.
- `reserve` acquires all resources or none.
- `reclaim` requires an expired lease, an explicit operator reason, and a
  positive `stopped` or `not-found` process result. `alive`, `unknown` and
  `identity-mismatch` are refused. Every takeover is recorded with the previous
  campaign, the reason and the observed owner state.
- `summarize`/`export` produce a public-safe view with no worktree locators, PIDs
  or process identities.

The registry documents itself as a coordination promise between cooperating
agents, not an OS sandbox. It does not prevent a process that ignores it, and it
does not read or write guest state.

## 5. Allowance-aware scheduling

`scheduling.py` models four things that must not be conflated:

| Measurement | Typical unit | Scope | Semantics |
| --- | --- | --- | --- |
| Account allowance | hours | account | remaining or consumed |
| Current context | percent or tokens | thread | current |
| Cumulative thread usage | tokens | thread | cumulative |
| Per-task inference | tokens or turns | campaign | incremental |

`Measurement.unknown()` records absence explicitly: the value is `None`, the
source is `unavailable`, and `known` is false. `total()` refuses to sum unlike
units and unlike scopes or semantics. Cached input and reasoning output are
subsets, and the module never adds them again.

`select()` filters on capability, health, resource kinds and inference mode,
then requires a fresh known allowance for an inference worker. An unknown or
stale allowance makes that worker ineligible; it never makes it look free. A
task that requires no inference selects a deterministic worker even when an
inference worker is available, and records the unneeded allowance as unknown.

## 6. Observatory extension

`src/deskmate_formats/observer/campaigns.py` is a pure projection over a frozen
snapshot. It reports, per campaign: identity, owner, provider and worker kind,
status, branch, base commit, milestone, checkpoint, tasks with state and
`state_basis`, structured results, resources with staleness, pending approvals,
blockers, measurements with source and freshness, evidence references, and an
activity block whose `basis` is `measured` only when a receipt timestamp exists.

It never infers progress from elapsed time. Rendering cannot dispatch, steer,
cancel, touch an emulator or mutate a file; the module exposes no mutation API.

The Observer listener gains three optional read-only routes — `/campaigns`,
`/campaigns.txt` and `/api/campaigns` — served only when a snapshot path is
configured. Without one they return 404, preserving prior behaviour exactly. An
unreadable snapshot returns 503 rather than a partial page. The existing classic
HTML 2.0 and ASCII views are untouched, and the new text view is ASCII-only by
construction.

## 7. External task submission and result retrieval

The intended ChatGPT-to-lab bridge reuses the trusted Git intake:

1. A reviewed task manifest is committed under `ops/tasks/<id>.json` on the
   trusted branch, with the procedure name, typed arguments and declared
   resources.
2. The operator discovers it from the pinned branch tip and accepts the exact
   revision through the private queue. Acceptance is the authorization; the
   manifest itself is data, never a command.
3. `deskmate-supervisor-deterministic prepare-task` re-verifies acceptance and
   freezes a plan whose digest is printed.
4. `run --authorization <digest>` executes once, inside an owned worktree, with
   bounded capture, artifact hashes and a terminal or `uncertain` outcome.
5. The frozen snapshot and rendering make the structured result readable through
   the read-only Observatory; the receipt and artifacts can be reviewed and, if
   eligible, committed on a review branch for ChatGPT to inspect through its
   repository access.

Steps 1–4 were exercised end-to-end with a real procedure in the trusted-intake
regression test. Step 5 was exercised with synthetic receipts through the demo.
What has **not** happened is a submission authored by ChatGPT itself and an
acceptance by an independent operator: that requires an actual independently
approved submission, which this campaign cannot manufacture. No remote execution
endpoint was created.

## 8. The reported Windows owner-termination failure

Analysed in the [audit](supervisor-observatory-state-audit-20261126.md#11-the-reported-windows-owner-termination-failure).
It was a test synchronization defect: the wait loop stopped as soon as the owner
process exited and therefore skipped its final evidence scan. The loop now waits
on the durable record alone, and a deterministic regression test covers an owner
that exits before the first scan. No product defect was found and no assertion
was weakened.

## 9. Non-goals and explicit non-actions

- No model session, provider credential, paid call or additional agent.
- No emulator launch, guest mutation or socket connection.
- No change to `main`, no force-push, no merge, no published deployment.
- No new third-party dependency.
- No relaxation of `LIVE_BLOCKERS`, `NATIVE_SHA256`, the schema profile pin or
  the S2/S3 authorization gates.
- No published screenshot: see §11.

## 10. Verification

Host: Windows 10, CPython 3.13.17, Git Bash. During the final runs another
campaign's portable suite, two loopback preview servers and a Ghidra import were
also using the same machine, which is relevant to the timing history below.

| Check | Result |
| --- | --- |
| Supervisor suite, full (`test_supervisor*.py`) | **167 tests, OK**, 995.7 s |
| Observer HTTP listener | 15 tests OK, including three new campaign-route tests |
| Observer campaign projection | 5 tests OK |
| Deterministic backend | 13 tests OK |
| Deterministic trusted intake | 7 tests OK |
| Procedures / workers / campaigns / scheduling | 5 / 6 / 7 / 10 tests OK |
| Windows backend | 4 tests OK |
| `ruff check src tests/portable tools` | clean |
| `reuse lint` | 1858 / 1858 files compliant |
| `tools/audit_repository.py` | passed, 3716 source files |
| wheel build and `tools/install_wheel.py` | succeeded |

### The earlier two-failure run

A full run before these fixes (166 tests, 1194.9 s) reported one error and one
failure, both in `test_supervisor_editing.py`, a module this campaign otherwise
did not modify:

- `ERROR` in `setUp`: a local `git commit` exceeded the fixture's fixed
  10-second `subprocess` timeout.
- `FAIL`: the synthetic S3 turn missed an observation window the test itself
  set to 2 s timeout and 4 s deadline, producing `blocked` with
  `worker incomplete; changes retained`.

Under the same load that module passed 12/12 in isolation (282 s). Both
numbers are hang guards inside portable test code, not assertions about the
product, and neither failure implicates `editing.py`. Both were widened —
10 s to 60 s, and 2 s/4 s to 10 s/30 s — with comments stating that the guard
exists to catch a hang rather than to measure latency. No assertion was
weakened, no product timeout changed, and no failure was relabelled flaky. The
subsequent full run was green.

The observer suite (80 tests) also reported one error in a module this campaign
did not modify: `test_observer_codex_http.py` exceeded a 10-second guard while
spawning a fixture writer, during a period when another campaign was running the
entire portable suite and a wheel build. That module passes 3/3 alone in 3.8 s.
Those fixture-spawn guards were left untouched: they belong to an unmodified
surface, and widening five guard sites across three observer test modules would
be a separate, reviewable change rather than a silent part of this one. It is
recorded as a follow-up.

## 11. Limitations

- The backend provides cooperating-owner custody, not an operating system
  sandbox. A host kill cannot prove a descendant caused no external effect.
- Captured output is a bounded prefix; the rest is drained and discarded. Only
  the artifact directory is hashed.
- `portable-tests` and `package-build` were validated for argument selection and
  for short-run behaviour, not for a full multi-minute build.
- The registry lock is a single-writer lock with bounded retry by callers; it is
  not a distributed consensus mechanism.
- There is still no unattended service: no queue loop, no automatic dispatch, no
  reboot recovery, no scheduler daemon.
- Observatory campaign projection is only as fresh as the frozen snapshot; it
  does not read private attempt directories at request time.
- The Freebuff adapter remains a declared absence.

## 12. Visual exemplars

The Observatory campaign page is reproducible with
`python tools/experimental/heterogeneous_workers_demo.py`, which writes
`campaigns.html` and `campaigns-view.json` beside the attempt receipts. No image
was captured or published in this campaign: publishing site imagery requires a
manifest entry, hashes and provenance review against the standing
documentary-image rules, and the page is a generated research interface rather
than a DeskMate observation. Stating that plainly is better than an unreviewed
binary in Git. A future batch can add a reviewed exemplar if the page becomes
part of the published reference.

## 13. Proposed follow-ups

1. **Freebuff `models` probe.** The single authorized read-only request described
   in the [discovery note](freebuff-integration-discovery-20261126.md#7-proposed-qualification-procedure-not-executed).
   Requires operator authorization and an explicit data-boundary decision.
2. **Provider-neutral receipt validator.** Turn the
   [agent usage contract](../evidence/agent-usage/README.md) into a versioned
   schema plus a deterministic validator and synthetic fixtures. No provider
   access is needed.
3. **Observatory snapshot writer as a CLI.** Today the demo builds the snapshot;
   a `deskmate-observer-campaigns collect` step should assemble it from the
   registry, attempt outcomes and agent journal under one bounded command.
4. **Live S2/S3 qualification.** Still gated. The deterministic backend removes
   infrastructure work from the model allowance, which makes this cheaper but no
   less authorized.
5. **Lease enforcement for a non-cooperating process.** Document and test what
   the registry can and cannot prevent; consider an OS-level lock only if a real
   conflict occurs.
6. **Consistent fixture-spawn guards.** Several portable test modules spawn a
   Python fixture child under a fixed 10-second `subprocess` timeout. Under a
   saturated host those guards fire and look like defects. Widen them in one
   reviewed sweep, with the same hang-guard rationale used here.
7. **Unattended service.** Only after a reviewed design: queue loop, restart
   recovery, explicit stop control and an operator-visible kill switch.
