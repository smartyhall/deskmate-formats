"""Fictional independent publishers, with deliberately unreliable source clocks."""


def event(seq=1, event_type="agent.note", agent="alpha", **fields):
    machines = {"alpha": ["synthetic-rsx"], "beta": ["synthetic-at"], "gamma": []}
    return {
        "schema_version": 1, "source": "synthetic", "origin_id": f"fixture-{agent}",
        "agent_id": agent, "run_id": f"run-{agent}", "machine_ids": machines[agent],
        "source_sequence": seq, "type": event_type, "summary": f"Synthetic {event_type}",
        "visibility": "observer", **fields,
    }


def trace():
    return (
        event(1, "session.started", source_time_utc="2099-01-01T00:00:00Z"),
        event(1, "turn.started", "beta", source_time_utc="1970-01-01T00:00:00Z"),
        event(1, "milestone.completed", "gamma"),
        event(2, "approval.requested", correlation={"approval": "request-1", "task": "sample"}),
        event(2, "test.completed", "beta", details={"passed": 4, "failed": 0, "skipped": 1}),
        event(4, "approval.resolved", correlation={"approval": "request-1"}),
        event(3, "turn.completed", "beta"),
        event(5, "experiment.checkpoint"),
    )
