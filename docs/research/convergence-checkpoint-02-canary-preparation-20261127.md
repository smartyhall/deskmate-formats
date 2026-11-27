# Convergence checkpoint 02 — deterministic task canary preparation

**Status: preparation and isolated synthetic qualification only.** No real task
was submitted, accepted, prepared, enqueued or executed. No frozen plan exists,
no approval token was created, and no shared baseline was tagged. This record
documents an orientation checkpoint, one proposed manifest and the reusable
control evidence needed to resume the [issue #204](https://github.com/smartyhall/deskmate-formats/issues/204)
canary inside [issue #213](https://github.com/smartyhall/deskmate-formats/issues/213)
without re-deriving them.

- Campaign: `convergence-02`
- Repository: `smartyhall/deskmate-formats`
- Observed base revision: `277a42a2d2fc23dffc4f4e60fc10d9f745ee9d91`
  (merge of PR #216; `origin/main` at orientation, 2026-11-27T21:2xZ)
- Provider: Freebuff, interactive local desktop session; no model API call, no
  emulator, no provider endpoint contacted
- Reused mechanism: `deskmate_formats.supervisor.deterministic`,
  `procedures`, `task_manifest`, `task_git`, `task_queue` and
  `deskmate_formats.campaign_env`. No parallel task format, executor or service
  was introduced.

## 1. What this checkpoint did and did not do

Done:

1. Re-established the shared origin, the campaign worktree, the qualified
   campaign environment and the controller identities (§2).
2. Established the expected input identity for `README.md` independently from
   the committed bytes and compared it with the working tree, including the
   line-ending policy (§3).
3. Prepared and validated the proposed manifest `ops/tasks/github-hash-canary.json`
   against the implemented schema and the reviewed procedure registry (§4).
4. Exercised 18 refusal and durability controls against disposable synthetic
   fixtures in a private environment, and separated them from pre-existing
   portable test coverage (§5).
5. Recorded exactly which prerequisites remain before a frozen plan can exist,
   and the operator-facing command sequence that would produce it (§6–§7).

Not done, and deliberately not done: trusted-source acceptance, `prepare-task`,
plan authorization, execution, enqueueing, self-review, self-merge, baseline
tagging, performance work, and the deferred investigations of
[#214](https://github.com/smartyhall/deskmate-formats/issues/214) and
[#215](https://github.com/smartyhall/deskmate-formats/issues/215).

## 2. Orientation

| Item | Value |
| --- | --- |
| `origin/main` at orientation | `277a42a2d2fc23dffc4f4e60fc10d9f745ee9d91` |
| Campaign worktree | `<worktree>`, branch `freebuff/convergence-cp02-canary-20261127`, created from `origin/main`, clean before the manifest was written |
| Previously measured baseline revision | `2b3113c15b333f8a0718e353698e427404b2c31b` ([baseline 001](convergence-baseline-001-20261127.md)) — an ancestor of the observed base revision, not the shared origin |
| Campaign environment | `convergence-02`, provisioned for the campaign worktree, `install_mode: offline`, `index_access: false` |
| Interpreter | CPython 3.13.17, campaign environment executable SHA-256 `4e67d9e9a3673aa7b6219f1280d5ec3f1b6c0d5bd98ea8688c72d0cb7582d664` |
| Installed package | `deskmate_formats` 0.1.0.dev0, origin `<campaign-env>/Lib/site-packages/deskmate_formats`, tree digest `9f733f809fa336d23afc4ccc1d2e627b9dd55308ea7b1bce9596d48a47838b34`, Python-only digest `98794053628589252c584652c4130923dc7b1755969a9b30449b8ffcbabf460e` |
| Controller implementation binding | `deskmate_formats.supervisor`, 33 files, 469,782 bytes, SHA-256 `b8e4d08237d59cc45e6a0e37bceee50a21452d97a7ef0331ff8d9f5922972e6d` |
| Provision verdict | `qualified` |
| Preflight | `qualified`, `measurement_allowed: true`, 11 of 11 checks passing, run with the campaign interpreter |
| Git | 2.56.0.windows.2 |

The campaign environment is a new, campaign-owned environment. The
`convergence-01` environment and its receipts were not modified, replaced or
reused for execution. The shared read-only tools environment recorded by the
[campaign environment procedure](campaign-environment-procedure.md) was used
only as the provisioning bootstrap; the default offline install succeeded with
it, and no package index was contacted.

Provisioning was first attempted with the system interpreter and was refused
with `installation-failed`, which is the documented consequence of a host whose
system interpreter has no build backend. That attempt produced no environment;
the retry used the documented bootstrap and produced a `qualified` receipt.

PR [#217](https://github.com/smartyhall/deskmate-formats/pull/217) (producer/CI
handoff policy) was **open and unmerged** at orientation (head
`3d8dc12e51a14a3b28664ed0e7c05e968711418a`; its documentation-only checks were
passing except one matrix job still pending when read). That policy changes only
`AGENTS.md` and `CONTRIBUTING.md`: it cannot alter the task schema, the reviewed
procedure registry, `README.md` or the intake code, so it does not invalidate
this preparation. It does mean the "pending CI is a valid producer handoff"
wording is **not yet integrated into `main`**, so this checkpoint concludes on
the older, stricter basis: nothing here depends on a policy that main does not
yet carry, and no producer self-merge occurred.

## 3. Source qualification and the independent expected identity

`README.md` is the declared input. Its identity was established from the
committed blob, not from the working tree:

| Item | Value |
| --- | --- |
| Revision inspected | `277a42a2d2fc23dffc4f4e60fc10d9f745ee9d91` |
| Blob object | `b2b3d17a0a70b94b5ae231feba319556bbff6430` |
| Committed bytes | 22,079 |
| Committed SHA-256 | `779b499e3760045f336151fa3910ce3abcba4836f2632e22b88a441583e86773` |
| Working-tree bytes | 22,079 |
| Working-tree SHA-256 | `779b499e3760045f336151fa3910ce3abcba4836f2632e22b88a441583e86773` |
| Committed CRLF / LF | 0 / 338 |
| `git ls-files --eol` | `i/lf w/lf attr/text eol=lf` |
| `git check-attr` | `text: set`, `eol: lf` |
| `core.autocrlf` | `true` |

The two byte sequences are identical, so there is **no** line-ending or
checkout-conversion gap to explain: the tracked blob already stores LF and the
`*.md text eol=lf` attribute forces LF in the working tree even though
`core.autocrlf` is `true` on this host. No input byte was normalized, rewritten
or re-encoded to make a comparison succeed; had the two differed, this record
would have stated a refusal rather than a match.

These values are the expected side of the canary comparison. They must be
re-established at the exact accepted revision before dispatch, because the
manifest itself names no commit and `README.md` may legitimately change after
`277a42a`.

## 4. The proposed manifest

`ops/tasks/github-hash-canary.json`, schema version 3, validated with the
implemented validator (`deskmate-supervisor-task validate`, exit 0). Parameter
checks against the implementation rather than the issue text:

| Claim (issue #204) | Implemented behaviour | Verdict |
| --- | --- | --- |
| `schema_version: 3` | version 3 is the only version that admits a `deterministic` block; `_REQUIRED`/`_OPTIONAL`/extras are enforced strictly | consistent |
| `category: verification`, `profile: offline` | the only accepted category pair for a deterministic block; any other profile is refused | consistent |
| `resources: ["source-read"]` | `validate_deterministic` requires the resource list to **equal** the procedure's declared resources; `hash-files` declares exactly `source-read` | consistent |
| `procedure: hash-files` | reviewed constant; descriptor `executes: fixed-script`, `execution_source: controller`, `modules: []`, `network: none`, timeout 300 s, limits 64 MiB per file / 256 MiB total / 64 paths | consistent |
| `arguments.paths: ["README.md"]` | `_safe_path` accepts a single relative segment; arguments must already equal their normalized form | consistent |
| `id`, `idempotency_key` | `[a-z0-9][a-z0-9-]{0,63}`; the canonical path must equal `ops/tasks/<id>.json` | consistent |

No `expires_at` was added: the manifest has no legitimate expiry to declare, and
a date chosen now would silently expire an operator-approved task. A later
revision may add one deliberately.

**Review and acceptance status: proposed, not accepted.** The manifest is not a
task. It becomes one only when an exact reviewed branch tip of the trusted source
contains it and an operator records an acceptance decision with the candidate's
review token and a reason. That has not happened, and this campaign did not
manufacture a token to simulate it.

## 5. Negative controls

Controls ran in a private, disposable tree under the campaign environment, each
against its own synthetic Git repository with a synthetic origin, manifest and
fixture. No real task, shared queue, other campaign, or live laboratory process
was touched. Harness:
`<private-evidence>/controls/run_controls.py`, SHA-256
`4171875572e8cbf3563e52ca77992db44f36404158151ebc192c9115724afbf3`; result
document: `<private-evidence>/controls/work/controls-result.json`, SHA-256
`0d9703fd8a4772a167ce53bf53aacb0b07c93a0119c86602b3bf838765cc679c`
(verdict `all-controls-as-expected`, 17 expected refusals, 0 unexpected).

| Control | Observed result |
| --- | --- |
| Acceptance decision with a token that is not the candidate's | refused: `review token does not match the exact candidate` |
| `prepare-task` binding with a fabricated token | refused: `exact current accepted revision required` (a bad token resolves to no acceptance at all) |
| Discovery at an ancestor commit instead of the branch tip | refused: `pinned commit is not the configured branch tip` |
| Trust anchor naming a different repository identity than the checkout's origin | refused: `Git origin is ambiguous or differs from configured identity` |
| Trusted reference that is not a canonical HTTPS repository identity | refused: `expected one canonical HTTPS repository identity` |
| Trusted reference that is a symbolic ref, not a direct branch | refused: `trusted branch must be a direct branch reference` |
| Changed manifest bytes at an already recorded revision | refused: `manifest bytes conflict with the recorded task revision` |
| Changed manifest bytes at a fresh queue | new candidate, distinct review token (`de348b13d132…` → `549b866d545a…`) |
| Earlier token used against the changed candidate | refused: `review token does not match the exact candidate` |
| Tracked input changed after the plan was frozen | refused at dispatch: `working-tree inputs changed after preparation` |
| Superseded revision bound for preparation | refused: `unresolved or superseded tasks block dispatch` |
| First authorized run | `completed`, `exit-zero`, source revision identical before and after |
| Structured result of that run | matches the independently computed digest and size of the fixture |
| Second dispatch of the same frozen plan | refused: `attempt already started; replay is forbidden` |
| Re-preparing into an existing attempt directory | refused: `attempt directory must be new` |
| Run authorized with a foreign digest | refused: `explicit authorization must match the exact plan digest` |
| Repeated acceptance decision on the same candidate | idempotent (`created: false`), no second record |
| Bound input removed before dispatch | refused: `a named procedure input does not exist in the working tree`; no attempt fence was written, so the attempt never started |
| Same plan after the exact bytes were restored | `completed` — the plan was not silently replayed, it had never started |
| Corrupted durable outcome record | refused: `invalid UTF-8 JSON` |
| Outcome record belonging to another plan | refused: `the recorded outcome belongs to another plan; it is not evidence for this attempt` |
| Started attempt with no terminal record | reads as `uncertain` with `requires_inspection: true` — never as success |
| Campaign worktree claim | acquired (`held`) and released (`released`, no lease left) in a private registry |
| Workspace-bound procedure without a qualified environment | refused: `a workspace procedure requires a qualified campaign environment` |

**Pre-existing coverage, kept separate from the controls exercised here.** The
following portable modules are the repository's own coverage of the same
refusals and were run, unmodified, with the campaign interpreter:
`test_supervisor_task_deterministic` (7 tests, OK),
`test_supervisor_deterministic` (25 tests, OK, 2 skipped),
`test_supervisor_deterministic_cli` (5 tests, OK),
`test_supervisor_task_queue` (7 tests, OK). This checkpoint adds no test file: it
qualifies the integrated mechanism rather than extending it.

Limitations of this control set:

- No procedure in the reviewed registry exits zero without emitting structured
  JSON, so "exit zero, unserialisable result" is exercised only by
  `test_supervisor_deterministic`, not here. The durable-record controls above
  cover the inspection side of missing or foreign evidence.
- The lease cycle ran against a private synthetic registry, not a real campaign
  claim, and no real worktree was reserved.
- Every synthetic origin was a local repository whose `remote.origin.url` merely
  matches the accepted identity shape. No network fetch, push or authentication
  occurred, and the controls say nothing about GitHub-side behaviour.
- The negative controls do not establish anything about the real canary's
  eventual observable outcome; they establish that the mechanism refuses what it
  is supposed to refuse.

## 6. Why no frozen plan exists

Two independent prerequisites are unmet, and neither may be manufactured:

1. **The manifest is not integrated into a trusted source tip.** Trusted intake
   discovers a manifest only in a configured branch of a trusted local clone,
   at an exact commit, and only after an operator records a decision against the
   candidate's review token. Opening this pull request is the reviewed
   integration boundary, not the acceptance.
2. **No operator authorization exists for any plan digest.** Even with an
   accepted revision, `prepare-task` would freeze a plan that the operator must
   approve by its exact digest before a single run.

A third, structural obstacle is worth recording because it constrains how the
next stage must be scheduled:

> **The accepted commit must still be the trusted branch tip.** `TrustedSource`
> pins a commit *and* requires it to be the tip of the configured direct branch
> at discovery, at acceptance, and again at planning. `main` advances on every
> merge, so a manifest merged to `main` is only acceptable at the merge commit
> itself; the next unrelated merge moves the tip and the pinned commit can no
> longer be accepted.

The low-risk way to satisfy that constraint is an operator-controlled, frozen
trusted reference: create a direct branch at the manifest's merge commit (so the
manifest exists at the tip and the pinned commit equals the tip), accept against
that branch, and leave it unmoved until the canary is closed. Advancing `main`
afterwards then cannot invalidate the accepted binding. This is a scheduling and
configuration decision for the operator, not a code change, and this campaign
did not create such a branch.

### Documentation and implementation drift (reported, not fixed)

[The source-bound execution procedure](source-bound-execution-procedure.md) and
§15 of [baseline 001](convergence-baseline-001-20261127.md) show
`prepare-task --environment-campaign … --environment-checkout …`. The
integrated `deterministic_cli` `prepare` and `prepare-task` parsers accept only
`--state --campaign --queue --working-directory --review-token [--timeout]`;
`--environment-*` exists only on `deskmate-supervisor-s3`. `deterministic.prepare`
does accept an `environment=` selection, and `hash-files` is a controller
procedure that does not need one, so the canary is unaffected — but a future
workspace-bound task prepared through this CLI would be refused with
`a workspace procedure requires a qualified campaign environment` and would have
to bind the environment another way. This is a documentation/code mismatch for a
reviewed change, not a defect introduced here, and it was not patched in this
checkpoint.

## 7. Proposed execution sequence (not executed)

Provided so the next session does not re-derive it. `<…>` marks a local path or
a private value that must not be published or pasted into a public record.

```text
# 1. operator: merge the manifest PR; note the merge commit M
# 2. operator: freeze a trusted reference at M in the trusted local clone
git branch canary/trusted-source M          # direct branch, tip == M, never advanced

# 3. operator: accept the reviewed candidate (reason on stdin; the token and
#    reason are private)
deskmate-supervisor-task --queue <queue> discover M ops/tasks/github-hash-canary.json
deskmate-supervisor-task --queue <queue> accept   M ops/tasks/github-hash-canary.json \
    --review-token <token> --reason-stdin

# 4. freeze the plan in a campaign checkout that is exactly at M and clean
deskmate-supervisor-deterministic prepare-task \
    --state <new attempt directory> --campaign convergence-02 \
    --queue <queue> --working-directory <checkout at M> \
    github-hash-canary 1 --review-token <token>

# 5. operator: authorize the printed plan_sha256 exactly, then one run
deskmate-supervisor-deterministic run --state <attempt> \
    --authorization <plan_sha256> --queue <queue> --registry <registry> --lease-seconds 300
```

Expected plan content to review before step 5: `procedure: hash-files`,
`arguments.paths: ["README.md"]`, `argv[0]` the campaign interpreter with
SHA-256 `4e67d9e9…`, `implementation.sha256` `b8e4d082…`, `source.revision` and
`source_commit` equal to `M`, `source.identity: git`, `source.dirty: false`,
`source.inputs.sha256` binding the accepted `README.md` bytes,
`resources: ["source-read"]`, `acceptance` equal to the accepted
`queue_id`/`id`/`revision`/`sequence`/`idempotency_key`/`review_token`, and
`execution.source: controller`.

Expected durable outcome: `completed`, `reason: exit-zero`,
`structured_result.files == [{"path": "README.md", "size": <n>, "sha256": <h>}]`
matching the independently computed values, `custody: clean`,
`source_revision_after == source_revision_before`,
`git_status_after` unchanged, `execution.verified: true` with the recorded note
that the child ran reviewed controller code rather than the workspace, the
attempt's process tree empty, and the worktree lease released.

**Scope of that proof.** `hash-files` is a controller procedure: it assembles a
fixed argument vector and runs `-I -c <reviewed script>` with the pinned
interpreter. The canary therefore qualifies trusted intake, source binding,
planning, lease and result return for the **controller process**. It does not
qualify workspace-bound child processes or project imports; that remains
[#207](https://github.com/smartyhall/deskmate-formats/issues/207)'s path
(`repository-audit` or `portable-tests` with a qualified environment), and no
part of this checkpoint narrows that distinction.

## 8. Evidence

Published here: this record and the proposed manifest with its REUSE sidecar. No
private path, token, account identity or raw process identifier appears in
either.

Retained private under `<private-evidence>`:

| File | Bytes | SHA-256 |
| --- | --- | --- |
| `source-identity.json` | 1,285 | `3db8de51289614f4aab9d8dc4d3d0ac1eab4bb72b67427aee6548b47f0d21364` |
| `environment/convergence-02-provision.json` | 25,411 | `b3428452bc9cf7bf48e0ea8a27baf6bb23741739ee0cb5b1d7eea14ea4f2a570` |
| `environment/convergence-02-preflight.json` | 16,309 | `a9eba650df2a242254259428eb1f1c869db769b78dbeb748a64a6158a6586a0a` |
| `controls/run_controls.py` | — | `4171875572e8cbf3563e52ca77992db44f36404158151ebc192c9115724afbf3` |
| `controls/work/controls-result.json` | 7,558 | `0d9703fd8a4772a167ce53bf53aacb0b07c93a0119c86602b3bf838765cc679c` |

`controls/work/` also holds the disposable synthetic repositories and queues the
controls created; they are regenerable from the harness and are not evidence in
themselves. The private environment directory keeps the `convergence-02` venv,
its `environment.json` record and its receipts.

## 9. Laboratory disposition

- No process was left running: every control child was a bounded
  `hash-files` invocation that completed or was refused before spawning; no
  emulator, provider call or long job was started.
- No lease is held. The synthetic registry claim was acquired and released; no
  real campaign resource was claimed.
- The `convergence-01` environment, its receipts, the previously measured
  worktrees and all other campaign checkouts were left untouched.
- `origin/main` was fetched, not reset; no local branch was rebased or force-pushed.

## 10. Operator decision required

Before the next stage, the operator must:

1. Review and integrate (or reject) this manifest PR. The producing agent did
   not and must not merge it.
2. Decide the trusted reference: a frozen direct branch at the merge commit, or
   acceptance against `main` inside the window before the next merge.
3. Record the acceptance decision with the candidate's review token and a
   reason, after confirming that the exact accepted revision's `README.md`
   identity still matches §3 or recording the new expected values.
4. Authorize the exact frozen plan digest, then permit one run.
5. Decide separately whether PR #217's producer/CI handoff wording should be
   integrated before further checkpoint handoffs.
