"""Deterministic, browser-safe agent projections from committed event records."""

from dataclasses import dataclass, field

from .process_health import verify_process

_TRANSPORT = frozenset(("process.heartbeat", "source.disconnected", "source.reconnected", "source.error"))
_TURN_END = {"turn.completed": "completed", "turn.failed": "failed", "turn.interrupted": "interrupted"}
_TERMINAL = frozenset(_TURN_END.values())
_MAX_PROCESS_PROBES = 64
_NS_PER_SECOND = 1_000_000_000


@dataclass(frozen=True, slots=True)
class PublicEvent:
    cursor: int
    event_id: str
    ingested_at_utc: str
    source: str
    origin_id: str
    agent_id: str
    run_id: str
    machine_ids: tuple[str, ...]
    type: str
    severity: str
    summary: str


@dataclass(frozen=True, slots=True)
class AgentView:
    origin_id: str
    agent_id: str
    run_id: str
    source: str
    machine_ids: tuple[str, ...]
    latest_cursor: int
    state: str
    reported_lifecycle: str
    stale: bool
    historical: bool
    last_activity: PublicEvent | None
    activity_age_ms: int | None
    last_signal_utc: str
    signal_age_ms: int | None
    transport: str
    process: str
    verified_pid: int | None
    pending_approval_count: int
    pending_approval_ids: tuple[str, ...]


@dataclass
class _Agent:
    latest: PublicEvent
    signal_ns: int | None
    activity: PublicEvent | None = None
    activity_ns: int | None = None
    lifecycle: str = "unknown"
    turn: str | None = None
    session_ended: bool = False
    disconnected: bool = False
    claim: tuple[int, str] | None = None
    approvals: dict[str, bool] = field(default_factory=dict)

    def apply(self, event, record, observed_ns):
        self.latest, self.signal_ns = event, observed_ns
        kind = event.type
        if kind not in _TRANSPORT:
            self.activity, self.activity_ns = event, observed_ns
            self.disconnected = False
        elif kind == "source.reconnected":
            self.disconnected = False
        elif kind == "source.disconnected":
            self.disconnected = True
        elif kind == "process.heartbeat":
            claim = record.get("process")
            self.claim = (claim["pid"], claim["identity"]) if claim else None

        if self.session_ended:
            return
        correlation = record["correlation"]
        turn = correlation.get("turn")
        if kind == "session.started" and self.lifecycle == "unknown":
            self.lifecycle = "running"
        elif kind == "turn.started":
            self.lifecycle, self.turn = "running", turn
        elif kind in _TURN_END and self.lifecycle not in _TERMINAL:
            if turn is None or self.turn is None or turn == self.turn:
                self.lifecycle, self.turn = _TURN_END[kind], turn or self.turn
        elif kind == "session.ended":
            if self.lifecycle not in ("failed", "interrupted"):
                self.lifecycle = "completed"
            self.session_ended = True
            self.approvals.clear()
        elif kind == "approval.requested":
            self.approvals.setdefault(correlation["approval"], True)
        elif kind == "approval.resolved":
            self.approvals[correlation["approval"]] = False

    def view(self, now_ns, quiet_ns, stale_ns, process):
        def elapsed(stamp):
            return None if stamp is None or stamp > now_ns else now_ns - stamp

        activity_age = elapsed(self.activity_ns)
        signal_age = elapsed(self.signal_ns)
        historical = signal_age is None
        expired = historical or signal_age >= stale_ns
        transport = "disconnected" if self.disconnected else "historical" if historical else "stale" if expired else "recent"
        stale = expired or self.disconnected
        pending = tuple(key for key, waiting in self.approvals.items() if waiting)
        if self.lifecycle in _TERMINAL:
            state = self.lifecycle
        elif (historical or self.disconnected or process in ("not-found", "stopped", "identity-mismatch")
              or expired and process != "alive"):
            state = "disconnected"
        elif pending:
            state = "approval-needed"
        elif not expired and activity_age is not None and activity_age < quiet_ns:
            state = "active-reporting"
        elif process == "alive":
            state = "alive-no-new-events"
        else:
            state = "unknown"
        latest = self.latest
        return AgentView(
            latest.origin_id, latest.agent_id, latest.run_id, latest.source, latest.machine_ids, latest.cursor,
            state, self.lifecycle, stale, historical, self.activity,
            None if activity_age is None else activity_age // 1_000_000,
            latest.ingested_at_utc, None if signal_age is None else signal_age // 1_000_000, transport,
            process, self.claim[0] if process in ("alive", "stopped") else None,
            len(pending), pending[-8:],
        )


class AgentProjection:
    """Replay in ingestion order, exposing only explicitly published fields."""

    def __init__(self, records, *, started_ns, scanned_ns, quiet_seconds=120, stale_seconds=600):
        if not 0 < quiet_seconds <= stale_seconds <= 86400:
            raise ValueError("expected 0 < quiet seconds <= stale seconds <= 86400")
        self._quiet = int(quiet_seconds * _NS_PER_SECOND)
        self._stale = int(stale_seconds * _NS_PER_SECOND)
        agents = {}
        events = []
        for record in records:
            if record["visibility"] != "observer":
                continue
            event = PublicEvent(
                record["cursor"], record["event_id"], record["ingested_at_utc"], record["source"],
                record["origin_id"], record["agent_id"], record["run_id"], tuple(record["machine_ids"]),
                record["type"], record["severity"], record["summary"],
            )
            events.append(event)
            stamp = int(record["ingested_monotonic_ns"])
            observed_ns = stamp if started_ns <= stamp <= scanned_ns else None
            agent = agents.get(event.origin_id)
            if agent is None:
                agent = agents[event.origin_id] = _Agent(event, observed_ns)
            agent.apply(event, record, observed_ns)
        self.events = tuple(events)
        self._agents = sorted(agents.values(), key=lambda agent: agent.latest.cursor, reverse=True)

    def views(self, now_ns, *, probe=verify_process):
        observed = {}
        views = []
        for agent in self._agents:
            process = "unknown"
            if agent.claim is not None:
                if agent.claim not in observed and len(observed) < _MAX_PROCESS_PROBES:
                    observed[agent.claim] = probe(*agent.claim)
                process = observed.get(agent.claim, "unknown")
            views.append(agent.view(now_ns, self._quiet, self._stale, process))
        return tuple(views)
