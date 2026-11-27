# Windows portable-suite performance under concurrent laboratory load

**Status:** two full runs analysed (concurrent load, less contended); an import
defect corrected, which recovers 72 tests that never ran; a host-CPU measurement
defect found by review, corrected, and the stored figures reconciled from the
raw samples (§2, §5.4); the comparison and lifecycle defects raised by
independent review corrected with regression tests (§5.5); one genuine failure
confirmed in both runs as a race and already fixed on PR #191; the dominant
bottleneck located down to Git subcommand; a controlled fixture A/B re-measured
with identity-recording reports and qualified as comparable (§6); a
cross-campaign wheel-skew hazard documented; remaining items listed as open
**Date:** 2026-11-26 (baseline), 2026-11-27 (recovery, correction, comparison)
**Host:** Windows 10 Pro 10.0.19045, 6 vCPU, 8 GiB RAM, shared laboratory VM
**Base revision:** `b5e525002b150352a8995de1bcddfbc5dc18a838`
**Harness:** [`portable-test-performance-harness.md`](portable-test-performance-harness.md)
**Private evidence:** retained outside Git (see §11)

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
| CPU total, mean / median / max (reconstructed †) | **78.3 % / 79.0 % / 99.8 %** | **32.9 % / 27.2 % / 91.4 %** |
| CPU total, mean / max as stored before the fix ‡ | 82.9 % / 99.8 % | 60.5 % / 92.0 % |
| Available memory, mean / min | 2.8 GiB / 1.9 GiB | 3.1 GiB / 2.3 GiB |
| Processes, mean / max | 228.9 / 253 | 209.2 / 235 |
| Threads, mean | 1983.7 | 1920.9 |
| Samples (5 s interval) | 252 | 183 |

† The first instrumentation double-counted idle time (§5.4). The corrected
distribution is reconstructed from the **stored per-sample percentages**, which
are what remains of the raw counters: for a single interval the relation between
the defective reading `b` and the true busy share is `(2b − 1) / b`. Applying it
to each of the 251 and 182 samples gives the mean, median and maximum above.
Reconstructing per sample rather than converting the mean preserves the
distribution — in particular the second run's minimum of 7.8 % busy and maximum
of 91.4 %.

‡ Shown so the earlier figures are traceable rather than quietly rewritten.

**Reconciling the contradictory second-run figures.** Three numbers appeared for
the same window, and none of them is a direct measurement of host CPU:

| Figure | Where it came from | Status |
| --- | --- | --- |
| 60.5 % | mean of the stored, defective per-sample readings | reproduced exactly from the raw report; describes the defective formula, not the host |
| 35 % | the scalar correction `(2b − 1)/b` applied to that mean | a coarse estimate; correct to about 2 points |
| **32.9 %** | the same correction applied per sample, then averaged | preferred reconstruction; differs from the scalar estimate because the correction is non-linear and the mean of a ratio is not the ratio of means |

The reconstruction assumes only the documented `GetSystemTimes` semantics
(kernel time includes idle) and the 0.01-point rounding of the stored samples.
It should be read as a band of roughly ±2 points, not a value. The maximum is
unaffected by the choice — 91.4 % either way — and the baseline's mean is
78.3 % (per sample) or 79.4 % (scalar), which is within the same band.

The correction widens rather than narrows the gap between the windows: the
baseline was around 78 % busy and the second run around 33 %, not 83 % and 60 %.
Both runs are still loaded windows, and neither was idle: the second run's own
samples range from 7.8 % to 91.4 % busy, because another campaign started work
part-way through it.

The baseline was taken while other campaigns were executing on the same VM. That
workload is not reproducible on demand, so those numbers are preserved as the
recorded concurrent-load condition rather than replaced by a quieter one.

The second run was labelled "lower contention" on the strength of a sample taken
just before it, and its own timeline tells a more honest story. It is therefore
a *less* contended window than the baseline and a *not idle* one — the
comparison below is between two loaded windows, not between load and quiet.

## 3. Where the time goes (measured)

**Suite wall 1284.3 s; parent-process CPU 197.1 s.** Those are two different
quantities and only one of them is about the suite's computational demand:

| Quantity | Measured value | What it is | What it is not |
| --- | --- | --- | --- |
| Suite wall clock | 1284.3 s | elapsed time of the whole run | — |
| Parent-process CPU | 197.1 s (15.4 % of one core) | user+system time of the harness process | the suite's total CPU demand: every child process is excluded, so it says nothing about host idleness or aggregate CPU use |
| Summed `subprocess.run` call duration | 931.7 s (72.5 % of suite wall *as a sum*) | creation plus child execution, added up over 8 304 calls | exclusive blocked wall time: concurrent calls overlap and uninstrumented waits are absent |
| Summed process-creation latency | 70.6 s (5.5 %) | process creation only | command execution or round-trip cost |

| Measurement | Value |
| --- | --- |
| Process spawns | 8 304 |
| — Git invocations | **8 045** |
| — Python child processes | 251 |
| Tests holding 80 % of attributed wall time | 46 of 727 (6.33 %) |

The distinction between the two subprocess figures matters: only 70.6 s is the
cost of *creating* processes. The remaining ~861 s is child execution attributed
to timed call sites — in a test that issues its calls sequentially this is close
to its wall time, but it is still a sum over calls rather than a measured share
of exclusive waiting. What the measurement establishes is that Git process
round-trips dominate both the call count and the summed duration; it does not
establish that 72.5 % of wall time was idle-wait, nor that adding CPU would not
help.

**Concentration.** 46 of 727 tests (6.33 %) account for 80 % of attributed wall
time. Four tests alone account for 36.2 %:

| Test | Wall | Spawns | Git | CPU |
| --- | --- | --- | --- | --- |
| `test_supervisor_s2_live…test_live_cli_gates_and_installed_source_pin_with_synthetic_image` | 128.9 s | 1 282 | 1 281 | 8.0 s |
| `test_supervisor_editing…test_live_profile_and_all_grants_using_only_synthetic_image` | 127.0 s | 975 | 971 | 7.9 s |
| `test_supervisor_editing…test_failure_scenarios_retain_and_never_replay` | 116.8 s | 719 | 704 | 15.6 s |
| `test_supervisor_s2_live…test_faults_are_durable_and_never_replay` | 91.5 s | 859 | 841 | 14.0 s |

The first test's 125.9 s of summed call duration is close to its 128.9 s wall
time — consistent with it issuing those 1 281 calls one at a time — while it
spent 8.0 s of parent CPU. That is **98 ms per Git call**, of which almost none
is the interpreter's own work. At 1 281 calls that single test pays two minutes
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
| Parent-process CPU | 197.1 s (ratio 0.154) | 136.6 s (ratio 0.149) |
| Git spawns, slowest test | 1 281 | 1 275 |
| Tests holding 80 % of wall | 46 of 727 (6.33 %) | 46 of 799 (5.76 %) |
| Top module share | 29.6 % | 28.7 % |

Three things are stable across both windows and do not depend on load:

- **The same 46 tests hold 80 % of the time.** The concentration is a property
  of the suite, not of the host.
- **Spawn counts barely move** (1 281 → 1 275 for the slowest test). Spawn count
  is a load-independent metric and the right one to compare; wall time is not.
- **The parent-process CPU ratio is unchanged** (0.154 vs 0.149). That ratio
  covers only the harness process; it says that the parent's own Python work is
  a stable, small fraction of wall time, not that the suite as a whole waits for
  a fixed proportion of its time.

**The re-judged comparison.** `deskmate-test-perf compare` reports these two
runs as **not comparable**, and now says why: the runs do not share a
test/iteration identity set (six identities appear only in the first run — the
six `unittest.loader._FailedTest` import failures of §5.1 — and 78 only in the
second); mean host CPU differs by far more than the 15-point tolerance; and both
source and package identity are *unknown*, because schema-version-1 reports do
not record whether the revision was stable for the run or which package was
imported. Outcomes, interpreter, platform and instrumentation matched.

That is the intended behaviour, and the reason the 1284.3 s → 918.6 s
difference is *not* claimed as an improvement anywhere in this document. The
four slowest tests fall from 128.9/127.0/116.8/91.5 s to
100.8/92.4/74.5/69.8 s, which is consistent with less contention; every one of
those per-test deltas is labelled an observation, because the runs are not a
controlled comparison.

### 3.2 What a process round-trip actually costs here

Bounded microbenchmarks, 8 iterations, measured with the **corrected** sampler
at 55.95 % mean host CPU (median 52.18 %, max 74.53 %):

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
287–500 ms and `git_rev_parse` at 80 ms. That session's *host CPU* reading was
inflated by the defect in §5.4; its durations were not, because no duration is
derived from the CPU percentage. The two sessions bracket the range the suite
actually experiences.

A bare `git rev-parse` costs about 80 ms and carries almost no work; the 98 ms
per call seen inside the suite is that plus the pipes, arguments and cwd of a
real query. This is why 8 045 invocations cost so much: the suite is paying a
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
two heaviest tests (1 985 calls, 197 s of attributable call duration):

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
tests, those 1 255 calls account for roughly 124 s of their 197 s *if* the
per-call cost is unchanged by batching. That is an arithmetic upper bound, not a
prediction and not an observed optimization: a batched call does more work per
process, and some queries genuinely need their own process. It is enough to say
the bottleneck is *query shape*, not filesystem speed — and `git config` being
called 88 times shows that trivially cacheable lookups are being re-run.

This is where the biggest measured win sits, and it is deliberately **not**
carried in this PR: the calls are issued by `supervisor/task_git.py`, product
code in the Supervisor campaign's area, and a half-implemented batching layer in
a competing branch would be worse than a measured handoff.

## 4. Ranked bottlenecks

Ranked by measured cost that a change could plausibly reclaim.

1. **Product-side Git invocation count.** 8 045 invocations were measured
   (§3.3); their summed call duration is 931.7 s, which is an upper bound on
   attributable time, not exclusive wait. `supervisor/task_git.py` runs one Git
   process per query; `discover()` alone makes roughly ten to thirteen (derived
   from a code reading, not counted per call site). This is the dominant cost
   and it is a property of the product, not the tests. Not addressed here — the
   file belongs to the Supervisor campaign's area, and a partial batching layer
   in a competing branch would be worse than this measured handoff.
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
   and about 2× at 78 % CPU, and it shrinks as the host busies. This is the most
   likely candidate for a future contention-induced failure that is *not* a
   product defect, and the remedy is a stated hang guard, not a hidden deadline
   increase.

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
code under test. The corrected comparator now makes the same point structurally:
re-judged, the pair's workload difference is *six named `_FailedTest`
identities*, not a count.

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
full runs — once under the heavier window and once under the lighter one — in the
one module that already carries a handshake-margin comment for the same reason.
Two occurrences in two runs, including a run at materially lower load, argue
against a pure contention threshold and for a genuine ordering defect of the
kind #191 corrects.

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

**Effect on the numbers in this document.** The stored reports keep only the
per-sample *percentages*, not the counters, so the correction is reconstructed
from those percentages. For one interval the relation is exact:

```
reported  b = (idle + kernel + user) / (idle + kernel + user + idle)
corrected   = (2b − 1) / b
```

Applying that per sample gives the "reconstructed" row in §2 (baseline mean
78.3 %, second run mean 32.9 %). Applying it once to each stored mean gives
79.4 % and 34.6 %, which is what the earlier revision of this document reported
as "≈79 %" and "≈35 %"; those are coarser estimates of the same quantity, and
the per-sample figures are preferred because they preserve the distribution. The
difference between the two methods (about 1–2 points) is the uncertainty of the
reconstruction, and it is a reconstruction either way.

What does **not** change: every wall-clock figure, spawn count, Git-call count
and per-test CPU ratio, none of which use the host CPU percentage. The
microbenchmarks were re-run with the corrected sampler, so §3.2 is measured, not
derived. The `compare` guard refuses comparability when host CPU is missing,
which this defect showed could happen.

### 5.5 Comparison and lifecycle defects corrected in this checkpoint

Independent review of the harness found that it could report unlike or
insufficiently characterized runs as comparable, and that several numbers were
computed from the wrong baseline. All of the following are now fixed, with
regression tests in `tests/portable/test_perf_harness.py`:

| Defect | Effect before the correction | Correction |
| --- | --- | --- |
| `compare` keyed tests by `test_id` alone | repeated iterations collapsed to the last one, so a repeat could silently overwrite an earlier measurement | identities are `(test_id, iteration)`; missing, extra and re-counted identities are reported by name |
| Comparability was "equal counts plus some overlap" | disjoint test sets of equal size, differing outcomes and differing interpreters could all read as comparable | ten independently qualified dimensions (schema, workload, repetitions, outcomes, interpreter, platform, source, package, instrumentation, host); `comparable` requires all ten |
| Source identity read only after the run, ignoring Git exit status | a failed `git status` looked clean; drift during the run was invisible | identity read before and after, every call's status checked, digest of the uncommitted change, unknown on failure or drift |
| `--source` named metadata, not the imported package | a stale wheel could be measured while the report named the checkout | the report records the resolved package origin, whether it is the named source's `src/`, and `sys.path` position |
| `_merge` mutated the first result | the first iteration's own metadata became the whole run's, and its per-iteration fields were destroyed | a new result is built from collected records; caller-less iterations are renumbered on copies |
| Peak working set compared lifetime peak with starting *current* working set | a test was charged for every earlier test's peak; deltas were systematically too large | the delta is growth of the peak during the test, against the peak at its start |
| `addError` outside an active test was dropped | a failing `setUpClass` produced an "unsuccessful" report with no reason and no failure entry | suite-level errors are kept, counted and listed separately from test outcomes |
| Discovery and execution were not reconciled | a report could not distinguish "no tests" from "tests that never ran" | discovered, executed, suite-level errors and not-executed are reported, and an empty run is refused by the CLI |
| Non-positive repetitions and sampling intervals were defaulted or clamped | a requested interval of 0.1 s silently ran at 0.5 s while the report said 0.1 s | invalid values raise; the recorded interval is the interval used |
| `python -m deskmate_formats.perf` was documented without `__main__.py` | the advertised entry point failed | `__main__.py` added and covered by a test |
| Reports recorded the raw command line and working directory | publishing a report would publish account and checkout paths | messages redacted as recorded; invocation redacted; `--public-out` emits an allowlisted projection |
| Two instrumented runs could overlap | hooks could attribute one run's spawns to the other, or restore each other's wrappers | a second concurrent instrumented run raises |

Two further lifecycle numbers were renamed rather than corrected, because they
were measured correctly and described wrongly: `git_seconds` counted *creation
latency* and is now `git_spawn_seconds`, with `git_run_seconds` added for whole
call duration. The distinction is now stated wherever the numbers are printed.

None of these changes alters what any test asserts. The two full runs are
preserved exactly as recorded; the corrected comparator now declines to qualify
them, which is the honest verdict on them.

## 6. Measured improvement: reuse the synthetic task repository

`tests/portable/task_fixture.py` built the fixture repository with six Git
invocations for every `TaskRepo`. Every field is frozen — same empty tree, same
author and committer dates, same remote — so the result is byte-identical every
time and the work cannot change. The fixture now builds one template repository
per process and copies it per test, keeping isolation (each test owns its
directory and objects) while removing repeated process creation.

**Controlled A/B, re-measured with identity-recording reports.** Same host, same
window, only this file swapped between arms, two iterations per arm
(`--repeat 2`) so each test has an iteration identity, and `compare` qualifies
the pair as **comparable**:

| | Before (per-test rebuild) | After (template reuse) | Change |
| --- | --- | --- | --- |
| Records | 10 (5 tests × 2) | 10 (5 tests × 2) | — |
| Suite wall | 31.36 s (15.73 + 15.64) | 25.36 s (13.03 + 12.32) | **−19.1 %** |
| Git invocations | 308 (154 + 154) | 266 (136 + 130) | −42 |
| Setup time (all tests) | 5.26 s | 1.24 s | **−76.4 %** |
| Host CPU, mean / max | 76.8 % / 83.3 % | 65.2 % / 72.4 % | −11.6 points |
| Outcome | 10 success | 10 success | unchanged |

The saving is explained by the call counts, not by timing noise: three fixtures
per iteration at six calls each, replaced by six calls once per process. The
first iteration saves 18 calls (154 → 136) and the second saves 24 (154 → 130),
because the process-wide template is already built by then — a difference the
per-iteration identity makes visible instead of averaging away.

The earlier single-iteration A/B, measured before the harness recorded
identities, gave 15.64 s → 12.13 s (−22.5 %), 154 → 136 Git calls and
3.90 → 0.80 s of setup, and was reported as comparable on host CPU 58.3 % vs
60.0 %. Those numbers are preserved as recorded; the re-measured pair is the
qualified one.

**One caveat on the wall-time figure.** The after arm ran under about 12 points
less mean host CPU, inside the comparator's 15-point tolerance but not
negligible. Part of the −19 % wall saving may therefore be less contention
rather than the change. The load-independent evidence is the Git call count
(−42 calls, deterministic) and the setup time (−76 %, a direct measurement of
the removed work). The module is 1.1 % of the suite, so the whole-suite effect
is a few seconds — real, but small. It is worth keeping because it removes a
per-fixture cost that every future test that builds a task repository would pay
again, not because it moves the total. The dominant cost in §4.1 is untouched
by it.

**Isolation regression.** `tests/portable/test_task_fixture_isolation.py` proves
the premise of the change: a commit in one clone does not reach another, the
template still builds clean clones after a clone is mutated, and deleting one
clone's object store leaves the others working.

**Coordination note (resolved).** PR #191 also edited `tests/portable/task_fixture.py`,
raising `TaskRepo.git`'s subprocess `timeout` from 10 s to 60 s as a hang guard
rather than a latency assertion. #191 merged as `412835c`, and this branch
reconciled with it in an ordinary merge commit: the template-copy rewrite is
kept, and #191's 60 s bound *and its comment* now sit on the single
`subprocess.run` inside the shared `_run_git`, which therefore covers every
fixture Git call, including the config calls the base version issued directly.
`pyproject.toml` overlapped too: #191 added the deterministic/campaigns/snapshot
entry points and this branch adds `deskmate-test-perf`, so the resolution keeps
every script entry rather than choosing a side. The combined fixture is tested
explicitly: the isolation tests in `tests/portable/test_task_fixture_isolation.py`
cover clone independence and now also verify that each clone is a valid
`TrustedSource` for its own history and not for another clone's commit.

## 7. What is measured, derived, estimated and hypothesised

**Measured directly:** suite wall, parent-process CPU, spawn counts, per-test
wall and CPU, summed subprocess call durations, process-creation latency, module
shares, Pareto concentration, the Git command mix, the scored A/B above, the
resolved import origin of the parent process (§7.1), and the failing behaviours
in §5.1–§5.3. Host CPU, memory, process and thread counts are measured too, with
§2's reconstruction applied to the two stored runs.

**Derived from measured values (stated as such):** the corrected host-CPU
distribution in §2; the ~98 ms per Git call in §3 (summed call duration divided
by calls); per-call cost differences between tests.

**Arithmetic upper bound, not an observation:** the ~124 s that batching the
`cat-file`/`ls-tree` calls in two tests could touch, obtained by multiplying
their call count by the measured per-call cost and assuming that cost is
unchanged. No batched implementation exists or has been timed.

**Hypothesis, not measured:**

- That batching or caching Git queries in `supervisor/task_git.py` would reclaim
  a large share of the 931.7 s. §3.3 measures *which* calls dominate (63 % are
  `cat-file`/`ls-tree`, both batchable) and bounds the opportunity for two tests,
  but no batched implementation has been written or timed.
- That the `timeout=1` handshake sites will stay within budget. They passed in
  both runs, and §3.2 bounds the cost they must cover at 287–500 ms of a
  1 000 ms budget — a headroom estimate from components, not an end-to-end
  measurement of the handshake itself. Measuring the handshake directly would
  require replicating the test's child environment (`CODEX_HOME`, policy file,
  synthetic peer argv), which was judged a bigger fixture commitment than the
  finding warrants.
- That parallel test execution would help. The summed call duration is a large
  share of wall time, which suggests it might, but process-creation pressure —
  the actually scarce resource here — would grow, and the Supervisor tests bind
  fixed-ish resources. Deliberately not implemented during a concurrent
  campaign.
- That `discover()` in `task_git.py` makes ten to thirteen calls. That comes
  from reading the code, not from counting calls per site; the harness counts
  subcommands, not callers.

### 7.1 Which code do the processes execute?

A measurement defect of a different kind, found while trying to time a protocol
handshake. Four spawn sites in the three slowest modules —
`test_supervisor_driver` (2), `test_supervisor_editing` (1) and
`test_supervisor_s2_live` (1), together 65 % of suite wall time — start children
as `python -I -m deskmate_formats…`. The `-I` flag ignores `PYTHONPATH`, so
those children import `deskmate_formats` from **site-packages**, not from the
checkout being measured:

```
parent (src first)  …\src\deskmate_formats\__init__.py
child  (python -I)  …\Python313\Lib\site-packages\deskmate_formats\__init__.py
```

On this VM the installed wheel is a **PR #191-era build**: it contains
`supervisor/process_tree.py`, `deterministic.py`, `procedures.py`,
`campaigns.py`, `scheduling.py`, `snapshot.py` and `workers.py`, none of which
exist at base revision `b5e5250`. Another campaign installed its wheel globally,
and that silently changed what every `-I` child on this host executes. It does
not even contain this campaign's `perf` package, which is how the skew surfaced:
`python -c "import deskmate_formats.perf.runner"` fails against the installed
wheel and succeeds with this checkout's `src/` first.

Verified for this campaign: the modules those children actually run are
byte-identical between the wheel and this checkout (`driver.py`, `driver_cli.py`,
`protocol.py`, `synthetic_peer.py`, `task_git.py`). Three differ —
`task_manifest.py` by 29 lines, `task_queue.py` by 4, `repository_audit.py` by 1
— so a test that builds a plan inside a child is not guaranteed to have
exercised base-revision code. The performance numbers in §3 are unaffected: they
are wall-clock and spawn counts, not assertions about that code.

The harness now records the *parent's* resolved package origin and whether it is
the named checkout, and `compare` refuses to qualify a run whose package came
from elsewhere. It still cannot see each child's origin; per-spawn child
identity, campaign-owned interpreters and preflight receipts were recorded by
issue #201, implemented by
[PR #206](https://github.com/smartyhall/deskmate-formats/pull/206) and tracked for
adoption in issue #207. Two remedies remain open, neither applied here because
both change test or product code owned elsewhere: have children execute the
checkout under test, or have the harness observe each child's resolved module
origin. Until one of them lands, a measurement whose child source identity is
unqualified is a characterization of this host, not a fully qualified
optimization result.

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
   "refuses_on": ["nonzero exit", "missing report",
                  "report integrity findings non-empty",
                  "report revision != planned revision"]}
  ```

  The revision refusal matters: a report whose recorded revision differs from the
  planned one describes different code, which §7.1 shows is not hypothetical.
- **Observatory projection.** The report's `host.summary`, `host.sampling` and
  per-module totals are the natural read-only projection: suite in progress,
  elapsed, and the expensive tests. Measured host values must be shown as
  measured and kept distinct from any inferred pressure.
- **Scheduling.** Admission should use measured host conditions plus a profile's
  measured cost class, not a fixed maximum number of concurrent suites. The
  baseline itself is the evidence: the same suite moved between 1 284 s under
  ≈78 % CPU and materially different conditions at ≈33 % CPU, so a fixed timeout
  cannot be correct for both.
- **Concurrency of the suite itself.** Because a large share of wall time is
  spent inside subprocess calls, running modules concurrently would raise
  throughput without adding parent CPU — but it would add process-creation
  pressure, which is the resource actually scarce here, and the Supervisor tests
  bind ports and temporary roots. Recommended as a separate, measured experiment
  rather than a change made during a concurrent campaign.

## 9. Handoff and open questions

- **To the Supervisor campaign (PR #191, merged `412835c`):** the
  `test_supervisor_process_tree` failure is semantic and belongs there (§5.3).
  The `test_owner_termination…` race from §5.2 is already fixed there, so
  nothing is carried here. The `timeout` hunk in `tests/portable/task_fixture.py`
  and the script table in `pyproject.toml` were resolved as described in §6.
  `tests/portable/test_task_fixture_isolation.py` survived the merge and was
extended to cover `TrustedSource` verification of each clone.
- **To whoever owns `supervisor/task_git.py`:** §3.3 is the actionable finding.
  `cat-file` (43.4 %) and `ls-tree` (19.8 %) dominate and both have batch modes;
  `config` is queried 88 times in two tests. A batched read path is where the
  measured win is. Precondition for implementing it, in order: #191 and this
  branch integrated; campaign-owned interpreter environments (#201) so a
  measurement cannot silently describe another campaign's wheel; and a
  qualified quiet-host baseline from this harness. Then implement batching with
  a before/after comparison that names the call counts, so the claim is measured
  rather than inferred from call counts.
- **Issues #201 and #207, PR #206:** the wheel skew in §7.1 is the
  cross-campaign environment contamination #201 records. The harness detects an
  imported package that is not the named source, which is a detection, not an
  isolation mechanism. #206 qualifies campaign-owned environments and source
  identity; #207 tracks their adoption in production procedures. Nothing in this
  branch duplicates that implementation or claims its result.
- **Open:** how much of the summed call duration a batched Git query interface
  would reclaim; the actual margin of the sub-second deadline cases; whether the
  venue for parallel execution is the harness or CI; and whether the six
  `_FailedTest` identities that the baseline recorded indicate anything beyond
  the `sys.path` defect in §5.1 (they do not, on inspection).
- **Not attempted, by design:** terminating or suspending other campaigns,
  changing VM allocation, disabling endpoint security or adding system-wide
  exclusions, exhausting the host deliberately, or merging this work.

## 10. Limitations

- The concurrent-load baseline cannot be reproduced on demand. It is preserved
  as a recorded condition, not as a target.
- Host CPU percentages for the two full runs are reconstructions from stored
  per-sample percentages, not direct measurements, and should be read as a band
  of roughly ±2 points (§2, §5.4).
- The suite durations in §3 and §6 were recorded before the measurement boundary
  was corrected, so each includes the post-run Git identity queries (four calls,
  well under a second) that the harness now times as `post_source_seconds`. They
  are preserved as recorded and are upper bounds on instrumented execution; they
  are not restated as if collected with the corrected boundary.
- Source identity for those runs binds tracked changes and, since this
  correction, untracked file contents. Reports written before the correction
  carry no untracked digest, so `compare` reports their source dimension as
  unknown rather than assuming it.
- CPU seconds are parent-process deltas and exclude work performed by child
  processes, so a Git-heavy test shows low CPU by construction. The 931.7 s
  figure is a sum of call durations, not exclusive blocked time, and not a
  predicted saving.
- `setUpClass` and module import are not attributed to individual tests; import
  time falls before the suite clock and is excluded rather than unattributed.
- The A/B covers one module and one pair of runs. It is a controlled comparison,
  not a suite-wide before/after, and the −19 % figure does not generalise to the
  suite. Its two arms differ by about 12 points of host CPU, so part of the wall
  difference may be contention.
- Host sampling is 5 s by default; a burst shorter than that is visible only in
  the per-test numbers.
- Endpoint-security interference was not measured. Windows Defender was
  deliberately left unmodified.
- Child processes started with `python -I` execute the installed wheel rather
  than this checkout (§7.1). The harness detects a mismatched *parent* import
  origin, but not a child's; the module-by-module comparison above is manual and
  does not generalise.
- The two full runs predate the harness recording before/after source identity
  and package origin, so the corrected comparator can only describe them as
  observations. They are preserved rather than re-run: another expensive
  baseline was explicitly not authorized for this checkpoint.

## 11. Evidence, privacy and reproduction

Raw run reports, microbenchmark JSON, the re-judged comparison, the A/B arms,
logs and the campaign registry are retained outside Git. Only this analysis and
the harness are published.

A stored report is not automatically publishable: it contains test messages,
invocation arguments and interpreter paths. `run --public-out` writes the
sanitized projection — allowlisted metadata, redacted messages, the interpreter
reduced to its file name and the package origin reduced to a match verdict —
which is the form intended for sharing. The projection keeps every measurement
and every host sample, so it remains independently checkable.

Reproduction, on this host, from the repository root:

```
python tools/test_performance.py run --profile portable --trace-processes \
    --trace-git-commands --label "baseline" \
    --json-out <private>/run.json --md-out <private>/run.md

python tools/test_performance.py microbench --iterations 8 \
    --json-out <private>/micro.json

python tools/test_performance.py compare --before <private>/a.json \
    --after <private>/b.json --print-markdown
```

The comparison refuses to qualify the result unless both runs record their
revision, their imported package, their instrumentation and their host
conditions; reproduce under the conditions you intend to claim.
