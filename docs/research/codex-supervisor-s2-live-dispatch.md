# Manual Git-to-Codex text analysis

This implements the first live-capable S2 path for [issue 86](https://github.com/smartyhall/deskmate-formats/issues/86).
**Only synthetic execution has been performed for this change. No Git-delivered
real model turn is authorized by this document or the implementation assignment.**
The [real S0 milestone](codex-supervisor-s0-second-live-result-20261116.md), merged
as `3f5622d534f800312e1a55a6dac47ba8522cc36c`, is the native foundation. It is not
repeated here. Issue 86 stays open until a real Git-delivered turn is reviewed.

## Reused components and narrow scope

The bridge extends the existing S1 `TrustedSource`, version-1 manifest and private
SQLite acceptance queue. It retains deterministic queue/task/revision claims,
the bridge lock, S0 immutable plan/attempt fence, owned `AppServer`, schema/native
pins, `Operations` write-ahead ledger, terminal/history validation, private
evidence, direct-child teardown and redacted Observatory publication. There is
no scheduler, service, listener for commands, desktop-session attachment, approval
sender or emulator capability. Native restart/resume is not a prerequisite.

The supported class is **text-analysis-v1**: a version-1 `offline` manifest whose
resources are exactly `["source-read"]`. The profile in the manifest is an S1
request label. The operator separately selects the worker's `experimental-lab`
execution profile. Task data never selects that profile, model, effort, cwd,
environment, approvals or executable. Portable-test execution, repository editing,
arbitrary filesystem reading, shell commands and tool-enabled research are not
implemented by this class.

The frozen context contains the original manifest UTF-8 bytes and the original
UTF-8 contents, Git blob identities and SHA-256 hashes of every `instructions`
reference. Documents must be regular non-executable Markdown under `docs/`, at
the exact accepted commit, as required by S1. This first slice supplies reviewed
documentation directly; it does not add a general source-file selector to the
manifest. Its entire rendered prompt is at most **32,768 UTF-8 bytes**. Oversize
input is refused, never silently truncated. All input prose is lower trust.
A fixed, independently frozen `developerInstructions` message prohibits tools
and overrides from the task. The only protocol interface expansion is permitting
that existing schema-defined `thread/start` field. The S0 sentinel prompt and
sentinel verification remain unchanged for non-task plans.

The owner requires a completed receipt and exact terminal thread/turn identity,
one nonblank final agent response of at most **16,384 UTF-8 bytes**, no unexpected
item/approval, one completed persisted turn with `itemsView=full` and no next
cursor, the exact input text and response in history, and an idle matching thread.
Empty optional text-element metadata is allowed. A terminal event may omit its
items; full persisted history is still required. If terminal answers are present,
they must agree too. The response and its hash are retained in private
`outcome.json`, with `answer_review=operator-review-required`. This verifies
protocol completion, not factual correctness. The answer requires human review.

## Four independent gates

1. Git discovery verifies the configured standalone clone, exact direct branch
   tip, ancestry, manifest blob and instruction hashes. It writes no acceptance.
2. S1 acceptance records the exact review token in the existing private queue.
   It starts no worker.
3. S2 preparation revalidates that receipt and Git source, freezes one plan and
   returns its digest as a distinct dispatch token. It consumes no model usage.
4. Dispatch requires that exact digest in `--authorize-dispatch`. A live command
   additionally requires separate `--authorize-live-plan` and `--accept-lab-risk`
   confirmations of the same frozen digest. These are explicit operator intent
   confirmations, not cryptographic signatures. Knowing a digest is not an
   approval workflow or authority obtained from Git.

Both preparation and dispatch refuse rejected/unaccepted, expired, superseded or
unresolved queue decisions, stale Git tips, changed bytes/provenance and unsatisfied
dependencies. S1 requires dependency acceptance; S2 additionally requires an exact
completed S2 outcome in the same bridge state, of the same worker kind. A synthetic
completion cannot satisfy a live dependency. Dependency outcome hashes are frozen.
First demonstrations should have no dependencies. Later Git commits make an old
acceptance stale even if the manifest is unchanged; prepare a newly reviewed task
revision at the new tip. Working-tree edits are ignored and never enter context.

For this repository's live first slice, all installed project Python modules and
the schema must byte-match `src/deskmate_formats/` at the accepted task commit.
Preparation and dispatch refuse a mismatched installation. The plan also pins
all installed module hashes, native executable/version/schema, config, staged
auth hash, model, effort, environment, deadlines, scratch cwd, exact task context
and response limits. Reinstalling or editing implementation after preparation
requires a new task revision and fresh review; never edit an approved plan.

One state directory is bound to one queue. Preserve it and the queue across runs.
The bridge holds its state lock and the read-only queue lock through execution;
one cooperating child runs at a time. Existing `synthetic-only` state binding
records are accepted as legacy custody records; new roots say `owned-one-shot`.
Existing claims are never overwritten. Old sentinel-only S2 plans are refused by
this task-specific bridge rather than migrated or replayed. Standalone S0 canaries
retain their original commands.

## Manual commands and inspection

Build/install the independently reviewed revision as in the
[operator driver guide](codex-supervisor-operator-driver.md). All command output
is private. Use a protected local parent outside Git as described in the
[S0 runbook](codex-supervisor-s0-live-canary.md). Do not loosen refused ACLs.

After review/merge, maintain a full standalone trusted clone manually. Fetching
does not execute tasks. Check that the selected local branch is its reviewed tip.
Do not use a linked worktree. For a new queue, the independently checked anchor
can be the merged S0 milestone above. A pre-existing queue retains its anchor.

```powershell
$checkout = 'C:\LAB\trusted-task-clone'
$queue = 'C:\PRIVATE-LAB-PARENT\s1-queue'
$state = 'C:\PRIVATE-LAB-PARENT\s2-state'
$anchor = '3f5622d534f800312e1a55a6dac47ba8522cc36c'
# Set this to the full independently reviewed local main tip after merge.
$reviewedTip = git -C $checkout rev-parse refs/heads/main
$task = 's2-canary-evidence-analysis'
$path = "ops/tasks/$task.json"

# Initialize only once; preserve an existing queue instead of replacing it.
deskmate-supervisor-task --queue $queue init --checkout $checkout --repository https://github.com/smartyhall/deskmate-formats.git --branch main --anchor $anchor
$candidate = deskmate-supervisor-task --queue $queue discover $reviewedTip $path | ConvertFrom-Json
# Inspect the full manifest and both documents at $reviewedTip; review their hashes.
$candidate | ConvertTo-Json -Depth 30
'Reviewed exact manifest and both supplied documents for text-only analysis' | deskmate-supervisor-task --queue $queue accept $reviewedTip $path --review-token $candidate.review_token --reason-stdin
deskmate-supervisor-task --queue $queue inspect $task 1
```

The version-1 candidate is committed at
[`ops/tasks/s2-canary-evidence-analysis.json`](../../ops/tasks/s2-canary-evidence-analysis.json).
Its only instructions are the existing nonproprietary second S0 live report and
experimental-lab posture document, with actual byte hashes in the manifest.
No new instruction document is needed. Publication is a proposal for review;
neither publication nor these examples accept or dispatch it.

The assignment asks for an evidence-based assessment of what the native milestone
establishes, what remains unproved, and how accepted VM-local risk affects the
next Git-driven experiment. Acceptance criterion: a substantive answer with at
least three concrete observed findings and three explicit limits, citations to
the supplied paths, a clear distinction between S0 success and S2 acceptance,
and a proposed review checklist for the first real Git result. No claims of OS
confinement, native restart validation or already-completed live S2 are acceptable.
Those are operator content criteria, not a synthetic sentinel test.

For offline rehearsal use a **disposable synthetic queue/task**, not the proposed
real task's permanent claim. The installed demo below does that automatically.
A synthetic dispatch of the actual accepted task would consume its one claim.

Live preparation requires every setting explicitly. The following example proposes
the previously proven `gpt-6-luna` / `low`; the operator must select and authorize
the actual values. There is no model lookup, default or fallback. `$native` must
be the pinned absolute `codex.exe` and `$auth` an existing absolute credential
file. Preparation copies only that file privately and runs only the verified
executable's `--version`, never login or app-server.

```powershell
$native = 'C:\EXACT-PINNED-INSTALL\codex.exe'
$auth = 'C:\EXISTING-PRIVATE-HOME\auth.json'
$grant = deskmate-supervisor-s2 --state $state prepare-live --queue $queue $task 1 --accepted-review-token $candidate.review_token --executable $native --profile experimental-lab --auth-file $auth --model gpt-6-luna --effort low | ConvertFrom-Json
deskmate-supervisor-s2 --state $state inspect $grant.claim
deskmate-supervisor-s2 --state $state validate --queue $queue $grant.claim
```

`inspect` displays the **complete** frozen plan, identity, source content, model,
effort, working directory, resource limits, attempts, operation receipts and outcome.
`validate` additionally rechecks Git, acceptance, dependencies and S0 preflight pins,
and refuses previously attempted claims. Both are offline; `validate` may repeat
the pinned executable's `--version` only. No grant is consumed. Preserve command
transcripts privately. Exit 4 gives fixed, specific source/plan refusal diagnostics;
storage/system exceptions retain a generic diagnostic to avoid leaking private data.

Stop here for the assignment. An example **future, separately supplied** operator
authorization is:

> I reviewed task ID/revision, accepted source commit/blob/review token, claim,
> complete plan and digest D, model gpt-6-luna, low effort, experimental-lab profile,
> empty scratch cwd, 10-second RPC and 60-second observation bounds. I authorize
> dispatch of this exact claim and one new supervisor-owned native text-analysis
> model turn. I separately accept the documented ordinary VM permissions and
> unverified confinement/cancellation/descendant limitations. No replay or other
> model turn is authorized.

Only after that grant, an operator manually invokes:

```powershell
$digest = $grant.plan_sha256 # Must equal the independently reviewed D.
deskmate-supervisor-s2 --state $state dispatch-live --queue $queue $grant.claim --authorize-dispatch $digest --authorize-live-plan $digest --accept-lab-risk $digest
deskmate-supervisor-s2 --state $state inspect $grant.claim
```

`prepare-synthetic` takes the same queue/ID/revision/review-token arguments and
an optional `--scenario`; it selects the fixed installed synthetic peer with
model `synthetic`, effort `low`, profile `synthetic`. `dispatch-synthetic` requires
only its separate dispatch digest. It cannot launch a live plan. Both worker
kinds send the exact reviewed task prompt. The synthetic peer deterministically
processes manifest fields and document lines/excerpts; it proves data flow, not
model reasoning or answer quality.

## Evidence, uncertainty and observation

Before launch, a permanent attempt records dispatch and model/lab confirmations.
The owner writes launch/request intent, registers its child generation/PID/stamp,
and records S0 mutation intent before pipe writes. Normal execution performs one
`thread/start`, one `turn/start`, `thread/read` and `thread/turns/list`. No tool or
approval request is answered. No uncertain mutation is retried. Blocked outcomes
retain ledger uncertainty and private evidence. A killed owner can leave an
attempt with no outcome: inspect it as uncertain, never dispatchable. There is no
live reconciliation/resume, force-clear or S2 replay command. An operator may
review and accept a new task revision after resolving consequences; deleting
state or using another root defeats the cooperating-owner boundary.

Child cleanup uses only the retained direct-child handle. Descendant containment,
provider cancellation, spending caps, power-loss durability and OS/network isolation
remain unproved. Developer instructions and read-only policy are behavior requests,
not proof that no tool could execute. The accepted laboratory posture applies;
no additional VM/account/isolation investigation is introduced here.

Observatory receives fixed lifecycle summaries, opaque correlations and a fixed
synthetic/live outcome note. It receives no prompt, raw source IDs, paths, model
answer or credential data. Publication follows the durable outcome; publication
failure never permits redispatch. The read-only HTTP viewer cannot access the
queue/owner, accept tasks or issue grants. Preserve original private evidence;
review a redacted projection before any publication.

## Reproduction

```powershell
python -m unittest discover -s tests/portable -p 'test_supervisor*.py' -v
python -m unittest discover -s tests/portable -v
python -m unittest discover -s deployment/windows10/tests -v
python -m ruff check src tests/portable tools
python -m reuse lint
python -m build
python tools/check_install.py
python tools/audit_repository.py
python tools/experimental/supervisor_offline_demo.py --private-root 'C:\PRIVATE-LAB-PARENT\s2-text-demo-UNIQUE'
```

The deterministic demo uses installed public CLIs and a disposable Git repository:
commit → discovery → acceptance → preparation → offline validation → bad-grant
refusal → explicit synthetic dispatch → terminal/full-input/history/answer outcome
→ duplicate refusal → read-only Observatory GET/denial checks. Queue, ledger,
outcome and peer hashes must remain unchanged across duplicate attempts and HTTP
reads. It preserves all commands/stdout/stderr/HTTP bodies and a hash-bearing
summary privately. No emulator is launched: attributable emulated time is 0 ms;
no guest counter is measured. See the accompanying validation evidence for actual
Windows 10 observations and hashes. Real S2 remains unverified until separately
authorized, executed and independently reviewed.

The [2026-11-16 validation report](codex-supervisor-s2-validation-20261116.md)
records the actual installed Windows demonstration and passing portable checks.
