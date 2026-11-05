"""In-memory handoff from a trusted producer to read-only observers."""

from collections import deque
from dataclasses import dataclass, field, replace
from enum import StrEnum
import re
from threading import Lock
from time import monotonic, time_ns
from unicodedata import category
from uuid import uuid4

from .frames import Frame, MAX_TIMESTAMP, counter

INSTANCE_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")
MAX_COLUMNS, MAX_ROWS = 132, 60
_CP437_GLYPHS = " ☺☻♥♦♣♠•◘○◙♂♀♪♫☼►◄↕‼¶§▬↨↑↓→←∟↔▲▼"
_CP437_TABLE = _CP437_GLYPHS + bytes(range(32, 256)).decode("cp437").replace("\x7f", "⌂")


def decode_cp437(rows):
    """Decode approved display-character rows, without attribute or RAM bytes."""
    decoded = []
    for row in rows:
        if len(decoded) == MAX_ROWS or type(row) is not bytes or len(row) > MAX_COLUMNS:
            raise ValueError("invalid CP437 screen rows")
        decoded.append("".join(_CP437_TABLE[byte] for byte in row))
    return "\n".join(decoded)


def _text(value, limit, multiline=False):
    if (type(value) is not str or len(value) > limit
            or any(category(char)[0] == "C" or category(char) in {"Zl", "Zp"}
                   for char in value if char != "\n" or not multiline)):
        raise ValueError("invalid observation text")


def host_time_ms():
    """Wall-clock UTC milliseconds, separate from guest and freshness clocks."""
    return time_ns() // 1_000_000


class Action(StrEnum):
    BOOT = "boot"
    STEP = "step"
    KEY_SEQUENCE = "key sequence"
    OBSERVE = "observe"
    RESET = "reset"
    CONNECTION = "connection"


class Connection(StrEnum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class ErrorCode(StrEnum):
    TIMEOUT = "timeout"
    TRANSPORT = "transport"
    OBSERVATION_FAILED = "observation failed"


@dataclass(frozen=True, slots=True)
class Machine:
    instance_id: str
    label: str

    def __post_init__(self):
        if type(self.instance_id) is not str or not INSTANCE_ID.fullmatch(self.instance_id):
            raise ValueError("invalid instance ID")
        _text(self.label, 80)
        if not self.label.strip():
            raise ValueError("machine label is empty")


@dataclass(frozen=True, slots=True)
class Observation:
    """An explicitly approved snapshot. Omit screen/frame to withhold them."""

    instance_id: str
    sequence: int
    generation: int
    observed_at_ms: int
    emulated_ms: int | None
    held: bool | None
    paused: bool | None
    action: Action = Action.OBSERVE
    milestone: str = ""
    connection: Connection = Connection.CONNECTED
    error: ErrorCode | None = None
    dropped_updates: int = 0
    screen: str | None = field(default=None, repr=False)
    frame: Frame | None = field(default=None, repr=False)

    def __post_init__(self):
        if type(self.instance_id) is not str or not INSTANCE_ID.fullmatch(self.instance_id):
            raise ValueError("invalid instance ID")
        for value in (self.sequence, self.generation, self.dropped_updates):
            counter(value)
        counter(self.observed_at_ms, MAX_TIMESTAMP)
        if self.emulated_ms is not None:
            counter(self.emulated_ms)
        if (type(self.action) is not Action or type(self.connection) is not Connection
                or self.error is not None and type(self.error) is not ErrorCode
                or (self.connection is Connection.ERROR) != (self.error is not None)):
            raise ValueError("invalid action, connection or error code")
        if self.connection is Connection.CONNECTED:
            if type(self.held) is not bool or type(self.paused) is not bool or self.emulated_ms is None:
                raise ValueError("connected observation requires guest clock and execution state")
        elif self.held is not None or self.paused is not None:
            raise ValueError("unavailable execution state must be unknown")
        _text(self.milestone, 120)
        if self.screen is not None:
            _text(self.screen, (MAX_COLUMNS + 1) * MAX_ROWS - 1, multiline=True)
            lines = self.screen.split("\n")
            if len(lines) > MAX_ROWS or any(len(line) > MAX_COLUMNS for line in lines):
                raise ValueError("screen exceeds row or column limit")
        if self.frame is not None:
            if (type(self.frame) is not Frame or self.connection is Connection.CONNECTED
                    and self.frame.captured_at_ms > self.observed_at_ms):
                raise ValueError("invalid frame or capture time")
            rendered_ms = self.frame.rendered_emulated_ms
            if rendered_ms is not None and (self.emulated_ms is None or rendered_ms > self.emulated_ms):
                raise ValueError("rendered frame is ahead of the observed guest clock")


@dataclass(frozen=True, slots=True)
class Event:
    """Timeline metadata only. Older screens and images are never retained here."""

    sequence: int
    generation: int
    emulated_ms: int | None
    observed_at_ms: int
    action: Action
    milestone: str
    connection: Connection
    error: ErrorCode | None

    @classmethod
    def from_observation(cls, observation):
        return cls(observation.sequence, observation.generation, observation.emulated_ms,
                   observation.observed_at_ms, observation.action, observation.milestone,
                   observation.connection, observation.error)


@dataclass(frozen=True, slots=True)
class View:
    publication_session: str
    observation: Observation | None
    history: tuple[Event, ...]
    stale: bool


class ObservationStream:
    """Publish one machine's snapshots and read a consistent latest view."""

    def __init__(self, machine: Machine, *, history_limit=24, stale_after=10.0):
        if type(machine) is not Machine:
            raise ValueError("expected a configured machine")
        if type(history_limit) is not int or not 1 <= history_limit <= 64:
            raise ValueError("history limit must be 1..64")
        if type(stale_after) not in (int, float) or not 0 < stale_after <= 86400:
            raise ValueError("freshness interval must be positive and at most one day")
        self._machine = machine
        self._session = uuid4().hex
        self._history = deque(maxlen=history_limit)
        self._stale_after = stale_after
        self._lock = Lock()
        self._latest = None
        self._last_frame_generation = -1
        self._last_emulated_ms = None
        self._fresh_until = 0.0

    @property
    def machine(self):
        return self._machine

    def publish(self, observation: Observation, *, sampled_at=None):
        """Replace the latest snapshot, optionally aging it from a monotonic sample time."""
        if type(observation) is not Observation or observation.instance_id != self.machine.instance_id:
            raise ValueError("observation belongs to another stream")
        with self._lock:
            self._publish(observation, sampled_at=sampled_at)

    def mark_unavailable(self, *, sequence, observed_at_ms, error=None):
        """Record a loss of contact while retaining the latest approved display."""
        with self._lock:
            if self._latest is None:
                raise ValueError("publish an initial observation first")
            observation = replace(
                self._latest, sequence=sequence, observed_at_ms=observed_at_ms,
                held=None, paused=None, action=Action.CONNECTION, error=error,
                connection=Connection.ERROR if error is not None else Connection.DISCONNECTED,
            )
            self._publish(observation)

    def _publish(self, observation, *, sampled_at=None):
        previous = self._latest
        last_frame_generation = self._last_frame_generation
        last_emulated_ms = self._last_emulated_ms
        if previous is not None:
            if (observation.sequence <= previous.sequence
                    or observation.generation < previous.generation
                    or observation.dropped_updates < previous.dropped_updates):
                raise ValueError("out-of-order observation")
            if observation.generation > previous.generation:
                if observation.frame is not None and observation.frame is previous.frame:
                    raise ValueError("a new generation requires a newly approved frame")
                last_frame_generation = -1
                last_emulated_ms = None
        if observation.emulated_ms is not None:
            if last_emulated_ms is not None and observation.emulated_ms < last_emulated_ms:
                raise ValueError("emulated clock regressed within a generation")
            last_emulated_ms = observation.emulated_ms
        frame = observation.frame
        if frame is not None:
            previous_frame = previous.frame if previous is not None else None
            if frame.generation <= last_frame_generation and frame is not previous_frame:
                raise ValueError("frame generation was already used or superseded")
            last_frame_generation = frame.generation

        # Readers hold this lock only long enough to copy the small timeline.
        # No socket I/O, image encoding, or HTML rendering happens here.
        self._history.append(Event.from_observation(observation))
        self._latest = observation
        self._last_frame_generation = last_frame_generation
        self._last_emulated_ms = last_emulated_ms
        self._fresh_until = (monotonic() if sampled_at is None else sampled_at) + self._stale_after

    def view(self):
        with self._lock:
            latest = self._latest
            stale = (latest is None or latest.connection is not Connection.CONNECTED
                     or monotonic() >= self._fresh_until)
            return View(self._session, latest, tuple(self._history), stale)


class ObservationRegistry:
    """Fixed set of named streams. The first machine is the default."""

    def __init__(self, machines, *, history_limit=24, stale_after=10.0):
        self._streams = {}
        for machine in machines:
            stream = ObservationStream(machine, history_limit=history_limit, stale_after=stale_after)
            if len(self._streams) == 8 or machine.instance_id in self._streams:
                raise ValueError("configure at most eight machines with unique IDs")
            self._streams[machine.instance_id] = stream
        if not self._streams:
            raise ValueError("configure at least one machine")

    @property
    def machines(self):
        return tuple(stream.machine for stream in self._streams.values())

    def stream(self, instance_id):
        return self._streams[instance_id]
