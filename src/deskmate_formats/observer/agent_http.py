"""Bounded read-only queries over a sanitized agent snapshot."""

from bisect import bisect_right
from dataclasses import asdict
from itertools import islice
from operator import attrgetter
import re

from .events import EVENT_TYPES, IDENTITY, MAX_SEQUENCE, SCHEMA_VERSION, SEVERITIES

_AGENTS = re.compile(r"/api/v1/agents(?:/(" + IDENTITY.pattern + r")(?:/(events))?)?")
_CATEGORIES = frozenset(kind.partition(".")[0] for kind in EVENT_TYPES)
_INTEGER = re.compile(r"0|[1-9][0-9]{0,15}")
_COMMON = frozenset(("limit", "agent", "run", "origin", "machine"))
_EVENTS = _COMMON | {"after", "tail", "severity", "type", "category"}
_AGENT_FILTERS = _COMMON | {"before"}
MAX_PAGE = 100


def match_route(path):
    if path == "/api/v1/events":
        return None, True
    match = _AGENTS.fullmatch(path)
    return (match[1], match[2] is not None) if match else None


def _number(value):
    if not _INTEGER.fullmatch(value) or int(value) > MAX_SEQUENCE:
        raise ValueError("invalid numeric query value")
    return int(value)


def _parameters(query, is_events):
    allowed = _EVENTS if is_events else _AGENT_FILTERS
    params = {}
    for field in query.split("&") if query else ():
        key, equal, value = field.partition("=")
        if not equal or not value or key not in allowed or key in params:
            raise ValueError("invalid query field")
        if key in ("limit", "after", "before", "tail"):
            value = _number(value)
            if key == "limit" and value == 0 or key == "tail" and value != 1:
                raise ValueError("invalid page parameter")
        elif key == "severity" and value not in SEVERITIES:
            raise ValueError("invalid severity filter")
        elif key == "type" and value not in EVENT_TYPES:
            raise ValueError("invalid event type filter")
        elif key == "category" and value not in _CATEGORIES:
            raise ValueError("invalid category filter")
        elif not IDENTITY.fullmatch(value):
            raise ValueError("invalid query identity")
        params[key] = value
    if "after" in params and "tail" in params:
        raise ValueError("after and tail are mutually exclusive")
    return params


def _matches(row, params):
    return all(getattr(row, attribute) == params[key] for key, attribute in (
        ("agent", "agent_id"), ("run", "run_id"), ("origin", "origin_id"),
    ) if key in params) and ("machine" not in params or params["machine"] in row.machine_ids)


def query_snapshot(snapshot, route, query, page_limit):
    agent, is_events = route
    params = _parameters(query, is_events)
    if agent is not None:
        if params.get("agent", agent) != agent:
            raise ValueError("agent query conflicts with route")
        if not any(row.agent_id == agent for row in snapshot.agents):
            raise LookupError("unknown agent")
        params["agent"] = agent
    limit = min(params.get("limit", 50), page_limit)
    result = {"schema_version": SCHEMA_VERSION, "collector": snapshot.collector, "limit": limit}
    if is_events:
        after = params.get("after", 0)
        events = snapshot.events
        index = bisect_right(events, after, key=attrgetter("cursor"))
        tail = params.get("tail", False)
        source = reversed(events) if tail else islice(events, index, None)
        matches = (row for row in source if _matches(row, params)
                   and ("severity" not in params or row.severity == params["severity"])
                   and ("type" not in params or row.type == params["type"])
                   and ("category" not in params or row.type.partition(".")[0] == params["category"]))
        page = list(islice(matches, limit + 1))
        displayed = page[:limit]
        if tail:
            displayed.reverse()
        return {**result, "events": [asdict(row) for row in displayed],
                "next_cursor": displayed[-1].cursor if displayed else after,
                "has_more": len(page) > limit}
    before = params.get("before", MAX_SEQUENCE + 1)
    matches = (row for row in snapshot.agents if row.latest_cursor < before and _matches(row, params))
    page = list(islice(matches, limit + 1))
    displayed = page[:limit]
    return {**result, "agents": [asdict(row) for row in displayed],
            "next_before": displayed[-1].latest_cursor if displayed else None,
            "has_more": len(page) > limit}
