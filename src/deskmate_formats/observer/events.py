"""Version 1 Observatory event contract and deterministic ingestion order."""

from datetime import datetime
from hashlib import sha256
import json
import math
import re

SCHEMA_VERSION = 1
MAX_INPUT_BYTES = 8192
MAX_RECORD_BYTES = MAX_INPUT_BYTES + 512  # Includes collector fields and LF.
MAX_SEQUENCE = (1 << 53) - 1  # Exact in browser JSON numbers.
IDENTITY = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
EVENT_TYPES = frozenset("""
    session.started session.ended turn.started turn.completed turn.failed turn.interrupted
    plan.updated milestone.completed tool.started tool.completed tool.failed command.started
    command.completed test.started test.completed git.commit git.branch git.pr.opened git.pr.updated
    experiment.checkpoint experiment.sample experiment.result approval.requested approval.resolved
    process.heartbeat process.exited source.disconnected source.reconnected source.error agent.note
""".split())
SEVERITIES = frozenset(("debug", "info", "warning", "error"))
CORRELATIONS = frozenset(("session", "turn", "command", "tool", "experiment", "task", "approval", "test"))
_REQUIRED = frozenset(("schema_version", "source", "origin_id", "run_id", "agent_id",
                       "source_sequence", "type", "summary"))
_OPTIONAL = frozenset(("machine_ids", "severity", "source_time_utc", "correlation", "visibility",
                       "details", "process"))
_INGESTED = frozenset(("cursor", "event_id", "ingested_at_utc", "ingested_monotonic_ns"))
_UTC = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z")


class EventError(ValueError):
    """Event rejected. Diagnostics omit untrusted values."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EventError("duplicate JSON member")
        result[key] = value
    return result


def _invalid_constant(_):
    raise EventError("non-JSON numeric constant")


def decode_json(data, limit=MAX_INPUT_BYTES):
    if len(data) > limit:
        raise EventError("JSON exceeds byte limit")
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object,
                          parse_constant=_invalid_constant)
    except EventError:
        raise
    except (ValueError, RecursionError):
        raise EventError("invalid UTF-8 JSON") from None


def encode_json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"),
                      sort_keys=True).encode("utf-8")


def _choice(value, choices, label):
    if type(value) is not str or value not in choices:
        raise EventError(f"invalid {label}")
    return value


def _integer(value, minimum, maximum, label):
    if type(value) is not int or not minimum <= value <= maximum:
        raise EventError(f"invalid {label}")
    return value


def _identity(value):
    if type(value) is not str or not IDENTITY.fullmatch(value):
        raise EventError("invalid identity")
    return value


def _text(value, limit, label):
    if (type(value) is not str or len(value) > limit
            or (value and not value.isprintable())):
        raise EventError(f"invalid {label}")
    return value


def _timestamp(value):
    if type(value) is not str or not _UTC.fullmatch(value):
        raise EventError("expected an ISO UTC timestamp ending in Z")
    try:
        datetime.fromisoformat(value)
    except ValueError:
        raise EventError("invalid UTC date or time") from None
    return value


def _detail(value, budget, depth=0):
    budget[0] -= 1
    if budget[0] < 0:
        raise EventError("details exceed node limit")
    if depth > 5:
        raise EventError("details exceed nesting limit")
    if type(value) is dict and len(value) <= 32:
        return {_text(key, 64, "detail key"): _detail(item, budget, depth + 1)
                for key, item in value.items()}
    if type(value) is list and len(value) <= 32:
        return [_detail(item, budget, depth + 1) for item in value]
    if type(value) is str:
        return _text(value, 1024, "detail text")
    if value is None or type(value) is bool:
        return value
    if type(value) is int and abs(value) <= MAX_SEQUENCE or type(value) is float and math.isfinite(value):
        return value
    raise EventError("invalid or oversized details")


def normalize_event(value):
    """Validate producer fields and return a canonical, detached JSON object."""
    if type(value) is not dict or not _REQUIRED <= value.keys() <= _REQUIRED | _OPTIONAL:
        raise EventError("missing or unexpected event fields")
    _integer(value["schema_version"], SCHEMA_VERSION, SCHEMA_VERSION, "schema version")
    event = {key: _identity(value[key]) for key in ("source", "origin_id", "run_id", "agent_id")}
    event["schema_version"] = SCHEMA_VERSION
    event["source_sequence"] = _integer(value["source_sequence"], 1, MAX_SEQUENCE, "source sequence")
    event["type"] = _choice(value["type"], EVENT_TYPES, "event type")
    event["severity"] = _choice(value.get("severity", "info"), SEVERITIES, "severity")
    event["visibility"] = _choice(value.get("visibility", "private"), ("private", "observer"), "visibility")
    event["summary"] = _text(value["summary"], 240, "summary")
    if not event["summary"].strip():
        raise EventError("empty summary")
    machines = value.get("machine_ids", [])
    if type(machines) is not list or len(machines) > 8:
        raise EventError("invalid machine identities")
    event["machine_ids"] = [_identity(machine) for machine in machines]
    if len(set(machines)) != len(machines):
        raise EventError("duplicate machine identity")
    timestamp = value.get("source_time_utc")
    event["source_time_utc"] = None if timestamp is None else _timestamp(timestamp)
    correlation = value.get("correlation", {})
    if type(correlation) is not dict or not correlation.keys() <= CORRELATIONS:
        raise EventError("invalid correlation fields")
    event["correlation"] = {key: _identity(item) for key, item in correlation.items()}
    if event["type"].startswith("approval.") and "approval" not in correlation:
        raise EventError("approval events require an approval correlation ID")
    if "details" in value:
        if type(value["details"]) is not dict:
            raise EventError("details must be an object")
        event["details"] = _detail(value["details"], [256])
    if "process" in value:
        process = value["process"]
        if (event["type"] != "process.heartbeat" or type(process) is not dict
                or process.keys() != {"pid", "identity"}):
            raise EventError("invalid process claim")
        event["process"] = {
            "pid": _integer(process["pid"], 1, (1 << 31) - 1, "PID"),
            "identity": _identity(process["identity"]),
        }
    if len(encode_json(event)) > MAX_INPUT_BYTES:
        raise EventError("normalized event exceeds byte limit")
    return event


def envelope(event, cursor, utc, monotonic_ns):
    return {**event, "cursor": cursor, "event_id": f"local-{cursor:016d}",
            "ingested_at_utc": utc, "ingested_monotonic_ns": str(monotonic_ns)}


def decode_record(line):
    """Decode an LF-committed record including its collector-owned fields."""
    if not line.endswith(b"\n"):
        raise EventError("incomplete journal record")
    raw = decode_json(line, MAX_RECORD_BYTES)
    if type(raw) is not dict or not _INGESTED <= raw.keys():
        raise EventError("missing ingestion fields")
    cursor = _integer(raw["cursor"], 1, MAX_SEQUENCE, "cursor")
    clock = raw["ingested_monotonic_ns"]
    if type(clock) is not str or not re.fullmatch(r"0|[1-9][0-9]{0,19}", clock):
        raise EventError("invalid ingestion monotonic time")
    producer = normalize_event({key: value for key, value in raw.items() if key not in _INGESTED})
    record = envelope(producer, cursor, _timestamp(raw["ingested_at_utc"]), int(clock))
    if raw["event_id"] != record["event_id"]:
        raise EventError("invalid event ID")
    return record


class IngestionOrder:
    """Index source sequences and cursor order within one bounded journal."""

    def __init__(self):
        self.cursor = 0
        self._origins = {}
        self._seen = {}

    def accept(self, record):
        cursor = record["cursor"]
        if cursor <= self.cursor:
            raise EventError("non-increasing ingestion cursor")
        origin, seq = record["origin_id"], record["source_sequence"]
        identity = (record["source"], record["agent_id"], record["run_id"])
        previous_identity, previous_seq = self._origins.get(origin, (identity, 0))
        if previous_identity != identity:
            raise EventError("origin identity changed")
        fingerprint = sha256(encode_json({key: value for key, value in record.items()
                                         if key not in _INGESTED})).digest()
        if seq <= previous_seq:
            previous = self._seen.get((origin, seq))
            if previous is None:
                raise EventError("out-of-order source sequence")
            if previous == fingerprint:
                raise EventError("duplicate source sequence")
            raise EventError("conflicting source sequence")
        self._origins[origin] = (identity, seq)
        self._seen[origin, seq] = fingerprint
        self.cursor = cursor
