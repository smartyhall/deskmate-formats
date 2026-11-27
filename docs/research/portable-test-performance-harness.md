# Portable test performance qualification harness

**Status:** Implemented and qualified on Windows 10 (19045), 2026-11-26;
measurement-integrity corrected 2026-11-27
**Module:** `deskmate_formats.perf`
**Command:** `python -m deskmate_formats.perf …`, `deskmate-test-perf …` or
`python tools/test_performance.py …`
**Tests:** `tests/portable/test_perf_harness.py`

## 1. Why a dedicated harness

The portable suite runs on a shared research VM where several campaigns execute
concurrently. Under that load, a single wall-clock number for "the suite" is not
evidence: it cannot say which test was slow, whether the delay was computation
or waiting, or whether the host was saturated while it ran. The harness exists
to answer those questions reproducibly and to keep the answers comparable later.

Its second job is provenance. A measurement report is only usable if it says
*which* code, *which* interpreter and *what* conditions produced it, and if it
refuses a comparison when it cannot establish them. Sections 3, 6 and 9 exist
for that reason.

## 2. Tool selection

| Need | Chosen approach | Why the alternatives were not used |
| --- | --- | --- |
| Per-test wall and CPU | `unittest.TestResult` subclass plus `time.perf_counter` / `time.process_time` | `cProfile` records Python call time (a performance-counter timer in 3.13) and so is accurate for pure-Python work, but a test blocked in `subprocess.run` shows almost no call cost, and it offers no per-test attribution, spawn counting or host telemetry. |
| Setup/teardown split | Wrappers around `unittest.TestCase._callSetUp` / `_callTearDown` | Rewriting tests to time themselves would change them. |
| Host CPU, memory, process count | `ctypes` calls to `GetSystemTimes`, `GlobalMemoryStatusEx`, `GetPerformanceInfo` | WMI and PowerShell take hundreds of milliseconds to seconds on a loaded host and would dominate the measurement. `psutil` is not a project dependency. |
| Subprocess cost | Opt-in wrappers around `subprocess.Popen.__init__` and `subprocess.run` | Kernel-level ETW/WPR tracing is far more intrusive and needs administrator setup; it is reserved for a targeted investigation. |
| Disk latency, queue depth | Not sampled by default; use `typeperf`/PerfMon for a targeted session | `PhysicalDisk` counters require a perf-counter query that is slow and noisy at test granularity. |

Instrumentation is observation only: no test is rewritten, skipped or given a
different deadline, and `--trace-processes` changes no argument, pipe or
environment. The hooks are process-wide, so a second concurrent instrumented
run raises instead of silently attributing events to whichever run drains last.

## 3. What a run records

**Identity, before and after.** The checkout's revision, branch, dirty flag and
a SHA-256 digest of its uncommitted difference from `HEAD` are read both before
the suite starts and after it finishes. Each Git call's exit status is checked:
a failed `rev-parse` or `status` yields `null` (unknown), never an empty string
that would read as "clean at no revision". If the two observations differ, the
report records **no** revision and sets `source.changed`, because a tree that
moved during the run cannot be attributed to what `HEAD` said afterwards.

Untracked files are the part of that digest `git diff` cannot describe: rewriting
the bytes of an already-untracked file changes neither its pathname nor its `??`
status, so the digest stayed the same while the code under measurement changed.
The harness therefore hashes the contents of every file
`git ls-files --others --exclude-standard` names, under a fixed budget (400
files, 1 MiB per file, 8 MiB in total). A tree that exceeds the budget is
recorded as an **incomplete** identity rather than a partly hashed one, and an
incomplete identity cannot qualify a comparison. Files Git is told to ignore are
excluded: they are not part of the measured source.

**Imported package identity.** `--source` names a checkout; it does not prove
that the interpreter imported code from it. The report records the resolved
`deskmate_formats` package directory, whether it is the `src/` directory of the
named source, whether that directory is on `sys.path` and whether it comes
first, plus the installed distribution version. On this VM another campaign's
wheel sits in site-packages, so the two can differ without any visible symptom.

**Invocation.** The program name, the argument count and the argument string
with path-like tokens redacted. The raw working directory is not recorded.

**Measurement boundary.** The suite duration is instrumented execution only.
Source qualification before the run and provenance queries after it are timed
separately in `meta.timing`: `pre_source_seconds`, `pre_package_seconds`,
`execution_seconds` (the value `wall_seconds` carries), `post_source_seconds`,
and `harness_seconds` for the whole call. The finish timestamp is taken when the
last test returns and the host timeline closes, before the post-run Git queries,
so a slow `git status` cannot be reported as test time. Repeated runs sum each
phase across their iterations.

**Per test:** identity (`test_id` and the `iteration` it belongs to), module,
case, name, outcome, message, wall seconds, parent-process CPU seconds, setup
and teardown seconds, subprocess call count and duration, process-creation
count and latency (total and maximum), Git call count, Git creation latency and
Git call duration separately, Python spawn count, working-set before/after and
peak, and the peak working-set growth during the test.

**Per run:** the above identity, profile, label, repetition count, discovered
versus executed test counts, suite-level errors (see below), and a host timeline
sampled off the test thread (default every 5 s) with CPU, available and total
memory, commit charge, process and thread counts, plus whether that sampling
covered the run.

**Suite-level errors.** A module import failure or a failing `setUpClass`
reaches `unittest` with no test running. Those outcomes are kept as
`suite_errors` with their identity and message rather than dropped, so a report
cannot be "unsuccessful" without saying why. A class fixture failure also makes
the discovered-versus-executed counts disagree, which is reported as an
integrity finding rather than hidden.

With `--trace-git-commands` the harness also counts the Git *subcommand* of
every spawn, so a report can say whether time goes into `cat-file`, `ls-tree`,
`config` or plumbing writes instead of merely how many processes ran. It is off
by default because it retains a short string per spawn; it changes no argument,
pipe or environment either way.

**Counting rules that are easy to get wrong:**

- a `subprocess.run` call produces one *call* event and one *spawn* event, so
  spawns and calls are different totals, not a duplicate count;
- `spawn_seconds` is process creation only, `subprocess_seconds` is the whole
  call (creation plus child execution);
- the summed call duration adds overlapping calls together, so it is not a wall
  clock interval and not exclusive blocked time;
- the peak working-set delta is growth of a process-wide high-water mark during
  the test, measured against the high-water mark when the test started.

Aggregates: module totals and shares, a ranked list of records with cumulative
share, a Pareto view, subprocess totals, the Git command mix, every failure and
suite-level error, and an `integrity` list naming every reason the report cannot
support a qualified claim.

## 4. Profiles

| Profile | Selection | Intended use |
| --- | --- | --- |
| `portable` | `test_*.py` in `tests/portable` | Full portable verification |
| `supervisor` | `test_supervisor*.py` | Process ownership, protocol, Git fixtures |
| `observer` | `test_observer*.py` | Observer HTTP, journal, Codex child fixtures |
| `stress` | Synchronization-heavy modules, repeated 3× | Process-synchronization stress |
| `focused` | `--module` or `--test` | Single-test development loop |

`microbench` is the Windows characterisation profile; `compare` is the
before/after profile.

Repetition re-runs the same suite in one process. Cached module state, and any
process-wide fixture such as the task-repository template, therefore persists
between iterations; iteration identity is recorded so the difference is visible
instead of being averaged away.

## 5. Commands

```
# Full portable baseline with spawn tracing
python tools/test_performance.py run --profile portable --trace-processes \
    --label "baseline" --json-out perf/base.json --md-out perf/base.md

# One module while iterating, repeated twice, with a publishable copy
python tools/test_performance.py run --profile focused --module test_supervisor_task_git \
    --trace-processes --repeat 2 --json-out perf/a.json --public-out perf/a-public.json

# Which Git subcommands dominate a slow test
python tools/test_performance.py run --profile focused --test \
    test_supervisor_s2_live.LiveBridgeTests.test_live_cli_gates_and_installed_source_pin_with_synthetic_image \
    --trace-git-commands --print-markdown

# Bounded host microbenchmarks
python tools/test_performance.py microbench --iterations 8 \
    --json-out perf/micro.json --md-out perf/micro.md

# Before/after
python tools/test_performance.py compare --before perf/base.json \
    --after perf/after.json --print-markdown
```

`python -m deskmate_formats.perf …` and the `deskmate-test-perf` script reach the
same entry point as the wrapper.

`tools/test_performance.py` puts this checkout's `src` first on `sys.path`, so
a measurement describes the working tree rather than whichever wheel is
installed. Use it rather than `python -m deskmate_formats.perf` unless the
package is installed, because module invocation resolves `deskmate_formats`
from wherever Python finds it.

Invalid configuration is refused rather than defaulted: a non-positive
`--repeat`, a zero or non-finite sample interval, a non-positive microbenchmark
iteration count, an unknown benchmark name, and a discovery run that finds no
tests all exit with an error. An empty report that exits successfully looks
exactly like a measurement and is the most dangerous outcome of a typo.

## 6. Comparison rules

`compare` qualifies each dimension separately and reports its status as
`matched`, `different` or `unknown`:

| Dimension | Comparable when |
| --- | --- |
| `schema` | both reports use the same report schema version |
| `workload` | the same set of `(test_id, iteration)` identities appears in both runs |
| `repetitions` | each test recorded the same number of iterations in both runs |
| `outcomes` | every common identity has the same outcome, and the suite-level error counts agree |
| `interpreter` | same implementation and version |
| `platform` | same platform string and CPU count |
| `source` | both runs established their revision and the checkout did not change during either run |
| `package` | both runs imported `deskmate_formats` from the checkout named by `--source` |
| `instrumentation` | same tracing flags, per-test sampling and host sample interval |
| `host` | mean host CPU within 15 points, available memory within a 0.75–1.33 ratio, and complete host sampling on both sides |

Two different but *identified* revisions are allowed: measuring a change is the
point of a comparison. An unidentified revision, or a package imported from
outside the named checkout, is not.

`comparable` is true only when every dimension is `matched`. Otherwise every
per-identity delta is still reported, but `delta_label` is `observation` and the
Markdown headings say "not a speedup claim". The output also names the workload
differences, repetition changes and outcome changes explicitly, so a reader does
not have to infer them from totals.

Absolute durations are never a CI gate. A shared VM produces a distribution, not
a constant; a gate derived from one sample would fail for reasons unrelated to
the change. Compare distributions, and compare under stated conditions.

Reports written before schema version 2 carry no package identity and no
before/after source identity, so `compare` can only treat them as observations.
That is deliberate: the fields needed to qualify them were not recorded.

## 7. Reading a report honestly

| Quantity | What it is | What it is not |
| --- | --- | --- |
| `cpu_seconds` (parent) | user+system time of the harness process | the suite's total CPU demand; child processes (`git`, child interpreters) are excluded |
| `subprocess_seconds` | sum of `subprocess.run` call durations, creation plus child execution | exclusive blocked wall time; overlapping calls are added together and untimed waits are absent |
| `spawn_seconds` | process-creation latency | command execution time |
| `git_spawn_seconds` / `git_run_seconds` | creation latency / whole call duration for Git | one shared "Git time" number |
| `peak_working_set_delta` | growth of a process-wide high-water mark during the test | the memory the test itself allocated |
| `share_percent` | fraction of attributed test wall time | fraction of the process's wall time or of host CPU |
| `wall_seconds` (suite) | instrumented test execution, from the first test to the last | the whole command; source qualification before and after is excluded |
| `post_source_seconds` | provenance queries run after the suite finished | test time, or time any test spent |
| `harness_seconds` | the whole harness call, provenance included | what the tests took |

Low parent CPU therefore does not show an idle host, and a large summed call
duration does not show that the same wall time is reclaimable.

## 8. Limitations

- Wall time on a shared VM is only comparable when the recorded host conditions
  are comparable.
- CPU seconds are the parent process's user+system deltas, so child work is
  excluded.
- Subprocess durations are summed per call; concurrency inside a run makes the
  sum larger than any wall-clock interval.
- Peak working-set delta is a process high-water mark, not a per-test maximum.
- Module import happens during discovery, before the suite clock starts, so it
  is excluded from reported time. `setUpClass` time happens inside the clock but
  outside any test, and appears as unattributed time.
- Subprocess tracing adds a Python-level wrapper around process creation. It is
  small but not zero; use the same flag on both sides of a comparison.
- Host CPU comes from `GetSystemTimes`, whose kernel counter includes idle
  time; the sampler separates them before taking a delta. Getting this wrong
  overstates the busy share while still looking plausible, so the regression
  test pins the arithmetic rather than a live reading. An interval in which any
  counter moves backwards is reported as unknown instead of guessed.
- Host process and thread counts, and commit charge, come from
  `GetPerformanceInfo`, which reports host-wide values. The process-scoped
  page-file fields of `MEMORYSTATUSEX` are not used for commit headroom.
- Process memory fields the platform cannot observe are `null`; on POSIX only
  the peak is available (`ru_maxrss`, converted from KiB except on Darwin).
- Disk latency and queue depth are not sampled by default.
- Endpoint-security scanning is reported only where the host exposes it; a
  missing value is `null`, never zero.
- The suite duration excludes source qualification. A command's real cost is
  `harness_seconds`, which is larger by `pre_source_seconds`,
  `pre_package_seconds` and `post_source_seconds`.
- Untracked-file binding stops at a fixed budget. More than 400 untracked files,
  a single file above 1 MiB, or more than 8 MiB in total is recorded as an
  incomplete identity rather than a partial digest, so the bound is visible and
  such a run cannot qualify a comparison.
- Reports written before this correction included the post-run Git queries in
  `wall_seconds`. They are preserved as recorded; their suite durations are
  upper bounds by a few tenths of a second, and they are not restated as if they
  had been collected with the corrected boundary.
- Child processes started with `python -I` ignore `PYTHONPATH` and resolve the
  package from site-packages. The report records the *parent's* import origin,
  not each child's, so a measurement involving an unqualified child source
  identity is a characterization, not a fully qualified optimization result.
  [PR #206](https://github.com/smartyhall/deskmate-formats/pull/206) qualifies
  campaign-owned environments and issue #207 tracks their adoption.

## 9. Private evidence and the publication projection

A report quotes test messages, skip reasons and interpreter paths. On a shared
VM those contain account names, checkout locations, temporary directories and
exception strings. Two mechanisms keep them out of published material:

- `redact_text` replaces known private roots (the working directory, the
  checkout, the temporary root) along with anything following them, then any
  remaining drive-qualified, UNC or home-directory path. Free-text messages are
  redacted when they are recorded, so a stored report does not accumulate them.
- `public_projection` reduces a whole report to an allowlist of fields: it keeps
  every measurement, identity verdict and host sample, drops unknown metadata
  keys, replaces the interpreter path with its file name, and reduces the
  package origin to "recorded" plus the match verdict.

`run --public-out` writes that projection; `--json-out` writes the full report,
which is private evidence and is not published. Neither layer is a secret
filter: a report still needs reading before publication, but routine paths and
messages do not travel with it.

## 10. Integration points

- **Supervisor deterministic procedures.** The harness is a pure local command
  with a deterministic JSON artifact, so it fits the reviewed-procedure model:
  a `portable-test-perf` procedure could run a named profile and hash its
  report as an artifact. It must not be admitted as a model task, and its report
  is evidence, not an approval. A procedure should refuse a report whose
  `integrity` list is non-empty or whose revision is unknown.
- **Observatory.** The report's `host.summary`, `host.sampling` and per-module
  totals are the fields a read-only console could project: current CPU and
  memory, running test suite and progress, historical durations and expensive
  tests. Measured values must stay distinct from inferred resource pressure.
- **Scheduling.** Admission decisions should use the measured host conditions
  and the profile's expected cost class, not a fixed maximum number of
  concurrent suites. The measured spawn count is the load-independent quantity
  to budget with; wall time is not.
