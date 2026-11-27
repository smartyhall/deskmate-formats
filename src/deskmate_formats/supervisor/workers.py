"""Provider-independent worker descriptions with explicit capability negotiation.

Three worker classes exist today:

``deterministic``
    A bounded local procedure runner. No model inference, no session, no
    continuation. It really executes (see :mod:`deterministic`).
``codex``
    The pinned app-server protocol. Session, turn and interrupt semantics are
    implemented and covered by offline tests, but live model dispatch remains
    behind the existing authorization gates.
``freebuff``
    A supplementary coding agent operated manually through its desktop client.
    No supported programmatic dispatch or telemetry interface is verified, so
    the adapter advertises no capabilities rather than pretending.

Capabilities are advertised, never assumed. A caller must ask a worker whether
it supports an operation and must handle a refusal.
"""

from dataclasses import dataclass, field
from pathlib import Path

from . import deterministic, procedures

CAPABILITIES = frozenset((
    "prepare", "dispatch", "progress", "cancellation", "recovery",
    "artifacts", "session", "continuation", "steering", "usage",
))
KINDS = frozenset(("deterministic", "codex", "freebuff", "synthetic"))
RESOURCE_KINDS = frozenset(("source-read", "portable-tests", "synthetic-fixtures",
                            "worktree", "emulator", "account-allowance"))


class WorkerUnsupported(RuntimeError):
    """This worker does not implement the requested operation."""


class WorkerUnavailable(RuntimeError):
    """The capability exists but an authorization or environment gate blocks it."""


@dataclass(frozen=True, slots=True)
class WorkerDescriptor:
    worker_id: str
    kind: str
    capabilities: frozenset
    resources: tuple[str, ...]
    limitations: tuple[str, ...] = ()

    def supports(self, capability):
        return capability in self.capabilities

    def require(self, capability):
        if capability not in CAPABILITIES:
            raise WorkerUnsupported("unknown worker capability")
        if capability not in self.capabilities:
            raise WorkerUnsupported(f"worker {self.worker_id} does not support {capability}")
        return True


@dataclass(frozen=True, slots=True)
class WorkerHealth:
    state: str
    evidence: str
    observed_at_utc: str | None

    def available(self):
        return self.state == "available"


@dataclass(frozen=True, slots=True)
class WorkerResult:
    worker_id: str
    attempt_id: str
    state: str
    exit_status: object = None
    artifacts: tuple = ()
    evidence: tuple = ()
    measurements: tuple = ()
    limitations: tuple = ()

    def completed(self):
        return self.state == "completed"


def deterministic_descriptor(worker_id="deterministic-local"):
    return WorkerDescriptor(
        worker_id, "deterministic",
        frozenset(("prepare", "dispatch", "progress", "cancellation", "recovery", "artifacts")),
        tuple(sorted({"source-read", "portable-tests", "synthetic-fixtures"})),
        ("no model inference and therefore no usage measurement",
         "cooperating-owner custody, not an operating system sandbox",
         "no continuation or steering; one bounded attempt"))


def codex_descriptor(worker_id="codex-app-server"):
    return WorkerDescriptor(
        worker_id, "codex",
        frozenset(("prepare", "dispatch", "progress", "cancellation", "recovery",
                   "session", "continuation", "steering")),
        ("worktree",),
        ("live model dispatch remains behind explicit operator authorization",
         "usage and allowance telemetry are not verified for the pinned protocol",
         "effective Windows sandbox and tool restrictions remain unverified"))


def freebuff_descriptor(worker_id="freebuff-desktop"):
    return WorkerDescriptor(
        worker_id, "freebuff", frozenset(), ("worktree",),
        ("no supported programmatic session, dispatch, cancellation or event interface is verified",
         "desktop context and daily-hours meters are manual UI observations only",
         "no adapter is implemented; manual operation does not require one"))


class Worker:
    """Base contract. Unsupported operations raise instead of pretending."""

    descriptor: WorkerDescriptor

    def health(self):
        raise WorkerUnsupported("health is not implemented")

    def prepare(self, request):
        raise WorkerUnsupported("preparation is not implemented")

    def dispatch(self, attempt, *, authorization):
        raise WorkerUnsupported("dispatch is not implemented")

    def status(self, attempt):
        raise WorkerUnsupported("status is not implemented")

    def cancel(self, attempt, *, authorization):
        raise WorkerUnsupported("cancellation is not implemented")

    def recover(self, attempt):
        raise WorkerUnsupported("recovery is not implemented")

    def usage(self):
        raise WorkerUnsupported("usage reporting is not implemented")


class DeterministicWorker(Worker):
    """Executes a reviewed procedure in an owned attempt directory."""

    def __init__(self, descriptor=None):
        self.descriptor = descriptor or deterministic_descriptor()

    def health(self, *, interpreter=None):
        self.descriptor.require("dispatch")
        try:
            procedures.get("repository-audit")
        except procedures.ProcedureError as error:  # pragma: no cover - defensive
            return WorkerHealth("unavailable", str(error), None)
        minimum = Path(interpreter or __import__("sys").executable)
        return WorkerHealth("available" if minimum.is_file() else "unavailable",
                            "local reviewed procedure registry and pinned interpreter",
                            None)

    def prepare(self, request):
        self.descriptor.require("prepare")
        return deterministic.prepare(**request)

    def dispatch(self, attempt, *, authorization, reservation=None):
        self.descriptor.require("dispatch")
        outcome = deterministic.run(attempt.directory, authorization=authorization,
                                    reservation=reservation)
        return WorkerResult(self.descriptor.worker_id, outcome["attempt_id"], outcome["state"],
                            outcome["exit_status"], tuple(outcome.get("artifacts") or ()),
                            (("stdout", outcome["stdout"]["sha256"]),
                             ("stderr", outcome["stderr"]["sha256"])),
                            (), tuple(outcome.get("limitations") or ()))

    def status(self, attempt):
        self.descriptor.require("progress")
        return deterministic.status(attempt.directory)

    def cancel(self, attempt, *, authorization):
        self.descriptor.require("cancellation")
        return deterministic.cancel(attempt.directory, authorization=authorization)

    def recover(self, attempt):
        self.descriptor.require("recovery")
        return deterministic.recover(attempt.directory)

    def usage(self):
        return ({"metric": "model_inference", "value": 0, "unit": "turns",
                 "scope": "worker", "semantics": "cumulative", "source": "procedure-registry",
                 "known": True},)


class CodexWorker(Worker):
    """Reports the existing protocol capabilities without granting dispatch."""

    def __init__(self, descriptor=None):
        self.descriptor = descriptor or codex_descriptor()

    def health(self):
        return WorkerHealth("unavailable",
                            "live gates: no verified OS boundary; "
                            "effective sandbox, authentication and tool restrictions unverified",
                            None)

    def prepare(self, request):
        raise WorkerUnavailable("Codex dispatch requires the existing exact-plan operator grant")

    def dispatch(self, attempt, *, authorization):
        raise WorkerUnavailable("Codex dispatch requires the existing exact-plan operator grant")

    def usage(self):
        return ()


class FreebuffWorker(Worker):
    """Declares no programmatic capability; manual use is outside the adapter."""

    def __init__(self, descriptor=None):
        self.descriptor = descriptor or freebuff_descriptor()

    def health(self):
        return WorkerHealth("unknown", "no verified programmatic interface", None)


@dataclass
class SyntheticWorker(Worker):
    """Deterministic in-memory double for multi-worker demonstrations and tests."""

    descriptor: WorkerDescriptor
    script: dict = field(default_factory=dict)
    calls: list = field(default_factory=list)

    def __init__(self, descriptor=None):
        self.descriptor = descriptor or WorkerDescriptor(
            "synthetic-" + str(id(self) % 1000), "synthetic",
            frozenset(("prepare", "dispatch", "progress", "cancellation", "recovery",
                       "session", "usage")),
            ("source-read",), ("synthetic only; performs no real work",))
        self.script = {"state": "completed", "exit_status": 0}
        self.calls = []

    def health(self):
        return WorkerHealth("available", "synthetic demonstration double", None)

    def prepare(self, request):
        self.calls.append(("prepare", request))
        return {"attempt_id": "synthetic-attempt", "state": "prepared"}

    def dispatch(self, attempt, *, authorization):
        self.calls.append(("dispatch", authorization))
        if authorization != "synthetic-authorization":
            raise WorkerUnsupported("synthetic worker requires its scripted authorization")
        return WorkerResult(self.descriptor.worker_id, attempt["attempt_id"],
                            self.script["state"], self.script.get("exit_status"))

    def usage(self):
        return ({"metric": "model_inference", "value": 0, "unit": "turns",
                 "scope": "worker", "semantics": "cumulative",
                 "source": "synthetic", "known": False},)


def catalog(workers=None):
    """Descriptors for every known worker class."""
    workers = workers or [DeterministicWorker(), CodexWorker(), FreebuffWorker()]
    return [worker.descriptor for worker in workers]


def eligible(workers, required_capabilities):
    """Return workers that advertise every required capability."""
    required = frozenset(required_capabilities)
    if not required <= CAPABILITIES:
        raise WorkerUnsupported("unknown required capability")
    return [worker for worker in workers if required <= worker.descriptor.capabilities]
