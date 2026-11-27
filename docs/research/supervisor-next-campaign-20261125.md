# Supervisor revisit: heterogeneous workers and deterministic execution

**Planning direction, 2026-11-25 (operator discussion).** Prioritize revisiting
the Supervisor as the next major infrastructure campaign rather than leaving
it behind the native-format backlog. Freebuff's preliminary investigations and
independent review are encouraging; substantial sustainable free access and
autonomous implementation still need qualification. Do not interrupt the
website navigation campaign or abandon active native-format research to
implement this entire roadmap at once.

This supplements the [existing Supervisor design](codex-supervisor-design.md),
[Observatory specification](observatory-v2-spec.md), and
[long-term preservation roadmap](../preservation-roadmap.md). It is not
authorization for a live model call, unattended dispatch, an external control
endpoint, or emulator operation.


## Integration checkpoint — 2026-11-27

The numbered implementation sequence below preserves the November 25 planning
record. The first implementation is now submitted in [PR #191](https://github.com/smartyhall/deskmate-formats/pull/191): the worker reports a deterministic procedure registry, version-3 trusted task intake, separate prepare/run/recovery gates, a heterogeneous worker descriptor, campaign leases, allowance-aware selection, and read-only Observatory projections. These are candidate capabilities pending independent integration; do not treat a branch or passing CI as proof of live operation. Freebuff remains a manual worker, not a qualified automatic adapter.

The next bounded infrastructure steps are campaign-specific Python environment
isolation and import identity ([#201](https://github.com/smartyhall/deskmate-formats/issues/201)), integration of the current stack, and a single harmless trusted-Git deterministic hash task with independently checked result return ([#204](https://github.com/smartyhall/deskmate-formats/issues/204)). The performance work ([#199](https://github.com/smartyhall/deskmate-formats/pull/199), [#147](https://github.com/smartyhall/deskmate-formats/issues/147)) needs an integrated quiet-host baseline before optimization; it need not block a separately qualified hash canary. No unattended dispatch or model authorization is implied.

## Motivation and initial state

The previous development trade-off was that engineering the Supervisor
consumed the same limited Codex allowance needed for DeskMate research.
A supplementary coding agent could make infrastructure investment practical
without exhausting that allowance. Another major opportunity is to eliminate
inference from tasks that already have deterministic implementations.

ChatGPT's authenticated GitHub connector can manipulate repository objects,
PRs, CI and artifacts but its ordinary code-execution environment cannot
currently perform the normal networked Git clone/build/test workflow.
Codex and Freebuff in the lab have access to an actual development checkout.
A deterministic execution backend would bridge some of this gap without
requiring an additional agent turn. Direct submission from ChatGPT to the
lab is not presently demonstrated; the trusted Git intake and a privately
operated local spool are candidate paths, not new grants.

Begin by reconciling the actual repository and test state, not by trusting
dated planning prose. The [project status](../../PROJECT_STATUS.md) records
a passed owned real S0 single-turn canary, S1 trusted Git intake/manual
decisions, S2 synthetic and separately gated live paths, and S3 bounded
editing work with unverified native editing. It contains historical status
snapshots as well as later results, including a first live S2 analysis
report. Audit actual current implementations, receipts and remaining gates
before claiming live coverage or resuming a milestone. Retain all existing
authorization, ownership, and no-ambiguous-replay guarantees.

## Target architecture

Keep a single durable coordinator for task identity, priority, dependencies,
reviewed task revision, authority, checkpoints, ownership and recovery.
Worker adapters describe capabilities rather than pretending different
providers have identical protocols or meters:

| Worker | Initial purpose | Qualification |
| --- | --- | --- |
| Deterministic task runner | Builds, tests, link audits, hashing, fixture comparisons, established archive/index procedures, receipts | New bounded local backend; no model inference required |
| Codex | Complex research and development, existing app-server integration | Preserve pinned S0 protocol, S1 intake and S2/S3 gates |
| Freebuff | Supplementary research, implementation, independent review | Manual local evaluation first; discover and verify supported developer interfaces before an adapter |

All workers report a shared campaign/attempt identity and normalized
lifecycle, outcomes, evidence locators/hashes and limitations. Preserve
provider-specific raw records privately. Observatory projections remain
read-only; browser viewers must not control agents or emulators. A single
assigned owner controls each emulator instance, automation socket, writable
image or mutable research resource. Use isolated writing worktrees and
campaign-specific derived outputs; a Git worktree is not a security boundary.
Ordinary project reads should generally be unrestricted except explicitly
blinded experiments, consistent with the operator's revised governance
direction; credential access, unrelated personal data, mutation, external
transfer and publication are separate matters.

## Early deterministic backend

Prefer an independently useful first implementation over a comprehensive
new service. Reuse the existing task identity/decision ledger and approved
Git intake where practical. Define a versioned task kind for named, locally
reviewed procedures with typed validated arguments, exact source revision,
owned worktree, executable/argv, resource reservations, timeout and result
contract. No arbitrary untrusted shell commands, implicit execution of a PR
comment, or substitution of a downloaded script for an approved procedure.
Separate authorization for consequential tasks and live native operation.

Start with a harmless portable test or build in a disposable/owned checkout.
Capture start/end times, process exit status, bounded stdout/stderr, artifact
hashes, actual command/configuration and Git status before/after; retain
larger/raw output privately. Distinguish timeout, cancellation, child-process
failure, success and uncertain completion. Test invalid paths/arguments,
missing dependencies, nonzero exits, interruption, duplicate task IDs and
restart recovery using synthetic jobs first. Reconcile uncertain mutations
instead of blindly replaying them. Do not start with a public network shell
or a comprehensive sandbox project; apply the accepted recoverable-lab
posture while verifying concrete external exposure.

An eventual externally submitted job must enter the same reviewed/authorized
queue and return a structured result through an approved mechanism, e.g.
sanitized Git receipts or eligible CI artifacts. An authenticated GitHub
connector could submit a reviewed manifest without direct network access to
the VM. Prove the complete harmless end-to-end path before offering broader
procedures; no external remote execution currently exists in this chat.

## Freebuff usage observation: desktop context tooltip

Source: operator-supplied screenshot captured during the follow-up independent
PR review on the local desktop client, evening 2026-11-25 (VM clock had
advanced to November 26). Values below are direct UI readings, rounded as
displayed, not exact token counters or measured charges. The raw screenshot
contains lab/session details and is not published. The selector displayed
`Powerful High`; the actual provider/model identity for this snapshot is
not independently verified. Earlier model selections must not be assumed
to identify every call in a multi-turn thread.

| Display label | Displayed value | Interpretation |
| --- | --- | --- |
| Context | 170k / 1.0m; 16% | Current context vs displayed capacity |
| Compacts at | 300k | Displayed compaction threshold, not context maximum |
| Thread usage | 4.8m | Cumulative provider-reported usage in current thread transcript |
| Input | 4.7m | Includes cached input |
| Cached input (included) | 4.4m | Subset of input, not additional tokens |
| Output | 90k | Includes reasoning output |
| Reasoning output (included) | 50k | Subset of output, not additional tokens |
| Compactions | 1 | Count displayed for thread |
| Latest | cache expiry · 143k | Exact label; size semantics not independently verified |
| Daily hours | 30:00 | UI meter observation; charge/reset semantics unverified |

Approximately 94% of displayed cumulative input was cached (4.4m/4.7m).
The displayed output includes approximately 56% reasoning tokens. These
ratios use rounded quantities. Do not sum cache/reasoning subsets into total
usage; do not derive billing or allowance consumption from token totals.
The daily-hours display is not proof of free/unlimited use, a specific
reset time, or that this work consumed zero allowance. A reset may have
occurred, and model/routing/plan eligibility and accounting units are unknown.
Record the context percentage as displayed; do not force it to agree with
a ratio of rounded context values. Thread totals may span more than one
campaign or model and must not be assigned wholesale to one task.

The agent initially reported no model/quota introspection tool. That is
compatible with the operator finding richer telemetry in the desktop UI.
This screenshot establishes a practical manual receipt source, not a
programmatic API or validated allowance feed. Take manual start/checkpoint/
completion observations when available without extra inference; use
differences only between comparable observations of the same scope and
note reset, compaction and model changes. Preserve display labels, units,
scope, precision, observation time, source type and unknowns. Keep private
account identifiers, raw transcript and exact local paths out of Git.

## Revised implementation sequence

1. **State audit.** Pin main, inventory S0-S3 code, tests, actual successful
   and failed live receipts, open gates, Observatory and usage collectors.
   Identify the smallest meaningful next canary and what is already reusable.
2. **Deterministic runner.** Deliver a bounded no-model job in the existing
   Windows lab, with portable synthetic tests and independently reviewed
   receipts. Prefer direct utility now over waiting for agent adapters.
3. **Shared worker interface.** Generalize lifecycle, capability discovery,
   resource ownership, attempts, checkpointing and result contracts
   incrementally around existing Codex behavior; keep provider-specific
   protocol logic behind adapters and preserve regression coverage.
4. **Freebuff integration research.** Inspect installed version and supported
   Developer API, CLI or other documented interfaces. Verify session creation,
   dispatch, status/events, cancellation, continuation, workspace assignment,
   model settings and available usage fields. Distinguish documented, source-
   verified, actually exercised and unavailable capabilities. Start with
   read-only discovery; no new credentials, paid calls or live dispatch
   implied. Manual Freebuff operation need not wait for an adapter.
5. **Observatory and registry.** Normalize deterministic and agent events
   with campaign attribution; retain native units and source freshness.
   Add private machine-readable ownership records and leases where needed.
6. **Allowance-aware scheduling.** Distinguish account allowance from worker
   token totals and current context. Select by demonstrated capabilities,
   availability, priority, authority and resource ownership; use deterministic
   procedures when sufficient. Observe reset boundaries and unknown/stale
   meter values; do not automatically purchase credits, redeem resets or
   retry model turns merely to check availability. Calibrate on comparable
   tasks, not a presumed exchange rate between tokens and hours.
7. **External submission.** Qualify a supported, bounded, reviewed task intake
   and result path accessible through the existing GitHub workflow; prove
   harmless deterministic end-to-end operation before broader orchestration.

Phases may proceed in parallel where independent. Continue Freebuff's website
implementation evaluation without waiting for infrastructure. Consider the
next Codex campaign for the state audit and deterministic interface while
Freebuff works on the website; allocate further work according to measured
capabilities and actual available allowance. Revisit the existing orchestrator
reuse ADR rather than automatically importing a new framework.

## Handoff and non-goals

The first campaign should produce an accurate current capability matrix,
a minimal implementation plan, the first independently reviewable no-model
job if feasible, test/evidence receipts, and concrete follow-up tasks.
Do not claim the API exists or the allowance is durable merely because
the desktop exposes a settings screen or meter. The neutral usage receipt
schema/validator and private campaign registry are compatible follow-up
work under the proposed multi-agent governance (PR #181). Existing
[Codex usage receipts](../evidence/codex-usage/README.md) remain intact.
No code, live backend, provider credential, or deployment is changed by
this planning note.
