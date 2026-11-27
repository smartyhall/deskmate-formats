"""Instrumented ``unittest`` execution with per-test timing and spawn tracing.

The runner observes a suite; it does not alter what the suite asserts.  Every
number it records is labelled with the host conditions observed while it ran,
because a shared laboratory VM does not produce repeatable wall-clock times.
"""

from __future__ import annotations

from dataclasses import dataclass, field, field
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import subprocess
import sys
import threading
import time
import unittest
from typing import Any, Iterable

from .hostload import HostSample, HostTimeline, describe_environment, process_memory


SCHEMA_VERSION = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _basename(command: object) -> str:
    """Best-effort executable name for a ``Popen``-style argument."""
    if isinstance(command, (bytes, bytearray)):
        command = command.decode("utf-8", "replace")
    if isinstance(command, str):
        return Path(command).name.lower()
    if isinstance(command, (list, tuple)) and command:
        return _basename(command[0])
    return ""


@dataclass
class TestRecord:
    test_id: str
    module: str
    case: str
    name: str
    outcome: str = "unknown"
    message: str = ""
    wall_seconds: float = 0.0
    cpu_seconds: float = 0.0
    setup_seconds: float = 0.0
    teardown_seconds: float = 0.0
    subprocess_calls: int = 0
    subprocess_seconds: float = 0.0
    spawn_count: int = 0
    spawn_seconds: float = 0.0
    spawn_max_seconds: float = 0.0
    git_calls: int = 0
    git_seconds: float = 0.0
    python_spawns: int = 0
    git_commands: dict[str, int] = field(default_factory=dict)
    working_set_before: int | None = None
    working_set_after: int | None = None
    peak_working_set_delta: int | None = None
    host: dict[str, Any] | None = None
    iteration: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "module": self.module,
            "case": self.case,
            "name": self.name,
            "outcome": self.outcome,
            "message": self.message,
            "wall_seconds": round(self.wall_seconds, 6),
            "cpu_seconds": round(self.cpu_seconds, 6),
            "setup_seconds": round(self.setup_seconds, 6),
            "teardown_seconds": round(self.teardown_seconds, 6),
            "subprocess_calls": self.subprocess_calls,
            "subprocess_seconds": round(self.subprocess_seconds, 6),
            "spawn_count": self.spawn_count,
            "spawn_seconds": round(self.spawn_seconds, 6),
            "spawn_max_seconds": round(self.spawn_max_seconds, 6),
            "git_calls": self.git_calls,
            "git_seconds": round(self.git_seconds, 6),
            "python_spawns": self.python_spawns,
            "git_commands": dict(sorted(self.git_commands.items(), key=lambda item: (-item[1], item[0]))),
            "working_set_before": self.working_set_before,
            "working_set_after": self.working_set_after,
            "peak_working_set_delta": self.peak_working_set_delta,
            "host": self.host,
            "iteration": self.iteration,
        }


def _git_subcommand(command: object) -> str:
    """Return the Git subcommand of an argument vector, best effort.

    Global options are skipped so that ``git -c a=b rev-parse`` and
    ``git rev-parse`` are reported together.  An argument vector this cannot
    interpret is reported as ``unknown`` rather than guessed at.
    """
    if isinstance(command, (str, bytes)):
        parts = (command.decode("utf-8", "replace") if isinstance(command, bytes)
                 else command).split()
    else:
        try:
            parts = [part.decode("utf-8", "replace") if isinstance(part, bytes) else str(part)
                     for part in command]  # type: ignore[union-attr]
        except TypeError:
            return "unknown"
    index = 1  # element 0 is the program itself
    while index < len(parts):
        token = parts[index]
        if token in ("-c", "-C", "--git-dir", "--work-tree", "--exec-path"):
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token
    return "unknown"


class SubprocessTracer:
    """Record spawn latency and total subprocess wall time, per test.

    Both ``Popen.__init__`` and ``subprocess.run`` are wrapped, so ``run``
    contributes one *call* and one *spawn*.  The wrapper is observation only:
    arguments, environment, pipes and exit status pass through untouched.

    With ``sample_commands`` the Git subcommand of each spawn is counted as
    well.  It is off by default because it keeps a string per spawn; it changes
    no argument, pipe or environment either way.
    """

    def __init__(self, *, sample_commands: bool = False) -> None:
        self._lock = threading.Lock()
        self._events: list[dict[str, Any]] = []
        self._installed = False
        self._originals: list[tuple[object, str, object]] = []
        self._sample_commands = sample_commands

    def install(self) -> None:
        if self._installed:
            return
        tracer = self
        original_init = subprocess.Popen.__init__
        original_run = subprocess.run

        def timed_init(instance, args, *rest, **kwargs):
            start = time.perf_counter()
            original_init(instance, args, *rest, **kwargs)
            tracer._record("spawn", args, time.perf_counter() - start)

        def timed_run(*popenargs, **kwargs):
            start = time.perf_counter()
            try:
                return original_run(*popenargs, **kwargs)
            finally:
                command = popenargs[0] if popenargs else kwargs.get("args")
                tracer._record("run", command, time.perf_counter() - start)

        self._originals = [(subprocess.Popen, "__init__", original_init),
                           (subprocess, "run", original_run)]
        subprocess.Popen.__init__ = timed_init
        subprocess.run = timed_run
        self._installed = True

    def uninstall(self) -> None:
        if not self._installed:
            return
        for owner, name, original in self._originals:
            setattr(owner, name, original)
        self._installed = False

    def _record(self, kind: str, command: object, seconds: float) -> None:
        executable = _basename(command)
        event: dict[str, Any] = {"kind": kind, "exe": executable, "seconds": seconds}
        if kind == "spawn" and self._sample_commands and executable in ("git", "git.exe"):
            event["git_subcommand"] = _git_subcommand(command)
        with self._lock:
            self._events.append(event)

    def drain(self) -> list[dict[str, Any]]:
        with self._lock:
            events, self._events = self._events, []
        return events


@dataclass
class _Active:
    record: TestRecord
    started: float
    cpu_started: float


class _TimedResult(unittest.TextTestResult):
    """Text result that additionally records per-test cost."""

    def __init__(self, stream, descriptions, verbosity, *, records, tracer, sample_tests,
                 iteration=0):
        super().__init__(stream, descriptions, verbosity)
        self._records: list[TestRecord] = records
        self._tracer = tracer
        self._sample_tests = sample_tests
        self._iteration = iteration
        self._active: _Active | None = None
        self._setup_seconds = 0.0
        self._teardown_seconds = 0.0

    # -- lifecycle ---------------------------------------------------------
    def startTest(self, test):
        super().startTest(test)
        identifier = test.id()
        parts = identifier.split(".")
        record = TestRecord(
            test_id=identifier,
            # Keep dotted package prefixes: ``pkg.test_alpha.Case.test_one`` is
            # in module ``pkg.test_alpha``, not ``pkg``.
            module=".".join(parts[:-2]) if len(parts) > 2 else "",
            case=parts[-2] if len(parts) > 1 else "",
            name=parts[-1],
            host=None,
            iteration=self._iteration,
        )
        if self._sample_tests:
            from .hostload import default_sampler

            record.host = default_sampler().sample().as_dict()
        memory = process_memory()
        if memory is not None:
            record.working_set_before = memory.working_set_bytes
        if self._tracer is not None:
            self._tracer.drain()  # discard anything outside a test
        self._setup_seconds = 0.0
        self._teardown_seconds = 0.0
        self._active = _Active(record=record, started=time.perf_counter(),
                               cpu_started=time.process_time())

    def stopTest(self, test):
        super().stopTest(test)
        active = self._active
        self._active = None
        if active is None:
            return
        record = active.record
        record.wall_seconds = time.perf_counter() - active.started
        record.cpu_seconds = time.process_time() - active.cpu_started
        record.setup_seconds = self._setup_seconds
        record.teardown_seconds = self._teardown_seconds
        memory = process_memory()
        if memory is not None:
            record.working_set_after = memory.working_set_bytes
            if record.working_set_before is not None:
                record.peak_working_set_delta = max(
                    0, memory.peak_working_set_bytes - record.working_set_before
                )
        if self._tracer is not None:
            for event in self._tracer.drain():
                if event["kind"] == "spawn":
                    record.spawn_count += 1
                    record.spawn_seconds += event["seconds"]
                    record.spawn_max_seconds = max(record.spawn_max_seconds, event["seconds"])
                    if event["exe"] in ("git", "git.exe"):
                        record.git_calls += 1
                        record.git_seconds += event["seconds"]
                        subcommand = event.get("git_subcommand")
                        if subcommand:
                            record.git_commands[subcommand] = record.git_commands.get(subcommand, 0) + 1
                    elif event["exe"].startswith("python"):
                        record.python_spawns += 1
                else:
                    record.subprocess_calls += 1
                    record.subprocess_seconds += event["seconds"]
        self._records.append(record)

    # -- outcomes ----------------------------------------------------------
    def addSuccess(self, test):
        super().addSuccess(test)
        self._set_outcome("success")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._set_outcome("failure", err)

    def addError(self, test, err):
        super().addError(test, err)
        self._set_outcome("error", err)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._set_outcome("skipped", message=str(reason))

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._set_outcome("expected-failure", err)

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._set_outcome("unexpected-success")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None and self._active is not None:
            self._set_outcome("error" if issubclass(err[0], Exception) and not issubclass(
                err[0], AssertionError) else "failure", err)

    def _set_outcome(self, outcome: str, err: object | None = None, message: str = "") -> None:
        if self._active is None:
            return
        record = self._active.record
        # Failures take precedence over success; skips never mask a failure.
        rank = {"unknown": 0, "success": 1, "skipped": 1, "expected-failure": 1,
                "unexpected-success": 2, "failure": 3, "error": 4}
        if rank.get(outcome, 0) >= rank.get(record.outcome, 0):
            record.outcome = outcome
        if err is not None:
            try:
                name = err[0].__name__  # type: ignore[index]
                text = str(err[1]) if len(err) > 1 else ""  # type: ignore[index]
            except (TypeError, IndexError):
                name, text = "Exception", ""
            record.message = f"{name}: {text}"[:400]
        elif message:
            record.message = message[:400]

    # -- fixture timing ----------------------------------------------------
    def note_setup(self, seconds: float) -> None:
        self._setup_seconds += seconds

    def note_teardown(self, seconds: float) -> None:
        self._teardown_seconds += seconds


class _FixtureTimer:
    """Time ``setUp``/``tearDown`` per test by wrapping the unittest hooks."""

    def __init__(self) -> None:
        self._originals: list[tuple[str, object]] = []
        self._result: _TimedResult | None = None

    def install(self) -> None:
        timer = self

        for name, note in (("_callSetUp", "note_setup"), ("_callTearDown", "note_teardown")):
            original = getattr(unittest.TestCase, name, None)
            if original is None:
                continue
            self._originals.append((name, original))

            def wrapper(instance, _original=original, _note=note):
                start = time.perf_counter()
                try:
                    return _original(instance)
                finally:
                    result = timer._result
                    if result is not None:
                        getattr(result, _note)(time.perf_counter() - start)

            setattr(unittest.TestCase, name, wrapper)

    def uninstall(self) -> None:
        for name, original in self._originals:
            setattr(unittest.TestCase, name, original)
        self._originals.clear()


@dataclass
class RunResult:
    records: list[TestRecord] = field(default_factory=list)
    samples: list[HostSample] = field(default_factory=list)
    started_utc: str = ""
    finished_utc: str = ""
    wall_seconds: float = 0.0
    successful: bool = False
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def outcomes(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in self.records:
            counts[record.outcome] = counts.get(record.outcome, 0) + 1
        return dict(sorted(counts.items()))

    def as_dict(self) -> dict[str, Any]:
        from .hostload import summarize_samples

        return {
            "schema_version": SCHEMA_VERSION,
            "meta": {
                **self.meta,
                "started_utc": self.started_utc,
                "finished_utc": self.finished_utc,
                "wall_seconds": round(self.wall_seconds, 6),
                "tests": len(self.records),
                "outcomes": self.outcomes,
                "successful": self.successful,
            },
            "environment": describe_environment(),
            "host": {
                "summary": summarize_samples(self.samples),
                "samples": [sample.as_dict() for sample in self.samples],
            },
            "tests": [record.as_dict() for record in self.records],
        }


def _source_revision(directory: Path) -> dict[str, Any]:
    """Record the exact revision, without requiring a Git checkout."""
    info: dict[str, Any] = {"revision": None, "dirty": None, "branch": None}
    try:
        info["revision"] = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=directory, capture_output=True,
            timeout=20, text=True,
        ).stdout.strip() or None
        info["branch"] = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=directory,
            capture_output=True, timeout=20, text=True,
        ).stdout.strip() or None
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=directory, capture_output=True,
            timeout=20, text=True,
        ).stdout
        info["dirty"] = bool(status.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return info


def run_suite(
    suite: unittest.TestSuite,
    *,
    label: str = "",
    profile: str = "",
    trace_processes: bool = False,
    trace_git_commands: bool = False,
    sample_interval: float = 5.0,
    sample_tests: bool = False,
    verbosity: int = 1,
    stream=None,
    source_directory: Path | None = None,
    iteration: int = 0,
) -> RunResult:
    """Run ``suite`` under instrumentation and return a serializable result."""
    records: list[TestRecord] = []
    tracer = (SubprocessTracer(sample_commands=trace_git_commands)
              if (trace_processes or trace_git_commands) else None)
    timer = _FixtureTimer()
    stream = stream if stream is not None else sys.stderr

    class Result(_TimedResult):
        def __init__(self, result_stream, descriptions, result_verbosity):
            super().__init__(result_stream, descriptions, result_verbosity,
                             records=records, tracer=tracer, sample_tests=sample_tests,
                             iteration=iteration)
            # Fixture hooks reach the live result through the timer.
            timer._result = self

    runner = unittest.TextTestRunner(stream=stream, verbosity=verbosity, resultclass=Result)
    started = _utc_now()
    clock = time.perf_counter()
    samples: list[HostSample] = []
    if tracer is not None:
        tracer.install()
    timer.install()
    try:
        with HostTimeline(interval=sample_interval) as timeline:
            result = runner.run(suite)
        # After ``__exit__``, which appends the closing sample; copying inside
        # the block loses the last interval, and on a short run that is the only
        # sample carrying a CPU delta.
        samples = list(timeline.samples)
    finally:
        timer.uninstall()
        if tracer is not None:
            tracer.uninstall()

    run = RunResult(
        records=records,
        samples=samples,
        started_utc=started,
        finished_utc=_utc_now(),
        wall_seconds=time.perf_counter() - clock,
        successful=result.wasSuccessful(),
        meta={
            "label": label,
            "profile": profile,
            "trace_processes": trace_processes,
            "trace_git_commands": trace_git_commands,
            "sample_interval": sample_interval,
            "sample_tests": sample_tests,
            "iteration": iteration,
            "command": " ".join(sys.argv),
            "working_directory": os.getcwd(),
            "source": _source_revision(source_directory or Path.cwd()),
        },
    )
    return run


def iter_records(result: RunResult) -> Iterable[TestRecord]:
    return iter(result.records)


def python_identity() -> str:
    return f"{platform.python_implementation()} {platform.python_version()}"
