"""Aggregation, ranking and before/after comparison of qualification reports.

Two rules govern this module:

* an aggregate is only as good as its identity.  A report records tests by
  ``(test_id, iteration)`` because the runner can execute the same test several
  times, and collapsing those records would silently drop measurements;
* a comparison either states that the two runs are like-for-like and
  sufficiently characterized, or it labels every delta an observation.  There
  is no third state in which a convenient number is called an improvement.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


SCHEMA_VERSION = 1
COMPARISON_SCHEMA_VERSION = 1

#: Mean host CPU difference, in percentage points, above which two runs were
#: taken under materially different load.
CPU_POINT_TOLERANCE = 15.0
#: Available-memory ratio outside which paging behaviour may differ.
MEMORY_RATIO = (0.75, 1.33)

LIMITATIONS = (
    "Wall-clock durations were observed on a shared laboratory VM; they are "
    "comparable only when host conditions are comparable.",
    "Per-test CPU seconds are the parent process's user+system time deltas. "
    "Work performed by child processes is excluded, so low parent CPU does not "
    "mean the host was idle or that the suite is not CPU-bound overall.",
    "Summed subprocess durations add up call durations: concurrent calls "
    "overlap in wall time and uninstrumented waits are excluded, so the sum is "
    "neither exclusive blocked time nor a reclaimable saving.",
    "Peak working-set delta is growth of a process-wide high-water mark during "
    "the test, not the memory the test itself allocated.",
    "Module import happens during discovery, before the suite clock starts; "
    "setUpClass time appears as unattributed time.",
)

_STATUS_ORDER = {"matched": 0, "unknown": 1, "different": 2}
_DIMENSIONS = ("schema", "workload", "repetitions", "outcomes", "interpreter",
               "platform", "source", "package", "instrumentation", "host")


def _share(part: float, whole: float) -> float:
    return round(100.0 * part / whole, 2) if whole > 0 else 0.0


def _outcome_is_failure(outcome: str) -> bool:
    return outcome in ("failure", "error", "unexpected-success")


def _identity(test: dict[str, Any]) -> tuple[str, int]:
    """The identity the runner recorded: a test id *and* its iteration."""
    identifier = str(test.get("test_id") or "<unknown>")
    try:
        iteration = int(test.get("iteration") or 0)
    except (TypeError, ValueError):
        iteration = 0
    return identifier, iteration


def _identity_key(identity: tuple[str, int]) -> str:
    return f"{identity[0]}#{identity[1]}"


def _case_module(identifier: str) -> str:
    parts = identifier.split(".")
    return ".".join(parts[:-2]) if len(parts) > 2 else ""


def summarize(report: dict[str, Any], *, top: int = 25, pareto_target: float = 0.8) -> dict[str, Any]:
    """Derive module totals, ranked tests and a Pareto view from a run report."""
    tests: list[dict[str, Any]] = list(report.get("tests", ()))
    meta = report.get("meta") or {}
    suite_errors = list(report.get("suite_errors") or ())
    identities = [_identity(test) for test in tests]
    identity_keys = [_identity_key(identity) for identity in identities]

    total_wall = sum(float(test.get("wall_seconds") or 0.0) for test in tests)
    total_cpu = sum(float(test.get("cpu_seconds") or 0.0) for test in tests)
    suite_wall = float(meta.get("wall_seconds") or 0.0)
    failures = [test for test in tests if _outcome_is_failure(test.get("outcome", ""))]

    modules: dict[str, dict[str, Any]] = {}
    for test in tests:
        module = test.get("module") or "<unknown>"
        entry = modules.setdefault(module, {
            "module": module, "tests": 0, "wall_seconds": 0.0, "cpu_seconds": 0.0,
            "failures": 0, "spawn_count": 0, "git_calls": 0, "subprocess_seconds": 0.0,
        })
        entry["tests"] += 1
        entry["wall_seconds"] += float(test.get("wall_seconds") or 0.0)
        entry["cpu_seconds"] += float(test.get("cpu_seconds") or 0.0)
        entry["spawn_count"] += int(test.get("spawn_count") or 0)
        entry["git_calls"] += int(test.get("git_calls") or 0)
        entry["subprocess_seconds"] += float(test.get("subprocess_seconds") or 0.0)
        if _outcome_is_failure(test.get("outcome", "")):
            entry["failures"] += 1

    ordered_modules = sorted(modules.values(), key=lambda item: item["wall_seconds"], reverse=True)
    for entry in ordered_modules:
        # Share comes from the unrounded total; rounding is for display only.
        share = _share(entry["wall_seconds"], total_wall)
        entry["wall_seconds"] = round(entry["wall_seconds"], 3)
        entry["cpu_seconds"] = round(entry["cpu_seconds"], 3)
        entry["subprocess_seconds"] = round(entry["subprocess_seconds"], 3)
        entry["share_percent"] = share

    ranked = sorted(tests, key=lambda test: float(test.get("wall_seconds") or 0.0), reverse=True)
    ranking: list[dict[str, Any]] = []
    cumulative = 0.0
    for position, test in enumerate(ranked[:top], start=1):
        duration = float(test.get("wall_seconds") or 0.0)
        cumulative += duration
        ranking.append({
            "rank": position,
            "test_id": test.get("test_id"),
            "iteration": _identity(test)[1],
            "module": test.get("module"),
            "outcome": test.get("outcome"),
            "wall_seconds": round(duration, 3),
            "cpu_seconds": round(float(test.get("cpu_seconds") or 0.0), 3),
            "setup_seconds": round(float(test.get("setup_seconds") or 0.0), 3),
            "teardown_seconds": round(float(test.get("teardown_seconds") or 0.0), 3),
            "share_percent": _share(duration, total_wall),
            "cumulative_percent": _share(cumulative, total_wall),
            "spawn_count": int(test.get("spawn_count") or 0),
            "git_calls": int(test.get("git_calls") or 0),
            "subprocess_seconds": round(float(test.get("subprocess_seconds") or 0.0), 3),
        })

    target_seconds = pareto_target * total_wall
    running = 0.0
    tests_for_target = 0
    for test in ranked:
        running += float(test.get("wall_seconds") or 0.0)
        tests_for_target += 1
        if running >= target_seconds:
            break

    spawns = sum(int(test.get("spawn_count") or 0) for test in tests)
    git_calls = sum(int(test.get("git_calls") or 0) for test in tests)
    python_spawns = sum(int(test.get("python_spawns") or 0) for test in tests)
    subprocess_seconds = sum(float(test.get("subprocess_seconds") or 0.0) for test in tests)
    spawn_seconds = sum(float(test.get("spawn_seconds") or 0.0) for test in tests)
    git_spawn_seconds = sum(float(test.get("git_spawn_seconds") or 0.0) for test in tests)
    git_run_seconds = sum(float(test.get("git_run_seconds") or 0.0) for test in tests)
    traced = bool(meta.get("trace_processes") or meta.get("trace_git_commands"))
    command_counts: dict[str, int] = {}
    for test in tests:
        for command, count in (test.get("git_commands") or {}).items():
            command_counts[command] = command_counts.get(command, 0) + int(count)
    git_commands = [{"command": command, "calls": count}
                    for command, count in sorted(command_counts.items(),
                                                 key=lambda item: (-item[1], item[0]))]

    discovered = meta.get("discovered_tests")
    executed = len(tests)
    duplicates = sorted(
        {key for key, count in Counter(identity_keys).items() if count > 1}
    )
    not_executed = None
    if isinstance(discovered, int):
        not_executed = max(0, discovered - executed - len(suite_errors))

    summary_failures = [
        {
            "scope": "test",
            "test_id": test.get("test_id"),
            "iteration": _identity(test)[1],
            "outcome": test.get("outcome"),
            "message": test.get("message"),
            "wall_seconds": round(float(test.get("wall_seconds") or 0.0), 3),
        }
        for test in failures
    ] + [
        {
            "scope": "suite",
            "test_id": issue.get("test_id"),
            "iteration": None,
            "outcome": issue.get("outcome") or "error",
            "message": issue.get("message"),
            "wall_seconds": None,
        }
        for issue in suite_errors
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "meta": meta,
        "environment": report.get("environment", {}),
        "host": (report.get("host") or {}).get("summary", {}),
        "host_sampling": (report.get("host") or {}).get("sampling"),
        "totals": {
            "tests": len(tests),
            "distinct_tests": len({identifier for identifier, _ in identities}),
            "iterations": meta.get("iterations") or 1,
            "discovered_tests": discovered,
            "executed_tests": executed,
            "suite_errors": len(suite_errors),
            "not_executed": not_executed,
            "outcomes": meta.get("outcomes", {}),
            "failures": len(failures) + len(suite_errors),
            "attributed_wall_seconds": round(total_wall, 3),
            "suite_wall_seconds": round(suite_wall, 3),
            "unattributed_seconds": round(max(0.0, suite_wall - total_wall), 3),
            "cpu_seconds": round(total_cpu, 3),
            "cpu_ratio": round(total_cpu / total_wall, 3) if total_wall > 0 else None,
            "mean_test_seconds": round(total_wall / len(tests), 4) if tests else None,
        },
        "subprocess": {
            "traced": traced,
            "spawns": spawns,
            "git_calls": git_calls,
            "python_spawns": python_spawns,
            "wall_seconds": round(subprocess_seconds, 3),
            "spawn_seconds": round(spawn_seconds, 3),
            "git_spawn_seconds": round(git_spawn_seconds, 3),
            "git_run_seconds": round(git_run_seconds, 3),
        },
        "git_commands": git_commands,
        "modules": ordered_modules,
        "ranking": ranking,
        "pareto": {
            "target": pareto_target,
            "tests_for_target": tests_for_target,
            "tests_total": len(tests),
            "tests_share_percent": _share(tests_for_target, len(tests)),
            "seconds_for_target": round(running, 3),
        },
        "failures": summary_failures,
        "integrity": _integrity(report, duplicates=duplicates),
        "limitations": list(LIMITATIONS),
    }


def _integrity(report: dict[str, Any], *, duplicates: list[str]) -> list[dict[str, Any]]:
    """Every reason this report cannot support a qualified claim."""
    meta = report.get("meta") or {}
    host = report.get("host") or {}
    summary = host.get("summary") or {}
    sampling = host.get("sampling") or {}
    package = meta.get("package") or {}
    issues: list[dict[str, Any]] = []

    def note(kind: str, detail: str) -> None:
        issues.append({"kind": kind, "detail": detail})

    source = meta.get("source") or {}
    if source.get("revision") is None:
        note("source-identity",
             "the revision this run measured was not established"
             + (" (the checkout changed while the suite ran)" if meta.get("source_changed")
                else " (a Git metadata command failed)"))
    if meta.get("source_changed"):
        note("source-drift", "the checkout was not identical before and after the run")
    if package:
        if package.get("matches_source") is False:
            note("package-mismatch",
                 "the imported deskmate_formats package is not the checkout named by --source")
        elif package.get("origin") is None:
            note("package-unknown", "the imported package origin was not recorded")
    else:
        note("package-unknown", "the report records no package identity")
    discovered = meta.get("discovered_tests")
    executed = len(report.get("tests") or ())
    suite_errors = len(report.get("suite_errors") or ())
    if duplicates:
        note("duplicate-identity",
             f"{len(duplicates)} test/iteration identities appear more than once"
             f" (e.g. {duplicates[0]})")
    if executed == 0:
        note("empty-run", "no test produced a measurement")
    if isinstance(discovered, int) and executed + suite_errors < discovered:
        note("not-executed",
             f"{discovered - executed - suite_errors} of {discovered} discovered tests produced"
             " no record (a class or module fixture may have failed)")
    cpu = (summary.get("cpu_total_percent") or {}).get("mean")
    if cpu is None:
        note("host-cpu-missing", "host CPU was not observed, so load cannot be characterized")
    if sampling and sampling.get("complete") is False:
        note("host-sampling-incomplete",
             "the host timeline covers less than its sampling interval implies"
             + (f" ({sampling.get('error')})" if sampling.get("error") else ""))
    elif not sampling:
        note("host-sampling-unknown", "the report records no host sampling coverage")
    return issues


def _format_seconds(value: float | None) -> str:
    if value is None:
        return "n/a"
    # A negative delta is a reduction; rendering it in milliseconds because it
    # is "less than one" would misread a 47-second saving as 47 ms.
    if abs(value) < 1.0:
        return f"{value * 1000:.0f} ms"
    return f"{value:.1f} s"


def _format_bytes(value: float | None) -> str:
    if value is None:
        return "n/a"
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(value) < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} TiB"


def _describe_identity(meta: dict[str, Any]) -> str:
    source = meta.get("source") or {}
    revision = source.get("revision")
    state = source.get("state") or ("unknown" if revision is None else "stable")
    if revision is None:
        return f"unidentified revision ({state})"
    return f"`{str(revision)[:12]}` ({state}, dirty={source.get('dirty')})"


def to_markdown(summary: dict[str, Any]) -> str:
    """Human-readable qualification summary."""
    meta = summary.get("meta", {})
    environment = summary.get("environment", {})
    host = summary.get("host", {})
    sampling = summary.get("host_sampling") or {}
    totals = summary.get("totals", {})
    cpu = host.get("cpu_total_percent", {})
    memory = host.get("memory_available_bytes", {})
    package = meta.get("package") or {}

    lines = [
        "# Portable test performance qualification",
        "",
        f"- Profile: `{meta.get('profile') or 'unspecified'}`"
        f" (label: {meta.get('label') or 'none'})",
        f"- Started: {meta.get('started_utc')}  Finished: {meta.get('finished_utc')}",
        f"- Revision: {_describe_identity(meta)}",
        f"- Imported package: {package.get('name') or 'unknown'}"
        f" version {package.get('version') or 'unknown'}"
        f" (matches the named source: {package.get('matches_source')})",
        f"- Python: {environment.get('python_implementation')}"
        f" {environment.get('python_version')}",
        f"- Platform: {environment.get('platform')} ({environment.get('cpu_count')} CPUs)",
        f"- Tests: {totals.get('tests')} records over"
        f" {totals.get('distinct_tests')} tests -> {totals.get('outcomes')}",
        f"- Discovery: {totals.get('discovered_tests')} discovered,"
        f" {totals.get('executed_tests')} executed,"
        f" {totals.get('suite_errors')} suite-level errors,"
        f" {totals.get('not_executed')} without a record",
        f"- Suite wall: {_format_seconds(totals.get('suite_wall_seconds'))}"
        f" (attributed {_format_seconds(totals.get('attributed_wall_seconds'))},"
        f" unattributed {_format_seconds(totals.get('unattributed_seconds'))})",
        f"- Parent-process CPU: {_format_seconds(totals.get('cpu_seconds'))}"
        f" (ratio {totals.get('cpu_ratio')}; child processes excluded)",
        "",
        "## Host conditions during the run",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Samples | {host.get('samples')} (complete: {sampling.get('complete')}) |",
        f"| CPU total % (mean / median / max) | {cpu.get('mean')} / {cpu.get('median')} / {cpu.get('max')} |",
        f"| Available memory (mean / min) | {_format_bytes(memory.get('mean'))} / {_format_bytes(memory.get('min'))} |",
        f"| Total memory | {_format_bytes(host.get('memory_total_bytes'))} |",
        f"| Processes (mean / max) | {(host.get('process_count') or {}).get('mean')}"
        f" / {(host.get('process_count') or {}).get('max')} |",
        f"| Threads (mean / max) | {(host.get('thread_count') or {}).get('mean')}"
        f" / {(host.get('thread_count') or {}).get('max')} |",
        "",
        "## Slowest modules",
        "",
        "| Module | Tests | Wall | Share | CPU | Failures |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for module in summary.get("modules", [])[:15]:
        lines.append(
            f"| `{module['module']}` | {module['tests']} | {_format_seconds(module['wall_seconds'])}"
            f" | {module['share_percent']}% | {_format_seconds(module['cpu_seconds'])}"
            f" | {module['failures']} |"
        )

    pareto = summary.get("pareto", {})
    lines += [
        "",
        "## Pareto concentration",
        "",
        f"{pareto.get('tests_for_target')} of {pareto.get('tests_total')} records"
        f" ({pareto.get('tests_share_percent')}%) account for"
        f" {int(float(pareto.get('target', 0)) * 100)}% of attributed wall time"
        f" ({_format_seconds(pareto.get('seconds_for_target'))}).",
        "",
        "## Slowest individual records",
        "",
        "| # | Test | Iter | Outcome | Wall | Share | Cum. | CPU | Spawns | Git |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in summary.get("ranking", []):
        lines.append(
            f"| {entry['rank']} | `{entry['test_id']}` | {entry.get('iteration', 0)}"
            f" | {entry['outcome']}"
            f" | {_format_seconds(entry['wall_seconds'])} | {entry['share_percent']}%"
            f" | {entry['cumulative_percent']}% | {_format_seconds(entry['cpu_seconds'])}"
            f" | {entry['spawn_count']} | {entry['git_calls']} |"
        )

    subprocess = summary.get("subprocess", {})
    lines += [
        "",
        "## Subprocess activity",
        "",
        f"- Traced: {subprocess.get('traced')}",
        f"- Spawns: {subprocess.get('spawns')} (Git {subprocess.get('git_calls')},"
        f" Python {subprocess.get('python_spawns')})",
        f"- Summed process-creation latency: {_format_seconds(subprocess.get('spawn_seconds'))}",
        f"- Summed `subprocess.run` call duration"
        f" (creation plus child execution, overlapping calls counted once each):"
        f" {_format_seconds(subprocess.get('wall_seconds'))}",
        f"- Git creation latency: {_format_seconds(subprocess.get('git_spawn_seconds'))};"
        f" Git call duration: {_format_seconds(subprocess.get('git_run_seconds'))}",
    ]

    if summary.get("git_commands"):
        lines += ["", "## Git command mix", "",
                  "| Subcommand | Calls |", "| --- | --- |"]
        for entry in summary["git_commands"][:15]:
            lines.append(f"| `git {entry['command']}` | {entry['calls']} |")

    if summary.get("integrity"):
        lines += ["", "## Integrity", ""]
        for issue in summary["integrity"]:
            lines.append(f"- **{issue['kind']}**: {issue['detail']}")

    if summary.get("failures"):
        lines += ["", "## Failures", ""]
        for failure in summary["failures"]:
            scope = "suite" if failure.get("scope") == "suite" else "test"
            iteration = "" if failure.get("iteration") in (None, 0) else \
                f" iteration {failure['iteration']}"
            duration = _format_seconds(failure.get("wall_seconds"))
            lines.append(
                f"- `{failure['test_id']}`{iteration} ({scope} {failure['outcome']},"
                f" {duration}): {failure['message']}"
            )

    lines += ["", "## Limitations", ""]
    lines += [f"- {item}" for item in summary.get("limitations", [])]
    lines.append("")
    return "\n".join(lines)


def _labels(labels: list[str]) -> str:
    """Join ``['earlier', 'later']`` as prose rather than as a CSV fragment."""
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + " and " + labels[-1]


def _run_identity(report: dict[str, Any]) -> dict[str, Any]:
    meta = report.get("meta") or {}
    environment = report.get("environment") or {}
    source = meta.get("source") or {}
    package = meta.get("package") or {}
    host = report.get("host") or {}
    host_summary = host.get("summary") or {}
    sampling = host.get("sampling") or {}
    cpu = host_summary.get("cpu_total_percent") or {}
    memory = host_summary.get("memory_available_bytes") or {}
    implementation = environment.get("python_implementation")
    version = environment.get("python_version")
    return {
        "revision": source.get("revision"),
        "branch": source.get("branch"),
        "dirty": source.get("dirty"),
        "worktree_digest": source.get("worktree_digest"),
        "source_state": source.get("state") or (
            "stable" if source.get("complete") and source.get("revision") else "unknown"
        ),
        "source_complete": bool(source.get("complete")) and source.get("revision") is not None,
        "source_changed": bool(meta.get("source_changed")),
        "interpreter": f"{implementation} {version}" if implementation and version else None,
        "interpreter_implementation": implementation,
        "interpreter_version": version,
        "platform": environment.get("platform"),
        "cpu_count": environment.get("cpu_count"),
        "package_origin_known": bool(package.get("origin")),
        "package_matches_source": package.get("matches_source"),
        "package_version": package.get("version"),
        "distribution_version": package.get("distribution_version"),
        "trace_processes": bool(meta.get("trace_processes")),
        "trace_git_commands": bool(meta.get("trace_git_commands")),
        "sample_tests": bool(meta.get("sample_tests")),
        "sample_interval": meta.get("sample_interval"),
        "iterations": meta.get("iterations") or 1,
        "suite_wall_seconds": meta.get("wall_seconds"),
        "host_cpu_mean": cpu.get("mean"),
        "host_cpu_max": cpu.get("max"),
        "host_memory_mean": memory.get("mean"),
        "host_samples": host_summary.get("samples"),
        "host_sampling_complete": sampling.get("complete"),
        "host_sampling_error": sampling.get("error"),
    }


def compare(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Compare two reports, refusing to imply a speedup under unlike conditions."""
    before_summary = summarize(before)
    after_summary = summarize(after)
    before_ident = _run_identity(before)
    after_ident = _run_identity(after)

    before_tests = list(before.get("tests", ()))
    after_tests = list(after.get("tests", ()))
    before_index = {_identity_key(_identity(test)): test for test in before_tests}
    after_index = {_identity_key(_identity(test)): test for test in after_tests}
    before_repeats = Counter(identifier for identifier, _ in (_identity(t) for t in before_tests))
    after_repeats = Counter(identifier for identifier, _ in (_identity(t) for t in after_tests))

    findings: dict[str, dict[str, Any]] = {}

    def note(dimension: str, status: str, message: str) -> None:
        entry = findings.get(dimension)
        if entry is None:
            findings[dimension] = {"dimension": dimension, "status": status,
                                   "messages": [message]}
            return
        if _STATUS_ORDER[status] > _STATUS_ORDER[entry["status"]]:
            entry["status"] = status
        entry["messages"].append(message)

    # -- report shape ------------------------------------------------------
    if before.get("schema_version") == after.get("schema_version"):
        note("schema", "matched",
             f"both reports use schema version {before.get('schema_version')}")
    else:
        note("schema", "different",
             f"report schema versions differ ({before.get('schema_version')} vs"
             f" {after.get('schema_version')}); fields one side never recorded"
             " cannot be compared")

    # -- workload and repetition identity ----------------------------------
    only_before = sorted(set(before_index) - set(after_index))
    only_after = sorted(set(after_index) - set(before_index))
    common = sorted(set(before_index) & set(after_index))
    if only_before or only_after:
        note("workload", "different",
             f"{len(set(before_index))} and {len(set(after_index))} test/iteration"
             f" identities; {len(only_before)} appear only in the earlier run and"
             f" {len(only_after)} only in the later one")
    else:
        note("workload", "matched",
             f"the same {len(before_index)} test/iteration identities appear in both runs")

    # Repetition is only comparable for tests both runs recorded; a test that
    # exists in one run alone is a workload difference, not a repeat-count one.
    differing_repeats = [
        (identifier, before_repeats[identifier], after_repeats[identifier])
        for identifier in sorted(set(before_repeats) & set(after_repeats))
        if before_repeats[identifier] != after_repeats[identifier]
    ]
    if differing_repeats:
        identifier, earlier, later = differing_repeats[0]
        note("repetitions", "different",
             f"{len(differing_repeats)} tests were repeated a different number of"
             f" times (e.g. {identifier}: {earlier} vs {later})")
    elif before_ident["iterations"] != after_ident["iterations"]:
        note("repetitions", "different",
             f"the runs declare {before_ident['iterations']} and"
             f" {after_ident['iterations']} iterations")
    else:
        note("repetitions", "matched",
             f"each test was repeated {before_ident['iterations']} time(s) in both runs")

    # -- outcomes ----------------------------------------------------------
    outcome_changes = []
    for key in common:
        old = before_index[key].get("outcome")
        new = after_index[key].get("outcome")
        if old == new:
            continue
        outcome_changes.append({
            "identity": key,
            "test_id": before_index[key].get("test_id"),
            "iteration": _identity(before_index[key])[1],
            "outcome_before": old,
            "outcome_after": new,
        })
    new_failures = [
        change for change in outcome_changes
        if not _outcome_is_failure(change["outcome_before"])
        and _outcome_is_failure(change["outcome_after"])
    ]
    resolved = [
        change for change in outcome_changes
        if _outcome_is_failure(change["outcome_before"])
        and not _outcome_is_failure(change["outcome_after"])
    ]
    suite_errors = (before_summary["totals"]["suite_errors"],
                    after_summary["totals"]["suite_errors"])
    if outcome_changes:
        note("outcomes", "different",
             f"{len(outcome_changes)} identities changed outcome"
             f" ({len(new_failures)} newly failing, {len(resolved)} no longer failing);"
             " the two runs did not complete the same work")
    elif suite_errors[0] != suite_errors[1]:
        note("outcomes", "different",
             f"{suite_errors[0]} and {suite_errors[1]} suite-level errors"
             " (a class or module fixture failed on one side only)")
    else:
        note("outcomes", "matched",
             "every common identity has the same outcome in both runs")

    # -- interpreter and platform -----------------------------------------
    if before_ident["interpreter"] is None or after_ident["interpreter"] is None:
        note("interpreter", "unknown",
             "the interpreter identity was not recorded in one or both runs")
    elif (before_ident["interpreter_version"] != after_ident["interpreter_version"]
          or before_ident["interpreter_implementation"] != after_ident["interpreter_implementation"]):
        note("interpreter", "different",
             f"{before_ident['interpreter']} vs {after_ident['interpreter']}")
    else:
        note("interpreter", "matched", before_ident["interpreter"])

    if not before_ident["platform"] or not after_ident["platform"]:
        note("platform", "unknown",
             "the platform was not recorded in one or both runs")
    elif before_ident["platform"] != after_ident["platform"]:
        note("platform", "different",
             f"{before_ident['platform']} vs {after_ident['platform']}")
    elif (before_ident["cpu_count"] is not None and after_ident["cpu_count"] is not None
          and before_ident["cpu_count"] != after_ident["cpu_count"]):
        note("platform", "different",
             f"{before_ident['cpu_count']} vs {after_ident['cpu_count']} CPUs")
    else:
        note("platform", "matched", before_ident["platform"])

    # -- source and imported package identity ------------------------------
    source_unknown = []
    for label, ident in (("earlier", before_ident), ("later", after_ident)):
        if ident["revision"] is None:
            source_unknown.append(f"{label}: the revision was not established"
                                  " (a Git metadata command failed, or the checkout"
                                  " changed while it ran)")
        elif not ident["source_complete"]:
            source_unknown.append(f"{label}: a revision is recorded but not whether"
                                  " the checkout stayed unchanged for the whole run")
        elif ident["source_changed"]:
            source_unknown.append(f"{label}: the checkout changed during the run")
    if source_unknown:
        note("source", "unknown", "; ".join(source_unknown))
    else:
        same_content = before_ident["worktree_digest"] == after_ident["worktree_digest"]
        note("source", "matched",
             f"{str(before_ident['revision'])[:12]} and"
             f" {str(after_ident['revision'])[:12]},"
             + (" identical uncommitted change" if same_content
                else " different uncommitted changes (as expected for a controlled change)"))

    mismatched_package = [
        label for label, ident in (("earlier", before_ident), ("later", after_ident))
        if ident["package_matches_source"] is False
    ]
    unknown_package = [
        label for label, ident in (("earlier", before_ident), ("later", after_ident))
        if ident["package_matches_source"] is None or not ident["package_origin_known"]
    ]
    if mismatched_package:
        note("package", "different",
             f"the {_labels(mismatched_package)} run imported deskmate_formats from"
             " outside the checkout named by --source, so its measurements describe"
             " different code than its revision claims")
    elif unknown_package:
        note("package", "unknown",
             "the imported package origin was not recorded for the"
             f" {_labels(unknown_package)} run" + ("s" if len(unknown_package) > 1 else ""))
    else:
        note("package", "matched",
             "both runs imported deskmate_formats from the checkout they name")

    # -- instrumentation ---------------------------------------------------
    instrumentation_differences = []
    for key, label in (("trace_processes", "process tracing"),
                       ("trace_git_commands", "Git command sampling"),
                       ("sample_tests", "per-test host sampling")):
        if before_ident[key] != after_ident[key]:
            instrumentation_differences.append(
                f"{label} ({before_ident[key]} vs {after_ident[key]})"
            )
    earlier_interval, later_interval = before_ident["sample_interval"], after_ident["sample_interval"]
    if (isinstance(earlier_interval, (int, float)) and isinstance(later_interval, (int, float))
            and float(earlier_interval) != float(later_interval)):
        instrumentation_differences.append(
            f"host sample interval ({earlier_interval} s vs {later_interval} s)"
        )
    if instrumentation_differences:
        note("instrumentation", "different",
             "; ".join(instrumentation_differences)
             + "; one side paid instrumentation overhead the other did not")
    else:
        note("instrumentation", "matched",
             "both runs traced and sampled in the same way")

    # -- host conditions ---------------------------------------------------
    earlier_cpu, later_cpu = before_ident["host_cpu_mean"], after_ident["host_cpu_mean"]
    if earlier_cpu is None or later_cpu is None:
        note("host", "unknown",
             "host CPU was not observed in one or both runs, so comparable load"
             " cannot be claimed")
    elif abs(float(earlier_cpu) - float(later_cpu)) > CPU_POINT_TOLERANCE:
        note("host", "different",
             f"mean host CPU differs by more than {int(CPU_POINT_TOLERANCE)} points"
             f" ({earlier_cpu} vs {later_cpu})")
    else:
        note("host", "matched",
             f"mean host CPU {earlier_cpu} vs {later_cpu}")

    earlier_memory, later_memory = before_ident["host_memory_mean"], after_ident["host_memory_mean"]
    if earlier_memory is None or later_memory is None:
        note("host", "unknown",
             "available memory was not observed in one or both runs")
    elif float(earlier_memory) == 0 or float(later_memory) == 0:
        note("host", "unknown",
             "available memory was recorded as zero in at least one run, which"
             " cannot be turned into a ratio")
    else:
        ratio = float(later_memory) / float(earlier_memory)
        if ratio < MEMORY_RATIO[0] or ratio > MEMORY_RATIO[1]:
            note("host", "different",
                 f"available memory differs by more than a third"
                 f" ({_format_bytes(earlier_memory)} vs {_format_bytes(later_memory)});"
                 " paging behaviour may differ")

    for label, ident in (("earlier", before_ident), ("later", after_ident)):
        if ident["host_samples"] in (None, 0):
            note("host", "unknown", f"the {label} run recorded no host samples")
        elif ident["host_sampling_complete"] is False:
            note("host", "unknown",
                 f"host sampling in the {label} run covered less than its interval implies"
                 + (f" ({ident['host_sampling_error']})" if ident["host_sampling_error"] else ""))

    qualification = [
        {
            "dimension": dimension,
            "status": findings[dimension]["status"],
            "detail": "; ".join(findings[dimension]["messages"]),
        }
        for dimension in _DIMENSIONS
        if dimension in findings
    ]
    warnings = [
        f"{entry['dimension']}: {entry['detail']}"
        for entry in qualification if entry["status"] != "matched"
    ]
    comparable = not warnings

    # -- per-identity deltas ----------------------------------------------
    deltas = []
    for key in common:
        old_test, new_test = before_index[key], after_index[key]
        old = float(old_test.get("wall_seconds") or 0.0)
        new = float(new_test.get("wall_seconds") or 0.0)
        deltas.append({
            "identity": key,
            "test_id": old_test.get("test_id"),
            "iteration": _identity(old_test)[1],
            "before_seconds": round(old, 3),
            "after_seconds": round(new, 3),
            "delta_seconds": round(new - old, 3),
            "ratio": round(new / old, 3) if old > 0 else None,
            "outcome_before": old_test.get("outcome"),
            "outcome_after": new_test.get("outcome"),
        })
    deltas.sort(key=lambda item: item["delta_seconds"])

    before_wall = float(before_summary["totals"]["suite_wall_seconds"] or 0.0)
    after_wall = float(after_summary["totals"]["suite_wall_seconds"] or 0.0)
    total_delta = round(after_wall - before_wall, 3)
    if not comparable:
        delta_label = "observation"
    elif total_delta < -0.005:
        delta_label = "improvement"
    elif total_delta > 0.005:
        delta_label = "regression"
    else:
        delta_label = "observation"

    return {
        "schema_version": COMPARISON_SCHEMA_VERSION,
        "report_schema_version": before.get("schema_version"),
        "before": {
            "revision": before_ident["revision"],
            "source_state": before_ident["source_state"],
            "interpreter": before_ident["interpreter"],
            "platform": before_ident["platform"],
            "suite_wall_seconds": before_summary["totals"]["suite_wall_seconds"],
            "tests": before_summary["totals"]["tests"],
            "distinct_tests": before_summary["totals"]["distinct_tests"],
            "iterations": before_ident["iterations"],
            "host_cpu_mean": earlier_cpu,
            "host_cpu_max": before_ident["host_cpu_max"],
            "host_memory_mean": earlier_memory,
            "host_samples": before_ident["host_samples"],
        },
        "after": {
            "revision": after_ident["revision"],
            "source_state": after_ident["source_state"],
            "interpreter": after_ident["interpreter"],
            "platform": after_ident["platform"],
            "suite_wall_seconds": after_summary["totals"]["suite_wall_seconds"],
            "tests": after_summary["totals"]["tests"],
            "distinct_tests": after_summary["totals"]["distinct_tests"],
            "iterations": after_ident["iterations"],
            "host_cpu_mean": later_cpu,
            "host_cpu_max": after_ident["host_cpu_max"],
            "host_memory_mean": later_memory,
            "host_samples": after_ident["host_samples"],
        },
        "totals": {
            "before_seconds": before_wall,
            "after_seconds": after_wall,
            "delta_seconds": total_delta,
            "comparable": comparable,
        },
        "comparable": comparable,
        "warnings": warnings,
        "qualification": qualification,
        "workload": {
            "before": len(before_index),
            "after": len(after_index),
            "common": len(common),
            "only_before": only_before,
            "only_after": only_after,
            "repeats_before": dict(sorted(before_repeats.items())),
            "repeats_after": dict(sorted(after_repeats.items())),
        },
        "outcome_changes": {
            "all": outcome_changes,
            "new_failures": new_failures,
            "resolved": resolved,
        },
        # The same signed deltas mean different things depending on comparability,
        # so the label travels with them instead of being assumed by the reader.
        "delta_label": delta_label,
        "improved": [item for item in deltas if item["delta_seconds"] < -0.005][:25],
        "regressed": [item for item in reversed(deltas) if item["delta_seconds"] > 0.005][:25],
        "per_test": deltas,
    }


def compare_markdown(comparison: dict[str, Any]) -> str:
    before = comparison.get("before", {})
    after = comparison.get("after", {})
    totals = comparison.get("totals", {})
    label = comparison.get("delta_label", "observation")
    qualified = label in ("improvement", "regression")
    lines = [
        "# Before/after qualification comparison",
        "",
        f"- Before: `{str(before.get('revision'))[:12]}`"
        f" ({before.get('source_state')}, {before.get('interpreter')},"
        f" {before.get('platform')}),"
        f" {before.get('tests')} records over {before.get('distinct_tests')} tests"
        f" × {before.get('iterations')} iteration(s),"
        f" {_format_seconds(before.get('suite_wall_seconds'))},"
        f" host CPU mean/max {before.get('host_cpu_mean')} / {before.get('host_cpu_max')} %",
        f"- After: `{str(after.get('revision'))[:12]}`"
        f" ({after.get('source_state')}, {after.get('interpreter')},"
        f" {after.get('platform')}),"
        f" {after.get('tests')} records over {after.get('distinct_tests')} tests"
        f" × {after.get('iterations')} iteration(s),"
        f" {_format_seconds(after.get('suite_wall_seconds'))},"
        f" host CPU mean/max {after.get('host_cpu_mean')} / {after.get('host_cpu_max')} %",
        f"- Delta: {_format_seconds(totals.get('delta_seconds'))}",
        f"- Comparable conditions: {comparison.get('comparable')}",
        "",
        "## Qualification",
        "",
        "| Dimension | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for entry in comparison.get("qualification", []):
        lines.append(f"| {entry['dimension']} | {entry['status']} | {entry['detail']} |")
    lines.append("")
    if not comparison.get("comparable"):
        lines += [
            "> The two runs are not like-for-like, or one of them is not fully",
            "> characterized. Every duration below is an **observation**; none of",
            "> them supports a speedup or slowdown claim.",
            "",
        ]

    workload = comparison.get("workload") or {}
    only_before = workload.get("only_before") or []
    only_after = workload.get("only_after") or []
    if only_before or only_after:
        lines += ["## Workload differences", ""]
        lines.append(f"- Only in the earlier run ({len(only_before)}): "
                     + (", ".join(f"`{item}`" for item in only_before[:10]) or "none"))
        lines.append(f"- Only in the later run ({len(only_after)}): "
                     + (", ".join(f"`{item}`" for item in only_after[:10]) or "none"))
        lines.append("")

    changes = (comparison.get("outcome_changes") or {}).get("all") or []
    if changes:
        lines += ["## Outcome changes", "",
                  "| Test | Iter | Before | After |", "| --- | --- | --- | --- |"]
        for change in changes[:25]:
            lines.append(
                f"| `{change['test_id']}` | {change['iteration']}"
                f" | {change['outcome_before']} | {change['outcome_after']} |"
            )
        lines.append("")

    reductions = ("## Most improved tests" if qualified
                  else "## Largest reductions (observations, not a speedup claim)")
    increases = ("## Most regressed tests" if qualified
                 else "## Largest increases (observations, not a slowdown claim)")
    lines += [reductions, "",
              "| Test | Iter | Before | After | Delta |",
              "| --- | --- | --- | --- | --- |"]
    for item in comparison.get("improved", []):
        lines.append(
            f"| `{item['test_id']}` | {item.get('iteration', 0)}"
            f" | {_format_seconds(item['before_seconds'])}"
            f" | {_format_seconds(item['after_seconds'])}"
            f" | {_format_seconds(item['delta_seconds'])} |"
        )
    lines += ["", increases, "",
              "| Test | Iter | Before | After | Delta |",
              "| --- | --- | --- | --- | --- |"]
    for item in comparison.get("regressed", []):
        lines.append(
            f"| `{item['test_id']}` | {item.get('iteration', 0)}"
            f" | {_format_seconds(item['before_seconds'])}"
            f" | {_format_seconds(item['after_seconds'])}"
            f" | +{_format_seconds(item['delta_seconds'])} |"
        )
    lines.append("")
    return "\n".join(lines)


def rank_operations(tests: Iterable[dict[str, Any]], *, top: int = 15) -> list[dict[str, Any]]:
    """Rank repeated expensive operations shared across tests."""
    totals: dict[str, dict[str, Any]] = {}
    for test in tests:
        key = f"{test.get('git_calls') or 0} git / {test.get('spawn_count') or 0} spawns"
        entry = totals.setdefault(key, {"operations": key, "tests": 0, "wall_seconds": 0.0})
        entry["tests"] += 1
        entry["wall_seconds"] += float(test.get("wall_seconds") or 0.0)
    ranked = sorted(totals.values(), key=lambda item: item["wall_seconds"], reverse=True)
    return ranked[:top]
