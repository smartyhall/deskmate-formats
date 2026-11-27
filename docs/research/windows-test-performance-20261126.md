# Windows portable-suite performance under concurrent laboratory load

**Status:** baseline recovered and analysed; one measurement defect corrected,
one test-synchronization defect confirmed (fixed on PR #191, not duplicated
here); remaining items listed as open
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

| | Baseline (concurrent load) | Recovery window (lower contention) |
| --- | --- | --- |
| Window (UTC) | 2026-11-26 09:29:02 – 09:50:27 | 2026-11-27 02:25:58 – 02:26:06 (sample) |
| CPU total, mean / max | **82.9 % / 99.8 %** | **50.5 % / 51.3 %** |
| Available memory, mean | 2.8 GiB (min 1.9 GiB) | 3.25 GiB |
| Processes, mean / max | 228.9 / 253 | 207 |
| Threads, mean | 1983.7 | 1932 |
| Samples | 252 (5 s interval) | 9 (1 s interval) |

The baseline was taken while other campaigns were executing on the same VM. That
workload is not reproducible on demand, so those numbers are preserved as the
recorded concurrent-load condition rather than replaced by a quieter one.

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

## 4. Ranked bottlenecks

Ranked by measured wall time that a change could actually reclaim.

1. **Product-side Git invocation count (8 045 calls, ~931 s of waiting).**
   `supervisor/task_git.py` runs one Git process per query; `discover()` alone
   makes roughly ten to thirteen. This is the dominant cost and it is a property
   of the product, not the tests. Not addressed here — PR #191 owns this file,
   and duplicating a refactor would collide with the Supervisor campaign.
2. **Test-side fixture construction (fixed, see §6).** The synthetic task
   repository was rebuilt with Git for every test even though it is
   byte-identical each time.
3. **Polling loops with fixed sleeps.** Several Supervisor tests wait with
   `sleep(0.02)`-style loops under an absolute deadline. Under contention those
   loops consume real seconds; their cost is a function of host responsiveness,
   not of the behaviour under test.
4. **Short absolute deadlines (open question).** `timeout=1, deadline=0.1` and
   `timeout=5, deadline=0.3` cases exist in `test_supervisor_driver.py` and
   `test_supervisor_s2_live.py`. They passed in the baseline, but no margin
   measurement has been made, so their headroom is unknown rather than proven.

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
adds is independent evidence that the failure is real and reproducible under
contention (one occurrence in 727 tests at 83 % CPU, in the one module that
already carries a handshake-margin comment for the same reason).

### 5.3 Not our defect

`test_supervisor_process_tree.ProcessTreeTests.test_a_stopped_tree_reports_no_descendants`
fails on both Linux CI configurations of PR #191. Independent review classifies
it as semantic — the implementation derives the descendant answer from the
owner's disappearance, with additional enumeration-completeness concerns. It is
an implementation correction in the Supervisor campaign's territory and is left
there; see §9 for the handoff.

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
concentration, the fixture A/B, the two failure classes in §5.1 and §5.2, and
the host conditions in §2.

**Hypothesis, not measured:**

- That batching or caching Git queries in `supervisor/task_git.py` would reclaim
  most of the 931 s. The call counts support it; no alternative implementation
  has been written or timed, and the saving depends on how many distinct queries
  the tests issue.
- That the `timeout=1, deadline=0.1` cases have adequate margin. They passed
  once under 83 % CPU; one pass is not a margin measurement.
- That parallel test execution would help. The suite is idle-waiting 85 % of the
  time, which suggests it might, but process spawn cost would then be contended
  with the other campaign and the Supervisor tests bind fixed-ish resources.
  Deliberately not implemented during a concurrent campaign.

## 8. Integration with the Supervisor and Observatory work

- **Deterministic procedure.** `deskmate-test-perf run --profile <name>` is a
  pure local command with a deterministic JSON artifact, so it fits the reviewed
  procedure model as a `fixed-script` / `reviewed-repository-code` entry whose
  report is hashed as an artifact. Its report is evidence, never an approval.
- **Observatory projection.** The report's `host.summary` fields (CPU, available
  memory, process count) and per-module totals are the natural read-only
  projection: suite in progress, elapsed, and the expensive tests. Measured host
  values must be shown as measured and kept distinct from any inferred pressure.
- **Scheduling.** Admission should use measured host conditions plus a profile's
  measured cost class, not a fixed maximum number of concurrent suites. The
  baseline itself is the evidence: the same suite moved between 1 284 s under
  83 % CPU and materially different conditions at 50 % CPU, so a fixed timeout
  cannot be correct for both.

## 9. Handoff and open questions

- **To the Supervisor campaign (PR #191):** the `test_supervisor_process_tree`
  failure is semantic and belongs there (§5.3). The
  `test_owner_termination…` race from §5.2 is already fixed on that branch, so
  nothing is carried here. The remaining overlap is the `timeout` hunk in
  `tests/portable/task_fixture.py` described in §6.
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
- Raw measurement files, logs and the campaign registry are retained outside
  Git; only this analysis and the harness are published.
