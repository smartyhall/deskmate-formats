"""Aggregation, ranking and before/after comparison of qualification reports."""

from __future__ import annotations

from typing import Any, Iterable


SCHEMA_VERSION = 1

LIMITATIONS = (
    "Wall-clock durations were observed on a shared laboratory VM; they are "
    "comparable only when host conditions are comparable.",
    "Per-test CPU seconds are process-wide user+system time deltas, so work "
    "performed by child processes is not included.",
    "Peak working-set deltas are process high-water marks, not per-test maxima.",
    "Fixture setup performed in setUpClass and module import is not attributed "
    "to individual tests; it appears as unattributed time.",
)


def _share(part: float, whole: float) -> float:
    return round(100.0 * part / whole, 2) if whole > 0 else 0.0


def _outcome_is_failure(outcome: str) -> bool:
    return outcome in ("failure", "error", "unexpected-success")


def summarize(report: dict[str, Any], *, top: int = 25, pareto_target: float = 0.8) -> dict[str, Any]:
    """Derive module totals, ranked tests and a Pareto view from a run report."""
    tests: list[dict[str, Any]] = list(report.get("tests", ()))
    total_wall = sum(float(test.get("wall_seconds") or 0.0) for test in tests)
    total_cpu = sum(float(test.get("cpu_seconds") or 0.0) for test in tests)
    suite_wall = float((report.get("meta") or {}).get("wall_seconds") or 0.0)
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
        entry["wall_seconds"] = round(entry["wall_seconds"], 3)
        entry["cpu_seconds"] = round(entry["cpu_seconds"], 3)
        entry["subprocess_seconds"] = round(entry["subprocess_seconds"], 3)
        entry["share_percent"] = _share(entry["wall_seconds"], total_wall)

    ranked = sorted(tests, key=lambda test: float(test.get("wall_seconds") or 0.0), reverse=True)
    ranking: list[dict[str, Any]] = []
    cumulative = 0.0
    for position, test in enumerate(ranked[:top], start=1):
        duration = float(test.get("wall_seconds") or 0.0)
        cumulative += duration
        ranking.append({
            "rank": position,
            "test_id": test.get("test_id"),
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
    traced = any(test.get("spawn_count") is not None for test in tests) and bool(
        (report.get("meta") or {}).get("trace_processes")
    )
    command_counts: dict[str, int] = {}
    for test in tests:
        for command, count in (test.get("git_commands") or {}).items():
            command_counts[command] = command_counts.get(command, 0) + int(count)
    git_commands = [{"command": command, "calls": count}
                    for command, count in sorted(command_counts.items(),
                                                 key=lambda item: (-item[1], item[0]))]

    return {
        "schema_version": SCHEMA_VERSION,
        "meta": report.get("meta", {}),
        "environment": report.get("environment", {}),
        "host": (report.get("host") or {}).get("summary", {}),
        "totals": {
            "tests": len(tests),
            "outcomes": (report.get("meta") or {}).get("outcomes", {}),
            "failures": len(failures),
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
        "failures": [
            {
                "test_id": test.get("test_id"),
                "outcome": test.get("outcome"),
                "message": test.get("message"),
                "wall_seconds": round(float(test.get("wall_seconds") or 0.0), 3),
            }
            for test in failures
        ],
        "limitations": list(LIMITATIONS),
    }


def _format_seconds(value: float | None) -> str:
    if value is None:
        return "n/a"
    if value < 1.0:
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


def to_markdown(summary: dict[str, Any]) -> str:
    """Human-readable qualification summary."""
    meta = summary.get("meta", {})
    environment = summary.get("environment", {})
    host = summary.get("host", {})
    totals = summary.get("totals", {})
    cpu = host.get("cpu_total_percent", {})
    memory = host.get("memory_available_bytes", {})
    source = meta.get("source", {})

    lines = [
        "# Portable test performance qualification",
        "",
        f"- Profile: `{meta.get('profile') or 'unspecified'}`"
        f" (label: {meta.get('label') or 'none'})",
        f"- Started: {meta.get('started_utc')}  Finished: {meta.get('finished_utc')}",
        f"- Revision: `{source.get('revision')}`"
        f" branch `{source.get('branch')}`"
        f" dirty={source.get('dirty')}",
        f"- Python: {environment.get('python_implementation')}"
        f" {environment.get('python_version')} ({environment.get('python_executable')})",
        f"- Platform: {environment.get('platform')} ({environment.get('cpu_count')} CPUs)",
        f"- Tests: {totals.get('tests')} -> {totals.get('outcomes')}",
        f"- Suite wall: {_format_seconds(totals.get('suite_wall_seconds'))}"
        f" (attributed {_format_seconds(totals.get('attributed_wall_seconds'))},"
        f" unattributed {_format_seconds(totals.get('unattributed_seconds'))})",
        f"- Process CPU: {_format_seconds(totals.get('cpu_seconds'))}"
        f" (ratio {totals.get('cpu_ratio')})",
        "",
        "## Host conditions during the run",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Samples | {host.get('samples')} |",
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
        f"{pareto.get('tests_for_target')} of {pareto.get('tests_total')} tests"
        f" ({pareto.get('tests_share_percent')}%) account for"
        f" {int(float(pareto.get('target', 0)) * 100)}% of attributed wall time"
        f" ({_format_seconds(pareto.get('seconds_for_target'))}).",
        "",
        "## Slowest individual tests",
        "",
        "| # | Test | Outcome | Wall | Share | Cum. | CPU | Spawns | Git |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in summary.get("ranking", []):
        lines.append(
            f"| {entry['rank']} | `{entry['test_id']}` | {entry['outcome']}"
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
        f"- Spawn latency total: {_format_seconds(subprocess.get('spawn_seconds'))}",
        f"- Subprocess wall total: {_format_seconds(subprocess.get('wall_seconds'))}",
    ]

    if summary.get("git_commands"):
        lines += ["", "## Git command mix", "",
                  "| Subcommand | Calls |", "| --- | --- |"]
        for entry in summary["git_commands"][:15]:
            lines.append(f"| `git {entry['command']}` | {entry['calls']} |")

    if summary.get("failures"):
        lines += ["", "## Failures", ""]
        for failure in summary["failures"]:
            lines.append(
                f"- `{failure['test_id']}` ({failure['outcome']},"
                f" {_format_seconds(failure['wall_seconds'])}): {failure['message']}"
            )

    lines += ["", "## Limitations", ""]
    lines += [f"- {item}" for item in summary.get("limitations", [])]
    lines.append("")
    return "\n".join(lines)


def compare(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Compare two reports, refusing to imply a speedup under unlike conditions."""
    before_summary = summarize(before)
    after_summary = summarize(after)
    before_tests = {test["test_id"]: test for test in before.get("tests", [])}
    after_tests = {test["test_id"]: test for test in after.get("tests", [])}

    common = sorted(set(before_tests) & set(after_tests))
    deltas = []
    for identifier in common:
        old = float(before_tests[identifier].get("wall_seconds") or 0.0)
        new = float(after_tests[identifier].get("wall_seconds") or 0.0)
        deltas.append({
            "test_id": identifier,
            "before_seconds": round(old, 3),
            "after_seconds": round(new, 3),
            "delta_seconds": round(new - old, 3),
            "ratio": round(new / old, 3) if old > 0 else None,
        })
    deltas.sort(key=lambda item: item["delta_seconds"])

    old_cpu = ((before_summary.get("host") or {}).get("cpu_total_percent") or {}).get("mean")
    new_cpu = ((after_summary.get("host") or {}).get("cpu_total_percent") or {}).get("mean")
    old_memory = ((before_summary.get("host") or {}).get("memory_available_bytes") or {}).get("mean")
    new_memory = ((after_summary.get("host") or {}).get("memory_available_bytes") or {}).get("mean")

    warnings: list[str] = []
    if before_summary["totals"]["tests"] != after_summary["totals"]["tests"]:
        warnings.append(
            "The two runs cover different test counts; totals are not directly comparable."
        )
    if old_cpu is not None and new_cpu is not None and abs(float(old_cpu) - float(new_cpu)) > 15:
        warnings.append(
            f"Mean host CPU differs by more than 15 points ({old_cpu} vs {new_cpu});"
            " the runs were taken under materially different load."
        )
    if old_memory and new_memory:
        ratio = float(new_memory) / float(old_memory)
        if ratio < 0.75 or ratio > 1.33:
            warnings.append(
                "Available memory differs by more than a third between runs;"
                " paging behaviour may differ."
            )
    if not common:
        warnings.append("No tests appear in both runs.")

    return {
        "schema_version": SCHEMA_VERSION,
        "before": {
            "revision": (before.get("meta", {}).get("source") or {}).get("revision"),
            "suite_wall_seconds": before_summary["totals"]["suite_wall_seconds"],
            "tests": before_summary["totals"]["tests"],
            "host_cpu_mean": old_cpu,
            "host_memory_mean": old_memory,
        },
        "after": {
            "revision": (after.get("meta", {}).get("source") or {}).get("revision"),
            "suite_wall_seconds": after_summary["totals"]["suite_wall_seconds"],
            "tests": after_summary["totals"]["tests"],
            "host_cpu_mean": new_cpu,
            "host_memory_mean": new_memory,
        },
        "totals": {
            "before_seconds": before_summary["totals"]["suite_wall_seconds"],
            "after_seconds": after_summary["totals"]["suite_wall_seconds"],
            "delta_seconds": round(
                after_summary["totals"]["suite_wall_seconds"]
                - before_summary["totals"]["suite_wall_seconds"], 3
            ),
        },
        "comparable": not warnings,
        "warnings": warnings,
        "improved": [item for item in deltas if item["delta_seconds"] < -0.005][:25],
        "regressed": [item for item in reversed(deltas) if item["delta_seconds"] > 0.005][:25],
        "per_test": deltas,
    }


def compare_markdown(comparison: dict[str, Any]) -> str:
    before = comparison.get("before", {})
    after = comparison.get("after", {})
    totals = comparison.get("totals", {})
    lines = [
        "# Before/after qualification comparison",
        "",
        f"- Before: `{before.get('revision')}`"
        f" {_format_seconds(before.get('suite_wall_seconds'))}"
        f" over {before.get('tests')} tests, host CPU {before.get('host_cpu_mean')}%",
        f"- After: `{after.get('revision')}`"
        f" {_format_seconds(after.get('suite_wall_seconds'))}"
        f" over {after.get('tests')} tests, host CPU {after.get('host_cpu_mean')}%",
        f"- Delta: {_format_seconds(totals.get('delta_seconds'))}",
        f"- Comparable conditions: {comparison.get('comparable')}",
        "",
    ]
    for warning in comparison.get("warnings", []):
        lines.append(f"> **Caveat:** {warning}")
    if comparison.get("warnings"):
        lines.append("")

    lines += ["## Most improved tests", "",
              "| Test | Before | After | Delta |", "| --- | --- | --- | --- |"]
    for item in comparison.get("improved", []):
        lines.append(
            f"| `{item['test_id']}` | {_format_seconds(item['before_seconds'])}"
            f" | {_format_seconds(item['after_seconds'])}"
            f" | {_format_seconds(item['delta_seconds'])} |"
        )
    lines += ["", "## Most regressed tests", "",
              "| Test | Before | After | Delta |", "| --- | --- | --- | --- |"]
    for item in comparison.get("regressed", []):
        lines.append(
            f"| `{item['test_id']}` | {_format_seconds(item['before_seconds'])}"
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
