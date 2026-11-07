# ADR — Agent orchestrator reuse for Supervisor S2–S5

**Decision.** Build a small S2 coordinator in DeskMate Formats on the existing
S0 and S1 boundaries. Use upstream implementations for bounded algorithms,
protocol examples and test cases. Advance S2 only after review of this ADR
and the separately authorized real S0 smoke test in
[issue 58](https://github.com/smartyhall/deskmate-formats/issues/58).

## Requirements baseline

The [independent inventory](agent-orchestrator-requirements.md) was committed
before external source inspection. The decisive requirements are separate
observer, dispatch, approval and native-control authorities, write-ahead
operation identity with no replay after uncertain send, exact-revision
operator review, an additional dispatch grant, exclusive custody of held
guests, private evidence and a native Windows 10 operating path. The
desirable features are a small owned worker, follow-up queue and deliberate
steering in S2, audited checkpoint publication in S3, isolated parallel
workers in S4 and service/restart recovery in S5.

## Source and version inventory

Source inspection used shallow default-branch Git clones
(`git clone --depth 1 https://github.com/<owner>/<repo>.git`), verified with
`git rev-parse HEAD`. Snapshot dates describe the inspected head commits.
They give limited maintenance signals. CI configuration and source tests
indicate intended coverage, without establishing successful runs, a support
commitment or maintenance cadence. See the linked evidence notes for pinned
code, specs, tests and deployment sources.

| Snapshot | License and main footprint | Maintenance signal |
| --- | --- | --- |
| [Symphony](https://github.com/openai/symphony/tree/be10a1b79df723d6d7612b5651c8522704dafb2e) `be10a1b79df723d6d7612b5651c8522704dafb2e` | [Apache-2.0](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/LICENSE) with NOTICE. Elixir/OTP, Bash, Codex, tracker, optional Phoenix HTTP/SSH. | 2026-09-15 head adds main-push nightlies. Linux/macOS build matrix. |
| [Command Center](https://github.com/cgeene/commandcenter/tree/85f39956976ceb03aec668bd5955e5304ddd5dae) `85f39956976ceb03aec668bd5955e5304ddd5dae` | [MIT](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/LICENSE). Node 22+, SQLite native addon, tmux/node-pty, agent CLI, Git and gh for PRs. | 2026-07-29 head is a merged PR. Source tests cover scheduler and daemon. Native Windows support and ongoing release cadence are unclear. |
| [Codex Monitor](https://github.com/Dimillian/CodexMonitor/tree/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5) `dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5` | [MIT](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/LICENSE). Rust/Tauri and React/Node for desktop, standalone Rust daemon option, Codex, Git. | 2026-03-26 head is a tray UI change. Windows CI and installer workflow exist. Current support cadence remains unverified. |
| [Gas Town](https://github.com/gastownhall/gastown/tree/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476) `466aa41c83ee73b1fa0eb79eb9d172fb1eca9476` | [MIT](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/LICENSE). Go, Git, Beads, Dolt, tmux and agent CLI for full orchestration. | 2026-10-28 head updates dependencies and Go. Windows build/vet smoke workflow covers the CLI toolchain. |

License file SHA-256, computed on Git blob bytes from `git show HEAD:LICENSE`
in each pinned checkout using Python `subprocess.check_output` and
`hashlib.sha256`, in inventory order:

| Project | License blob SHA-256 |
| --- | --- |
| Symphony | `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4` |
| Command Center | `b84b8f62e77553c485ba0a4aace64c2540545974f35b71e72441eeefa187b26e` |
| Codex Monitor | `df17aae89ce4705d0a6e5f7b46eeea3b9023967ecad948f8779b47039eb55a8b` |
| Gas Town | `6141d15e761ef772bdd45fdd4036dfc1f97488011429e6643e1445afa9d22f4d` |

No source from these projects is incorporated by this ADR. Their top-level
licenses leave room for bounded software reuse under the project's GPLv3
option, subject to preserving upstream terms and notices. A later import
needs a file/dependency-specific review, accurate sidecars, the Apache NOTICE
where applicable and independent consideration of any documentation
dual-license grant. No incompatible top-level license was identified in
these four snapshots. Transitive and file-specific rights were outside
this source survey. See [repository licensing policy](../../LICENSING.md)
and [existing Apache-derived S0 provenance](codex-supervisor-s0.md).

## Capability comparison

Evidence and limitations are detailed in the
[Symphony and Command Center notes](agent-orchestrator-symphony-command-center.md)
and [Codex Monitor and Gas Town notes](agent-orchestrator-monitor-gas-town.md).
A gap denotes a missing guarantee in the inspected paths.

| Capability | Symphony | Command Center | Codex Monitor | Gas Town |
| --- | --- | --- | --- | --- |
| Scheduling and task identity | Poll, label/state/capacity checks, current issue by ID | SQLite queue, row claim, budgets and dependencies | Per-thread composer queue in UI memory | Bead IDs, dispatch and assignee locks, persistent hooks |
| Exact reviewed Git input and separate dispatch grant | Gap | Gap | Gap | Gap |
| Owned Codex transport | Owned stdio thread per worker attempt, sequential turns | tmux CLI and provider session resume | Owned stdio, start/resume/read, steer with expected ID | Managed CLI and resume preset |
| S0 version/schema compatibility | Handshake implemented, lab pin unverified | Different CLI interface | Experimental API enabled, lab pin unverified | Different CLI interface |
| Lost acknowledgement and restart | Retry/backoff, refetch active work after restart | Pane/row reconciliation and queued delivery recovery, possible duplicate submit | Volatile request IDs, failed steer can queue, no durable receipt | Persistent assignment and bounded redispatch, no turn receipt |
| Approval and security posture | Policy-dependent blocking or auto-approval, tracker tools and shell hooks | Pane guards and provider policies, manual terminal input | Workspace/request routing, remembered rules, shared-token control daemon | Codex preset bypasses approvals and sandbox |
| Git isolation and publication | Per-issue directory and hooks, workflow delegates commits/PRs | Task worktrees, detached review snapshot, PR state helpers | Operator worktrees and Git actions | Polecat worktrees, automatic WIP checkpoints and merge machinery |
| Parallel resource ownership | In-process claims and host capacity | Worker claims, pane checks, serial/capacity policy | Session routing | Work locks and worker lifecycle lease |
| Held native emulator fencing | Gap | Gap | Gap | Gap |
| Browser and authority | State/LiveView plus POST scheduler refresh | Status and writable terminal/API | App/remote event display and control, no qualifying read-only browser surface | Dashboard includes command and issue mutations |
| Usage/activity signals | [Codex tokens, activity and limits](https://github.com/openai/symphony/blob/be10a1b79df723d6d7612b5651c8522704dafb2e/elixir/lib/symphony_elixir/orchestrator.ex) | [token estimates](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/db/tokens.ts) and [provider usage poll](https://github.com/cgeene/commandcenter/blob/85f39956976ceb03aec668bd5955e5304ddd5dae/src/daemon/usagelive.ts) | [rate limits](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/src/features/threads/hooks/useThreadRateLimits.ts) and [tray session usage](https://github.com/Dimillian/CodexMonitor/blob/dd61b9abd37de5ded86e82b9fe8a83fd49d46fa5/src/features/app/hooks/useTraySessionUsage.ts) | [role/subprocess telemetry](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/telemetry/telemetry.go) and [cost reporting](https://github.com/gastownhall/gastown/blob/466aa41c83ee73b1fa0eb79eb9d172fb1eca9476/internal/cmd/costs.go) |
| Native Windows 10 burden | High, Bash launch/hooks and no Windows release target | High, tmux and POSIX process/terminal tooling | Native build path, substantial stack, lab unverified | CLI build path, WSL/Linux expected for full stack |

## Failure cases and required lab behavior

The two complete upstream traces, including test references, are in the
[Symphony and Command Center notes](agent-orchestrator-symphony-command-center.md).
Command Center uses a terminal submission as the closest analogue to a
mutating RPC. Codex Monitor provides a second direct app-server comparison.
These are source-path conclusions with conditional outcomes, without
runtime fault injection.

| Case | Upstream behavior in the inspected paths | Proposed lab behavior | Unresolved evidence |
| --- | --- | --- | --- |
| A. Server acts, acknowledgement disappears | Symphony sends then waits. A failed attempt can retry, and restart refetches the active issue with empty claims and starts a new thread. Command Center can resend a queued terminal submission if the daemon died after Enter but before clearing the row. Codex Monitor can enqueue a failed steer while still processing, including after a transport error with unknown outcome. None of these paths ties the ambiguous mutation to a durable authoritative operation identity. | Record the stable identity and mark sent-unknown before the write. Halt dependent sends and preserve the receipt. Reconcile only with saved acknowledgements or exact thread/turn evidence. Keep an unacknowledged start unresolved if its outcome cannot be identified. Never convert an uncertain steer into a fresh turn. | What exact history is available after Windows process or connection loss? What survives a lost reply versus an acknowledged turn? |
| B. Restart while an emulator is held | Symphony sweeps terminal workspaces and may run cleanup hooks. Active retries can run hooks again. Command Center can respawn a vanished or abandoned worker into the same worktree/session and documents the unrecorded-pane gap. Neither tracks held native ownership. A guest effect would depend on how a lab integration coupled credentials, files or process lifetime to the worker. | Keep guest custody and files outside worker teardown and worktree cleanup. Preserve an exclusive claim and block reassignment, including after lease expiry, until verified operator reconciliation. Preserve identity, hold counters and private evidence, with no reset, resume, media change or new controller. | Can Windows process-tree boundaries preserve a held clone while identifying and fencing a stale controller? Validate counters and ownership on a disposable guest in a later authorized test. |
| C. Task edited or delivered twice | Symphony re-fetches the current tracker issue and renders the current workflow. Its in-memory claim deduplicates by issue, without freezing input. Command Center creates task rows independently, claims each ID and reads the current prompt at spawn. In both systems, text from permitted task writers can become agent instructions under the configured workflow. | Use the immutable S1 receipt, verified Git provenance and separately scoped dispatch grant. Bind the exact accepted revision, content digest and operation intent. Reject stale, superseded or conflicting intents. Repeated intake or dispatch grants must not create another wire send. Keep untrusted text outside authorization and privileged configuration. | Exercise branch movement, duplicate grant delivery and crash between grant consumption and the S0 send gate. Establish which persisted record governs each restart boundary. |

## Subsystem decisions

Complexity is qualitative and includes adapting, testing and maintaining
the component on Windows. The names below describe the unit of reuse.

| Subsystem | Decision | Complexity and reason |
| --- | --- | --- |
| Trusted intake and acceptance | **Reuse as-is** | Low. Read the existing S1 receipts. Keep its trust checks, manual acceptance and queue history intact. |
| Dispatch authorization and scheduling | **Retain our own implementation** | Medium. One worker and one explicit local dispatch grant make a small S2. An imported scheduler would still need all the trust, uncertainty and lease gates plus a foreign runtime. |
| Owned protocol and mutation receipt | **Reuse as-is** | Low for the offline S0 primitives. Real process identity and protocol evidence remain gates. Do not substitute transport correlation for operation identity. |
| Follow-up selection and exact-ID steering | **Adapt a bounded component** | Low to medium. Use Codex Monitor's one-item-per-thread selection and exact-turn request pattern through S0. Replace volatile/fallback behavior with durable intent and reconcile before any dependent send. A small Python adaptation can avoid a React/Rust dependency. |
| Approval authorization and delivery | **Retain our own implementation** | Medium. Reuse S0's scope model and add a separately authorized response path only once its race and generation handling are verified. No imported auto-approval, remembered rules or terminal-input proxy. |
| Worktree lifecycle | **Adapt a bounded component** | Medium. Use Command Center's distinct worker and detached reviewer patterns and Gas Town's structural-vs-transient probe distinction. Pin exact base SHA, record branch/path identity, verify existing ownership and remove implicit fallback and force-reuse. |
| Checkpoint and draft PR publication | **Adapt a bounded component** | Medium. Use Command Center's snapshot/PR lookup patterns and narrow Git/GitHub CLI calls. Keep staging allowlist, barrier, audit and commit/remote/PR receipts local. Look up exact target branch and PR before retrying an ambiguous remote result. Keep PR draft and merging under operator control. |
| Exclusive resource leases | **Retain our own implementation** | High. Gas Town's locks and lifecycle are useful examples for worker admission. Native credential custody and recovery need durable fencing even when a worker, parent or time-based lease disappears. |
| Service restart reconciliation | **Retain our own implementation** | High. Bring S0 receipts, process identity, worktree receipts and resource custody into explicit recovery. Treat uncertain evidence as a dispatch stop. Learn from Command Center's caution about unreliable probes without inheriting retry-on-loss. |
| Browser publication | **Reuse as-is** | Low. Extend sanitized events via the Observatory journal and immutable HTTP projection. Keep tokens, prompts, private paths and native captures out of browser telemetry. |
| Scheduling diagnostics and usage | **Learn from the implementation** | Low. Use Symphony's separate blocked/running/retry and last-activity indicators and Command Center's distinction between estimated and provider-reported usage. Publish approved metadata with provenance. |
| Deployment and process launching | **Learn from the implementation** | Medium. Use Codex Monitor's Windows executable/shim cases for launch tests. Validate native executable selection and owned child trees in the existing Python/Windows stack. |

**Symphony as a foundation.** Its owned app-server runner, revalidation,
workspace safety and scheduler/worker separation are good reference designs.
Its tracker-driven recovery deliberately accepts repeated work, live issue
and workflow inputs bypass the S1 review model, and its local shell and
HTTP control patterns would need replacement. Incorporating S0/S1 would
require replacing authority, dispatch and recovery internals while adding
Elixir/OTP and qualifying Bash-dependent behavior on Windows. Use the
scheduler and tests as design references. Keep the S2 control loop small.
None of the four projects exposed a concrete missing capability that
justifies adding OpenHands or Agetor to this assessment.

## Sequence and experiment

1. **S2** — After the review and live S0 gate, add one local coordinator with
   an explicit per-intent dispatch grant, an owned thread, and durable
   follow-ups. Enable steering only for a matching active turn. A stop on
   unknown outcome is part of the first S2 change. Start with no privileged
   emulator resources and no production approval sender.
2. **S3** — Put publication on its own state machine. Record exact worktree,
   expected parent and staged hashes. Test a failed push, an acknowledged
   local commit, and a lost PR-create response against disposable Git
   fixtures. A source checkpoint must never release guest custody.
3. **S4** — Add bounded concurrency for synthetic worktrees first. Assign
   worktree and native resources independently. Prove that a second worker
   cannot claim a synthetic held resource through stale lease recovery.
4. **S5** — Qualify native Windows service/process identity, startup with
   outstanding receipts, operator stop/reconcile, and durable state
   preservation across restart. Add a live guest only after separately
   authorized Windows acceptance. Keep the appliance roadmap deferred.

The smallest next integration spike is the real S0 gate on Windows 10. In a
future authorized run, use a disposable scratch workspace and a single
supervisor-owned pinned Codex app-server. Submit one bounded harmless turn
with sandbox intact, no emulator resources, no remote publication and no
approval escalation. Record the launcher/build hash, Windows build,
protocol schema, process identity, generation and saved thread/turn receipt
in the private lab record. Use the existing synthetic peer to inject a
lost acknowledgement before attempting a real transport cut. For a later
approved cut, suppress delivery of the reply after forwarding the request,
then reopen in read-only reconciliation and prove there was one mutation
send. A receipt without a recoverable exact turn remains unresolved.
Compare with a normal acknowledged run and record which server evidence
survives. This review performed neither run.

Further experiments must establish Windows child-tree survival and cleanup
ownership, exact handling of approval resolution races, independent Git/PR
side-effect reconciliation, held-resource fencing without guest-clock
advance, and browser traffic isolation with the integrated feed. Keep real
and synthetic results separately labeled. No emulated time was measured in
this source review.
