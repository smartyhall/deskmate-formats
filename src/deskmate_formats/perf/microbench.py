"""Bounded microbenchmarks for Windows-specific process and filesystem cost.

These isolate the overheads that a Python-level profile cannot show: process
creation, interpreter start-up, Git invocation, NTFS metadata operations and
temporary-directory lifecycle.  Every benchmark is bounded and uses only
disposable paths.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Callable

from .hostload import HostTimeline, describe_environment, summarize_samples


SCHEMA_VERSION = 1

# A benchmark that hangs must not hang the whole session: ``_measure`` records a
# ``subprocess.SubprocessError`` as an error row, but only if the call returns.
BENCHMARK_TIMEOUT = 120.0

_GIT_ENV_KEYS = ("GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL", "GIT_TERMINAL_PROMPT")


def _git_environment() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT="0")
    return env


def _python(*arguments: str) -> list[str]:
    return [sys.executable, *arguments]


def _source_environment() -> dict[str, str]:
    """Child environment that resolves this checkout's package first.

    A benchmark that imports ``deskmate_formats`` must measure the tree being
    measured, not whichever wheel another campaign installed.  ``python -I``
    would ignore ``PYTHONPATH``, so the import benchmark deliberately does not
    use it and sets the path explicitly instead.
    """
    env = dict(os.environ)
    source = str(Path(__file__).resolve().parents[1])
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = source + (os.pathsep + existing if existing else "")
    return env


@dataclass
class Benchmark:
    name: str
    description: str
    run: Callable[[int], float]
    iterations: int = 8


def _bench_python_startup(_index: int) -> float:
    start = time.perf_counter()
    subprocess.run(_python("-c", "pass"), check=True, timeout=BENCHMARK_TIMEOUT,
                   stdin=subprocess.DEVNULL,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return time.perf_counter() - start


def _bench_python_import(_index: int) -> float:
    start = time.perf_counter()
    subprocess.run(_python("-c", "import deskmate_formats.supervisor.protocol"),
                   check=True, timeout=BENCHMARK_TIMEOUT, stdin=subprocess.DEVNULL,
                   env=_source_environment(),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return time.perf_counter() - start


def _bench_git_version(_index: int) -> float:
    start = time.perf_counter()
    subprocess.run(["git", "--version"], check=True, env=_git_environment(),
                   timeout=BENCHMARK_TIMEOUT,
                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)
    return time.perf_counter() - start


def _bench_git_init(_index: int) -> float:
    with tempfile.TemporaryDirectory() as directory:
        start = time.perf_counter()
        subprocess.run(["git", "init", "-q", "-b", "main", "--object-format=sha1"],
                       cwd=directory, check=True, env=_git_environment(),
                       timeout=BENCHMARK_TIMEOUT,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        return time.perf_counter() - start


def _bench_git_commit(_index: int) -> float:
    with tempfile.TemporaryDirectory() as directory:
        env = _git_environment()
        env.update(GIT_AUTHOR_NAME="Synthetic Benchmark", GIT_AUTHOR_EMAIL="bench@example.invalid",
                   GIT_COMMITTER_NAME="Synthetic Benchmark",
                   GIT_COMMITTER_EMAIL="bench@example.invalid",
                   GIT_AUTHOR_DATE="2026-01-01T00:00:00Z",
                   GIT_COMMITTER_DATE="2026-01-01T00:00:00Z")
        subprocess.run(["git", "init", "-q", "-b", "main", "--object-format=sha1"],
                       cwd=directory, check=True, env=env, timeout=BENCHMARK_TIMEOUT,
                       stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        start = time.perf_counter()
        subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "Synthetic benchmark"],
                       cwd=directory, check=True, env=env, timeout=BENCHMARK_TIMEOUT,
                       stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return time.perf_counter() - start


def _bench_git_rev_parse(_index: int) -> float:
    with tempfile.TemporaryDirectory() as directory:
        env = _git_environment()
        env.update(GIT_AUTHOR_NAME="Synthetic Benchmark", GIT_AUTHOR_EMAIL="bench@example.invalid",
                   GIT_COMMITTER_NAME="Synthetic Benchmark",
                   GIT_COMMITTER_EMAIL="bench@example.invalid",
                   GIT_AUTHOR_DATE="2026-01-01T00:00:00Z",
                   GIT_COMMITTER_DATE="2026-01-01T00:00:00Z")
        subprocess.run(["git", "init", "-q", "-b", "main", "--object-format=sha1"],
                       cwd=directory, check=True, env=env, timeout=BENCHMARK_TIMEOUT,
                       stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "anchor"],
                       cwd=directory, check=True, env=env, timeout=BENCHMARK_TIMEOUT,
                       stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        start = time.perf_counter()
        subprocess.run(["git", "rev-parse", "HEAD"], cwd=directory, check=True, env=env,
                       timeout=BENCHMARK_TIMEOUT,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        return time.perf_counter() - start


def _bench_tempdir(_index: int) -> float:
    start = time.perf_counter()
    with tempfile.TemporaryDirectory() as directory:
        Path(directory, "probe").write_bytes(b"x")
    return time.perf_counter() - start


def _bench_file_write(_index: int) -> float:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory, "payload.bin")
        start = time.perf_counter()
        target.write_bytes(b"x" * 4096)
        return time.perf_counter() - start


def _bench_file_fsync(_index: int) -> float:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory, "payload.bin")
        start = time.perf_counter()
        with target.open("wb") as stream:
            stream.write(b"x" * 4096)
            stream.flush()
            os.fsync(stream.fileno())
        return time.perf_counter() - start


def _bench_file_stat(_index: int) -> float:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory, "payload.bin")
        target.write_bytes(b"x")
        start = time.perf_counter()
        target.stat()
        return time.perf_counter() - start


def _bench_sqlite(_index: int) -> float:
    with tempfile.TemporaryDirectory() as directory:
        start = time.perf_counter()
        connection = sqlite3.connect(str(Path(directory, "queue.sqlite3")))
        try:
            connection.execute("CREATE TABLE tasks (id INTEGER PRIMARY KEY, state TEXT)")
            connection.execute("INSERT INTO tasks (state) VALUES ('accepted')")
            connection.commit()
        finally:
            connection.close()
        return time.perf_counter() - start


def _bench_thread(_index: int) -> float:
    start = time.perf_counter()
    thread = threading.Thread(target=lambda: None)
    thread.start()
    thread.join()
    return time.perf_counter() - start


BENCHMARKS: tuple[Benchmark, ...] = (
    Benchmark("python_startup", "Spawn this interpreter and exit immediately.", _bench_python_startup),
    Benchmark("python_import_supervisor",
              "Spawn this interpreter and import the supervisor protocol.", _bench_python_import),
    Benchmark("git_version", "Spawn Git with no repository.", _bench_git_version),
    Benchmark("git_init", "Create a fresh SHA-1 repository in a temporary directory.", _bench_git_init),
    Benchmark("git_commit", "Record one empty commit in a fresh repository.", _bench_git_commit),
    Benchmark("git_rev_parse", "Resolve HEAD in a fresh repository.", _bench_git_rev_parse),
    Benchmark("tempdir_create", "Create and remove a temporary directory.", _bench_tempdir),
    Benchmark("file_write_4k", "Write a 4 KiB file.", _bench_file_write),
    Benchmark("file_write_4k_fsync", "Write a 4 KiB file and flush it to disk.", _bench_file_fsync),
    Benchmark("file_stat", "Stat an existing file.", _bench_file_stat),
    Benchmark("sqlite_create", "Open SQLite, create a table, insert and commit.", _bench_sqlite),
    Benchmark("thread_start_join", "Start and join an empty thread.", _bench_thread),
)


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return ordered[position]


def _measure(benchmark: Benchmark, iterations: int) -> dict[str, Any]:
    samples: list[float] = []
    error: str | None = None
    for index in range(iterations):
        try:
            samples.append(benchmark.run(index))
        except (OSError, sqlite3.Error, subprocess.SubprocessError) as failure:
            error = f"{type(failure).__name__}: {failure}"
            break
    if not samples:
        return {"name": benchmark.name, "description": benchmark.description,
                "iterations": 0, "error": error}
    return {
        "name": benchmark.name,
        "description": benchmark.description,
        "iterations": len(samples),
        "min_seconds": round(min(samples), 6),
        "median_seconds": round(statistics.median(samples), 6),
        "mean_seconds": round(statistics.fmean(samples), 6),
        "p90_seconds": round(_percentile(samples, 0.9) or 0.0, 6),
        "max_seconds": round(max(samples), 6),
        "total_seconds": round(sum(samples), 6),
        "samples": [round(value, 6) for value in samples],
        "error": error,
    }


def run_microbenchmarks(
    *, iterations: int = 8, names: list[str] | None = None,
    sample_interval: float = 5.0,
) -> dict[str, Any]:
    """Run bounded microbenchmarks and return a serializable report."""
    if not isinstance(iterations, int) or isinstance(iterations, bool) or iterations < 1:
        raise ValueError(f"iterations must be a positive integer, not {iterations!r}")
    requested = None if names is None else list(dict.fromkeys(names))
    if requested is not None:
        unknown = sorted(set(requested) - {benchmark.name for benchmark in BENCHMARKS})
        if unknown:
            # A silently empty report looks like a successful measurement of
            # nothing, which is the worst possible outcome of a typo.
            raise ValueError(
                "unknown benchmark name(s): " + ", ".join(unknown)
                + "; available: " + ", ".join(benchmark.name for benchmark in BENCHMARKS)
            )
    selected = [benchmark for benchmark in BENCHMARKS
                if requested is None or benchmark.name in set(requested)]
    results = []
    started = time.perf_counter()
    with HostTimeline(interval=sample_interval) as timeline:
        for benchmark in selected:
            results.append(_measure(benchmark, iterations))
    return {
        "schema_version": SCHEMA_VERSION,
        "meta": {
            "kind": "microbench",
            "iterations": iterations,
            "started_utc": timeline.samples[0].at_utc if timeline.samples else None,
            "finished_utc": timeline.samples[-1].at_utc if timeline.samples else None,
            "wall_seconds": round(time.perf_counter() - started, 3),
            "command": " ".join(sys.argv),
        },
        "environment": describe_environment(),
        "host": {"summary": summarize_samples(list(timeline.samples)),
                 "samples": [sample.as_dict() for sample in timeline.samples]},
        "benchmarks": results,
    }


def to_markdown(report: dict[str, Any]) -> str:
    meta = report.get("meta", {})
    environment = report.get("environment", {})
    host = (report.get("host") or {}).get("summary", {})
    cpu = host.get("cpu_total_percent", {})
    lines = [
        "# Host microbenchmarks",
        "",
        f"- Started: {meta.get('started_utc')}  Finished: {meta.get('finished_utc')}",
        f"- Iterations per benchmark: {meta.get('iterations')}",
        f"- Python: {environment.get('python_implementation')}"
        f" {environment.get('python_version')}",
        f"- Platform: {environment.get('platform')}",
        f"- Host CPU during the run (mean / max): {cpu.get('mean')} / {cpu.get('max')}",
        "",
        "| Benchmark | n | min | median | p90 | max |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for entry in report.get("benchmarks", []):
        if entry.get("error") and not entry.get("iterations"):
            lines.append(f"| `{entry['name']}` | 0 | unavailable: {entry['error']} | | | |")
            continue
        lines.append(
            f"| `{entry['name']}` | {entry['iterations']}"
            f" | {entry['min_seconds'] * 1000:.1f} ms"
            f" | {entry['median_seconds'] * 1000:.1f} ms"
            f" | {entry['p90_seconds'] * 1000:.1f} ms"
            f" | {entry['max_seconds'] * 1000:.1f} ms |"
        )
    problems = [entry for entry in report.get("benchmarks", []) if entry.get("error")]
    if problems:
        lines += ["", "Incomplete benchmarks:", ""]
        for entry in problems:
            lines.append(
                f"- `{entry['name']}`: {entry['error']}"
                f" after {entry.get('iterations') or 0} completed iteration(s)"
            )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    iterations = 8
    names: list[str] | None = None
    output: Path | None = None
    index = 0
    while index < len(arguments):
        item = arguments[index]
        if item == "--iterations":
            iterations = int(arguments[index + 1])
            index += 2
        elif item == "--name":
            names = list(names or []) + [arguments[index + 1]]
            index += 2
        elif item == "--json-out":
            output = Path(arguments[index + 1])
            index += 2
        elif item == "--markdown":
            print(to_markdown(run_microbenchmarks(iterations=iterations, names=names)))
            return 0
        else:
            raise SystemExit(f"unknown argument: {item}")
    report = run_microbenchmarks(iterations=iterations, names=names)
    text = json.dumps(report, indent=2)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0
