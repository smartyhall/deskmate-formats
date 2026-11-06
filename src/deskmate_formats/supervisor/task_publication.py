"""Explicit, one-way publication of a committed intake decision."""

from pathlib import Path

from deskmate_formats.observer.events import EventError, normalize_event
from deskmate_formats.observer.journal import JournalError, JournalLimits, publish_event, read_journal

from .task_manifest import TaskError
from .task_queue import open_queue


def publish_decision(directory, journal, identifier, rev, *, limits=JournalLimits()):
    """Return a cursor and whether this call appended it. No queue state changes."""
    queue_path, journal_path = Path(directory).resolve(), Path(journal).resolve()
    if queue_path.is_relative_to(journal_path) or journal_path.is_relative_to(queue_path):
        raise TaskError("queue and event journal require separate private directories")
    if (journal_path / "operations.sqlite3").exists():
        raise TaskError("event journal must be separate from the operation ledger")
    with open_queue(directory) as queue:
        receipt = queue.get(identifier, rev)
        if receipt is None or receipt.state not in ("accepted", "rejected"):
            raise TaskError("only finalized acceptance or rejection can be published")
        counts = queue.counts(through=receipt.sequence)
        totals = ", ".join(f"{state}={count}" for state, count in counts.items())
        payload = normalize_event({
            "schema_version": 1, "source": "supervisor-queue", "agent_id": "supervisor-queue",
            "origin_id": f"queue-{queue.queue_id}-{receipt.sequence}", "run_id": queue.queue_id,
            "source_sequence": 1, "type": f"task.{receipt.state}", "visibility": "observer",
            "source_time_utc": receipt.resolved_at, "correlation": {"task": receipt.id},
            "summary": f"Task {receipt.id} r{receipt.revision} {receipt.state} at {receipt.resolved_at}. "
                       f"Decision totals {totals}",
        })
    try:
        return publish_event(journal, payload, limits=limits).cursor, True
    except EventError:
        replay = read_journal(journal, limits=limits)
        for row in replay.records:
            if all(row.get(key) == value for key, value in payload.items()):
                return row["cursor"], False
        raise JournalError("queue event conflicts with journal history") from None
