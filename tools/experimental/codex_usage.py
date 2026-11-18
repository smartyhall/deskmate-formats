"""Export allowlisted DeskMate usage observations without model inference."""

import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile


DURATIONS = (300, 10080)
TOKENS = {
    "input": ("input_tokens", "inputTokens"),
    "cached_input": ("cached_input_tokens", "cachedInputTokens"),
    "output": ("output_tokens", "outputTokens"),
    "reasoning_output": ("reasoning_output_tokens", "reasoningOutputTokens"),
    "total": ("total_tokens", "totalTokens"),
}
MODELS = {"gpt-6-astra", "gpt-6-luna", "gpt-6.1-sol", "gpt-6.2-sol"}
EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"}


def mapping(value):
    return value if isinstance(value, dict) else {}


def value_for(data, *keys):
    return next((data[key] for key in keys if key in data), None)


def integer(value):
    return value if type(value) is int and 0 <= value < 2**63 else None


def percentage(value):
    return value if type(value) in (int, float) and 0 <= value <= 100 else None


def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is not None:
            return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        pass
    return None


def counters(data):
    return {name: integer(value_for(mapping(data), *keys)) for name, keys in TOKENS.items()}


def windows(data, at):
    """Normalize the default Codex meter; ignore other buckets and credit fields."""
    data = mapping(data)
    readings = {}
    ambiguous = set()
    if value_for(data, "limit_id", "limitId") in (None, "codex"):
        for slot in ("primary", "secondary"):
            entry = mapping(data.get(slot))
            duration = integer(value_for(entry, "window_minutes", "windowDurationMins"))
            if duration not in DURATIONS:
                continue
            used = percentage(value_for(entry, "used_percent", "usedPercent"))
            remaining = percentage(value_for(entry, "remaining_percent", "remainingPercent"))
            if used is None and remaining is not None:
                used = round(100 - remaining, 10)
            reset = integer(value_for(entry, "resets_at", "resetsAt"))
            reading = {"used_percent": used, "reset_epoch": reset}
            if duration in readings and readings[duration] != reading:
                ambiguous.add(duration)
            readings[duration] = reading
    for duration in DURATIONS:
        if duration in ambiguous:
            readings.pop(duration, None)
        entry = readings.setdefault(duration, {"used_percent": None, "reset_epoch": None})
        reset = entry["reset_epoch"]
        entry["status"] = (
            "missing" if entry["used_percent"] is None else
            "expired" if reset is not None and reset <= at.timestamp() else "observed"
        )
    return readings


def encode(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)


def pseudonym(key, identity):
    return hmac.digest(key, identity.encode(), "sha256").hex()[:24]


def normal_path(path):
    resolved = str(path.resolve())
    if os.name == "nt":
        if resolved.startswith("\\\\?\\UNC\\"):
            resolved = "\\\\" + resolved[8:]
        else:
            resolved = resolved.removeprefix("\\\\?\\")
    return Path(resolved)


def project_cwd(cwd, roots):
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        return False
    directory = normal_path(Path(cwd))
    return any(directory.is_relative_to(root) for root in roots)


def rows(path, coverage):
    with path.open("rb") as source:
        for line in source:
            if not line.endswith(b"\n"):
                coverage["incomplete_lines"] += 1
                continue
            try:
                record = mapping(json.loads(line))
            except (ValueError, UnicodeError):
                coverage["malformed_lines"] += 1
                continue
            yield record, mapping(record.get("payload"))


def collect(homes, roots, key, *, cutoff=None):
    observed = {}
    index = {}
    coverage = Counter()
    roots = [normal_path(root) for root in roots]
    for store in ("sessions", "archived_sessions"):
        paths = {path.resolve() for home in homes for path in (home / store).rglob("rollout-*.jsonl")}
        for path in sorted(paths):
            diagnostics = Counter()
            with closing(rows(path, diagnostics)) as records:
                header, meta = next(records, ({}, {}))
                cwd = meta.get("cwd")
                identity = next((meta[k] for k in ("session_id", "id")
                                 if isinstance(meta.get(k), str) and meta[k]), None)
                if (header.get("type") != "session_meta" or not identity
                        or not project_cwd(cwd, roots)):
                    continue
                session = pseudonym(key, "session:" + identity)
                index.setdefault(session, []).append({"id": identity, "path": str(path)})
                coverage[store + "_matched_files"] += 1
                model = effort = None
                for record, payload in records:
                    at = timestamp(record.get("timestamp"))
                    if at is None or (cutoff is not None and at > cutoff):
                        continue
                    kind = record.get("type")
                    if kind == "turn_context":
                        candidate = payload.get("model")
                        model = candidate if isinstance(candidate, str) and candidate in MODELS else None
                        candidate = value_for(payload, "effort", "reasoning_effort")
                        effort = candidate if isinstance(candidate, str) and candidate in EFFORTS else None
                    elif kind == "compacted":
                        event = {"measured_at": at.isoformat(), "kind": "compaction"}
                        observed.setdefault(session, {})[encode(event)] = event
                    elif kind == "event_msg" and payload.get("type") == "token_count":
                        info = mapping(payload.get("info"))
                        event = {
                            "measured_at": at.isoformat(), "kind": "token_count",
                            "model": model, "effort": effort,
                            "cumulative": counters(value_for(info, "total_token_usage", "total")),
                            "reported_last": counters(value_for(info, "last_token_usage", "last")),
                            "windows": windows(payload.get("rate_limits"), at),
                        }
                        coverage["token_records"] += 1
                        signature = encode(event)
                        bucket = observed.setdefault(session, {})
                        if signature in bucket:
                            coverage["duplicate_token_records"] += 1
                        bucket[signature] = event
            coverage.update(diagnostics)
    return {session: annotate(events.values()) for session, events in sorted(observed.items())}, index, coverage


def index_history(database, roots, key, rollout_sessions, cutoff):
    roots = [normal_path(root) for root in roots]
    observations = {}
    index = {}
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        query = """SELECT id, rollout_path, cwd, created_at, updated_at, archived,
                          tokens_used, model, reasoning_effort FROM threads"""
        for identity, rollout, cwd, created, updated, archived, total, model, effort in db.execute(query):
            if (not isinstance(identity, str) or not identity or not isinstance(rollout, str)
                    or not project_cwd(cwd, roots)):
                continue
            if not all(type(value) is int and 0 <= value <= cutoff.timestamp()
                       for value in (created, updated)):
                continue
            session = pseudonym(key, "session:" + identity)
            if session in rollout_sessions or Path(rollout).is_file():
                continue
            observations[session] = {
                "created_at": datetime.fromtimestamp(created, timezone.utc).isoformat(),
                "updated_at": datetime.fromtimestamp(updated, timezone.utc).isoformat(),
                "archived": bool(archived),
                "model": model if model in MODELS else None,
                "effort": effort if effort in EFFORTS else None,
                "indexed_total_tokens": integer(total) or None,
            }
            index[session] = {"id": identity, "path": rollout}
    return dict(sorted(observations.items())), index


def annotate(events):
    previous = None
    prior_windows = {}
    ordered = sorted(events, key=lambda event: event["measured_at"])
    for event in ordered:
        if event["kind"] != "token_count":
            continue
        cumulative = event["cumulative"]
        if all(value is None for value in cumulative.values()):
            state = "missing"
        elif previous is not None and cumulative == previous:
            state = "repeated"
        elif previous is not None and any(
            previous[name] is not None and value is not None and value < previous[name]
            for name, value in cumulative.items()
        ):
            state = "decreased"
        else:
            state = "first" if previous is None else "changed"
        event["counter_state"] = state
        if state != "missing":
            previous = cumulative
        for duration, reading in event["windows"].items():
            if reading["status"] != "observed":
                continue
            prior = prior_windows.get(duration)
            epoch = reading["reset_epoch"]
            if prior is not None:
                old_epoch, old_used = prior
                if old_epoch is not None and epoch is not None and epoch != old_epoch:
                    reading["boundary"] = "epoch_advanced" if epoch > old_epoch else "epoch_regressed"
                elif reading["used_percent"] < old_used:
                    reading["boundary"] = "decrease"
            prior_windows[duration] = (epoch, reading["used_percent"])
    return ordered


def checkpoint(sessions, at, max_age):
    candidates = [(event["measured_at"], session, event)
                  for session, events in sessions.items() for event in events
                  if event["kind"] == "token_count"]
    if not candidates:
        return None
    _, session, event = max(candidates, key=lambda result: result[:2])
    age = (at - timestamp(event["measured_at"])).total_seconds()
    for reading in event["windows"].values():
        if reading["status"] == "observed" and (
            age > max_age or (reading["reset_epoch"] is not None
                              and reading["reset_epoch"] <= at.timestamp())
        ):
            reading["status"] = "stale"
    return {"session": session, **event}


def compact_history(sessions):
    window_fields = ("used_percent", "reset_epoch", "status", "boundary")
    columns = ["measured_at", "kind", "model", "effort", "counter_state",
               "cumulative", "reported_last", *(str(duration) for duration in DURATIONS)]
    packed = {}
    for session, events in sessions.items():
        packed[session] = []
        for event in events:
            if event["kind"] == "compaction":
                row = [event["measured_at"], event["kind"]]
            else:
                row = [event[name] for name in columns[:5]]
                row.extend([event[name][counter] for counter in TOKENS] for name in columns[5:7])
                row.extend([event["windows"][duration].get(field) for field in window_fields]
                           for duration in DURATIONS)
            packed[session].append(row)
    return {"columns": columns, "token_columns": list(TOKENS), "window_columns": window_fields,
            "sessions": packed}


def write_json(path, data, *, compact=False):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                     dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        output.write((encode(data) if compact else json.dumps(data, indent=2, allow_nan=False)) + "\n")
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, action="append",
                        help="Known Codex home; repeat for distinct private stores")
    parser.add_argument("--root", action="append", type=Path, required=True,
                        help="Allowlisted project checkout (repeat for additional worktrees)")
    parser.add_argument("--private-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--label", required=True, help="Public campaign or batch label")
    parser.add_argument("--checkpoint", help="Public milestone label; export only the latest event")
    parser.add_argument("--at", help="UTC measurement cutoff; defaults to time of collection")
    parser.add_argument("--commit", help="Known public Git commit related to this snapshot")
    parser.add_argument("--account-snapshot", type=Path,
                        help="Private sanitized account/rateLimits/read snapshot")
    parser.add_argument("--compact-history", action="store_true",
                        help="Export event history with declared positional columns")
    parser.add_argument("--state-index", type=Path,
                        help="Export missing-rollout session totals from a known desktop state database")
    args = parser.parse_args()
    if args.state_index and (args.checkpoint or args.compact_history or args.account_snapshot):
        parser.error("export the state index as a separate historical batch")
    for label in (args.label, args.checkpoint):
        if label is not None and not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", label):
            parser.error("use a public slug for campaign and milestone labels")
    if args.commit and not re.fullmatch(r"[0-9a-f]{40}", args.commit):
        parser.error("use a full public commit SHA")
    at = timestamp(args.at) if args.at else datetime.now(timezone.utc)
    if at is None:
        parser.error("measurement cutoff requires an ISO timestamp with timezone")
    private = args.private_dir.resolve()
    if any(private.is_relative_to(root.resolve()) for root in args.root):
        parser.error("keep the key and source index outside project checkouts")
    homes = args.home or [Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")]
    if any(target.is_relative_to(home.resolve() / store)
           for target in (args.output.resolve(), private)
           for home in homes
           for store in ("sessions", "archived_sessions")):
        parser.error("keep outputs outside the input stores")
    if args.state_index and args.output.resolve() == args.state_index.resolve():
        parser.error("keep the output separate from the state index")
    private.mkdir(parents=True, exist_ok=True)
    keyfile = private / "pseudonym-key"
    try:
        with keyfile.open("xb") as key_output:
            key_output.write(os.urandom(32))
    except FileExistsError:
        pass
    key = keyfile.read_bytes()
    if len(key) != 32:
        parser.error("invalid private pseudonym key")
    sessions, index, coverage = collect(homes, args.root, key, cutoff=at)
    write_json(private / "source-index.json", index)
    receipt = {
        "schema_version": 1, "collector_version": 1, "label": args.label,
        "source": "codex_rollout", "coverage": dict(coverage, sessions=len(sessions)),
    }
    if args.state_index:
        historical, missing = index_history(args.state_index, args.root, key, index, at)
        write_json(private / "state-source-index.json", missing)
        receipt.update(source="codex_desktop_state_index", cutoff=at.isoformat(),
                       coverage={"missing_rollout_sessions": len(historical)},
                       sessions=historical)
    elif args.checkpoint:
        receipt.update(checkpoint=args.checkpoint, collected_at=at.isoformat(),
                       commit=args.commit, observation=checkpoint(sessions, at, 900))
    elif args.compact_history:
        receipt["cutoff"] = at.isoformat()
        receipt["history"] = compact_history(sessions)
    else:
        receipt["sessions"] = sessions
    if args.account_snapshot:
        snapshot = mapping(json.loads(args.account_snapshot.read_bytes()))
        measured = timestamp(snapshot.get("measured_at"))
        entries = snapshot.get("windows")
        if measured is None or not isinstance(entries, list) or len(entries) > 2:
            parser.error("invalid account snapshot")
        limits = dict(zip(("primary", "secondary"), entries))
        receipt["account"] = {
            "source": "account/rateLimits/read", "measured_at": measured.isoformat(),
            "windows": windows(limits, measured),
        }
    write_json(args.output, receipt, compact=not (args.checkpoint or args.state_index))


if __name__ == "__main__":
    main()
