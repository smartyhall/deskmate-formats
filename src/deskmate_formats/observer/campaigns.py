"""Read-only heterogeneous campaign projection for the Observatory.

The projection is a pure function of a frozen snapshot. Rendering it cannot
dispatch work, steer an agent, cancel an attempt, touch an emulator or mutate
any file. Every value carries its basis so an operator can tell a durable
receipt from a registry claim, and measured activity from an unknown.
"""

from datetime import UTC, datetime
from html import escape
import json
from pathlib import Path

from .events import EventError, decode_json
from .presentation import ascii_display

SCHEMA_VERSION = 1
MAX_BYTES = 1024 * 1024
MAX_CAMPAIGNS = 64
MAX_ITEMS = 64
MAX_STALE_SECONDS = 3600


class CampaignSnapshotError(ValueError):
    """The frozen snapshot is missing, malformed or unsupported."""


def _utc(value):
    if type(value) is not str:
        raise CampaignSnapshotError("expected a UTC timestamp")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise CampaignSnapshotError("invalid UTC timestamp") from None


def _text(value, limit):
    return value if type(value) is str and len(value) <= limit and value.isprintable() else ""


def _items(value, label, limit=MAX_ITEMS):
    if value is None:
        return []
    if type(value) is not list or len(value) > limit:
        raise CampaignSnapshotError(f"invalid {label}")
    return value


def _measurements(values):
    measurements = []
    for item in _items(values, "measurements"):
        if type(item) is not dict:
            raise CampaignSnapshotError("invalid measurement record")
        metric = _text(item.get("metric"), 64)
        unit = _text(item.get("unit"), 16)
        if not metric or not unit:
            raise CampaignSnapshotError("measurement requires a metric and unit")
        known = item.get("known") is True and item.get("value") is not None
        observed = item.get("observed_at_utc")
        measurements.append({
            "metric": metric, "unit": unit,
            "value": item.get("value") if known else None,
            "scope": _text(item.get("scope"), 16) or "unknown",
            "semantics": _text(item.get("semantics"), 16) or "unknown",
            "source": _text(item.get("source"), 32) or "unavailable",
            "observed_at_utc": observed if type(observed) is str else None,
            "known": known,
        })
    return measurements


def validate(snapshot):
    """Validate the frozen snapshot without trusting any embedded prose."""
    if type(snapshot) is not dict:
        raise CampaignSnapshotError("snapshot must be an object")
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        raise CampaignSnapshotError("unsupported snapshot schema version")
    _utc(snapshot.get("generated_at_utc"))
    unreachable = snapshot.get("unreachable", [])
    if type(unreachable) is not list or len(unreachable) > MAX_ITEMS:
        raise CampaignSnapshotError("invalid unreachable list")
    campaigns = _items(snapshot.get("campaigns"), "campaigns", MAX_CAMPAIGNS)
    for record in campaigns:
        if type(record) is not dict:
            raise CampaignSnapshotError("invalid campaign record")
        if not _text(record.get("id"), 64) or not _text(record.get("owner"), 120):
            raise CampaignSnapshotError("campaign requires an id and owner")
        _measurements(record.get("measurements"))
    return snapshot


def load(path, *, limit=MAX_BYTES):
    target = Path(path)
    with target.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise CampaignSnapshotError("snapshot exceeds the byte limit")
    try:
        return validate(decode_json(raw, limit))
    except EventError:
        raise CampaignSnapshotError("snapshot is not valid strict JSON") from None


def _task_view(task):
    if type(task) is not dict:
        raise CampaignSnapshotError("invalid task record")
    state = _text(task.get("state"), 32)
    basis = "receipt" if _text(task.get("started_at_utc"), 32) else "unverified"
    return {
        "id": _text(task.get("id"), 64), "revision": task.get("revision"),
        "procedure": _text(task.get("procedure"), 64),
        "worker": _text(task.get("worker"), 64) or "unknown",
        "attempt": _text(task.get("attempt"), 64) or None,
        "state": state or "unknown", "state_basis": basis,
        "exit_status": task.get("exit_status") if type(task.get("exit_status")) in (int, str) else None,
        "started_at_utc": task.get("started_at_utc") if type(task.get("started_at_utc")) is str else None,
        "finished_at_utc": task.get("finished_at_utc") if type(task.get("finished_at_utc")) is str else None,
        "result_sha256": _text(task.get("result_sha256"), 64) or None,
    }


def _campaign_view(record, now, *, stale_seconds):
    tasks = [_task_view(task) for task in _items(record.get("tasks"), "tasks")]
    resources = [{"name": _text(item.get("name"), 64), "state": _text(item.get("state"), 32) or "unknown",
                  "owner": _text(item.get("owner"), 64) or None,
                  "expires_at": item.get("expires_at") if type(item.get("expires_at")) is str else None,
                  "stale": item.get("stale") is True}
                 for item in _items(record.get("resources"), "resources") if type(item) is dict]
    measurements = _measurements(record.get("measurements"))
    for measurement in measurements:
        stamp = measurement["observed_at_utc"]
        age = None
        if measurement["known"] and stamp is not None:
            try:
                age = round((now - _utc(stamp)).total_seconds(), 3)
            except CampaignSnapshotError:
                age = None
                measurement["known"] = False
        measurement["age_seconds"] = age
        measurement["fresh"] = age is not None and 0 <= age <= stale_seconds
    activity = [item for item in tasks if item["started_at_utc"]]
    last = max((item["started_at_utc"] for item in activity), default=None)
    results = [{"label": _text(item.get("label"), 64), "state": _text(item.get("state"), 32) or "unknown",
                "exit_status": item.get("exit_status") if type(item.get("exit_status")) in (int, str) else None}
               for item in _items(record.get("results"), "results") if type(item) is dict]
    return {
        "id": _text(record.get("id"), 64),
        "owner": _text(record.get("owner"), 120),
        "provider": _text(record.get("provider"), 32) or "unknown",
        "worker_kind": _text(record.get("worker_kind"), 32) or _text(record.get("provider"), 32) or "unknown",
        "status": _text(record.get("status"), 32) or "unknown",
        "branch": _text(record.get("branch"), 160) or None,
        "base_commit": _text(record.get("base_commit"), 40) or None,
        "milestone": _text(record.get("milestone"), 120) or None,
        "checkpoint": _text(record.get("checkpoint"), 120) or None,
        "tasks": tasks,
        "results": results,
        "resources": resources,
        "approvals": [{"id": _text(item.get("id"), 64), "summary": _text(item.get("summary"), 160)}
                      for item in _items(record.get("approvals"), "approvals") if type(item) is dict],
        "blockers": [{"summary": _text(item.get("summary"), 200),
                      "kind": _text(item.get("kind"), 32) or "blocker"}
                     for item in _items(record.get("blockers"), "blockers") if type(item) is dict],
        "measurements": measurements,
        "evidence": [{"label": _text(item.get("label"), 64),
                      "locator": _text(item.get("locator"), 200),
                      "sha256": _text(item.get("sha256"), 64) or None}
                     for item in _items(record.get("evidence"), "evidence") if type(item) is dict],
        "activity": {"basis": "measured" if last else "unknown",
                     "last_observed_at_utc": last},
        "synthetic": record.get("synthetic") is True,
        "sources": [{"label": _text(item.get("label"), 64),
                     "kind": _text(item.get("kind"), 32) or "unknown",
                     "observed_at_utc": item.get("observed_at_utc")
                     if type(item.get("observed_at_utc")) is str else None}
                    for item in _items(record.get("sources"), "sources")
                    if type(item) is dict],
    }


def projection(snapshot, *, now=None, stale_seconds=MAX_STALE_SECONDS):
    """Pure read-only view. Never infers progress from elapsed time."""
    if not 0 < stale_seconds <= 86400:
        raise CampaignSnapshotError("invalid freshness window")
    validate(snapshot)
    now = now or datetime.now(UTC)
    generated = _utc(snapshot["generated_at_utc"])
    age = round((now - generated).total_seconds(), 3)
    campaigns = [_campaign_view(record, now, stale_seconds=stale_seconds)
                 for record in sorted(snapshot["campaigns"], key=lambda item: item["id"])]
    states = {}
    for campaign in campaigns:
        for task in campaign["tasks"]:
            states[task["state"]] = states.get(task["state"], 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": snapshot["generated_at_utc"],
        "age_seconds": age,
        "stale": age < 0 or age > stale_seconds,
        "campaign_count": len(campaigns),
        "task_states": states,
        "campaigns": campaigns,
        "unreachable": [_text(item, 200) for item in snapshot.get("unreachable", [])],
        "note": "Read-only projection. Measured activity is reported separately from unknown state.",
    }


def _cell(value):
    return "-" if value in (None, "") else str(value)


def render_text(view):
    lines = [
        "DESKMATE RESEARCH LABORATORY - CAMPAIGN OPERATIONS",
        f"Snapshot         {view['generated_at_utc']} ({view['age_seconds']:g}s old"
        f"{', STALE' if view['stale'] else ''})",
        f"Campaigns        {view['campaign_count']}",
        f"Task states      " + (", ".join(f"{key}={value}" for key, value in
                                         sorted(view["task_states"].items())) or "none"),
        f"Unreachable      {len(view['unreachable'])}",
        "",
    ]
    for campaign in view["campaigns"]:
        marker = " (SYNTHETIC)" if campaign["synthetic"] else ""
        lines.append(f"[{campaign['id']}] {campaign['status']} / {campaign['worker_kind']} / "
                     f"owner {campaign['owner']}{marker}")
        if campaign["branch"]:
            lines.append(f"  Branch         {campaign['branch']}")
        lines.append(f"  Milestone      {_cell(campaign['milestone'])}")
        lines.append(f"  Checkpoint     {_cell(campaign['checkpoint'])}")
        lines.append(f"  Activity       {campaign['activity']['basis']}: "
                     f"{_cell(campaign['activity']['last_observed_at_utc'])}")
        for task in campaign["tasks"]:
            lines.append(f"  Task           {task['id']} r{task['revision']} {task['state']}"
                         f" [{task['state_basis']}] {task['procedure'] or task['worker']}")
        for result in campaign["results"]:
            lines.append(f"  Result         {result['label']}: {result['state']}"
                         f" (exit {_cell(result['exit_status'])})")
        for resource in campaign["resources"]:
            lines.append(f"  Resource       {resource['name']}: {resource['state']}"
                         f"{' STALE' if resource['stale'] else ''}")
        for approval in campaign["approvals"]:
            lines.append(f"  Approval       {approval['id']}: {approval['summary']}")
        for blocker in campaign["blockers"]:
            lines.append(f"  Blocker        {blocker['summary']}")
        for measurement in campaign["measurements"]:
            if measurement["known"]:
                lines.append(f"  Usage          {measurement['metric']} = "
                             f"{measurement['value']:g} {measurement['unit']} "
                             f"({measurement['source']}, "
                             f"{'fresh' if measurement['fresh'] else 'stale'})")
            else:
                lines.append(f"  Usage          {measurement['metric']} = unknown "
                             f"{measurement['unit']}")
        lines.append("")
    if view["unreachable"]:
        lines.append("UNREACHABLE SOURCES")
        lines.extend(f"  {item}" for item in view["unreachable"])
        lines.append("")
    return ascii_display("\n".join(lines))


def render_html(view):
    rows = []
    for campaign in view["campaigns"]:
        tasks = ", ".join(f"{escape(task['id'])} r{escape(str(task['revision']))} "
                          f"{escape(task['state'])}" for task in campaign["tasks"]) or "none"
        usage = ", ".join(
            (f"{escape(item['metric'])} {item['value']:g} {escape(item['unit'])}"
             if item["known"] else f"{escape(item['metric'])} unknown")
            for item in campaign["measurements"]) or "not reported"
        resources = ", ".join(f"{escape(item['name'])} ({escape(item['state'])})"
                              for item in campaign["resources"]) or "none"
        if campaign["synthetic"]:
            campaign_id = f"{campaign['id']} (synthetic)"
        else:
            campaign_id = campaign["id"]
        rows.append(
            "<tr>"
            f"<th scope=\"row\">{escape(campaign_id)}</th>"
            f"<td>{escape(campaign['status'])}</td>"
            f"<td>{escape(campaign['worker_kind'])}</td>"
            f"<td>{escape(campaign['owner'])}</td>"
            f"<td>{tasks}</td>"
            f"<td>{resources}</td>"
            f"<td>{escape(campaign['activity']['basis'])}</td>"
            f"<td>{usage}</td>"
            "</tr>")
    stale = " STALE" if view["stale"] else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Campaign operations | DeskMate Observatory</title>
  <link rel="stylesheet" href="/dashboard.css">
</head>
<body>
  <header><div class="eyebrow">DeskMate Observatory <span> / </span> Read-only campaign operations{stale}</div></header>
  <main>
    <h1>Campaign operations</h1>
    <p class="muted">Snapshot {escape(view['generated_at_utc'])} ({view['age_seconds']:g}s old).
       Measured activity is reported separately from unknown state. This page cannot dispatch work.</p>
    <table>
      <thead><tr><th scope="col">Campaign</th><th scope="col">Status</th><th scope="col">Worker</th>
      <th scope="col">Owner</th><th scope="col">Tasks</th><th scope="col">Resources</th>
      <th scope="col">Activity basis</th><th scope="col">Usage</th></tr></thead>
      <tbody>{''.join(rows) or '<tr><td colspan="8">No campaigns reported</td></tr>'}</tbody>
    </table>
    <p><a href="/campaigns.txt">Plain text</a> | <a href="/api/campaigns">JSON</a></p>
  </main>
</body>
</html>
"""


def render(view, fmt):
    if fmt == "json":
        return "application/json", json.dumps(view, sort_keys=True, indent=2)
    if fmt == "text":
        return "text/plain; charset=us-ascii", render_text(view)
    if fmt == "html":
        return "text/html; charset=utf-8", render_html(view)
    raise CampaignSnapshotError("unsupported output format")
