# Windows portable-suite performance under concurrent laboratory load

**Status:** two full runs analysed (concurrent load, less contended); an import
defect corrected, which recovers 72 tests that never ran; a host-CPU measurement
defect found by review and corrected (§5.4); one genuine failure confirmed in
both runs as a race and already fixed on PR #191; the dominant bottleneck
located down to Git subcommand; a cross-campaign wheel-skew hazard documented;
remaining items listed as open
**Date:** 2026-11-26 (baseline), 2026-11-27 (recovery and comparison)
**Host:** Windows 10 Pro 10.0.19045, 6 vCPU, 8 GiB RAM, shared laboratory VM
**Base revision:** `b5e525002b150352a8995de1bcddfbc5dc18a838`
**Harness:** [`portable-test-performance-harness.md`](portable-test-performance-harness.md)
**Private evidence:** retained outside Git (see §10)

## 1. The question

The portable suite intermittently fails and is unpredictably slow on this host,
but "the suite took 20 minutes" is not a finding: it does not say which test was
slow, whether the cost was computation or waiting, or whether the host was
saturated while it ran. Three questions were asked:

1. Where does portable-suite wall time actually go?
2. Which failures are defects in the code under test, which are defects in the
   tests, and which are the host exceeding a deadline?
3. What can be changed without weakening an assertion, reducing coverage or
   hiding a race?

## 2. Conditions, stated before the numbers

Measurements on a shared VM are only comparable when the host conditions are
comparable, so every run records its own host timeline and its own revision.
Absolute durations below are *observations under stated conditions*, not
constants.

| | Baseline (concurrent load) | Second run (less contended) |
| --- | --- | --- |
| Window (UTC) | 2026-11-26 09:29:02 – 09:50:27 | 2026-11-27 02:27:43 – 02:43:02 |
| CPU total, mean / max (corrected †) | **≈79 % / ≈100 %** | **≈35 % / ≈91 %** |
| CPU total, mean as first reported ‡ | 82.9 % / 99.8 % | 60.5 % / 92.0 % |
| Available memory, mean / min | 2.8 GiB / 1.9 GiB | 3.1 GiB / 2.3 GiB |
| Processes, mean / max | 228.9 / 253 | 209.2 / 235 |
| Threads, mean | 1983.7 | 1920.9 |
| Samples (5 s interval) | 252 | 183 |

† The first instrumentation double-counted idle time (§5.4). Corrected values
are derived from the stored ones — see that section for the derivation and its
limits. ‡ Shown so the earlier figures are traceable rather than quietly
rewritten.

The correction widens rather than narrows the gap between the windows: the
baseline was around 79 % busy and the second run around 35 %, not 83 % and 60 %.
Both runs are still loaded windows, and neither was idle.

The baseline was taken while other campaigns were executing on the same VM. That
workload is not reproducible on demand, so those numbers are preserved as the
recorded concurrent-load condition rather than replaced by a quieter one.

The second run was labelled "lower contention" on the strength of a sample taken
just before it, and its own timeline tells a more honest story: load rose during
the run because another campaign started work. It is therefore a *less*
contended window than the baseline and a *not idle* one — the comparison below is
between two loaded windows, not between load and quiet.

## 3. Where the time goes (measured)

**Suite wall 1284.3 s; process CPU 197.1 s.** The suite is idle-waiting for
roughly 85 % of its wall time. It is not CPU-bound on this host, and adding CPU
would not make it faster. What it waits for is process creation:

| Measurement | Value | Share of suite wall |
| --- | --- | --- |
| Process spawns | 8 304 | — |
| — Git invocations | **8 045** | — |
| — Python child processes | 251 | — |
| Wall time blocked in subprocess calls | **931.7 s** | **72.5 %** |
| Spawn latency (creation only) | 70.6 s | 5.5 % |

The distinction matters: only 70.6 s is the cost of *creating* processes. The
remaining ~861 s is time spent *waiting for Git to finish* once started. On a
saturated host with 229 processes and 1 984 threads, each invocation competes
for a run queue it does not own.

**Concentration.** 46 of 727 tests (6.33 %) account for 80 % of attributed wall
time. Four tests alone account for 36.2 %:

| Test | Wall | Spawns | Git | CPU |
| --- | --- | --- | --- | --- |
| `test_supervisor_s2_live…test_live_cli_gates_and_installed_source_pin_with_synthetic_image` | 128.9 s | 1 282 | 1 281 | 8.0 s |
| `test_supervisor_editing…test_live_profile_and_all_grants_using_only_synthetic_image` | 127.0 s | 975 | 971 | 7.9 s |
| `test_supervisor_editing…test_failure_scenarios_retain_and_never_replay` | 116.8 s | 719 | 704 | 15.6 s |
| `test_supervisor_s2_live…test_faults_are_durable_and_never_replay` | 91.5 s | 859 | 841 | 14.0 s |

The first test spends 125.9 s of its 128.9 s wall inside subprocess calls and
8.0 s of CPU: **98 ms per Git invocation**, of which almost none is the
interpreter's own work. At 1 281 invocations that single test pays two minutes
for process round-trips.

**Modules** (top of the ranking, by attributed wall time):

| Module | Tests | Wall | Share | CPU |
| --- | --- | --- | --- | --- |
| `test_supervisor_editing` | 12 | 380.3 s | 29.6 % | 37.9 s |
| `test_supervisor_s2_live` | 13 | 336.3 s | 26.2 % | 33.2 s |
| `test_supervisor_driver` | 33 | 115.7 s | 9.0 % | 50.6 s |
| `test_supervisor_timeouts` | 7 | 86.8 s | 6.8 % | 12.0 s |
| `test_supervisor_bridge` | 8 | 73.5 s | 5.7 % | 11.8 s |
| `test_supervisor_task_queue` | 7 | 62.5 s | 4.9 % | 5.2 s |

Five Supervisor modules hold 77.3 % of the suite. The non-Supervisor modules are
small: `test_draw_writer` 19.8 s (16 tests) and `test_calendar_multicalendar`
11.5 s (19 tests) together cost less than one Git-heavy Supervisor test.

### 3.1 The same suite in a less contended window

The second run is not a before/after: it also fixes the import defect in §5.1,
so it *discovers 72 more tests* than the baseline. It does, however, give a
second observation of the same structure under different load:

| | Baseline | Second run |
| --- | --- | --- |
| Tests discovered | 727 | **799** |
| Suite wall | 1284.3 s | 918.6 s |
| Process CPU | 197.1 s (ratio 0.154) | 136.6 s (ratio 0.149) |
| Git spawns, slowest test | 1 281 | 1 275 |
| Tests holding 80 % of wall | 46 of 727 (6.33 %) | 46 of 799 (5.76 %) |
| Top module share | 29.6 % | 28.7 % |

Three things are stable across both windows and do not depend on load:

- **The same 46 tests hold 80 % of the time.** The concentration is a property
  of the suite, not of the host.
- **Spawn counts barely move** (1 281 → 1 275 for the slowest test). Spawn count
  is a load-independent metric and the right one to compare; wall time is not.
- **The CPU ratio is unchanged** (0.154 vs 0.149). The suite waits for the same
  proportion of its time when the host is less busy; the wait shrinks but does
  not disappear.

`deskmate-test-perf compare` reports these two runs as **not comparable** —
different test counts and a 22-point CPU difference — and declines to state a
speedup. That is the intended behaviour, and the reason the 1284.3 s → 918.6 s
difference is *not* claimed as an improvement anywhere in this document. The
four slowest tests fall from 128.9/127.0/116.8/91.5 s to
100.8/92.4/74.5/69.8 s, which is consistent with less contention and with
nothing else.

### 3.2 What a process round-trip actually costs here

Bounded microbenchmarks, 8 iterations, taken at 56 % host CPU with the corrected
sampler (§5.4):

| Benchmark | median | p90 | max |
| --- | --- | --- | --- |
| `git_rev_parse` | 73.9 ms | 75.3 ms | 78.6 ms |
| `git_version` | 69.1 ms | 70.0 ms | 74.1 ms |
| `git_init` | 118.2 ms | 125.3 ms | 137.0 ms |
| `git_commit` | 214.3 ms | 321.2 ms | 374.3 ms |
| `python_startup` | 61.6 ms | 61.9 ms | 69.3 ms |
| `python_import_supervisor` | 258.8 ms | 265.7 ms | 283.7 ms |
| `file_write_4k` | 0.6 ms | 0.6 ms | 0.6 ms |
| `sqlite_create` | 14.7 ms | 42.3 ms | 196.0 ms |
| `thread_start_join` | 0.3 ms | 0.3 ms | 0.4 ms |

An earlier session at higher load measured `python_import_supervisor` at
287–500 ms and `git_rev_parse` at 80 ms; the two sessions bracket the range the
suite actually experiences.

A bare `git rev-parse` costs about 80 ms and carries almost no work; the 98 ms
per call seen inside the suite is that plus the pipes, arguments and cwd of a
real query. This is why 8 045 invocations cost 931 s: the suite is paying a
process-creation tax roughly a thousand times over, and filesystem work
(`file_write_4k`, 0.6 ms) is three orders of magnitude cheaper than a process.

The same table answers the margin question for the short handshake budgets: a
child interpreter that imports the supervisor protocol alone costs
**259 ms at 56 % CPU and up to 500 ms at higher load**, before process creation,
identity query and the two JSON round-trips of the handshake. Against a
`timeout=1` budget that is roughly 4× headroom when the host is quiet and about
2× when it is not — a margin that shrinks exactly when the suite is slowest.

### 3.3 Which Git commands dominate

`--trace-git-commands` counts the subcommand of every Git spawn. Sampled on the
two heaviest tests (1 985 calls, 197 s of the suite):

| Subcommand | Calls | Share |
| --- | --- | --- |
| `git cat-file` | 862 | 43.4 % |
| `git ls-tree` | 393 | 19.8 % |
| `git symbolic-ref` | 128 | 6.4 % |
| `git hash-object` | 111 | 5.6 % |
| `git update-index` | 111 | 5.6 % |
| `git show-ref` | 107 | 5.4 % |
| `git config` | 88 | 4.4 % |
| `git merge-base` | 56 | 2.8 % |
| `git rev-parse` | 36 | 1.8 % |
| other (13 commands) | 93 | 4.7 % |

**The top two commands are 63.2 % of all invocations and both have a batch mode**
(`cat-file --batch`, `ls-tree -r`). At the ~99 ms per call measured in these two
tests, those 1 255 calls account for roughly 124 s of their 197 s. That is an
upper bound on what batching could recover, not a prediction: a batched call
does more work per process, and some queries genuinely need their own process.
It is enough to say the bottleneck is *query shape*, not filesystem speed — and
`git config` being called 88 times shows that even trivially cacheable lookups
are being re-run.

This is where the biggest measured win sits, and it is deliberately **not**
carried in this PR: the calls are issued by `supervisor/task_git.py`, product
code in the Supervisor campaign's area, and a half-implemented batching layer in
a competing branch would be worse than a measured handoff.

## 4. Ranked bottlenecks

Ranked by measured wall time that a change could actually reclaim.

1. **Product-side Git invocation count (8 045 calls, ~931 s of waiting).**
   `supervisor/task_git.py` runs one Git process per query; `discover()` alone
   makes roughly ten to thirteen. §3.3 shows the shape of the problem:
   `cat-file` and `ls-tree` are 63 % of calls and both are batchable. This is the
   dominant cost and it is a property of the product, not the tests. Not
   addressed here — the file belongs to the Supervisor campaign's area, and a
   partial batching layer in a competing branch would be worse than this
   measured handoff.
2. **Test-side fixture construction (fixed, see §6).** The synthetic task
   repository was rebuilt with Git for every test even though it is
   byte-identical each time.
3. **Polling loops with fixed sleeps.** Several Supervisor tests wait with
   `sleep(0.02)`-style loops under an absolute deadline. Under contention those
   loops consume real seconds; their cost is a function of host responsiveness,
   not of the behaviour under test.
4. **Short handshake budgets (measured, thin).** `timeout=1` and
   `deadline=0.1`/`0.3` cases exist in `test_supervisor_driver.py` (3 sites) and
   `test_supervisor_s2_live.py` (1 site). They passed in both runs, but §3.2
   shows the child interpreter and protocol import alone consume 287–500 ms of
   a 1 000 ms budget. Headroom is therefore roughly 4× when the host is quiet
   and about 2× at 79 % CPU, and it shrinks as the host busies. This is the most likely candidate for a
   future contention-induced failure that is *not* a product defect, and the
   remedy is a stated hang guard, not a hidden deadline increase.

## 5. Defects found, classified

### 5.1 Measurement defect in this campaign's harness (fixed)

The baseline reported 6 errors. All six were
`ModuleNotFoundError: No module named 'tools'` — `test_cp290_replay`,
`test_dm_music_control`, `test_draw_comparison_audit`, `test_faxback_ocr`,
`test_lab_storage`, `test_repository_audit` import helpers from the repository's
`tools/` directory.

The cause was in `tools/test_performance.py`, not in the suite: running
`python tools/test_performance.py` places `tools/` on `sys.path` rather than the
repository root, which `python -m unittest` gets implicitly. The wrapper now
places the repository root on `sys.path` as well, with this checkout's `src`
ahead of any installed wheel. These six modules are not slow and were never
broken; they could not be imported under the harness.

This is worth recording rather than quietly fixing: a harness that fails to
import a module reports it as a test error, and a baseline accepted without
reading its failure messages would have attributed six false failures to the
code under test.

### 5.2 Test synchronization defect (independently confirmed; fixed upstream)

One genuine failure:
`test_supervisor_driver.DriverTests.test_owner_termination_leaves_permanent_fence_and_read_only_restart`
— `AssertionError: False is not true : owner never durably observed
acknowledgement`.

The defect is in the observation loop, not the deadline:

```python
while monotonic() < deadline and owner.poll() is None:
    for path in (self.directory / "evidence").glob("[0-9]*.json"):
        observed |= read_record(path)["kind"] == "turn-result"
    if observed: break
    sleep(0.02)
self.assertTrue(observed, …)
```

`owner.poll() is None` is a loop *guard*, so the moment the owner process exits
the loop ends — before the evidence directory is scanned again. The durable
record the test requires is written by the owner just before it exits, so the
last scan can precede the write by up to one poll interval and the record is
then never examined. The test loses a race with a correctly behaving
implementation, which is why it fails under contention and passes when idle.

`timeout` and `deadline` were both ample (`timeout=5, deadline=60`); raising
either would not have changed the outcome, which is why this is classified as a
test-synchronization defect rather than an inadequate deadline.

**Already fixed on PR #191.** That branch introduces an `await_evidence` helper
whose docstring names this exact failure mode — process exit is not a stop
condition for the wait, only the deadline is — and replaces this loop with it,
plus a regression test that writes the record from an already-exited process.
No competing fix is carried here: the fix belongs to that branch, a duplicate
in this one would only create a conflict on the same lines. What this campaign
adds is independent evidence that the failure is real: it occurred in **both**
full runs — once under the heavier window and once under the lighter one — in the one
module that already carries a handshake-margin comment for the same reason. Two
occurrences in two runs, including a run at materially lower load, argue against
a pure contention threshold and for a genuine ordering defect of the kind #191
corrects.

One caveat on attribution: the owner process in this test is launched with
`-I` and therefore ran the installed wheel, not this checkout (§7.1).
`driver.py`, `driver_cli.py` and `protocol.py` were verified byte-identical, so
the race analysis stands, but the failure cannot be attributed to base-revision
code by this run alone.

### 5.3 Not our defect

`test_supervisor_process_tree.ProcessTreeTests.test_a_stopped_tree_reports_no_descendants`
fails on both Linux CI configurations of PR #191. Independent review classifies
it as semantic — the implementation derives the descendant answer from the
owner's disappearance, with additional enumeration-completeness concerns. It is
an implementation correction in the Supervisor campaign's territory and is left
there; see §9 for the handoff.

### 5.4 A measurement defect found by review: inflated host CPU

An advisory review of this branch found that `GetSystemTimes` reports kernel
time **including** idle time. The sampler summed the three returned counters, so
idle was counted twice and the busy share was overstated. Checking it against
the host's own counter confirmed the finding decisively:

```
raw deltas  idle=152031250 kernel=170156250 user=10781250
pre-fix formula : 54.3 %
corrected       : 16.0 %
Windows LoadPercentage (approximate, different window): 16
```

`_windows_times` now subtracts idle from kernel time before the delta is taken,
and a regression test asserts the documented example (80 idle, 90 kernel, 10
user → 20 % busy, not 55.6 %).

This is classification §5.1 again, in a more dangerous form: a measurement
defect that produces *plausible* numbers. 82.9 % CPU on a shared VM reads as
entirely believable, and every conclusion drawn from it would have been wrong by
a third without ever looking wrong.

**Effect on the numbers in this document.** The stored reports cannot be
re-derived exactly, because the summary keeps the mean of per-sample ratios
rather than the counters. For a single interval the relation is exact:
reported `b = (kernel + user) / (idle + kernel + user)`, so the corrected share
is `(2b − 1) / b`. That is what the "corrected †" row in §2 applies, and it is an
estimate for a mean of ratios — accurate to roughly a percentage point here, and
labelled as derived rather than measured. The microbenchmarks were re-run with
the corrected sampler, so §3.2 is measured, not derived.

What does **not** change: every wall-clock figure, spawn count, Git-call count
and per-test CPU ratio, none of which use the host CPU percentage. The
`compare` guard now also refuses comparability when host CPU is missing, which
this defect showed could happen.

## 6. Measured improvement: reuse the synthetic task repository

`tests/portable/task_fixture.py` built the fixture repository with six Git
invocations for every `TaskRepo`. Every field is frozen — same empty tree, same
author and committer dates, same remote — so the result is byte-identical every
time and the work cannot change. The fixture now builds one template repository
per process and copies it per test, keeping isolation (each test owns its
directory and objects) while removing repeated process creation.

Controlled A/B on `test_supervisor_task_git`, both runs on the same host in the
same window, reverting only this file between them:

| | Before | After | Change |
| --- | --- | --- | --- |
| Module wall | 15.64 s | 12.13 s | **−22.5 %** |
| Git invocations | 154 | 136 | −18 |
| Setup time (all tests) | 3.90 s | 0.80 s | **−79 %** |
| Subprocess wall | 15.4 s | 11.7 s | −24 % |
| Outcome | 5 OK | 5 OK | unchanged |

The saving is exactly 18 Git calls: three fixtures × six calls, replaced by six
calls once. The module is 1.1 % of the suite, so the whole-suite effect is a few
seconds — real, but small. It is worth keeping because it removes a per-fixture
cost that would otherwise be paid again by every future test that builds a task
repository, not because it moves the total. The dominant cost in §4.1 is
untouched by it.

**Coordination note.** PR #191 also edits this file, raising `TaskRepo.git`'s
subprocess `timeout` from 10 s to 60 s as a hang guard rather than a latency
assertion. The rewrite here moves that call into a module-level `_run_git` with
the same 60 s bound, so the two intents agree but the hunks will collide
textually. If #191 lands first, the resolution is to keep its 60 s comment and
bound around `_run_git`; no behaviour depends on which hunk is kept first.

## 7. What is measured, and what is not

**Measured:** the spawn counts, wall and CPU splits, module shares, Pareto
concentration, the fixture A/B, the resolved module origin of child processes
(§7.1), the two failure classes in §5.1 and §5.2, and the host conditions in §2 (with §5.4's correction).

**Hypothesis, not measured:**

- That batching or caching Git queries in `supervisor/task_git.py` would reclaim
  a large share of the 931 s. §3.3 measures *which* calls dominate (63 % are
  `cat-file`/`ls-tree`, both batchable) and bounds the opportunity at ~124 s for
  two tests, but no batched implementation has been written or timed.
- That the `timeout=1` handshake sites will stay within budget. They passed in
  both runs, and §3.2 bounds the cost they must cover at 287–500 ms of a
  1 000 ms budget — a headroom estimate from components, not an end-to-end
  measurement of the handshake itself. Measuring the handshake directly would
  require replicating the test's child environment (`CODEX_HOME`, policy file,
  synthetic peer argv), which was judged a bigger fixture commitment than the
  finding warrants.
- That parallel test execution would help. The suite is idle-waiting 85 % of the
  time, which suggests it might, but process spawn cost would then be contended
  with the other campaign and the Supervisor tests bind fixed-ish resources.
  Deliberately not implemented during a concurrent campaign.

### 7.1 Which code do the child processes execute?

A measurement defect of a different kind, found while trying to time a protocol
handshake. Four spawn sites in the three slowest modules —
`test_supervisor_driver` (2), `test_supervisor_editing` (1) and
`test_supervisor_s2_live` (1), together 65 % of suite wall time — start children
as `python -I -m deskmate_formats…`. The `-I` flag ignores `PYTHONPATH`, so
those children import `deskmate_formats` from **site-packages**, not from the
checkout being measured:

```
parent (src first)  …\786ea03e\deskmate-formats\src\deskmate_formats\__init__.py
child  (python -I)  …\Python313\Lib\site-packages\deskmate_formats\__init__.py
```

On this VM the installed wheel is a **PR #191-era build**: it contains
`supervisor/process_tree.py`, `deterministic.py`, `procedures.py`,
`campaigns.py`, `scheduling.py`, `snapshot.py` and `workers.py`, none of which
exist at base revision `b5e5250`. Another campaign installed its wheel globally,
and that silently changed what every `-I` child on this host executes.

Verified for this campaign: the modules those children actually run are
byte-identical between the wheel and this checkout (`driver.py`, `driver_cli.py`,
`protocol.py`, `synthetic_peer.py`, `task_git.py`). Three differ —
`task_manifest.py` by 29 lines, `task_queue.py` by 4, `repository_audit.py` by 1
— so a test that builds a plan inside a child is not guaranteed to have
exercised base-revision code. The performance numbers in §3 are unaffected: they
are wall-clock and spawn counts, not assertions about that code.

The hazard is general and worth stating plainly: a report records the *parent's*
revision and cannot see the child's. A campaign that reinstalls the shared
package changes every other campaign's subprocess behaviour with no signal in
any report. Two remedies, neither applied here because both change test or
product code owned elsewhere: have children execute the checkout under test, or
have the harness record each child's resolved module origin.

## 8. Integration with the Supervisor and Observatory work

- **Deterministic procedure.** `deskmate-test-perf run --profile <name>` is a
  pure local command with a deterministic JSON artifact, so it fits the reviewed
  procedure model as a `fixed-script` / `reviewed-repository-code` entry whose
  report is hashed as an artifact. Its report is evidence, never an approval.
  Sketch only — the procedure registry lives on PR #191 and nothing here assumes
  its schema:

  ```json
  {"id": "portable-test-perf",
   "executes": "reviewed-repository-code",
   "network": false,
   "argv": ["python", "tools/test_performance.py", "run",
            "--profile", "portable", "--json-out", "perf/report.json"],
   "artifacts": ["perf/report.json"],
   "refuses_on": ["nonzero exit", "missing report", "report revision != planned revision"]}
  ```

  The revision refusal matters: a report whose recorded revision differs from the
  planned one describes different code, which §7.1 shows is not hypothetical.
- **Observatory projection.** The report's `host.summary` fields (CPU, available
  memory, process count) and per-module totals are the natural read-only
  projection: suite in progress, elapsed, and the expensive tests. Measured host
  values must be shown as measured and kept distinct from any inferred pressure.
- **Scheduling.** Admission should use measured host conditions plus a profile's
  measured cost class, not a fixed maximum number of concurrent suites. The
  baseline itself is the evidence: the same suite moved between 1 284 s under
  ≈79 % CPU and materially different conditions at ≈35 % CPU, so a fixed
  timeout cannot be correct for both.
- **Concurrency of the suite itself.** Because the suite is idle-waiting most of
  its wall time, running modules concurrently would raise throughput without
  adding CPU pressure — but it would add process-creation pressure, which is the
  resource actually scarce here, and the Supervisor tests bind ports and
  temporary roots. Recommended as a separate, measured experiment rather than a
  change made during a concurrent campaign.

## 9. Handoff and open questions

- **To the Supervisor campaign (PR #191):** the `test_supervisor_process_tree`
  failure is semantic and belongs there (§5.3). The
  `test_owner_termination…` race from §5.2 is already fixed on that branch, so
  nothing is carried here. The remaining overlap is the `timeout` hunk in
  `tests/portable/task_fixture.py` described in §6.
- **To whoever owns `supervisor/task_git.py`:** §3.3 is the actionable finding.
  `cat-file` (43.4 %) and `ls-tree` (19.8 %) dominate and both have batch modes;
  `config` is queried 88 times in two tests. A batched read path is where the
  measured win is, and it needs a benchmark before/after with this harness so the
  claim is measured rather than inferred from call counts.
- **Open:** how much of the 931 s a batched Git query interface would reclaim;
  the actual margin of the sub-second deadline cases; whether the venue for
  parallel execution is the harness or CI.
- **Not attempted, by design:** terminating or suspending other campaigns,
  changing VM allocation, disabling endpoint security or adding system-wide
  exclusions, exhausting the host deliberately, or merging this work.

## 10. Limitations

- The concurrent-load baseline cannot be reproduced on demand. It is preserved
  as a recorded condition, not as a target.
- CPU seconds are process-wide deltas and exclude work performed by child
  processes, so a Git-heavy test shows low CPU by construction.
- `setUpClass` and module import are not attributed to individual tests.
- The A/B covers one module. It is a controlled comparison, not a suite-wide
  before/after, and the 22.5 % figure does not generalise to the suite.
- Host sampling is 5 s by default; a burst shorter than that is visible only in
  the per-test numbers.
- Endpoint-security interference was not measured. Windows Defender was
  deliberately left unmodified.
- Child processes started with `python -I` execute the installed wheel rather
  than this checkout (§7.1). This campaign verified that the modules in question
  were byte-identical, but that verification is manual and does not generalise.
- Host CPU percentages from the two full runs are derived corrections of
  inflated figures, not direct measurements (§5.4). They are good to about a
  percentage point and should be treated as a band, not a value.
- Raw measurement files, logs and the campaign registry are retained outside
  Git; only this analysis and the harness are published.
