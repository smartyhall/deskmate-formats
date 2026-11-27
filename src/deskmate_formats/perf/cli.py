"""Command line for performance qualification.

Subcommands:

``run``        instrumented test execution with a machine-readable report
``microbench`` bounded host microbenchmarks
``compare``    before/after comparison that states whether conditions matched
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import unittest

from . import microbench, report
from .runner import RunResult, run_suite


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
    merged = results[0]
    if len(results) == 1:
        return merged
    records = [record for result in results for record in result.records]
    samples = [sample for result in results for sample in result.samples]
    merged.records = records
    merged.samples = samples
    merged.wall_seconds = sum(result.wall_seconds for result in results)
    merged.successful = all(result.successful for result in results)
    merged.finished_utc = results[-1].finished_utc
    merged.meta["iterations"] = len(results)
    merged.meta["iteration_wall_seconds"] = [round(result.wall_seconds, 3) for result in results]
    merged.meta["iteration_outcomes"] = [result.outcomes for result in results]
    return merged


def _write(path: Path | None, text: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def _command_run(arguments: argparse.Namespace) -> int:
    profile = PROFILES[arguments.profile]
    patterns = tuple(profile["patterns"])  # type: ignore[arg-type]
    repeat = arguments.repeat or int(profile.get("repeat", 1))  # type: ignore[arg-type]
    start = arguments.start

    if arguments.list_profiles:
        for name, entry in PROFILES.items():
            print(f"{name:12s} {entry['description']}")
        return 0

    source = Path(arguments.source).resolve()
    results: list[RunResult] = []
    for iteration in range(repeat):
        suite = build_suite(profile=arguments.profile, patterns=patterns, start=start,
                            module=arguments.module, test=arguments.test)
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
        results.append(result)
        if repeat > 1:
            print(f"iteration {iteration + 1}/{repeat}: {result.wall_seconds:.1f} s,"
                  f" {result.outcomes}", file=sys.stderr)

    combined = _merge(results)
    payload = combined.as_dict()
    summary = report.summarize(payload, top=arguments.top)
    markdown = report.to_markdown(summary)

    _write(Path(arguments.json_out) if arguments.json_out else None,
           json.dumps(payload, indent=2))
    _write(Path(arguments.summary_out) if arguments.summary_out else None,
           json.dumps(summary, indent=2))
    _write(Path(arguments.md_out) if arguments.md_out else None, markdown)
    if arguments.print_markdown:
        print(markdown)
    return 0 if combined.successful else 1


def _command_microbench(arguments: argparse.Namespace) -> int:
    result = microbench.run_microbenchmarks(
        iterations=arguments.iterations,
        names=arguments.name,
        sample_interval=arguments.sample_interval,
    )
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
    run.add_argument("--source", default=".", help="repository root for revision metadata")
    run.add_argument("--label", default="", help="free-form label for this measurement")
    run.add_argument("--repeat", type=int, default=0, help="override profile repetitions")
    run.add_argument("--top", type=int, default=25, help="rows in the ranking")
    run.add_argument("--trace-git-commands", action="store_true",
                     help="count the Git subcommand of every spawn (implies tracing)")
    run.add_argument("--trace-processes", action="store_true",
                     help="record subprocess spawn latency and Git calls per test")
    run.add_argument("--sample-tests", action="store_true",
                     help="record a host sample per test (adds a few milliseconds each)")
    run.add_argument("--sample-interval", type=float, default=5.0,
                     help="seconds between background host samples")
    run.add_argument("--verbosity", type=int, default=1, choices=(0, 1, 2))
    run.add_argument("--json-out", help="write the machine-readable run report")
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
