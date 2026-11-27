"""Instrumented ``unittest`` execution with per-test timing and spawn tracing.

The runner observes a suite; it does not alter what the suite asserts.  Every
number it records is labelled with the host conditions observed while it ran,
because a shared laboratory VM does not produce repeatable wall-clock times.

Three rules keep a report honest about its own provenance:

* the checkout identity is read **before and after** the run, so a tree that
  changed underneath the measurement is reported as unidentified instead of
  being attributed to whatever ``HEAD`` happened to say afterwards;
* which package the parent interpreter actually imported is recorded, because
  on this VM an installed wheel can differ from the checkout being measured;
* an outcome that cannot be attributed to a running test (a module or class
  fixture failure) is kept as a suite-level issue rather than dropped, so a run
  is never "unsuccessful" without saying why.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import math
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
from .sanitize import redact_text

# Bumped when the recorded shape changes enough that an older report cannot be
# compared like for like.  Version 1 reports carry no package or before/after
# source identity, so they remain readable but cannot be qualified.
SCHEMA_VERSION = 2

_GIT_EXECUTABLES = ("git", "git.exe")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _basename(command: object) -> str:
    """Best-effort executable name for a ``Popen``-style argument."""
    if isinstance(command, (bytes, bytearray)):
        command = command.decode("utf-8", "replace")
    if isinstance(command, str):
        return Path(command).name.lower()
    if isinstance(command, os.PathLike):
        return Path(os.fspath(command)).name.lower()
    if isinstance(command, (list, tuple)) and command:
        return _basename(command[0])
    return ""


def _describe(err: object) -> str:
    """Render an exception triple without keeping more of it than is useful."""
    try:
        name = err[0].__name__  # type: ignore[index]
        text = str(err[1]) if len(err) > 1 else ""  # type: ignore[index]
    except (TypeError, IndexError):
        name, text = "Exception", ""
    return redact_text(f"{name}: {text}", roots=_private_roots())[:400]


def _private_roots() -> tuple[str, ...]:
    """Directories that must never appear in a recorded message.

    The working directory is always included: it usually *is* the checkout a
    test names in an assertion, and it contains the account name on every
    platform.
    """
    try:
        return (os.getcwd(),)
    except OSError:  # pragma: no cover - defensive
        return ()


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
    git_spawn_seconds: float = 0.0
    git_run_seconds: float = 0.0
    python_spawns: int = 0
    git_commands: dict[str, int] = field(default_factory=dict)
    working_set_before: int | None = None
    working_set_after: int | None = None
    working_set_peak_before: int | None = None
    working_set_peak_after: int | None = None
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
            # Creation latency and whole-call duration are different numbers:
            # the first is paid even by a ``Popen`` the test manages itself, the
            # second only exists for ``subprocess.run`` calls.
            "git_spawn_seconds": round(self.git_spawn_seconds, 6),
            "git_run_seconds": round(self.git_run_seconds, 6),
            "python_spawns": self.python_spawns,
            "git_commands": dict(sorted(self.git_commands.items(), key=lambda item: (-item[1], item[0]))),
            "working_set_before": self.working_set_before,
            "working_set_after": self.working_set_after,
            "working_set_peak_before": self.working_set_peak_before,
            "working_set_peak_after": self.working_set_peak_after,
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

    The hooks are process-wide, so only one traced run can exist at a time.
    Installing a second tracer raises instead of silently interleaving two
    runs' events or restoring hooks the other tracer replaced.
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
        _claim_instrumentation(self)
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
        _release_instrumentation(self)

    def _record(self, kind: str, command: object, seconds: float) -> None:
        executable = _basename(command)
        event: dict[str, Any] = {"kind": kind, "exe": executable, "seconds": seconds}
        if kind == "spawn" and self._sample_commands and executable in _GIT_EXECUTABLES:
            event["git_subcommand"] = _git_subcommand(command)
        with self._lock:
            self._events.append(event)

    def drain(self) -> list[dict[str, Any]]:
        with self._lock:
            events, self._events = self._events, []
        return events


# Instrumentation patches process-wide objects (``subprocess`` and
# ``unittest.TestCase``), so two overlapping runs would attribute each other's
# events.  Overlap is a programming error, not something to absorb silently.
_INSTRUMENTATION_OWNER: object | None = None
_INSTRUMENTATION_LOCK = threading.Lock()


def _claim_instrumentation(owner: object) -> None:
    global _INSTRUMENTATION_OWNER
    with _INSTRUMENTATION_LOCK:
        if _INSTRUMENTATION_OWNER is not None and _INSTRUMENTATION_OWNER is not owner:
            raise RuntimeError(
                "an instrumented run is already active in this process; the "
                "subprocess and fixture hooks are process-wide and cannot be "
                "nested or overlapped"
            )
        _INSTRUMENTATION_OWNER = owner


def _release_instrumentation(owner: object) -> None:
    global _INSTRUMENTATION_OWNER
    with _INSTRUMENTATION_LOCK:
        if _INSTRUMENTATION_OWNER is owner:
            _INSTRUMENTATION_OWNER = None


@dataclass
class _Active:
    record: TestRecord
    started: float
    cpu_started: float


class _TimedResult(unittest.TextTestResult):
    """Text result that additionally records per-test cost."""

    def __init__(self, stream, descriptions, verbosity, *, records, issues, tracer,
                 sample_tests, iteration=0):
        super().__init__(stream, descriptions, verbosity)
        self._records: list[TestRecord] = records
        self._issues: list[dict[str, Any]] = issues
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
            record.working_set_peak_before = memory.peak_working_set_bytes
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
            record.working_set_peak_after = memory.peak_working_set_bytes
            # The high-water mark is process-wide and only ever grows, so the
            # honest per-test figure is how much it grew *during* the test:
            # peak at stop minus peak at start.  Subtracting the current working
            # set instead would charge a test for every earlier test's peak.
            if (record.working_set_peak_before is not None
                    and memory.peak_working_set_bytes is not None):
                record.peak_working_set_delta = max(
                    0, memory.peak_working_set_bytes - record.working_set_peak_before
                )
        if self._tracer is not None:
            for event in self._tracer.drain():
                if event["kind"] == "spawn":
                    record.spawn_count += 1
                    record.spawn_seconds += event["seconds"]
                    record.spawn_max_seconds = max(record.spawn_max_seconds, event["seconds"])
                    if event["exe"] in _GIT_EXECUTABLES:
                        record.git_calls += 1
                        record.git_spawn_seconds += event["seconds"]
                        subcommand = event.get("git_subcommand")
                        if subcommand:
                            record.git_commands[subcommand] = record.git_commands.get(subcommand, 0) + 1
                    elif event["exe"].startswith("python"):
                        record.python_spawns += 1
                else:
                    record.subprocess_calls += 1
                    record.subprocess_seconds += event["seconds"]
                    if event["exe"] in _GIT_EXECUTABLES:
                        record.git_run_seconds += event["seconds"]
        self._records.append(record)

    # -- outcomes ----------------------------------------------------------
    def addSuccess(self, test):
        super().addSuccess(test)
        self._set_outcome("success", test=test)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._set_outcome("failure", err, test=test)

    def addError(self, test, err):
        super().addError(test, err)
        self._set_outcome("error", err, test=test)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._set_outcome("skipped", message=str(reason), test=test)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._set_outcome("expected-failure", err, test=test)

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._set_outcome("unexpected-success", test=test)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is None:
            return
        # unittest distinguishes a failed subtest by the test's own
        # ``failureException``, not by ``AssertionError`` specifically.
        failure_type = getattr(test, "failureException", AssertionError)
        try:
            is_failure = issubclass(err[0], failure_type)
        except TypeError:
            is_failure = False
        self._set_outcome("failure" if is_failure else "error", err, test=test)

    def _set_outcome(self, outcome: str, err: object | None = None, message: str = "",
                     test: object | None = None) -> None:
        if self._active is None:
            self._note_suite_issue(test, outcome, err, message)
            return
        record = self._active.record
        # Failures take precedence over success; skips never mask a failure.
        rank = {"unknown": 0, "success": 1, "skipped": 1, "expected-failure": 1,
                "unexpected-success": 2, "failure": 3, "error": 4}
        if rank.get(outcome, 0) < rank.get(record.outcome, 0):
            # A lower-ranked callback must not replace the message either: the
            # outcome and its explanation always describe the same event.
            return
        record.outcome = outcome
        if err is not None:
            record.message = _describe(err)
        elif message:
            record.message = redact_text(message, roots=_private_roots())[:400]

    def _note_suite_issue(self, test: object | None, outcome: str, err: object | None,
                          message: str) -> None:
        """Keep an outcome that happened outside any active test.

        A module import error or a failing ``setUpClass`` reaches
        ``addError`` with no test running.  The run is unsuccessful, so
        dropping the reason would leave a report that contradicts itself.
        """
        try:
            identifier = test.id() if hasattr(test, "id") else str(test)
        except Exception:  # pragma: no cover - defensive
            identifier = str(test)
        self._issues.append({
            "test_id": redact_text(identifier, roots=_private_roots())[:400],
            "outcome": outcome,
            "message": (_describe(err) if err is not None
                        else redact_text(message, roots=_private_roots()))[:400],
        })

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
    suite_errors: list[dict[str, Any]] = field(default_factory=list)
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

    @property
    def suite_outcomes(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for issue in self.suite_errors:
            counts[issue["outcome"]] = counts.get(issue["outcome"], 0) + 1
        return dict(sorted(counts.items()))

    def as_dict(self) -> dict[str, Any]:
        from .hostload import summarize_samples

        sampling_meta = self.meta.get("host_sampling") or {}
        interval = float(sampling_meta.get("interval") or 0.0)
        expected = max(2, int(self.wall_seconds / interval) + 2) if interval > 0 else None
        return {
            "schema_version": SCHEMA_VERSION,
            "meta": {
                **self.meta,
                "started_utc": self.started_utc,
                "finished_utc": self.finished_utc,
                "wall_seconds": round(self.wall_seconds, 6),
                "tests": len(self.records),
                "outcomes": self.outcomes,
                "suite_errors": len(self.suite_errors),
                "suite_outcomes": self.suite_outcomes,
                "successful": self.successful,
            },
            "environment": describe_environment(),
            "host": {
                "summary": summarize_samples(self.samples),
                "sampling": {
                    "interval": interval or None,
                    "samples": len(self.samples),
                    "expected_at_least": expected,
                    "complete": bool(
                        interval > 0
                        and expected is not None
                        and len(self.samples) >= expected - 1
                        and not sampling_meta.get("error")
                    ),
                    "error": sampling_meta.get("error"),
                    "failures": sampling_meta.get("failures", 0),
                },
                "samples": [sample.as_dict() for sample in self.samples],
            },
            "tests": [record.as_dict() for record in self.records],
            "suite_errors": list(self.suite_errors),
        }


_IDENTITY_FIELDS = ("revision", "branch", "dirty", "worktree_digest")


def _source_revision(directory: Path) -> dict[str, Any]:
    """Describe the checkout a run claims to measure, without assuming success.

    Every Git call is checked.  A failed ``rev-parse`` or ``status`` yields an
    unknown value rather than an empty one, because "clean" and "no repository"
    look identical when only stdout is read.

    A digest of the status output and of ``git diff --binary HEAD`` pins the
    working tree's uncommitted difference from ``HEAD``.  Without it, two runs
    that both say "dirty at revision X" cannot be told apart from two different
    trees.

    Only argument names and a failure class are retained.  Git's stderr quotes
    paths, and a measurement report is not the place for them.
    """
    directory = Path(directory)
    info: dict[str, Any] = {
        "revision": None,
        "branch": None,
        "dirty": None,
        "worktree_digest": None,
        "observed_utc": _utc_now(),
        "complete": False,
        "failed_commands": [],
    }

    def git(*arguments: str) -> bytes | None:
        try:
            completed = subprocess.run(
                ["git", *arguments], cwd=directory, capture_output=True,
                timeout=20, stdin=subprocess.DEVNULL,
            )
        except (OSError, subprocess.SubprocessError) as error:
            info["failed_commands"].append(
                {"arguments": list(arguments), "failure": type(error).__name__}
            )
            return None
        if completed.returncode != 0:
            info["failed_commands"].append(
                {"arguments": list(arguments), "returncode": completed.returncode}
            )
            return None
        return completed.stdout

    revision = git("rev-parse", "HEAD")
    if revision is not None:
        info["revision"] = revision.decode("ascii", "replace").strip() or None
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch is not None:
        info["branch"] = branch.decode("utf-8", "replace").strip() or None
    status = git("status", "--porcelain")
    if status is not None:
        info["dirty"] = bool(status.strip())
    diff = git("diff", "--binary", "HEAD") if info["revision"] else None
    if status is not None and diff is not None:
        digest = hashlib.sha256()
        digest.update(status)
        digest.update(b"\0")
        digest.update(diff)
        info["worktree_digest"] = digest.hexdigest()
    info["complete"] = all(
        info[field] is not None for field in ("revision", "branch", "dirty", "worktree_digest")
    )
    return info


def _package_identity(source_directory: Path) -> dict[str, Any]:
    """Which package the parent interpreter actually imported.

    ``--source`` names a checkout; it does not prove that the code under
    measurement came from it.  On this VM another campaign's wheel sits in
    site-packages, so the two can differ without any visible symptom.
    """
    import deskmate_formats

    identity: dict[str, Any] = {
        "name": "deskmate_formats",
        "version": getattr(deskmate_formats, "__version__", None),
        "distribution_version": None,
        "origin": None,
        "expected_origin": None,
        "matches_source": None,
        "source_on_path": None,
        "source_first": None,
        "modules": {},
    }
    module_file = getattr(deskmate_formats, "__file__", None)
    if module_file:
        identity["origin"] = str(Path(module_file).resolve().parent)
    try:
        identity["distribution_version"] = importlib.metadata.version("deskmate-formats")
    except importlib.metadata.PackageNotFoundError:
        identity["distribution_version"] = None
    expected = (Path(source_directory) / "src" / "deskmate_formats").resolve()
    identity["expected_origin"] = str(expected)
    if identity["origin"] is not None:
        origin_path = Path(identity["origin"])
        try:
            identity["matches_source"] = origin_path.samefile(expected)
        except OSError:
            identity["matches_source"] = (
                os.path.normcase(str(origin_path)) == os.path.normcase(str(expected))
            )
    source_root = str(expected.parent)
    try:
        entries = [os.path.normcase(str(Path(entry or os.curdir).resolve())) for entry in sys.path]
    except (OSError, ValueError):  # pragma: no cover - defensive
        entries = []
    normalised_source = os.path.normcase(source_root)
    identity["source_on_path"] = normalised_source in entries
    identity["source_first"] = bool(entries) and entries[0] == normalised_source
    for name in ("runner", "report", "hostload", "cli", "sanitize"):
        module = sys.modules.get(f"deskmate_formats.perf.{name}")
        identity["modules"][name] = getattr(module, "__file__", None)
    return identity


def _invocation() -> dict[str, Any]:
    """The command shape, with path-like arguments redacted."""
    argv = list(sys.argv)
    return {
        "program": Path(argv[0]).name if argv else "",
        "argument_count": max(0, len(argv) - 1),
        "arguments": redact_text(" ".join(argv)),
    }


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
    if not (isinstance(sample_interval, (int, float))
            and math.isfinite(float(sample_interval))
            and float(sample_interval) > 0):
        raise ValueError(
            f"sample_interval must be a positive finite number of seconds, not {sample_interval!r}"
        )
    if isinstance(iteration, int) and iteration < 0:
        raise ValueError(f"iteration must not be negative, not {iteration!r}")

    directory = Path(source_directory) if source_directory is not None else Path.cwd()
    discovered = suite.countTestCases()
    records: list[TestRecord] = []
    issues: list[dict[str, Any]] = []
    tracer = (SubprocessTracer(sample_commands=trace_git_commands)
              if (trace_processes or trace_git_commands) else None)
    timer = _FixtureTimer()
    stream = stream if stream is not None else sys.stderr

    class Result(_TimedResult):
        def __init__(self, result_stream, descriptions, result_verbosity):
            super().__init__(result_stream, descriptions, result_verbosity,
                             records=records, issues=issues, tracer=tracer,
                             sample_tests=sample_tests, iteration=iteration)
            # Fixture hooks reach the live result through the timer.
            timer._result = self

    runner = unittest.TextTestRunner(stream=stream, verbosity=verbosity, resultclass=Result)
    # Identity first: a checkout that is already unreadable must not be
    # attributed to whatever it says after the run.
    source_before = _source_revision(directory)
    package = _package_identity(directory)
    started = _utc_now()
    clock = time.perf_counter()
    samples: list[HostSample] = []
    timeline: HostTimeline | None = None
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

    source_after = _source_revision(directory)
    stable = bool(
        source_before["complete"]
        and source_after["complete"]
        and all(source_before[field] == source_after[field] for field in _IDENTITY_FIELDS)
    )
    if stable:
        source = dict(source_after, state="stable")
    else:
        # A half-known or moving identity must not be presented as a revision.
        source = {
            "revision": None,
            "branch": None,
            "dirty": None,
            "worktree_digest": None,
            "observed_utc": source_after["observed_utc"],
            "complete": False,
            "state": "changed" if source_before["complete"] and source_after["complete"] else "unknown",
            "failed_commands": list(source_before["failed_commands"])
            + list(source_after["failed_commands"]),
        }

    run = RunResult(
        records=records,
        samples=samples,
        suite_errors=issues,
        started_utc=started,
        finished_utc=_utc_now(),
        wall_seconds=time.perf_counter() - clock,
        successful=result.wasSuccessful(),
        meta={
            "label": label,
            "profile": profile,
            "trace_processes": trace_processes,
            "trace_git_commands": trace_git_commands,
            "sample_interval": float(sample_interval),
            "sample_tests": sample_tests,
            "iteration": iteration,
            "iterations": 1,
            "discovered_tests": discovered,
            "executed_tests": len(records),
            "invocation": _invocation(),
            "source_before": source_before,
            "source_after": source_after,
            "source": source,
            "source_changed": not stable,
            "package": package,
            "host_sampling": {
                "interval": float(sample_interval),
                "error": timeline.error if timeline is not None else "timeline not started",
                "failures": timeline.failures if timeline is not None else 0,
            },
        },
    )
    return run


def iter_records(result: RunResult) -> Iterable[TestRecord]:
    return iter(result.records)


def python_identity() -> str:
    return f"{platform.python_implementation()} {platform.python_version()}"
