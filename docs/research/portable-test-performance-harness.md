# Portable test performance qualification harness

**Status:** Implemented and qualified on Windows 10 (19045), 2026-11-26  
**Module:** `deskmate_formats.perf`  
**Command:** `python tools/test_performance.py …` or `deskmate-test-perf`  
**Tests:** `tests/portable/test_perf_harness.py`

## 1. Why a dedicated harness

The portable suite runs on a shared research VM where several campaigns execute
concurrently. Under that load, a single wall-clock number for "the suite" is not
evidence: it cannot say which test was slow, whether the delay was computation
or waiting, or whether the host was saturated while it ran. The harness exists
to answer those questions reproducibly and to keep the answers comparable later.

## 2. Tool selection

| Need | Chosen approach | Why the alternatives were not used |
| --- | --- | --- |
| Per-test wall and CPU | `unittest.TestResult` subclass plus `time.perf_counter` / `time.process_time` | `cProfile` profiles Python frames only; a test blocked in `subprocess.run` shows no cost. |
| Setup/teardown split | Wrappers around `unittest.TestCase._callSetUp` / `_callTearDown` | Rewriting tests to time themselves would change them. |
| Host CPU, memory, process count | `ctypes` calls to `GlobalMemoryStatusEx`, `GetSystemTimes`, `CreateToolhelp32Snapshot` | WMI and PowerShell take hundreds of milliseconds to seconds on a loaded host and would dominate the measurement. `psutil` is not a project dependency. |
| Subprocess cost | Opt-in wrappers around `subprocess.Popen.__init__` and `subprocess.run` | Kernel-level ETW/WPR tracing is far more intrusive and needs administrator setup; it is reserved for a targeted investigation. |
| Disk latency, queue depth | Not sampled by default; use `typeperf`/PerfMon for a targeted session | `PhysicalDisk` counters require a perf-counter query that is slow and noisy at test granularity. |

Instrumentation is observation only: no test is rewritten, skipped or given a
different deadline, and `--trace-processes` changes no argument, pipe or
environment.

## 3. What a run records

Per test: identity, module, case, name, outcome, message, wall seconds, process
CPU seconds, setup seconds, teardown seconds, subprocess call count and wall
time, process spawn count and latency (total and maximum), Git call count and
time, Python spawn count, working-set before/after and an approximate peak
delta.

Per run: exact Git revision and dirty flag, interpreter identity and version,
platform, CPU count, UTF-8 mode, profile, label, repetitions, and a host
timeline sampled off the test thread (default every 5 s) with CPU, available
and total memory, commit charge, process and thread counts.

Aggregates: module totals and shares, a ranked list of the slowest tests with
cumulative share, a Pareto view (how few tests account for most of the time),
subprocess totals, and every failure with its message.

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

## 5. Commands

```
# Full portable baseline with spawn tracing
python tools/test_performance.py run --profile portable --trace-processes \
    --label "baseline" --json-out perf/base.json --md-out perf/base.md

# One module while iterating
python tools/test_performance.py run --profile focused --module test_supervisor_task_git \
    --trace-processes --print-markdown

# Bounded host microbenchmarks
python tools/test_performance.py microbench --iterations 8 \
    --json-out perf/micro.json --md-out perf/micro.md

# Before/after
python tools/test_performance.py compare --before perf/base.json \
    --after perf/after.json --print-markdown
```

`tools/test_performance.py` puts this checkout's `src` first on `sys.path`, so
a measurement describes the working tree rather than whichever wheel is
installed. Use it rather than `python -m deskmate_formats.perf.cli` when
several checkouts are active.

## 6. Comparison rules

`compare` refuses to imply a speedup when the runs are not comparable. It emits
a warning, and sets `comparable: false`, when:

- the two runs cover different test counts;
- mean host CPU differs by more than 15 percentage points;
- mean available memory differs by more than a third;
- no test appears in both runs.

Absolute durations are never a CI gate. A shared VM produces a distribution,
not a constant; a gate derived from one sample would fail for reasons unrelated
to the change. Compare distributions, and compare under stated conditions.

## 7. Limitations

- Wall time on a shared VM is only comparable when the recorded host conditions
  are comparable.
- CPU seconds are process-wide user+system deltas, so child work is excluded.
- Peak working-set delta is a process high-water mark, not a per-test maximum.
- `setUpClass` and module import are not attributed to individual tests; the
  report shows them as unattributed time.
- Subprocess tracing adds a Python-level wrapper around process creation. It is
  small but not zero; use the same flag on both sides of a comparison.
- Disk latency and queue depth are not sampled by default.
- Endpoint-security scanning is reported only where the host exposes it; a
  missing value is `null`, never zero.

## 8. Integration points

- **Supervisor deterministic procedures.** The harness is a pure local command
  with a deterministic JSON artifact, so it fits the reviewed-procedure model:
  a `portable-test-perf` procedure could run a named profile and hash its
  report as an artifact. It must not be admitted as a model task, and its
  report is evidence, not an approval.
- **Observatory.** The report's `host.summary` and per-module totals are the
  fields a read-only console could project: current CPU and memory, running
  test suite and progress, historical durations and expensive tests. Measured
  values must stay distinct from inferred resource pressure.
- **Scheduling.** Admission decisions should use the measured host conditions
  and the profile's expected cost class, not a fixed maximum number of
  concurrent suites.
