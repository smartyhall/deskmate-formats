"""Assemble a frozen campaign snapshot from actual private local records.

The collector reads three things and invents nothing:

* the private campaign registry (recorded campaign identity and live leases),
* deterministic attempt directories (durable plans and terminal outcomes),
* optional usage receipts (explicit measurements, with their own source).

Anything it cannot read is reported as unreachable. Anything a source does not
state is reported as unknown. A campaign that exists only as an attempt is not
given a status it never had. The result is a plain frozen document; the
Observer renders it and cannot mutate anything through it.
"""

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys

from deskmate_formats.observer import campaigns as projection

from . import campaigns, deterministic

MAX_ATTEMPTS = 32
MAX_RECEIPTS = 16
SCHEMA_VERSION = projection.SCHEMA_VERSION


def _stamp(value):
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _attempt_task(status):
    """Project one attempt directory. Nothing is executed or resumed."""
    outcome = status.get("outcome") or {}
    stream = outcome.get("stdout") or {}
    return {
        "id": f"attempt:{status['attempt_id'][:16]}",
        "revision": 1,
        "procedure": status["procedure"],
        "worker": "deterministic-local",
        "attempt": status["attempt_id"],
        "state": status["state"],
        "exit_status": outcome.get("exit_status"),
        "started_at_utc": outcome.get("started_at_utc"),
        "finished_at_utc": outcome.get("finished_at_utc"),
        "result_sha256": stream.get("sha256"),
    }


def _receipts(paths):
    """Read reviewed usage receipts. A malformed receipt is skipped, not guessed."""
    found, unreachable = [], []
    for path in list(paths)[:MAX_RECEIPTS]:
        try:
            value = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            unreachable.append(f"usage receipt unreadable: {Path(path).name}")
            continue
        if type(value) is not dict or not value.get("campaign_id"):
            unreachable.append(f"usage receipt unusable: {Path(path).name}")
            continue
        measurements = []
        for item in value.get("measurements") or []:
            if type(item) is not dict or not item.get("metric") or not item.get("unit"):
                continue
            measurements.append({
                "metric": str(item["metric"])[:64], "unit": str(item["unit"])[:16],
                "value": item.get("value"), "scope": item.get("scope") or "unknown",
                "semantics": item.get("semantics") or "unknown",
                "source": f"receipt:{value.get('checkpoint') or 'unknown'}"[:32],
                "observed_at_utc": item.get("observed_at_utc"),
                "known": item.get("known") is True and item.get("value") is not None,
            })
        found.append((str(value["campaign_id"]), measurements))
    return found, unreachable


def collect(*, registry_directory, attempts=(), receipts=(), now=None):
    """Return a frozen snapshot document. Raises only on an unreadable registry."""
    now = now or datetime.now(UTC)
    try:
        with campaigns.open_registry(registry_directory) as registry:
            records = registry.campaigns()
            leases = registry.leases(now=now)
    except (campaigns.RegistryError, OSError):
        # No private path or record detail belongs in the error or the snapshot.
        raise campaigns.RegistryError("campaign registry is unavailable") from None

    unreachable = []
    tasks = {}
    for directory in list(attempts)[:MAX_ATTEMPTS]:
        try:
            status = deterministic.status(directory)
        except (deterministic.DeterministicError, OSError):
            unreachable.append(f"attempt directory unavailable: {Path(directory).name}")
            continue
        tasks.setdefault(status["campaign"], []).append(status)

    receipt_measurements, receipt_problems = _receipts(receipts)
    unreachable.extend(receipt_problems)
    by_campaign = {}
    for identifier, measurements in receipt_measurements:
        by_campaign.setdefault(identifier, []).extend(measurements)

    entries = {}
    for record in records:
        entries[record.id] = {
            "id": record.id, "owner": record.owner, "provider": record.provider,
            "worker_kind": record.provider, "status": record.status,
            "branch": record.branch, "base_commit": record.base_commit,
            "tasks": [], "resources": [], "measurements": [],
            "sources": [{"label": "campaign registry", "kind": "recorded",
                         "observed_at_utc": record.updated_at}],
        }
    for identifier, statuses in tasks.items():
        entry = entries.get(identifier)
        if entry is None:
            # An attempt exists for a campaign the operator never registered.
            # Report that plainly instead of inventing a status for it.
            entry = entries[identifier] = {
                "id": identifier, "owner": "unknown", "provider": "deterministic",
                "worker_kind": "deterministic", "status": "unrecorded",
                "tasks": [], "measurements": [],
                "sources": [{"label": "attempt directories", "kind": "observed",
                             "observed_at_utc": _stamp(now)}],
                "blockers": [{"summary": "campaign is not in the private registry",
                              "kind": "registry"}],
            }
        for status in statuses:
            entry["tasks"].append(_attempt_task(status))
    for record in records:
        entry = entries[record.id]
        entry["resources"] = [
            {"name": lease.resource, "state": "held", "owner": lease.campaign,
             "expires_at": lease.expires_at, "stale": lease.stale}
            for lease in leases if lease.campaign == record.id]
    for identifier, entry in entries.items():
        entry["measurements"] = by_campaign.get(identifier, [])
        if entry["tasks"]:
            entry["sources"].append({"label": "attempt outcomes", "kind": "observed",
                                     "observed_at_utc": _stamp(now)})
        if entry["measurements"]:
            entry["sources"].append({"label": "usage receipts", "kind": "observed",
                                     "observed_at_utc": _stamp(now)})

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _stamp(now),
        "synthetic": False,
        "campaigns": [entries[key] for key in sorted(entries)],
        "unreachable": unreachable,
        "note": ("Assembled from the private registry, attempt outcomes and usage receipts. "
                 "Unreadable sources are listed as unreachable; unstated values stay unknown."),
    }


def write(snapshot, path):
    """Write the frozen document atomically. The rendering side stays read-only."""
    target = Path(path)
    temp = target.with_name(target.name + ".tmp")
    raw = json.dumps(snapshot, indent=2, sort_keys=True).encode("utf-8")
    with temp.open("wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, target)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--attempt", type=Path, action="append", default=[])
    parser.add_argument("--receipt", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        snapshot = collect(registry_directory=args.registry, attempts=args.attempt,
                           receipts=args.receipt)
    except campaigns.RegistryError as error:
        print(str(error), file=sys.stderr)
        return 2
    write(snapshot, args.output)
    print(json.dumps({"campaigns": len(snapshot["campaigns"]),
                      "unreachable": len(snapshot["unreachable"]),
                      "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
