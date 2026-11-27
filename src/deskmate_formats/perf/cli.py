"""Command line for performance qualification.

Subcommands:

``run``        instrumented test execution with a machine-readable report
``microbench`` bounded host microbenchmarks
``compare``    before/after comparison that states whether conditions matched

Every numeric option is validated here as well as in the library: a negative
repetition count or a zero sampling interval is a configuration error, not a
measurement, and must not be silently replaced by a default or a clamp.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import unittest

from . import microbench, report
from .runner import RunResult, run_suite
from .sanitize import public_projection


PROFILES: dict[str, dict[str, object]] = {
    "portable": {
        "patterns": ("test_*.py",),
        "description": "Full portable verification suite (no lab fixtures).",
    },
    "supervisor": {
        "patterns": ("test_supervisor*.py",),
        "description": "Supervisor process ownership, protocol and Git fixtures.",
    },
    "observer": {
        "patterns": ("test_observer*.py",),
        "description": "Observer HTTP, journal and Codex child-process fixtures.",
    },
    "stress": {
        "patterns": (
            "test_supervisor_driver.py",
            "test_supervisor_timeouts.py",
            "test_supervisor_s2_live.py",
            "test_observer_codex_exec.py",
            "test_observer_codex_wrapper.py",
        ),
        "repeat": 3,
        "description": "Process-synchronization stress profile; repeats the "
                       "synchronization-heavy modules.",
    },
    "focused": {
        "patterns": (),
        "description": "One module or test id supplied with --module/--test.",
    },
}

DEFAULT_START = "tests/portable"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _positive_int(value: int | None, default: int, flag: str) -> int:
    resolved = default if value is None else value
    if not isinstance(resolved, int) or isinstance(resolved, bool) or resolved < 1:
        raise SystemExit(f"{flag} must be a positive integer (got {value!r})")
    return resolved


def build_suite(*, profile: str, patterns: tuple[str, ...], start: str,
                module: str | None = None, test: str | None = None) -> unittest.TestSuite:
    loader = unittest.TestLoader()
    # ``discover`` inserts the start directory itself; the explicit forms do not,
    # and the portable suite imports its fixtures as top-level modules.
    resolved_start = str(Path(start).resolve())
    if resolved_start not in sys.path:
        sys.path.insert(0, resolved_start)
    if test:
        return loader.loadTestsFromNames([test])
    if module:
        names = [module] if module.startswith("test_") else [f"test_{module}"]
        return loader.loadTestsFromNames(names)
    if not patterns:
        raise SystemExit(
            f"profile '{profile}' needs --module or --test (for example --module "
            "test_supervisor_task_git)"
        )
    suites = []
    for pattern in patterns:
        suites.append(loader.discover(start, pattern=pattern, top_level_dir=start))
    return unittest.TestSuite(suites)


def _merge(results: list[RunResult]) -> RunResult:
    """Combine repeated iterations without editing any of them.

    Editing the first result made its own per-iteration fields describe the
    whole run, and the measurements that had already been taken could not be
    recovered afterwards.  The merged result is built from the collected
    records instead, so every iteration stays inspectable on its own.
    """
    if not results:
        raise ValueError("nothing to merge: no iteration produced a result")
    if len(results) == 1:
        return results[0]

    first, last = results[0], results[-1]
    # Renumber records that a caller ran without an iteration, so the merged
    # report never carries two records under one identity.  Copies are used:
    # each input result stays exactly as it was measured.
    records = []
    for index, result in enumerate(results):
        for record in result.records:
            records.append(record if record.iteration == index
                           else replace(record, iteration=index))
    samples = [sample for result in results for sample in result.samples]
    issues = [issue for result in results for issue in result.suite_errors]
    sources = [result.meta.get("source") or {} for result in results]
    identities = {
        (source.get("revision"), source.get("worktree_digest"),
         source.get("untracked_digest"), source.get("state"))
        for source in sources
    }
    stable = (
        len(identities) == 1
        and all(source.get("state") == "stable" and source.get("revision") for source in sources)
    )
    if stable:
        source = sources[0]
    else:
        source = {
            "revision": None,
            "branch": None,
            "dirty": None,
            "worktree_digest": None,
            "untracked_digest": None,
            "untracked_reason": None,
            "observed_utc": (last.meta.get("source_after") or {}).get("observed_utc"),
            "complete": False,
            "state": "changed",
            "failed_commands": [
                failure
                for result in results
                for failure in (result.meta.get("source") or {}).get("failed_commands", [])
            ],
        }

    # Provenance overhead is summed rather than dropped: an iteration whose
    # identity queries took longer is still comparable, but the report should
    # let a reader see what the harness itself cost.
    timings = [result.meta.get("timing") or {} for result in results]
    timing = {
        "iterations": len(results),
        "harness_started_utc": timings[0].get("harness_started_utc"),
        "execution_seconds": round(sum(result.wall_seconds for result in results), 6),
        "harness_seconds": round(
            sum(float(entry.get("harness_seconds") or 0.0) for entry in timings), 6
        ),
        "execution_boundary": timings[0].get("execution_boundary"),
    }
    for key in ("pre_source_seconds", "pre_package_seconds", "post_source_seconds"):
        timing[key] = round(
            sum(float(entry.get(key) or 0.0) for entry in timings), 6
        )

    meta = dict(first.meta)
    meta.update({
        "iterations": len(results),
        "iteration_wall_seconds": [round(result.wall_seconds, 3) for result in results],
        "timing": timing,
        "iteration_outcomes": [result.outcomes for result in results],
        "iteration_discovered_tests": [result.meta.get("discovered_tests") for result in results],
        "iteration_suite_errors": [len(result.suite_errors) for result in results],
        "executed_tests": len(records),
        "discovered_tests": sum(int(result.meta.get("discovered_tests") or 0)
                                for result in results),
        "source_before": first.meta.get("source_before"),
        "source_after": last.meta.get("source_after"),
        "source": source,
        "source_changed": not stable,
        "package": last.meta.get("package"),
    })
    return RunResult(
        records=records,
        samples=samples,
        suite_errors=issues,
        started_utc=first.started_utc,
        finished_utc=last.finished_utc,
        wall_seconds=sum(result.wall_seconds for result in results),
        successful=all(result.successful for result in results),
        meta=meta,
    )


def _write(path: Path | None, text: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def _command_run(arguments: argparse.Namespace) -> int:
    if arguments.list_profiles:
        for name, entry in PROFILES.items():
            print(f"{name:12s} {entry['description']}")
        return 0

    profile = PROFILES[arguments.profile]
    patterns = tuple(profile["patterns"])  # type: ignore[arg-type]
    repeat = _positive_int(arguments.repeat, int(profile.get("repeat", 1)), "--repeat")  # type: ignore[arg-type]
    top = _positive_int(arguments.top, 25, "--top")
    start = arguments.start
    source = Path(arguments.source).resolve()

    results: list[RunResult] = []
    for iteration in range(repeat):
        suite = build_suite(profile=arguments.profile, patterns=patterns, start=start,
                            module=arguments.module, test=arguments.test)
        discovered = suite.countTestCases()
        if discovered == 0:
            raise SystemExit(
                f"no tests were discovered for profile '{arguments.profile}' in '{start}';"
                " refusing to record an empty run as a successful measurement"
            )
        try:
            result = run_suite(
                suite,
                label=arguments.label,
                profile=arguments.profile,
                trace_processes=arguments.trace_processes,
                trace_git_commands=arguments.trace_git_commands,
                sample_interval=arguments.sample_interval,
                sample_tests=arguments.sample_tests,
                verbosity=arguments.verbosity,
                stream=sys.stderr,
                source_directory=source,
                iteration=iteration,
            )
        except ValueError as error:
            raise SystemExit(f"invalid measurement configuration: {error}") from None
        missing = discovered - len(result.records) - len(result.suite_errors)
        if missing > 0:
            print(f"warning: {missing} of {discovered} discovered tests produced no record"
                  f" (suite-level errors: {len(result.suite_errors)})", file=sys.stderr)
        results.append(result)
        if repeat > 1:
            print(f"iteration {iteration + 1}/{repeat}: {result.wall_seconds:.1f} s,"
                  f" {result.outcomes}", file=sys.stderr)

    combined = _merge(results)
    payload = combined.as_dict()
    summary = report.summarize(payload, top=top)
    markdown = report.to_markdown(summary)

    _write(Path(arguments.json_out) if arguments.json_out else None,
           json.dumps(payload, indent=2))
    _write(Path(arguments.public_out) if arguments.public_out else None,
           json.dumps(public_projection(payload), indent=2))
    _write(Path(arguments.summary_out) if arguments.summary_out else None,
           json.dumps(summary, indent=2))
    _write(Path(arguments.md_out) if arguments.md_out else None, markdown)
    if arguments.print_markdown:
        print(markdown)
    return 0 if combined.successful else 1


def _command_microbench(arguments: argparse.Namespace) -> int:
    known = {benchmark.name for benchmark in microbench.BENCHMARKS}
    unknown = sorted(set(arguments.name or ()) - known)
    if unknown:
        raise SystemExit(
            f"unknown benchmark name(s): {', '.join(unknown)};"
            f" available: {', '.join(sorted(known))}"
        )
    try:
        result = microbench.run_microbenchmarks(
            iterations=arguments.iterations,
            names=arguments.name,
            sample_interval=arguments.sample_interval,
        )
    except ValueError as error:
        raise SystemExit(f"invalid measurement configuration: {error}") from None
    markdown = microbench.to_markdown(result)
    _write(Path(arguments.json_out) if arguments.json_out else None,
           json.dumps(result, indent=2))
    _write(Path(arguments.md_out) if arguments.md_out else None, markdown)
    if arguments.print_markdown:
        print(markdown)
    return 0


def _command_compare(arguments: argparse.Namespace) -> int:
    before = json.loads(Path(arguments.before).read_text(encoding="utf-8"))
    after = json.loads(Path(arguments.after).read_text(encoding="utf-8"))
    comparison = report.compare(before, after)
    markdown = report.compare_markdown(comparison)
    _write(Path(arguments.json_out) if arguments.json_out else None,
           json.dumps(comparison, indent=2))
    _write(Path(arguments.md_out) if arguments.md_out else None, markdown)
    if arguments.print_markdown:
        print(markdown)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deskmate-test-perf",
        description="Performance qualification for the portable test suite.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="run an instrumented test profile")
    run.add_argument("--profile", default="portable", choices=sorted(PROFILES))
    run.add_argument("--module", help="single test module (focused profile)")
    run.add_argument("--test", help="single dotted test id")
    run.add_argument("--start", default=DEFAULT_START, help="discovery directory")
    run.add_argument("--source", default=".",
                     help="checkout whose revision and import origin describe this run")
    run.add_argument("--label", default="", help="free-form label for this measurement")
    run.add_argument("--repeat", type=int, default=None,
                     help="override profile repetitions (positive integer)")
    run.add_argument("--top", type=int, default=25, help="rows in the ranking")
    run.add_argument("--trace-git-commands", action="store_true",
                     help="count the Git subcommand of every spawn (implies tracing)")
    run.add_argument("--trace-processes", action="store_true",
                     help="record subprocess spawn latency and Git calls per test")
    run.add_argument("--sample-tests", action="store_true",
                     help="record a host sample per test (adds a few milliseconds each)")
    run.add_argument("--sample-interval", type=float, default=5.0,
                     help="seconds between background host samples (positive)")
    run.add_argument("--verbosity", type=int, default=1, choices=(0, 1, 2))
    run.add_argument("--json-out", help="write the machine-readable run report (private)")
    run.add_argument("--public-out",
                     help="write the sanitized projection of the run report (publishable)")
    run.add_argument("--summary-out", help="write the derived summary as JSON")
    run.add_argument("--md-out", help="write the markdown summary")
    run.add_argument("--print-markdown", action="store_true", help="print the markdown summary")
    run.add_argument("--list-profiles", action="store_true", help="list available profiles")
    run.set_defaults(handler=_command_run)

    bench = subparsers.add_parser("microbench", help="run bounded host microbenchmarks")
    bench.add_argument("--iterations", type=int, default=8)
    bench.add_argument("--name", action="append", help="restrict to a named benchmark")
    bench.add_argument("--sample-interval", type=float, default=5.0)
    bench.add_argument("--json-out")
    bench.add_argument("--md-out")
    bench.add_argument("--print-markdown", action="store_true")
    bench.set_defaults(handler=_command_microbench)

    comparison = subparsers.add_parser("compare", help="compare two run reports")
    comparison.add_argument("--before", required=True)
    comparison.add_argument("--after", required=True)
    comparison.add_argument("--json-out")
    comparison.add_argument("--md-out")
    comparison.add_argument("--print-markdown", action="store_true")
    comparison.set_defaults(handler=_command_compare)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    return int(arguments.handler(arguments))


if __name__ == "__main__":
    raise SystemExit(main())
