# Next Codex campaign readiness

Audit date: 2026-11-07 (America/New_York). **Preparation only; no campaign
started.** Recommendation: a bounded laboratory reliability campaign (C),
then reverse engineering (A), then Supervisor integration (B). C offers the
best initial combination of independent offline work, durable checkpoints and
manageable risk. It does not need a working autonomous supervisor.

## Starting point and evidence limits

Fetched `origin/main`: `0d8c9e9cb538c65c382cd4f5478048e4397c6bb7`, matching
the requested base. Initial checkout was clean on
`codex/issue-58-s0-live-canary` at
`1a0c9ae300e82da1defb6a2ad10122871aa95e36`; this report branches from main,
not that unmerged work. [PR #65](https://github.com/smartyhall/deskmate-formats/pull/65)
was inspected read-only: open, draft, preparation only, live results NOT RUN.
Its runbook is a proposal, not a capability present on main.

`PROJECT_STATUS.md` is absent from tracked files and was not found in bounded
searches of local sources, references, Desktop and Documents. This audit uses
the [README status](../../README.md#project-status), research reports and
[deployment status](../../deployment/windows10/INTEGRATION-STATUS.md) instead.
README's broad Filer/no-native-experiment wording predates the later sample
open/exit observation; prefer the scoped newer evidence below. Locate the
intended private status file before the next campaign, without inventing its
contents or replacing historical reports.

| Area | Demonstrated or implemented | Limit / next question |
| --- | --- | --- |
| Native 86Box | Authenticated loopback client, bounded stepping, registers, approved RAM, native framebuffer, disposable RSX/DOS baseline and original guest canary; visible/background/offscreen modes tested in a logged-in session. [Client](86box-client.md), [canary](86box-guest-canary.md), [display modes](86box-visible-operation.md). | Not a general debugger. Service, locked desktop and RDP-disconnected operation untested; passive display does not completely fence host input. |
| Observatory | Live held-canary browser comparison: guest clock 15,044→15,044 ms, **0 ms elapsed**, over 14.408 host seconds; no additional native connection attempts in the monitored owner process. [Live report](86box-observatory-live-report.md). | Scoped RAM/counter samples, not proof about all host processes or unsampled transitions. Genuine old-browser acceptance remains open. |
| Agent telemetry | [M0/M1](observatory-v2-m0-m1.md) journal/feed and [M2](observatory-v2-m2.md) owned CLI wrapper implemented; synthetic crash/privacy/HTTP cases exercised. | Real M2 event ordering and Windows graceful Ctrl+C unmeasured. Browser is read-only; neither feed nor heartbeat grants control. |
| Calendar | Bounded reader/append writer, five-event native acceptance, E15–E19 storage observations, E01/E02 historical byte matches and ordinary timed Alarm `31→71` differential. [Writer](../formats/calendar/writer-lab-notes.md), [Alarm](calendar-alarm-encoding.md). | No general allocator, arbitrary time/date codec, edit/delete writer or universal reuse rule. Alarm delivery and other appointment types remain untested. |
| Window/control semantics | Calendar held Add/Change identity requires allocation plus descriptor ownership/frame/table/title evidence. Address Book shared packed layout/allocation demonstrated. [Calendar](calendar-live-dialog-identity.md), [portability](sdk-dialog-portability.md). | Stale titles survive cancellation; Calendar outer-record ownership rule fails at Address Book B. Filer Print Form remains a static prediction. |
| DMDB/Filer | Named service thunks and conditional loader paths established statically. Later native CARMAINT open/menu/cancel/exit preserved the whole disk. | Actual INT E0 vector, DS:2A62 callee and record-operation consumers unresolved. Print record/report disabled; printer absence is only a hypothesis. F01/F02 schema/record creation unperformed. |
| Supervisor | [S0](codex-supervisor-s0.md): pinned stdio/profile, receipts, exact-ID reconciliation and telemetry with synthetic child. [S1](codex-supervisor-s1.md): trusted Git intake, exact-revision review, private durable queue and sanitized publication with crash tests. | No real S0 model turn/restart validation, integrated canary driver, production approval sender or S2 dispatch. S1 acceptance is not dispatch authority. Real child descendants and cleanup unverified. |

These are historical runtime observations, source findings and synthetic tests
as labeled, not new live validation. The packaged S0 profile is pinned to CLI
0.166.0, SHA-256
`c28048281174969346b83cfc30bd05523da1d608a73375abfcc86040309b5bb9`;
binary/source/ROM/config pins remain in the linked reports. Reverify them
before use; do not silently upgrade to make an experiment run.

## Open issue triage and session blockers

GitHub open-issue snapshot obtained with
`gh issue list --repo smartyhall/deskmate-formats --state open --limit 100 --json number,title,body,url`:

| Issue | Readiness decision |
| --- | --- |
| [#35](https://github.com/smartyhall/deskmate-formats/issues/35) startup readiness timeout | Best offline entry: synthetic delayed token/listener/authentication/deadline diagnosis. A timeout previously left a healthy visible child; never infer exit or relaunch. |
| [#54](https://github.com/smartyhall/deskmate-formats/issues/54) disabled Filer print commands | Static predicate investigation ready with pinned private binaries. Dispatch route is not the enablement predicate. New record creation, printer changes, RAM capture and printing are not authorized by the issue. |
| [#25](https://github.com/smartyhall/deskmate-formats/issues/25) DMDB binding | Static checkpoint already reached its unresolved loader edge. Exact runtime plan exists but needs instruction-synchronized non-writing stops; current millisecond stepping and GDB-disabled build do not establish that ability. |
| [#58](https://github.com/smartyhall/deskmate-formats/issues/58) real S0 gate | Offline foundation complete; ordinary live canary remains separately gated. PR #65 identifies missing controls, not an executable driver. |
| [#31](https://github.com/smartyhall/deskmate-formats/issues/31) observation dashboard | Issue body is older than implemented/live observer evidence. Remaining historical-browser qualification is independent; do not rebuild the dashboard from that stale description. |
| [#32](https://github.com/smartyhall/deskmate-formats/issues/32) Windows provisioning | Partial live installation is not clean ISO/OOBE validation. VM changes, reboot/resume and provisioning are a separate operator mission. |
| [#10](https://github.com/smartyhall/deskmate-formats/issues/10) DOSBox keyboard MCP | Older, separate registration path; not a prerequisite for native 86Box work. New registration and guest trials need their own scope. |

Long-session blockers include inaccessible private source/evidence or DOSLAB_ROOT,
missing optional dependencies, source imports resolving to an older wheel,
Ghidra import failures/locks, unavailable exact-stop debugging, wrong process or
reset epoch, native socket contention, auth/quota exhaustion, private storage
ACL/space failures, and journal retention caps. M0/M1 defaults fail closed at
16 MiB or 10,000 records; arrange deliberate archive/rollover, not deletion.
Installed Ghidra's segment-MOV display anomaly requires original-byte checks
([call review](database-call-review.md)); do not equate displayed names or
synthetic addresses with runtime DS. No framework installation is prerequisite
to this audit or an offline first milestone.

## Candidate campaigns and first milestones

All sequences below are proposals for a later authorized mission. Each arrow
ends in a reviewable artifact; a blocked live gate need not stop other offline
work. None requires additional Codex agents or automatic dispatch.

| Campaign | Required start / evidence | Longest useful sequence and deliverables | Concrete first milestone / stopping point |
| --- | --- | --- | --- |
| **C — reliability first** | Clean dedicated checkout; #35 failure/verification receipts preserved privately; existing ROM-free client/launcher tests and synthetic native peer. No emulator needed initially. | Model delayed token/listener/authentication and finite deadline cases → regress healthy-child-after-timeout/no-relaunch behavior → review process identity and ownership handoff → checkpoint/evidence manifests and retention failure cases → nonintrusive immutable-view monitoring tests. Produce small tested patches and an operator recovery decision table. Later qualify startup/recovery live only on a separately authorized clone. | Reproduce #35's ambiguity with a synthetic delayed peer and add focused regression cases that preserve the original failure receipt, identify the surviving process and refuse a second launch. Stop before live reproduction or any automatic kill/reconnect/replay policy. |
| **A — reverse engineering next** | Pin private DeskMate/SDK bytes and tool revisions; use fresh Ghidra project/output, preserve original databases. Three committed Calendar fixtures plus synthetic corpus and private fixed-byte assertions exist; no committed Filer F01/F02 specimen. | Review exact Filer menu enable predicates (#54) → publish confidence/offset findings or first unresolved edge → trace bounded DMDB index/allocator candidates → extend conservative offline semantic replay/negative cases → select one controlled fixture differential. Existing headless Ghidra scripts and structural helpers support static work; native framebuffer plus approved RAM support later held checkpoints. Fixture writers/regressions support measured profiles only. | Explain F504/Print report enablement statically, or produce the smallest unresolved predicate and safe A/B proposal. Then stop that trace rather than guessing. Independent Calendar replay or consumer tracing can continue. Later authorize F00 reconciliation then F01→F02, or one Calendar variant; do not batch speculative guest saves. |
| **B — Supervisor last** | Main's S0/S1 primitives, pinned schema/CLI, synthetic protocol and task Git/queue fixtures. Review PR #65 without assuming merge. No emulator resources in canary. | Implement a small experiment-only bounded owner/driver → synthetic normal/failure/restart tests and private export → review isolated argv/cwd/environment/configuration → separately authorize ordinary live A once → durable exact-ID read-only restart evidence → review lost-ack extension separately. Only after real S0 acceptance and the [reuse ADR](agent-orchestrator-reuse-assessment.md) gate consider S2's one-worker explicit dispatch grants and durable follow-ups. | Offline driver/configuration design and synthetic acceptance: deadlines, notification-to-telemetry wiring, receipt preservation, effective-policy gate and owned-child close. Stop before real process launch/model input. No S2 implementation as preparation. |

B's launch gaps are material: dedicated CODEX_HOME alone does not establish
isolation; model/sandbox/approval/tools/budget are not settable through the S0
RPC allowlist. There is no hard model-budget API, bounded public wire recorder,
transport-only fault cut or verified real descendant cleanup. Ordinary success
must precede a separately reviewed lost-ack experiment. A time limit bounds
observation, not model cost or server execution. Production approval replies
remain absent; abort unexpected approval requests.

## Checkpoints, recovery and authorization

1. Before spending a fresh allocation, locate private PROJECT_STATUS/DOSLAB,
   confirm existing dependency/import paths without installs, storage/ACLs and
   archive capacity, and pin the accepted base/tool/media/configuration hashes.
   Establish whether an emulator already has an owner from existing receipts;
   no speculative connection or launch. Choose a finite offline backlog plus
   explicit live gates, exclusions, budget and stop conditions with the operator.
2. Work one small claim at a time: define oracle/control, record command and
   revision, run applicable portable checks, preserve artifacts, then commit.
   Maintain a compact current-status record after each milestone, referring to
   settled Alarm/Add-Change/E15–E19 results instead of repeating them. Stop a
   static trace at its first unresolved edge; switch to independent offline work.
3. Software reads and deterministic tests against fresh disposable directories
   can be retried after checking local state. A guest key batch/save/reset/media
   change or model mutation with a lost response cannot. Preserve stable operation
   IDs, original receipts and uncertainty; halt dependent actions and reconcile
   exact process/generation/thread/turn/checkpoint evidence before proceeding.
   Missing history or a plausible screen is not proof of nonexecution. Never
   replay with a new ID, reset the guest or create a fresh ledger as recovery.
4. Stop on identity/pin/reset mismatch, unexpected prompt/label, unknown RAM
   scope, ambiguous mutation, storage/publication failure, retention exhaustion,
   auth/quota failure or deadline. A failed guest experiment does not block
   fixture analysis, static work or portable reliability tests. Lost emulator
   custody cannot be released by worker timeout, lease expiry or worktree cleanup.
5. Archive raw screenshots, RAM, native journals, commercial inputs, disks,
   launch receipts and private protocol/history outside Git. Keep credentials
   separately protected and out of logs. Back up config/NVRAM before authorized
   changes; use disposable media and format only a new explicitly identified disk.
   Preserve closed/consistent SQLite stores with journals and hash manifests.
   Commit eligible application-created synthetic documents byte-for-byte with
   SHA-256, experimental provenance and REUSE sidecars; embedded schema is eligible.
6. Commit and, **only within an explicit future publication grant**, push each
   verified milestone on a dedicated branch; inspect exact remote state before
   retrying an uncertain push/PR creation. Keep PRs draft; no merge authority is
   implied. Finish with commits/PRs, test results, private archive locations/hashes,
   unresolved operations/ownership, exact next gate and skipped work. Preserve a
   useful partial checkpoint before quota exhaustion; no self-restarting agent,
   watchdog, scheduled job or paid-model launcher.

Explicit operator approval is required for new native runs/connections and guest
mutations; exact RAM spans and instruction-stop experiments; Filer schema/data
creation or printer-setting comparisons (never submit a print job as observation);
VM/dependency/emulator/debugger changes; headless/background mode selection;
and real app-server/model usage, isolation policy, owned-child teardown and any
interrupt/restart/fault injection. Visible 86Box remains the demonstration default,
controlled exclusively by the authenticated socket. Computer Use/host input over
RDP requires explicit approval and is unnecessary here. New future remote
publication also needs a grant; this audit alone authorizes only its own report
commit, push and draft PR.

## Audit validation

This preflight used source/docs, fetched Git metadata, open issue bodies and
PR #65 metadata/runbook. No emulator/native connection, app-server, model child,
additional agent, installation or VM change was performed. Actual guest-clock
delta was **not measured**; attributable requested emulated execution was **0 ms**.
Historical runtime results above were not reproduced. Host: Windows 10 build
19045, Python 3.13.17; installed REUSE 6.3.0 and jsonschema 4.26.0.
Validation (source imports via `PYTHONPATH=src`, no dependency changes):

- `python -m unittest discover -s tests/portable -p 'test_86box_*.py' -v`:
  **18 passed**, 0.562 seconds; synthetic peers only.
- `python -m reuse lint`: **passed**, 251/251 files covered.
- `python tools/audit_repository.py`: **passed**, 509 source files,
  three application-generated fixtures and four synthetic JSONL fixtures.
- `git diff --check` and report-relative-link/fence checks: **passed**.

No full portable suite, new build, private-fixture suite or live acceptance
was run for this documentation-only change.
