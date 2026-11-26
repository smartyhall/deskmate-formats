"""Allowance-aware worker selection with explicit unknown measurements.

Four different things are never conflated here:

* a provider *allowance* (for example consumed or remaining hours),
* the *current context* of one conversation,
* a *cumulative thread* token total,
* the inference *consumed by one task*.

They have different units, scopes and reset semantics. Nothing in this module
converts between them, sums across units, or treats a missing sample as zero.
A missing or stale allowance sample makes an inference worker ineligible; it
never makes it look free.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

UNITS = frozenset(("hours", "tokens", "percent", "count", "seconds"))
SCOPES = frozenset(("account", "campaign", "worker", "thread"))
SEMANTICS = frozenset(("remaining", "consumed", "cumulative", "current", "incremental"))
SOURCES = frozenset(("ui-observation", "documented-api", "local-collector",
                     "procedure-registry", "synthetic", "unavailable"))
ALLOWANCE = "allowance_remaining_hours"


class SchedulingError(ValueError):
    """The request or the measurement set is not coherent."""


def _utc(value):
    if type(value) is not str:
        raise SchedulingError("expected a UTC timestamp")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise SchedulingError("invalid UTC timestamp") from None


@dataclass(frozen=True, slots=True)
class Measurement:
    metric: str
    value: float | None
    unit: str
    scope: str
    semantics: str
    source: str
    observed_at_utc: str | None
    known: bool

    @classmethod
    def observed(cls, metric, value, unit, *, scope, semantics, source, observed_at_utc):
        if type(value) not in (int, float) or type(value) is bool:
            raise SchedulingError("measurement value must be numeric")
        for item, allowed in ((unit, UNITS), (scope, SCOPES), (semantics, SEMANTICS),
                              (source, SOURCES)):
            if item not in allowed:
                raise SchedulingError("unsupported measurement field")
        _utc(observed_at_utc)
        return cls(metric, float(value), unit, scope, semantics, source, observed_at_utc, True)

    @classmethod
    def unknown(cls, metric, unit, *, scope, semantics, reason="unavailable"):
        """An explicitly unavailable measurement. Never silently zero."""
        if unit not in UNITS or scope not in SCOPES or semantics not in SEMANTICS:
            raise SchedulingError("unsupported measurement field")
        return cls(metric, None, unit, scope, semantics,
                   "unavailable" if reason else "unavailable", None, False)

    def age_seconds(self, now):
        if not self.known:
            return None
        return (now - _utc(self.observed_at_utc)).total_seconds()

    def fresh(self, now, *, max_age_seconds):
        age = self.age_seconds(now)
        return age is not None and 0 <= age <= max_age_seconds

    def as_dict(self):
        return {"metric": self.metric, "value": self.value, "unit": self.unit,
                "scope": self.scope, "semantics": self.semantics, "source": self.source,
                "observed_at_utc": self.observed_at_utc, "known": self.known}


def grouped(measurements):
    """Group by unit so unlike quantities are never added together."""
    units = {}
    for measurement in measurements:
        units.setdefault(measurement.unit, []).append(measurement)
    return units


def total(measurements, unit):
    """Sum only same-unit, same-semantics, same-scope measurements.

    A measurement with a different unit is refused rather than filtered out:
    silently dropping it would turn a mixed ledger into a plausible total.
    """
    measurements = list(measurements)
    if any(item.unit != unit for item in measurements):
        raise SchedulingError("refusing to sum measurements with unlike units")
    selected = [item for item in measurements if item.known]
    if not selected:
        raise SchedulingError(f"no known {unit} measurement")
    keys = {(item.semantics, item.scope) for item in selected}
    if len(keys) != 1:
        raise SchedulingError("refusing to sum unlike semantics or scopes")
    return sum(item.value for item in selected)


@dataclass(frozen=True, slots=True)
class TaskRequirement:
    name: str
    requires_inference: bool
    capabilities: frozenset
    resources: tuple = ()

    def __post_init__(self):
        if type(self.name) is not str or not self.name:
            raise SchedulingError("task requirement needs a name")
        if not isinstance(self.capabilities, frozenset):
            raise SchedulingError("capabilities must be a frozenset")


@dataclass(frozen=True, slots=True)
class WorkerCapacity:
    """A worker description plus its measurements. No live process handle."""

    worker_id: str
    kind: str
    capabilities: frozenset
    health: str
    resource_kinds: tuple
    measurements: tuple = ()
    limitations: tuple = ()

    def measurement(self, metric):
        for item in self.measurements:
            if item.metric == metric:
                return item
        return None


@dataclass(frozen=True, slots=True)
class Decision:
    worker_id: str | None
    rationale: str
    rejected: tuple
    unknowns: tuple

    @property
    def chosen(self):
        return self.worker_id is not None

    def as_dict(self):
        return {"worker_id": self.worker_id, "chosen": self.chosen, "rationale": self.rationale,
                "rejected": [{"worker_id": worker, "reason": reason} for worker, reason in self.rejected],
                "unknowns": list(self.unknowns)}


def _reject(capacity, reason):
    return (capacity.worker_id, reason)


def select(task, capacities, *, now=None, max_measurement_age_seconds=900):
    """Choose one worker, preferring a deterministic procedure when sufficient."""
    if not isinstance(task, TaskRequirement):
        raise SchedulingError("expected a task requirement")
    if not 0 < max_measurement_age_seconds <= 86400:
        raise SchedulingError("invalid measurement freshness window")
    now = now or datetime.now(UTC)
    rejected, unknowns, viable = [], [], []

    for capacity in capacities:
        if capacity.health != "available":
            rejected.append(_reject(capacity, f"health is {capacity.health}"))
            continue
        if not task.capabilities <= capacity.capabilities:
            missing = ", ".join(sorted(task.capabilities - capacity.capabilities))
            rejected.append(_reject(capacity, f"missing capability: {missing}"))
            continue
        if not set(task.resources) <= set(capacity.resource_kinds):
            rejected.append(_reject(capacity, "does not declare the required resource kinds"))
            continue
        if task.requires_inference == (capacity.kind == "deterministic"):
            rejected.append(_reject(capacity, "worker class does not match the required inference mode"))
            continue
        if task.requires_inference:
            allowance = capacity.measurement(ALLOWANCE)
            if allowance is None or not allowance.known:
                rejected.append(_reject(capacity, "allowance is unknown, not zero and not unlimited"))
                continue
            if not allowance.fresh(now, max_age_seconds=max_measurement_age_seconds):
                rejected.append(_reject(capacity, "allowance measurement is stale"))
                continue
            if allowance.value <= 0:
                rejected.append(_reject(capacity, "allowance is exhausted"))
                continue
        else:
            allowance = capacity.measurement(ALLOWANCE)
            if allowance is None or not allowance.known:
                unknowns.append(f"{capacity.worker_id}: allowance is not required and remains unknown")
        viable.append(capacity)

    if not viable:
        return Decision(None, "no eligible worker", tuple(rejected), tuple(unknowns))

    # A deterministic procedure must not consume inference merely because an
    # inference worker also happens to be available.
    viable.sort(key=lambda item: (item.kind != "deterministic", item.worker_id))
    chosen = viable[0]
    for other in viable[1:]:
        rejected.append(_reject(other, "a lower-cost eligible worker was selected"))
    if task.requires_inference:
        allowance = chosen.measurement(ALLOWANCE)
        rationale = (f"inference worker with a fresh known allowance measurement "
                     f"({allowance.value:g} {allowance.unit} remaining)")
    else:
        rationale = "deterministic procedure; no model inference consumed"
    return Decision(chosen.worker_id, rationale, tuple(rejected), tuple(unknowns))


def capacity_from(worker, *, measurements=(), health_state=None):
    """Build a capacity view from a worker adapter without calling its methods."""
    if health_state is None:
        try:
            health_state = worker.health().state
        except Exception:  # noqa: BLE001 - a worker that cannot report health is unknown
            health_state = "unknown"
    return WorkerCapacity(worker.descriptor.worker_id, worker.descriptor.kind,
                          worker.descriptor.capabilities, health_state,
                          worker.descriptor.resources, tuple(measurements),
                          worker.descriptor.limitations)
