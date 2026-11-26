"""Synthetic-but-real demonstration of heterogeneous worker coordination.

Two deterministic procedures really execute in owned attempt directories while a
private campaign registry tracks who owns which worktree. The resulting attempt
receipts and an explicitly synthetic agent campaign are projected into the
read-only Observatory campaign view.

Nothing here uses model inference, the network, an emulator, or another agent.
Run it from the repository root:

    python tools/experimental/heterogeneous_workers_demo.py

The state directory defaults to a fresh directory under the system temporary
directory, because Supervisor private state must live outside Git worktrees.
"""

from argparse import ArgumentParser
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import sys
import tempfile
from threading import Thread
from time import sleep
from uuid import uuid4

from deskmate_formats.observer import campaigns as observatory
from deskmate_formats.observer.process_health import process_claim
from deskmate_formats.supervisor import campaigns, deterministic, scheduling

STALE_SECONDS = 900


def _stamp(moment):
    return moment.isoformat(timespec="seconds").replace("+00:00", "Z")


def _with_registry(directory, action, *, attempts=100):
    """Cooperating writers serialize on the registry lock; retry briefly."""
    for attempt in range(attempts):
        try:
            with campaigns.open_registry(directory) as registry:
                return action(registry)
        except campaigns.RegistryBusy:
            if attempt == attempts - 1:
                raise
            sleep(0.02)
    raise AssertionError("unreachable")


def _reserve(registry_directory, campaign, ttl_seconds=600):
    claim = process_claim(os.getpid())
    if claim is None:
        raise SystemExit("cannot establish the owning process identity")

    def reserve(_plan):
        _with_registry(registry_directory, lambda registry: registry.acquire(
            f"worktree:{campaign}", campaign, pid=claim["pid"],
            process_identity=claim["identity"], ttl_seconds=ttl_seconds))

        def release():
            _with_registry(registry_directory, lambda registry: registry.release(
                f"worktree:{campaign}", campaign))
        return release
    return reserve


def run_procedure(state_root, registry, campaign, procedure, arguments, worktree):
    directory = state_root / campaign / procedure
    attempt = deterministic.prepare(directory, campaign=campaign, procedure=procedure,
                                    arguments=arguments, working_directory=str(worktree))
    return deterministic.run(directory, authorization=attempt.plan_sha256,
                             reservation=_reserve(registry, campaign))


def _task(campaign, outcome):
    return {
        "id": f"{campaign}-{outcome['procedure']}",
        "revision": 1,
        "state": outcome["state"],
        "procedure": outcome["procedure"],
        "worker": "deterministic-local",
        "attempt": outcome["attempt_id"],
        "started_at_utc": outcome["started_at_utc"],
        "finished_at_utc": outcome["finished_at_utc"],
        "exit_status": outcome["exit_status"],
        "result_sha256": outcome["stdout"]["sha256"],
    }


def _measurement(metric, unit, *, scope, semantics, source, value=None, observed=None):
    if value is None:
        return {"metric": metric, "unit": unit, "scope": scope, "semantics": semantics,
                "source": "unavailable", "value": None, "observed_at_utc": None, "known": False}
    return {"metric": metric, "unit": unit, "scope": scope, "semantics": semantics,
            "source": source, "value": value, "observed_at_utc": observed, "known": True}


def build_snapshot(registry_directory, outcomes, *, now=None):
    now = now or datetime.now(UTC)
    with campaigns.open_registry(registry_directory) as registry:
        summary = campaigns.summarize(registry, now=now)
    by_campaign = {}
    for campaign, outcome in outcomes:
        by_campaign.setdefault(campaign, []).append(outcome)
    records = []
    for record in summary["campaigns"]:
        record = dict(record)
        tasks = [_task(record["id"], outcome) for outcome in by_campaign.get(record["id"], [])]
        record.update({
            "tasks": tasks,
            "results": [{"label": task["procedure"], "state": task["state"],
                         "exit_status": task["exit_status"]} for task in tasks],
            "measurements": [],
        })
        records.append(record)
    # An explicitly synthetic agent campaign. It proves the projection carries an
    # agent worker alongside deterministic ones without claiming real activity.
    records.append({
        "id": "synthetic-agent-session", "owner": "Freebuff (synthetic)", "provider": "freebuff",
        "worker_kind": "freebuff", "status": "active",
        "milestone": "synthetic multi-worker projection", "checkpoint": "none",
        "tasks": [{"id": "synthetic-analysis", "revision": 1, "state": "running",
                   "worker": "freebuff", "attempt": "synthetic",
                   "started_at_utc": _stamp(now - timedelta(minutes=2))}],
        "resources": [{"name": "worktree:synthetic-agent-session", "state": "held",
                       "owner": "synthetic-agent-session",
                       "expires_at": _stamp(now + timedelta(minutes=10)), "stale": False}],
        "measurements": [
            _measurement("allowance_remaining_hours", "hours", scope="account",
                         semantics="remaining", source="ui-observation"),
            _measurement("thread_input_tokens", "tokens", scope="thread",
                         semantics="cumulative", source="ui-observation"),
            _measurement("context_percent", "percent", scope="thread",
                         semantics="current", source="ui-observation", value=16.0,
                         observed=_stamp(now - timedelta(minutes=3))),
        ],
        "evidence": [{"label": "synthetic", "locator": "not-applicable", "sha256": None}],
    })
    return {"schema_version": 1, "generated_at_utc": _stamp(now), "campaigns": records}


def scheduler_demonstration(now):
    allowance_unknown = scheduling.Measurement.unknown(
        scheduling.ALLOWANCE, "hours", scope="account", semantics="remaining")
    capacities = [
        scheduling.WorkerCapacity("deterministic-local", "deterministic",
                                  frozenset(("prepare", "dispatch")), "available",
                                  ("source-read",)),
        scheduling.WorkerCapacity("codex-app-server", "codex",
                                  frozenset(("prepare", "dispatch")), "available",
                                  ("worktree",), (allowance_unknown,)),
    ]
    requirements = (("hash-and-compare-fixtures", False),
                    ("design-a-new-format-writer", True))
    decisions = []
    for name, requires_inference in requirements:
        decision = scheduling.select(
            scheduling.TaskRequirement(name, requires_inference,
                                       frozenset(("prepare", "dispatch")),
                                       resources=("source-read",)),
            capacities, now=now)
        decisions.append(decision.as_dict())
    return decisions


def main(argv=None):
    parser = ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--worktree", type=Path, default=Path.cwd(),
                        help="repository checkout whose files are hashed (read-only)")
    parser.add_argument("--state", type=Path,
                        help="fresh private state directory outside any Git worktree")
    args = parser.parse_args(argv)

    worktree = args.worktree.resolve()
    state_root = args.state or (Path(tempfile.gettempdir())
                                / f"deskmate-heterogeneous-demo-{uuid4().hex[:8]}")
    if state_root.exists():
        raise SystemExit("state directory must not already exist")
    registry_directory = state_root / "registry"
    state_root.mkdir(parents=True)
    with campaigns.open_registry(registry_directory, create=True):
        pass
    with campaigns.open_registry(registry_directory) as registry:
        for campaign, branch, purpose in (
                ("audit-worker", "freebuff/supervisor-audit", "State audit and deterministic backend"),
                ("docs-worker", "freebuff/observatory-projection", "Campaign projection work")):
            registry.register(campaign, owner="Freebuff", provider="freebuff", branch=branch,
                              worktree=str(worktree), purpose=purpose)

    jobs = [
        ("audit-worker", "hash-files", {"paths": ["README.md", "AGENTS.md"]}),
        ("docs-worker", "fixture-compare",
         {"expected": "pyproject.toml", "actual": "pyproject.toml"}),
    ]
    outcomes, errors = {}, []

    def worker(campaign, procedure, arguments):
        try:
            outcomes[campaign] = run_procedure(state_root, registry_directory, campaign,
                                               procedure, arguments, worktree)
        except Exception as error:  # noqa: BLE001 - the demo reports, never hides
            errors.append((campaign, type(error).__name__))

    threads = [Thread(target=worker, args=job) for job in jobs]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(300)
    if errors:
        raise SystemExit(f"deterministic procedure failed: {errors}")
    if len(outcomes) != len(jobs):
        raise SystemExit("a deterministic worker did not finish")

    now = datetime.now(UTC)
    pairs = [(campaign, outcomes[campaign]) for campaign, _, _ in jobs]
    snapshot = build_snapshot(registry_directory, pairs, now=now)
    view = observatory.projection(snapshot, now=now, stale_seconds=STALE_SECONDS)
    _, text = observatory.render(view, "text")
    _, html = observatory.render(view, "html")
    _, payload = observatory.render(view, "json")

    (state_root / "campaigns-view.json").write_text(payload, encoding="utf-8")
    (state_root / "campaigns.html").write_text(html, encoding="utf-8")

    print(text)
    print("DETERMINISTIC ATTEMPT RECEIPTS")
    for campaign, outcome in pairs:
        print(f"  {campaign}: {outcome['procedure']} -> {outcome['state']} "
              f"exit={outcome['exit_status']} elapsed={outcome['elapsed_seconds']}s "
              f"stdout_sha256={outcome['stdout']['sha256'][:16]}...")
        for artifact in outcome["artifacts"]:
            print(f"    artifact {artifact['path']} {artifact['sha256'][:16]}...")
    print("\nSCHEDULER DECISIONS")
    for decision in scheduler_demonstration(now):
        print(f"  worker={decision['worker_id']} rationale={decision['rationale']}")
        for item in decision["rejected"]:
            print(f"    rejected {item['worker_id']}: {item['reason']}")
        for unknown in decision["unknowns"]:
            print(f"    unknown: {unknown}")
    print(f"\nPrivate state: {state_root}")
    print("Frozen snapshot and rendered page written beside the receipts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
