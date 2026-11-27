# Quiet-host baseline qualification plan (after #206 and #207)

Status: **plan, with one attempt published**. This document implements no
optimization and makes no performance claim. It records what a baseline would
have to satisfy, and which Git subprocess costs the recorded measurements
already identify as the first candidates.

The first attempt is recorded in
[convergence baseline 001](convergence-baseline-001-20261127.md): measured
revision `2b3113c15b333f8a0718e353698e427404b2c31b`, two passing quiet gates,
three recorded iterations. It qualifies as a **characterization** baseline only
— §4's `package.source_first` condition fails structurally and the per-iteration
CPU condition was not recorded. The gates below are unchanged; nothing in this
plan was reweighted after the result was known.

## 1. Why another baseline is needed

The two full-suite runs in [the Windows study](windows-test-performance-20261126.md)
were taken on a host that other campaigns were loading, before the harness
recorded source and package identity. They are preserved there as **observed
conditions**, not as a baseline: their suite durations are upper bounds by the
old post-run Git queries, their source identity could not bind untracked files,
and their child-interpreter package origin was not qualified. The template-copy
A/B is a controlled comparison of one module, not a suite-wide result.

A baseline that can support an optimization claim has to answer four questions
the earlier runs could not: *exactly which source*, *which imported package*,
*which host conditions*, and *whether all of it stayed the same for every
iteration*.

## 2. Preconditions, in order

1. **Integration.** PR #199 is merged into `main`; PR #206 is merged (or its
   branch is the measured checkout, recorded as such); the #207 adoption
   decision for this campaign is written down rather than assumed.
2. **Campaign-owned environment.** The run uses the interpreter environment
   #206 provisions, not a shared site-packages. The report must show
   `package.matches_source: true` and `package.source_first: true` for the
   parent interpreter. Child processes are separate identities: a child started
   with `python -I` ignores `PYTHONPATH` and resolves from site-packages, and
   the harness records only the parent's origin. If a measured test spawns such
   a child, the run is a characterization and cannot become a fully qualified
   optimization result until #207's adoption makes the child's source provable.
3. **Quiet host.** No other campaign suite, laboratory VM job or agent
   workload. Provisional gate, recorded with the run: a five-minute idle
   observation with host CPU mean at or below 20 % and maximum at or below
   50 %, at most two CPUs of background activity, and no pending endpoint scan.
   If the gate is not met, stop and reschedule; a loaded run is not a slow
   baseline and must not be relabelled as one afterwards.

## 3. Protocol

- **Revision:** the exact integrated commit, recorded by the harness itself
  (`meta.source.revision`), not copied from a branch name.
- **Commands** (run from the checkout root, with the campaign environment
  active):

  ```console
  python -m deskmate_formats.perf run --profile portable --source . \
    --label quiet-baseline --repeat 3 --trace-processes --trace-git-commands \
    --sample-interval 5 \
    --json-out <private>/quiet-baseline.json \
    --public-out <private>/quiet-baseline.public.json \
    --summary-out <private>/quiet-baseline.summary.json \
    --md-out <private>/quiet-baseline.md
  ```

  One warm-up run is executed and discarded before the three recorded
  iterations, so import and template construction do not land in iteration 1.
  `--repeat` keeps each iteration's identity separate instead of averaging it
  away.
- **Same host for both arms.** Before/after comparisons are made on the same
  machine, same interpreter and same quiet gate; a comparison across hosts or
  across load bands is an observation.
- **Arms:** baseline first; then one optimization at a time on the same
  revision plus its own commit, with the same protocol. No optimization is
  combined with another before each has its own measured pair.
- **Microbenchmarks** are a separate command and a separate report. They
  characterize the host; they are never mixed into suite totals.

## 4. Acceptance gates

A baseline run qualifies only when all of these hold for every iteration:

- `meta.source.complete` is true, `untracked_digest` is present and
  `untracked_truncated` is false: no refusal category in `untracked_reason`.
- `meta.source_changed` is false; the before/after identity is identical.
- `package.matches_source` and `package.source_first` are true.
- Host sampling is complete, and the iteration's CPU mean stays inside the
  quiet band (spread across iterations at most 15 points, the comparator's
  existing tolerance).
- The workload identity set (test id, iteration) is identical across
  iterations and no new failure or error appears.
- `deskmate-test-perf compare` between the first and last iteration reports
  every qualification dimension as matched.

Anything short of that is written up as an observation with the failing
dimension named. The harness already reports those dimensions; the gate is a
reading of them, not a new mechanism.

## 5. Candidate optimizations (measured, not implemented)

The Git command mix measured on the two heaviest Supervisor tests (1 985 calls,
197 s of attributable call duration, about 99 ms per call) is in
[§3.3](windows-test-performance-20261126.md):

| Subcommand | Calls | Share | Batchable read path |
| --- | --- | --- | --- |
| `git cat-file` | 862 | 43.4 % | `--batch` / `--batch-check` |
| `git ls-tree` | 393 | 19.8 % | one recursive listing per commit |
| `git symbolic-ref` | 128 | 6.4 % | one `rev-parse --verify` per pass |
| `git hash-object` | 111 | 5.6 % | fixture-side write, not a read path |
| `git update-index` | 111 | 5.6 % | fixture-side write, not a read path |
| `git show-ref` | 107 | 5.4 % | cached with the branch tip |
| `git config` | 88 | 4.4 % | read once per source binding |
| `git merge-base` | 56 | 2.8 % | cached per (commit, anchor) |
| `git rev-parse` | 36 | 1.8 % | cached with the branch tip |

In `supervisor/task_git.py`, in measured-share order:

1. **Batch the blob reads.** `_blob` runs `cat-file -s` and `cat-file blob`
   per path; `cat-file --batch-check` and `cat-file --batch` answer size and
   content for many objects in one process. Each reply must still be matched to
   the requested object ID, type and size, and a missing or malformed reply must
   fail closed exactly as the single-object calls do.
2. **List the tree once.** `_blob` runs `ls-tree -z --full-tree <commit> -- <path>`
   per path. A single `ls-tree -r -z --full-tree <commit>` per commit can serve
   every path a `discover`/`verify` pass needs, with the same exact-path and
   mode checks applied to the parsed entry.
3. **Bind the source once per pass.** `_check_repository` re-runs
   `config --get-all remote.origin.url` and the include-config probe on every
   call; reading them once per `TrustedSource` binding removes repeated
   processes without changing what is verified.
4. **Resolve the tip once.** `symbolic-ref`, `show-ref --verify` and
   `merge-base --is-ancestor` are each run per verification. One
   `rev-parse --verify refs/heads/<branch>` plus a cached ancestry check per
   `(tip, anchor)` pair preserves the direct-reference requirement and removes
   the repeated spawns.

What must not change: a direct branch reference, a full object ID, exact-path
and regular-non-executable-blob checks, the no-redirect/no-alternates/no-include
config checks, single dispatch, no replay, and fail-closed behaviour on timeout
or malformed output. Batching is a change of query shape, not of trust.

Expected evidence for each optimization, in order of strength: the deterministic
Git call count for the same tests; setup time; per-test wall and CPU on the same
quiet host; and the suite total with all qualification dimensions matched. A
call-count reduction is not by itself a wall-clock claim: the earlier arithmetic
upper bound of about 124 s for the two tests assumed the per-call cost is
unchanged, which batching does not guarantee.

## 6. Artifacts and handoff

- Private raw report, summary and markdown under the private campaign evidence
  directory; the public projection is produced with `--public-out`, never by
  editing the private file.
- One usage receipt under `docs/evidence/agent-usage/` with an accurate dual
  licence sidecar (`GPL-3.0-or-later OR CC-BY-SA-4.0`), as for the other
  campaign receipts.
- A short results document that keeps the earlier concurrent-load findings as
  observations and states the baseline's host band, iterations and identity.
- Optimization work stays in its own reviewable branch and PR, owned by whoever
  owns `supervisor/task_git.py`; this branch hands over the plan and the
  measured call mix, not a partially batched implementation.

## 7. Non-goals

- No second concurrent-load baseline, and no reinterpretation of the first as a
  qualified one.
- No optimization code in this checkpoint.
- No change to shared Python installations, and no edit to the
  environment-isolation worker's branch.
- No claim that a child-process improvement is a suite improvement, and no
  merged result before the baseline's own dimensions are all matched.
